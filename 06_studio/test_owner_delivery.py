import time
from datetime import datetime, timezone
from types import SimpleNamespace

import app as studio
import owner_delivery as delivery
import owner_notifications as alerts
import sms_inbox as sms
from test_owner_notifications import setup, configure, create, host, jobs
from test_sms_inbox import bridge, claim, begin, auth, STUDIO_NUMBER


def enable_phone(client):
    host()
    bridge('owner_alert')
    response = client.put('/studio-api/manage/messages/settings',json={
      'version':1,'owner_enabled':True,'owner_phone':STUDIO_NUMBER})
    assert response.status_code==200
    with studio.database() as db:
        db.execute('UPDATE studio_sms_bridges SET last_seen=?',(time.time(),))


def phone_sent(client, job):
    path='/studio-api/message-bridge/jobs/'+job['id']
    assert client.post(path+'/result',headers=auth('owner_alert'),
      json={'claim_token':job['claim_token'],'state':'submitted'}).status_code==200
    assert client.post(path+'/observation',headers=auth('owner_alert'),json={
      'claim_token':job['claim_token'],'external_id':'qa-guid-'+job['id'],
      'sender':job['sender'],'state':'sent','channel':'SMS'}).status_code==200


def test_transient_owner_failure_survives_attempt_limit_and_restart(setup,monkeypatch):
    client,sent,_=setup
    now=[time.time()]
    monkeypatch.setattr(alerts,'time',SimpleNamespace(time=lambda:now[0]))
    configure(client)
    create(client)
    successful=alerts.deliver
    monkeypatch.setattr(alerts,'deliver',lambda *args:{'ok':False,'error':'network_error','retry':True})
    for _ in range(10):
        assert alerts.process_one(studio.database)
        job=jobs()[0]
        assert job['state']=='retry'
        now[0]=job['next_attempt']+1
    studio.initialize()
    monkeypatch.setattr(alerts,'deliver',successful)
    assert alerts.process_one(studio.database)
    assert jobs()[0]['state']=='accepted' and len(sent)==1


def test_recovery_never_replays_handled_or_accepted_reservations(setup):
    client,sent,_=setup
    configure(client)
    accepted=create(client).json()['id']
    alerts.process_one(studio.database)
    handled=create(client).json()['id']
    with studio.database() as db:
        db.execute("UPDATE studio_owner_notifications SET state='expired',error='expired',expires_at=1 WHERE reservation_id=?",(handled,))
    assert client.patch('/studio-api/manage/reservations/'+handled,json={'version':1,'status':'confirmed'}).status_code==200
    studio.initialize()
    alerts.process_one(studio.database)
    assert len(sent)==1
    assert {r['reservation_id']:r['state'] for r in jobs()}=={accepted:'accepted',handled:'skipped'}


def test_phone_alert_recovers_after_device_offline_for_more_than_a_day(setup):
    client,_,_=setup
    enable_phone(client)
    reference=create(client).json()['id']
    with studio.database() as db:
        db.execute("UPDATE studio_sms_jobs SET state='skipped',error='expired',expires_at=1 WHERE reservation_id=?",(reference,))
    studio.initialize()
    job=claim(client,'owner_alert')
    assert job and job['expires_at']>time.time()+80000
    assert begin(client,job,'owner_alert').json()['send'] is True
    phone_sent(client,job)
    assert claim(client,'owner_alert') is None


def test_phone_unknown_send_is_not_replayed_and_contact_change_is_respected(setup):
    client,_,_=setup
    enable_phone(client)
    first=create(client).json()['id']
    job=claim(client,'owner_alert')
    assert begin(client,job,'owner_alert').json()['send']
    with studio.database() as db:
        db.execute("UPDATE studio_sms_jobs SET state='unknown',error='interrupted',expires_at=1 WHERE reservation_id=?",(first,))
    second=create(client).json()['id']
    with studio.database() as db:
        db.execute("UPDATE studio_sms_jobs SET expires_at=1 WHERE reservation_id=?",(second,))
        db.execute("UPDATE studio_sms_settings SET owner_phone='+14165550999'")
    assert claim(client,'owner_alert') is None
    with studio.database() as db:
        assert db.execute('SELECT state FROM studio_sms_jobs WHERE reservation_id=?',(first,)).fetchone()[0]=='unknown'
        assert db.execute('SELECT state FROM studio_sms_jobs WHERE reservation_id=?',(second,)).fetchone()[0]=='skipped'


def test_phone_reservation_confirmed_after_claim_does_not_send(setup):
    client,_,_=setup
    enable_phone(client)
    reference=create(client).json()['id']
    with studio.database() as db:
        db.execute('UPDATE studio_sms_jobs SET expires_at=1 WHERE reservation_id=?',(reference,))
    job=claim(client,'owner_alert')
    assert job
    assert client.patch('/studio-api/manage/reservations/'+reference,json={'version':1,'status':'confirmed'}).status_code==200
    assert begin(client,job,'owner_alert').json()=={'send':False,'state':'skipped'}


def test_health_exposes_exhausted_wechat_but_phone_continues_without_grants(setup):
    client,sent,_=setup
    enable_phone(client)
    configure(client,daily_limit=5)
    for _ in range(6):create(client)
    for _ in range(6):alerts.process_one(studio.database)
    assert len(sent)==5
    for _ in range(6):
        job=claim(client,'owner_alert')
        assert job and begin(client,job,'owner_alert').json()['send']
        phone_sent(client,job)
    health=client.get('/studio-api/manage/owner-delivery')
    assert health.status_code==200
    data=health.json()
    assert data['continuous_ready'] and data['level']=='warning'
    assert data['channels']['serverchan']['limited']
    assert data['channels']['sms']['ready']
    assert not data['channels']['wechat']['authorized']
    assert data['pending_count']==6 and data['unacknowledged_count']==0
    assert STUDIO_NUMBER not in health.text and 'SCT123' not in health.text


def test_health_reports_unacknowledged_reservations_and_is_read_only(setup):
    client,_,_=setup
    assert client.get('/studio-api/manage/owner-delivery').status_code==401
    host()
    reference=create(client).json()['id']
    with studio.database() as db:
        db.execute('UPDATE studio_reservations SET created_at=? WHERE id=?',
          (datetime.fromtimestamp(time.time()-600,timezone.utc).isoformat(),reference))
        before=list(db.execute('SELECT * FROM studio_reservations'))
        total_before=db.total_changes
        data=delivery.snapshot(db)
        assert db.total_changes==total_before
        assert list(db.execute('SELECT * FROM studio_reservations'))==before
    assert not data['continuous_ready'] and data['level']=='critical'
    assert data['unacknowledged_ids']==[reference]
