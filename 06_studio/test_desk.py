"""Host desk reads must reflect all orders and retain server authorization."""
import json
import time
import uuid
from datetime import datetime, timedelta

import pytest

import app as studio
import commerce as shop
from test_commerce import client, items, payload, place, notify, publish_product


def test_overview_counts_entire_database_not_first_page(client):
    body = payload(client)
    oid = place(client, body).json()['id']
    assert notify(client, oid).text == 'success'
    with studio.database() as db:
        row = dict(db.execute('SELECT * FROM commerce_orders WHERE id=?', (oid,)).fetchone())
        for n in range(40):
            clone = {**row, 'id': 'PSDESKTEST' + str(n), 'idempotency_key': str(uuid.uuid4()), 'trade_id': 'DESKTRADE' + str(n)}
            columns = ','.join(clone)
            db.execute(f'INSERT INTO commerce_orders({columns}) VALUES({",".join("?" for _ in clone)})', tuple(clone.values()))
    listing = client.get('/studio-api/manage/orders').json()
    assert len(listing['items']) == 30 and listing['total'] == 41
    overview = client.get('/studio-api/manage/overview').json()
    assert overview['metrics']['orders_today'] == 41
    assert overview['metrics']['received_cny_fen'] == 41 * 8000
    assert len(overview['recent_orders']) == 5


def test_order_filters_search_customer_booking_date_kind_and_state(client):
    a = payload(client); a['name'] = 'Sunshine guest'
    visit_id = place(client, a).json()['id']
    assert notify(client, visit_id).text == 'success'
    publish_product(client)
    b = payload(client, [{'product_id':'starter','quantity':1}]); b['name'] = 'Pickup guest'
    pickup_id = place(client, b).json()['id']
    assert client.get('/studio-api/manage/orders?search=Sunshine').json()['items'][0]['id'] == visit_id
    assert client.get('/studio-api/manage/orders?kind=pickup').json()['items'][0]['id'] == pickup_id
    assert client.get('/studio-api/manage/orders?status=paid').json()['total'] == 1
    assert client.get('/studio-api/manage/orders', params={'day':items()[0]['booking']['date']}).json()['total'] == 1
    assert client.get('/studio-api/manage/orders?search=unmatched').json()['total'] == 0
    assert client.get('/studio-api/manage/orders?status=paid%27%20OR%201=1').status_code == 422


def test_calendar_excludes_expired_holds_and_preserves_confirmed_seats(client):
    oid = place(client).json()['id']
    selected = items()[0]['booking']['date']
    data = client.get('/studio-api/manage/overview', params={'day':selected}).json()
    assert len(data['days']) == 7
    assert data['days'][0]['entries'][0]['status'] == 'pending'
    assert data['metrics']['guests_today'] == 0
    with studio.database() as db:
        db.execute('UPDATE commerce_orders SET hold_until=? WHERE id=?', (time.time()-1,oid))
    assert client.get('/studio-api/manage/overview',params={'day':selected}).json()['days'][0]['entries'] == []
    assert notify(client,oid).text == 'success'
    data = client.get('/studio-api/manage/overview',params={'day':selected}).json()
    assert data['metrics']['guests_today'] == 1
    assert data['days'][0]['entries'][0]['status'] == 'paid'


def test_audit_has_settings_and_product_snapshots_and_order_detail(client):
    settings = client.get('/studio-api/manage/commerce').json()['settings']
    settings['capacity'] = 4
    assert client.put('/studio-api/manage/schedule',json=settings).status_code == 200
    publish_product(client)
    events = client.get('/studio-api/manage/activity').json()['items']
    event = next(r for r in events if r['event'] == 'schedule_and_prices_updated')
    changes = json.loads(event['detail'])
    assert changes['before']['capacity'] == 2 and changes['after']['capacity'] == 4
    product = next(r for r in events if r['event'] == 'product_updated')
    assert json.loads(product['detail'])['after']['price_cents'] == 1234
    oid = place(client).json()['id']
    detail = client.get('/studio-api/manage/orders/' + oid).json()
    assert detail['customer']['name'] == 'Commerce QA'
    assert any(event['event'] == 'created_and_held' for event in detail['events'])
    assert 'access_hash' not in detail


def test_overview_uses_toronto_day_boundaries_including_dst(client):
    oid = place(client).json()['id']
    assert notify(client,oid).text == 'success'
    start = datetime(2026,11,1,tzinfo=shop.TORONTO)
    finish = start + timedelta(days=1)
    assert finish.timestamp() - start.timestamp() == 25 * 3600
    with studio.database() as db:
        db.execute('UPDATE commerce_orders SET created_at=?,paid_at=? WHERE id=?',(finish.timestamp()-1,finish.timestamp()-1,oid))
    data = client.get('/studio-api/manage/overview?day=2026-11-01').json()
    assert data['metrics']['orders_today'] == 1
    assert data['metrics']['received_cny_fen'] == 8000
    assert client.get('/studio-api/manage/overview?day=2026-11-02').json()['metrics']['received_cny_fen'] == 0


def test_every_new_desk_read_requires_admin(client):
    oid = place(client).json()['id']
    studio.app.dependency_overrides.clear()
    for path in ['/manage/overview','/manage/activity','/manage/orders/'+oid,'/manage/orders?search=test']:
        assert client.get('/studio-api'+path).status_code == 401
