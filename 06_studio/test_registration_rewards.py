import json,uuid
from concurrent.futures import ThreadPoolExecutor
import pytest
import app as studio
import wallet
from test_reservations import client,admin
from test_wallet import prepare,post,get

def test_verified_signin_grants_once_across_concurrent_refresh_and_restart(client):
    assert client.get('/studio-api/auth/me').status_code==200
    with ThreadPoolExecutor(max_workers=8) as pool:
        assert all(r.status_code==200 for r in pool.map(lambda _:client.get('/studio-api/auth/me'),range(12)))
    studio.initialize()
    result=client.get('/studio-api/auth/wallet').json()
    assert result['account']['points']==166 and result['account']['minutes']==0
    assert result['account']['redeemable_cad']==1 and result['total']==1
    assert result['entries'][0]['kind']=='registration_reward'
    admin();assert post(client,kind='opening',minutes_delta=90).status_code==200

def test_first_password_signin_awards_the_same_shared_account(client):
    result=client.post('/studio-api/auth/password-login',json={'email':'new-member@example.test','password':'local-password'}).json()
    client.headers['Authorization']='Bearer '+result['token']
    assert client.get('/studio-api/auth/wallet').json()['account']['points']==166
    again=client.post('/studio-api/auth/password-login',json={'email':'new-member@example.test','password':'local-password'}).json()
    assert again['user']['id']==result['user']['id']
    assert client.get('/studio-api/auth/wallet').json()['total']==1

def test_existing_member_receives_one_increment_and_original_history_is_retained(client):
    with studio.database() as db:
        db.execute("INSERT INTO studio_members(owner_id,name,email,minutes,points,staff_note,created_at,updated_at) VALUES('qa-owner','Existing','qa-owner@example.test',90,188,'private note','2026-09-01','2026-09-01')")
    first=client.get('/studio-api/auth/wallet').json()
    assert first['account']['points']==354 and first['account']['minutes']==90
    assert client.get('/studio-api/auth/wallet').json()['total']==1
    with studio.database() as db:assert db.execute("SELECT staff_note FROM studio_members WHERE owner_id='qa-owner'").fetchone()[0]=='private note'

def test_reversed_registration_reward_is_not_granted_again(client):
    prepare(client);initial=get(client);entry=initial['entries'][0]['id']
    assert client.post(f'/studio-api/manage/members/qa-owner/entries/{entry}/reverse',json={'version':initial['account']['version'],'note':'Correct this award'},headers={'Idempotency-Key':str(uuid.uuid4())}).status_code==200
    assert client.get('/studio-api/auth/wallet').json()['account']['points']==0

@pytest.mark.parametrize('field,value,error',[('no_promotion',None,'wallet_promotion_confirmation_required'),('no_promotion',False,'wallet_promotion_confirmation_required'),('redemption_use',None,'wallet_redemption_use_required')])
def test_redemption_requires_use_and_confirmation_without_writing(client,field,value,error):
    prepare(client);response=post(client,kind='redeem',minutes_delta=0,points_delta=-100,bill_cents=888,**{field:value})
    assert response.status_code==422 and response.json()['detail']==error
    assert get(client)['account']['points']==166 and get(client)['total']==1

def test_shop_redemption_has_audited_use_and_retains_remainder(client):
    prepare(client);response=post(client,kind='redeem',minutes_delta=0,points_delta=-100,bill_cents=888,redemption_use='shop')
    assert response.status_code==200
    data=response.json();assert data['account']['points']==66
    assert data['entries'][0]['redemption_use']=='shop' and data['entries'][0]['no_promotion']==1

def test_old_successful_redemption_retry_survives_policy_change(client):
    prepare(client);key=str(uuid.uuid4());payload={'version':2,'kind':'redeem','minutes_delta':0,'points_delta':-100,'note':'Old verified bill','effective_date':'2026-09-07','reservation_id':'','bill_cents':888}
    with studio.database() as db:
        wallet.append(db,'qa-owner',kind='redeem',minutes=0,points=-100,note=payload['note'],actor='old-host',key=key,digest=wallet.fingerprint(payload|{'owner_id':'qa-owner'}),effective_date='2026-09-07',bill_cents=888)
    response=client.post('/studio-api/manage/members/qa-owner/transactions',json=payload,headers={'Idempotency-Key':key})
    assert response.status_code==200 and response.json()['account']['points']==66 and response.json()['total']==2

def test_notes_visible_and_searchable_only_in_admin_responses(client):
    prepare(client);private='Jessica, WeChat — private desk note'
    assert client.patch('/studio-api/manage/members/qa-owner',json={'version':get(client)['account']['version'],'staff_note':private}).status_code==200
    listing=client.get('/studio-api/manage/members?search=Jessica').json()
    assert listing['total']==1 and listing['items'][0]['staff_note']==private
    assert private not in client.get('/studio-api/auth/wallet').text
    assert 'staff_note' not in client.get('/studio-api/auth/wallet').text
    studio.app.dependency_overrides.clear()
    assert client.get('/studio-api/manage/members?search=Jessica').status_code==401
