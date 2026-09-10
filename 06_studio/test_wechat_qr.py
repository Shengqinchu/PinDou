import time
import pytest
from fastapi.testclient import TestClient
import app as studio
import authing_login as auth
import wechat_qr as qr
from test_authing_login import configured
from test_reservations import client

ORIGIN={'Origin':'http://testserver'}
SUBJECT='a'*24


@pytest.fixture
def provider(configured,monkeypatch):
    state={'status':0,'calls':[],'subject':SUBJECT}
    def request(path,body=None):
        state['calls'].append((path,body))
        if path=='gene':
            assert body=={'scene':'WXAPP_AUTH','autoMergeQrCode':False}
            return {'random':'generatedQR123','url':'https://files.authing.co/qr.png'}
        if path.startswith('check?'):return {'random':'generatedQR123','status':state['status'],'ticket':'server-only-ticket'}
        if path=='userinfo':
            assert body=={'ticket':'server-only-ticket'}
            return {'id':state['subject']}
        raise AssertionError(path)
    monkeypatch.setattr(qr,'provider',request)
    return configured,state


def start(client,**values):
    result=client.post('/studio-api/auth/wechat/qr/start',headers=ORIGIN,json={'return_to':'/visit?step=3',**values})
    assert result.status_code==200,result.text
    assert set(result.json())=={'state','image','expires_in'}
    assert 'HttpOnly' in result.headers['set-cookie']
    return result.json()['state']


def poll(client,state):
    with studio.database() as db:db.execute('UPDATE studio_oauth_flows SET poll_after=0')
    return client.post('/studio-api/auth/wechat/qr/poll',headers=ORIGIN,json={'state':state})


def test_qr_generation_poll_binding_and_same_account(provider):
    client,remote=provider;state=start(client)
    assert poll(client,state).json()['status']=='qr_pending'
    remote['status']=1;assert poll(client,state).json()['status']=='qr_scanned'
    remote['status']=2;assert poll(client,state).json()['status']=='needs_email'
    assert client.post('/studio-api/auth/wechat/bind',headers=ORIGIN,json={'state':state}).status_code==200
    state=start(client);assert poll(client,state).json()['status']=='ready'
    result=client.post('/studio-api/auth/wechat/finish',headers=ORIGIN,json={'state':state})
    assert result.json()['user']['id']=='qa-owner'
    assert result.json()['return_to']=='/visit?step=3'
    assert client.post('/studio-api/auth/wechat/finish',headers=ORIGIN,json={'state':state}).status_code==409


def test_no_browser_identity_ticket_or_cross_site_state(provider):
    client,remote=provider
    assert client.post('/studio-api/auth/wechat/qr/start',json={},headers={'Origin':'https://evil.invalid'}).status_code==403
    state=start(client)
    assert client.post('/studio-api/auth/wechat/qr/poll',headers=ORIGIN,json={'state':state,'ticket':'forged','subject':SUBJECT}).status_code==422
    with TestClient(studio.app) as other:
        assert other.post('/studio-api/auth/wechat/qr/poll',headers=ORIGIN,json={'state':state}).status_code==400
    assert len(remote['calls'])==1


@pytest.mark.parametrize('status,error',[(-1,'wechat_flow_expired'),(3,'wechat_cancelled')])
def test_cancelled_expired_codes_never_create_identity(provider,status,error):
    client,remote=provider;state=start(client);remote['status']=status
    assert poll(client,state).json()=={'status':'failed','error':error}
    with studio.database() as db:assert db.execute('SELECT count(*) FROM studio_auth_identities').fetchone()[0]==0


def test_provider_identity_shape_and_qr_expiry(provider):
    client,remote=provider;state=start(client);remote.update(status=2,subject='forged profile')
    assert poll(client,state).json()['error']=='wechat_identity_invalid'
    state=start(client)
    with studio.database() as db:db.execute('UPDATE studio_oauth_flows SET created_at=?',(int(time.time())-121,))
    assert poll(client,state).json()['error']=='wechat_flow_expired'


def test_qr_link_intent_cannot_switch_existing_account(provider):
    client,remote=provider;state=start(client,mode='link');remote['status']=2
    assert poll(client,state).json()['status']=='linked'
    client.headers['Authorization']='Bearer qa-other';state=start(client,mode='link')
    assert poll(client,state).json()['error']=='wechat_binding_conflict'


def test_new_account_only_after_verified_qr_and_explicit_request(provider,monkeypatch):
    client,remote=provider;client.headers.pop('Authorization');state=start(client)
    assert client.post('/studio-api/auth/wechat/create-account',headers=ORIGIN,json={'state':state}).status_code==409
    remote['status']=2;assert poll(client,state).json()['status']=='needs_email'
    calls=[]
    def create(action,**values):
        calls.append((action,values));ident='wechat_authing_'+values['subject_key']
        return {'token':'created-fixture','user':{'id':ident,'email':'','nickname':''},'shared_user':{'user_id':ident,'email':None}}
    monkeypatch.setattr(auth,'account_action',create)
    assert client.post('/studio-api/auth/wechat/create-account',headers=ORIGIN,json={'state':state}).json()['status']=='ready'
    assert client.post('/studio-api/auth/wechat/create-account',headers=ORIGIN,json={'state':state}).status_code==409
    result=client.post('/studio-api/auth/wechat/finish',headers=ORIGIN,json={'state':state})
    assert result.status_code==200,result.text
    assert len(calls)==1 and calls[0][0]=='wechat_create'
    with studio.database() as db:
        assert db.execute('SELECT count(*) FROM studio_auth_identities').fetchone()[0]==1
        assert db.execute("SELECT count(*) FROM studio_wallet_ledger WHERE kind='registration_reward'").fetchone()[0]==1


@pytest.mark.parametrize('url',['http://files.authing.co/x','https://files.authing.co.evil.invalid/x','https://evil.invalid/x','data:text/html,bad','https://a:password@files.authing.co/x'])
def test_provider_image_allowlist(url):
    with pytest.raises(Exception):qr.image_url(url)
