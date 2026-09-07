"""Origin-only smoke check with short-lived admin tokens and exact QA row cleanup."""
import json
import os
import sqlite3
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from dotenv import dotenv_values

for name, value in dotenv_values('/opt/pindou/shared/.env').items():
    if value is not None:
        os.environ[name] = value
sys.path.insert(0, '/opt/pindou/current/06_backend')
from pindou.api.security import create_access_token

base = 'http://127.0.0.1:8011/studio-api'
admin = create_access_token(subject='studio-deployment-qa', role='admin', expires_delta=timedelta(minutes=2))
viewer = create_access_token(subject='studio-deployment-qa', role='viewer', expires_delta=timedelta(minutes=2))
created = []


def call(path, method='GET', body=None, token=None, key=None):
    headers = {'Content-Type': 'application/json'}
    if token: headers['Authorization'] = 'Bearer ' + token
    if key: headers['Idempotency-Key'] = key
    data = None if body is None else json.dumps(body).encode()
    try:
        with urlopen(Request(base + path, data=data, headers=headers, method=method), timeout=15) as response:
            return response.status, json.load(response)
    except HTTPError as error:
        return error.code, json.load(error)


try:
    assert call('/health')[0] == 200
    assert call('/manage/requests')[0] == 401
    assert call('/manage/requests', token=viewer)[0] == 403
    assert call('/manage/requests', token=admin)[0] == 200
    tomorrow = (datetime.now(ZoneInfo('America/Toronto')) + timedelta(days=1)).date().isoformat()
    for kind in ['visit', 'pickup']:
        payload = {'name': 'DEPLOYMENT QA - DO NOT CONTACT', 'kind': kind, 'contact_method': 'wechat', 'contact': 'local-deploy-test-only', 'consent': True}
        if kind == 'visit': payload['booking'] = {'date': tomorrow, 'start': '14:00', 'end': '15:00', 'guests': 1, 'plan': 'hourly'}
        else: payload['items'] = [{'id': 'beads', 'quantity': 2}]
        key = str(uuid.uuid4())
        status, result = call('/requests', 'POST', payload, key=key)
        assert status == 201, (status, result)
        ref = result['id']; created.append(ref)
        assert call('/requests', 'POST', payload, key=key)[1]['id'] == ref
        status, listing = call('/manage/requests', token=admin)
        row = next(row for row in listing['items'] if row['id'] == ref)
        assert row['payload']['name'] == payload['name']
        update = {'status': 'confirmed', 'staff_note': 'Automated QA; no customer involved.', 'version': 1}
        assert call('/manage/requests/' + ref, 'PATCH', update, token=admin)[0] == 200
        assert call('/manage/requests/' + ref, 'PATCH', update, token=admin)[0] == 409
    print(json.dumps({'health': 'ok', 'anonymous': 'denied', 'viewer': 'denied', 'admin': 'verified via existing backend', 'visit_and_pickup': 'saved and readable', 'duplicate_retry': 'same id', 'version_conflict': '409', 'qa_rows': len(created)}, indent=2))
finally:
    with sqlite3.connect('/opt/pindou/studio/shared/studio.sqlite3') as db:
        for ref in created:
            row = db.execute('SELECT payload FROM studio_requests WHERE id=?', (ref,)).fetchone()
            if row and json.loads(row[0])['name'] == 'DEPLOYMENT QA - DO NOT CONTACT':
                db.execute('DELETE FROM studio_audit WHERE request_id=?', (ref,))
                db.execute('DELETE FROM studio_requests WHERE id=?', (ref,))
    print('Exact synthetic QA rows removed; customer rows untouched.')
