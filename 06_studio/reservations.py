"""VISION manual reservations. Separate from paid orders and legacy inquiries."""
from __future__ import annotations
import hashlib
import json
import os
import re
import secrets
import time
import uuid
from datetime import date, datetime, timedelta
from typing import Annotated, Literal
from zoneinfo import ZoneInfo
from fastapi import Depends, Header, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, model_validator

ZONE = ZoneInfo("America/Toronto")
COOKIE = "puppy_reservation_session"
COOKIE_SECURE = os.getenv("STUDIO_RESERVATION_COOKIE_SECURE", "1") != "0"
STATES = {"pending", "confirmed", "completed", "cancelled"}

def now_local():
    return datetime.now(ZONE)

def initialize(database):
    with database() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS studio_reservations (
          id TEXT PRIMARY KEY, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'pending', payload TEXT NOT NULL,
          visitor_hash TEXT NOT NULL, idempotency_key TEXT NOT NULL UNIQUE,
          payload_hash TEXT NOT NULL, staff_note TEXT NOT NULL DEFAULT '',
          version INTEGER NOT NULL DEFAULT 1
        );
        CREATE INDEX IF NOT EXISTS reservation_status_date ON studio_reservations(status,created_at);
        CREATE TABLE IF NOT EXISTS reservation_events (
          id INTEGER PRIMARY KEY, reservation_id TEXT NOT NULL, actor TEXT NOT NULL,
          created_at TEXT NOT NULL, status TEXT NOT NULL, note TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS reservation_policy (
          id INTEGER PRIMARY KEY CHECK(id=1), exclusive_groups INTEGER NOT NULL DEFAULT 0,
          version INTEGER NOT NULL DEFAULT 1
        );
        INSERT OR IGNORE INTO reservation_policy(id) VALUES(1);
        """)

def clock(value):
    return f"{value // 60:02d}:{value % 60:02d}"

def minute(value):
    try:
        h, m = map(int, value.split(":"))
        if h > 23 or m not in (0, 30):
            raise ValueError()
        return h * 60 + m
    except (ValueError, AttributeError):
        raise HTTPException(422, "invalid_reservation_time")

def closing(day):
    return 960 if day.weekday() == 2 else 1080 if day.weekday() == 3 else 1320

def visitor(request, response=None):
    token = request.cookies.get(COOKIE, "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
        if response is None:
            raise HTTPException(409, "reservation_session_missing")
        token = secrets.token_urlsafe(32)
        response.set_cookie(COOKIE, token, max_age=30*86400, httponly=True,
                            secure=COOKIE_SECURE, samesite="lax", path="/studio-api")
    return hashlib.sha256(token.encode()).hexdigest()

class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

class Visit(Strict):
    date: date
    start: str = Field(pattern=r"^\d{2}:\d{2}$")
    end: str = Field(pattern=r"^\d{2}:\d{2}$")
    plan: Literal["hourly", "day"]
    guests: int = Field(ge=1, le=20, strict=True)

class Submission(Strict):
    booking: Visit
    name: str = Field(min_length=1, max_length=80)
    contact_method: Literal["wechat", "phone", "email", "other"]
    contact: str = Field(min_length=3, max_length=180)
    notes: str = Field(default="", max_length=1500)
    consent: Literal[True]
    locale: Literal["zh", "en"] = "zh"
    website: str = Field(default="", max_length=0)

    @model_validator(mode="after")
    def contact_valid(self):
        if self.contact_method == "phone" and (not re.fullmatch(r"[+\d ()-]{7,30}", self.contact) or len(re.sub(r"\D", "", self.contact)) < 7):
            raise ValueError("Invalid phone")
        if self.contact_method == "email" and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", self.contact):
            raise ValueError("Invalid email")
        return self

def validate_interval(booking, current):
    start, end = minute(booking.start), minute(booking.end)
    if not current.date() <= booking.date < current.date() + timedelta(days=14):
        raise HTTPException(422, "reservation_outside_window")
    if start < 600 or end > closing(booking.date) or end - start < 120:
        raise HTTPException(422, "reservation_interval_unavailable")
    if booking.plan == "day" and end != closing(booking.date):
        raise HTTPException(422, "reservation_day_end")
    if datetime.combine(booking.date, datetime.min.time(), tzinfo=ZONE) + timedelta(minutes=start) <= current:
        raise HTTPException(422, "reservation_in_past")

def overlaps(db, booking, exclude=""):
    rows = db.execute("SELECT id,payload FROM studio_reservations WHERE status='confirmed' AND id!=? AND json_extract(payload,'$.booking.date')=?", (exclude, str(booking.date))).fetchall()
    return any(minute(json.loads(r["payload"])["booking"]["start"]) < minute(booking.end)
               and minute(json.loads(r["payload"])["booking"]["end"]) > minute(booking.start) for r in rows)

def public_row(row):
    data = json.loads(row["payload"])
    return {key: row[key] for key in ("id", "status", "created_at", "updated_at", "version")} | {"booking": data["booking"], "name": data["name"]}

class ReservationUpdate(Strict):
    status: Literal["pending", "confirmed", "completed", "cancelled"]
    staff_note: str = Field(default="", max_length=1500)
    version: int = Field(ge=1)

class ReservationPolicy(Strict):
    exclusive_groups: bool
    version: int = Field(ge=1)

def register(app, database, admin_actor):
    @app.get("/studio-api/reservation-calendar")
    def calendar(request: Request, response: Response):
        visitor(request, response)
        current = now_local()
        with database() as db:
            exclusive = bool(db.execute("SELECT exclusive_groups FROM reservation_policy WHERE id=1").fetchone()[0])
            confirmed = [json.loads(r[0])["booking"] for r in db.execute("SELECT payload FROM studio_reservations WHERE status='confirmed'")] if exclusive else []
        days = []
        for n in range(14):
            day = current.date() + timedelta(days=n)
            slots = []
            for start in range(600, 1320, 30):
                past = datetime.combine(day, datetime.min.time(), tzinfo=ZONE) + timedelta(minutes=start) <= current
                busy = any(b["date"] == str(day) and minute(b["start"]) < start + 30 and minute(b["end"]) > start for b in confirmed)
                reason = "closed" if start >= closing(day) else "past" if past else "confirmed" if busy else None
                slots.append({"start": clock(start), "end": clock(start + 30), "available": reason is None, "reason": reason})
            days.append({"date": str(day), "close": clock(closing(day)), "slots": slots})
        return {"today": str(current.date()), "timezone": "America/Toronto", "minimum_minutes": 120, "days": days}

    @app.post("/studio-api/reservations", status_code=201)
    def submit(payload: Submission, request: Request, idempotency_key: Annotated[str, Header()]):
        try:
            uuid.UUID(idempotency_key)
        except ValueError:
            raise HTTPException(422, "invalid_request_id")
        actor = visitor(request)
        encoded = payload.model_dump_json()
        digest = hashlib.sha256(encoded.encode()).hexdigest()
        current = now_local()
        with database() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute("SELECT * FROM studio_reservations WHERE idempotency_key=?", (idempotency_key,)).fetchone()
            if existing:
                if existing["visitor_hash"] != actor or existing["payload_hash"] != digest:
                    raise HTTPException(409, "reservation_request_changed")
                return public_row(existing)
            validate_interval(payload.booking, current)
            exclusive = db.execute("SELECT exclusive_groups FROM reservation_policy WHERE id=1").fetchone()[0]
            if exclusive and overlaps(db, payload.booking):
                raise HTTPException(409, "reservation_interval_unavailable")
            bucket = int(time.time()) // 3600
            client = "reservation:" + hashlib.sha256((request.client.host if request.client else "unknown").encode()).hexdigest()
            count = db.execute("SELECT count FROM submission_limits WHERE client_hash=? AND bucket=?", (client, bucket)).fetchone()
            if count and count[0] >= 8:
                raise HTTPException(429, "reservation_rate_limit")
            db.execute("DELETE FROM submission_limits WHERE bucket<?", (bucket-1,))
            db.execute("INSERT INTO submission_limits VALUES(?,?,1) ON CONFLICT(client_hash,bucket) DO UPDATE SET count=count+1", (client,bucket))
            ref = "VIS-" + uuid.uuid4().hex[:16].upper()
            timestamp = current.isoformat()
            db.execute("INSERT INTO studio_reservations(id,created_at,updated_at,payload,visitor_hash,idempotency_key,payload_hash) VALUES(?,?,?,?,?,?,?)", (ref,timestamp,timestamp,encoded,actor,idempotency_key,digest))
            row = db.execute("SELECT * FROM studio_reservations WHERE id=?", (ref,)).fetchone()
            return public_row(row)

    @app.get("/studio-api/reservations/{reference}")
    def receipt(reference: str, request: Request):
        try:
            actor = visitor(request)
        except HTTPException:
            raise HTTPException(404, "reservation_not_found")
        with database() as db:
            row = db.execute("SELECT * FROM studio_reservations WHERE id=? AND visitor_hash=?", (reference, actor)).fetchone()
        if not row:
            raise HTTPException(404, "reservation_not_found")
        return public_row(row)

    @app.get("/studio-api/manage/reservations")
    def listing(_actor=Depends(admin_actor), status: str="all", day: date | None=None, search: str="", page: int=1):
        if status not in STATES | {"all"} or not 1 <= page <= 10000 or len(search) > 120:
            raise HTTPException(422, "invalid_filter")
        clauses, params = [], []
        if status != "all": clauses.append("status=?"); params.append(status)
        if day: clauses.append("json_extract(payload,'$.booking.date')=?"); params.append(str(day))
        if search: clauses.append("(instr(lower(json_extract(payload,'$.name')),lower(?))>0 OR instr(id,?)>0)"); params.extend([search,search])
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with database() as db:
            count = db.execute("SELECT count(*) FROM studio_reservations"+where, params).fetchone()[0]
            rows = db.execute("SELECT * FROM studio_reservations"+where+" ORDER BY created_at DESC,id DESC LIMIT 30 OFFSET ?", (*params,(page-1)*30)).fetchall()
            counts = dict(db.execute("SELECT status,count(*) FROM studio_reservations GROUP BY status").fetchall())
            policy = dict(db.execute("SELECT exclusive_groups,version FROM reservation_policy WHERE id=1").fetchone())
        return {"items":[public_row(r) | {"payload":json.loads(r["payload"]),"staff_note":r["staff_note"]} for r in rows], "total":count,"counts":counts,"policy":policy}

    @app.patch("/studio-api/manage/reservations/{reference}")
    def update(reference: str, payload: ReservationUpdate, actor=Depends(admin_actor)):
        current = now_local()
        with database() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM studio_reservations WHERE id=?", (reference,)).fetchone()
            if not row: raise HTTPException(404,"reservation_not_found")
            if row["version"] != payload.version: raise HTTPException(409,"version_conflict")
            if payload.status == "confirmed" and row["status"] != "confirmed":
                booking = Visit(**json.loads(row["payload"])["booking"])
                validate_interval(booking, current)
                if db.execute("SELECT exclusive_groups FROM reservation_policy WHERE id=1").fetchone()[0] and overlaps(db, booking, reference):
                    raise HTTPException(409,"reservation_confirmation_conflict")
            if payload.status == "completed" and row["status"] not in ("confirmed","completed"):
                raise HTTPException(409,"reservation_not_confirmed")
            db.execute("UPDATE studio_reservations SET status=?,staff_note=?,version=version+1,updated_at=? WHERE id=?", (payload.status,payload.staff_note,current.isoformat(),reference))
            db.execute("INSERT INTO reservation_events(reservation_id,actor,created_at,status,note) VALUES(?,?,?,?,?)", (reference,actor,current.isoformat(),payload.status,payload.staff_note))
        return {"id":reference,"status":payload.status,"version":payload.version+1}

    @app.put("/studio-api/manage/reservation-policy")
    def policy(payload: ReservationPolicy, _actor=Depends(admin_actor)):
        with database() as db:
            db.execute("BEGIN IMMEDIATE")
            current = db.execute("SELECT * FROM reservation_policy WHERE id=1").fetchone()
            if current["version"] != payload.version: raise HTTPException(409,"version_conflict")
            if payload.exclusive_groups:
                rows = db.execute("SELECT id,payload FROM studio_reservations WHERE status='confirmed'").fetchall()
                if any(overlaps(db, Visit(**json.loads(r["payload"])["booking"]), r["id"]) for r in rows):
                    raise HTTPException(409,"reservation_confirmation_conflict")
            db.execute("UPDATE reservation_policy SET exclusive_groups=?,version=version+1 WHERE id=1", (payload.exclusive_groups,))
        return {"exclusive_groups":payload.exclusive_groups,"version":payload.version+1}
