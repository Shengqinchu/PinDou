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
from customer_auth import require_customer

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
        CREATE TABLE IF NOT EXISTS reservation_blocks (
          id TEXT PRIMARY KEY, date TEXT NOT NULL, start TEXT NOT NULL, end TEXT NOT NULL,
          note TEXT NOT NULL DEFAULT '', actor TEXT NOT NULL, version INTEGER NOT NULL DEFAULT 1,
          created_at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS blocks_day ON reservation_blocks(date,start);
        CREATE TABLE IF NOT EXISTS reservation_customer_cancellations (
          id INTEGER PRIMARY KEY, reservation_id TEXT NOT NULL, owner_id TEXT NOT NULL,
          from_version INTEGER NOT NULL, month TEXT NOT NULL, created_at TEXT NOT NULL,
          UNIQUE(reservation_id,from_version)
        );
        CREATE INDEX IF NOT EXISTS cancellation_owner_month
          ON reservation_customer_cancellations(owner_id,month);
        """)
        if "settings" not in {row[1] for row in db.execute("PRAGMA table_info(reservation_policy)")}:
            db.execute("ALTER TABLE reservation_policy ADD COLUMN settings TEXT NOT NULL DEFAULT '{}'")
        if "owner_id" not in {row[1] for row in db.execute("PRAGMA table_info(studio_reservations)")}:
            db.execute("ALTER TABLE studio_reservations ADD COLUMN owner_id TEXT NOT NULL DEFAULT ''")
        db.execute("CREATE INDEX IF NOT EXISTS reservation_owner ON studio_reservations(owner_id,created_at)")
        columns={row[1] for row in db.execute('PRAGMA table_info(studio_reservations)')}
        for name,definition in {
            'actual_minutes':'INTEGER', 'actual_guests':'INTEGER',
            'public_note':"TEXT NOT NULL DEFAULT ''", 'deleted_at':'TEXT',
        }.items():
            if name not in columns: db.execute(f'ALTER TABLE studio_reservations ADD COLUMN {name} {definition}')

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

def default_hours():
    return [{"weekday": i, "enabled": True, "open": "10:00", "close": {2:'16:00',3:'18:00'}.get(i,'22:00')} for i in range(7)]

def read_policy(db):
    row = dict(db.execute("SELECT * FROM reservation_policy WHERE id=1").fetchone())
    values = {"max_guests_per_group": 4, "max_concurrent_groups": None,
              "max_concurrent_guests": None, "weekly_hours": default_hours()}
    values.update(json.loads(row["settings"]))
    return values | {"exclusive_groups": bool(row["exclusive_groups"]), "version": row["version"]}

def hours(day, policy=None):
    return (policy or {"weekly_hours": default_hours()})["weekly_hours"][day.weekday()]

def closing(day, policy=None):
    return minute(hours(day, policy)["close"])

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
    guests: int = Field(ge=1, le=99, strict=True)

class Submission(Strict):
    booking: Visit
    name: str = Field(default="", max_length=80)
    contact_method: Literal["wechat", "phone", "email", "other"]
    contact: str = Field(default="", max_length=180)
    notes: str = Field(default="", max_length=1500)
    # New booking forms submit directly. Keep the optional legacy flag so an
    # already-saved request can be retried unchanged; never synthesize consent.
    consent: Literal[True] | None = None
    locale: Literal["zh", "en"] = "zh"
    website: str = Field(default="", max_length=0)
    offer: Literal['duo4h'] | None = None
    offer_revision: str | None = Field(default=None, pattern=r'^[a-f0-9]{64}$')
    contact_profile_version: int | None = Field(default=None, ge=0, strict=True)

    @model_validator(mode="after")
    def contact_valid(self):
        if not self.contact:return self
        if len(self.contact)<(1 if self.contact_method=='wechat' else 3):raise ValueError("Invalid contact")
        if self.contact_method == "phone" and (not re.fullmatch(r"[+\d ()-]{7,30}", self.contact) or len(re.sub(r"\D", "", self.contact)) < 7):
            raise ValueError("Invalid phone")
        if self.contact_method == "email" and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", self.contact):
            raise ValueError("Invalid email")
        return self

def validate_interval(booking, current, policy=None):
    start, end = minute(booking.start), minute(booking.end)
    opening = hours(booking.date, policy)
    if not current.date() <= booking.date < current.date() + timedelta(days=14):
        raise HTTPException(422, "reservation_outside_window")
    if not opening["enabled"] or start < minute(opening["open"]) or end > closing(booking.date, policy) or end - start < 120:
        raise HTTPException(422, "reservation_interval_unavailable")
    if policy and booking.guests > policy["max_guests_per_group"]:
        raise HTTPException(422, "reservation_group_limit")
    if booking.plan == "day" and end != closing(booking.date, policy):
        raise HTTPException(422, "reservation_day_end")
    if datetime.combine(booking.date, datetime.min.time(), tzinfo=ZONE) + timedelta(minutes=start) <= current:
        raise HTTPException(422, "reservation_in_past")

def overlaps(db, booking, exclude=""):
    rows = db.execute("SELECT id,payload FROM studio_reservations WHERE status='confirmed' AND id!=? AND json_extract(payload,'$.booking.date')=?", (exclude, str(booking.date))).fetchall()
    return any(minute(json.loads(r["payload"])["booking"]["start"]) < minute(booking.end)
               and minute(json.loads(r["payload"])["booking"]["end"]) > minute(booking.start) for r in rows)

def capacity_grid(confirmed, day, policy):
    """One authoritative half-hour map, independent of the requested group size."""
    group_limit = 1 if policy["exclusive_groups"] else policy["max_concurrent_groups"]
    people_limit = policy["max_concurrent_guests"]
    slots = {}
    for at in range(0, 1440, 30):
        present = [b for b in confirmed if b["date"] == str(day) and minute(b["start"]) < at + 30 and minute(b["end"]) > at]
        group_full = group_limit is not None and len(present) >= group_limit
        remaining = max(0, people_limit - sum(b["guests"] for b in present)) if people_limit is not None else None
        full = group_full or remaining == 0
        slots[at] = {"remaining_seats": 0 if group_full else remaining, "capacity_full": full}
    # Only genuinely full intervals create padding. Padding never creates more padding.
    full_slots = {at for at, slot in slots.items() if slot["capacity_full"]}
    for at, slot in slots.items():
        slot["buffered"] = not slot["capacity_full"] and (at - 30 in full_slots or at + 30 in full_slots)
        slot["low_capacity"] = not slot["buffered"] and slot["remaining_seats"] is not None and 0 < slot["remaining_seats"] <= 2
    return slots

def capacity_available(confirmed, day, start, end, guests, policy, *, include_buffer=True):
    slots = capacity_grid(confirmed, day, policy)
    return all(not slots[at]["capacity_full"]
               and (not include_buffer or not slots[at]["buffered"])
               and (slots[at]["remaining_seats"] is None or slots[at]["remaining_seats"] >= guests)
               for at in range(start, end, 30))

def has_capacity(db, booking, policy, exclude="", *, include_buffer=True):
    if db.execute('SELECT 1 FROM reservation_blocks WHERE date=? AND start<? AND end>? LIMIT 1', (str(booking.date),booking.end,booking.start)).fetchone():
        return False
    confirmed = [json.loads(r[0])["booking"] for r in db.execute("SELECT payload FROM studio_reservations WHERE status='confirmed' AND id!=? AND json_extract(payload,'$.booking.date')=?", (exclude, str(booking.date)))]
    return capacity_available(confirmed, booking.date, minute(booking.start), minute(booking.end), booking.guests, policy, include_buffer=include_buffer)

def available_offer(db, current):
    from pathlib import Path
    import content
    config = json.loads(Path(__file__).with_name('reservation-offers.json').read_text())['duo4h']
    if str(current.date()) > config['until']:
        return None
    rates = content.document_row(db, 'rate-fields')['published']
    words = content.document_row(db, 'pages-Visit')['published']
    value = {'id': 'duo4h', 'guests': 2, 'minutes': 240, 'until': config['until'],
             'amount': rates[config['price_key']][0], 'currency': 'CAD', 'label': words[config['name_key']]}
    value['revision'] = hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    return value


def validate_offer(db, payload, current):
    if not payload.offer:
        if payload.offer_revision:
            raise HTTPException(422, 'reservation_offer_invalid')
        return None
    value = available_offer(db, current)
    if not value or str(payload.booking.date) > value['until']:
        raise HTTPException(422, 'reservation_offer_expired')
    if payload.booking.plan != 'hourly' or payload.booking.guests != value['guests'] or minute(payload.booking.end)-minute(payload.booking.start) != value['minutes']:
        raise HTTPException(422, 'reservation_offer_invalid')
    if payload.offer_revision != value['revision']:
        raise HTTPException(409, 'reservation_offer_changed')
    return value


def public_row(row):
    data = json.loads(row["payload"])
    booking=data['booking']
    return {key: row[key] for key in ("id", "status", "created_at", "updated_at", "version", "actual_minutes", "actual_guests", "public_note")} | {
        "booking": booking, "name": data["name"],
        "booked_minutes": minute(booking['end'])-minute(booking['start']),
        "offer": data.get('offer_snapshot'),
        "can_cancel": self_cancellable(row,now_local()),
    }

def self_cancellable(row,current):
    booking=json.loads(row['payload'])['booking']
    starts=datetime.combine(date.fromisoformat(booking['date']),datetime.strptime(booking['start'],'%H:%M').time(),tzinfo=ZONE)
    return bool(row['owner_id'] and not row['deleted_at'] and row['status'] in ('pending','confirmed')
                and row['actual_minutes'] is None and starts>current)

def cancellation_policy(db,owner_id,row,current):
    current=current.astimezone(ZONE)
    month=current.strftime('%Y-%m')
    reset=(current.date().replace(day=1)+timedelta(days=32)).replace(day=1)
    used=db.execute('SELECT count(*) FROM reservation_customer_cancellations WHERE owner_id=? AND month=?',(owner_id,month)).fetchone()[0]
    reason='reservation_cancellation_unavailable' if not self_cancellable(row,current) else 'reservation_cancellation_limit' if used>=3 else None
    return {'limit':3,'used':used,'remaining':max(0,3-used),'month':month,'reset_date':str(reset),
            'timezone':str(ZONE),'eligible':reason is None,'reason':reason,'version':row['version']}

class CustomerCancellation(Strict):
    version: int = Field(ge=1,strict=True)

class ReservationUpdate(Strict):
    status: Literal["pending", "confirmed", "completed", "cancelled"]
    staff_note: str = Field(default="", max_length=1500)
    version: int = Field(ge=1)
    actual_minutes: int | None = Field(default=None, ge=1, le=1440, strict=True)
    actual_guests: int | None = Field(default=None, ge=1, le=99, strict=True)
    public_note: str = Field(default='',max_length=600)

class ReservationDeletion(Strict):
    version: int = Field(ge=1,strict=True)
    reason: str = Field(min_length=1,max_length=600)

class DayHours(Strict):
    weekday: int = Field(ge=0, le=6, strict=True)
    enabled: bool
    open: str = Field(pattern=r"^(?:[01]\d|2[0-3]):(?:00|30)$")
    close: str = Field(pattern=r"^(?:[01]\d|2[0-3]):(?:00|30)$")

    @model_validator(mode="after")
    def ordered(self):
        if self.enabled and minute(self.close) - minute(self.open) < 120:
            raise ValueError("Opening hours need at least two hours")
        return self


def returning_customer(db, owner_id, current):
    """Attendance is tied to the authenticated account, never a contact match."""
    day=str(current.date())
    completed=db.execute("""SELECT 1 FROM studio_reservations WHERE owner_id=?
      AND status='completed' AND actual_minutes>0 AND deleted_at IS NULL
      AND json_extract(payload,'$.booking.date')<=? LIMIT 1""",(owner_id,day)).fetchone()
    used=db.execute("""SELECT 1 FROM studio_wallet_ledger l WHERE owner_id=? AND effective_date<=?
      AND ((kind='usage' AND minutes_delta<0) OR kind='visit_reward')
      AND NOT EXISTS(SELECT 1 FROM studio_wallet_ledger r WHERE r.reverses_id=l.id) LIMIT 1""",(owner_id,day)).fetchone()
    return bool(completed or used)


def reservation_contact(db, payload, customer, current):
    if payload.name and payload.contact:return {}
    import booking_profile
    profile=booking_profile.read(db,customer['id'])
    if profile['complete']:
        return {**({'name':profile['name']} if not payload.name else {}),
                **({'contact':profile['contact'],'contact_method':profile['contact_method']} if not payload.contact else {})}
    if not returning_customer(db,customer['id'],current):
        raise HTTPException(422,'reservation_contact_required')
    # Resolve only this account's history. The request hash remains the original
    # blank input so a retry returns the original receipt after history changes.
    row=db.execute("""SELECT payload FROM studio_reservations WHERE owner_id=? AND deleted_at IS NULL
      AND status IN ('completed','confirmed','pending')
      AND length(json_extract(payload,'$.contact'))>=CASE WHEN json_extract(payload,'$.contact_method')='wechat' THEN 1 ELSE 3 END
      ORDER BY (status='completed') DESC,created_at DESC,id DESC LIMIT 1""",(customer['id'],)).fetchone()
    history=json.loads(row['payload']) if row else {}
    values={'returning_customer':True}
    if not payload.name:
        member=db.execute('SELECT name FROM studio_members WHERE owner_id=?',(customer['id'],)).fetchone()
        values['name']=(history.get('name') or customer.get('nickname') or (member['name'] if member else '') or customer.get('email') or customer['id'])[:80]
    if not payload.contact:
        values['contact']=history.get('contact') or customer.get('email') or ''
        values['contact_method']=history.get('contact_method') if history.get('contact') else 'email' if customer.get('email') else 'other'
    return values

class ReservationPolicy(Strict):
    exclusive_groups: bool = False  # Kept for old desk clients; new desk edits explicit limits.
    max_guests_per_group: int = Field(default=4, ge=1, le=99, strict=True)
    max_concurrent_groups: int | None = Field(default=None, ge=1, le=999, strict=True)
    max_concurrent_guests: int | None = Field(default=None, ge=1, le=999, strict=True)
    weekly_hours: list[DayHours] = Field(default_factory=lambda: [DayHours(**v) for v in default_hours()], min_length=7, max_length=7)
    version: int = Field(ge=1)

    @model_validator(mode="after")
    def weekdays(self):
        if sorted(day.weekday for day in self.weekly_hours) != list(range(7)):
            raise ValueError("Provide each weekday exactly once")
        self.weekly_hours.sort(key=lambda day: day.weekday)
        return self

class Block(Strict):
    date: date
    start: str = Field(pattern=r'^(?:[01]\d|2[0-3]):(?:00|30)$')
    end: str = Field(pattern=r'^(?:[01]\d|2[0-3]):(?:00|30)$')
    note: str = Field(default='',max_length=200)

    @model_validator(mode='after')
    def ordered(self):
        if minute(self.end)<=minute(self.start):raise ValueError('End must follow start')
        return self

def register(app, database, admin_actor):
    def owned_reservation(db,reference,customer):
        row=db.execute('SELECT * FROM studio_reservations WHERE id=?',(reference,)).fetchone()
        if not row or row['deleted_at'] or row['owner_id']!=customer['id']:
            raise HTTPException(404,'reservation_not_found')
        return row

    @app.get('/studio-api/reservations/{reference}/cancellation')
    def cancellation_details(reference:str,customer=Depends(require_customer)):
        with database() as db:
            row=owned_reservation(db,reference,customer)
            return cancellation_policy(db,customer['id'],row,now_local())

    @app.post('/studio-api/reservations/{reference}/cancel')
    def cancel_reservation(reference:str,payload:CustomerCancellation,customer=Depends(require_customer)):
        with database() as db:
            db.execute('BEGIN IMMEDIATE')
            row=owned_reservation(db,reference,customer)
            current=now_local().astimezone(ZONE)
            # A lost response can be retried without spending another cancellation.
            replay=db.execute('SELECT 1 FROM reservation_customer_cancellations WHERE reservation_id=? AND from_version=? AND owner_id=?',
                              (reference,payload.version,customer['id'])).fetchone()
            if row['status']=='cancelled' and replay:
                return {'reservation':public_row(row),'policy':cancellation_policy(db,customer['id'],row,current)}
            if row['version']!=payload.version:raise HTTPException(409,'version_conflict')
            policy=cancellation_policy(db,customer['id'],row,current)
            if policy['reason']:raise HTTPException(409,policy['reason'])
            timestamp=current.isoformat()
            db.execute("UPDATE studio_reservations SET status='cancelled',version=version+1,updated_at=? WHERE id=?",(timestamp,reference))
            db.execute('INSERT INTO reservation_customer_cancellations(reservation_id,owner_id,from_version,month,created_at) VALUES(?,?,?,?,?)',
                       (reference,customer['id'],payload.version,policy['month'],timestamp))
            db.execute("INSERT INTO reservation_events(reservation_id,actor,created_at,status,note) VALUES(?,?,?,'cancelled','')",
                       (reference,'customer:'+customer['id'],timestamp))
            row=db.execute('SELECT * FROM studio_reservations WHERE id=?',(reference,)).fetchone()
            import owner_notifications
            owner_notifications.enqueue_reservation(db,'cancelled',row)
            return {'reservation':public_row(row),'policy':cancellation_policy(db,customer['id'],row,current)}

    @app.get('/studio-api/auth/reservation-context')
    def contact_context(customer=Depends(require_customer)):
        with database() as db:
            import booking_profile
            profile=booking_profile.read(db,customer['id'])
            return {'can_omit_details':profile['complete'] or returning_customer(db,customer['id'],now_local()),'profile':profile}

    @app.get("/studio-api/reservation-calendar")
    def calendar(request: Request, response: Response, guests: int = 1):
        visitor(request, response)
        current = now_local()
        if not 1 <= guests <= 99:
            raise HTTPException(422, "reservation_group_limit")
        with database() as db:
            settings = read_policy(db)
            offer = available_offer(db, current)
            confirmed = [json.loads(r[0])["booking"] for r in db.execute("SELECT payload FROM studio_reservations WHERE status='confirmed' AND json_extract(payload,'$.booking.date')>=?", (str(current.date()),))]
            blocks = [dict(r) for r in db.execute('SELECT date,start,end FROM reservation_blocks WHERE date>=?', (str(current.date()),))]
        enabled = [h for h in settings["weekly_hours"] if h["enabled"]]
        grid_start = min((minute(h["open"]) for h in enabled), default=600)
        grid_end = max((minute(h["close"]) for h in enabled), default=1320)
        days = []
        for n in range(14):
            day = current.date() + timedelta(days=n)
            slots = []
            opening = hours(day, settings)
            capacity = capacity_grid(confirmed, day, settings)
            for start in range(grid_start, grid_end, 30):
                past = datetime.combine(day, datetime.min.time(), tzinfo=ZONE) + timedelta(minutes=start) <= current
                state = capacity[start]
                busy = state["capacity_full"] or state["remaining_seats"] is not None and state["remaining_seats"] < guests
                closed = not opening["enabled"] or start < minute(opening["open"]) or start >= minute(opening["close"]) or any(b['date']==str(day) and minute(b['start'])<start+30 and minute(b['end'])>start for b in blocks)
                reason = "closed" if closed else "past" if past else "capacity" if busy or guests > settings["max_guests_per_group"] else "buffer" if state["buffered"] else None
                slots.append({**state, "start": clock(start), "end": clock(start + 30), "available": reason is None, "reason": reason,
                              "low_capacity": state["low_capacity"] and not closed and not past})
            days.append({"date": str(day), "open": opening["open"], "close": opening["close"], "closed": not opening["enabled"], "slots": slots})
        return {"today": str(current.date()), "timezone": "America/Toronto", "minimum_minutes": 120, "capacity_buffer_minutes": 30, "max_guests_per_group": settings["max_guests_per_group"], "weekly_hours": settings["weekly_hours"], "policy_version": settings["version"], "days": days, "offers": [offer] if offer and settings['max_guests_per_group'] >= 2 else []}

    @app.post("/studio-api/reservations", status_code=201)
    def submit(payload: Submission, request: Request, idempotency_key: Annotated[str, Header()], customer=Depends(require_customer)):
        try:
            uuid.UUID(idempotency_key)
        except ValueError:
            raise HTTPException(422, "invalid_request_id")
        actor = visitor(request)
        # Keep the pre-offer canonical representation for existing request keys.
        excluded={'offer', 'offer_revision'} if not payload.offer and not payload.offer_revision else set()
        if payload.contact_profile_version is None:excluded.add('contact_profile_version')
        encoded = payload.model_dump_json(exclude=excluded)
        digest = hashlib.sha256(encoded.encode()).hexdigest()
        current = now_local()
        with database() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute("SELECT * FROM studio_reservations WHERE idempotency_key=?", (idempotency_key,)).fetchone()
            if existing:
                wrong_owner = existing["owner_id"] != customer["id"] if existing["owner_id"] else existing["visitor_hash"] != actor
                if wrong_owner or existing["payload_hash"] != digest:
                    raise HTTPException(409, "reservation_request_changed")
                return public_row(existing)
            contact=reservation_contact(db,payload,customer,current)
            settings = read_policy(db)
            validate_interval(payload.booking, current, settings)
            offer = validate_offer(db, payload, current)
            if not has_capacity(db, payload.booking, settings):
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
            stored = json.dumps(json.loads(encoded) | contact | ({'offer_snapshot': offer} if offer else {}), ensure_ascii=False, separators=(',', ':')) if offer or contact else encoded
            db.execute("INSERT INTO studio_reservations(id,created_at,updated_at,payload,visitor_hash,idempotency_key,payload_hash,owner_id) VALUES(?,?,?,?,?,?,?,?)", (ref,timestamp,timestamp,stored,actor,idempotency_key,digest,customer["id"]))
            import booking_profile
            booking_profile.capture(db,customer['id'],json.loads(stored),payload.contact_profile_version,ref)
            row = db.execute("SELECT * FROM studio_reservations WHERE id=?", (ref,)).fetchone()
            import owner_notifications
            owner_notifications.enqueue_reservation(db, 'created', row)
            return public_row(row)

    @app.get("/studio-api/reservations/{reference}")
    def receipt(reference: str, request: Request, authorization: Annotated[str | None, Header()]=None):
        with database() as db:
            row = db.execute("SELECT * FROM studio_reservations WHERE id=?", (reference,)).fetchone()
        if not row or row['deleted_at']:
            raise HTTPException(404, "reservation_not_found")
        if row["owner_id"]:
            if require_customer(request,authorization)["id"]!=row["owner_id"]:
                raise HTTPException(404,"reservation_not_found")
        else:
            try: actor=visitor(request)
            except HTTPException: raise HTTPException(404,"reservation_not_found") from None
            if row["visitor_hash"]!=actor:raise HTTPException(404,"reservation_not_found")
        return public_row(row)

    @app.get("/studio-api/auth/reservations")
    def my_reservations(page:int=1,customer=Depends(require_customer)):
        if not 1<=page<=100000: raise HTTPException(422,'invalid_filter')
        with database() as db:
            rows=db.execute("SELECT * FROM studio_reservations WHERE owner_id=? AND deleted_at IS NULL ORDER BY created_at DESC,id DESC LIMIT 30 OFFSET ?",(customer["id"],(page-1)*30)).fetchall()
            total=db.execute('SELECT count(*) FROM studio_reservations WHERE owner_id=? AND deleted_at IS NULL',(customer['id'],)).fetchone()[0]
        return {"items":[public_row(row) for row in rows],'total':total,'page':page}

    @app.get("/studio-api/manage/reservations")
    def listing(_actor=Depends(admin_actor), status: str="all", day: date | None=None, search: str="", page: int=1, deleted:bool=False, at:str=""):
        if status not in STATES | {"all"} or not 1 <= page <= 10000 or len(search) > 120:
            raise HTTPException(422, "invalid_filter")
        clauses, params = ['deleted_at IS NOT NULL' if deleted else 'deleted_at IS NULL'], []
        if status != "all": clauses.append("status=?"); params.append(status)
        if day: clauses.append("json_extract(payload,'$.booking.date')=?"); params.append(str(day))
        if at:
            if not day or deleted or not re.fullmatch(r'\d{2}:\d{2}',at): raise HTTPException(422,'invalid_filter')
            end=clock(minute(at)+30)
            clauses.extend(["status IN ('pending','confirmed','completed')","json_extract(payload,'$.booking.start')<?","json_extract(payload,'$.booking.end')>?"])
            params.extend([end,at])
        if search: clauses.append("(instr(lower(json_extract(payload,'$.name')),lower(?))>0 OR instr(id,?)>0)"); params.extend([search,search])
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with database() as db:
            count = db.execute("SELECT count(*) FROM studio_reservations"+where, params).fetchone()[0]
            rows = db.execute("SELECT * FROM studio_reservations"+where+" ORDER BY created_at DESC,id DESC LIMIT 30 OFFSET ?", (*params,(page-1)*30)).fetchall()
            counts = dict(db.execute("SELECT status,count(*) FROM studio_reservations WHERE deleted_at IS NULL GROUP BY status").fetchall())
            policy = read_policy(db)
        return {"items":[public_row(r) | {"payload":json.loads(r["payload"]),"staff_note":r["staff_note"],'owner_id':r['owner_id'],'deleted_at':r['deleted_at']} for r in rows], "total":count,"counts":counts,"policy":policy}

    @app.get('/studio-api/manage/reservation-timetable')
    def timetable(_actor=Depends(admin_actor),start:date|None=None):
        first=start or now_local().date();last=first+timedelta(days=14)
        with database() as db:
            policy=read_policy(db)
            # Aggregate every overlapping booking, independently of the list's 30-row pagination.
            rows=db.execute("SELECT r.*,m.name AS member_name,m.staff_note AS member_note FROM studio_reservations r LEFT JOIN studio_members m ON m.owner_id=r.owner_id WHERE r.deleted_at IS NULL AND r.status IN ('pending','confirmed','completed') AND json_extract(r.payload,'$.booking.date')>=? AND json_extract(r.payload,'$.booking.date')<? ORDER BY r.id",(str(first),str(last))).fetchall()
            blocks=[dict(r) for r in db.execute('SELECT date,start,end FROM reservation_blocks WHERE date>=? AND date<?',(str(first),str(last)))]
        days=[]
        booked=[(r['status'],json.loads(r['payload'])['booking']) for r in rows]
        groups=[]
        for row in rows:
            data=json.loads(row['payload'])
            note='\n'.join(dict.fromkeys(n.strip() for n in (row['member_note'] or '',row['staff_note'],data.get('notes','')) if n.strip()))
            groups.append({'id':row['id'],'status':row['status'],'name':data.get('name') or row['member_name'] or row['id'],'note':note,**data['booking']})
        for index in range(14):
            day=first+timedelta(days=index);opening=hours(day,policy);slots=[]
            present=[(s,b) for s,b in booked if b['date']==str(day)]
            capacity=capacity_grid([b for s,b in present if s=='confirmed'],day,policy)
            for at in range(0,1440,30):
                begin,end=clock(at),clock(at+30)
                slot={**capacity[at],'start':begin,'end':end,'closed':not opening['enabled'] or begin<opening['open'] or end>opening['close'],
                      'blocked':any(b['date']==str(day) and b['start']<end and b['end']>begin for b in blocks)}
                slot['low_capacity']=slot['low_capacity'] and not slot['closed'] and not slot['blocked']
                for state in ('pending','confirmed','completed'):
                    overlaps=[b for s,b in present if s==state and b['start']<end and b['end']>begin]
                    slot[state]=sum(b['guests'] for b in overlaps);slot[state+'_groups']=len(overlaps)
                slots.append(slot)
            days.append({'date':str(day),'open':opening['open'],'close':opening['close'],'closed':not opening['enabled'],'slots':slots,
                         'bookings':[g for g in groups if g['date']==str(day)]})
        return {'days':days,'timezone':str(ZONE),'policy_version':policy['version'],'capacity_buffer_minutes':30}

    @app.patch("/studio-api/manage/reservations/{reference}")
    @app.post("/studio-api/manage/reservations/{reference}/update")
    def update(reference: str, payload: ReservationUpdate, actor=Depends(admin_actor)):
        current = now_local()
        with database() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM studio_reservations WHERE id=?", (reference,)).fetchone()
            if not row or row['deleted_at']: raise HTTPException(404,"reservation_not_found")
            if row["version"] != payload.version: raise HTTPException(409,"version_conflict")
            if payload.status == "confirmed" and row["status"] != "confirmed":
                booking = Visit(**json.loads(row["payload"])["booking"])
                settings = read_policy(db)
                validate_interval(booking, current, settings)
                if not has_capacity(db, booking, settings, reference):
                    raise HTTPException(409,"reservation_confirmation_conflict")
            if payload.status == "completed" and row["status"] not in ("confirmed","completed"):
                raise HTTPException(409,"reservation_not_confirmed")
            actual=payload.actual_minutes if 'actual_minutes' in payload.model_fields_set else row['actual_minutes']
            guests=payload.actual_guests if 'actual_guests' in payload.model_fields_set else row['actual_guests']
            public_note=payload.public_note if 'public_note' in payload.model_fields_set else row['public_note']
            if {'actual_minutes','actual_guests'} & payload.model_fields_set and (actual is None)!=(guests is None):
                raise HTTPException(422,'wallet_actual_details_required')
            # Once attendance has earned points, status cannot quietly erase the visit.
            earned=db.execute('SELECT 1 FROM studio_wallet_ledger l WHERE idempotency_key=? AND NOT EXISTS(SELECT 1 FROM studio_wallet_ledger r WHERE r.reverses_id=l.id)',('visit-reward:'+reference,)).fetchone()
            if earned and (payload.status!='completed' or actual is None):
                raise HTTPException(409,'wallet_completed_record_locked')
            if payload.status=='completed' and (not actual or not guests):
                raise HTTPException(422,'wallet_actual_hours_details_required')
            db.execute("UPDATE studio_reservations SET status=?,staff_note=?,actual_minutes=?,actual_guests=?,public_note=?,version=version+1,updated_at=? WHERE id=?", (payload.status,payload.staff_note,actual,guests,public_note,current.isoformat(),reference))
            if payload.status=='completed':
                from wallet import reward_visit
                reward_visit(db,db.execute('SELECT * FROM studio_reservations WHERE id=?',(reference,)).fetchone(),actor)
                from studio_finance import from_completed
                from_completed(db,db.execute('SELECT * FROM studio_reservations WHERE id=?',(reference,)).fetchone(),actor)
            db.execute("INSERT INTO reservation_events(reservation_id,actor,created_at,status,note) VALUES(?,?,?,?,?)", (reference,actor,current.isoformat(),payload.status,payload.staff_note))
            if payload.status!=row['status'] and payload.status in ('confirmed','cancelled'):
                import customer_notifications
                customer_notifications.on_reservation(db,payload.status,db.execute('SELECT * FROM studio_reservations WHERE id=?',(reference,)).fetchone())
            if (actual,guests,public_note)!=(row['actual_minutes'],row['actual_guests'],row['public_note']):
                db.execute('INSERT INTO reservation_events(reservation_id,actor,created_at,status,note) VALUES(?,?,?,?,?)',
                    (reference,actor,current.isoformat(),'attendance',json.dumps({'minutes':actual,'guests':guests,'public_note':public_note},ensure_ascii=False)))
        return {"id":reference,"status":payload.status,"version":payload.version+1}

    @app.delete('/studio-api/manage/reservations/{reference}')
    def remove_reservation(reference:str,payload:ReservationDeletion,actor=Depends(admin_actor)):
        with database() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT * FROM studio_reservations WHERE id=?',(reference,)).fetchone()
            if row is None: raise HTTPException(404,'reservation_not_found')
            if row['deleted_at']: return {'deleted':True}
            if row['version']!=payload.version: raise HTTPException(409,'version_conflict')
            if row['status']=='confirmed': raise HTTPException(409,'reservation_cancel_before_delete')
            db.execute('UPDATE studio_reservations SET deleted_at=?,updated_at=?,version=version+1 WHERE id=?',(now_local().isoformat(),now_local().isoformat(),reference))
            db.execute('INSERT INTO reservation_events(reservation_id,actor,created_at,status,note) VALUES(?,?,?,?,?)',(reference,actor,now_local().isoformat(),'deleted',payload.reason))
        return {'deleted':True}

    @app.post('/studio-api/manage/reservations/{reference}/restore')
    def restore_reservation(reference:str,payload:ReservationDeletion,actor=Depends(admin_actor)):
        with database() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT * FROM studio_reservations WHERE id=?',(reference,)).fetchone()
            if row is None: raise HTTPException(404,'reservation_not_found')
            if not row['deleted_at']: return {'restored':True}
            if row['version']!=payload.version: raise HTTPException(409,'version_conflict')
            db.execute('UPDATE studio_reservations SET deleted_at=NULL,updated_at=?,version=version+1 WHERE id=?',(now_local().isoformat(),reference))
            db.execute('INSERT INTO reservation_events(reservation_id,actor,created_at,status,note) VALUES(?,?,?,?,?)',(reference,actor,now_local().isoformat(),'restored',payload.reason))
        return {'restored':True}

    @app.get("/studio-api/manage/reservation-policy")
    def get_policy(_actor=Depends(admin_actor)):
        with database() as db:
            return read_policy(db)

    @app.get('/studio-api/manage/reservation-blocks')
    def list_blocks(_actor=Depends(admin_actor)):
        with database() as db:
            rows=[dict(r) for r in db.execute('SELECT * FROM reservation_blocks WHERE date>=? ORDER BY date,start LIMIT 1000',(str(now_local().date()),))]
        return {'items':rows}

    @app.post('/studio-api/manage/reservation-blocks',status_code=201)
    def add_block(payload:Block,actor=Depends(admin_actor)):
        if not now_local().date()<=payload.date<=now_local().date()+timedelta(days=365):raise HTTPException(422,'block_invalid_date')
        with database() as db:
            db.execute('BEGIN IMMEDIATE')
            confirmed=db.execute("SELECT payload FROM studio_reservations WHERE status='confirmed' AND json_extract(payload,'$.booking.date')=?",(str(payload.date),)).fetchall()
            if any(json.loads(r[0])['booking']['start']<payload.end and json.loads(r[0])['booking']['end']>payload.start for r in confirmed):
                raise HTTPException(409,'block_confirmed_conflict')
            ident=uuid.uuid4().hex
            db.execute('INSERT INTO reservation_blocks(id,date,start,end,note,actor,created_at) VALUES(?,?,?,?,?,?,?)',(ident,str(payload.date),payload.start,payload.end,payload.note,actor,now_local().isoformat()))
            db.execute("UPDATE reservation_policy SET version=version+1 WHERE id=1")
        return {'id':ident,'version':1}

    @app.delete('/studio-api/manage/reservation-blocks/{ident}')
    def remove_block(ident:str,version:int,actor=Depends(admin_actor)):
        with database() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT version FROM reservation_blocks WHERE id=?',(ident,)).fetchone()
            if not row:raise HTTPException(404,'block_not_found')
            if row[0]!=version:raise HTTPException(409,'version_conflict')
            db.execute('DELETE FROM reservation_blocks WHERE id=?',(ident,))
            db.execute("UPDATE reservation_policy SET version=version+1 WHERE id=1")
        return {'removed':True}

    @app.get('/studio-api/manage/reservation-notifications')
    def notifications(after:int=0,_actor=Depends(admin_actor)):
        if after<0:raise HTTPException(422,'invalid_filter')
        with database() as db:
            latest=db.execute('SELECT coalesce(max(rowid),0) FROM studio_reservations').fetchone()[0]
            new=db.execute('SELECT count(*) FROM studio_reservations WHERE rowid>? AND deleted_at IS NULL',(after,)).fetchone()[0]
            pending=db.execute("SELECT count(*) FROM studio_reservations WHERE status='pending' AND deleted_at IS NULL").fetchone()[0]
        return {'cursor':latest,'new_count':new,'pending':pending}

    @app.put("/studio-api/manage/reservation-policy")
    def policy(payload: ReservationPolicy, _actor=Depends(admin_actor)):
        with database() as db:
            db.execute("BEGIN IMMEDIATE")
            current = read_policy(db)
            if current["version"] != payload.version: raise HTTPException(409,"version_conflict")
            settings = ReservationPolicy(**(current | payload.model_dump(exclude_unset=True))).model_dump()
            future = db.execute("SELECT id,payload FROM studio_reservations WHERE status='confirmed' AND json_extract(payload,'$.booking.date')>=?", (str(now_local().date()),)).fetchall()
            for row in future:
                booking = Visit(**json.loads(row["payload"])["booking"])
                opening = hours(booking.date, settings)
                # New buffers must not retroactively invalidate accepted visits.
                if (not opening["enabled"] or booking.start < opening["open"] or booking.end > opening["close"] or booking.guests > settings["max_guests_per_group"] or not has_capacity(db, booking, settings, row["id"], include_buffer=False)):
                    raise HTTPException(409, "reservation_policy_conflict")
            encoded = {k:v for k,v in settings.items() if k not in ("exclusive_groups", "version")}
            db.execute("UPDATE reservation_policy SET exclusive_groups=?,settings=?,version=version+1 WHERE id=1", (settings["exclusive_groups"], json.dumps(encoded)))
            return read_policy(db)
