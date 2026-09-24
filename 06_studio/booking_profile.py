"""Account-owned booking contact details, separate from login and wallet data."""
from datetime import datetime, timezone
import json
import re
from typing import Literal

from fastapi import Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator
from customer_auth import require_customer

METHODS = ('wechat', 'phone', 'email', 'other')


def valid_contact(method, value):
    minimum = 1 if method == 'wechat' else 3
    if method not in METHODS or not minimum <= len(value) <= 180:
        return False
    if method == 'phone':
        return bool(re.fullmatch(r'[+\d ()-]{7,30}', value)) and len(re.sub(r'\D', '', value)) >= 7
    if method == 'email':
        return bool(re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value))
    return True


class Details(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    name: str = Field(default='', max_length=80)
    contact_method: Literal['wechat', 'phone', 'email', 'other'] = 'wechat'
    contact: str = Field(default='', max_length=180)
    # Optional secondary contact. An older client omitting it must not erase it.
    wechat_id: str | None = Field(default=None, max_length=80)
    delivery_address: str | None = Field(default=None, max_length=500)

    @model_validator(mode='after')
    def contact_valid(self):
        if self.wechat_id and not re.fullmatch(r'[A-Za-z0-9_.-]{3,80}',self.wechat_id):
            raise ValueError('Provide a valid WeChat ID')
        # Both empty is an intentional clear. Never resurrect a cleared profile.
        if not self.name and not self.contact:
            return self
        if not self.name or not valid_contact(self.contact_method, self.contact):
            raise ValueError('Provide a name and valid contact details')
        return self


class Update(Details):
    version: int = Field(ge=0, strict=True)


def read(db, owner_id):
    row = db.execute('SELECT * FROM studio_booking_profiles WHERE owner_id=?', (owner_id,)).fetchone()
    value = dict(row) if row else dict(owner_id=owner_id, name='', contact_method='wechat', contact='', wechat_id='', delivery_address='', version=0, updated_at='', source_reservation_id='')
    return value | {'complete': bool(value['name'] and valid_contact(value['contact_method'], value['contact']))}


def save(db, owner_id, details, version, *, source='', actor=''):
    current = read(db, owner_id)
    values = {key: details[key] for key in ('name', 'contact_method', 'contact')}
    values['wechat_id']=details.get('wechat_id') if details.get('wechat_id') is not None else current.get('wechat_id','')
    values['delivery_address']=details.get('delivery_address') if details.get('delivery_address') is not None else current.get('delivery_address','')
    if current['version'] and all(current[key] == value for key, value in values.items()):
        return current
    if current['version'] != version:
        raise HTTPException(409, 'booking_profile_changed')
    stamp = datetime.now(timezone.utc).isoformat()
    db.execute('''INSERT INTO studio_booking_profiles(owner_id,name,contact_method,contact,wechat_id,delivery_address,version,updated_at,source_reservation_id)
      VALUES(?,?,?,?,?,?,1,?,?) ON CONFLICT(owner_id) DO UPDATE SET name=excluded.name,
      contact_method=excluded.contact_method,contact=excluded.contact,version=studio_booking_profiles.version+1,
      wechat_id=excluded.wechat_id,delivery_address=excluded.delivery_address,updated_at=excluded.updated_at,source_reservation_id=excluded.source_reservation_id''',
      (owner_id, values['name'], values['contact_method'], values['contact'], values['wechat_id'],values['delivery_address'],stamp, source))
    if actor:
        db.execute('INSERT INTO studio_audit(request_id,changed_at,actor,previous_status,new_status,staff_note) VALUES(?,?,?,?,?,?)',
                   (owner_id, stamp, actor, 'booking_profile', 'booking_profile', ''))
    return read(db, owner_id)


def capture(db, owner_id, details, version, reservation_id):
    """Called only inside the successful reservation transaction, after retry lookup."""
    if details.get('returning_customer') or not details.get('name') or not valid_contact(details.get('contact_method'), details.get('contact', '')):
        return
    current = read(db, owner_id)
    # Old clients can create the initial profile, but cannot overwrite a newer one.
    if version is None and current['version']:
        return
    save(db, owner_id, details, version or 0, source=reservation_id)


def initialize(database):
    with database() as db:
        db.executescript('''CREATE TABLE IF NOT EXISTS studio_booking_profiles (
          owner_id TEXT PRIMARY KEY, name TEXT NOT NULL DEFAULT '', contact_method TEXT NOT NULL DEFAULT 'wechat',
          contact TEXT NOT NULL DEFAULT '', version INTEGER NOT NULL DEFAULT 1,
          updated_at TEXT NOT NULL, source_reservation_id TEXT NOT NULL DEFAULT ''
        );''')
        if 'wechat_id' not in {r[1] for r in db.execute('PRAGMA table_info(studio_booking_profiles)')}:
            db.execute("ALTER TABLE studio_booking_profiles ADD COLUMN wechat_id TEXT NOT NULL DEFAULT ''")
        if 'delivery_address' not in {r[1] for r in db.execute('PRAGMA table_info(studio_booking_profiles)')}:
            db.execute("ALTER TABLE studio_booking_profiles ADD COLUMN delivery_address TEXT NOT NULL DEFAULT ''")
        db.execute('BEGIN IMMEDIATE')
        rows = db.execute('''SELECT r.owner_id,r.id,r.payload FROM studio_reservations r
          WHERE r.owner_id!='' AND r.deleted_at IS NULL
          AND NOT EXISTS(SELECT 1 FROM studio_booking_profiles p WHERE p.owner_id=r.owner_id)
          ORDER BY r.created_at DESC,r.id DESC''').fetchall()
        seen = set()
        for row in rows:
            if row['owner_id'] in seen:
                continue
            try:
                data = json.loads(row['payload'])
                # Only explicitly supplied contact info, not prior synthetic fallbacks.
                if data.get('returning_customer'):
                    continue
                details = Details(**{key: data.get(key, '') for key in ('name','contact_method','contact')})
                if not details.name or not details.contact:
                    continue
            except (ValueError, TypeError):
                continue
            save(db, row['owner_id'], details.model_dump(), 0, source=row['id'])
            seen.add(row['owner_id'])


def register(app, database, admin_actor):
    @app.get('/studio-api/auth/booking-profile')
    def own_profile(customer=Depends(require_customer)):
        with database() as db:
            return read(db, customer['id'])

    @app.put('/studio-api/auth/booking-profile')
    def update_profile(payload: Update, customer=Depends(require_customer)):
        with database() as db:
            db.execute('BEGIN IMMEDIATE')
            return save(db, customer['id'], payload.model_dump(), payload.version, actor=customer['id'])

    @app.put('/studio-api/manage/members/{owner_id}/booking-profile')
    def update_member_profile(owner_id: str, payload: Update, actor=Depends(admin_actor)):
        with database() as db:
            db.execute('BEGIN IMMEDIATE')
            if not db.execute('SELECT 1 FROM studio_members WHERE owner_id=?', (owner_id,)).fetchone():
                raise HTTPException(404, 'wallet_member_missing')
            return save(db, owner_id, payload.model_dump(), payload.version, actor=actor)
