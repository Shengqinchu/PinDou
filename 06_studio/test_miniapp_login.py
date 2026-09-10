"""Real native/website handlers with isolated WeChat and shared-account doubles."""
import io,json,time
from urllib.error import URLError
from urllib.parse import parse_qs,urlsplit
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
import app as studio
import miniapp_login as mini
import authing_login as auth
from test_authing_login import configured
from test_reservations import client

PREFIX='/studio-api/auth/wechat/miniapp'
ORIGIN={'Origin':'http://testserver'}
APP='wx0123456789abcdef'
OPEN='o_fixture_wechat_account_1234'

@pytest.fixture
def setup(configured,monkeypatch):
    monkeypatch.setattr(mini,'config',lambda:mini.Config(APP,'s'*32,True,'trial'))
    scenes=[];actions=[]
    def qr(scene):
        scenes.append(scene)
        return 'data:image/png;base64,aW1hZ2U='
    def exchange(code):
        if code=='expired-code':raise HTTPException(400,'miniapp_code_expired')
        return OPEN if code=='real-wechat-code' else OPEN+'other'
    def create(action,**values):
        actions.append((action,values))
        user='wechat_authing_'+values['subject_key']
        return {'token':'signed-new-user','user':{'id':user,'nickname':'New member','email':''},'shared_user':{'user_id':user}}
    monkeypatch.setattr(mini,'qr_image',qr)
    monkeypatch.setattr(mini,'exchange_code',exchange)
    monkeypatch.setattr(auth,'account_action',create)
    return configured,scenes,actions

def start(setup,**changes):
    client,scenes,_=setup
    result=client.post(PREFIX+'/qr/start',json={'return_to':'/visit'}|changes,headers=ORIGIN)
    assert result.status_code==200,result.text
    return result.json()|{'scene':scenes[-1]}

def ticket(client,code='real-wechat-code'):
    result=client.post(PREFIX+'/session',json={'code':code})
    assert result.status_code==200,result.text
    assert set(result.json())=={'ticket','linked','expires_in'}
    return {'X-Pindou-Miniapp':result.json()['ticket']}

def action(client,name,flow):
    return client.post(PREFIX+'/'+name,json={'state':flow['state']},headers=ORIGIN)

def scan(client,flow,proof):
    return client.post(PREFIX+'/scan',json={'scene':flow['scene']},headers=proof)

def confirm(client,flow,proof,**changes):
    return client.post(PREFIX+'/confirm',json={'scene':flow['scene'],'approve':True,'display_code':flow['display_code']}|changes,headers=proof)

def test_existing_account_binding_and_single_browser_finish_preserve_owner(setup):
    client,_,actions=setup
    flow=start(setup);proof=ticket(client)
    assert action(client,'finish',flow).status_code==409
    assert scan(client,flow,proof).json()['status']=='qr_scanned'
    assert actions==[]
    assert confirm(client,flow,proof).json()=={'status':'approved'}
    assert action(client,'qr/poll',flow).json()['status']=='needs_email'
    assert action(client,'bind',flow).json()=={'linked':True}
    assert client.get(PREFIX+'/binding').json()=={'linked':True}
    second=start(setup)
    scan(client,second,proof);confirm(client,second,proof)
    result=action(client,'finish',second)
    assert result.json()['user']['id']=='qa-owner' and result.json()['return_to']=='/visit'
    assert action(client,'finish',second).status_code==409
    assert actions==[]
    with studio.database() as db:
        assert db.execute('SELECT count(*) FROM studio_miniapp_identities').fetchone()[0]==1
        assert db.execute('SELECT result FROM studio_miniapp_flows WHERE state_hash=?',(auth.digest(second['state']),)).fetchone()[0]==''
        assert db.execute("SELECT count(*) FROM studio_wallet_ledger WHERE owner_id='qa-owner'").fetchone()[0]==1

def test_scan_and_approval_never_auto_register_create_is_explicit_and_idempotent(setup):
    client,_,actions=setup;flow=start(setup);proof=ticket(client)
    scan(client,flow,proof)
    assert action(client,'create-account',flow).status_code==409
    confirm(client,flow,proof)
    assert actions==[]
    assert action(client,'create-account',flow).status_code==200
    assert action(client,'create-account',flow).status_code==200
    result=action(client,'finish',flow).json()
    expected=auth.digest('pindou-native-wechat-v1|'+APP+'|'+OPEN)
    assert actions==[('wechat_create',{'subject_key':expected})]
    assert result['user']['id']=='wechat_authing_'+expected
    with studio.database() as db:
        assert db.execute('SELECT points FROM studio_members WHERE owner_id=?',(result['user']['id'],)).fetchone()[0]==166

def test_native_login_requires_explicit_account_then_uses_same_account(setup):
    client,_,actions=setup;proof=ticket(client)
    assert client.post(PREFIX+'/native/sign-in',headers=proof).json()['detail']=='miniapp_account_required'
    assert actions==[]
    assert client.post(PREFIX+'/native/bind',headers=proof).json()=={'linked':True}
    result=client.post(PREFIX+'/native/sign-in',headers=proof).json()
    assert result['user']['id']=='qa-owner'
    assert client.post(PREFIX+'/native/create',headers=proof).json()['user']['id']=='qa-owner'
    assert actions==[]

def test_native_create_grants_registration_reward_once(setup):
    client,_,actions=setup;proof=ticket(client)
    first=client.post(PREFIX+'/native/create',headers=proof)
    assert first.status_code==200
    assert client.post(PREFIX+'/native/create',headers=proof).status_code==200
    assert len(actions)==1
    with studio.database() as db:
        assert db.execute('SELECT points FROM studio_members WHERE owner_id=?',(first.json()['user']['id'],)).fetchone()[0]==166
        assert db.execute('SELECT count(*) FROM studio_wallet_ledger WHERE owner_id=?',(first.json()['user']['id'],)).fetchone()[0]==1

def test_link_mode_displays_existing_account_requires_native_approval(setup):
    client,_,actions=setup;flow=start(setup,mode='link');proof=ticket(client)
    result=scan(client,flow,proof).json()
    assert result['mode']=='link' and result['account']=='Local QA'
    assert result['site']=='pindoupuppy.com' and result['display_code']==flow['display_code']
    assert client.get(PREFIX+'/binding').json()=={'linked':False}
    confirm(client,flow,proof)
    assert action(client,'qr/poll',flow).json()['status']=='linked'
    assert action(client,'create-account',flow).status_code==409
    assert actions==[]

@pytest.mark.parametrize('route',['native/sign-in','native/bind','native/create','scan','confirm'])
def test_native_endpoints_reject_forged_and_expired_ticket(setup,route):
    client,_,_=setup;flow=start(setup)
    body={'scene':flow['scene'],'approve':True,'display_code':flow['display_code']} if route=='confirm' else {'scene':flow['scene']} if route=='scan' else {}
    assert client.post(PREFIX+'/'+route,json=body,headers={'X-Pindou-Miniapp':'x'*43}).status_code==401
    proof=ticket(client)
    with studio.database() as db:db.execute('UPDATE studio_miniapp_tickets SET expires_at=1')
    assert client.post(PREFIX+'/'+route,json=body,headers=proof).status_code==401

def test_client_cannot_supply_wechat_identity_and_invalid_wx_code_fails(setup):
    client,_,_=setup
    for values in [{'code':'real-wechat-code','openid':OPEN},{'code':'real-wechat-code','user_id':'qa-owner'},{'openid':OPEN}]:
        assert client.post(PREFIX+'/session',json=values).status_code==422
    assert client.post(PREFIX+'/session',json={'code':'expired-code'}).json()['detail']=='miniapp_code_expired'

def test_wrong_scanner_wrong_code_and_confirmation_without_scan_rejected(setup):
    client,_,_=setup;flow=start(setup);proof=ticket(client)
    assert confirm(client,flow,proof).status_code==409
    scan(client,flow,proof)
    assert confirm(client,flow,proof,display_code='0000').status_code==400
    other=ticket(client,'another-wechat-code')
    assert scan(client,flow,other).json()['detail']=='miniapp_other_scanner'
    assert confirm(client,flow,other).status_code==409
    assert action(client,'qr/poll',flow).json()['status']=='qr_scanned'

def test_cancellation_cannot_be_approved_or_create_account_later(setup):
    client,_,actions=setup;flow=start(setup);proof=ticket(client)
    scan(client,flow,proof)
    assert confirm(client,flow,proof,approve=False).json()=={'status':'denied'}
    assert confirm(client,flow,proof).status_code==409
    assert action(client,'qr/poll',flow).json()=={'status':'failed','error':'wechat_cancelled'}
    assert action(client,'create-account',flow).status_code==409 and actions==[]

@pytest.mark.parametrize('name',['qr/poll','bind','create-account','finish'])
def test_browser_actions_require_original_browser_and_same_origin(setup,name):
    client,_,_=setup;flow=start(setup);proof=ticket(client)
    scan(client,flow,proof);confirm(client,flow,proof)
    with TestClient(studio.app) as other:
        other.headers['Authorization']='Bearer qa-owner'
        assert action(other,name,flow).status_code==400
    assert client.post(PREFIX+'/'+name,json={'state':flow['state']},headers={'Origin':'https://attacker.invalid'}).status_code==403

def test_expiration_app_change_and_authing_flow_isolation(setup,monkeypatch):
    client,_,_=setup;flow=start(setup);proof=ticket(client)
    assert client.post('/studio-api/auth/wechat/finish',json={'state':flow['state']},headers=ORIGIN).status_code==400
    monkeypatch.setattr(mini,'config',lambda:mini.Config('wxabcdef0123456789','s'*32,True,'trial'))
    assert action(client,'qr/poll',flow).status_code==400
    monkeypatch.setattr(mini,'config',lambda:mini.Config(APP,'s'*32,True,'trial'))
    with studio.database() as db:db.execute('UPDATE studio_miniapp_flows SET expires_at=1')
    assert scan(client,flow,proof).status_code==400
    assert action(client,'qr/poll',flow).status_code==400

def test_binding_never_reassigns_wechat_or_existing_customer(setup):
    client,_,_=setup;proof=ticket(client)
    assert client.post(PREFIX+'/native/bind',headers=proof).status_code==200
    assert client.post(PREFIX+'/native/bind',headers=proof|{'Authorization':'Bearer qa-other'}).json()['detail']=='wechat_binding_conflict'
    other=ticket(client,'another-wechat-code')
    assert client.post(PREFIX+'/native/bind',headers=other).status_code==409
    flow=start(setup,mode='link')
    client.headers['Authorization']='Bearer qa-other'
    flow=start(setup,mode='link')
    scan(client,flow,proof)
    assert confirm(client,flow,proof).json()['detail']=='wechat_binding_conflict'
    with studio.database() as db:assert db.execute('SELECT user_id FROM studio_miniapp_identities').fetchone()[0]=='qa-owner'

def test_native_and_web_binding_require_authenticated_existing_account(setup):
    client,_,_=setup;proof=ticket(client);flow=start(setup)
    scan(client,flow,proof);confirm(client,flow,proof)
    client.headers.pop('Authorization')
    assert client.post(PREFIX+'/native/bind',headers=proof).status_code==401
    assert action(client,'bind',flow).status_code==401
    assert client.post(PREFIX+'/qr/start',json={'mode':'link'},headers=ORIGIN).status_code==401

@pytest.mark.parametrize('target',['https://bad.invalid','//bad.invalid','/api/v1/user/login'])
def test_qr_return_cannot_escape_website(setup,target):
    assert setup[0].post(PREFIX+'/qr/start',json={'return_to':target},headers=ORIGIN).status_code==422

def test_options_default_remains_authing_and_disabled_miniapp_never_selected(setup,monkeypatch):
    client,_,_=setup
    assert client.get('/studio-api/auth/options').json()['wechat_provider']=='authing'
    monkeypatch.setenv('STUDIO_WECHAT_PROVIDER','miniapp')
    assert client.get('/studio-api/auth/options').json()['wechat_provider']=='miniapp'
    monkeypatch.setattr(mini,'config',lambda:mini.Config(APP,'s'*32,False,'trial'))
    assert client.get('/studio-api/auth/options').json()['wechat_provider']=='authing'
    assert client.post(PREFIX+'/session',json={'code':'real-wechat-code'}).status_code==503

def test_real_exchange_shape_discards_session_key_and_unionid(monkeypatch):
    monkeypatch.setattr(mini,'config',lambda:mini.Config(APP,'s'*32,True))
    def request(path,**kwargs):
        assert path=='sns/jscode2session'
        assert kwargs['params']=={'appid':APP,'secret':'s'*32,'js_code':'wx-code','grant_type':'authorization_code'}
        return {'openid':OPEN,'session_key':'never-public','unionid':'never-public'}
    monkeypatch.setattr(mini,'wx_request',request)
    assert mini.exchange_code('wx-code')==OPEN
    monkeypatch.setattr(mini,'wx_request',lambda *a,**kw:{'openid':'bad'})
    with pytest.raises(HTTPException):mini.exchange_code('wx-code')

@pytest.mark.parametrize('environment',['release','trial','develop'])
def test_native_qr_uses_correct_page_environment_and_cached_access_token(monkeypatch,environment):
    mini._access_cache.clear();calls=[]
    monkeypatch.setattr(mini,'config',lambda:mini.Config(APP,'s'*32,True,environment))
    def request(path,body=None,**kwargs):
        calls.append(path)
        if path=='cgi-bin/stable_token':
            assert body['force_refresh'] is False
            return {'access_token':'t'*32,'expires_in':7200}
        assert path=='wxa/getwxacodeunlimit'
        assert body['env_version']==environment and body['check_path']==(environment=='release')
        assert body['page']=='pages/auth/studio-confirm' and body['scene']=='a'*24
        assert kwargs['params']=={'access_token':'t'*32}
        return b'\x89PNG\r\n\x1a\nfixture'
    monkeypatch.setattr(mini,'wx_request',request)
    assert mini.qr_image('a'*24).startswith('data:image/png;base64,')
    mini.qr_image('a'*24)
    assert calls.count('cgi-bin/stable_token')==1
    mini._access_cache.clear()

@pytest.mark.parametrize('payload',[b'{"errcode":40029}',b'{"errcode":40163}',b'{"errcode":40013}',b'not JSON',b'[]',b'x'*600001],ids=['invalid-code','reused-code','bad-app','invalid-json','array','oversize'])
def test_provider_errors_are_safe_and_do_not_leak_secret(monkeypatch,payload):
    class Response(io.BytesIO):pass
    class Opener:
        def open(self,request,timeout):return Response(payload)
    monkeypatch.setattr(mini,'build_opener',lambda *_:Opener())
    with pytest.raises(HTTPException) as result:mini.wx_request('sns/jscode2session',params={'secret':'secret-value'})
    assert 'secret' not in str(result.value.detail)

def test_provider_network_error_does_not_leak_url_or_secret(monkeypatch):
    class Opener:
        def open(self,request,timeout):raise URLError(request.full_url)
    monkeypatch.setattr(mini,'build_opener',lambda *_:Opener())
    with pytest.raises(HTTPException) as result:mini.wx_request('sns/jscode2session',params={'secret':'secret-value'})
    assert result.value.detail=='miniapp_provider_unavailable'
