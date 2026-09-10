"""Real Studio HTTP handlers with an isolated legacy-account service double."""
import io,json,uuid
from datetime import datetime,timedelta
from urllib.error import HTTPError,URLError
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request
import app as studio
import customer_auth as auth
from test_reservations import client,submit,body

def request():return Request({'type':'http','method':'POST','headers':[],'client':('127.0.0.1',123),'path':'/'})

def test_public_pages_and_calendar_need_no_login_but_submission_does(client):
    client.headers.pop('Authorization')
    assert client.get('/studio-api/reservation-calendar').status_code==200
    assert client.get('/studio-api/journal').status_code==200
    assert client.get('/studio-api/auth/options').json()=={'email':False,'password':True,'recovery':True,'wechat':False,'phone':False,'wechat_provider':'authing','miniapp_available':False}
    assert submit(client).status_code==401
    assert client.get('/studio-api/auth/me').status_code==401
    assert client.get('/studio-api/auth/reservations').status_code==401
    from test_app import visit
    assert client.post('/studio-api/requests',json=visit(),headers={'Idempotency-Key':str(uuid.uuid4())}).status_code==401
    with studio.database() as db:assert db.execute('SELECT count(*) FROM studio_reservations').fetchone()[0]==0

def test_account_owns_receipts_across_browsers_and_idempotency(client):
    key=str(uuid.uuid4());ref=submit(client,key=key).json()['id']
    with TestClient(studio.app) as other:
        other.get('/studio-api/reservation-calendar')
        other.headers['Authorization']='Bearer qa-other'
        assert other.get('/studio-api/reservations/'+ref).status_code==404
        assert other.get('/studio-api/auth/reservations').json()['items']==[]
        assert submit(other,key=key).status_code==409
        other.headers['Authorization']='Bearer qa-owner'
        assert other.get('/studio-api/reservations/'+ref).status_code==200
        assert submit(other,key=key).json()['id']==ref
        assert other.get('/studio-api/auth/reservations').json()['items'][0]['id']==ref
    with studio.database() as db:
        row=db.execute('SELECT owner_id FROM studio_reservations').fetchone();assert row[0]=='qa-owner'
        assert db.execute('SELECT count(*) FROM studio_reservations').fetchone()[0]==1

def test_legacy_anonymous_receipt_stays_browser_private(client):
    ref=submit(client).json()['id']
    with studio.database() as db:db.execute("UPDATE studio_reservations SET owner_id='' WHERE id=?",(ref,))
    client.headers.pop('Authorization')
    assert client.get('/studio-api/reservations/'+ref).status_code==200
    with TestClient(studio.app) as other:
        other.get('/studio-api/reservation-calendar')
        assert other.get('/studio-api/reservations/'+ref).status_code==404

def test_password_shared_identity_and_email_codes_are_not_login(client,monkeypatch):
    client.headers.pop('Authorization');email='existing@example.test'
    for path,body in [('send-code',{'email':email}),('code-login',{'email':email,'code':'123456'}),('register',{'email':email,'code':'123456','password':'local-password'})]:
        response=client.post('/studio-api/auth/'+path,json=body)
        assert response.status_code==410 and response.json()['detail']=='account_code_login_disabled'
    password=client.post('/studio-api/auth/password-login',json={'email':email,'password':'local-password'}).json()
    assert password['user']['id']==password['shared_user']['user_id'] and 'device_token' not in password
    assert client.post('/studio-api/auth/password-login',json={'email':email,'password':'incorrect'}).status_code==401


def test_expired_or_fake_email_less_identity_cannot_reserve(client,monkeypatch):
    client.headers['Authorization']='Bearer expired'
    assert submit(client).status_code==401
    monkeypatch.setattr(auth,'upstream',lambda *a,**kw:{'user_id':'wx_development_stub','email':None})
    assert client.get('/studio-api/auth/me').json()['detail']=='account_email_required'
    assert submit(client).status_code==401

def test_rate_limits_apply_to_login_and_sending(client):
    for _ in range(10):client.post('/studio-api/auth/password-login',json={'email':'test@example.test','password':'incorrect'})
    assert client.post('/studio-api/auth/password-login',json={'email':'test@example.test','password':'local-password'}).status_code==429

@pytest.mark.parametrize('status,code,expected',[(400,'EMAIL_CODE_INVALID','account_code_invalid'),(400,'EMAIL_CODE_EXPIRED','account_code_expired'),(429,'EMAIL_CODE_RATE_LIMITED','account_rate_limited'),(503,'EMAIL_SEND_FAILED','account_email_unavailable')])
def test_real_upstream_error_shape_is_translated(monkeypatch,status,code,expected):
    class Opener:
        def open(self,req,timeout):raise HTTPError(req.full_url,status,'',{},io.BytesIO(json.dumps({'error':code,'message_cn':'private upstream error'}).encode()))
    monkeypatch.setattr(auth,'build_opener',lambda *_:Opener())
    with pytest.raises(HTTPException) as error:auth.upstream('email/verify',request(),{'email':'a@example.test','code':'123456'})
    assert error.value.detail==expected

def test_fixed_upstream_allowlist_no_redirect_and_failure_closed(monkeypatch):
    with pytest.raises(HTTPException):auth.upstream('https://external.invalid',request(),token='secret')
    with pytest.raises(HTTPException):auth.NoRedirect().redirect_request(None,None,302,'',{},'https://external.invalid')
    class Opener:
        def open(self,req,timeout):
            assert req.full_url.endswith('/api/v1/user/profile')
            assert req.get_header('Authorization')=='Bearer safe-fixture-token'
            assert 'password' not in req.full_url
            raise URLError('No connection')
    monkeypatch.setattr(auth,'build_opener',lambda *_:Opener())
    with pytest.raises(HTTPException) as error:auth.upstream('profile',request(),token='safe-fixture-token')
    assert error.value.status_code==503

def test_account_profile_exposes_shared_avatar_but_no_provider_or_private_fields(client,monkeypatch):
    monkeypatch.setattr(auth,'upstream',lambda *a,**kw:{'user_id':'qa-owner','email':'qa@example.test',
        'nickname':'Shared name','avatar':'/static/thumbnails/avatar_test.png','phone':'private',
        'password_hash':'private','wechat_openid':'private','paid_credits':188})
    assert client.get('/studio-api/auth/me').json()['user']=={
        'id':'qa-owner','email':'qa@example.test','nickname':'Shared name','avatar':'/static/thumbnails/avatar_test.png'}


def test_password_signup_uses_bridge_and_rewards_once(client,monkeypatch):
    import authing_login as login
    from test_authing_login import configured
    settings=login.Config('app-test','https://fixture.authing.cn/app-test/oidc','s'*40,'b'*64,
        'http://127.0.0.1:8000',('http://testserver',),True,False)
    monkeypatch.setattr(login,'config',lambda:settings)
    calls=[]
    def action(name,**values):
        calls.append((name,values))
        return {'token':'qa-email-registration','user':{'id':'qa-email-registration','email':values['email'],'nickname':'New member'},'shared_user':{'user_id':'qa-email-registration','email':values['email']}}
    monkeypatch.setattr(login,'account_action',action)
    payload={'email':'  New@Example.Test ','password':'local-password'}
    response=client.post('/studio-api/auth/password-register',json=payload,headers={'Origin':'http://testserver'})
    assert response.status_code==200,response.text
    assert calls[0][0]=='password_register' and calls[0][1]['email']=='new@example.test'
    assert 'code' not in calls[0][1] and response.json()['token']=='qa-email-registration'
    # A retried shared result cannot duplicate the Studio registration reward.
    assert client.post('/studio-api/auth/password-register',json=payload,headers={'Origin':'http://testserver'}).status_code==200
    with studio.database() as db:
        assert db.execute("SELECT points FROM studio_members WHERE owner_id='qa-email-registration'").fetchone()[0]==166
        assert db.execute("SELECT count(*) FROM studio_wallet_ledger WHERE owner_id='qa-email-registration'").fetchone()[0]==1
    assert client.post('/studio-api/auth/password-register',json=payload,headers={'Origin':'https://attacker.invalid'}).status_code==403
    assert len(calls)==2
    for changes in [{'password':'short'},{'role':'admin'},{'email':'not an email'}]:
        assert client.post('/studio-api/auth/password-register',json=payload|changes,headers={'Origin':'http://testserver'}).status_code==422
