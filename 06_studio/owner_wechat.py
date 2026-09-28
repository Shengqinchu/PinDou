"""Owner mini-program identity binding and one-time subscription notices.

Uses the existing WeChat client/credential cache. Permission comes from the
receiving WeChat identity, never from a phone number or a website nickname.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import secrets
import time
import uuid
from pathlib import Path
from typing import Literal

from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

import miniapp_login as miniapp

LOG = logging.getLogger(__name__)
TEMPLATE_KEYS = ("thing1", "time2", "time3", "thing4", "thing5")
# This caps our record of individual accepted subscriptions, not WeChat's
# upstream permission. Raising it never pre-fills or grants any send rights.
MAX_OWNER_GRANTS = 10_000
COPY_PATH = Path(__file__).with_name("owner-wechat-copy.json")
if not COPY_PATH.exists():
    COPY_PATH = Path(__file__).resolve().parents[1] / "05_studio/src/content/owner-wechat.json"


def key_hash(value):
    return hashlib.sha256(value.encode()).hexdigest()


def initialize(database):
    with database() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS studio_owner_wechat_settings (
          id INTEGER PRIMARY KEY CHECK(id=1), enabled INTEGER NOT NULL DEFAULT 0,
          template_id TEXT NOT NULL DEFAULT '', template_title TEXT NOT NULL DEFAULT '',
          version INTEGER NOT NULL DEFAULT 1
        );
        INSERT OR IGNORE INTO studio_owner_wechat_settings(id) VALUES(1);
        CREATE TABLE IF NOT EXISTS studio_owner_wechat_bindings (
          id TEXT PRIMARY KEY, app_id TEXT NOT NULL, openid TEXT NOT NULL,
          label TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 1,
          grants INTEGER NOT NULL DEFAULT 0, created_at REAL NOT NULL, actor TEXT NOT NULL,
          last_sent_at REAL NOT NULL DEFAULT 0, error TEXT NOT NULL DEFAULT '',
          UNIQUE(app_id,openid)
        );
        CREATE TABLE IF NOT EXISTS studio_owner_wechat_bind_tokens (
          token_hash TEXT PRIMARY KEY, app_id TEXT NOT NULL, actor TEXT NOT NULL,
          label TEXT NOT NULL, created_at REAL NOT NULL, expires_at REAL NOT NULL,
          consumed_at REAL NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS studio_owner_wechat_subscriptions (
          nonce_hash TEXT PRIMARY KEY, binding_id TEXT NOT NULL, template_id TEXT NOT NULL,
          created_at REAL NOT NULL, expires_at REAL NOT NULL, result TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS studio_owner_wechat_jobs (
          id TEXT PRIMARY KEY, event_key TEXT NOT NULL UNIQUE, binding_id TEXT NOT NULL,
          reservation_id TEXT NOT NULL, template_id TEXT NOT NULL, payload TEXT NOT NULL,
          state TEXT NOT NULL, created_at REAL NOT NULL, updated_at REAL NOT NULL,
          expires_at REAL NOT NULL, lease_until REAL NOT NULL DEFAULT 0,
          error TEXT NOT NULL DEFAULT '', provider_id TEXT NOT NULL DEFAULT ''
        );
        """)


def provider(path, body=None, params=None):
    return miniapp.wx_request(path, body, params={**(params or {}), "access_token": miniapp.access_token()}, return_errors=True)


def bind_for(db, request):
    ticket = miniapp.ticket_for(db, request)
    row = db.execute("SELECT * FROM studio_owner_wechat_bindings WHERE app_id=? AND openid=? AND enabled=1", (ticket["app_id"], ticket["openid"])).fetchone()
    if not row:
        raise HTTPException(403, "owner_wechat_binding_required")
    return row


def public_binding(row):
    return {"id": row["id"], "label": row["label"], "enabled": bool(row["enabled"]),
            "authorization_available": row["grants"] > 0, "last_sent_at": row["last_sent_at"], "error": row["error"]}


def on_reservation(db, kind, row):
    if kind != "created":
        return
    settings = db.execute("SELECT * FROM studio_owner_wechat_settings WHERE id=1").fetchone()
    if not settings or not settings["enabled"] or not settings["template_id"]:
        return
    value = json.loads(row["payload"])
    data = {"name": value.get("name", ""), "booking": value["booking"]}
    stamp = time.time()
    for binding in db.execute("SELECT * FROM studio_owner_wechat_bindings WHERE enabled=1 AND app_id=?", (miniapp.config().app_id,)).fetchall():
        db.execute("""INSERT OR IGNORE INTO studio_owner_wechat_jobs(id,event_key,binding_id,reservation_id,
          template_id,payload,state,created_at,updated_at,expires_at) VALUES(?,?,?,?,?,?,?,?,?,?)""",
          (uuid.uuid4().hex, "created:" + row["id"] + ":" + binding["id"], binding["id"], row["id"],
           settings["template_id"], json.dumps(data, ensure_ascii=False), "queued" if binding["grants"] else "waiting_subscription", stamp, stamp, stamp + 86400))


def message_payload(job, binding):
    value = json.loads(job["payload"])
    booking = value["booking"]
    copy = json.loads(COPY_PATH.read_text(encoding="utf-8"))
    name = re.sub(r"[\x00-\x1f\x7f]", " ", value.get("name", ""))[:20] or copy["customer"][0]
    return {"touser": binding["openid"], "template_id": job["template_id"],
            "page": "pages/studio/owner?reservation=" + job["reservation_id"],
            "miniprogram_state": {"release": "formal", "trial": "trial", "develop": "developer"}[miniapp.config().environment],
            "lang": "zh_CN", "data": {"thing1": {"value": copy["studio"][0]},
                "time2": {"value": booking["date"] + " " + booking["start"]},
                "time3": {"value": booking["date"] + " " + booking["end"]},
                "thing4": {"value": name}, "thing5": {"value": copy["patch_card_note" if booking.get("plan") == "patch" else "card_note"][0].format(guests=booking["guests"])}}}


def process_one(database):
    stamp = time.time()
    with database() as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("UPDATE studio_owner_wechat_jobs SET state='unknown',error='interrupted',updated_at=? WHERE state='sending' AND lease_until<?", (stamp, stamp))
        db.execute("UPDATE studio_owner_wechat_jobs SET state='expired',updated_at=? WHERE state IN ('queued','waiting_subscription') AND expires_at<=?", (stamp, stamp))
        settings = db.execute("SELECT * FROM studio_owner_wechat_settings WHERE id=1").fetchone()
        if not settings["enabled"] or not settings["template_id"] or not miniapp.available():
            return False
        row = db.execute("SELECT * FROM studio_owner_wechat_jobs WHERE state='queued' AND expires_at>? ORDER BY created_at,id LIMIT 1", (stamp,)).fetchone()
        if not row:
            return False
        job = dict(row)
        binding = db.execute("SELECT * FROM studio_owner_wechat_bindings WHERE id=? AND enabled=1 AND app_id=?", (job["binding_id"], miniapp.config().app_id)).fetchone()
        reservation = db.execute("SELECT status,deleted_at FROM studio_reservations WHERE id=?", (job["reservation_id"],)).fetchone()
        if not binding or not reservation or reservation["deleted_at"] or reservation["status"] != "pending" or job["template_id"] != settings["template_id"]:
            db.execute("UPDATE studio_owner_wechat_jobs SET state='skipped',error='superseded',updated_at=? WHERE id=?", (stamp, job["id"]))
            return True
        if not binding["grants"]:
            db.execute("UPDATE studio_owner_wechat_jobs SET state='waiting_subscription',updated_at=? WHERE id=?", (stamp, job["id"]))
            return False
        binding = dict(binding)
        db.execute("UPDATE studio_owner_wechat_bindings SET grants=grants-1 WHERE id=?", (binding["id"],))
        db.execute("UPDATE studio_owner_wechat_jobs SET state='sending',lease_until=?,updated_at=? WHERE id=?", (stamp + 90, stamp, job["id"]))
    # A send attempt consumes the local opportunity even when its result is unknown.
    # The client report is not an authoritative WeChat subscription balance.
    state, error, provider_id = "unknown", "network_error", ""
    try:
        response = provider("cgi-bin/message/subscribe/send", message_payload(job, binding))
        if type(response.get("errcode")) is int and response["errcode"] == 0:
            state, error, provider_id = "accepted", "", str(response.get("msgid", ""))[:120]
        elif type(response.get("errcode")) is int:
            state = "failed"
            error = {43101: "owner_wechat_subscription_required", 40037: "owner_wechat_template_invalid",
                     47003: "owner_wechat_template_invalid", 40003: "owner_wechat_binding_required",
                     45009: "owner_wechat_provider_quota"}.get(response.get("errcode"), "owner_wechat_provider_rejected")
    except Exception:
        pass
    with database() as db:
        db.execute("UPDATE studio_owner_wechat_jobs SET state=?,error=?,provider_id=?,updated_at=?,lease_until=0 WHERE id=? AND state='sending'",
                   (state, error, provider_id, time.time(), job["id"]))
        db.execute("UPDATE studio_owner_wechat_bindings SET last_sent_at=CASE WHEN ?='accepted' THEN ? ELSE last_sent_at END,error=?,grants=CASE WHEN ?='owner_wechat_subscription_required' THEN 0 ELSE grants END WHERE id=?",
                   (state, time.time(), error, error, binding["id"]))
    return True


async def worker(database):
    while True:
        try:
            await asyncio.to_thread(process_one, database)
        except Exception:
            LOG.warning("Owner WeChat worker encountered an internal error")
        await asyncio.sleep(3)


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Setting(Strict):
    version: int = Field(ge=1)
    enabled: bool


class BindRequest(Strict):
    label: str = Field(min_length=1, max_length=40)


class BindConfirm(Strict):
    scene: str = Field(pattern=r"^[A-Za-z0-9_-]{24}$")
    confirm: Literal[True]


class Subscribe(Strict):
    nonce: str = Field(pattern=r"^[A-Za-z0-9_-]{43}$")
    result: Literal["accept", "reject", "ban"]


def register(app, database, admin_actor):
    admin = "/studio-api/manage/owner-wechat"
    native = "/studio-api/owner-wechat"

    @app.get(admin)
    def settings(_actor=Depends(admin_actor)):
        with database() as db:
            value = dict(db.execute("SELECT * FROM studio_owner_wechat_settings WHERE id=1").fetchone())
            value["enabled"] = bool(value["enabled"])
            bindings = [public_binding(r) for r in db.execute("SELECT * FROM studio_owner_wechat_bindings WHERE app_id=? ORDER BY created_at", (miniapp.config().app_id,))]
            jobs = [dict(r) for r in db.execute("SELECT id,reservation_id,state,error,created_at,updated_at FROM studio_owner_wechat_jobs ORDER BY created_at DESC LIMIT 20")]
        return {**value, "available": miniapp.available(), "bindings": bindings, "items": jobs}

    @app.put(admin)
    def update_settings(payload: Setting, actor=Depends(admin_actor)):
        with database() as db:
            db.execute("BEGIN IMMEDIATE")
            current = db.execute("SELECT * FROM studio_owner_wechat_settings WHERE id=1").fetchone()
            if current["version"] != payload.version:
                raise HTTPException(409, "version_conflict")
            if payload.enabled and (not miniapp.available() or not current["template_id"]):
                raise HTTPException(409, "owner_wechat_template_required")
            db.execute("UPDATE studio_owner_wechat_settings SET enabled=?,version=version+1 WHERE id=1", (payload.enabled,))
        return settings(actor)

    @app.post(admin + "/template")
    def setup_template(actor=Depends(admin_actor)):
        miniapp.ensure_available()
        response = provider("wxaapi/newtmpl/gettemplate")
        if response.get("errcode", 0):
            raise HTTPException(503, "owner_wechat_provider_rejected")
        matching = next((r for r in response.get("data", []) if r.get("type") == 2 and all(k + ".DATA" in r.get("content", "") for k in TEMPLATE_KEYS) and r.get("title") == "新预约审核通知"), None)
        if matching:
            template = matching["priTmplId"]
        else:
            keywords = provider("wxaapi/newtmpl/getpubtemplatekeywords", params={"tid": "26378"})
            rules = {r.get("kid"): r.get("rule") for r in keywords.get("data", [])}
            if keywords.get("errcode", 0) or not all(rules.get(k) == v for k,v in {1: "thing", 2: "time", 3: "time", 4: "thing", 5: "thing"}.items()):
                raise HTTPException(409, "owner_wechat_template_invalid")
            response = provider("wxaapi/newtmpl/addtemplate", {"tid": "26378", "kidList": [1, 2, 3, 4, 5], "sceneDesc": "店主接收新预约提醒"})
            if response.get("errcode", 0):
                raise HTTPException(503, "owner_wechat_provider_rejected")
            template = response.get("priTmplId", "")
        if not isinstance(template, str) or not re.fullmatch(r"[A-Za-z0-9_-]{20,160}", template):
            raise HTTPException(503, "owner_wechat_template_invalid")
        with database() as db:
            db.execute("UPDATE studio_owner_wechat_settings SET template_id=?,template_title=?,version=version+1 WHERE id=1", (template, "新预约审核通知"))
        return settings(actor)

    @app.post(admin + "/bindings")
    def make_binding(payload: BindRequest, actor=Depends(admin_actor)):
        miniapp.ensure_available()
        scene, stamp = secrets.token_urlsafe(18), time.time()
        with database() as db:
            if db.execute("SELECT count(*) FROM studio_owner_wechat_bind_tokens WHERE created_at>?", (stamp - 3600,)).fetchone()[0] >= 20:
                raise HTTPException(429, "owner_wechat_binding_limit")
            db.execute("INSERT INTO studio_owner_wechat_bind_tokens(token_hash,app_id,actor,label,created_at,expires_at) VALUES(?,?,?,?,?,?)",
                       (key_hash(scene), miniapp.config().app_id, actor, payload.label.strip(), stamp, stamp + 300))
        image = miniapp.wx_request("wxa/getwxacodeunlimit", {"scene": scene, "page": "pages/studio/owner", "width": 360,
            "check_path": miniapp.config().environment == "release", "env_version": miniapp.config().environment},
            params={"access_token": miniapp.access_token()}, binary=True)
        import base64
        mime = "image/png" if image.startswith(b"\x89PNG") else "image/jpeg"
        return {"scene": scene, "expires_at": stamp + 300, "qr_image": "data:" + mime + ";base64," + base64.b64encode(image).decode()}

    @app.delete(admin + "/bindings/{ident}")
    def revoke_binding(ident: str, _actor=Depends(admin_actor)):
        with database() as db:
            db.execute("UPDATE studio_owner_wechat_bindings SET enabled=0,grants=0 WHERE id=?", (ident,))
            db.execute("UPDATE studio_owner_wechat_jobs SET state='skipped',error='binding_revoked' WHERE binding_id=? AND state IN ('queued','waiting_subscription')", (ident,))
        return {"ok": True}

    @app.get(native + "/binding")
    def preview_binding(scene: str, request: Request):
        if not re.fullmatch(r"[A-Za-z0-9_-]{24}", scene):
            raise HTTPException(400, "owner_wechat_binding_expired")
        with database() as db:
            ticket = miniapp.ticket_for(db, request)
            token = db.execute("SELECT * FROM studio_owner_wechat_bind_tokens WHERE token_hash=? AND app_id=? AND consumed_at=0 AND expires_at>?", (key_hash(scene), ticket["app_id"], time.time())).fetchone()
            if not token:
                raise HTTPException(400, "owner_wechat_binding_expired")
        return {"label": token["label"], "expires_at": token["expires_at"]}

    @app.post(native + "/binding")
    def confirm_binding(payload: BindConfirm, request: Request):
        with database() as db:
            db.execute("BEGIN IMMEDIATE")
            ticket = miniapp.ticket_for(db, request)
            token = db.execute("SELECT * FROM studio_owner_wechat_bind_tokens WHERE token_hash=? AND app_id=? AND consumed_at=0 AND expires_at>?", (key_hash(payload.scene), ticket["app_id"], time.time())).fetchone()
            if not token:
                raise HTTPException(400, "owner_wechat_binding_expired")
            existing = db.execute("SELECT id FROM studio_owner_wechat_bindings WHERE app_id=? AND openid=?", (ticket["app_id"], ticket["openid"])).fetchone()
            ident = existing["id"] if existing else uuid.uuid4().hex
            db.execute("""INSERT INTO studio_owner_wechat_bindings(id,app_id,openid,label,created_at,actor) VALUES(?,?,?,?,?,?)
              ON CONFLICT(app_id,openid) DO UPDATE SET label=excluded.label,actor=excluded.actor,enabled=1,error=''""",
              (ident, ticket["app_id"], ticket["openid"], token["label"], time.time(), token["actor"]))
            db.execute("UPDATE studio_owner_wechat_bind_tokens SET consumed_at=? WHERE token_hash=?", (time.time(), token["token_hash"]))
        return {"bound": True}

    @app.get(native + "/status")
    def status(request: Request):
        with database() as db:
            ticket = miniapp.ticket_for(db, request)
            row = db.execute("SELECT * FROM studio_owner_wechat_bindings WHERE app_id=? AND openid=? AND enabled=1", (ticket["app_id"], ticket["openid"])).fetchone()
            if not row:
                return {"bound": False}
            settings = db.execute("SELECT * FROM studio_owner_wechat_settings WHERE id=1").fetchone()
            nonce = secrets.token_urlsafe(32)
            # Keep earlier prompts valid: returning from WeChat's subscription
            # sheet may trigger onShow and refresh the page before its callback.
            db.execute("DELETE FROM studio_owner_wechat_subscriptions WHERE expires_at<?", (time.time()-86400,))
            if db.execute("SELECT count(*) FROM studio_owner_wechat_subscriptions WHERE binding_id=? AND result='' AND expires_at>?", (row["id"],time.time())).fetchone()[0] >= 30:
                raise HTTPException(429,"owner_wechat_binding_limit")
            db.execute("INSERT INTO studio_owner_wechat_subscriptions(nonce_hash,binding_id,template_id,created_at,expires_at) VALUES(?,?,?,?,?)",
                       (key_hash(nonce), row["id"], settings["template_id"], time.time(), time.time() + 300))
            administrator=db.execute("""SELECT 1 FROM studio_staff_accounts s JOIN studio_miniapp_identities i ON s.user_id=i.user_id
              WHERE i.app_id=? AND i.openid=? AND s.enabled=1 AND s.role='admin'""",(ticket['app_id'],ticket['openid'])).fetchone()
            return {"bound": True, "binding": public_binding(row), "template_id": settings["template_id"], "enabled": bool(settings["enabled"]), "nonce": nonce,"admin":bool(administrator)}

    from customer_auth import require_customer

    @app.get('/studio-api/auth/owner-notifications')
    def account_owner_status(customer=Depends(require_customer)):
        with database() as db:
            row = db.execute("""SELECT 1 FROM studio_owner_wechat_bindings b JOIN studio_miniapp_identities i
              ON i.app_id=b.app_id AND i.openid=b.openid WHERE b.app_id=? AND b.enabled=1 AND i.user_id=? LIMIT 1""",
              (miniapp.config().app_id,customer['id'])).fetchone()
        return {'bound':bool(row)}

    @app.post(native + "/subscribe")
    def subscribed(payload: Subscribe, request: Request):
        with database() as db:
            db.execute("BEGIN IMMEDIATE")
            binding = bind_for(db, request)
            item = db.execute("SELECT * FROM studio_owner_wechat_subscriptions WHERE nonce_hash=? AND binding_id=?", (key_hash(payload.nonce), binding["id"])).fetchone()
            settings = db.execute("SELECT * FROM studio_owner_wechat_settings WHERE id=1").fetchone()
            if not item or item["expires_at"] <= time.time() or not item["template_id"] or item["template_id"] != settings["template_id"]:
                raise HTTPException(409, "owner_wechat_prompt_expired")
            if item["result"]:
                if item["result"] != payload.result:
                    raise HTTPException(409, "owner_wechat_prompt_expired")
                return {"ok": True}
            db.execute("UPDATE studio_owner_wechat_subscriptions SET result=? WHERE nonce_hash=?", (payload.result, key_hash(payload.nonce)))
            if payload.result == "accept":
                db.execute("UPDATE studio_owner_wechat_bindings SET grants=MIN(grants+1,?),error='' WHERE id=?", (MAX_OWNER_GRANTS, binding["id"]))
                db.execute("UPDATE studio_owner_wechat_jobs SET state='queued' WHERE binding_id=? AND state='waiting_subscription' AND expires_at>?", (binding["id"], time.time()))
            else:
                db.execute("UPDATE studio_owner_wechat_bindings SET grants=0,error='owner_wechat_subscription_required' WHERE id=?", (binding["id"],))
        return {"ok": True}

    @app.get(native + "/reservations")
    def reservations(request: Request, reference: str = ""):
        with database() as db:
            bind_for(db, request)
            if reference:
                rows = db.execute("SELECT id,status,payload FROM studio_reservations WHERE id=? AND deleted_at IS NULL", (reference,)).fetchall()
            else:
                rows = db.execute("SELECT id,status,payload FROM studio_reservations WHERE status='pending' AND deleted_at IS NULL ORDER BY created_at DESC LIMIT 30").fetchall()
            result = []
            for row in rows:
                payload = json.loads(row["payload"])
                result.append({"id": row["id"], "status": row["status"], "name": payload.get("name", ""), "booking": payload["booking"]})
        return {"items": result}
