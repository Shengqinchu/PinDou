"""Reservation-linked SMS/iMessage inbox and a pull-based Mac transport.

The Mac owns transport and message decoding (imsg). This module owns business
authorization, selected contacts, unread state and durable dispatch. Nothing
in a customer request can read the Mac's unrelated conversations.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import math
import re
import secrets
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Annotated, Literal

from fastapi import Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field

BRIDGE_IDS = {"customer": "studio-customer", "owner_alert": "owner-alert"}
LEASE_SECONDS = 45
COPY_PATH = Path(__file__).with_name("messaging-copy.json")
if not COPY_PATH.exists():
    COPY_PATH = Path(__file__).resolve().parents[1] / "05_studio/src/content/messaging.json"


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def phone(value):
    """Canonicalize the explicitly supported NANP range, without identity claims."""
    value = re.sub(r"[\s().-]", "", str(value))
    if re.fullmatch(r"[2-9]\d{2}[2-9]\d{6}", value):
        value = "+1" + value
    elif re.fullmatch(r"1[2-9]\d{2}[2-9]\d{6}", value):
        value = "+" + value
    if not re.fullmatch(r"\+1[2-9]\d{2}[2-9]\d{6}", value):
        raise HTTPException(422, "sms_invalid_number")
    return value


def initialize(database):
    with database() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS studio_sms_bridges (
          id TEXT PRIMARY KEY, role TEXT NOT NULL UNIQUE, token_hash TEXT NOT NULL,
          sender TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 0,
          send_enabled INTEGER NOT NULL DEFAULT 0, last_seen REAL NOT NULL DEFAULT 0,
          health TEXT NOT NULL DEFAULT '{}', created_at REAL NOT NULL
        );
        CREATE UNIQUE INDEX IF NOT EXISTS sms_bridge_token ON studio_sms_bridges(token_hash);
        CREATE TABLE IF NOT EXISTS studio_sms_settings (
          id INTEGER PRIMARY KEY CHECK(id=1), owner_enabled INTEGER NOT NULL DEFAULT 0,
          owner_phone TEXT NOT NULL DEFAULT '', language TEXT NOT NULL DEFAULT 'zh',
          version INTEGER NOT NULL DEFAULT 1
        );
        INSERT OR IGNORE INTO studio_sms_settings(id) VALUES(1);
        CREATE TABLE IF NOT EXISTS studio_sms_threads (
          id TEXT PRIMARY KEY, phone TEXT NOT NULL UNIQUE, name TEXT NOT NULL DEFAULT '',
          created_at REAL NOT NULL, sync_since REAL NOT NULL, updated_at REAL NOT NULL,
          status TEXT NOT NULL DEFAULT 'open', last_seq INTEGER NOT NULL DEFAULT 0,
          read_seq INTEGER NOT NULL DEFAULT 0, enabled INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS studio_sms_thread_reservations (
          thread_id TEXT NOT NULL, reservation_id TEXT NOT NULL,
          PRIMARY KEY(thread_id,reservation_id)
        );
        CREATE TABLE IF NOT EXISTS studio_sms_messages (
          seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT NOT NULL UNIQUE,
          thread_id TEXT NOT NULL, bridge_id TEXT NOT NULL, external_id TEXT,
          direction TEXT NOT NULL, source TEXT NOT NULL, channel TEXT NOT NULL,
          content TEXT NOT NULL, created_at REAL NOT NULL, state TEXT NOT NULL,
          error TEXT NOT NULL DEFAULT '', actor TEXT NOT NULL DEFAULT '',
          UNIQUE(bridge_id,external_id)
        );
        CREATE INDEX IF NOT EXISTS sms_thread_messages ON studio_sms_messages(thread_id,seq);
        CREATE TABLE IF NOT EXISTS studio_sms_jobs (
          id TEXT PRIMARY KEY, bridge_id TEXT NOT NULL, message_id TEXT,
          notification_key TEXT UNIQUE, reservation_id TEXT NOT NULL DEFAULT '',
          recipient TEXT NOT NULL, content TEXT NOT NULL, request_key TEXT NOT NULL UNIQUE,
          payload_hash TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'queued',
          created_at REAL NOT NULL, expires_at REAL NOT NULL, lease_until REAL NOT NULL DEFAULT 0,
          claim_token TEXT NOT NULL DEFAULT '', started_at REAL NOT NULL DEFAULT 0,
          finished_at REAL NOT NULL DEFAULT 0, result_hash TEXT NOT NULL DEFAULT '',
          external_id TEXT NOT NULL DEFAULT '', error TEXT NOT NULL DEFAULT ''
        );
        CREATE INDEX IF NOT EXISTS sms_jobs_due ON studio_sms_jobs(bridge_id,state,created_at);
        """)


def configure_bridge(database, *, role, sender, token, enabled=False, send_enabled=False):
    """Private deployment entrypoint. HTTP callers cannot choose bridge credentials."""
    if role not in BRIDGE_IDS or not re.fullmatch(r"[A-Za-z0-9_-]{43,128}", token):
        raise ValueError("invalid_private_bridge_configuration")
    sender = phone(sender)
    with database() as db:
        db.execute("BEGIN IMMEDIATE")
        existing = db.execute("SELECT sender FROM studio_sms_bridges WHERE role=?", (role,)).fetchone()
        if existing and existing["sender"] != sender:
            active = db.execute("SELECT 1 FROM studio_sms_jobs WHERE bridge_id=? AND state IN ('queued','claimed','dispatching') LIMIT 1", (BRIDGE_IDS[role],)).fetchone()
            if active:
                raise ValueError("pending_jobs_prevent_sender_change")
        db.execute("""INSERT INTO studio_sms_bridges(id,role,token_hash,sender,enabled,send_enabled,created_at)
          VALUES(?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET token_hash=excluded.token_hash,
          sender=excluded.sender,enabled=excluded.enabled,send_enabled=excluded.send_enabled""",
          (BRIDGE_IDS[role], role, digest(token), sender, int(enabled), int(send_enabled), time.time()))


def ensure_thread(db, number, name="", *, reservation_id="", since=None):
    number = phone(number)
    existing = db.execute("SELECT * FROM studio_sms_threads WHERE phone=?", (number,)).fetchone()
    if existing:
        ident = existing["id"]
    else:
        ident, stamp = uuid.uuid4().hex, time.time()
        # Creating an inbox never silently imports a person's old conversation.
        db.execute("INSERT INTO studio_sms_threads(id,phone,name,created_at,sync_since,updated_at) VALUES(?,?,?,?,?,?)",
                   (ident, number, str(name).strip()[:80], stamp, stamp if since is None else since, stamp))
    if reservation_id:
        db.execute("INSERT OR IGNORE INTO studio_sms_thread_reservations VALUES(?,?)", (ident, reservation_id))
    return db.execute("SELECT * FROM studio_sms_threads WHERE id=?", (ident,)).fetchone()


def on_reservation(db, kind, row):
    if kind != "created":
        return
    value = json.loads(row["payload"])
    if value.get("contact_method") == "phone":
        try:
            ensure_thread(db, value.get("contact", ""), value.get("name", ""), reservation_id=row["id"])
        except HTTPException:
            # A saved contact can be outside the supported SMS range.
            pass
    settings = db.execute("SELECT * FROM studio_sms_settings WHERE id=1").fetchone()
    if not settings or not settings["owner_enabled"] or not settings["owner_phone"]:
        return
    bridge = db.execute("SELECT * FROM studio_sms_bridges WHERE role='owner_alert' AND enabled=1").fetchone()
    if not bridge:
        return
    booking = value["booking"]
    name = re.sub(r"[\x00-\x1f\x7f]", " ", value.get("name", ""))[:30]
    copy = json.loads(COPY_PATH.read_text(encoding="utf-8"))
    body = copy["owner_sms"][1 if settings["language"] == "en" else 0].format(name=name, **booking)
    queue_job(db, bridge["id"], settings["owner_phone"], body,
              request_key="owner-created:" + row["id"], reservation_id=row["id"], notification_key="created:" + row["id"])


def queue_job(db, bridge_id, number, content, *, request_key, message_id=None, reservation_id="", notification_key=None):
    payload_hash = digest(json.dumps([bridge_id, number, content, message_id, reservation_id], ensure_ascii=False))
    existing = db.execute("SELECT * FROM studio_sms_jobs WHERE request_key=?", (request_key,)).fetchone()
    if existing:
        if existing["payload_hash"] != payload_hash:
            raise HTTPException(409, "sms_request_changed")
        return existing
    ident, stamp = uuid.uuid4().hex, time.time()
    db.execute("""INSERT INTO studio_sms_jobs(id,bridge_id,message_id,notification_key,reservation_id,
      recipient,content,request_key,payload_hash,created_at,expires_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
      (ident, bridge_id, message_id, notification_key, reservation_id, number, content, request_key, payload_hash, stamp, stamp + 86400))
    return db.execute("SELECT * FROM studio_sms_jobs WHERE id=?", (ident,)).fetchone()


def public_bridge(row):
    if not row:
        return None
    health = json.loads(row["health"])
    return {"id": row["id"], "role": row["role"], "sender": row["sender"], "enabled": bool(row["enabled"]),
            "send_enabled": bool(row["send_enabled"]), "online": row["last_seen"] > time.time() - 90,
            "last_seen": row["last_seen"], "health": health}


def public_message(row):
    return {key: row[key] for key in ("seq", "id", "thread_id", "direction", "source", "channel", "content", "created_at", "state", "error")}


def thread_summary(db, row):
    latest = db.execute("SELECT content,created_at,direction FROM studio_sms_messages WHERE thread_id=? ORDER BY seq DESC LIMIT 1", (row["id"],)).fetchone()
    unread = db.execute("SELECT count(*) FROM studio_sms_messages WHERE thread_id=? AND seq>? AND direction='inbound'", (row["id"], row["read_seq"])).fetchone()[0]
    refs = db.execute("""SELECT r.id,r.status,r.payload FROM studio_reservations r
      JOIN studio_sms_thread_reservations l ON l.reservation_id=r.id WHERE l.thread_id=? ORDER BY r.created_at DESC LIMIT 20""", (row["id"],)).fetchall()
    reservations = []
    for ref in refs:
        value = json.loads(ref["payload"])
        reservations.append({"id": ref["id"], "status": ref["status"], "name": value.get("name", ""), "booking": value["booking"]})
    return {"id": row["id"], "phone": row["phone"], "name": row["name"], "status": row["status"],
            "enabled": bool(row["enabled"]), "unread": unread, "last_seq": row["last_seq"],
            "latest": dict(latest) if latest else None, "reservations": reservations}


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ThreadCreate(Strict):
    phone: str = Field(default="", max_length=40)
    name: str = Field(default="", max_length=80)
    reservation_id: str = Field(default="", max_length=64)


class MessageSend(Strict):
    request_id: uuid.UUID
    content: str = Field(min_length=1, max_length=2000)


class ReadProgress(Strict):
    through_seq: int = Field(ge=0)


class ThreadUpdate(Strict):
    status: Literal["open", "closed"]


class SmsSettings(Strict):
    version: int = Field(ge=1)
    owner_enabled: bool
    owner_phone: str = Field(max_length=40)
    language: Literal["zh", "en"] = "zh"


class Heartbeat(Strict):
    readable: bool = False
    automation: bool = False
    sender: str = Field(max_length=40)
    version: str = Field(max_length=40)
    error: Literal["", "permission_required", "account_unavailable", "transport_unavailable", "sender_mismatch"] = ""


class Claim(Strict):
    claim_token: str = Field(min_length=32, max_length=80)


class JobResult(Claim):
    state: Literal["submitted", "failed", "unknown", "skipped"]
    external_id: str = Field(default="", max_length=160)
    error: Literal["", "permission_required", "account_unavailable", "transport_unavailable", "send_rejected", "send_timeout", "interrupted", "sender_mismatch", "conversation_unavailable"] = ""


class JobObservation(Claim):
    external_id: str = Field(min_length=1, max_length=160)
    sender: str = Field(max_length=40)
    channel: Literal["SMS", "iMessage", "RCS"] = "SMS"
    state: Literal["sent", "delivered", "failed"]


class IncomingMessage(Strict):
    thread_id: str = Field(max_length=64)
    external_id: str = Field(min_length=1, max_length=160)
    phone: str = Field(max_length=40)
    direction: Literal["inbound", "outbound"]
    channel: Literal["SMS", "iMessage", "RCS"]
    content: str = Field(min_length=1, max_length=4000)
    timestamp: float = Field(gt=0)
    sent: bool = False
    delivered: bool = False
    error: bool = False
    job_id: str = Field(default="", max_length=64)


class MessageBatch(Strict):
    messages: list[IncomingMessage] = Field(max_length=10)


def ingest(db, bridge, item):
    if bridge["role"] != "customer":
        raise HTTPException(403, "sms_bridge_scope_invalid")
    thread = db.execute("SELECT * FROM studio_sms_threads WHERE id=? AND enabled=1", (item.thread_id,)).fetchone()
    if not thread or thread["phone"] != phone(item.phone) or item.timestamp < thread["sync_since"] or item.timestamp > time.time() + 300:
        raise HTTPException(422, "sms_message_scope_invalid")
    existing = db.execute("SELECT * FROM studio_sms_messages WHERE bridge_id=? AND external_id=?", (bridge["id"], item.external_id)).fetchone()
    if existing and (existing["thread_id"] != thread["id"] or existing["direction"] != item.direction or existing["content"] != item.content):
        raise HTTPException(409, "sms_external_message_conflict")
    state = "received" if item.direction == "inbound" else "failed" if item.error else "delivered" if item.delivered else "sent" if item.sent else "submitted"
    if existing:
        # Delivery updates do not increment unread or make duplicate bubbles.
        if existing["state"] != "delivered" or state == "delivered":
            db.execute("UPDATE studio_sms_messages SET state=? WHERE id=?", (state, existing["id"]))
        return existing["id"]
    matched = None
    if item.direction == "outbound" and item.job_id:
        job = db.execute("SELECT * FROM studio_sms_jobs WHERE id=? AND bridge_id=?", (item.job_id, bridge["id"])).fetchone()
        if not job or job["recipient"] != thread["phone"] or job["content"] != item.content or not job["started_at"] or item.timestamp < job["started_at"] - 3:
            raise HTTPException(422, "sms_echo_invalid")
        if job["message_id"]:
            matched = db.execute("SELECT * FROM studio_sms_messages WHERE id=? AND thread_id=?", (job["message_id"], thread["id"])).fetchone()
    if matched:
        if matched["external_id"] and matched["external_id"] != item.external_id:
            raise HTTPException(409, "sms_echo_invalid")
        db.execute("UPDATE studio_sms_messages SET external_id=?,channel=?,state=?,created_at=?,error='' WHERE id=?",
                   (item.external_id, item.channel, state, item.timestamp, matched["id"]))
        return matched["id"]
    ident = uuid.uuid4().hex
    cur = db.execute("""INSERT INTO studio_sms_messages(id,thread_id,bridge_id,external_id,direction,source,channel,content,created_at,state)
      VALUES(?,?,?,?,?,?,?,?,?,?)""", (ident, thread["id"], bridge["id"], item.external_id, item.direction, "phone", item.channel, item.content, item.timestamp, state))
    db.execute("UPDATE studio_sms_threads SET last_seq=?,updated_at=MAX(updated_at,?),status=CASE WHEN ?='inbound' THEN 'open' ELSE status END WHERE id=?",
               (cur.lastrowid, item.timestamp, item.direction, thread["id"]))
    return ident


def register(app, database, admin_actor):
    prefix = "/studio-api/manage/messages"

    def bridge_actor(authorization: Annotated[str | None, Header()] = None):
        token = authorization[7:] if authorization and authorization.startswith("Bearer ") else ""
        if not re.fullmatch(r"[A-Za-z0-9_-]{43,128}", token):
            raise HTTPException(401, "sms_bridge_auth_required")
        with database() as db:
            row = db.execute("SELECT * FROM studio_sms_bridges WHERE token_hash=? AND enabled=1", (digest(token),)).fetchone()
        if not row:
            raise HTTPException(401, "sms_bridge_auth_required")
        return dict(row)

    @app.get(prefix + "/settings")
    def settings(_actor=Depends(admin_actor)):
        with database() as db:
            value = dict(db.execute("SELECT * FROM studio_sms_settings WHERE id=1").fetchone())
            value["owner_enabled"] = bool(value["owner_enabled"])
            bridges = [public_bridge(r) for r in db.execute("SELECT * FROM studio_sms_bridges ORDER BY role")]
            jobs = db.execute("SELECT id,state,error,created_at,reservation_id FROM studio_sms_jobs WHERE notification_key IS NOT NULL ORDER BY created_at DESC LIMIT 20").fetchall()
        return {**value, "bridges": bridges, "notifications": [dict(r) for r in jobs]}

    @app.put(prefix + "/settings")
    def update_settings(payload: SmsSettings, _actor=Depends(admin_actor)):
        number = phone(payload.owner_phone) if payload.owner_phone else ""
        with database() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM studio_sms_settings WHERE id=1").fetchone()
            if row["version"] != payload.version:
                raise HTTPException(409, "version_conflict")
            bridge = db.execute("SELECT * FROM studio_sms_bridges WHERE role='owner_alert' AND enabled=1 AND send_enabled=1").fetchone()
            if payload.owner_enabled and (not number or not bridge or bridge["sender"] == number):
                raise HTTPException(409, "sms_owner_channel_required")
            db.execute("UPDATE studio_sms_settings SET owner_enabled=?,owner_phone=?,language=?,version=version+1 WHERE id=1",
                       (payload.owner_enabled, number, payload.language))
        return settings(_actor)

    @app.get(prefix + "/threads")
    def threads(query: str = "", unread: bool = False, limit: int = 50, cursor: str = "", _actor=Depends(admin_actor)):
        if len(query) > 80 or not 1 <= limit <= 100 or len(cursor) > 80:
            raise HTTPException(422, "sms_query_invalid")
        with database() as db:
            conditions, args = ["enabled=1"], []
            if query:
                conditions.append("(instr(lower(name),lower(?))>0 OR instr(phone,?)>0)")
                args.extend([query, query])
            if cursor:
                try:
                    stamp, ident = cursor.split(":")
                    stamp = float(stamp)
                    if not math.isfinite(stamp) or not re.fullmatch(r"[a-f0-9]{32}", ident):
                        raise ValueError()
                except ValueError:
                    raise HTTPException(422, "sms_query_invalid") from None
                conditions.append("(updated_at<? OR (updated_at=? AND id<?))")
                args.extend([stamp, stamp, ident])
            if unread:
                conditions.append("EXISTS(SELECT 1 FROM studio_sms_messages m WHERE m.thread_id=studio_sms_threads.id AND m.seq>studio_sms_threads.read_seq AND m.direction='inbound')")
            rows = db.execute("SELECT * FROM studio_sms_threads WHERE " + " AND ".join(conditions) + " ORDER BY updated_at DESC,id DESC LIMIT ?", (*args, limit + 1)).fetchall()
            more, rows = len(rows) > limit, rows[:limit]
            items = [thread_summary(db, r) for r in rows]
            bridge = db.execute("SELECT * FROM studio_sms_bridges WHERE role='customer'").fetchone()
        return {"items": items, "bridge": public_bridge(bridge), "next_cursor": f"{rows[-1]['updated_at']}:{rows[-1]['id']}" if more else ""}

    @app.post(prefix + "/threads", status_code=201)
    def create_thread(payload: ThreadCreate, _actor=Depends(admin_actor)):
        with database() as db:
            db.execute("BEGIN IMMEDIATE")
            number, name = payload.phone, payload.name
            if payload.reservation_id:
                reservation = db.execute("SELECT payload FROM studio_reservations WHERE id=? AND deleted_at IS NULL", (payload.reservation_id,)).fetchone()
                if not reservation:
                    raise HTTPException(404, "reservation_not_found")
                value = json.loads(reservation["payload"])
                if not number:
                    if value.get("contact_method") != "phone":
                        raise HTTPException(422, "sms_number_required")
                    number = value.get("contact", "")
                name = name or value.get("name", "")
            row = ensure_thread(db, number, name, reservation_id=payload.reservation_id)
            return thread_summary(db, row)

    @app.get(prefix + "/threads/{ident}")
    def detail(ident: str, before: int | None = None, limit: int = 50, _actor=Depends(admin_actor)):
        if not 1 <= limit <= 100 or (before is not None and before < 1):
            raise HTTPException(422, "sms_query_invalid")
        with database() as db:
            thread = db.execute("SELECT * FROM studio_sms_threads WHERE id=? AND enabled=1", (ident,)).fetchone()
            if not thread:
                raise HTTPException(404, "sms_thread_not_found")
            rows = db.execute("SELECT * FROM studio_sms_messages WHERE thread_id=? AND seq<? ORDER BY seq DESC LIMIT ?", (ident, before or 9223372036854775807, limit + 1)).fetchall()
            more = len(rows) > limit
            rows = rows[:limit]
            return {"thread": thread_summary(db, thread), "items": [public_message(r) for r in reversed(rows)], "has_more": more,
                    "next_before": rows[-1]["seq"] if more else None}

    @app.post(prefix + "/threads/{ident}/read")
    def mark_read(ident: str, payload: ReadProgress, _actor=Depends(admin_actor)):
        with database() as db:
            row = db.execute("SELECT * FROM studio_sms_threads WHERE id=?", (ident,)).fetchone()
            if not row:
                raise HTTPException(404, "sms_thread_not_found")
            if payload.through_seq and not db.execute("SELECT 1 FROM studio_sms_messages WHERE seq=? AND thread_id=?", (payload.through_seq, ident)).fetchone():
                raise HTTPException(422, "sms_read_cursor_invalid")
            db.execute("UPDATE studio_sms_threads SET read_seq=MAX(read_seq,?) WHERE id=?", (payload.through_seq, ident))
        return {"ok": True}

    @app.patch(prefix + "/threads/{ident}")
    @app.post(prefix + "/threads/{ident}/update")
    def update_thread(ident: str, payload: ThreadUpdate, _actor=Depends(admin_actor)):
        with database() as db:
            changed = db.execute("UPDATE studio_sms_threads SET status=? WHERE id=?", (payload.status, ident)).rowcount
            if not changed:
                raise HTTPException(404, "sms_thread_not_found")
        return {"ok": True}

    @app.post(prefix + "/threads/{ident}/messages", status_code=202)
    def send_message(ident: str, payload: MessageSend, actor=Depends(admin_actor)):
        content = payload.content.strip()
        if not content or re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", content):
            raise HTTPException(422, "sms_content_invalid")
        key = "desk:" + str(payload.request_id)
        with database() as db:
            db.execute("BEGIN IMMEDIATE")
            thread = db.execute("SELECT * FROM studio_sms_threads WHERE id=? AND enabled=1", (ident,)).fetchone()
            if not thread:
                raise HTTPException(404, "sms_thread_not_found")
            old = db.execute("SELECT * FROM studio_sms_jobs WHERE request_key=?", (key,)).fetchone()
            if old:
                message = db.execute("SELECT * FROM studio_sms_messages WHERE id=?", (old["message_id"],)).fetchone()
                if not message or message["thread_id"] != ident or old["content"] != content:
                    raise HTTPException(409, "sms_request_changed")
                return public_message(message)
            bridge = db.execute("SELECT * FROM studio_sms_bridges WHERE role='customer' AND enabled=1 AND send_enabled=1").fetchone()
            if not bridge:
                raise HTTPException(409, "sms_bridge_not_ready")
            count = db.execute("SELECT count(*) FROM studio_sms_jobs WHERE bridge_id=? AND created_at>?", (bridge["id"], time.time() - 60)).fetchone()[0]
            if count >= 20:
                raise HTTPException(429, "sms_send_rate_limit")
            mid, stamp = uuid.uuid4().hex, time.time()
            cur = db.execute("""INSERT INTO studio_sms_messages(id,thread_id,bridge_id,direction,source,channel,content,created_at,state,actor)
              VALUES(?,?,?,'outbound','desk','SMS',?,?,'queued',?)""", (mid, ident, bridge["id"], content, stamp, actor))
            queue_job(db, bridge["id"], thread["phone"], content, request_key=key, message_id=mid)
            db.execute("UPDATE studio_sms_threads SET last_seq=?,updated_at=? WHERE id=?", (cur.lastrowid, stamp, ident))
            return public_message(db.execute("SELECT * FROM studio_sms_messages WHERE id=?", (mid,)).fetchone())

    bridge_prefix = "/studio-api/message-bridge"

    @app.post(bridge_prefix + "/heartbeat")
    def heartbeat(payload: Heartbeat, bridge=Depends(bridge_actor)):
        if phone(payload.sender) != bridge["sender"]:
            raise HTTPException(409, "sms_sender_mismatch")
        with database() as db:
            db.execute("UPDATE studio_sms_bridges SET last_seen=?,health=? WHERE id=?", (time.time(), payload.model_dump_json(exclude={"sender"}), bridge["id"]))
        return {"ok": True}

    @app.get(bridge_prefix + "/contacts")
    def contacts(bridge=Depends(bridge_actor)):
        with database() as db:
            rows = db.execute("SELECT id,phone,sync_since FROM studio_sms_threads WHERE enabled=1 ORDER BY id").fetchall() if bridge["role"] == "customer" else []
        return {"role": bridge["role"], "sender": bridge["sender"], "send_enabled": bool(bridge["send_enabled"]), "items": [dict(r) for r in rows]}

    @app.post(bridge_prefix + "/messages")
    def receive(payload: MessageBatch, bridge=Depends(bridge_actor)):
        with database() as db:
            db.execute("BEGIN IMMEDIATE")
            identifiers = [ingest(db, bridge, item) for item in payload.messages]
        return {"ids": identifiers}

    @app.post(bridge_prefix + "/claim")
    def claim_job(bridge=Depends(bridge_actor)):
        if not bridge["send_enabled"]:
            return {"job": None}
        stamp = time.time()
        with database() as db:
            db.execute("BEGIN IMMEDIATE")
            # Unstarted leases may be reclaimed. A started send is never replayed.
            db.execute("UPDATE studio_sms_jobs SET state='queued',claim_token='' WHERE bridge_id=? AND state='claimed' AND lease_until<?", (bridge["id"], stamp))
            stale = db.execute("SELECT message_id FROM studio_sms_jobs WHERE bridge_id=? AND state='dispatching' AND lease_until<?", (bridge["id"], stamp)).fetchall()
            for row in stale:
                if row["message_id"]:
                    db.execute("UPDATE studio_sms_messages SET state='unknown',error='interrupted' WHERE id=? AND state NOT IN ('sent','delivered')", (row["message_id"],))
            db.execute("UPDATE studio_sms_jobs SET state='unknown',error='interrupted' WHERE bridge_id=? AND state='dispatching' AND lease_until<?", (bridge["id"], stamp))
            db.execute("UPDATE studio_sms_jobs SET state='skipped',error='expired' WHERE bridge_id=? AND state='queued' AND expires_at<=?", (bridge["id"], stamp))
            db.execute("UPDATE studio_sms_messages SET state='skipped',error='expired' WHERE id IN (SELECT message_id FROM studio_sms_jobs WHERE bridge_id=? AND state='skipped' AND error='expired') AND external_id IS NULL", (bridge["id"],))
            job = db.execute("SELECT * FROM studio_sms_jobs WHERE bridge_id=? AND state='queued' ORDER BY created_at,id LIMIT 1", (bridge["id"],)).fetchone()
            if not job:
                return {"job": None}
            import customer_notifications
            if not customer_notifications.valid_sms(db,job):
                db.execute("UPDATE studio_sms_jobs SET state='skipped',error='superseded' WHERE id=?",(job['id'],))
                if job['message_id']:db.execute("UPDATE studio_sms_messages SET state='skipped',error='superseded' WHERE id=?",(job['message_id'],))
                return {'job':None}
            if job["notification_key"]:
                reservation = db.execute("SELECT status,deleted_at FROM studio_reservations WHERE id=?", (job["reservation_id"],)).fetchone()
                current = db.execute("SELECT * FROM studio_sms_settings WHERE id=1").fetchone()
                if not reservation or reservation["status"] != "pending" or reservation["deleted_at"] or not current["owner_enabled"] or current["owner_phone"] != job["recipient"]:
                    db.execute("UPDATE studio_sms_jobs SET state='skipped',error='superseded' WHERE id=?", (job["id"],))
                    return {"job": None}
            token = secrets.token_urlsafe(32)
            db.execute("UPDATE studio_sms_jobs SET state='claimed',claim_token=?,lease_until=? WHERE id=?", (token, stamp + LEASE_SECONDS, job["id"]))
            return {"job": {"id": job["id"], "recipient": job["recipient"], "content": job["content"], "claim_token": token,
                            "expires_at": job["expires_at"], "message_id": job["message_id"], "sender": bridge["sender"]}}

    def owned_job(db, ident, token, bridge):
        row = db.execute("SELECT * FROM studio_sms_jobs WHERE id=? AND bridge_id=?", (ident, bridge["id"])).fetchone()
        if not row or not hmac.compare_digest(row["claim_token"], token):
            raise HTTPException(409, "sms_claim_invalid")
        return row

    @app.post(bridge_prefix + "/jobs/{ident}/begin")
    def begin(ident: str, payload: Claim, bridge=Depends(bridge_actor)):
        stamp = time.time()
        with database() as db:
            db.execute("BEGIN IMMEDIATE")
            job = owned_job(db, ident, payload.claim_token, bridge)
            if job["state"] != "claimed":
                return {"send": False, "state": job["state"]}
            current_bridge = db.execute("SELECT enabled,send_enabled FROM studio_sms_bridges WHERE id=?", (bridge["id"],)).fetchone()
            if not current_bridge["enabled"] or not current_bridge["send_enabled"] or job["lease_until"] < stamp or job["expires_at"] <= stamp:
                raise HTTPException(409, "sms_claim_expired")
            import customer_notifications
            if not customer_notifications.valid_sms(db,job):
                db.execute("UPDATE studio_sms_jobs SET state='skipped',error='superseded' WHERE id=?",(ident,))
                if job['message_id']:db.execute("UPDATE studio_sms_messages SET state='skipped',error='superseded' WHERE id=?",(job['message_id'],))
                return {'send':False,'state':'skipped'}
            if job["notification_key"]:
                reservation = db.execute("SELECT status,deleted_at FROM studio_reservations WHERE id=?", (job["reservation_id"],)).fetchone()
                current = db.execute("SELECT * FROM studio_sms_settings WHERE id=1").fetchone()
                if not reservation or reservation["status"] != "pending" or reservation["deleted_at"] or not current["owner_enabled"] or current["owner_phone"] != job["recipient"]:
                    db.execute("UPDATE studio_sms_jobs SET state='skipped',error='superseded' WHERE id=?", (ident,))
                    return {"send": False, "state": "skipped"}
            db.execute("UPDATE studio_sms_jobs SET state='dispatching',started_at=?,lease_until=? WHERE id=?", (stamp, stamp + 150, ident))
            if job["message_id"]:
                db.execute("UPDATE studio_sms_messages SET state='sending' WHERE id=?", (job["message_id"],))
        return {"send": True, "state": "dispatching"}

    @app.post(bridge_prefix + "/jobs/{ident}/result")
    def result(ident: str, payload: JobResult, bridge=Depends(bridge_actor)):
        result_hash = digest(payload.model_dump_json())
        with database() as db:
            db.execute("BEGIN IMMEDIATE")
            job = owned_job(db, ident, payload.claim_token, bridge)
            if job["result_hash"]:
                if job["result_hash"] != result_hash:
                    raise HTTPException(409, "sms_result_conflict")
                return {"ok": True}
            if not job["started_at"] or job["state"] not in ("dispatching", "unknown"):
                raise HTTPException(409, "sms_result_invalid")
            db.execute("UPDATE studio_sms_jobs SET state=?,finished_at=?,result_hash=?,external_id=?,error=? WHERE id=?",
                       (payload.state, time.time(), result_hash, payload.external_id, payload.error, ident))
            if job["message_id"]:
                db.execute("UPDATE studio_sms_messages SET state=?,error=? WHERE id=? AND external_id IS NULL",
                           (payload.state, payload.error, job["message_id"]))
        return {"ok": True}

    @app.post(bridge_prefix + "/jobs/{ident}/observation")
    def observe_job(ident: str, payload: JobObservation, bridge=Depends(bridge_actor)):
        if phone(payload.sender) != bridge["sender"]:
            raise HTTPException(409, "sms_sender_mismatch")
        with database() as db:
            db.execute("BEGIN IMMEDIATE")
            job = owned_job(db, ident, payload.claim_token, bridge)
            if not job["started_at"] or (job["external_id"] and job["external_id"] != payload.external_id):
                raise HTTPException(409, "sms_echo_invalid")
            state = "delivered" if job["state"] == "delivered" else payload.state
            db.execute("UPDATE studio_sms_jobs SET state=?,external_id=?,error=? WHERE id=?", (state, payload.external_id, "send_rejected" if state == "failed" else "", ident))
            # The ordinary ingest endpoint adds the channel and timestamp. Keeping
            # the draft row's external_id empty here allows that echo to merge.
            if job["message_id"]:
                db.execute("UPDATE studio_sms_messages SET state=?,channel=?,error=? WHERE id=?", (state, payload.channel, "send_rejected" if state == "failed" else "", job["message_id"]))
        return {"ok": True}
