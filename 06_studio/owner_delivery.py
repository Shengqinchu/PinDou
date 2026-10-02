"""Keep unhandled owner alerts durable and expose transport health without PII."""
from datetime import datetime
import time

from fastapi import Depends


def keep_pending_alerts(db, stamp):
    # An unhandled reservation, unlike a test or cancellation message, is not
    # obsolete merely because the free provider window lasted 24 hours.
    db.execute("""UPDATE studio_owner_notifications SET state='skipped',error='superseded',
      updated_at=?,lease_until=0 WHERE kind IN ('created','changed') AND state IN ('queued','retry','expired','failed')
      AND NOT EXISTS(SELECT 1 FROM studio_reservations r WHERE r.id=reservation_id
        AND r.status='pending' AND r.deleted_at IS NULL)""", (stamp,))
    db.execute("""UPDATE studio_owner_notifications SET
      state=CASE WHEN state IN ('expired','failed') THEN 'retry' ELSE state END,
      error=CASE WHEN state IN ('expired','failed') THEN '' ELSE error END,
      next_attempt=CASE WHEN state IN ('expired','failed') THEN ? ELSE next_attempt END,
      expires_at=MAX(expires_at,?),updated_at=?
      WHERE kind IN ('created','changed') AND (state IN ('queued','retry') OR
        (state='expired' AND error='expired') OR (state='failed' AND error='retry_exhausted'))
      AND (expires_at<=? OR state IN ('expired','failed'))
      AND EXISTS(SELECT 1 FROM studio_reservations r WHERE r.id=reservation_id
        AND r.status='pending' AND r.deleted_at IS NULL)""", (stamp,stamp+86400,stamp,stamp+60))
    keep_pending_sms(db, stamp)


def keep_pending_sms(db, stamp):
    # Only automatic owner alerts that have NEVER begun sending are recoverable.
    # Customer messages, explicit failures and uncertain sends keep their existing
    # expiry/idempotency rules; a changed recipient must not replay old messages.
    db.execute("""UPDATE studio_sms_jobs SET state='queued',error='',expires_at=?
      WHERE message_id IS NULL AND (notification_key='created:'||reservation_id OR notification_key LIKE 'changed:'||reservation_id||':%')
      AND started_at=0 AND expires_at<=?
      AND (state='queued' OR (state='skipped' AND error='expired'))
      AND bridge_id IN (SELECT id FROM studio_sms_bridges WHERE role='owner_alert')
      AND EXISTS(SELECT 1 FROM studio_reservations r,studio_sms_settings s
        WHERE r.id=reservation_id AND r.status='pending' AND r.deleted_at IS NULL
          AND s.id=1 AND s.owner_enabled=1 AND s.owner_phone=recipient)""", (stamp+86400,stamp+60))


def snapshot(db, stamp=None):
    import owner_notifications as outbox
    import telegram_notifications as telegram
    stamp = time.time() if stamp is None else stamp
    settings = outbox.settings_for(db)
    attempts = [r[0] for r in db.execute("""SELECT created_at FROM studio_owner_notification_attempts
      WHERE channel='serverchan' AND created_at>? ORDER BY created_at""", (stamp-86400,))]
    limited = len(attempts) >= settings['daily_limit']
    configured = bool(settings['enabled'] and outbox.read_key(db))
    serverchan = {'enabled': bool(settings['enabled']), 'configured': configured,
      'ready': configured and not limited and settings['blocked_until']<=stamp,
      'used': len(attempts), 'limit': settings['daily_limit'], 'limited': limited,
      'next_available': max(settings['blocked_until'],
        attempts[-settings['daily_limit']]+86401 if limited else 0)}
    phone = db.execute('SELECT * FROM studio_sms_settings WHERE id=1').fetchone()
    bridge = db.execute("SELECT * FROM studio_sms_bridges WHERE role='owner_alert'").fetchone()
    phone_enabled = bool(phone and phone['owner_enabled'])
    phone_configured = bool(phone_enabled and phone['owner_phone'] and bridge and bridge['enabled'] and bridge['send_enabled'])
    phone_online = bool(bridge and bridge['last_seen']>stamp-90)
    sms = {'enabled': phone_enabled, 'configured': phone_configured,
      'ready': phone_configured and phone_online, 'online': phone_online,
      'last_seen': bridge['last_seen'] if bridge else 0}
    tg = telegram.settings_for(db)
    tg_configured = bool(tg['enabled'] and tg['chat_id'] and telegram.read_token(db))
    tg_state = {'enabled': bool(tg['enabled']), 'configured': tg_configured,
      'ready': tg_configured and tg['blocked_until']<=stamp}
    wx = db.execute('SELECT * FROM studio_owner_wechat_settings WHERE id=1').fetchone()
    import miniapp_login
    bindings = db.execute('SELECT count(*),coalesce(sum(grants),0) FROM studio_owner_wechat_bindings WHERE enabled=1 AND app_id=?',
      (miniapp_login.config().app_id,)).fetchone()
    wechat = {'enabled': bool(wx and wx['enabled']), 'bound': bindings[0]>0,
      'authorized': bool(bindings[1]>0), 'continuous': False}
    pending = db.execute("""SELECT r.id,r.created_at,
      EXISTS(SELECT 1 FROM studio_owner_notifications j WHERE j.reservation_id=r.id
        AND j.kind IN ('created','changed') AND j.state='accepted'
        AND j.created_at>=coalesce((SELECT max(c.created_at) FROM reservation_schedule_changes c WHERE c.reservation_id=r.id AND c.actor LIKE 'customer:%'),0)) OR
      EXISTS(SELECT 1 FROM studio_sms_jobs j JOIN studio_sms_bridges b ON b.id=j.bridge_id
        WHERE j.reservation_id=r.id AND b.role='owner_alert' AND (j.notification_key='created:'||r.id OR j.notification_key LIKE 'changed:'||r.id||':%')
        AND j.state IN ('sent','delivered')
        AND j.created_at>=coalesce((SELECT max(c.created_at) FROM reservation_schedule_changes c WHERE c.reservation_id=r.id AND c.actor LIKE 'customer:%'),0)) OR
      EXISTS(SELECT 1 FROM studio_owner_wechat_jobs j WHERE j.reservation_id=r.id AND j.state='accepted'
        AND j.created_at>=coalesce((SELECT max(c.created_at) FROM reservation_schedule_changes c WHERE c.reservation_id=r.id AND c.actor LIKE 'customer:%'),0)) AS acknowledged
      FROM studio_reservations r WHERE r.status='pending' AND r.deleted_at IS NULL ORDER BY r.created_at""").fetchall()
    needs_attention = []
    for row in pending:
        if row['acknowledged']:
            continue
        try:
            created = datetime.fromisoformat(row['created_at']).timestamp()
        except (ValueError, TypeError):
            created = 0
        if stamp-created >= 120:
            needs_attention.append(row['id'])
    continuous = sms['ready'] or serverchan['ready'] or tg_state['ready']
    degraded = any(c['enabled'] and not c['ready'] for c in (sms,serverchan,tg_state))
    return {'checked_at': stamp, 'level': 'critical' if not continuous or needs_attention else 'warning' if degraded else 'ready',
      'continuous_ready': bool(continuous), 'pending_count': len(pending),
      'unacknowledged_count': len(needs_attention), 'unacknowledged_ids': needs_attention[:20],
      'channels': {'sms': sms,'serverchan': serverchan,'telegram': tg_state,'wechat': wechat}}


def register(app, database, admin_actor):
    @app.get('/studio-api/manage/owner-delivery')
    def status(_actor=Depends(admin_actor)):
        with database() as db:
            db.execute('BEGIN')
            return snapshot(db)
