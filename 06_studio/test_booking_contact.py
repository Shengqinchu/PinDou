import json
import uuid
import pytest

from test_reservations import client, body, submit
import app as studio


def test_direct_booking_without_checkbox_and_retry(client):
    payload = body()
    payload.pop('consent')
    key = str(uuid.uuid4())
    response = submit(client, payload, key)
    assert response.status_code == 201
    assert submit(client, payload, key).json()['id'] == response.json()['id']
    with studio.database() as db:
        rows = db.execute('SELECT payload FROM studio_reservations').fetchall()
        assert len(rows) == 1
        assert json.loads(rows[0]['payload']).get('consent') is None


def test_legacy_opted_in_request_remains_retryable(client):
    key = str(uuid.uuid4())
    response = submit(client, key=key)
    assert response.status_code == 201
    assert submit(client, key=key).json()['id'] == response.json()['id']


def test_explicit_refusal_and_invalid_contact_still_rejected(client):
    payload = body()
    payload['consent'] = False
    assert submit(client, payload).status_code == 422
    payload.pop('consent')
    payload['contact_method'] = 'email'
    payload['contact'] = 'not-an-email'
    assert submit(client, payload).status_code == 422
    with studio.database() as db:
        assert db.execute('SELECT count(*) FROM studio_reservations').fetchone()[0] == 0


@pytest.mark.parametrize('contact', ['名', '表情', '🐶'])
def test_short_wechat_booking_is_saved_reused_and_retryable(client, contact):
    payload = body() | {'contact': contact, 'contact_profile_version': 0}
    key = str(uuid.uuid4())
    booked = submit(client, payload, key)
    assert booked.status_code == 201, booked.text
    assert submit(client, payload, key).json() == booked.json()
    profile = client.get('/studio-api/auth/booking-profile').json()
    assert profile['contact'] == contact and profile['complete']
    updated = client.put('/studio-api/auth/booking-profile', json={
        'name': 'Local booking guest', 'contact_method': 'wechat', 'contact': '兔', 'version': profile['version']})
    assert updated.status_code == 200, updated.text
    assert updated.json()['complete']
    reused = submit(client, body() | {'name': '', 'contact': '', 'contact_profile_version': updated.json()['version']})
    assert reused.status_code == 201, reused.text
    with studio.database() as db:
        rows = dict(db.execute('SELECT id,payload FROM studio_reservations'))
        assert len(rows) == 2
        assert json.loads(rows[booked.json()['id']])['contact'] == contact
        assert json.loads(rows[reused.json()['id']])['contact'] == '兔'


@pytest.mark.parametrize('method,contact', [('wechat',''),('wechat','  '),('email','名'),('phone','1'),('other','名')])
def test_relaxed_wechat_minimum_still_rejects_missing_or_invalid_contacts(client, method, contact):
    assert submit(client, body() | {'contact_method': method, 'contact': contact}).status_code == 422
    assert client.put('/studio-api/auth/booking-profile', json={
        'name':'Local booking guest','contact_method':method,'contact':contact,'version':0}).status_code == 422
    with studio.database() as db:
        assert db.execute('SELECT count(*) FROM studio_reservations').fetchone()[0] == 0
        assert db.execute('SELECT count(*) FROM studio_booking_profiles').fetchone()[0] == 0


def test_returning_guest_can_recover_short_wechat_from_own_history(client):
    from test_returning_reservations import completed
    completed()
    with studio.database() as db:
        row = db.execute('SELECT id,payload FROM studio_reservations').fetchone()
        payload = json.loads(row['payload']) | {'contact_method':'wechat','contact':'猫'}
        db.execute('UPDATE studio_reservations SET payload=? WHERE id=?', (json.dumps(payload),row['id']))
    booked = submit(client, body() | {'name':'','contact':''})
    assert booked.status_code == 201, booked.text
    with studio.database() as db:
        saved = json.loads(db.execute('SELECT payload FROM studio_reservations WHERE id=?',(booked.json()['id'],)).fetchone()[0])
        assert saved['contact_method'] == 'wechat' and saved['contact'] == '猫'
