"""Profile metadata must improve matching without changing account ownership or money."""
import json
import hashlib
import pytest
import app as studio
import wallet
import customer_auth as auth
import auth_fixture
from test_reservations import client, admin, submit
from test_booking_profile import details, own
from test_customer_auth import request


@pytest.fixture(autouse=True)
def isolated_profiles(monkeypatch):
    monkeypatch.setattr(auth_fixture,'profiles',{})


def protected():
    with studio.database() as db:
        return {
            'balances':[tuple(r) for r in db.execute('SELECT owner_id,minutes,points,version,staff_note FROM studio_members ORDER BY owner_id')],
            'ledger':[tuple(r) for r in db.execute('SELECT * FROM studio_wallet_ledger ORDER BY id')],
            'bookings':[tuple(r) for r in db.execute('SELECT id,owner_id,payload,status,version FROM studio_reservations ORDER BY id')],
        }


def test_native_compatible_profile_update_stays_with_same_customer_and_wallet(client):
    auth_fixture.profiles['qa-owner']={'user_id':'qa-owner','email':'qa@example.test','nickname':'Before','avatar':'/static/old.png'}
    assert submit(client).status_code==201
    admin()
    with studio.database() as db:
        db.execute("UPDATE studio_members SET staff_note='Private original note' WHERE owner_id='qa-owner'")
    before=protected()
    code=client.get('/studio-api/auth/me').json()['user']['customer_code']
    result=client.put('/studio-api/auth/profile',json={'nickname':'New customer name'})
    assert result.status_code==200,result.text
    assert result.json()['user']['id']=='qa-owner' and result.json()['user']['customer_code']==code
    assert result.json()['shared_user']['nickname']=='New customer name'
    account=client.get('/studio-api/manage/members/qa-owner').json()['account']
    assert account['name']=='New customer name' and account['avatar']=='/static/old.png'
    assert account['booking_profile']['name']=='Reservation QA'
    assert protected()==before
    # A repeat cannot issue points, alter the booking or change the reference.
    assert client.put('/studio-api/auth/profile',json={'nickname':'New customer name'}).status_code==200
    wallet.initialize(studio.database)
    assert client.get('/studio-api/auth/me').json()['user']['customer_code']==code
    assert protected()==before


def test_profile_endpoint_rejects_other_owners_and_untrusted_fields(client,monkeypatch):
    client.headers.pop('Authorization')
    assert client.put('/studio-api/auth/profile',json={'nickname':'Name'}).status_code==401
    client.headers['Authorization']='Bearer qa-owner'
    for bad in ({'nickname':''},{'nickname':'x'*21},{'nickname':'Name','owner_id':'qa-other'},
                {'nickname':'Name','is_admin':True},{'nickname':'Name','avatar':'https://elsewhere.invalid/avatar'}):
        assert client.put('/studio-api/auth/profile',json=bad).status_code==422
    def mismatched(path,request,body=None,token='',method=None):
        return {'user_id':'qa-other' if method=='PATCH' else 'qa-owner','email':'qa@example.test','nickname':'Name'}
    monkeypatch.setattr(auth,'upstream',mismatched)
    assert client.put('/studio-api/auth/profile',json={'nickname':'Name'}).status_code==503
    with studio.database() as db:
        assert db.execute("SELECT count(*) FROM studio_members WHERE owner_id='qa-other'").fetchone()[0]==0


def test_bridge_uses_patch_and_fixed_authorized_endpoint(monkeypatch):
    class Reply:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,*args):return b'{"nickname":"New name"}'
    class Opener:
        def open(self,req,timeout):
            assert req.get_method()=='PATCH'
            assert req.full_url.endswith('/api/v1/user/profile')
            assert req.get_header('Authorization')=='Bearer profile-token'
            assert json.loads(req.data)=={'nickname':'New name'}
            return Reply()
    monkeypatch.setattr(auth,'build_opener',lambda *_:Opener())
    assert auth.upstream('profile',request(),{'nickname':'New name'},token='profile-token',method='PATCH')['nickname']=='New name'


def test_optional_wechat_contact_is_searchable_and_legacy_edits_preserve_it(client):
    initial=client.put('/studio-api/auth/booking-profile',json=details(method='phone',contact='+1 416 555 0199')|{'wechat_id':'local_wechat'})
    assert initial.status_code==200,initial.text
    legacy=client.put('/studio-api/auth/booking-profile',json=details(name='Booking name',method='phone',contact='+1 416 555 0199',version=1))
    assert legacy.json()['wechat_id']=='local_wechat'
    assert client.put('/studio-api/auth/booking-profile',json=details(version=1)|{'wechat_id':'changed-id'}).status_code==409
    assert client.put('/studio-api/auth/booking-profile',json=details(version=2)|{'wechat_id':'bad id!'}).status_code==422
    admin()
    matched=client.get('/studio-api/manage/members?search=local_wechat').json()['items']
    assert [r['owner_id'] for r in matched]==['qa-owner']
    assert {'kind':'wechat','value':'local_wechat'} in matched[0]['contacts']
    assert {'kind':'phone','value':'+1 416 555 0199'} in matched[0]['contacts']
    reference=matched[0]['customer_code']
    assert client.get('/studio-api/manage/members?search='+reference).json()['items'][0]['owner_id']=='qa-owner'
    # Explicitly clearing the secondary ID survives both old clients and migrations.
    assert client.put('/studio-api/auth/booking-profile',json=details(version=2)|{'wechat_id':''}).status_code==200
    import booking_profile
    booking_profile.initialize(studio.database)
    assert own(client)['wechat_id']==''


def test_same_contact_or_nickname_never_merges_accounts(client):
    for ident in ('qa-owner','qa-other'):
        client.headers['Authorization']='Bearer '+ident
        client.put('/studio-api/auth/profile',json={'nickname':'Same name'})
        assert client.put('/studio-api/auth/booking-profile',json=details(contact='same-wechat')).status_code==200
    admin()
    matches=client.get('/studio-api/manage/members?search=same-wechat').json()['items']
    assert {r['owner_id'] for r in matches}=={'qa-owner','qa-other'}
    assert len({r['customer_code'] for r in matches})==2
    assert all(r['points']==166 for r in matches)
    assert own(client)['owner_id']=='qa-other'
    # Customer APIs never expose the aggregated contact list or host private note.
    own_wallet=client.get('/studio-api/auth/wallet').json()
    assert 'contacts' not in own_wallet['account'] and 'staff_note' not in own_wallet['account']


def test_saved_avatar_refresh_and_existing_default_names_have_distinct_references(client):
    client.get('/studio-api/auth/me')
    auth_fixture.profiles['qa-owner']['avatar']='/static/new-avatar.png'
    client.get('/studio-api/auth/me')
    admin()
    assert client.get('/studio-api/manage/members/qa-owner').json()['account']['avatar']=='/static/new-avatar.png'
    with studio.database() as db:
        db.execute("UPDATE studio_members SET name='拼豆用户' WHERE owner_id='qa-owner'")
    listed=client.get('/studio-api/manage/members?search=拼豆用户').json()['items'][0]
    assert listed['name']=='拼豆用户_'+hashlib.sha256(b'qa-owner').hexdigest()[:8].upper()
    # Presenting a unique fallback leaves the historical stored name intact.
    with studio.database() as db:assert db.execute("SELECT name FROM studio_members WHERE owner_id='qa-owner'").fetchone()[0]=='拼豆用户'
