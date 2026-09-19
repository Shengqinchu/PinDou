import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
import app as studio
from test_wallet import get, post, prepare
from test_reservations import client, submit


def archive(client, action='delete', version=None, key=None):
    return client.post('/studio-api/manage/members/qa-owner/archive',
                       json={'action': action, 'version': version or get(client)['account']['version']},
                       headers={'Idempotency-Key': key or str(uuid.uuid4())})


def snapshot():
    with studio.database() as db:
        return {table: [tuple(r) for r in db.execute('SELECT * FROM '+table)]
                for table in ('studio_wallet_ledger', 'studio_reservations', 'studio_booking_profiles')}


def test_remove_restore_preserves_every_record_and_does_not_reregister(client):
    prepare(client)
    post(client)
    submit(client)
    before=snapshot();account=get(client)['account'];version=account['version'];key=str(uuid.uuid4())
    assert archive(client, version=version, key=key).status_code==200
    assert archive(client, version=version, key=key).status_code==200
    for search in ('', account['name'], account['email'], 'qa-owner', account['customer_code']):
        assert client.get('/studio-api/manage/members',params={'search':search}).json()['total']==0
    removed=client.get('/studio-api/manage/members?deleted=true').json()
    assert removed['total']==1 and removed['items'][0]['points']==166
    assert get(client)['account']['deleted_at']
    assert snapshot()==before
    # Login and repeat initialization must neither resurrect nor award points.
    client.get('/studio-api/auth/me');studio.initialize();client.get('/studio-api/auth/me')
    assert client.get('/studio-api/manage/members').json()['total']==0
    public=client.get('/studio-api/auth/wallet').json()
    assert public['account']['points']==166 and public['account']['minutes']==600
    assert 'deleted_at' not in public['account']
    assert archive(client, 'restore').status_code==200
    assert client.get('/studio-api/manage/members').json()['total']==1
    assert client.get('/studio-api/manage/members?deleted=true').json()['total']==0
    assert not get(client)['account']['deleted_at']
    assert snapshot()==before
    # A lost delete response retried after restore must not delete again.
    assert archive(client, version=version, key=key).status_code==200
    assert not get(client)['account']['deleted_at']
    assert archive(client, 'restore', version=version, key=key).status_code==409


def test_member_delete_auth_versions_and_concurrent_edits(client):
    assert client.post('/studio-api/manage/members/qa-owner/archive',json={'action':'delete','version':1},headers={'Idempotency-Key':str(uuid.uuid4())}).status_code==401
    prepare(client)
    version=get(client)['account']['version']
    post(client)
    assert archive(client, version=version).status_code==409
    version=get(client)['account']['version']
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses=list(pool.map(lambda _:archive(client,version=version).status_code,range(2)))
    assert sorted(responses)==[200,409]
    assert get(client)['account']['minutes']==600


@pytest.mark.parametrize('amount',[1,29,66,166,332])
def test_admin_fractional_redemption_exact_retry_and_reversal(client,amount):
    prepare(client)
    assert post(client,kind='gift',minutes_delta=0,points_delta=166).status_code==200
    assert client.get('/studio-api/auth/wallet').json()['account']['redeemable_cad']==3
    version=get(client)['account']['version'];key=str(uuid.uuid4())
    result=post(client,kind='redeem',minutes_delta=0,points_delta=-amount,bill_cents=amount,version=version,key=key)
    assert result.status_code==200,result.text
    assert post(client,kind='redeem',minutes_delta=0,points_delta=-amount,bill_cents=amount,version=version,key=key).status_code==200
    state=get(client);entry=state['entries'][0]
    assert state['account']['points']==332-amount and state['total']==3
    assert state['account']['redeemable_cad']==(332-amount)//100
    assert entry['points_delta']==-amount and entry['bill_cents']==amount
    result=client.post(f"/studio-api/manage/members/qa-owner/entries/{entry['id']}/reverse",
                       json={'version':state['account']['version'],'note':'QA reverse exact points'},headers={'Idempotency-Key':str(uuid.uuid4())})
    assert result.status_code==200 and result.json()['account']['points']==332


@pytest.mark.parametrize('changes',[
    {'points_delta':-167,'bill_cents':167}, {'points_delta':-166,'bill_cents':165},
    {'points_delta':-1,'bill_cents':0}, {'points_delta':-1.2,'bill_cents':10},
    {'points_delta':-1,'bill_cents':1.5}, {'points_delta':-1,'bill_cents':True},
    {'points_delta':-1,'bill_cents':1,'no_promotion':False},
])
def test_invalid_fractional_redemption_never_changes_ledger(client,changes):
    prepare(client);before=snapshot()
    assert post(client,kind='redeem',minutes_delta=0,**changes).status_code in (409,422)
    assert snapshot()==before
