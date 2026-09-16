"""Admin-created visits must never mint customer self-booking rewards."""
import json
import base64
import sqlite3
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime

import pytest
import app as studio
import reservations
import wallet
from test_reservations import client, admin, body, submit


def prepare(client):
    client.get('/studio-api/auth/me')
    admin()


def payload(kind='booking', **changes):
    return {
        'kind': kind, 'booking': body()['booking'] if kind == 'booking' else body('2026-09-06')['booking'],
        'status': 'pending' if kind == 'booking' else 'completed',
        'reason': 'Host verified visit', 'staff_note': 'Private source record', 'public_note': 'See you soon',
        **({} if kind == 'booking' else {'actual_minutes': 90, 'actual_guests': 2}), **changes,
    }


def create(client, data=None, key=None, owner='qa-owner'):
    return client.post(f'/studio-api/manage/members/{owner}/reservations', json=data or payload(),
                       headers={'Idempotency-Key': key or str(uuid.uuid4())})


def entries(reference):
    with studio.database() as db:
        return (db.execute('SELECT count(*) FROM studio_wallet_ledger WHERE reservation_id=?', (reference,)).fetchone()[0],
                db.execute('SELECT count(*) FROM studio_finance_entries WHERE reservation_id=?', (reference,)).fetchone()[0])


def change(client, row, status, **fields):
    return client.patch('/studio-api/manage/reservations/'+row['id'],
                        json={'version': row['version'], 'status': status, **fields})


def test_admin_booking_completion_retries_edits_and_status_cycles(client, monkeypatch):
    prepare(client)
    key = str(uuid.uuid4())
    first = create(client, key=key)
    assert first.status_code == 201
    row = first.json()
    assert row['creation_source'] == 'admin_booking'
    assert create(client, key=key).json()['id'] == row['id']
    assert entries(row['id']) == (0, 0)
    confirmed = change(client, row, 'confirmed').json()
    early = change(client, confirmed, 'completed', actual_minutes=120, actual_guests=2)
    assert early.status_code == 422
    assert entries(row['id']) == (0, 0)
    monkeypatch.setattr(reservations, 'now_local', lambda: datetime(2026, 9, 8, 18, tzinfo=reservations.ZONE))
    done = change(client, confirmed, 'completed', actual_minutes=120, actual_guests=2)
    assert done.status_code == 200
    assert change(client, confirmed, 'completed', actual_minutes=120, actual_guests=2).status_code == 409
    edited = change(client, done.json(), 'completed', actual_minutes=150, actual_guests=3, public_note='Corrected')
    assert edited.status_code == 200
    assert change(client, edited.json(), 'cancelled').status_code == 200
    # Follow existing status rules when confirming again; origin stays unchanged.
    monkeypatch.setattr(reservations, 'now_local', lambda: datetime(2026, 9, 8, 9, tzinfo=reservations.ZONE))
    restored = change(client, {'id': row['id'], 'version': edited.json()['version']+1}, 'confirmed').json()
    assert change(client, restored, 'completed').status_code == 200
    assert entries(row['id']) == (0, 1)
    with studio.database() as db:
        assert db.execute('SELECT points FROM studio_members WHERE owner_id=?', ('qa-owner',)).fetchone()[0] == 166
        assert db.execute("SELECT count(*) FROM studio_wallet_ledger WHERE kind='registration_reward'").fetchone()[0] == 1


def test_backfill_is_visible_private_audited_and_atomic(client):
    prepare(client)
    key = str(uuid.uuid4())
    before = client.get('/studio-api/auth/wallet').json()
    result = create(client, payload('backfill'), key)
    assert result.status_code == 201
    row = result.json()
    assert row['status'] == 'completed' and row['creation_source'] == 'admin_backfill'
    assert create(client, payload('backfill'), key).json()['id'] == row['id']
    assert entries(row['id']) == (0, 1)
    assert client.get('/studio-api/auth/wallet').json() == before
    visible = client.get('/studio-api/auth/reservations').json()['items']
    assert visible[0]['id'] == row['id'] and visible[0]['actual_minutes'] == 90
    assert 'staff_note' not in visible[0] and 'created_by' not in visible[0]
    personal = client.get('/studio-api/reservations/'+row['id']).json()
    assert 'Private source record' not in json.dumps(personal)
    listing = client.get('/studio-api/manage/reservations', params={'owner_id':'qa-owner'}).json()
    assert listing['items'][0]['created_by'] == 'test-owner'
    assert client.get('/studio-api/manage/reservations', params={'owner_id':'missing'}).json()['items'] == []
    audit = client.get('/studio-api/manage/reservations/'+row['id']+'/events').json()
    assert audit['total'] == 1
    snapshot = json.loads(audit['items'][0]['note'])
    assert snapshot['reason'] == 'Host verified visit' and snapshot['owner_id'] == 'qa-owner'
    assert snapshot['creation_source'] == 'admin_backfill'
    with studio.database() as db:
        cash = db.execute('SELECT * FROM studio_finance_entries WHERE reservation_id=?', (row['id'],)).fetchone()
        assert cash['amount_cents'] is None and cash['occurred_on'] == '2026-09-06'
    client.headers['Authorization'] = 'Bearer qa-other'
    assert client.get('/studio-api/reservations/'+row['id']).status_code == 404
    assert client.get('/studio-api/auth/reservations').json()['items'] == []


def test_backfill_does_not_reapply_current_schedule_or_award_on_restore(client):
    prepare(client)
    with studio.database() as db:
        policy = reservations.read_policy(db)
        policy['max_guests_per_group'] = 1
        for day in policy['weekly_hours']: day['enabled'] = False
        db.execute('UPDATE reservation_policy SET settings=?', (json.dumps(policy),))
    row = create(client, payload('backfill')).json()
    assert change(client, row, 'completed', actual_minutes=30, actual_guests=3).status_code == 200
    url = '/studio-api/manage/reservations/'+row['id']
    assert client.request('DELETE', url, json={'version':2,'reason':'Correction'}).status_code == 200
    assert client.post(url+'/restore', json={'version':3,'reason':'Restored visit'}).status_code == 200
    assert change(client, {'id':row['id'],'version':4}, 'completed').status_code == 200
    assert entries(row['id']) == (0, 1)
    studio.initialize()
    assert entries(row['id']) == (0, 1)


@pytest.mark.parametrize('field,value', [('creation_source','customer_self'),('created_by','customer:qa-owner'),('owner_id','qa-other')])
def test_api_cannot_rewrite_origin(client, field, value):
    prepare(client)
    assert create(client, payload(**{field:value})).status_code == 422
    row = create(client, payload('backfill')).json()
    assert change(client, row, 'completed', **{field:value}).status_code == 422
    assert entries(row['id']) == (0, 1)


def test_database_origin_and_audit_are_immutable_ledger_rechecks_origin(client):
    prepare(client)
    row = create(client, payload('backfill')).json()
    with studio.database() as db:
        for sql in ("UPDATE studio_reservations SET creation_source='customer_self' WHERE id=?",
                    "UPDATE studio_reservations SET created_by='customer:qa-owner' WHERE id=?"):
            with pytest.raises(sqlite3.IntegrityError): db.execute(sql, (row['id'],))
        with pytest.raises(sqlite3.IntegrityError):
            db.execute('DELETE FROM reservation_events WHERE reservation_id=?', (row['id'],))
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("UPDATE reservation_events SET note='' WHERE reservation_id=?", (row['id'],))
        forged = dict(db.execute('SELECT * FROM studio_reservations WHERE id=?', (row['id'],)).fetchone())
        forged['creation_source'] = 'customer_self'
        wallet.reward_visit(db, forged, 'test-owner')
    assert entries(row['id']) == (0, 1)


def test_replay_conflicts_and_concurrent_same_key(client):
    prepare(client)
    data, key = payload('backfill'), str(uuid.uuid4())
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _:create(client, data, key), range(2)))
    assert [r.status_code for r in results] == [201, 201]
    assert results[0].json()['id'] == results[1].json()['id']
    assert create(client, payload('backfill', actual_minutes=91), key).status_code == 409
    assert create(client, data, key, owner='qa-other').status_code == 409
    assert create(client, payload(), key).status_code == 409
    assert submit(client, key=key).status_code == 409
    studio.app.dependency_overrides[studio.admin_actor] = lambda:'another-admin'
    assert create(client, data, key).status_code == 409
    assert entries(results[0].json()['id']) == (0, 1)


@pytest.mark.parametrize('changes', [
    {'booking':body('2026-09-08')['booking']},
    {'booking':body('2026-09-07', '08:00','10:00')['booking']},
    {'booking':body('2026-09-06', '16:00','14:00')['booking']},
    {'booking':body('2026-09-06', '14:15','16:00')['booking']},
    {'actual_minutes':None}, {'actual_minutes':0}, {'actual_minutes':True},
    {'actual_guests':None}, {'actual_guests':100}, {'actual_guests':1.5},
    {'status':'pending'}, {'reason':''},
])
def test_invalid_backfill_writes_nothing(client, changes):
    prepare(client)
    assert create(client, payload('backfill', **changes)).status_code == 422
    with studio.database() as db:
        for table in ('studio_reservations','reservation_events','studio_finance_entries'):
            assert db.execute('SELECT count(*) FROM '+table).fetchone()[0] == 0


def test_admin_booking_uses_policy_blocks_and_capacity(client):
    prepare(client)
    for booking in (body('2026-09-21')['booking'], body('2026-09-06')['booking'],
                    body('2026-09-09', '16:00','18:00')['booking'], body(end='15:00')['booking'],
                    body()['booking'] | {'guests':5}):
        assert create(client, payload(booking=booking)).status_code == 422
    with studio.database() as db:
        db.execute('UPDATE reservation_policy SET exclusive_groups=1')
    assert create(client, payload(status='confirmed')).status_code == 201
    assert create(client).status_code == 409
    assert create(client, payload(booking=body(start='16:00',end='18:00')['booking'])).status_code == 409
    assert client.post('/studio-api/manage/reservation-blocks', json={'date':'2026-09-10','start':'12:00','end':'16:00'}).status_code == 201
    assert create(client, payload(booking=body('2026-09-10')['booking'])).status_code == 409


def test_permissions_existing_member_and_stable_id_only(client):
    assert create(client).status_code in (401,403)
    assert client.get('/studio-api/manage/reservations/anything/events').status_code in (401,403)
    client.headers.pop('Authorization')
    assert create(client).status_code == 401
    client.headers['Authorization'] = 'Bearer qa-owner'
    prepare(client)
    assert create(client, owner='missing').status_code == 404
    with studio.database() as db:
        account = wallet.member(db,'qa-owner')
        assert create(client, owner=account['email']).status_code == 404
    assert create(client, key='not-a-uuid').status_code == 422


def test_verified_viewer_role_still_cannot_create(client, monkeypatch):
    class Verified:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *args): pass
    monkeypatch.setattr(studio, 'urlopen', lambda *args, **kwargs: Verified())
    claims = base64.urlsafe_b64encode(json.dumps({'role':'viewer','sub':'viewer-id'}).encode()).decode().rstrip('=')
    client.headers['Authorization'] = 'Bearer header.'+claims+'.signature'
    assert create(client).status_code == 403


def test_failed_finance_write_rolls_back_visit_and_audit(client, monkeypatch):
    import studio_finance
    prepare(client)
    def fail(*args): raise RuntimeError('Injected ledger failure')
    monkeypatch.setattr(studio_finance, 'from_completed', fail)
    # Observability middleware intentionally converts internal failures to 500.
    assert create(client, payload('backfill')).status_code == 500
    with studio.database() as db:
        for table in ('studio_reservations','reservation_events','studio_finance_entries'):
            assert db.execute('SELECT count(*) FROM '+table).fetchone()[0] == 0


def test_admin_creation_never_triggers_registration_for_existing_unrewarded_member(client):
    admin()
    with studio.database() as db:
        db.execute("INSERT INTO studio_members(owner_id,name,created_at,updated_at) VALUES('old-id','Earlier customer','old','old')")
    assert create(client, payload('backfill'), owner='old-id').status_code == 201
    with studio.database() as db:
        assert db.execute("SELECT points FROM studio_members WHERE owner_id='old-id'").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM studio_wallet_ledger WHERE owner_id='old-id'").fetchone()[0] == 0


def test_new_copy_is_registered_for_host_editor_and_preserves_overrides(client):
    prepare(client)
    path = '/studio-api/manage/content/admin-visits'
    doc = client.get(path).json()
    assert 'no_reward' in doc['data'] and 'add_backfill' in doc['data']
    doc['data']['add_booking'] = ['Owner wording', 'Host wording']
    saved = client.put(path, json={'version':doc['version'], 'data':doc['data'], 'publish':True})
    assert saved.status_code == 200
    studio.initialize()
    assert client.get(path).json()['published']['add_booking'] == ['Owner wording', 'Host wording']


def test_self_booking_and_registration_reward_unchanged(client, monkeypatch):
    prepare(client)
    row = submit(client).json()
    assert row['creation_source'] == 'customer_self'
    confirmed = change(client, row, 'confirmed').json()
    monkeypatch.setattr(wallet,'now',lambda:'2026-09-08T18:00:00-04:00')
    done = change(client, confirmed, 'completed', actual_minutes=120, actual_guests=2)
    assert done.status_code == 200
    assert change(client, done.json(), 'completed', actual_minutes=150).status_code == 200
    assert entries(row['id']) == (1, 1)
    assert client.get('/studio-api/auth/wallet').json()['account']['points'] == 332


def test_legacy_migration_is_once_only_and_unknown_writers_fail_closed(client, monkeypatch):
    prepare(client)
    row = submit(client).json()
    with studio.database() as db:
        # Reconstruct the schema immediately before this feature migration.
        db.execute('DROP TRIGGER reservation_origin_immutable')
        db.execute('DROP TRIGGER IF EXISTS wallet_self_booking_rewards')
        db.execute('ALTER TABLE studio_reservations DROP COLUMN creation_source')
        db.execute('ALTER TABLE studio_reservations DROP COLUMN created_by')
    reservations.initialize(studio.database)
    reservations.initialize(studio.database)
    with studio.database() as db:
        old = db.execute('SELECT * FROM studio_reservations WHERE id=?',(row['id'],)).fetchone()
        assert old['creation_source'] == 'legacy_customer'
    confirmed = change(client,row,'confirmed').json()
    monkeypatch.setattr(wallet,'now',lambda:'2026-09-08T18:00:00-04:00')
    assert change(client,confirmed,'completed',actual_minutes=120,actual_guests=2).status_code == 200
    assert entries(row['id']) == (1, 1)
    with studio.database() as db:
        db.execute('''INSERT INTO studio_reservations(id,created_at,updated_at,status,payload,visitor_hash,
          idempotency_key,payload_hash,owner_id,actual_minutes,actual_guests)
          VALUES('UNKNOWN','now','now','completed',?,'',?,'','qa-owner',120,2)''',
          (json.dumps(body('2026-09-06')),str(uuid.uuid4())))
        wallet.reward_visit(db,db.execute("SELECT * FROM studio_reservations WHERE id='UNKNOWN'").fetchone(),'test')
    assert entries('UNKNOWN') == (0, 0)


def test_schema_migration_is_atomic_when_interrupted_between_columns(client):
    prepare(client)
    row = submit(client).json()
    with studio.database() as db:
        db.execute('DROP TRIGGER reservation_origin_immutable')
        db.execute('DROP TRIGGER IF EXISTS wallet_self_booking_rewards')
        db.execute('ALTER TABLE studio_reservations DROP COLUMN creation_source')
        db.execute('ALTER TABLE studio_reservations DROP COLUMN created_by')

    class InterruptedConnection:
        def __init__(self, db): self.db = db
        def executescript(self, sql): return self.db.executescript(sql)
        def execute(self, sql, *args):
            if 'ADD COLUMN created_by' in sql:
                raise RuntimeError('Interrupted schema upgrade')
            return self.db.execute(sql, *args)

    @contextmanager
    def interrupted_database():
        with studio.database() as db:
            yield InterruptedConnection(db)

    with pytest.raises(RuntimeError, match='Interrupted schema upgrade'):
        reservations.initialize(interrupted_database)
    with studio.database() as db:
        columns = {r[1] for r in db.execute('PRAGMA table_info(studio_reservations)')}
        assert not {'creation_source', 'created_by'} & columns
    reservations.initialize(studio.database)
    with studio.database() as db:
        original = db.execute('SELECT * FROM studio_reservations WHERE id=?', (row['id'],)).fetchone()
        assert original['creation_source'] == 'legacy_customer'
        assert json.loads(original['payload'])['booking'] == row['booking']


def test_legacy_reward_writer_cannot_mint_admin_points(client):
    prepare(client)
    row = create(client, payload('backfill')).json()
    with studio.database() as db:
        before = dict(db.execute("SELECT * FROM studio_members WHERE owner_id='qa-owner'").fetchone())
    # Simulate a rollback writer that calls the ledger without the new Python guard.
    with pytest.raises(sqlite3.IntegrityError, match='visit reward requires a self booking'):
        with studio.database() as db:
            db.execute('BEGIN IMMEDIATE')
            wallet.append(db, 'qa-owner', kind='visit_reward', minutes=0, points=166,
                          note='', actor='old-release', key='visit-reward:'+row['id'],
                          digest=wallet.fingerprint({'visit':row['id'],'points':166}),
                          effective_date=row['booking']['date'], reservation_id=row['id'])
    with studio.database() as db:
        assert dict(db.execute("SELECT * FROM studio_members WHERE owner_id='qa-owner'").fetchone()) == before
    assert entries(row['id']) == (0, 1)
