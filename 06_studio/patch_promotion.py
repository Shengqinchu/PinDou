"""One launch campaign, counted by people in atomic reservation transactions.

The final eligible group receives a canvas strap for every guest, even if this exceeds
the configured quota. Existing reservations are never enrolled by migration.
"""
from __future__ import annotations

import json
from fastapi import Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field

CAMPAIGN = "patch-launch-20260928"


def initialize(database, stamp):
    with database() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS patch_promotion (
          id INTEGER PRIMARY KEY CHECK(id=1), campaign TEXT NOT NULL,
          started_at TEXT NOT NULL, quota INTEGER NOT NULL CHECK(quota>=0),
          enabled INTEGER NOT NULL DEFAULT 1, version INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS patch_promotion_claims (
          reservation_id TEXT PRIMARY KEY REFERENCES studio_reservations(id),
          guests INTEGER NOT NULL CHECK(guests>=0), active INTEGER NOT NULL,
          fulfilled INTEGER NOT NULL DEFAULT 0,
          created_at TEXT NOT NULL, released_at TEXT
        );
        CREATE TABLE IF NOT EXISTS patch_promotion_events (
          id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, actor TEXT NOT NULL,
          reservation_id TEXT, action TEXT NOT NULL, detail TEXT NOT NULL
        );
        """)
        columns = {row[1] for row in db.execute("PRAGMA table_info(patch_promotion)")}
        if "remaining_adjustment" not in columns:
            db.execute("ALTER TABLE patch_promotion ADD COLUMN remaining_adjustment INTEGER NOT NULL DEFAULT 0")
        db.execute("""INSERT OR IGNORE INTO patch_promotion
          (id,campaign,started_at,quota) VALUES(1,?,?,10)""", (CAMPAIGN, stamp))


def snapshot(db):
    row = dict(db.execute("SELECT * FROM patch_promotion WHERE id=1").fetchone())
    used = db.execute("SELECT coalesce(sum(guests),0) FROM patch_promotion_claims WHERE active=1").fetchone()[0]
    return {**row, "enabled": bool(row["enabled"]), "allocated": used,
            "remaining": max(0, row["quota"] - used + row["remaining_adjustment"])}


def public_snapshot(db):
    data = snapshot(db)
    return {key: data[key] for key in ("campaign", "enabled", "quota", "remaining")}


def event(db, stamp, actor, reference, action, detail):
    db.execute("""INSERT INTO patch_promotion_events
      (created_at,actor,reservation_id,action,detail) VALUES(?,?,?,?,?)""",
      (stamp, actor, reference, action, json.dumps(detail, separators=(",", ":"))))


def capacity_changed(db):
    # Editing a displayed remaining count must not overwrite a concurrent claim
    # or cancellation. This revision covers both settings and allocated people.
    db.execute("UPDATE patch_promotion SET version=version+1 WHERE id=1")


def enroll(db, row, stamp, actor):
    """Called only after a NEW booking insert and before its transaction commits."""
    booking = json.loads(row["payload"])["booking"]
    if booking["plan"] != "patch" or row["creation_source"] == "admin_backfill":
        return
    promotion = snapshot(db)
    if not promotion["enabled"]:
        return
    # Strictly positive balance at the start of this transaction qualifies the
    # entire group. BEGIN IMMEDIATE serializes competing claims and quota edits.
    guests = booking["guests"] if promotion["remaining"] > 0 else 0
    db.execute("""INSERT INTO patch_promotion_claims
      (reservation_id,guests,active,created_at) VALUES(?,?,?,?)""",
      (row["id"], guests, int(guests > 0), stamp))
    if guests:
        capacity_changed(db)
    event(db, stamp, actor, row["id"], "enrolled", {"guests": guests})


def reconcile(db, row, stamp, actor, *, restoring=False):
    claim = db.execute("SELECT * FROM patch_promotion_claims WHERE reservation_id=?", (row["id"],)).fetchone()
    if not claim or claim["fulfilled"]:
        return
    if row["status"] == "completed" and claim["active"]:
        # Archiving a completed visit must not turn a delivered strap into stock.
        db.execute("UPDATE patch_promotion_claims SET fulfilled=1 WHERE reservation_id=?", (row["id"],))
        event(db, stamp, actor, row["id"], "fulfilled", {"guests": claim["guests"]})
    elif row["status"] == "cancelled" or row["deleted_at"]:
        if claim["active"]:
            db.execute("UPDATE patch_promotion_claims SET active=0,released_at=? WHERE reservation_id=?", (stamp, row["id"]))
            capacity_changed(db)
            event(db, stamp, actor, row["id"], "released", {"guests": claim["guests"]})
    elif restoring and claim["released_at"] and not claim["active"] and claim["guests"]:
        # Restoring a cancelled booking is a new claim, never an oversell of an
        # exhausted campaign. Never retroactively enroll a pre-launch booking.
        promotion = snapshot(db)
        if promotion["enabled"] and promotion["remaining"] > 0:
            db.execute("UPDATE patch_promotion_claims SET active=1,released_at=NULL WHERE reservation_id=?", (row["id"],))
            capacity_changed(db)
            event(db, stamp, actor, row["id"], "restored", {"guests": claim["guests"]})


def awards(db):
    return dict(db.execute("SELECT reservation_id,guests FROM patch_promotion_claims WHERE active=1"))


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    quota: int = Field(ge=0, le=100000, strict=True)
    remaining: int | None = Field(default=None, ge=0, le=100000, strict=True)
    enabled: bool = Field(strict=True)
    version: int = Field(ge=1, strict=True)


def register(app, database, admin_actor, now):
    @app.get("/studio-api/patch-promotion")
    def public(response: Response):
        response.headers["Cache-Control"] = "no-store"
        with database() as db:
            return public_snapshot(db)

    @app.get("/studio-api/manage/patch-promotion")
    def read(response: Response, _actor=Depends(admin_actor)):
        response.headers["Cache-Control"] = "no-store"
        with database() as db:
            return snapshot(db)

    @app.put("/studio-api/manage/patch-promotion")
    def update(payload: Settings, actor=Depends(admin_actor)):
        with database() as db:
            db.execute("BEGIN IMMEDIATE")
            previous = snapshot(db)
            requested = payload.model_dump(exclude_none=True)
            if payload.version != previous["version"]:
                # Replaying the last exact settings request returns CURRENT
                # stock, even when a booking arrived after the lost response.
                last = db.execute("SELECT detail FROM patch_promotion_events WHERE action='settings' AND actor=? ORDER BY id DESC LIMIT 1", (actor,)).fetchone()
                detail = json.loads(last[0]) if last else {}
                if detail.get("request") == requested:
                    return previous
                # Preserve retries from versions that wrote the old event shape.
                if ("request" not in detail and payload.remaining is None
                        and payload.version + 1 == previous["version"]
                        and detail.get("after", {}).get("version") == previous["version"]
                        and payload.quota == previous["quota"] and payload.enabled == previous["enabled"]):
                    return previous
                raise HTTPException(409, "version_conflict")
            adjustment = previous["remaining_adjustment"]
            if payload.remaining is not None:
                adjustment = payload.remaining - payload.quota + previous["allocated"]
            db.execute("UPDATE patch_promotion SET quota=?,enabled=?,remaining_adjustment=?,version=version+1 WHERE id=1",
                       (payload.quota, int(payload.enabled), adjustment))
            current = snapshot(db)
            event(db, now().isoformat(), actor, None, "settings",
                  {"before": {k: previous[k] for k in ("quota", "remaining", "remaining_adjustment", "allocated", "enabled", "version")},
                   "after": {k: current[k] for k in ("quota", "remaining", "remaining_adjustment", "allocated", "enabled", "version")},
                   "request": requested})
            return current
