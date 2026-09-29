"""Dry-run first. Reconnect an explicitly verified, unused WeChat duplicate.

Run on the current origin. No account/asset merge, password reset, or outbound
notification. Both databases are backed up; only the Studio binding, retirement,
archive and audit records change. Pending conflicts alone are not auto-applied.
"""
import argparse
import hashlib
import json
import socket
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

STUDIO = '/opt/pindou/studio/shared/studio.sqlite3'
GENERATOR = '/opt/pindou/shared/var/pindou.db'
APP_ID = 'wx9f2b4d171e92a5ef'


def connect(path, readonly=True):
    db = sqlite3.connect('file:' + str(path) + ('?mode=ro' if readonly else '?mode=rw'), uri=True, timeout=15)
    db.row_factory = sqlite3.Row
    return db


def require(condition, message):
    if not condition:
        raise ValueError(message)


def snapshots(db):
    result = {}
    for name, in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"):
        rows = sorted(json.dumps(list(row), sort_keys=True, default=str) for row in db.execute('SELECT * FROM "' + name + '"'))
        result[name] = hashlib.sha256('\n'.join(rows).encode()).hexdigest()
    return result


def reference_counts(db, ids):
    result = {}
    for table, in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"):
        columns = {r[1] for r in db.execute('PRAGMA table_info("' + table + '")')}
        refs = columns.intersection({'owner_id', 'user_id', 'customer_id', 'member_id', 'bound_user', 'link_user', 'claimed_by_user_id'})
        for column in refs:
            count = db.execute('SELECT count(*) FROM "' + table + '" WHERE "' + column + '" IN (' + ','.join('?' for _ in ids) + ')', ids).fetchone()[0]
            if count:
                result[table + '.' + column] = count
    return result


def plan(studio, generator, source_code, target_code, app_id=APP_ID, owner_confirmed=False):
    require(source_code != target_code, 'Source and target must differ')
    source = studio.execute('SELECT * FROM studio_members WHERE customer_code=?', (source_code,)).fetchone()
    target = studio.execute('SELECT * FROM studio_members WHERE customer_code=?', (target_code,)).fetchone()
    require(source is not None and target is not None, 'Both customer codes must exist')
    source_id, target_id = source['owner_id'], target['owner_id']
    require(not studio.execute('SELECT 1 FROM studio_account_retirements WHERE owner_id=?', (target_id,)).fetchone(), 'Target is retired')
    existing = studio.execute('SELECT replacement_id FROM studio_account_retirements WHERE owner_id=?', (source_id,)).fetchone()
    if existing:
        require(existing[0] == target_id, 'Source retired to a different account')
        recovered = studio.execute('SELECT openid FROM studio_miniapp_identities WHERE app_id=? AND user_id=?', (app_id, target_id)).fetchone()
        require(recovered is not None, 'Recovered binding missing')
        digest = hashlib.sha256((app_id + '|' + recovered['openid']).encode()).hexdigest()
        require(studio.execute('''SELECT 1 FROM studio_account_recovery_events WHERE
          action='reconnect_unused_native_account' AND source_user_id=? AND target_user_id=?
          AND app_id=? AND identity_hash=?''', (source_id, target_id, app_id, digest)).fetchone(), 'Recovered binding does not match its audit record')
        return {'status': 'already_recovered', 'source_code': source_code, 'target_code': target_code}
    bindings = studio.execute('SELECT * FROM studio_miniapp_identities WHERE user_id=?', (source_id,)).fetchall()
    require(len(bindings) == 1 and bindings[0]['app_id'] == app_id, 'Source must have exactly the current miniapp binding')
    binding = bindings[0]
    expected = 'wechat_authing_' + hashlib.sha256(('pindou-native-wechat-v1|' + app_id + '|' + binding['openid']).encode()).hexdigest()
    require(source_id == expected, 'Source is not the independently created native WeChat account')
    require(not studio.execute('SELECT 1 FROM studio_miniapp_identities WHERE app_id=? AND user_id=?', (app_id, target_id)).fetchone(), 'Target has another WeChat binding')
    src = generator.execute('SELECT * FROM users WHERE openid=?', (source_id,)).fetchone()
    dst = generator.execute('SELECT * FROM users WHERE openid=?', (target_id,)).fetchone()
    require(src is not None and dst is not None, 'Shared account missing')
    require(bool(dst['email']) and bool(dst['password_hash']), 'Target must be an existing password account')
    require(not src['email'] and not src['password_hash'] and not src['nickname'] and not src['avatar'], 'Source already has its own identity/profile')
    require(src['created_at'] > dst['created_at'], 'Target is not older than the unused WeChat account')
    require(src['free_credits_remaining'] == 3 and src['paid_credits'] == 1, 'Source legacy credits differ from registration defaults')
    require(not src['monthly_card_expires_at'] and not src['membership_expires_at'], 'Source has membership rights')
    require(source['minutes'] == 0 and source['points'] == 166 and not source['staff_note'], 'Source has non-registration balances or host notes')
    ledger = studio.execute('SELECT kind,minutes_delta,points_delta FROM studio_wallet_ledger WHERE owner_id=?', (source_id,)).fetchall()
    require(len(ledger) == 1 and tuple(ledger[0]) == ('registration_reward', 0, 166), 'Source has business ledger activity')
    allowed_studio = {'studio_members', 'studio_wallet_ledger', 'studio_miniapp_identities',
                      'studio_customer_notification_preferences', 'studio_customer_wechat_nonces'}
    refs = reference_counts(studio, (source_id,))
    require(all(key.split('.')[0] in allowed_studio for key in refs), 'Source has profile, bookings, orders, another identity or other activity: ' + ','.join(refs))
    pref = studio.execute('SELECT email,phone FROM studio_customer_notification_preferences WHERE owner_id=?', (source_id,)).fetchone()
    require(not pref or not any(pref), 'Source has contact details requiring review')
    generator_ids = (source_id, str(src['id']))
    gen_refs = reference_counts(generator, generator_ids)
    require(all(key.split('.')[0] in {'credit_grants', 'credit_transactions'} for key in gen_refs), 'Source has generator assets or activity: ' + ','.join(gen_refs))
    for row in generator.execute('SELECT * FROM credit_grants WHERE owner_id IN (?,?)', generator_ids):
        require(row['kind'] == 'gift' and row['source_type'] == 'register_gift' and row['amount_remaining'] == row['amount_original'] and row['amount_reserved'] == 0, 'Source has spent or non-registration credits')
    for row in generator.execute('SELECT * FROM credit_transactions WHERE owner_id IN (?,?)', generator_ids):
        require(row['source_type'] == 'register_gift' and row['direction'] == 'grant', 'Source has credit transactions requiring review')
    digest = hashlib.sha256((app_id + '|' + binding['openid']).encode()).hexdigest()
    proof = studio.execute('''SELECT 1 FROM studio_miniapp_binding_conflicts WHERE
      app_id=? AND identity_hash=? AND target_user_id=? AND source_user_id=? AND last_seen>=?''',
      (app_id, digest, target_id, source_id, int(time.time()) - 7 * 86400)).fetchone()
    require(owner_confirmed or proof is not None, 'Need a recent dual-verified conflict or explicit owner confirmation of this pair')
    return {'status': 'ready', 'source_code': source_code, 'target_code': target_code,
            'source_id': source_id, 'target_id': target_id, 'app_id': app_id,
            'identity_hash': digest, 'binding_created_at': binding['created_at'],
            'target_minutes': target['minutes'], 'target_points': target['points'],
            'owner_confirmed': owner_confirmed}


def apply_plan(db, proposal, actor):
    require(proposal['status'] == 'ready', 'Plan is not ready')
    stamp = int(time.time())
    src, dst, app = proposal['source_id'], proposal['target_id'], proposal['app_id']
    changed = db.execute('UPDATE studio_miniapp_identities SET user_id=? WHERE app_id=? AND user_id=? AND created_at=?',
                         (dst, app, src, proposal['binding_created_at'])).rowcount
    require(changed == 1, 'Binding changed since planning')
    db.execute('INSERT INTO studio_account_retirements VALUES(?,?,?,?,?)',
               (src, dst, stamp, actor, 'unused_native_account_reconnected'))
    db.execute('INSERT INTO studio_archives(kind,entity_id,deleted_at,actor) VALUES(?,?,?,?)',
               ('member', src, datetime.now(timezone.utc).isoformat(), actor))
    db.execute('''UPDATE studio_miniapp_binding_conflicts SET status='resolved'
      WHERE app_id=? AND identity_hash=? AND target_user_id=?''', (app, proposal['identity_hash'], dst))
    detail = json.dumps({k: proposal[k] for k in ('source_code', 'target_code', 'target_minutes', 'target_points', 'owner_confirmed')}, sort_keys=True)
    db.execute('''INSERT INTO studio_account_recovery_events
      (created_at,actor,action,source_user_id,target_user_id,app_id,identity_hash,detail)
      VALUES(?,?,?,?,?,?,?,?)''', (stamp, actor, 'reconnect_unused_native_account', src, dst, app, proposal['identity_hash'], detail))


def public_plan(value):
    return {k: v for k, v in value.items() if k not in ('source_id', 'target_id', 'identity_hash')}


def pending_conflicts(db):
    """Codes are sufficient for an operator; omit raw WeChat IDs and login data."""
    return [dict(row) for row in db.execute('''SELECT
      s.customer_code AS source_code,t.customer_code AS target_code,
      c.first_seen,c.last_seen,c.attempts,c.status
      FROM studio_miniapp_binding_conflicts c
      LEFT JOIN studio_members s ON s.owner_id=c.source_user_id
      LEFT JOIN studio_members t ON t.owner_id=c.target_user_id
      WHERE c.status='pending' ORDER BY c.last_seen DESC''')]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source')
    parser.add_argument('--target')
    parser.add_argument('--list-conflicts', action='store_true')
    parser.add_argument('--owner-confirmed', action='store_true')
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--actor', default='owner-approved:codex-support')
    args = parser.parse_args()
    require(socket.gethostname() == '19558948263', 'Wrong production host')
    if args.list_conflicts:
        require(not args.source and not args.target and not args.apply, 'List mode cannot modify an account')
        with connect(STUDIO) as studio:
            print(json.dumps({'pending': pending_conflicts(studio)}))
        return
    require(bool(args.source and args.target), 'Provide --source and --target, or --list-conflicts')
    with connect(STUDIO) as studio, connect(GENERATOR) as generator:
        proposal = plan(studio, generator, args.source, args.target, owner_confirmed=args.owner_confirmed)
    if not args.apply or proposal['status'] == 'already_recovered':
        print(json.dumps(public_plan(proposal)));return
    folder = Path('/opt/pindou/studio/backups') / ('account-recovery-' + datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S'))
    folder.mkdir(mode=0o700)
    backups = {}
    for label, source in (('studio', STUDIO), ('generator', GENERATOR)):
        path = folder / (label + '.sqlite3')
        with connect(source) as origin, sqlite3.connect(path) as dest:
            origin.backup(dest)
            require(dest.execute('PRAGMA integrity_check').fetchone()[0] == 'ok', 'Invalid backup')
        path.chmod(0o600)
        backups[label] = hashlib.sha256(path.read_bytes()).hexdigest()
    # A short generator write reservation closes the inspection/use race; there
    # are no generator writes. All actual changes commit in one Studio transaction.
    with connect(GENERATOR, False) as generator, connect(STUDIO, False) as studio:
        generator.execute('BEGIN IMMEDIATE');studio.execute('BEGIN IMMEDIATE')
        proposal = plan(studio, generator, args.source, args.target, owner_confirmed=args.owner_confirmed)
        before, gen_before = snapshots(studio), snapshots(generator)
        apply_plan(studio, proposal, args.actor)
        changed = {k for k, v in snapshots(studio).items() if before.get(k) != v}
        require(changed <= {'studio_miniapp_identities', 'studio_account_retirements', 'studio_archives',
                            'studio_miniapp_binding_conflicts', 'studio_account_recovery_events'}, 'Unexpected Studio changes')
        require(gen_before == snapshots(generator), 'Generator data changed')
        for db in (studio, generator):
            require(db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok', 'Integrity check failed')
        require(plan(studio, generator, args.source, args.target, owner_confirmed=True)['status'] == 'already_recovered', 'Post-check failed')
    evidence = public_plan(proposal) | {'status': 'recovered', 'backup': str(folder), 'backup_sha256': backups,
                                      'changed_tables': sorted(changed), 'generator_unchanged': True}
    (folder / 'recovery.json').write_text(json.dumps(evidence, indent=2))
    (folder / 'recovery.json').chmod(0o600)
    print(json.dumps(evidence))


if __name__ == '__main__':
    main()
