import hashlib,hmac,json,time,uuid
import pytest
from sqlalchemy import select,text
from fastapi.testclient import TestClient
from pindou.db.models import User
from pindou.services import studio_accounts as service
from pindou.services.password_auth import verify_password
from test_studio_session import api


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
