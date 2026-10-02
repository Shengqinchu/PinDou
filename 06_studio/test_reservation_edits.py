"""Disposable DB workflows; no production bookings or external message delivery."""
import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import pytest
import app as studio
import reservations as visits
from test_reservations import client, body, submit, admin


def change(client, row, **fields):
    booking = {k: row['booking'][k] for k in ('date', 'start', 'end', 'guests')}
    booking.update(fields)
    return {'booking': booking, 'version': row['version'], 'request_key': str(uuid.uuid4())}


def edit(client, row, payload=None, **fields):
    return client.post('/studio-api/reservations/'+row['id']+'/reschedule', json=payload or change(client,row,**fields))


@pytest.mark.parametrize('state', ['pending','confirmed','cancelled'])
def test_customer_change_resets_state_and_keeps_origin(client,state):
    row=submit(client).json();admin()
    if state!='pending':
        response=client.patch('/studio-api/manage/reservations/'+row['id'],json={'status':state,'version':row['version']})
        assert response.status_code==200,response.text
    row=client.get('/studio-api/reservations/'+row['id']).json()
    result=edit(client,row,date='2026-09-10',start='11:00',end='13:00',guests=3)
    assert result.status_code==200,result.text
    value=result.json()['reservation']
    assert value['status']=='pending' and value['booking']['guests']==3 and value['creation_source']==row['creation_source']
    assert value['version']==row['version']+1
    with studio.database() as db:
        alerts=db.execute("SELECT kind,payload FROM studio_owner_notifications WHERE reservation_id=? AND kind='changed'",(row['id'],)).fetchall()
        assert len(alerts)==1 and json.loads(alerts[0]['payload'])['previous_booking']==row['booking']
        assert db.execute("SELECT count(*) FROM reservation_events WHERE reservation_id=? AND status='schedule_changed'",(row['id'],)).fetchone()[0]==1


def test_completed_rebooking_preserves_finance_and_reward(client,monkeypatch):
    row=submit(client).json();admin()
    assert client.patch('/studio-api/manage/reservations/'+row['id'],json={'status':'confirmed','version':1}).status_code==200
    monkeypatch.setattr(visits,'now_local',lambda:datetime(2026,9,9,9,tzinfo=visits.ZONE))
    assert client.patch('/studio-api/manage/reservations/'+row['id'],json={'status':'completed','version':2,'actual_minutes':120,'actual_guests':2}).status_code==200
    with studio.database() as db:
        ledger=[tuple(r) for r in db.execute('SELECT * FROM studio_wallet_ledger')]
        finance=[tuple(r) for r in db.execute('SELECT * FROM studio_finance_entries')]
    row=client.get('/studio-api/reservations/'+row['id']).json()
    response=edit(client,row,date='2026-09-10',start='11:00',end='13:00')
    assert response.status_code==200,response.text
    after=response.json()['reservation']
    assert after['status']=='pending' and after['actual_minutes'] is None and after['actual_guests'] is None
    assert after['previous_visit']['actual_minutes']==120 and after['previous_visit']['booking']==row['booking']
    assert after['can_cancel']
    assert client.patch('/studio-api/manage/reservations/'+row['id'],json={'status':'confirmed','version':after['version']}).status_code==200
    monkeypatch.setattr(visits,'now_local',lambda:datetime(2026,9,11,9,tzinfo=visits.ZONE))
    assert client.patch('/studio-api/manage/reservations/'+row['id'],json={'status':'completed','version':after['version']+1,'actual_minutes':180,'actual_guests':3}).status_code==200
    with studio.database() as db:
        assert [tuple(r) for r in db.execute('SELECT * FROM studio_wallet_ledger')]==ledger
        assert [tuple(r) for r in db.execute('SELECT * FROM studio_finance_entries')]==finance


def test_retry_does_not_duplicate_changes_or_alerts(client):
    row=submit(client).json();payload=change(client,row,start='15:00',end='17:00')
    first=edit(client,row,payload);second=edit(client,row,payload)
    assert first.status_code==second.status_code==200
    assert first.json()['reservation']==second.json()['reservation']
    assert second.json()['replayed']
    payload['booking']['guests']=4
    assert edit(client,row,payload).json()['detail']=='reservation_edit_request_changed'
    with studio.database() as db:
        assert db.execute("SELECT count(*) FROM studio_owner_notifications WHERE kind='changed'").fetchone()[0]==1


def test_owner_version_and_plan_are_protected(client):
    row=submit(client).json();payload=change(client,row,start='15:00',end='17:00')
    assert client.get('/studio-api/reservations/'+row['id']+'/edit-calendar',headers={'Authorization':'Bearer qa-other'}).status_code==404
    assert client.post('/studio-api/reservations/'+row['id']+'/reschedule',json=payload,headers={'Authorization':'Bearer qa-other'}).status_code==404
    forged=change(client,row);forged['booking']['plan']='patch'
    assert edit(client,row,forged).status_code==422
    assert edit(client,row,payload).status_code==200
    assert edit(client,row,change(client,row,guests=3)).json()['detail']=='version_conflict'


def test_patch_self_exclusion_and_conflicting_booking_are_atomic(client):
    row=submit(client,body('2026-09-08','11:00','12:00','patch')).json()
    private=client.get('/studio-api/reservations/'+row['id']+'/edit-calendar',params={'guests':2}).json()
    day=next(d for d in private['days'] if d['date']==row['booking']['date'])
    assert next(s for s in day['slots'] if s['start']=='11:00')['available']
    other=submit(client,body('2026-09-08','13:00','14:00','patch')).json()
    assert edit(client,row,start='13:00',end='14:00').json()['detail']=='reservation_confirmation_conflict'
    assert edit(client,row,start='12:00',end='14:00').json()['detail']=='reservation_patch_duration'
    assert client.get('/studio-api/reservations/'+row['id']).json()['booking']==row['booking']
    assert edit(client,row,start='12:00',end='13:00',guests=3).status_code==200
    public=client.get('/studio-api/reservation-calendar?experience=patch').json()
    day=next(d for d in public['days'] if d['date']==row['booking']['date'])
    assert next(s for s in day['slots'] if s['start']=='11:00')['available']
    assert not next(s for s in day['slots'] if s['start']=='12:00')['available']
    assert other['id']!=row['id']


@pytest.mark.parametrize('state',['pending','confirmed','cancelled'])
def test_admin_schedule_keeps_status_and_retry_is_idempotent(client,state):
    row=submit(client).json();admin()
    if state!='pending':
        assert client.patch('/studio-api/manage/reservations/'+row['id'],json={'status':state,'version':row['version']}).status_code==200
    row=client.get('/studio-api/reservations/'+row['id']).json()
    payload={'status':state,'version':row['version'],'request_key':str(uuid.uuid4()),'booking':row['booking']|{'start':'15:00','end':'17:00','guests':3}}
    for _ in range(2):
        result=client.patch('/studio-api/manage/reservations/'+row['id'],json=payload)
        assert result.status_code==200,result.text
        assert result.json()['status']==state and result.json()['version']==row['version']+1


def test_noop_confirmation_and_existing_customer_jobs(client):
    row=submit(client).json();admin()
    assert client.patch('/studio-api/manage/reservations/'+row['id'],json={'status':'confirmed','version':1}).status_code==200
    row=client.get('/studio-api/reservations/'+row['id']).json()
    result=edit(client,row)
    assert result.status_code==200 and result.json()['unchanged'] and result.json()['reservation']['status']=='confirmed'
    assert result.json()['reservation']['version']==row['version']
    assert edit(client,row,start='15:00',end='17:00').status_code==200
    with studio.database() as db:
        assert not db.execute("SELECT 1 FROM studio_customer_notification_jobs WHERE reservation_id=? AND kind IN ('confirmed','reminder') AND state IN ('queued','retry')",(row['id'],)).fetchone()


@pytest.mark.parametrize('changes',[{'date':'2026-09-21'},{'date':'2026-09-06'},{'guests':99},{'start':'14:15'},{'start':'15:00','end':'16:00'}])
def test_new_customer_schedule_obeys_current_policy(client,changes):
    row=submit(client).json()
    assert edit(client,row,**changes).status_code==422
    assert client.get('/studio-api/reservations/'+row['id']).json()['version']==row['version']


def test_two_patch_moves_cannot_claim_the_same_slot(client):
    first=submit(client,body('2026-09-08','11:00','12:00','patch')).json()
    second=submit(client,body('2026-09-08','13:00','14:00','patch')).json()
    with ThreadPoolExecutor(max_workers=2) as pool:
        answers=list(pool.map(lambda row:edit(client,row,start='15:00',end='16:00'),(first,second)))
    assert sorted(r.status_code for r in answers)==[200,409]
    with studio.database() as db:
        assert db.execute("SELECT count(*) FROM studio_reservations WHERE json_extract(payload,'$.booking.start')='15:00' AND status='pending'").fetchone()[0]==1


def test_unused_gifts_resize_but_fulfilled_claims_and_assets_stay(client,monkeypatch):
    row=submit(client,body('2026-09-08','11:00','12:00','patch')).json()
    assert client.get('/studio-api/patch-promotion').json()['remaining']==8
    result=edit(client,row,start='12:00',end='13:00',guests=3)
    assert result.status_code==200,result.text
    assert client.get('/studio-api/patch-promotion').json()['remaining']==7
    admin();version=result.json()['reservation']['version']
    assert client.patch('/studio-api/manage/reservations/'+row['id'],json={'status':'confirmed','version':version}).status_code==200
    monkeypatch.setattr(visits,'now_local',lambda:datetime(2026,9,9,9,tzinfo=visits.ZONE))
    assert client.patch('/studio-api/manage/reservations/'+row['id'],json={'status':'completed','version':version+1,'actual_minutes':60,'actual_guests':3}).status_code==200
    with studio.database() as db:
        gift=tuple(db.execute('SELECT * FROM patch_promotion_claims WHERE reservation_id=?',(row['id'],)).fetchone())
        ledger=[tuple(r) for r in db.execute('SELECT * FROM studio_wallet_ledger')]
    row=client.get('/studio-api/reservations/'+row['id']).json()
    assert edit(client,row,date='2026-09-10',start='11:00',end='12:00',guests=4).status_code==200
    with studio.database() as db:
        assert tuple(db.execute('SELECT * FROM patch_promotion_claims WHERE reservation_id=?',(row['id'],)).fetchone())==gift
        assert [tuple(r) for r in db.execute('SELECT * FROM studio_wallet_ledger')]==ledger


def test_admin_can_correct_completed_history_without_rewriting_settlement(client,monkeypatch):
    row=submit(client).json();admin()
    assert client.patch('/studio-api/manage/reservations/'+row['id'],json={'status':'confirmed','version':1}).status_code==200
    monkeypatch.setattr(visits,'now_local',lambda:datetime(2026,9,9,9,tzinfo=visits.ZONE))
    assert client.patch('/studio-api/manage/reservations/'+row['id'],json={'status':'completed','version':2,'actual_minutes':120,'actual_guests':2}).status_code==200
    with studio.database() as db:
        ledger=[tuple(r) for r in db.execute('SELECT * FROM studio_wallet_ledger')]
        finance=[tuple(r) for r in db.execute('SELECT * FROM studio_finance_entries')]
    row=client.get('/studio-api/reservations/'+row['id']).json()
    result=client.patch('/studio-api/manage/reservations/'+row['id'],json={'status':'completed','version':row['version'],
        'booking':row['booking']|{'date':'2026-08-01','start':'09:00','end':'10:00','guests':5},'request_key':str(uuid.uuid4())})
    assert result.status_code==200,result.text
    after=client.get('/studio-api/reservations/'+row['id']).json()
    assert after['status']=='completed' and after['actual_minutes']==120
    with studio.database() as db:
        assert [tuple(r) for r in db.execute('SELECT * FROM studio_wallet_ledger')]==ledger
        assert [tuple(r) for r in db.execute('SELECT * FROM studio_finance_entries')]==finance


def test_owner_transport_renders_current_and_previous_schedule(client,monkeypatch):
    import owner_notifications as alerts
    sent=[]
    monkeypatch.setattr(alerts,'deliver',lambda key,title,body:(sent.append(body) or {'ok':True,'provider_id':'local-only'}))
    admin();current=client.get('/studio-api/manage/owner-notifications').json()
    assert client.put('/studio-api/manage/owner-notifications',json={'version':current['version'],'enabled':True,'daily_limit':1000,
        'language':'en','sendkey':'SCT12345678901234567890LocalEditOnly'}).status_code==200
    row=submit(client).json()
    response=edit(client,row,start='15:00',end='17:00')
    assert response.status_code==200,response.text
    with studio.database() as db:
        old=db.execute("SELECT * FROM studio_owner_notifications WHERE kind='created'").fetchone()
        job=db.execute("SELECT * FROM studio_owner_notifications WHERE kind='changed'").fetchone()
        assert old['state']=='skipped' and old['error']=='superseded'
        assert not alerts.obsolete(db,dict(job))
        title,text=alerts.render_message(dict(job),'en')
        assert 'Booking change' in title and '15:00' in text and '14:00' in text
    assert alerts.process_one(studio.database)
    assert len(sent)==1 and 'Previous:' in sent[0]


def test_owner_phone_change_is_a_new_dispatchable_alert(client):
    from test_sms_inbox import bridge,claim,begin
    bridge('owner_alert')
    with studio.database() as db:
        db.execute("UPDATE studio_sms_settings SET owner_enabled=1,owner_phone='+14165550123',language='en' WHERE id=1")
    row=submit(client).json()
    response=edit(client,row,start='15:00',end='17:00',guests=3)
    assert response.status_code==200,response.text
    job=claim(client,'owner_alert')
    assert job and 'Booking change' in job['content'] and '15:00' in job['content'] and '14:00' in job['content']
    result=begin(client,job,'owner_alert')
    assert result.status_code==200 and result.json()['send']
    with studio.database() as db:
        assert db.execute("SELECT state FROM studio_sms_jobs WHERE notification_key=?",('created:'+row['id'],)).fetchone()[0]=='skipped'
        assert db.execute("SELECT count(*) FROM studio_sms_jobs WHERE notification_key LIKE ?",('changed:'+row['id']+':%',)).fetchone()[0]==1


def test_owner_native_change_has_a_distinct_subscription_job(client,monkeypatch):
    from types import SimpleNamespace
    import owner_wechat,miniapp_login
    monkeypatch.setattr(miniapp_login,'config',lambda:SimpleNamespace(app_id='wx-local-edit',environment='trial'))
    monkeypatch.setattr(miniapp_login,'available',lambda:False)
    with studio.database() as db:
        db.execute("UPDATE studio_owner_wechat_settings SET enabled=1,template_id='local-template' WHERE id=1")
        db.execute("INSERT INTO studio_owner_wechat_bindings(id,app_id,openid,label,created_at,actor,grants) VALUES('local-binding','wx-local-edit','local-openid','Local test',0,'test',1)")
    row=submit(client).json()
    assert edit(client,row,start='15:00',end='17:00').status_code==200
    with studio.database() as db:
        jobs=db.execute('SELECT * FROM studio_owner_wechat_jobs ORDER BY created_at').fetchall()
        assert len(jobs)==2 and jobs[0]['state']=='skipped' and jobs[1]['state']=='queued'
        assert jobs[1]['event_key'].startswith('changed:'+row['id']+':')
        binding=db.execute("SELECT * FROM studio_owner_wechat_bindings WHERE id='local-binding'").fetchone()
        card=owner_wechat.message_payload(jobs[1],binding)
        assert card['data']['time2']['value'].endswith('15:00') and '修改' in card['data']['thing5']['value']
