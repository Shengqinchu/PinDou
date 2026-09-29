"""Audited login conflicts and retired, unused duplicate Studio accounts.

Contact text and account age are never identity proofs. A conflict is recorded
only after both a customer session and a server-exchanged WeChat proof pass.
This module never merges accounts or transfers balances automatically.
"""
import hashlib
import time


def initialize(db):
    db.executescript('''
    CREATE TABLE IF NOT EXISTS studio_miniapp_binding_conflicts (
      app_id TEXT NOT NULL, identity_hash TEXT NOT NULL, target_user_id TEXT NOT NULL,
      source_user_id TEXT NOT NULL, first_seen INTEGER NOT NULL, last_seen INTEGER NOT NULL,
      attempts INTEGER NOT NULL DEFAULT 1, status TEXT NOT NULL DEFAULT 'pending',
      PRIMARY KEY(app_id,identity_hash,target_user_id)
    );
    CREATE TABLE IF NOT EXISTS studio_account_retirements (
      owner_id TEXT PRIMARY KEY, replacement_id TEXT NOT NULL, created_at INTEGER NOT NULL,
      actor TEXT NOT NULL, reason TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS studio_account_recovery_events (
      id INTEGER PRIMARY KEY AUTOINCREMENT, created_at INTEGER NOT NULL,
      actor TEXT NOT NULL, action TEXT NOT NULL, source_user_id TEXT NOT NULL,
      target_user_id TEXT NOT NULL, app_id TEXT NOT NULL, identity_hash TEXT NOT NULL,
      detail TEXT NOT NULL
    );
    CREATE TRIGGER IF NOT EXISTS studio_recovery_event_no_update
      BEFORE UPDATE ON studio_account_recovery_events
      BEGIN SELECT RAISE(ABORT, 'account recovery audit is append-only'); END;
    CREATE TRIGGER IF NOT EXISTS studio_recovery_event_no_delete
      BEFORE DELETE ON studio_account_recovery_events
      BEGIN SELECT RAISE(ABORT, 'account recovery audit is append-only'); END;
    ''')


def retired(db, owner_id):
    return db.execute('SELECT 1 FROM studio_account_retirements WHERE owner_id=?', (owner_id,)).fetchone() is not None


def record_conflict(db, app_id, openid, target_user_id):
    source = db.execute('SELECT user_id FROM studio_miniapp_identities WHERE app_id=? AND openid=?',
                        (app_id, openid)).fetchone()
    digest = hashlib.sha256((app_id + '|' + openid).encode()).hexdigest()
    stamp = int(time.time())
    db.execute('''INSERT INTO studio_miniapp_binding_conflicts
      (app_id,identity_hash,target_user_id,source_user_id,first_seen,last_seen)
      VALUES(?,?,?,?,?,?) ON CONFLICT(app_id,identity_hash,target_user_id) DO UPDATE SET
      source_user_id=excluded.source_user_id,last_seen=excluded.last_seen,
      attempts=studio_miniapp_binding_conflicts.attempts+1,status='pending' ''',
      (app_id, digest, target_user_id, source['user_id'] if source else '', stamp, stamp))
