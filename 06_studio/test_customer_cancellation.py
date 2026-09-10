from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import json
import pytest
from test_reservations import client,submit,body,admin
import app as studio
import reservations as visits

def cancel(client,item):
    return client.post('/studio-api/reservations/'+item['id']+'/cancel',json={'version':item['version']})

def policy(client,item):
    return client.get('/studio-api/reservations/'+item['id']+'/cancellation')

@pytest.mark.parametrize('confirmed',[False,True])
def test_customer_cancels_once_and_releases_capacity(client,confirmed):
    item=submit(client).json();admin()
    if confirmed:
        client.put('/studio-api/manage/reservation-policy',json={'version':1,'exclusive_groups':True})
        assert client.patch('/studio-api/manage/reservations/'+item['id'],json={'version':1,'status':'confirmed'}).status_code==200
        item=client.get('/studio-api/reservations/'+item['id']).json()
        assert submit(client).status_code==409
    assert item['can_cancel']
    assert policy(client,item).json()['remaining']==3
    response=cancel(client,item);assert response.status_code==200,response.text
    assert response.json()['reservation']['status']=='cancelled'
    assert response.json()['reservation']['can_cancel'] is False
    assert response.json()['policy']['used']==1
    assert cancel(client,item).json()['policy']['used']==1
    assert submit(client).status_code==201
    with studio.database() as db:
        assert db.execute('SELECT count(*) FROM reservation_customer_cancellations').fetchone()[0]==1
        event=db.execute("SELECT actor FROM reservation_events WHERE reservation_id=? AND status='cancelled'",(item['id'],)).fetchone()
        assert event[0]=='customer:qa-owner'

def test_three_per_account_and_admin_cancellations_do_not_count(client):
    items=[submit(client).json() for _ in range(5)];admin()
    client.patch('/studio-api/manage/reservations/'+items[0]['id'],json={'version':1,'status':'cancelled'})
    for index,item in enumerate(items[1:4]):
        assert cancel(client,item).json()['policy']['used']==index+1
    response=cancel(client,items[4]);assert response.status_code==409
    assert response.json()['detail']=='reservation_cancellation_limit'
    assert policy(client,items[4]).json()['remaining']==0
    assert client.patch('/studio-api/manage/reservations/'+items[4]['id'],json={'version':1,'status':'cancelled'}).status_code==200
    with studio.database() as db:assert db.execute('SELECT count(*) FROM reservation_customer_cancellations').fetchone()[0]==3
    client.headers['Authorization']='Bearer qa-other'
    other=submit(client).json();assert cancel(client,other).json()['policy']['used']==1

def test_owner_version_and_payload_are_enforced(client):
    item=submit(client).json();client.headers['Authorization']='Bearer qa-other'
    assert cancel(client,item).status_code==404
    assert policy(client,item).status_code==404
    del client.headers['Authorization'];assert cancel(client,item).status_code==401
    client.headers['Authorization']='Bearer qa-owner';admin()
    client.patch('/studio-api/manage/reservations/'+item['id'],json={'version':1,'status':'confirmed'})
    assert cancel(client,item).json()['detail']=='version_conflict'
    assert client.post('/studio-api/reservations/'+item['id']+'/cancel',json={'version':2,'owner_id':'qa-other'}).status_code==422
    assert client.post('/studio-api/reservations/'+item['id']+'/cancel',json={'version':True}).status_code==422
    with studio.database() as db:assert db.execute('SELECT count(*) FROM reservation_customer_cancellations').fetchone()[0]==0

@pytest.mark.parametrize('state',['completed','cancelled','started','recorded','deleted'])
def test_unavailable_reservations_cannot_be_cancelled(client,monkeypatch,state):
    item=submit(client).json()
    with studio.database() as db:
        if state in ('completed','cancelled'):db.execute('UPDATE studio_reservations SET status=?',(state,))
        if state=='recorded':db.execute('UPDATE studio_reservations SET actual_minutes=120,actual_guests=2')
        if state=='deleted':db.execute("UPDATE studio_reservations SET deleted_at='2026-09-07'")
    if state=='started':monkeypatch.setattr(visits,'now_local',lambda:datetime(2026,9,8,14,tzinfo=visits.ZONE))
    assert cancel(client,item).status_code==(404 if state=='deleted' else 409)
    with studio.database() as db:assert db.execute('SELECT count(*) FROM reservation_customer_cancellations').fetchone()[0]==0

def test_toronto_calendar_month_not_utc_or_booking_month(client,monkeypatch):
    monkeypatch.setattr(visits,'now_local',lambda:datetime(2026,9,30,23,0,tzinfo=visits.ZONE))
    items=[submit(client,body('2026-10-02')).json() for _ in range(4)]
    # UTC October 1 is still September 30 in Hamilton.
    monkeypatch.setattr(visits,'now_local',lambda:datetime(2026,10,1,3,30,tzinfo=timezone.utc))
    for item in items[:3]:assert cancel(client,item).json()['policy']['month']=='2026-09'
    assert cancel(client,items[3]).status_code==409
    monkeypatch.setattr(visits,'now_local',lambda:datetime(2026,10,1,4,0,tzinfo=timezone.utc))
    assert policy(client,items[3]).json()['remaining']==3
    assert cancel(client,items[3]).json()['policy']['used']==1
    assert cancel(client,items[0]).json()['policy']['used']==1

def test_parallel_cancellations_cannot_exceed_allowance(client):
    items=[submit(client).json() for _ in range(4)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        codes=sorted(pool.map(lambda item:cancel(client,item).status_code,items))
    assert codes==[200,200,200,409]
    with studio.database() as db:assert db.execute('SELECT count(*) FROM reservation_customer_cancellations').fetchone()[0]==3

def test_reactivation_and_deletion_do_not_erase_cancellation_history(client):
    item=submit(client).json();assert cancel(client,item).status_code==200;admin()
    assert client.patch('/studio-api/manage/reservations/'+item['id'],json={'version':2,'status':'pending'}).status_code==200
    assert cancel(client,item).status_code==409
    item=client.get('/studio-api/reservations/'+item['id']).json()
    assert cancel(client,item).json()['policy']['used']==2
    assert client.request('DELETE','/studio-api/manage/reservations/'+item['id'],json={'version':4,'reason':'test'}).status_code==200
    another=submit(client).json();assert policy(client,another).json()['used']==2

def test_timetable_has_one_group_with_private_notes_only_for_admin(client):
    data=body();data['name']='Guest';data['notes']='Booking note'
    item=submit(client,data).json();admin()
    with studio.database() as db:
        db.execute("UPDATE studio_members SET staff_note='Member note' WHERE owner_id='qa-owner'")
        db.execute("UPDATE studio_reservations SET staff_note='Host note' WHERE id=?",(item['id'],))
    result=client.get('/studio-api/manage/reservation-timetable?start=2026-09-07').json()
    blocks=result['days'][1]['bookings'];assert len(blocks)==1
    assert blocks[0]['id']==item['id'] and blocks[0]['guests']==2
    assert blocks[0]['note']=='Member note\nHost note\nBooking note'
    assert 'contact' not in blocks[0]
    receipt=client.get('/studio-api/reservations/'+item['id']).text
    assert 'Member note' not in receipt and 'Host note' not in receipt
    assert cancel(client,item).status_code==200
    assert client.get('/studio-api/manage/reservation-timetable?start=2026-09-07').json()['days'][1]['bookings']==[]
