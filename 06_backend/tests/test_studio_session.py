"""The bridge issues only existing customer sessions, once per assertion."""
import hashlib,hmac,json,time,uuid
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from pindou.api import studio_session
from pindou.api.deps import get_db
from pindou.api.errors import install_exception_handlers
from pindou.api.security import decode_access_token
from pindou.db.models import Base,User

@pytest.fixture
def api(monkeypatch):
    monkeypatch.setenv('PINDOU_STUDIO_AUTH_BRIDGE_KEY','k'*64)
    engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
    Base.metadata.create_all(engine);sessions=sessionmaker(engine,expire_on_commit=False)
    with sessions() as db:
        db.add(User(openid='email-fixture',email='fixture@example.test',free_credits_remaining=3,paid_credits=188))
        db.add(User(openid='anonymous-fixture'));db.commit()
    app=FastAPI();app.include_router(studio_session.router);install_exception_handlers(app)
    def database():
        with sessions() as db:yield db
    app.dependency_overrides[get_db]=database
    with TestClient(app,client=('127.0.0.1',19000)) as client:yield client,app,sessions
    engine.dispose()

def assertion(**changes):
    data={'user_id':'email-fixture','issued_at':int(time.time()),'nonce':uuid.uuid4().hex,'audience':'pindou-studio-customer'}|changes
    signature=hmac.new(b'k'*64,json.dumps(data,sort_keys=True,separators=(',',':')).encode(),hashlib.sha256).hexdigest()
    return {'json':data,'headers':{'X-Studio-Signature':signature}}

def test_customer_identity_credits_and_replay(api):
    client,app,sessions=api;request=assertion();response=client.post('/studio-session/exchange',**request)
    assert response.status_code==200,response.text
    data=response.json();claims=decode_access_token(data['token'])
    assert claims['sub']=='email-fixture' and claims['role']=='user' and claims.get('is_admin',False) is False
    assert data['user']['user_id']=='email-fixture'
    assert client.post('/studio-session/exchange',**request).status_code==409
    with sessions() as db:
        assert db.query(User).count()==2
        user=db.query(User).filter(User.openid=='email-fixture').one()
        assert user.paid_credits==188 and user.free_credits_remaining==3

@pytest.mark.parametrize('changes',[{'user_id':'unknown'},{'user_id':'anonymous-fixture'}, {'issued_at':1},{'issued_at':int(time.time())+60}])
def test_invalid_existing_customer_or_time(api,changes):
    assert api[0].post('/studio-session/exchange',**assertion(**changes)).status_code==401

def test_requires_loopback_key_and_fixed_claims(api,monkeypatch):
    client,app,_=api
    with TestClient(app,client=('203.0.113.4',443)) as external:
        assert external.post('/studio-session/exchange',**assertion()).status_code==403
    request=assertion();request['headers']['X-Studio-Signature']='0'*64
    assert client.post('/studio-session/exchange',**request).status_code==401
    assert client.post('/studio-session/exchange',**assertion(role='admin')).status_code==422
    assert client.post('/studio-session/exchange',**assertion(audience='admin')).status_code==422
    monkeypatch.delenv('PINDOU_STUDIO_AUTH_BRIDGE_KEY')
    assert client.post('/studio-session/exchange',**assertion()).status_code==503
