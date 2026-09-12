"""Studio-only administrators, attached to verified shared account identities."""
import json
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import Depends, HTTPException, Request

import customer_auth
import miniapp_login

_database = None


def initialize(database):
    with database() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS studio_staff_accounts (
          user_id TEXT PRIMARY KEY, role TEXT NOT NULL CHECK(role='admin'),
          enabled INTEGER NOT NULL DEFAULT 1, label TEXT NOT NULL DEFAULT '',
          created_at REAL NOT NULL, updated_at REAL NOT NULL, actor TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS studio_staff_events (
          id INTEGER PRIMARY KEY, user_id TEXT NOT NULL, actor TEXT NOT NULL,
          action TEXT NOT NULL, created_at REAL NOT NULL
        );
        """)


def staff(database, user_id):
    with database() as db:
        row = db.execute("SELECT user_id,label FROM studio_staff_accounts WHERE user_id=? AND enabled=1 AND role='admin'", (user_id,)).fetchone()
        return dict(row) if row else None


def native_actor(database, request):
    with database() as db:
        ticket = miniapp_login.ticket_for(db, request)
        row = db.execute("""SELECT s.user_id FROM studio_staff_accounts s JOIN studio_miniapp_identities i
          ON i.user_id=s.user_id WHERE i.app_id=? AND i.openid=? AND s.enabled=1 AND s.role='admin'""",
          (ticket['app_id'], ticket['openid'])).fetchone()
    if not row:
        raise HTTPException(403, 'studio_admin_required')
    return 'studio:' + row['user_id']


def customer_actor(database, request, authorization):
    customer = customer_auth.public_user(customer_auth.upstream('profile', request, token=authorization[7:]))
    if not staff(database, customer['id']):
        raise HTTPException(401, 'Administrator sign-in required')
    return 'studio:' + customer['id']


def is_admin(user_id):
    return bool(_database and staff(_database, user_id))


def register(app, database, admin_actor):
    global _database
    _database = database

    @app.get('/studio-api/auth/admin-access')
    def access(customer=Depends(customer_auth.require_customer)):
        return {'admin': is_admin(customer['id'])}

    @app.get('/studio-api/manage/session')
    def session(actor=Depends(admin_actor)):
        return {'admin': True, 'actor': actor}

    @app.get('/studio-api/manage/desk-summary')
    def summary(_actor=Depends(admin_actor)):
        import studio_finance
        today = datetime.now(ZoneInfo('America/Toronto')).date().isoformat()
        with database() as db:
            db.execute('BEGIN')
            pending = db.execute("SELECT count(*) FROM studio_reservations WHERE status='pending' AND deleted_at IS NULL").fetchone()[0]
            visits = db.execute("SELECT count(*) FROM studio_reservations WHERE deleted_at IS NULL AND status IN ('confirmed','completed') AND json_extract(payload,'$.booking.date')=?", (today,)).fetchone()[0]
            unread = db.execute("""SELECT count(*) FROM studio_sms_messages m JOIN studio_sms_threads t ON t.id=m.thread_id
              WHERE t.enabled=1 AND m.direction='inbound' AND m.seq>t.read_seq""").fetchone()[0]
            money = studio_finance.summary(db, today[:7]+'-01', today)
            import studio_messages
            unread+=studio_messages.unread_count(db)
        return {'today': today, 'pending': pending, 'visits': visits, 'unread': unread, 'finance': money}
