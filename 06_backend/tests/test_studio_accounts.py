import hashlib,hmac,json,time,uuid
import pytest
from sqlalchemy import select,text
from fastapi.testclient import TestClient
from pindou.db.models import User
from pindou.services import studio_accounts as service
from pindou.services.password_auth import verify_password
from test_studio_session import api
from pindou.api.security import decode_access_token
from pindou.services.user_service import email_openid,UserService
from pindou.db.models import CreditGrant


def assertion(action,**values):
    data={'action':action,'issued_at':int(time.time()),'nonce':uuid.uuid4().hex,'audience':'pindou-studio-account',**values}
    signature=hmac.new(b'k'*64,json.dumps(data,sort_keys=True,separators=(',',':')).encode(),hashlib.sha256).hexdigest()
    return {'json':data,'headers':{'X-Studio-Signature':signature}}


def test_new_wechat_account_is_stable_and_cannot_become_admin(api):
    client,app,sessions=api;request=assertion('wechat_create',subject_key='a'*64)
    one=client.post('/studio-session/account',**request)
    assert one.status_code==200,one.text
    assert one.json()['user']['user_id']=='wechat_authing_'+'a'*64
    assert client.post('/studio-session/account',**request).status_code==409
    two=client.post('/studio-session/account',**assertion('wechat_create',subject_key='a'*64))
    assert two.json()['user']['user_id']==one.json()['user']['user_id']
    assert client.post('/studio-session/account',**assertion('wechat_create',subject_key='b'*64,role='admin')).status_code==422
    with sessions() as db:assert db.query(User).count()==3
    with TestClient(app,client=('203.0.113.10',99)) as external:
        assert external.post('/studio-session/account',**assertion('wechat_create',subject_key='c'*64)).status_code==403
    bad=assertion('wechat_create',subject_key='b'*64);bad['headers']['X-Studio-Signature']='0'*64
    assert client.post('/studio-session/account',**bad).status_code==401


def test_recovery_only_existing_accounts_and_password_not_login(api,monkeypatch):
    client,_,sessions=api;sent=[]
    monkeypatch.setattr(service,'deliver_recovery',lambda email,code:sent.append((email,code)) or True)
    unknown=client.post('/studio-session/account',**assertion('recovery_send',email='missing@example.test',ip='127.0.0.1'))
    first=client.post('/studio-session/account',**assertion('recovery_send',email='fixture@example.test',ip='127.0.0.1'))
    assert first.json()==unknown.json() and len(sent)==1
    data={'email':sent[0][0],'code':sent[0][1],'password':'new-password'}
    result=client.post('/studio-session/account',**assertion('recovery_reset',**data))
    assert result.json()=={'success':True} and 'token' not in result.text
    assert client.post('/studio-session/account',**assertion('recovery_reset',**data)).json()['error']=='account_code_invalid'
    with sessions() as db:
        user=db.scalar(select(User).where(User.email==data['email']))
        assert verify_password('new-password',user.password_hash)
        assert user.paid_credits==188 and user.free_credits_remaining==3
        assert db.query(User).count()==2


def test_recovery_cooldown_guess_limit_and_expiry(api,monkeypatch):
    client,_,sessions=api;sent=[]
    monkeypatch.setattr(service,'deliver_recovery',lambda email,code:sent.append(code) or True)
    client.post('/studio-session/account',**assertion('recovery_send',email='fixture@example.test',ip='127.0.0.1'))
    assert client.post('/studio-session/account',**assertion('recovery_send',email='fixture@example.test',ip='127.0.0.1')).json()['error']=='account_rate_limited'
    wrong='000000' if sent[0]!='000000' else '111111'
    for _ in range(5):
        assert client.post('/studio-session/account',**assertion('recovery_reset',email='fixture@example.test',code=wrong,password='new-password')).json()['error']=='account_code_invalid'
    assert client.post('/studio-session/account',**assertion('recovery_reset',email='fixture@example.test',code=sent[0],password='new-password')).json()['error']=='account_code_invalid'
    with sessions() as db:db.execute(text('UPDATE studio_recovery_codes SET attempts=0,expires_at=1'));db.commit()
    assert client.post('/studio-session/account',**assertion('recovery_reset',email='fixture@example.test',code=sent[0],password='new-password')).json()['error']=='account_code_expired'
    assert len(sent)==1


def test_password_registration_is_new_only_and_sends_no_mail(api,monkeypatch):
    client,_,sessions=api
    monkeypatch.setattr(service,'deliver_recovery',lambda *args:pytest.fail('Registration must not send mail'))
    data={'email':' New@Example.Test ','password':'local-password','ip':'203.0.113.8'}
    one=client.post('/studio-session/account',**assertion('password_register',**data))
    assert one.status_code==200,one.text
    assert one.json()['user']['email']=='new@example.test'
    ident=email_openid('new@example.test');claims=decode_access_token(one.json()['token'])
    assert claims['sub']==ident and claims['role']=='user' and not claims.get('is_admin')
    with sessions() as db:
        user=UserService(db).authenticate_email_password(email='new@example.test',password='local-password')
        assert user.user_id==ident
        gift=db.query(CreditGrant).filter_by(owner_id=ident,source_type='register_gift').one()
        before=(user.password_hash,gift.amount_remaining,db.query(User).count())
    data.update(email='NEW@example.test',password='replacement-password')
    duplicate=client.post('/studio-session/account',**assertion('password_register',**data))
    assert duplicate.json()=={'error':'account_already_registered'}
    with sessions() as db:
        user=db.scalar(select(User).where(User.openid==ident))
        assert before==(user.password_hash,db.query(CreditGrant).filter_by(owner_id=ident,source_type='register_gift').one().amount_remaining,db.query(User).count())


def test_registration_cannot_claim_legacy_or_privileged_accounts(api,monkeypatch):
    client,_,sessions=api
    data={'email':'fixture@example.test','password':'replacement','ip':'203.0.113.10'}
    assert client.post('/studio-session/account',**assertion('password_register',**data)).json()=={'error':'account_already_registered'}
    with sessions() as db:
        existing=db.scalar(select(User).where(User.email=='fixture@example.test'))
        assert existing.password_hash is None and existing.paid_credits==188
        db.add(User(openid=email_openid('collision@example.test'),email=None));db.commit()
    data.update(email='collision@example.test')
    assert client.post('/studio-session/account',**assertion('password_register',**data)).json()=={'error':'account_already_registered'}
    from types import SimpleNamespace
    monkeypatch.setattr(service,'get_settings',lambda:SimpleNamespace(unlimited_credit_email_set={'reserved@example.test'}))
    data.update(email='reserved@example.test')
    assert client.post('/studio-session/account',**assertion('password_register',**data)).json()=={'error':'account_already_registered'}
    with sessions() as db:assert db.query(User).count()==3


def test_registration_rejects_forged_claims_invalid_password_and_rate(api):
    client,_,sessions=api
    data={'email':'new@example.test','password':'local-password','ip':'203.0.113.8'}
    assert client.post('/studio-session/account',**assertion('password_register',**data,role='admin')).status_code==422
    assert client.post('/studio-session/account',**assertion('password_register',**(data|{'password':'short'}))).status_code==422
    request=assertion('password_register',**data);request['headers']['X-Studio-Signature']='0'*64
    assert client.post('/studio-session/account',**request).status_code==401
    for _ in range(3):client.post('/studio-session/account',**assertion('password_register',**(data|{'email':'fixture@example.test'})))
    assert client.post('/studio-session/account',**assertion('password_register',**data)).json()=={'error':'account_rate_limited'}
    with sessions() as db:assert db.query(User).count()==2


def test_parallel_registration_creates_one_user_and_one_gift(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from pindou.db.models import Base
    engine=create_engine('sqlite:///'+str(tmp_path/'concurrent.sqlite3'),connect_args={'check_same_thread':False,'timeout':20})
    Base.metadata.create_all(engine);sessions=sessionmaker(engine,expire_on_commit=False)
    def register(ip):
        with sessions() as db:return service.password_account(db,'concurrent@example.test','local-password',ip)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(register,['203.0.113.20','203.0.113.21']))
        assert sum(isinstance(result,User) for result in results)==1
        assert sum(result=={'error':'account_already_registered'} for result in results if isinstance(result,dict))==1
        with sessions() as db:
            assert db.query(User).count()==1
            assert db.query(CreditGrant).filter_by(source_type='register_gift').count()==1
    finally:engine.dispose()
