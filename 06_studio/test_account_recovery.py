import importlib.util
import sqlite3
import time
from pathlib import Path

import pytest
import app as studio
import account_recovery
import customer_auth
import wallet
from test_reservations import client
from test_authing_login import configured
from test_miniapp_login import setup, ticket, PREFIX, APP

spec = importlib.util.spec_from_file_location('recovery_ops', Path(__file__).parents[1] / '07_ops/studio_account_recovery.py')
ops = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ops)


def test_released_client_can_keep_password_login_after_connection_conflict(setup):
    client, _, _ = setup
    proof = ticket(client)
    spare = client.post(PREFIX + '/native/create', headers=proof).json()['user']['id']
    login = client.post('/studio-api/auth/password-login', json={'email': 'returning@example.test', 'password': 'local-password'})
    assert login.status_code == 200
    session = login.json()
    for _ in range(2):
        result = client.post(PREFIX + '/native/bind', headers=proof | {'Authorization': 'Bearer ' + session['token']})
        assert result.status_code == 200
        assert result.json() == {'linked': False, 'reason': 'wechat_binding_conflict'}
    assert client.get('/studio-api/auth/wallet', headers={'Authorization': 'Bearer ' + session['token']}).status_code == 200
    with studio.database() as db:
        assert db.execute('SELECT user_id FROM studio_miniapp_identities').fetchone()[0] == spare
        record = db.execute('SELECT * FROM studio_miniapp_binding_conflicts').fetchone()
        assert record['source_user_id'] == spare and record['target_user_id'] == session['user']['id']
        assert record['attempts'] == 2 and record['status'] == 'pending'
        assert len(record['identity_hash']) == 64
        assert db.execute('SELECT count(*) FROM studio_wallet_ledger WHERE owner_id=?', (session['user']['id'],)).fetchone()[0] == 1


def test_unverified_or_expired_attempts_never_enter_support_queue(setup):
    client, _, _ = setup
    proof = ticket(client)
    client.post(PREFIX + '/native/create', headers=proof)
    assert client.post(PREFIX + '/native/bind', headers=proof | {'Authorization': 'Bearer forged'}).status_code == 401
    assert client.post(PREFIX + '/native/bind', headers={'X-Pindou-Miniapp': 'x' * 43}).status_code == 401
    with studio.database() as db:
        assert db.execute('SELECT count(*) FROM studio_miniapp_binding_conflicts').fetchone()[0] == 0


def test_retired_tokens_cannot_read_or_spend_studio_balances(client):
    client.get('/studio-api/auth/me')
    with studio.database() as db:
        db.execute('INSERT INTO studio_account_retirements VALUES(?,?,?,?,?)', ('qa-owner', 'qa-other', int(time.time()), 'test', 'verified duplicate'))
        before = ops.snapshots(db)
    assert client.get('/studio-api/auth/me').status_code == 401
    assert client.get('/studio-api/auth/wallet').status_code == 401
    assert client.put('/studio-api/auth/booking-profile', json={'name': '', 'contact': '', 'version': 0}).status_code == 401
    with studio.database() as db:
        assert ops.snapshots(db) == before


@pytest.fixture
def candidate(setup):
    client, _, _ = setup
    proof = ticket(client)
    source = client.post(PREFIX + '/native/create', headers=proof).json()['user']['id']
    client.get('/studio-api/auth/me')
    generator = sqlite3.connect(':memory:')
    generator.row_factory = sqlite3.Row
    generator.executescript('''
    CREATE TABLE users(id INTEGER PRIMARY KEY,openid TEXT,email TEXT,password_hash TEXT,nickname TEXT,avatar TEXT,
      created_at TEXT,free_credits_remaining INTEGER,paid_credits INTEGER,monthly_card_expires_at TEXT,membership_expires_at TEXT);
    CREATE TABLE credit_grants(owner_id TEXT,kind TEXT,source_type TEXT,amount_original INTEGER,amount_remaining INTEGER,amount_reserved INTEGER);
    CREATE TABLE credit_transactions(owner_id TEXT,source_type TEXT,direction TEXT,amount INTEGER);
    CREATE TABLE artworks(user_id TEXT,owner_id TEXT);
    ''')
    generator.execute('INSERT INTO users VALUES(?,?,?,?,?,?,?,?,?,?,?)', (1, 'qa-owner', 'owner@example.test', 'fixture', 'Original', '', '2026-09-01', 2, 1, None, None))
    generator.execute('INSERT INTO users VALUES(?,?,?,?,?,?,?,?,?,?,?)', (2, source, None, None, '', '', '2026-09-26', 3, 1, None, None))
    generator.execute('INSERT INTO credit_grants VALUES(?,?,?,?,?,?)', (source, 'gift', 'register_gift', 188, 188, 0))
    generator.execute('INSERT INTO credit_transactions VALUES(?,?,?,?)', (source, 'register_gift', 'grant', 188))
    with studio.database() as db:
        wallet.append(db, 'qa-owner', kind='gift', minutes=420, points=166, note='Fixture', actor='test', key='fixture-funds', digest='fixture')
        source_code = db.execute('SELECT customer_code FROM studio_members WHERE owner_id=?', (source,)).fetchone()[0]
        target_code = db.execute("SELECT customer_code FROM studio_members WHERE owner_id='qa-owner'").fetchone()[0]
    yield client, proof, source, source_code, target_code, generator
    generator.close()


def test_recovery_keeps_every_business_asset_and_changes_only_login_metadata(candidate):
    client, proof, source, sc, tc, generator = candidate
    with studio.database() as db:
        with pytest.raises(ValueError, match='confirmation'):
            ops.plan(db, generator, sc, tc, APP)
        account_recovery.record_conflict(db, APP, db.execute('SELECT openid FROM studio_miniapp_identities').fetchone()[0], 'qa-owner')
        before, gen_before = ops.snapshots(db), ops.snapshots(generator)
        proposal = ops.plan(db, generator, sc, tc, APP)
        assert proposal['target_minutes'] == 420 and proposal['target_points'] == 332
        ops.apply_plan(db, proposal, 'test-owner')
        changed = {k for k, v in ops.snapshots(db).items() if before[k] != v}
        assert changed == {'studio_miniapp_identities', 'studio_account_retirements', 'studio_archives', 'studio_miniapp_binding_conflicts', 'studio_account_recovery_events'}
        assert ops.snapshots(generator) == gen_before
        assert db.execute('SELECT minutes,points FROM studio_members WHERE owner_id=?', ('qa-owner',)).fetchone()[:] == (420, 332)
        assert ops.plan(db, generator, sc, tc, APP)['status'] == 'already_recovered'
    assert client.post(PREFIX + '/native/sign-in', headers=proof).json()['user']['id'] == 'qa-owner'
    assert client.post(PREFIX + '/native/create', headers=proof).json()['user']['id'] == 'qa-owner'


@pytest.mark.parametrize('case', ['studio_points', 'booking_profile', 'generator_art', 'credit_spent', 'membership', 'wechat_profile', 'another_binding', 'missing_proof', 'stale_proof', 'newer_target'])
def test_accounts_with_uncertain_ownership_or_assets_require_individual_review(candidate, case):
    _, _, source, sc, tc, generator = candidate
    with studio.database() as db:
        if case == 'studio_points':db.execute('UPDATE studio_members SET points=332 WHERE owner_id=?', (source,))
        if case == 'booking_profile':db.execute('INSERT INTO studio_booking_profiles(owner_id,updated_at) VALUES(?,?)', (source, '2026-09-26'))
        if case == 'generator_art':generator.execute('INSERT INTO artworks VALUES(?,?)', ('2', source))
        if case == 'credit_spent':generator.execute('UPDATE credit_grants SET amount_remaining=100')
        if case == 'membership':generator.execute('UPDATE users SET membership_expires_at=? WHERE openid=?', ('2026-12-01', source))
        if case == 'wechat_profile':generator.execute('UPDATE users SET nickname=? WHERE openid=?', ('An established customer', source))
        if case == 'another_binding':db.execute('INSERT INTO studio_miniapp_identities VALUES(?,?,?,?)', (APP, 'other-openid', 'qa-owner', 1))
        if case == 'newer_target':generator.execute("UPDATE users SET created_at='2026-10-01' WHERE openid='qa-owner'")
        if case == 'stale_proof':
            account_recovery.record_conflict(db, APP, db.execute('SELECT openid FROM studio_miniapp_identities').fetchone()[0], 'qa-owner')
            db.execute('UPDATE studio_miniapp_binding_conflicts SET last_seen=1')
        before = ops.snapshots(db)
        with pytest.raises(ValueError):ops.plan(db, generator, sc, tc, APP, owner_confirmed=case not in ('missing_proof', 'stale_proof'))
        assert ops.snapshots(db) == before


def test_retired_native_identity_cannot_be_created_again_if_mapping_is_lost(candidate):
    client, proof, source, sc, tc, generator = candidate
    with studio.database() as db:
        ops.apply_plan(db, ops.plan(db, generator, sc, tc, APP, owner_confirmed=True), 'test-owner')
        db.execute('DELETE FROM studio_miniapp_identities')
    assert client.post(PREFIX + '/native/create', headers=proof).status_code == 409
