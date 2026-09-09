import json
import uuid

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
