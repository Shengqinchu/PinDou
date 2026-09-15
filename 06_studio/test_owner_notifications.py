import asyncio
import json
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from types import SimpleNamespace
from urllib.error import HTTPError, URLError

import pytest
from fastapi.testclient import TestClient

import app as studio
import customer_auth
import owner_notifications as alerts
import owner_wechat
import reservations
from auth_fixture import fake_upstream, reject_legacy_admin

KEY = 'SCT12345678901234567890ForLocalTestsOnly'


@pytest.fixture
def setup(tmp_path, monkeypatch):
    studio.app.dependency_overrides.clear()
    monkeypatch.setattr(studio, 'DB_PATH', tmp_path/'studio.sqlite3')
    monkeypatch.setattr(reservations, 'now_local', lambda: datetime(2026,9,10,9,0,tzinfo=reservations.ZONE))
    monkeypatch.setattr(reservations, 'COOKIE_SECURE', False)
    monkeypatch.setattr(customer_auth, 'upstream', fake_upstream)
    monkeypatch.setattr(studio, 'urlopen', reject_legacy_admin)
    monkeypatch.delenv('STUDIO_SERVERCHAN_SENDKEY', raising=False)
    async def paused_worker(_database,channel='serverchan'):
        await asyncio.Event().wait()
    monkeypatch.setattr(alerts, 'worker', paused_worker)
    monkeypatch.setattr(owner_wechat, 'worker', paused_worker)
    import customer_notifications
    monkeypatch.setattr(customer_notifications,'worker',paused_worker)
    sent=[]
    def deliver(key,title,body):
        sent.append((key,title,body))
        return {'ok':True,'provider_id':'provider-test-1'}
    monkeypatch.setattr(alerts, 'deliver', deliver)
    with TestClient(studio.app) as client:
        client.headers['Authorization']='Bearer qa-owner'
        client.get('/studio-api/reservation-calendar')
        yield client,sent,tmp_path
    studio.app.dependency_overrides.clear()


def host():
    studio.app.dependency_overrides[studio.admin_actor]=lambda:'local-test-owner'


def configure(client, **changes):
    host()
    current=client.get('/studio-api/manage/owner-notifications').json()
    payload={'version':current['version'],'enabled':True,'daily_limit':1000,'language':'zh','sendkey':KEY,**changes}
    return client.put('/studio-api/manage/owner-notifications',json=payload)


def create(client, key=None):
    return client.post('/studio-api/reservations',headers={'Idempotency-Key':key or str(uuid.uuid4())},json={
        'booking':{'date':'2026-09-11','start':'14:00','end':'16:00','plan':'hourly','guests':2},
        'name':'客人 Local Test','contact_method':'wechat','contact':'private-contact-value','notes':'private-customer-note', 'consent':True})


def jobs():
    with studio.database() as db:
        return [dict(r) for r in db.execute('SELECT * FROM studio_owner_notifications ORDER BY created_at')]


def test_host_only_configuration_and_secret_storage(setup):
    client,sent,path=setup
    assert client.get('/studio-api/manage/owner-notifications').status_code==401
    assert client.put('/studio-api/manage/owner-notifications',json={'version':1,'enabled':True,'sendkey':KEY}).status_code==401
    response=configure(client)
    assert response.status_code==200
    assert KEY not in response.text and response.json()['configured'] is True
    assert (path/'serverchan-secret.json').exists()
    with studio.database() as db:
        assert KEY not in '\n'.join(db.iterdump())
    assert not sent
    invalid=configure(client,sendkey='sctp-not-a-turbo-key')
    assert invalid.status_code==422
    stale=configure(client,version=1,sendkey='SCTChanged12345678901234567')
    assert stale.status_code==409
    assert json.loads((path/'serverchan-secret.json').read_text())['sendkey']==KEY


def test_create_and_cancel_are_atomic_idempotent_alerts(setup):
    client,sent,_=setup
    assert configure(client).status_code==200
    key=str(uuid.uuid4())
    response=create(client,key)
    assert response.status_code==201,response.text
    reference=response.json()['id']
    assert create(client,key).json()['id']==reference
    assert len(jobs())==1 and not sent
    assert alerts.process_one(studio.database)
    assert jobs()[0]['state']=='accepted' and len(sent)==1
    assert '待确认' in sent[0][1]
    assert 'private-contact-value' not in sent[0][2] and 'private-customer-note' not in sent[0][2]
    assert client.patch('/studio-api/manage/reservations/'+reference,json={'version':1,'status':'confirmed','staff_note':'private-staff-note'}).status_code==200
    assert len(jobs())==1
    for _ in range(2):
        assert client.post('/studio-api/reservations/'+reference+'/cancel',json={'version':2}).status_code==200
    assert len(jobs())==2
    alerts.process_one(studio.database)
    assert len(sent)==2 and '顾客取消' in sent[-1][1]
    assert 'private-staff-note' not in str(sent)


def test_disabled_events_are_not_backfilled(setup):
    client,sent,_=setup
    create(client)
    assert jobs()[0]['state']=='skipped'
    configure(client)
    assert alerts.process_one(studio.database) is False
    assert not sent
    create(client)
    configure(client,enabled=False,sendkey='')
    assert alerts.process_one(studio.database) is False
    configure(client,sendkey='')
    assert alerts.process_one(studio.database) is True
    assert len(sent)==1


def test_reservation_and_alert_roll_back_together(setup,monkeypatch):
    client,_,_=setup
    configure(client)
    original=alerts.enqueue
    def broken(*args,**kwargs):
        original(*args,**kwargs)
        raise RuntimeError('local rollback test')
    monkeypatch.setattr(alerts,'enqueue',broken)
    assert create(client).status_code==500
    with studio.database() as db:
        assert db.execute('SELECT count(*) FROM studio_reservations').fetchone()[0]==0
    assert not jobs()


def test_worker_releases_transaction_during_network_and_claims_once(setup,monkeypatch):
    client,_,_=setup
    configure(client);create(client)
    entered=threading.Event();release=threading.Event();calls=[]
    def slow(*args):
        calls.append(1);entered.set();assert release.wait(5)
        return {'ok':True}
    monkeypatch.setattr(alerts,'deliver',slow)
    with ThreadPoolExecutor(max_workers=2) as executor:
        result=executor.submit(alerts.process_one,studio.database)
        try:
            assert entered.wait(5)
            assert client.get('/studio-api/manage/owner-notifications').status_code==200
            assert alerts.process_one(studio.database) is False
        finally:
            release.set()
        assert result.result(5)
    assert len(calls)==1 and jobs()[0]['state']=='accepted'


def test_retry_survives_restart_and_expired_claim(setup,monkeypatch):
    client,sent,_=setup
    now=[100000.0]
    monkeypatch.setattr(alerts,'time',SimpleNamespace(time=lambda:now[0]))
    configure(client);create(client)
    successful=alerts.deliver
    monkeypatch.setattr(alerts,'deliver',lambda *args:{'ok':False,'error':'network_error','retry':True})
    alerts.process_one(studio.database)
    assert jobs()[0]['state']=='retry' and jobs()[0]['next_attempt']==100060
    assert alerts.process_one(studio.database) is False
    studio.initialize()
    now[0]+=61
    with studio.database() as db:
        db.execute("UPDATE studio_owner_notifications SET state='sending',lease_until=?,claim_token='interrupted'",(now[0]-1,))
    monkeypatch.setattr(alerts,'deliver',successful)
    alerts.process_one(studio.database)
    assert len(sent)==1 and jobs()[0]['attempts']==2 and jobs()[0]['state']=='accepted'


def test_quota_is_durable_and_bounded(setup,monkeypatch):
    client,sent,_=setup
    now=[100000.0]
    monkeypatch.setattr(alerts,'time',SimpleNamespace(time=lambda:now[0]))
    configure(client,daily_limit=5)
    for _ in range(6):create(client)
    for _ in range(6):alerts.process_one(studio.database)
    assert len(sent)==5
    assert sum(r['state']=='retry' and r['error']=='local_quota' for r in jobs())==1
    studio.initialize()
    assert alerts.process_one(studio.database) is False
    assert client.get('/studio-api/manage/owner-notifications').json()['used']==5
    now[0]+=86402
    alerts.process_one(studio.database)
    assert len(sent)==6 and all(r['state']=='accepted' for r in jobs())
    # A restart or the next worker tick cannot send the recovered sixth alert twice.
    studio.initialize()
    assert alerts.process_one(studio.database) is False
    assert len(sent)==6


def test_skip_stale_new_booking_and_test_does_not_create_reservation(setup):
    client,sent,_=setup
    configure(client)
    reference=create(client).json()['id']
    client.patch('/studio-api/manage/reservations/'+reference,json={'version':1,'status':'confirmed'})
    alerts.process_one(studio.database)
    assert not sent and jobs()[0]['error']=='superseded'
    key=str(uuid.uuid4())
    first=client.post('/studio-api/manage/owner-notifications/test',json={'request_id':key})
    second=client.post('/studio-api/manage/owner-notifications/test',json={'request_id':key})
    assert first.status_code==202 and first.json()['id']==second.json()['id']
    alerts.process_one(studio.database)
    assert len(sent)==1 and '测试' in sent[0][1]
    for _ in range(2):assert client.post('/studio-api/manage/owner-notifications/test',json={'request_id':str(uuid.uuid4())}).status_code==202
    assert client.post('/studio-api/manage/owner-notifications/test',json={'request_id':str(uuid.uuid4())}).status_code==429
    with studio.database() as db:assert db.execute('SELECT count(*) FROM studio_reservations').fetchone()[0]==1


def test_provider_limit_stops_other_jobs_and_failure_is_visible(setup,monkeypatch):
    client,_,_=setup
    configure(client);create(client);create(client)
    monkeypatch.setattr(alerts,'deliver',lambda *args:{'ok':False,'error':'provider_quota','retry':True,'delay':86400})
    alerts.process_one(studio.database)
    assert alerts.process_one(studio.database) is False
    assert jobs()[0]['error']=='provider_quota'
    assert client.get('/studio-api/manage/owner-notifications').json()['blocked_until']>0


def test_manual_retry_cannot_resend_accepted_or_skipped(setup,monkeypatch):
    client,sent,_=setup
    configure(client);create(client)
    successful=alerts.deliver
    monkeypatch.setattr(alerts,'deliver',lambda *args:{'ok':False,'error':'provider_rejected','retry':False})
    alerts.process_one(studio.database)
    ident=jobs()[0]['id']
    assert jobs()[0]['state']=='failed'
    assert client.post('/studio-api/manage/owner-notifications/'+ident+'/retry').status_code==200
    assert client.post('/studio-api/manage/owner-notifications/'+ident+'/retry').status_code==200
    monkeypatch.setattr(alerts,'deliver',successful)
    alerts.process_one(studio.database)
    assert len(sent)==1
    assert client.post('/studio-api/manage/owner-notifications/'+ident+'/retry').status_code==409


@pytest.mark.parametrize('result,expected',[
    ({'code':0,'data':{'errno':0,'pushid':'ok'}},True),
    ({'code':0,'data':{'errno':1}},False),
    ({'code':0,'data':'broken'},False),
    ({'code':400,'message':KEY},False),
    ({'code':429,'message':KEY},False),
    ([],False),
])
def test_adapter_checks_provider_acknowledgement(monkeypatch,result,expected):
    class Response:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,_size):return json.dumps(result).encode()
    class Opener:
        def open(self,request,timeout):
            assert request.full_url.startswith('https://sctapi.ftqq.com/SCT')
            assert timeout==12
            assert b'title=' in request.data and b'desp=' in request.data
            return Response()
    monkeypatch.setattr(alerts,'build_opener',lambda *args:Opener())
    output=alerts.deliver(KEY,'Test','Body')
    assert output['ok'] is expected and KEY not in str(output)


@pytest.mark.parametrize('failure',[
    HTTPError('https://example.invalid/'+KEY,429,KEY,{},None),
    HTTPError('https://example.invalid/'+KEY,503,KEY,{},None),
    URLError(KEY),
])
def test_adapter_failures_do_not_expose_secret(monkeypatch,failure):
    class Opener:
        def open(self,*args,**kwargs):raise failure
    monkeypatch.setattr(alerts,'build_opener',lambda *args:Opener())
    output=alerts.deliver(KEY,'Test','Body')
    assert output['ok'] is False and output['retry'] is True and KEY not in str(output)
