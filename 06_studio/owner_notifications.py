"""Independent owner notification channels sharing a transactional outbox.

No network requests run in the reservation transaction. Secrets are kept in a
0600 file beside the private database, never in responses, messages or logs.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import tempfile
import time
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, build_opener, HTTPRedirectHandler

from fastapi import Depends, HTTPException
from pydantic import BaseModel, ConfigDict, SecretStr

LOG = logging.getLogger(__name__)
KEY_PATTERN = re.compile(r"SCT[A-Za-z0-9]{12,196}\Z")
LEASE_SECONDS = 90
MAX_ATTEMPTS = 8
RETRY_SECONDS = (60, 300, 900, 3600, 14400, 43200, 43200, 43200)
COPY_PATH = Path(__file__).with_name('owner-notification-copy.json')
if not COPY_PATH.exists():
    COPY_PATH = Path(__file__).resolve().parents[1] / '05_studio/src/content/owner-notifications.json'


def initialize(database):
    with database() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS studio_owner_notification_settings (
          id INTEGER PRIMARY KEY CHECK(id=1), enabled INTEGER NOT NULL DEFAULT 0,
          daily_limit INTEGER NOT NULL DEFAULT 5, language TEXT NOT NULL DEFAULT 'zh',
          version INTEGER NOT NULL DEFAULT 1, blocked_until REAL NOT NULL DEFAULT 0
        );
        INSERT OR IGNORE INTO studio_owner_notification_settings(id) VALUES(1);
        CREATE TABLE IF NOT EXISTS studio_owner_notifications (
          id TEXT PRIMARY KEY, event_key TEXT NOT NULL UNIQUE, kind TEXT NOT NULL,
          reservation_id TEXT NOT NULL DEFAULT '', payload TEXT NOT NULL,
          state TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
          created_at REAL NOT NULL, updated_at REAL NOT NULL, next_attempt REAL NOT NULL,
          expires_at REAL NOT NULL, lease_until REAL NOT NULL DEFAULT 0,
          claim_token TEXT NOT NULL DEFAULT '', error TEXT NOT NULL DEFAULT '',
          provider_id TEXT NOT NULL DEFAULT ''
        );
        CREATE INDEX IF NOT EXISTS owner_notifications_due ON studio_owner_notifications(state,next_attempt);
        CREATE TABLE IF NOT EXISTS studio_owner_notification_attempts (
          id INTEGER PRIMARY KEY, notification_id TEXT NOT NULL, created_at REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS owner_notification_attempt_time ON studio_owner_notification_attempts(created_at);
        """)
        for table, name, definition in (
            ('studio_owner_notifications','channel',"TEXT NOT NULL DEFAULT 'serverchan'"),
            ('studio_owner_notifications','target',"TEXT NOT NULL DEFAULT ''"),
            ('studio_owner_notification_attempts','channel',"TEXT NOT NULL DEFAULT 'serverchan'"),
        ):
            if name not in {r[1] for r in db.execute('PRAGMA table_info('+table+')')}:
                db.execute('ALTER TABLE '+table+' ADD COLUMN '+name+' '+definition)
        db.execute('CREATE INDEX IF NOT EXISTS owner_channel_due ON studio_owner_notifications(channel,state,next_attempt)')
    import telegram_notifications
    telegram_notifications.initialize(database)


def secret_path(db):
    db_file = db.execute('PRAGMA database_list').fetchone()[2]
    return Path(db_file).with_name('serverchan-secret.json')


def read_key(db):
    path = secret_path(db)
    try:
        key = json.loads(path.read_text(encoding='utf-8')).get('sendkey', '') if path.exists() else os.getenv('STUDIO_SERVERCHAN_SENDKEY', '')
    except (OSError, ValueError, AttributeError):
        return ''
    return key if isinstance(key, str) and KEY_PATTERN.fullmatch(key) else ''


def write_key(db, key):
    path = secret_path(db)
    descriptor, temporary = tempfile.mkstemp(prefix='.serverchan-', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
            os.chmod(temporary, 0o600)
            json.dump({'sendkey': key}, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def settings_for(db):
    return dict(db.execute('SELECT * FROM studio_owner_notification_settings WHERE id=1').fetchone())


def enqueue(db, kind, row=None, *, event_key=None, channel='serverchan'):
    """Called inside the same transaction as the source event; no history replay."""
    stamp = time.time()
    settings, send_key = channel_settings(db, channel)
    reference = row['id'] if row else ''
    key = event_key or f"{kind}:{reference}:{row['version']}"
    if channel != 'serverchan':
        key = channel+':'+key
    existing = db.execute('SELECT * FROM studio_owner_notifications WHERE event_key=?', (key,)).fetchone()
    if existing:
        return dict(existing)
    payload = {}
    if row:
        source = json.loads(row['payload'])
        # Contact details, customer notes and owner-private notes stay in the desk.
        payload = {'name': source.get('name', ''), 'booking': source['booking']}
    enabled = settings['enabled'] and bool(send_key)
    state, error = ('queued', '') if enabled else ('skipped', 'not_enabled')
    ident = uuid.uuid4().hex
    db.execute('''INSERT INTO studio_owner_notifications
        (id,event_key,kind,reservation_id,payload,state,created_at,updated_at,next_attempt,expires_at,error,channel,target)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''',
        (ident, key, kind, reference, json.dumps(payload, ensure_ascii=False), state, stamp, stamp, stamp, stamp+86400, error, channel, settings.get('target','')))
    return dict(db.execute('SELECT * FROM studio_owner_notifications WHERE id=?', (ident,)).fetchone())


def channel_settings(db, channel):
    if channel == 'serverchan':
        return settings_for(db), read_key(db)
    if channel == 'telegram':
        import telegram_notifications as telegram
        settings = telegram.settings_for(db)
        settings.update(daily_limit=10000, target=str(settings['bot_id'])+':'+settings['chat_id'])
        return settings, telegram.read_token(db) if settings['chat_id'] else ''
    raise ValueError('Unknown owner notification channel')


def enqueue_reservation(db, kind, row):
    enqueue(db, kind, row)
    settings, key = channel_settings(db, 'telegram')
    if settings['enabled'] and key:
        enqueue(db, kind, row, channel='telegram')
    import sms_inbox
    sms_inbox.on_reservation(db, kind, row)
    import owner_wechat
    owner_wechat.on_reservation(db, kind, row)
    import customer_notifications
    customer_notifications.on_reservation(db,kind,row)


def safe_text(value):
    value = re.sub(r'[\x00-\x1f\x7f]', ' ', str(value))[:100]
    return re.sub(r'([\\`*_{}\[\]()<>#+.!|~-])', r'\\\1', value)


def render_message(job, language):
    copy = json.loads(COPY_PATH.read_text(encoding='utf-8'))
    lang = 1 if language == 'en' else 0
    title = copy['message_'+job['kind']][lang]
    lines = [title, '']
    if job['reservation_id']:
        data = json.loads(job['payload'])
        booking = data['booking']
        if booking.get('plan') == 'patch':
            lines.append(copy['message_patch'][lang])
        title += f" · {booking['date'][5:]} {booking['start']} · {booking['guests']} " + copy['message_guests_unit'][lang]
        for label, value in (
            ('message_name', data['name']), ('message_time', f"{booking['date']} {booking['start']}–{booking['end']}"),
            ('message_guests', booking['guests']), ('message_reference', job['reservation_id']),
        ):
            lines.append(f"**{copy[label][lang]}**: {safe_text(value)}")
        lines.extend(['', copy['message_timezone'][lang]])
    else:
        lines.append(copy['message_test_body'][lang])
    lines.extend(['', f"[{copy['message_open'][lang]}](https://pindoupuppy.com/manage?view=reservations)"])
    return title[:100], '\n\n'.join(lines)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def deliver(sendkey, title, body):
    """Accepted means provider acknowledgement, not a WeChat delivery receipt."""
    if not KEY_PATTERN.fullmatch(sendkey):
        return {'ok': False, 'error': 'key_invalid', 'retry': False}
    request = Request('https://sctapi.ftqq.com/'+sendkey+'.send',
                      data=urlencode({'title': title, 'desp': body}).encode(),
                      headers={'Content-Type': 'application/x-www-form-urlencoded', 'User-Agent': 'PinDouStudio/1.0'}, method='POST')
    try:
        with build_opener(NoRedirect()).open(request, timeout=12) as response:
            result = json.loads(response.read(65536))
        if not isinstance(result, dict):
            raise ValueError('Invalid response')
        data = result.get('data') or {}
        if result.get('code') == 0 and isinstance(data, dict) and data.get('errno', 0) == 0:
            return {'ok': True, 'provider_id': str(data.get('pushid', ''))[:120]}
        code = result.get('code')
        # Provider text can contain secrets or request data: keep only fixed codes.
        if code == 429:
            return {'ok': False, 'error': 'provider_quota', 'retry': True, 'delay': 86400}
        return {'ok': False, 'error': 'provider_rejected', 'retry': False}
    except HTTPError as exc:
        if exc.code == 429:
            return {'ok': False, 'error': 'provider_quota', 'retry': True, 'delay': 86400}
        return {'ok': False, 'error': 'provider_unavailable' if exc.code >= 500 else 'provider_rejected', 'retry': exc.code >= 500}
    except (URLError, TimeoutError, OSError, ValueError):
        return {'ok': False, 'error': 'network_error', 'retry': True}


def public_job(row):
    return {k: row[k] for k in ('id', 'kind', 'reservation_id', 'state', 'attempts', 'created_at', 'updated_at', 'next_attempt', 'error')}


def obsolete(db, job):
    if not job['reservation_id']:
        return False
    row = db.execute('SELECT status,deleted_at FROM studio_reservations WHERE id=?', (job['reservation_id'],)).fetchone()
    return not row or row['deleted_at'] or row['status'] != ('pending' if job['kind'] == 'created' else 'cancelled')


def process_one(database, channel='serverchan'):
    current = time.time()
    with database() as db:
        db.execute('BEGIN IMMEDIATE')
        if channel == 'serverchan':
            import owner_delivery
            owner_delivery.keep_pending_alerts(db, current)
        settings, key = channel_settings(db, channel)
        db.execute("UPDATE studio_owner_notifications SET state='expired',error='expired',updated_at=? WHERE channel=? AND state IN ('queued','retry','sending') AND expires_at<=? AND lease_until<=?", (current, channel, current, current))
        if not settings['enabled'] or not key or settings['blocked_until'] > current:
            return False
        row = db.execute("""SELECT * FROM studio_owner_notifications WHERE channel=? AND expires_at>? AND
            ((state IN ('queued','retry') AND next_attempt<=?) OR (state='sending' AND lease_until<=?))
            ORDER BY created_at,id LIMIT 1""", (channel, current, current, current)).fetchone()
        if not row:
            return False
        job = dict(row)
        if obsolete(db, job) or job['target'] != settings.get('target',''):
            db.execute("UPDATE studio_owner_notifications SET state='skipped',error='superseded',updated_at=?,lease_until=0 WHERE id=?", (current, job['id']))
            return True
        persistent = job['kind'] == 'created'
        if job['attempts'] >= MAX_ATTEMPTS and not persistent:
            db.execute("UPDATE studio_owner_notifications SET state='failed',error='retry_exhausted',updated_at=?,lease_until=0 WHERE id=?", (current, job['id']))
            return True
        # Rolling windows also cover restarts and avoid assuming a provider timezone.
        timestamps = [r[0] for r in db.execute('SELECT created_at FROM studio_owner_notification_attempts WHERE channel=? AND created_at>? ORDER BY created_at', (channel,current-86400))]
        recent = [t for t in timestamps if t > current-60]
        deferred = max(timestamps[-settings['daily_limit']]+86401 if len(timestamps) >= settings['daily_limit'] else 0,
                       recent[-30]+61 if len(recent) >= 30 else 0,
                       timestamps[-1]+1.1 if channel=='telegram' and timestamps else 0)
        if deferred > current:
            db.execute("UPDATE studio_owner_notifications SET state='retry',next_attempt=?,error='local_quota',lease_until=0,updated_at=? WHERE id=?", (deferred, current, job['id']))
            return False
        token = uuid.uuid4().hex
        db.execute("UPDATE studio_owner_notifications SET state='sending',attempts=attempts+1,lease_until=?,claim_token=?,updated_at=?,error='' WHERE id=?", (current+LEASE_SECONDS, token, current, job['id']))
        db.execute('INSERT INTO studio_owner_notification_attempts(notification_id,created_at,channel) VALUES(?,?,?)', (job['id'], current,channel))
        db.execute('DELETE FROM studio_owner_notification_attempts WHERE created_at<?', (current-172800,))
    try:
        if channel == 'telegram':
            import telegram_notifications
            outcome = telegram_notifications.deliver(key, settings['chat_id'], job, settings['language'])
        else:
            title, body = render_message(job, settings['language'])
            outcome = deliver(key, title, body)
    except Exception:
        # No exception/URL logging here: the provider's URL contains the SendKey.
        outcome = {'ok': False, 'error': 'worker_error', 'retry': True}
    finished = time.time()
    attempt = job['attempts']+1
    state = 'accepted' if outcome['ok'] else ('retry' if outcome.get('retry') and (persistent or attempt < MAX_ATTEMPTS) else 'failed')
    delay = outcome.get('delay', RETRY_SECONDS[min(attempt-1, len(RETRY_SECONDS)-1)])
    with database() as db:
        db.execute('BEGIN IMMEDIATE')
        db.execute('''UPDATE studio_owner_notifications SET state=?,updated_at=?,next_attempt=?,lease_until=0,
            error=?,provider_id=? WHERE id=? AND state='sending' AND claim_token=?''',
            (state, finished, finished+delay, outcome.get('error', ''), outcome.get('provider_id', ''), job['id'], token))
        if outcome.get('error') in ('provider_quota','telegram_rate_limit'):
            table = 'studio_telegram_settings' if channel=='telegram' else 'studio_owner_notification_settings'
            db.execute('UPDATE '+table+' SET blocked_until=MAX(blocked_until,?) WHERE id=1', (finished+delay,))
    return True


async def worker(database, channel='serverchan'):
    while True:
        try:
            await asyncio.to_thread(process_one, database, channel)
        except Exception:
            LOG.warning('Owner notification worker will retry after an internal error')
        await asyncio.sleep(3)


class NotificationSettings(BaseModel):
    model_config = ConfigDict(extra='forbid')
    version: int
    enabled: bool
    daily_limit: int = 5
    language: str = 'zh'
    sendkey: SecretStr | None = None


class TestRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    request_id: uuid.UUID


def register(app, database, admin_actor):
    @app.get('/studio-api/manage/owner-notifications')
    def status(_actor=Depends(admin_actor)):
        with database() as db:
            settings = settings_for(db)
            key = read_key(db)
            rows = db.execute("SELECT * FROM studio_owner_notifications WHERE channel='serverchan' ORDER BY created_at DESC,id DESC LIMIT 30").fetchall()
            used = db.execute("SELECT count(*) FROM studio_owner_notification_attempts WHERE channel='serverchan' AND created_at>?", (time.time()-86400,)).fetchone()[0]
        return {**settings, 'configured': bool(key), 'key_fingerprint': hashlib.sha256(key.encode()).hexdigest()[:8] if key else '',
                'used': used, 'items': [public_job(r) for r in rows]}

    @app.put('/studio-api/manage/owner-notifications')
    def configure(payload: NotificationSettings, _actor=Depends(admin_actor)):
        if payload.daily_limit not in (5, 1000) or payload.language not in ('zh', 'en'):
            raise HTTPException(422, 'notification_settings_invalid')
        key = payload.sendkey.get_secret_value().strip() if payload.sendkey else ''
        if key and not KEY_PATTERN.fullmatch(key):
            raise HTTPException(422, 'notification_key_invalid')
        with database() as db:
            db.execute('BEGIN IMMEDIATE')
            current = settings_for(db)
            if current['version'] != payload.version:
                raise HTTPException(409, 'version_conflict')
            if payload.enabled and not (key or read_key(db)):
                raise HTTPException(409, 'notification_not_configured')
            if key:
                write_key(db, key)
            db.execute('''UPDATE studio_owner_notification_settings SET enabled=?,daily_limit=?,language=?,version=version+1,
                blocked_until=CASE WHEN ? THEN 0 ELSE blocked_until END WHERE id=1''',
                (payload.enabled, payload.daily_limit, payload.language, bool(key)))
        return status(_actor)

    @app.post('/studio-api/manage/owner-notifications/test', status_code=202)
    def test_message(payload: TestRequest, _actor=Depends(admin_actor)):
        with database() as db:
            db.execute('BEGIN IMMEDIATE')
            if not settings_for(db)['enabled'] or not read_key(db):
                raise HTTPException(409, 'notification_not_configured')
            recent = db.execute("SELECT count(*) FROM studio_owner_notifications WHERE channel='serverchan' AND kind='test' AND created_at>?", (time.time()-3600,)).fetchone()[0]
            event_key = 'test:'+str(payload.request_id)
            replay = db.execute('SELECT * FROM studio_owner_notifications WHERE event_key=?', (event_key,)).fetchone()
            if replay:
                return public_job(replay)
            if recent >= 3:
                raise HTTPException(429, 'notification_test_limit')
            return public_job(enqueue(db, 'test', event_key=event_key))

    @app.post('/studio-api/manage/owner-notifications/{ident}/retry')
    def retry_message(ident: str, _actor=Depends(admin_actor)):
        with database() as db:
            db.execute('BEGIN IMMEDIATE')
            if not settings_for(db)['enabled'] or not read_key(db):
                raise HTTPException(409, 'notification_not_configured')
            row = db.execute("SELECT * FROM studio_owner_notifications WHERE id=? AND channel='serverchan'", (ident,)).fetchone()
            if not row:
                raise HTTPException(404, 'notification_not_found')
            if row['state'] in ('queued', 'retry', 'sending'):
                return public_job(row)
            persistent = row['kind'] == 'created' and not obsolete(db, row)
            if row['state'] != 'failed' or (not persistent and (row['expires_at'] <= time.time() or row['attempts'] >= MAX_ATTEMPTS)):
                raise HTTPException(409, 'notification_not_retryable')
            db.execute("UPDATE studio_owner_notifications SET state='queued',next_attempt=?,updated_at=? WHERE id=?", (time.time(), time.time(), ident))
            return public_job(db.execute('SELECT * FROM studio_owner_notifications WHERE id=?', (ident,)).fetchone())
