import json,time
from urllib.parse import urlsplit,parse_qs
import jwt
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
import app as studio
import authing_login as login
from test_reservations import client


@pytest.fixture
def configured(client,monkeypatch):
    settings=login.Config('app-test','https://fixture.authing.cn/app-test/oidc','s'*40,'b'*64,
                          'http://127.0.0.1:8000',('http://testserver',),True,False)
    monkeypatch.setattr(login,'config',lambda:settings)
    monkeypatch.setattr(login,'shared_session',lambda user:{'token':'qa-owner' if user=='qa-owner' else 'qa-other',
        'user':{'id':user,'email':user+'@example.test','nickname':'Fixture'},
        'shared_user':{'user_id':user,'email':user+'@example.test','nickname':'Fixture'}})
    return client


def start(client,**payload):
    response=client.post('/studio-api/auth/wechat/start',json={'return_to':'/visit'}|payload,headers={'Origin':'http://testserver'})
    assert response.status_code==200,response.text
    params={k:v[0] for k,v in parse_qs(urlsplit(response.json()['url']).query).items()}
    assert params['code_challenge_method']=='S256' and params['scope']=='openid'
    return params


def token(params,**changes):
    return jwt.encode({'iss':login.config().issuer,'aud':login.config().app_id,'sub':'wechat-subject',
        'iat':int(time.time()),'exp':int(time.time())+600,'nonce':params['nonce']}|changes,login.config().secret,algorithm='HS256')


def callback(client,monkeypatch,params,**claims):
    def exchange(url,body=None,headers=None,form=False):
        assert url==login.config().issuer+'/token' and form
        assert body['redirect_uri']=='http://testserver'+login.CALLBACK
        import base64,hashlib
        assert base64.urlsafe_b64encode(hashlib.sha256(body['code_verifier'].encode()).digest()).decode().rstrip('=')==params['code_challenge']
        return {'id_token':token(params,**claims)}
    monkeypatch.setattr(login,'fetch_json',exchange)
    return client.get(login.CALLBACK,params={'state':params['state'],'code':'fixture-code'},follow_redirects=False)


def action(client,name,params):
    return client.post('/studio-api/auth/wechat/'+name,json={'state':params['state']},headers={'Origin':'http://testserver'})


def test_origin_state_cookie_and_pkce(configured,monkeypatch):
    client=configured
    assert client.post('/studio-api/auth/wechat/start',json={},headers={'Origin':'https://attacker.invalid'}).status_code==403
    params=start(client)
    assert client.get(login.CALLBACK,params={'state':'a'*43,'code':'x'}).status_code==400
    with TestClient(studio.app) as other:
        assert other.get(login.CALLBACK,params={'state':params['state'],'code':'x'}).status_code==400
    result=callback(client,monkeypatch,params)
    assert result.status_code==303 and 'token' not in result.headers['location']
    assert client.get('/studio-api/auth/wechat/flow',params={'state':params['state']}).json()['status']=='needs_email'
    assert callback(client,monkeypatch,params).status_code==409


def test_first_link_then_wechat_returns_same_existing_identity(configured,monkeypatch):
    client=configured;params=start(client);callback(client,monkeypatch,params)
    assert action(client,'finish',params).status_code==409
    assert action(client,'bind',params).status_code==200
    assert client.get('/studio-api/auth/wechat/binding').json()=={'linked':True}
    second=start(client);callback(client,monkeypatch,second)
    result=action(client,'finish',second)
    assert result.status_code==200 and result.json()['user']['id']=='qa-owner'
    assert result.json()['token']=='qa-owner' and result.json()['return_to']=='/visit'
    assert action(client,'finish',second).status_code==409
    with studio.database() as db:
        assert db.execute('SELECT count(*) FROM studio_auth_identities').fetchone()[0]==1
        assert db.execute('SELECT result FROM studio_oauth_flows WHERE state_hash=?',(login.digest(second['state']),)).fetchone()[0]==''


@pytest.mark.parametrize('target',['https://bad.invalid/','//bad.invalid','/\\bad.invalid','/%5cevil','/api/v1/user/login','/auth/wechat','/%0d%0alocation:evil'])
def test_return_to_cannot_escape_or_invoke_apis(configured,target):
    assert configured.post('/studio-api/auth/wechat/start',json={'return_to':target},headers={'Origin':'http://testserver'}).status_code==422


@pytest.mark.parametrize('claims',[{'iss':'https://other.authing.cn/oidc'}, {'aud':'other-app'},{'nonce':'wrong'},
    {'exp':1},{'iat':int(time.time())+900},{'sub':''},{'aud':['app-test','other']},{'azp':'other-app'}])
def test_invalid_signed_claims_fail_closed(configured,monkeypatch,claims):
    params=start(configured);callback(configured,monkeypatch,params,**claims)
    result=configured.get('/studio-api/auth/wechat/flow',params={'state':params['state']}).json()
    assert result['status']=='failed' and result['error']=='wechat_identity_invalid'
    assert action(configured,'bind',params).status_code==409


def test_expired_flow_and_no_email_authentication(configured,monkeypatch):
    params=start(configured);callback(configured,monkeypatch,params)
    configured.headers.pop('Authorization')
    assert action(configured,'bind',params).status_code==401
    with studio.database() as db:db.execute('UPDATE studio_oauth_flows SET expires_at=1')
    assert configured.get('/studio-api/auth/wechat/flow',params={'state':params['state']}).status_code==400


def test_link_intent_cannot_switch_to_someone_elses_account(configured,monkeypatch):
    params=start(configured,mode='link');callback(configured,monkeypatch,params)
    assert configured.get('/studio-api/auth/wechat/flow',params={'state':params['state']}).json()['status']=='linked'
    configured.headers['Authorization']='Bearer qa-other'
    other=start(configured,mode='link');callback(configured,monkeypatch,other)
    state=configured.get('/studio-api/auth/wechat/flow',params={'state':other['state']}).json()
    assert state['status']=='failed' and state['error']=='wechat_binding_conflict'
    with studio.database() as db:assert db.execute('SELECT user_id FROM studio_auth_identities').fetchone()[0]=='qa-owner'


def test_unknown_algorithm_and_tampering_are_rejected(configured):
    params=start(configured)
    with pytest.raises(Exception):login.verify_id_token(jwt.encode({'nonce':params['nonce']},None,algorithm='none'),params['nonce'])
    valid=token(params);changed=valid[:-8]+'abcdefgh'
    with pytest.raises(HTTPException):login.verify_id_token(changed,params['nonce'])


def test_rsa_jwks_key_rotation_and_signature(configured,monkeypatch):
    from cryptography.hazmat.primitives.asymmetric import rsa
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    jwk=json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key()))|{'kid':'new-key','use':'sig'}
    calls=[]
    def keys(*args,**kwargs):
        calls.append(1)
        return {'keys':[] if len(calls)==1 else [jwk]}
    login.signing_keys.cache_clear();monkeypatch.setattr(login,'fetch_json',keys)
    claims={'iss':login.config().issuer,'aud':login.config().app_id,'sub':'rsa-user','iat':int(time.time()),'exp':int(time.time())+600,'nonce':'expected'}
    encoded=jwt.encode(claims,key,algorithm='RS256',headers={'kid':'new-key'})
    assert login.verify_id_token(encoded,'expected')=='rsa-user' and len(calls)==2
    with pytest.raises(HTTPException):login.verify_id_token(encoded,'wrong')
    attacker=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    with pytest.raises(HTTPException):login.verify_id_token(jwt.encode(claims,attacker,algorithm='RS256',headers={'kid':'new-key'}),'expected')
    login.signing_keys.cache_clear()
