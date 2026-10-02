"""Versioned schedule changes; attendance and financial history stay append-only."""
from __future__ import annotations

import hashlib
import json
import time
from datetime import date

from fastapi import Depends, HTTPException
from pydantic import Field

import reservations as visits
from customer_auth import require_customer


def initialize(database):
    with database() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS reservation_schedule_changes (
          id INTEGER PRIMARY KEY, reservation_id TEXT NOT NULL, actor TEXT NOT NULL,
          request_key TEXT NOT NULL, request_hash TEXT NOT NULL,
          from_version INTEGER NOT NULL, to_version INTEGER NOT NULL,
          created_at REAL NOT NULL, reset_attendance INTEGER NOT NULL DEFAULT 0,
          before_snapshot TEXT NOT NULL, after_snapshot TEXT NOT NULL,
          UNIQUE(reservation_id,actor,request_key));
        CREATE INDEX IF NOT EXISTS schedule_changes_reservation
          ON reservation_schedule_changes(reservation_id,id);
        CREATE TRIGGER IF NOT EXISTS schedule_changes_immutable_update
          BEFORE UPDATE ON reservation_schedule_changes
          BEGIN SELECT RAISE(ABORT,'schedule changes are append-only'); END;
        CREATE TRIGGER IF NOT EXISTS schedule_changes_immutable_delete
          BEFORE DELETE ON reservation_schedule_changes
          BEGIN SELECT RAISE(ABORT,'schedule changes are append-only'); END;
        """)


class Schedule(visits.Strict):
    date: date
    start: str = Field(pattern=r"^\d{2}:\d{2}$")
    end: str = Field(pattern=r"^\d{2}:\d{2}$")
    guests: int = Field(ge=1, le=99, strict=True)


class Change(visits.Strict):
    booking: Schedule
    version: int = Field(ge=1, strict=True)
    request_key: str = Field(pattern=r"^[a-f0-9-]{36}$")


def digest(payload):
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def replay(db, row, actor, key, fingerprint):
    if not key:
        return False
    previous = db.execute("SELECT request_hash FROM reservation_schedule_changes WHERE reservation_id=? AND actor=? AND request_key=?",
                          (row['id'], actor, key)).fetchone()
    if not previous:
        return False
    if previous['request_hash'] != fingerprint:
        raise HTTPException(409, 'reservation_edit_request_changed')
    return True


def snapshot(row):
    return {key: row[key] for key in ('status', 'version', 'actual_minutes', 'actual_guests', 'public_note')} | {
        'booking': json.loads(row['payload'])['booking']}


def record(db, before, after, actor, key, fingerprint, *, reset_attendance=False):
    old, new = snapshot(before), snapshot(after)
    db.execute("""INSERT INTO reservation_schedule_changes
      (reservation_id,actor,request_key,request_hash,from_version,to_version,created_at,
       reset_attendance,before_snapshot,after_snapshot) VALUES(?,?,?,?,?,?,?,?,?,?)""",
      (before['id'], actor, key, fingerprint, before['version'], after['version'], time.time(),
       int(reset_attendance), json.dumps(old, ensure_ascii=False), json.dumps(new, ensure_ascii=False)))
    if old != new:
        db.execute("INSERT INTO reservation_events(reservation_id,actor,created_at,status,note) VALUES(?,?,?,'schedule_changed',?)",
                   (before['id'], actor, after['updated_at'], json.dumps({'before': old, 'after': new}, ensure_ascii=False)))


def reopened_attendance(db, row):
    # A customer explicitly rebooked a completed visit. Old rewards and finance
    # records remain; they must not lock confirmation of the new pending request.
    return row['status'] != 'completed' and bool(db.execute(
        "SELECT 1 FROM reservation_schedule_changes WHERE reservation_id=? AND reset_attendance=1 AND to_version<=? LIMIT 1",
        (row['id'], row['version'])).fetchone())


def booking_payload(row, booking):
    data = json.loads(row['payload'])
    data['booking'] = booking.model_dump(mode='json')
    offer = data.get('offer_snapshot')
    if offer and (booking.plan != 'hourly' or booking.guests != offer['guests']
                  or visits.minute(booking.end)-visits.minute(booking.start) != offer['minutes']
                  or str(booking.date) > offer['until']):
        # A historical promotion is not silently extended to a different booking.
        for key in ('offer', 'offer_revision', 'offer_snapshot'):
            data.pop(key, None)
    return json.dumps(data, ensure_ascii=False)


def validate_admin_change(db, row, booking, status, current):
    start, end = visits.minute(booking.start), visits.minute(booking.end)
    if end <= start:
        raise HTTPException(422, 'invalid_reservation_time')
    if status in ('completed', 'cancelled') or booking.date < current.date():
        # Correcting historical facts must not impose today's opening-hours,
        # minimum-duration or party-size policy retroactively.
        return
    policy = visits.read_policy(db)
    visits.validate_interval(booking, current, policy)
    if not visits.has_capacity(db, booking, policy, row['id']):
        raise HTTPException(409, 'reservation_confirmation_conflict')


def resize_claim(db, row, actor, stamp):
    claim = db.execute('SELECT * FROM patch_promotion_claims WHERE reservation_id=?', (row['id'],)).fetchone()
    booking = json.loads(row['payload'])['booking']
    if not claim or not claim['active'] or claim['fulfilled'] or not claim['guests']:
        return
    if claim['guests'] == booking['guests']:
        return
    # Existing eligible groups retain the whole-group award. Only unused claims
    # follow their revised party size; fulfilled gifts are never returned to stock.
    db.execute('UPDATE patch_promotion_claims SET guests=? WHERE reservation_id=?', (booking['guests'], row['id']))
    visits.patch_promotion.capacity_changed(db)
    visits.patch_promotion.event(db, stamp, actor, row['id'], 'resized', {'before': claim['guests'], 'guests': booking['guests']})


def supersede_owner_alerts(db, reference):
    stamp = time.time()
    db.execute("""UPDATE studio_owner_notifications SET state='skipped',error='superseded',updated_at=?,lease_until=0
      WHERE reservation_id=? AND kind IN ('created','changed') AND state IN ('queued','retry','expired','failed')""", (stamp, reference))
    db.execute("""UPDATE studio_sms_jobs SET state='skipped',error='superseded'
      WHERE reservation_id=? AND message_id IS NULL AND notification_key IS NOT NULL
      AND started_at=0 AND state='queued'""", (reference,))
    db.execute("""UPDATE studio_owner_wechat_jobs SET state='skipped',error='superseded',updated_at=?
      WHERE reservation_id=? AND state IN ('queued','waiting_subscription')""", (stamp, reference))


def register(app, database, admin_actor):
    def owned(db, reference, customer):
        row = db.execute('SELECT * FROM studio_reservations WHERE id=?', (reference,)).fetchone()
        if not row or row['deleted_at'] or row['owner_id'] != customer['id']:
            raise HTTPException(404, 'reservation_not_found')
        return row

    @app.get('/studio-api/reservations/{reference}/edit-calendar')
    def calendar(reference: str, guests: int = 1, customer=Depends(require_customer)):
        if not 1 <= guests <= 99:
            raise HTTPException(422, 'reservation_group_limit')
        with database() as db:
            row = owned(db, reference, customer)
            booking = json.loads(row['payload'])['booking']
            value = visits.calendar_data(db, visits.now_local(), guests,
                'patch' if booking['plan'] == 'patch' else 'beads', exclude=reference)
            return value | {'reservation_version': row['version']}

    @app.post('/studio-api/reservations/{reference}/reschedule')
    def change(reference: str, payload: Change, customer=Depends(require_customer)):
        with database() as db:
            db.execute('BEGIN IMMEDIATE')
            row = owned(db, reference, customer)
            actor = 'customer:' + customer['id']
            fingerprint = digest(payload.model_dump(mode='json'))
            if replay(db, row, actor, payload.request_key, fingerprint):
                return {'reservation': visits.public_row(row), 'replayed': True}
            if row['version'] != payload.version:
                raise HTTPException(409, 'version_conflict')
            old_booking = json.loads(row['payload'])['booking']
            booking = visits.Visit(**payload.booking.model_dump(), plan=old_booking['plan'])
            current, policy = visits.now_local(), visits.read_policy(db)
            visits.validate_interval(booking, current, policy)
            if not visits.has_capacity(db, booking, policy, reference):
                raise HTTPException(409, 'reservation_confirmation_conflict')
            if booking.model_dump(mode='json') == old_booking and row['status'] in ('pending', 'confirmed'):
                record(db, row, row, actor, payload.request_key, fingerprint)
                return {'reservation': visits.public_row(row), 'unchanged': True}
            stamp = current.isoformat()
            reset_attendance = row['status'] == 'completed'
            updated_payload = booking_payload(row, booking)
            if reset_attendance:
                data = json.loads(updated_payload)
                data['previous_visit'] = snapshot(row)
                updated_payload = json.dumps(data, ensure_ascii=False)
            db.execute("""UPDATE studio_reservations SET payload=?,status='pending',version=version+1,updated_at=?,
              actual_minutes=CASE WHEN ? THEN NULL ELSE actual_minutes END,
              actual_guests=CASE WHEN ? THEN NULL ELSE actual_guests END WHERE id=?""",
              (updated_payload, stamp, reset_attendance, reset_attendance, reference))
            after = db.execute('SELECT * FROM studio_reservations WHERE id=?', (reference,)).fetchone()
            visits.patch_promotion.reconcile(db, after, stamp, actor, restoring=row['status'] == 'cancelled')
            resize_claim(db, after, actor, stamp)
            record(db, row, after, actor, payload.request_key, fingerprint, reset_attendance=reset_attendance)
            supersede_owner_alerts(db, reference)
            import owner_notifications
            owner_notifications.enqueue_reservation(db, 'changed', after, previous=old_booking)
            return {'reservation': visits.public_row(after)}
