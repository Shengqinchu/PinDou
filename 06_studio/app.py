"""Isolated, durable studio inquiries. No changes to the pattern generator DB."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import sqlite3
import time
import uuid
from contextlib import asynccontextmanager, contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Annotated, Literal
from urllib.error import HTTPError, URLError
from urllib.request import Request as URLRequest, urlopen
from zoneinfo import ZoneInfo

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

DB_PATH = Path(os.getenv("STUDIO_DB_PATH", "var/studio.sqlite3"))
ADMIN_ORIGIN = os.getenv("STUDIO_ADMIN_ORIGIN", "http://127.0.0.1:8000").rstrip("/")
TORONTO = ZoneInfo("America/Toronto")
PRODUCT_IDS = {"starter", "beads", "findings", "custom"}
STATES = {"pending", "confirmed", "completed", "cancelled"}


@contextmanager
def database():
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with database() as db:
        db.executescript("""
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS studio_requests (
          id TEXT PRIMARY KEY, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
          kind TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending', payload TEXT NOT NULL,
          idempotency_key TEXT NOT NULL UNIQUE, payload_hash TEXT NOT NULL,
          staff_note TEXT NOT NULL DEFAULT '', version INTEGER NOT NULL DEFAULT 1
        );
        CREATE INDEX IF NOT EXISTS requests_status ON studio_requests(status,created_at);
        CREATE TABLE IF NOT EXISTS submission_limits (
          client_hash TEXT NOT NULL, bucket INTEGER NOT NULL, count INTEGER NOT NULL,
          PRIMARY KEY(client_hash,bucket)
        );
        CREATE TABLE IF NOT EXISTS studio_audit (
          id INTEGER PRIMARY KEY, request_id TEXT NOT NULL, changed_at TEXT NOT NULL,
          actor TEXT NOT NULL, previous_status TEXT NOT NULL, new_status TEXT NOT NULL,
          staff_note TEXT NOT NULL
        );
        """)


@asynccontextmanager
async def lifespan(_app):
    initialize()
    yield


app = FastAPI(title="PinDou Puppy Studio", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)


@app.middleware("http")
async def response_controls(request: Request, call_next):
    length = request.headers.get("content-length", "0")
    if not length.isdigit() or int(length) > 16000:
        from fastapi.responses import JSONResponse
        return JSONResponse({"detail": "Request too large"}, status_code=413)
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Booking(StrictModel):
    date: date
    start: str = Field(pattern=r"^\d{2}:\d{2}$")
    end: str = Field(pattern=r"^\d{2}:\d{2}$")
    guests: int = Field(ge=1, le=20, strict=True)
    plan: Literal["hourly", "day", "pair"]

    @model_validator(mode="after")
    def check_dates(self):
        now = datetime.now(TORONTO)
        if not now.date() <= self.date <= now.date() + timedelta(days=90):
            raise ValueError("Choose a date within the next 90 days")
        try:
            start = datetime.fromisoformat(f"{self.date}T{self.start}").replace(tzinfo=TORONTO)
            end = datetime.fromisoformat(f"{self.date}T{self.end}").replace(tzinfo=TORONTO)
        except ValueError as exc:
            raise ValueError("Invalid time") from exc
        if start <= now or end <= start or start.hour < 10 or end.hour > 23 or (end.hour == 23 and end.minute):
            raise ValueError("Invalid requested interval")
        if start.minute not in (0, 30) or end.minute not in (0, 30):
            raise ValueError("Choose a half-hour interval")
        if self.plan == "pair" and self.guests != 2:
            raise ValueError("The pair pass is for two guests")
        return self


class Item(StrictModel):
    id: str
    quantity: int = Field(ge=1, le=20, strict=True)

    @field_validator("id")
    @classmethod
    def known_item(cls, value):
        if value not in PRODUCT_IDS:
            raise ValueError("Unknown product")
        return value


class Inquiry(StrictModel):
    kind: Literal["visit", "pickup"]
    name: str = Field(min_length=1, max_length=80)
    contact_method: Literal["wechat", "email", "phone"]
    contact: str = Field(min_length=3, max_length=180)
    notes: str = Field(default="", max_length=1500)
    locale: Literal["zh", "en"] = "zh"
    consent: Literal[True]
    website: str = Field(default="", max_length=0)
    booking: Booking | None = None
    items: list[Item] = Field(default_factory=list, max_length=4)

    @model_validator(mode="after")
    def check_kind(self):
        if self.kind == "visit" and (self.booking is None or self.items):
            raise ValueError("Visit requires booking details only")
        if self.kind == "pickup" and (not self.items or self.booking is not None):
            raise ValueError("Pickup requires a selection only")
        if len({item.id for item in self.items}) != len(self.items):
            raise ValueError("Duplicate product")
        if self.contact_method == "email" and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", self.contact):
            raise ValueError("Invalid email")
        if self.contact_method == "phone" and not re.fullmatch(r"[+\d ()-]{7,30}", self.contact):
            raise ValueError("Invalid phone")
        if self.contact_method == "phone" and len(re.sub(r"\D", "", self.contact)) < 7:
            raise ValueError("Invalid phone")
        return self


def admin_actor(authorization: Annotated[str | None, Header()] = None) -> str:
    """Validate against the existing admin service; do not duplicate its secrets."""
    if not authorization or not authorization.startswith("Bearer ") or len(authorization) > 5000:
        raise HTTPException(401, "Administrator sign-in required")
    # Only the fixed loopback origin receives this token. Never use caller-supplied URLs.
    req = URLRequest(f"{ADMIN_ORIGIN}/api/v1/admin/dashboard", headers={"Authorization": authorization})
    try:
        with urlopen(req, timeout=8) as response:
            if response.status != 200:
                raise HTTPException(401, "Administrator sign-in required")
    except HTTPError as exc:
        raise HTTPException(401 if exc.code in (401, 403) else 503, "Administrator verification unavailable") from exc
    except (URLError, TimeoutError) as exc:
        raise HTTPException(503, "Administrator verification unavailable") from exc
    # The upstream has authenticated this signed token. Require full admin, not viewer/operator.
    try:
        segment = authorization[7:].split(".")[1]
        claims = json.loads(base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4)))
    except (ValueError, IndexError, TypeError) as exc:
        raise HTTPException(401, "Invalid administrator token") from exc
    role = claims.get("role") or ("admin" if claims.get("admin") else "user")
    if role != "admin":
        raise HTTPException(403, "Administrator role required")
    return str(claims.get("sub", "admin"))[:120]


@app.get("/studio-api/health")
def health():
    with database() as db:
        db.execute("SELECT 1 FROM studio_requests LIMIT 1")
    return {"status": "ok", "service": "pindou-studio", "version": "0.1.0"}


@app.post("/studio-api/requests", status_code=201)
def create_inquiry(payload: Inquiry, request: Request, idempotency_key: Annotated[str, Header()]):
    try:
        uuid.UUID(idempotency_key)
    except ValueError as exc:
        raise HTTPException(422, "Invalid request identifier") from exc
    encoded = payload.model_dump_json()
    digest = hashlib.sha256(encoded.encode()).hexdigest()
    now = datetime.now(TORONTO).isoformat()
    client = hashlib.sha256((request.client.host if request.client else "unknown").encode()).hexdigest()
    bucket = int(time.time()) // 3600
    with database() as db:
        db.execute("BEGIN IMMEDIATE")
        existing = db.execute("SELECT id,payload_hash,status FROM studio_requests WHERE idempotency_key=?", (idempotency_key,)).fetchone()
        if existing:
            if existing["payload_hash"] != digest:
                raise HTTPException(409, "Request identifier already used")
            return {"id": existing["id"], "status": existing["status"], "kind": payload.kind}
        count = db.execute("SELECT count FROM submission_limits WHERE client_hash=? AND bucket=?", (client, bucket)).fetchone()
        if count and count[0] >= 8:
            raise HTTPException(429, "Please try later", headers={"Retry-After": str(3600 - int(time.time()) % 3600)})
        db.execute("DELETE FROM submission_limits WHERE bucket<?", (bucket - 1,))
        db.execute("INSERT INTO submission_limits VALUES(?,?,1) ON CONFLICT(client_hash,bucket) DO UPDATE SET count=count+1", (client, bucket))
        ref = ("VIS-" if payload.kind == "visit" else "PUP-") + uuid.uuid4().hex[:12].upper()
        db.execute("INSERT INTO studio_requests(id,created_at,updated_at,kind,payload,idempotency_key,payload_hash) VALUES(?,?,?,?,?,?,?)", (ref, now, now, payload.kind, encoded, idempotency_key, digest))
    return {"id": ref, "status": "pending", "kind": payload.kind}


@app.get("/studio-api/manage/requests")
def list_inquiries(_actor: Annotated[str, Depends(admin_actor)], status: str = "all", page: int = 1):
    if status not in STATES | {"all"} or page < 1 or page > 10000:
        raise HTTPException(422, "Invalid filter")
    clause = "" if status == "all" else "WHERE status=?"
    params = () if status == "all" else (status,)
    with database() as db:
        count = db.execute(f"SELECT count(*) FROM studio_requests {clause}", params).fetchone()[0]
        rows = db.execute(f"SELECT id,created_at,updated_at,kind,status,payload,staff_note,version FROM studio_requests {clause} ORDER BY created_at DESC LIMIT 50 OFFSET ?", (*params, (page - 1) * 50)).fetchall()
    return {"items": [{**dict(row), "payload": json.loads(row["payload"])} for row in rows], "total": count, "page": page}


class StatusUpdate(StrictModel):
    status: Literal["pending", "confirmed", "completed", "cancelled"]
    staff_note: str = Field(default="", max_length=1500)
    version: int = Field(ge=1)


@app.patch("/studio-api/manage/requests/{request_id}")
def update_inquiry(request_id: str, payload: StatusUpdate, actor: Annotated[str, Depends(admin_actor)]):
    now = datetime.now(TORONTO).isoformat()
    with database() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT status,version FROM studio_requests WHERE id=?", (request_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Request not found")
        if row["version"] != payload.version:
            raise HTTPException(409, "Request was updated elsewhere; refresh first")
        db.execute("UPDATE studio_requests SET status=?,staff_note=?,updated_at=?,version=version+1 WHERE id=?", (payload.status, payload.staff_note, now, request_id))
        db.execute("INSERT INTO studio_audit(request_id,changed_at,actor,previous_status,new_status,staff_note) VALUES(?,?,?,?,?,?)", (request_id, now, actor, row["status"], payload.status, payload.staff_note))
    return {"id": request_id, "status": payload.status, "version": row["version"] + 1}
