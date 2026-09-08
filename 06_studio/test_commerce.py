"""Payment and inventory contracts; all gateway calls are isolated test doubles."""
import copy
import json
import secrets
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from urllib.parse import urlencode

import pytest
from fastapi.testclient import TestClient

import app as studio
import commerce as shop
from payments import PaymentUnavailable, sign, verify


class FakeGateway:
    app_id = "test-merchant"
    secret = "unit-test-only"
    configured = True

    def __init__(self):
        self.orders = {}
        self.creates = 0
        self.timeout = False

    def create(self, order_id, cny_fen):
        self.creates += 1
        self.orders[order_id] = {"status": "WP", "out_trade_order": order_id, "open_order_id": "GW" + order_id, "transaction_id": "TX" + order_id, "total_amount": f"{cny_fen / 100:.2f}"}
        if self.timeout:
            raise PaymentUnavailable("timeout after the provider created an order")
        return {"payment_url": "https://api.xunhupay.com/test-cashier", "qr_url": "https://api.xunhupay.com/test-qr", "provider_id": "GW" + order_id}

    def query(self, order_id):
        return self.orders[order_id]

    def verify_callback(self, params):
        return params.get("appid") == self.app_id and verify(params, self.secret)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(studio, "DB_PATH", tmp_path / "shop.sqlite3")
    monkeypatch.setattr(shop, "PUBLIC_SALES_ENABLED", True)
    fake = FakeGateway()
    monkeypatch.setattr(shop, "gateway", fake)
    studio.app.dependency_overrides[studio.admin_actor] = lambda: "test-owner"
    with TestClient(studio.app) as client:
        settings = client.get('/studio-api/manage/commerce').json()['settings']
        settings.update(enabled=True, capacity=2, tax_mode='included')
        for row in settings['weekly']:
            row['enabled'] = True
        assert client.put('/studio-api/manage/schedule', json=settings).status_code == 200
        client.gateway = fake
        yield client
    studio.app.dependency_overrides.clear()


def items(plan='hourly', guests=1):
    day = str((shop.now_local() + timedelta(days=1)).date())
    return [{'product_id': plan, 'quantity': 1, 'booking': {'date': day, 'start': '14:00', 'end': '16:00' if plan == 'hourly' else '22:00', 'guests': guests}}]


def payload(client, selection=None):
    selected = selection or items()
    quote = client.post('/studio-api/cart/quote', json={'items': selected})
    assert quote.status_code == 200, quote.text
    return {'items': selected, 'name': 'Commerce QA', 'contact_method': 'wechat', 'contact': 'local-test-only', 'consent': True, 'quote_id': quote.json()['quote_id'], 'access_key': secrets.token_hex(32)}


def place(client, body=None, key=None):
    return client.post('/studio-api/orders', json=body or payload(client), headers={'Idempotency-Key': key or str(uuid.uuid4())})


def notify(client, order_id, changes=None, sign_valid=True):
    data = client.gateway.orders[order_id]
    data['status'] = 'OD'
    params = {'appid': client.gateway.app_id, 'trade_order_id': order_id, 'status': 'OD', 'total_fee': data['total_amount'], 'transaction_id': data['transaction_id'], 'open_order_id': data['open_order_id'], 'time': str(int(time.time())), 'nonce_str': 'test-nonce'}
    params.update(changes or {})
    params['hash'] = sign(params, client.gateway.secret) if sign_valid else 'a' * 32
    return client.post('/studio-api/payments/hupijiao/notify', content=urlencode(params), headers={'Content-Type': 'application/x-www-form-urlencoded'})


def test_server_quote_cad_cny_and_tamper(client):
    body = payload(client)
    quote = client.post('/studio-api/cart/quote', json={'items': items()}).json()
    assert (quote['total_cents'], quote['cny_fen'], quote['fx_cny_per_cad']) == (1600, 8000, '5.0000')
    body['items'][0]['price'] = .01
    assert place(client, body).status_code == 422
    body['items'][0].pop('price')
    body['quote_id'] = 'a' * 64
    assert place(client, body).status_code == 409


def test_idempotent_durable_checkout_and_order_authorization(client):
    body = payload(client); key = str(uuid.uuid4())
    first = place(client, body, key)
    assert first.status_code == 201, first.text
    assert first.json()['status'] == 'pending'
    second = place(client, body, key)
    assert second.json()['id'] == first.json()['id']
    assert client.gateway.creates == 1
    oid = first.json()['id']
    assert client.get('/studio-api/orders/' + oid).status_code == 404
    result = client.get('/studio-api/orders/' + oid, headers={'X-Order-Key': body['access_key']})
    assert result.status_code == 200
    assert 'customer' not in result.json() and 'access_hash' not in result.json()
    body['name'] = 'changed'
    assert place(client, body, key).status_code == 409


def test_last_seat_concurrency_is_atomic(client):
    body = payload(client, items('pair', 2))
    bodies = [copy.deepcopy(body), copy.deepcopy(body)]
    for b in bodies: b['access_key'] = secrets.token_hex(32)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda b: place(client, b).status_code, bodies))
    assert sorted(results) == [201, 409]
    assert client.gateway.creates == 1


def test_payment_converts_hold_and_repeated_callback_does_not_duplicate(client):
    body = payload(client)
    oid = place(client, body).json()['id']
    assert notify(client, oid).text == 'success'
    assert notify(client, oid).text == 'success'
    result = client.get('/studio-api/orders/' + oid, headers={'X-Order-Key': body['access_key']}).json()
    assert (result['status'], result['fulfillment']) == ('paid', 'confirmed')
    assert 'payment_url' not in result
    with studio.database() as db:
        assert db.execute("SELECT count(*) FROM commerce_events WHERE event='paid'").fetchone()[0] == 1
    slots = client.get('/studio-api/availability', params={'date': items()[0]['booking']['date']}).json()['slots']
    assert next(s['remaining'] for s in slots if s['start'] == '14:00') == 1


@pytest.mark.parametrize('changes,valid', [({'total_fee': '0.01'}, True), ({'appid': 'wrong'}, True), ({}, False), ({'open_order_id': 'another'}, True), ({'total_fee': 'NaN'}, True)])
def test_bad_payment_proof_never_confirms(client, changes, valid):
    oid = place(client).json()['id']
    assert notify(client, oid, changes, valid).status_code != 200
    with studio.database() as db:
        assert db.execute('SELECT status FROM commerce_orders WHERE id=?', (oid,)).fetchone()[0] == 'pending'


def test_signed_forged_paid_callback_still_requires_provider_paid(client):
    oid = place(client).json()['id']
    original = client.gateway.query
    client.gateway.query = lambda order: {**original(order), 'status': 'WP'}
    assert notify(client, oid).status_code == 409


def test_gateway_timeout_reservation_and_retry_are_not_duplicate_orders(client):
    body = payload(client); key = str(uuid.uuid4()); client.gateway.timeout = True
    result = place(client, body, key)
    assert result.json()['status'] == 'payment_uncertain'
    assert place(client, body, key).json()['id'] == result.json()['id']
    assert client.gateway.creates == 1
    assert notify(client, result.json()['id']).text == 'success'


def test_expired_hold_releases_and_late_payment_cannot_overbook(client):
    body = payload(client, items('pair', 2))
    oid = place(client, body).json()['id']
    with studio.database() as db:
        db.execute('UPDATE commerce_orders SET hold_until=?,expires_at=? WHERE id=?', (time.time() - 1, time.time() - 1, oid))
    shop.reconcile(oid, force=True)
    second = place(client, payload(client, items('pair', 2))).json()['id']
    assert notify(client, second).text == 'success'
    assert notify(client, oid).text == 'success'
    with studio.database() as db:
        assert db.execute('SELECT status FROM commerce_orders WHERE id=?', (oid,)).fetchone()[0] == 'paid_needs_review'
        assert shop.remaining_seats(db, shop.settings_for(db), items()[0]['booking']['date'], 840, 960) == 0


def test_late_payment_with_capacity_is_fulfilled(client):
    oid = place(client).json()['id']
    with studio.database() as db: db.execute("UPDATE commerce_orders SET status='expired',hold_until=0 WHERE id=?", (oid,))
    assert notify(client, oid).text == 'success'
    with studio.database() as db: assert db.execute('SELECT status FROM commerce_orders WHERE id=?', (oid,)).fetchone()[0] == 'paid'


def test_day_pass_reserves_through_closing_and_pair_means_two(client):
    bad = items('pair', 1)
    assert client.post('/studio-api/cart/quote', json={'items': bad}).status_code == 422
    bad = items('day'); bad[0]['booking']['end'] = '16:00'
    assert client.post('/studio-api/cart/quote', json={'items': bad}).status_code == 422
    body = payload(client, items('pair', 2))
    assert place(client, body).status_code == 201
    late = items(); late[0]['booking'].update(start='20:00', end='21:00')
    assert client.post('/studio-api/cart/quote', json={'items': late}).status_code == 409
    early = items(); early[0]['booking'].update(start='12:00', end='14:00')
    assert client.post('/studio-api/cart/quote', json={'items': early}).status_code == 200


def test_combined_cart_cannot_overbook_itself(client):
    both = items('pair', 2) + items('hourly', 1)
    assert client.post('/studio-api/cart/quote', json={'items': both}).status_code == 409


def publish_product(client):
    p = next(p for p in client.get('/studio-api/manage/commerce').json()['products'] if p['id'] == 'starter')
    p.update(price_cents=1234, stock=2, active=True)
    assert client.put('/studio-api/manage/products/starter', json=p).status_code == 200


def test_goods_stock_is_reserved_and_decremented_only_once(client):
    publish_product(client)
    selected = [{'product_id': 'starter', 'quantity': 2}]
    oid = place(client, payload(client, selected)).json()['id']
    assert client.post('/studio-api/cart/quote', json={'items': selected}).status_code == 409
    assert notify(client, oid).text == 'success'
    assert notify(client, oid).text == 'success'
    p = next(p for p in client.get('/studio-api/catalog').json()['products'] if p['id'] == 'starter')
    assert p['stock'] == 0 and p['available_stock'] == 0


def test_admin_can_edit_settings_but_not_override_payment(client):
    data = client.get('/studio-api/manage/commerce').json()
    old = data['settings']
    old['tax_mode'] = 'additional'; old['tax_bps'] = 1300
    assert client.put('/studio-api/manage/schedule', json=old).status_code == 200
    assert client.put('/studio-api/manage/schedule', json=old).status_code == 409
    q = client.post('/studio-api/cart/quote', json={'items': items()}).json()
    assert (q['tax_cents'], q['cny_fen']) == (208, 9040)
    oid = place(client).json()['id']
    assert client.patch('/studio-api/manage/orders/' + oid, json={'completed': True, 'version': 1}).status_code == 409
    assert notify(client, oid).text == 'success'
    row = client.get('/studio-api/manage/orders').json()['items'][0]
    result = client.patch('/studio-api/manage/orders/' + oid, json={'completed': True, 'staff_note': 'Collected', 'version': row['version']})
    assert result.status_code == 200, result.text
    assert result.json()['fulfillment'] == 'completed'


def test_closed_override_and_admin_auth(client):
    config = client.get('/studio-api/manage/commerce').json()['settings']
    day = items()[0]['booking']['date']
    config['overrides'] = [{'date': day, 'enabled': False, 'start': '10:00', 'end': '22:00'}]
    assert client.put('/studio-api/manage/schedule', json=config).status_code == 200
    assert client.get('/studio-api/availability', params={'date': day}).json()['reason'] == 'closed'
    assert client.post('/studio-api/cart/quote', json={'items': items()}).status_code == 409
    studio.app.dependency_overrides.clear()
    assert client.get('/studio-api/manage/commerce').status_code == 401
    assert client.put('/studio-api/manage/schedule', json=config).status_code == 401


def test_unconfigured_schedule_is_not_claimed_available(client):
    config = client.get('/studio-api/manage/commerce').json()['settings']
    config.update(enabled=False, capacity=0, tax_mode='unconfirmed')
    assert client.put('/studio-api/manage/schedule', json=config).status_code == 200
    assert client.get('/studio-api/catalog').json()['checkout_ready'] is False
    assert client.get('/studio-api/availability', params={'date': items()[0]['booking']['date']}).json()['reason'] == 'not_open'
    assert client.post('/studio-api/cart/quote', json={'items': items()}).status_code == 409


def test_capacity_cannot_drop_below_paid_or_held_seats(client):
    assert place(client, payload(client, items('pair', 2))).status_code == 201
    config = client.get('/studio-api/manage/commerce').json()['settings']; config['capacity'] = 1
    assert client.put('/studio-api/manage/schedule', json=config).status_code == 409


def test_polling_recovers_lost_callback_and_cannot_be_spoofed_with_querystring(client):
    body = payload(client); oid = place(client, body).json()['id']
    result = client.get('/studio-api/orders/' + oid + '?payment=success', headers={'X-Order-Key': body['access_key']})
    assert result.json()['status'] == 'pending'
    client.gateway.orders[oid]['status'] = 'OD'
    shop.reconcile(oid, force=True)
    with studio.database() as db: assert db.execute('SELECT status FROM commerce_orders WHERE id=?', (oid,)).fetchone()[0] == 'paid'


def test_price_changes_do_not_mutate_existing_payment_amounts(client):
    body = payload(client); oid = place(client, body).json()['id']
    config = client.get('/studio-api/manage/commerce').json()['settings']; config['fx_cny_per_cad'] = '6.0000'
    assert client.put('/studio-api/manage/schedule', json=config).status_code == 200
    assert place(client, body).status_code == 409
    assert notify(client, oid).text == 'success'
    order = client.get('/studio-api/manage/orders').json()['items'][0]
    assert order['quote']['cny_fen'] == 8000
