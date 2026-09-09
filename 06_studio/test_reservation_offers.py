import hashlib
import json
import uuid
from datetime import datetime
import pytest
from test_reservations import client, body, submit, admin
import app as studio
import reservations

def offer_body(client, **changes):
    offer = client.get('/studio-api/reservation-calendar?guests=2').json()['offers'][0]
    payload = body(end='18:00')
    payload.pop('consent')
    payload.update(offer=offer['id'], offer_revision=offer['revision'])
    payload['booking'].update(changes)
    return payload

def test_offer_saved_for_customer_and_host_without_payment(client):
    payload = offer_body(client)
    key = str(uuid.uuid4())
    first = submit(client, payload, key)
    assert first.status_code == 201
    record = first.json()
    assert record['booked_minutes'] == 240 and record['booking']['guests'] == 2
    assert record['offer']['id'] == 'duo4h' and record['offer']['amount'] == '59.9'
    assert submit(client, payload, key).json()['id'] == record['id']
    assert client.get('/studio-api/auth/reservations').json()['items'][0]['offer'] == record['offer']
    admin()
    entry = client.get('/studio-api/manage/reservations').json()['items'][0]
    assert entry['offer'] == record['offer']
    assert client.patch('/studio-api/manage/reservations/'+record['id'],json={'status':'confirmed','version':1}).status_code == 200
    with studio.database() as db:
        assert db.execute('SELECT count(*) FROM commerce_orders').fetchone()[0] == 0

@pytest.mark.parametrize('changes',[{'guests':1},{'guests':3},{'end':'16:00'},{'end':'18:30'},{'plan':'day','end':'22:00'}])
def test_offer_rejects_wrong_people_or_duration(client, changes):
    assert submit(client, offer_body(client,**changes)).status_code == 422

def test_offer_uses_published_price_and_requires_current_revision(client):
    payload = offer_body(client)
    with studio.database() as db:
        db.execute("UPDATE studio_content SET published=? WHERE name='rate-fields'",(json.dumps({'school_two_four_hours':['65','65']}),))
    assert submit(client, payload).status_code == 409
    current = offer_body(client)
    result = submit(client, current)
    assert result.status_code == 201 and result.json()['offer']['amount'] == '65'
    with studio.database() as db:
        db.execute("UPDATE studio_content SET published=? WHERE name='rate-fields'",(json.dumps({'school_two_four_hours':['70','70']}),))
    assert client.get('/studio-api/reservations/'+result.json()['id']).json()['offer']['amount'] == '65'

def test_offer_expiry_and_replay_after_price_change(client, monkeypatch):
    monkeypatch.setattr(reservations,'now_local',lambda:datetime(2026,9,30,9,tzinfo=reservations.ZONE))
    payload = offer_body(client,date='2026-10-01',start='10:00',end='14:00')
    key = str(uuid.uuid4())
    result = submit(client,payload,key)
    assert result.status_code == 201
    payload2 = offer_body(client,date='2026-10-02',start='10:00',end='14:00')
    assert submit(client,payload2).status_code == 422
    monkeypatch.setattr(reservations,'now_local',lambda:datetime(2026,10,2,9,tzinfo=reservations.ZONE))
    assert client.get('/studio-api/reservation-calendar').json()['offers'] == []
    assert submit(client,payload,key).json()['id'] == result.json()['id']

def test_offer_does_not_bypass_capacity_or_closed_hours(client):
    payload = offer_body(client)
    admin()
    assert client.put('/studio-api/manage/reservation-policy',json={'max_concurrent_groups':1,'version':1}).status_code == 200
    first = submit(client,payload).json()
    assert client.patch('/studio-api/manage/reservations/'+first['id'],json={'status':'confirmed','version':1}).status_code == 200
    assert submit(client,payload).status_code == 409
    assert submit(client,offer_body(client,date='2026-09-09',start='14:00',end='18:00')).status_code == 422

def test_pre_offer_client_request_keeps_its_canonical_hash(client):
    # Exact JSON contract emitted by the previously deployed Submission model.
    legacy='{"booking":{"date":"2026-09-08","start":"14:00","end":"16:00","plan":"hourly","guests":2},"name":"Reservation QA","contact_method":"wechat","contact":"test-local","notes":"","consent":true,"locale":"zh","website":""}'
    key=str(uuid.uuid4())
    result=submit(client,key=key)
    assert result.status_code == 201
    with studio.database() as db:
        row=db.execute('SELECT payload_hash FROM studio_reservations WHERE id=?',(result.json()['id'],)).fetchone()
        assert row[0] == hashlib.sha256(legacy.encode()).hexdigest()
    assert submit(client,key=key).json()['id'] == result.json()['id']
