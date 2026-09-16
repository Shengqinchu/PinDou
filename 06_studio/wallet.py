"""Studio time and loyalty ledgers. Identity comes from the verified shared account.

No payment collection: the host records verified offline transactions. All units
are integers; writes are append-only, serialized, versioned and idempotent.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import date, datetime
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

from fastapi import Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator

from customer_auth import require_customer, display_name
import booking_profile

_database = None
POINTS_PER_CAD = 100
VISIT_REWARD = 166
REGISTRATION_REWARD = 166
ZONE = ZoneInfo("America/Toronto")


def now():
    return datetime.now(ZONE).isoformat()


def initialize(database):
    with database() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS studio_members (
          owner_id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL DEFAULT '',
          minutes INTEGER NOT NULL DEFAULT 0 CHECK(minutes>=0),
          points INTEGER NOT NULL DEFAULT 0 CHECK(points>=0),
          version INTEGER NOT NULL DEFAULT 1, staff_note TEXT NOT NULL DEFAULT '',
          created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS studio_wallet_ledger (
          id INTEGER PRIMARY KEY AUTOINCREMENT, owner_id TEXT NOT NULL,
          created_at TEXT NOT NULL, effective_date TEXT NOT NULL, actor TEXT NOT NULL,
          kind TEXT NOT NULL, minutes_delta INTEGER NOT NULL, points_delta INTEGER NOT NULL,
          minutes_balance INTEGER NOT NULL, points_balance INTEGER NOT NULL,
          note TEXT NOT NULL, reservation_id TEXT NOT NULL DEFAULT '', bill_cents INTEGER,
          idempotency_key TEXT NOT NULL UNIQUE, request_hash TEXT NOT NULL,
          reverses_id INTEGER UNIQUE
        );
        CREATE INDEX IF NOT EXISTS studio_ledger_owner ON studio_wallet_ledger(owner_id,id DESC);
        CREATE TRIGGER IF NOT EXISTS studio_ledger_immutable_update BEFORE UPDATE ON studio_wallet_ledger
        BEGIN SELECT RAISE(ABORT, 'wallet ledger is append-only'); END;
        CREATE TRIGGER IF NOT EXISTS studio_ledger_immutable_delete BEFORE DELETE ON studio_wallet_ledger
        BEGIN SELECT RAISE(ABORT, 'wallet ledger is append-only'); END;
        CREATE TRIGGER IF NOT EXISTS wallet_self_booking_rewards
          BEFORE INSERT ON studio_wallet_ledger
          WHEN NEW.kind='visit_reward' AND NOT EXISTS (
            SELECT 1 FROM studio_reservations r WHERE r.id=NEW.reservation_id
              AND r.owner_id=NEW.owner_id AND r.creation_source IN ('customer_self','legacy_customer'))
          BEGIN SELECT RAISE(ABORT, 'visit reward requires a self booking'); END;
        """)
        columns={row[1] for row in db.execute('PRAGMA table_info(studio_wallet_ledger)')}
        if 'redemption_use' not in columns:
            db.execute("ALTER TABLE studio_wallet_ledger ADD COLUMN redemption_use TEXT NOT NULL DEFAULT ''")
        if 'no_promotion' not in columns:
            db.execute('ALTER TABLE studio_wallet_ledger ADD COLUMN no_promotion INTEGER')
        member_columns={r[1] for r in db.execute('PRAGMA table_info(studio_members)')}
        for name in ('avatar','customer_code'):
            if name not in member_columns:db.execute(f"ALTER TABLE studio_members ADD COLUMN {name} TEXT NOT NULL DEFAULT ''")
        db.execute("CREATE UNIQUE INDEX IF NOT EXISTS studio_customer_code ON studio_members(customer_code) WHERE customer_code!=''")
        # Existing stable user IDs only. Contact details are not identity proofs.
        db.execute("""INSERT OR IGNORE INTO studio_members(owner_id,name,created_at,updated_at)
          SELECT owner_id, coalesce(json_extract(payload,'$.name'),owner_id),min(created_at),max(updated_at)
          FROM studio_reservations WHERE owner_id!='' GROUP BY owner_id""")
        for row in db.execute("SELECT owner_id FROM studio_members WHERE customer_code='' ").fetchall():
            ensure_customer_code(db,row['owner_id'])


def ensure_customer_code(db, owner_id):
    digest=hashlib.sha256(owner_id.encode()).hexdigest().upper()
    for length in range(10,65,2):
        code='PD-'+digest[:length]
        other=db.execute('SELECT owner_id FROM studio_members WHERE customer_code=?',(code,)).fetchone()
        if not other or other['owner_id']==owner_id:
            db.execute("UPDATE studio_members SET customer_code=? WHERE owner_id=? AND customer_code=''",(code,owner_id))
            return code
    raise RuntimeError('Customer reference collision')


def remember_customer(customer):
    if _database is None:
        return
    with _database() as db:
        db.execute("BEGIN IMMEDIATE")
        existing = db.execute("SELECT name,email,avatar,customer_code FROM studio_members WHERE owner_id=?", (customer['id'],)).fetchone()
        name = customer.get('nickname') or (existing['name'] if existing else customer['email'])
        avatar=customer.get('avatar') or ''
        if not existing:
            db.execute("INSERT INTO studio_members(owner_id,name,email,avatar,created_at,updated_at) VALUES(?,?,?,?,?,?)",
                       (customer['id'], name, customer['email'], avatar, now(), now()))
        elif existing['email'] != customer['email'] or existing['name'] != name or existing['avatar']!=avatar:
            db.execute("UPDATE studio_members SET name=?,email=?,avatar=? WHERE owner_id=?", (name, customer['email'], avatar, customer['id']))
        customer['customer_code']=existing['customer_code'] if existing and existing['customer_code'] else ensure_customer_code(db,customer['id'])
        reward_registration(db,customer['id'])


def member(db, owner_id):
    row = db.execute("SELECT * FROM studio_members WHERE owner_id=?", (owner_id,)).fetchone()
    if row is None:
        raise HTTPException(404, 'wallet_member_missing')
    return dict(row)


def public_member(row):
    return {k: row[k] for k in ('owner_id', 'name', 'email', 'minutes', 'points', 'version', 'updated_at')} | {
        'name':display_name(row['owner_id'],row['name']),
        'avatar':row.get('avatar',''),'customer_code':row.get('customer_code',''),
        'redeemable_cad': row['points'] // POINTS_PER_CAD, 'points_per_cad': POINTS_PER_CAD,
        'visit_reward': VISIT_REWARD, 'registration_reward': REGISTRATION_REWARD,
    }


def staff_profile(db, row):
    profile=booking_profile.read(db,row['owner_id']);contacts=[]
    def add(kind,value):
        if value and not any(c['kind']==kind and c['value']==value for c in contacts):contacts.append({'kind':kind,'value':value})
    add(profile['contact_method'],profile['contact']);add('wechat',profile.get('wechat_id',''));add('email',row['email'])
    if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='studio_customer_notification_preferences'").fetchone():
        pref=db.execute('SELECT email,phone FROM studio_customer_notification_preferences WHERE owner_id=?',(row['owner_id'],)).fetchone()
        if pref:add('email',pref['email']);add('phone',pref['phone'])
    return {'booking_profile':profile,'contacts':contacts}


def detail(db, owner_id, page=1, category='all', admin=False):
    account = member(db, owner_id)
    clause = {'all':'', 'time':' AND minutes_delta!=0', 'points':' AND points_delta!=0'}[category]
    total = db.execute('SELECT count(*) FROM studio_wallet_ledger WHERE owner_id=?'+clause, (owner_id,)).fetchone()[0]
    rows = db.execute("""SELECT l.*, (SELECT id FROM studio_wallet_ledger r WHERE r.reverses_id=l.id) reversed_by
        FROM studio_wallet_ledger l WHERE owner_id=?"""+clause+' ORDER BY id DESC LIMIT 30 OFFSET ?', (owner_id, (page-1)*30)).fetchall()
    entries = []
    for row in rows:
        entry = {k: row[k] for k in ('id','created_at','effective_date','kind','minutes_delta','points_delta',
                 'minutes_balance','points_balance','note','reservation_id','bill_cents','reverses_id','reversed_by','redemption_use','no_promotion')}
        if admin: entry['actor'] = row['actor']
        entries.append(entry)
    return {'account': (account | public_member(account) | staff_profile(db,account)) if admin else public_member(account),
            'entries': entries, 'total': total, 'page': page, 'booking_profile':booking_profile.read(db,owner_id)}


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def append(db, owner_id, *, kind, minutes, points, note, actor, key, digest,
           effective_date=None, reservation_id='', bill_cents=None, reverses_id=None,redemption_use='',no_promotion=None):
    account = member(db, owner_id)
    remaining_minutes, remaining_points = account['minutes']+minutes, account['points']+points
    if min(remaining_minutes, remaining_points) < 0:
        raise HTTPException(409, 'wallet_insufficient_balance')
    if max(remaining_minutes, remaining_points) > 100_000_000:
        raise HTTPException(422, 'wallet_amount_too_large')
    stamp = now()
    cursor = db.execute("""INSERT INTO studio_wallet_ledger(owner_id,created_at,effective_date,actor,kind,
        minutes_delta,points_delta,minutes_balance,points_balance,note,reservation_id,bill_cents,
        idempotency_key,request_hash,reverses_id,redemption_use,no_promotion) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (owner_id,stamp,str(effective_date or stamp[:10]),actor,kind,minutes,points,remaining_minutes,
         remaining_points,note,reservation_id,bill_cents,key,digest,reverses_id,redemption_use,no_promotion))
    db.execute('UPDATE studio_members SET minutes=?,points=?,version=version+1,updated_at=? WHERE owner_id=?',
               (remaining_minutes,remaining_points,stamp,owner_id))
    return cursor.lastrowid


def reward_registration(db,owner_id):
    """One system entry per verified shared account, including an authorized backfill."""
    key='registration-reward:'+owner_id
    if db.execute('SELECT 1 FROM studio_wallet_ledger WHERE idempotency_key=?',(key,)).fetchone():return False
    append(db,owner_id,kind='registration_reward',minutes=0,points=REGISTRATION_REWARD,note='',
           actor='system:registration',key=key,digest=fingerprint({'owner_id':owner_id,'registration_points':REGISTRATION_REWARD}))
    return True


def reward_visit(db, row, actor):
    """Called inside the reservation transaction. Not backfilled on deployment."""
    # Read authoritative persisted provenance, never a form/payload flag. The
    # guard lives at the ledger boundary so later completion paths cannot bypass it.
    origin = db.execute('SELECT creation_source FROM studio_reservations WHERE id=?', (row['id'],)).fetchone()
    if not origin or origin['creation_source'] not in ('customer_self', 'legacy_customer'):
        return
    if not row['owner_id'] or row['actual_minutes'] is None or row['actual_minutes'] <= 0:
        return
    key = 'visit-reward:'+row['id']
    if db.execute('SELECT 1 FROM studio_wallet_ledger WHERE idempotency_key=?', (key,)).fetchone():
        return
    data = json.loads(row['payload'])
    if data['booking']['date'] > now()[:10]:
        raise HTTPException(422, 'wallet_visit_not_arrived')
    # May be a pre-upgrade reservation with a stable ID but no Studio login yet.
    db.execute('INSERT OR IGNORE INTO studio_members(owner_id,name,created_at,updated_at) VALUES(?,?,?,?)',
               (row['owner_id'], data['name'], now(), now()))
    append(db,row['owner_id'],kind='visit_reward',minutes=0,points=VISIT_REWARD,
           note='',actor=actor,key=key,digest=fingerprint({'visit':row['id'],'points':VISIT_REWARD}),
           effective_date=data['booking']['date'],reservation_id=row['id'])


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class Transaction(Strict):
    version: int = Field(ge=1, strict=True)
    kind: Literal['opening','topup','gift','usage','redeem','adjustment']
    minutes_delta: int = Field(default=0, ge=-1000000, le=1000000, strict=True)
    points_delta: int = Field(default=0, ge=-1000000, le=1000000, strict=True)
    note: str = Field(min_length=1, max_length=600)
    effective_date: date
    reservation_id: str = Field(default='', max_length=64)
    bill_cents: int | None = Field(default=None, ge=100, le=100000000, strict=True)
    redemption_use: Literal['visit','shop'] | None = None
    no_promotion: bool | None = Field(default=None,strict=True)

    @model_validator(mode='after')
    def amounts(self):
        m,p = self.minutes_delta,self.points_delta
        if m==0 and p==0: raise ValueError('No balance change')
        if self.effective_date > datetime.now(ZONE).date(): raise ValueError('Use a past or current date')
        if self.kind in ('opening','gift') and (m<0 or p<0): raise ValueError('Credits must be positive')
        if self.kind=='topup' and (m<=0 or p!=0): raise ValueError('Top-up requires time only')
        if self.kind=='usage' and (m>=0 or p!=0): raise ValueError('Usage requires a time debit')
        if self.kind=='redeem':
            if m or p>=0 or p%POINTS_PER_CAD or self.bill_cents is None or -p>self.bill_cents:
                raise ValueError('Redeem whole CAD within the verified bill amount')
        elif self.bill_cents is not None or self.redemption_use is not None or self.no_promotion is not None:
            raise ValueError('Redemption details are for redemption only')
        return self


class Reversal(Strict):
    version: int = Field(ge=1, strict=True)
    note: str = Field(min_length=1, max_length=600)


class MemberNote(Strict):
    version: int = Field(ge=1, strict=True)
    staff_note: str = Field(max_length=1500)


def validate_key(key):
    try: uuid.UUID(key)
    except ValueError: raise HTTPException(422, 'invalid_request_id') from None


def repeated(db, key, owner_id, digest):
    row = db.execute('SELECT owner_id,request_hash FROM studio_wallet_ledger WHERE idempotency_key=?',(key,)).fetchone()
    if row and (row['owner_id']!=owner_id or row['request_hash']!=digest):
        raise HTTPException(409,'wallet_request_changed')
    return row is not None


def register(app, database, admin_actor):
    global _database
    _database = database

    @app.get('/studio-api/auth/wallet')
    def own_wallet(page:int=1,category:Literal['all','time','points']='all',customer=Depends(require_customer)):
        if not 1<=page<=100000: raise HTTPException(422,'invalid_filter')
        with database() as db:
            db.execute('BEGIN')
            return detail(db,customer['id'],page,category)

    @app.get('/studio-api/manage/members')
    def members(search:str='',page:int=1,_actor=Depends(admin_actor)):
        if len(search)>160 or not 1<=page<=100000: raise HTTPException(422,'invalid_filter')
        where=' WHERE instr(lower(name),lower(?))>0 OR instr(lower(email),lower(?))>0 OR instr(owner_id,?)>0 OR instr(lower(staff_note),lower(?))>0 OR instr(lower(customer_code),lower(?))>0 OR owner_id IN (SELECT owner_id FROM studio_booking_profiles WHERE instr(lower(name),lower(?))>0 OR instr(lower(contact),lower(?))>0 OR instr(lower(wechat_id),lower(?))>0)'
        params=(search,)*8
        with database() as db:
            if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='studio_customer_notification_preferences'").fetchone():
                where+=' OR owner_id IN (SELECT owner_id FROM studio_customer_notification_preferences WHERE instr(lower(email),lower(?))>0 OR instr(phone,?)>0)'
                params+=(search,search)
            total=db.execute('SELECT count(*) FROM studio_members'+where,params).fetchone()[0]
            rows=db.execute('SELECT * FROM studio_members'+where+' ORDER BY updated_at DESC,owner_id LIMIT 30 OFFSET ?',(*params,(page-1)*30)).fetchall()
            return {'items':[public_member(dict(r))|{'staff_note':r['staff_note'],**staff_profile(db,r)} for r in rows],'total':total,'page':page}

    @app.get('/studio-api/manage/members/{owner_id}')
    def get_member(owner_id:str,page:int=1,category:Literal['all','time','points']='all',_actor=Depends(admin_actor)):
        if not 1<=page<=100000: raise HTTPException(422,'invalid_filter')
        with database() as db:
            db.execute('BEGIN')
            return detail(db,owner_id,page,category,True)

    @app.patch('/studio-api/manage/members/{owner_id}')
    @app.post('/studio-api/manage/members/{owner_id}/update')
    def update_note(owner_id:str,payload:MemberNote,actor=Depends(admin_actor)):
        with database() as db:
            db.execute('BEGIN IMMEDIATE')
            account=member(db,owner_id)
            if account['version']!=payload.version: raise HTTPException(409,'version_conflict')
            db.execute('UPDATE studio_members SET staff_note=?,version=version+1,updated_at=? WHERE owner_id=?',
                       (payload.staff_note,now(),owner_id))
            # Private notes do not belong in the customer's financial ledger.
            db.execute('INSERT INTO studio_audit(request_id,changed_at,actor,previous_status,new_status,staff_note) VALUES(?,?,?,?,?,?)',
                       (owner_id,now(),actor,'member_note','member_note',payload.staff_note))
            return detail(db,owner_id,admin=True)

    @app.post('/studio-api/manage/members/{owner_id}/transactions')
    def transaction(owner_id:str,payload:Transaction,idempotency_key:Annotated[str,Header()],actor=Depends(admin_actor)):
        validate_key(idempotency_key)
        data=payload.model_dump()
        # Keep successful pre-policy retries compatible with their original hash.
        for field in ('redemption_use','no_promotion'):
            if data[field] is None:data.pop(field)
        digest=fingerprint(data | {'owner_id':owner_id})
        with database() as db:
            db.execute('BEGIN IMMEDIATE')
            if repeated(db,idempotency_key,owner_id,digest): return detail(db,owner_id,admin=True)
            if payload.kind=='redeem':
                if payload.redemption_use is None:raise HTTPException(422,'wallet_redemption_use_required')
                if payload.no_promotion is not True:raise HTTPException(422,'wallet_promotion_confirmation_required')
            account=member(db,owner_id)
            if account['version']!=payload.version: raise HTTPException(409,'version_conflict')
            if payload.kind=='opening' and db.execute("SELECT 1 FROM studio_wallet_ledger WHERE owner_id=? AND kind!='registration_reward' LIMIT 1",(owner_id,)).fetchone():
                raise HTTPException(409,'wallet_opening_exists')
            if payload.reservation_id:
                row=db.execute('SELECT owner_id,status,deleted_at FROM studio_reservations WHERE id=?',(payload.reservation_id,)).fetchone()
                if row is None or row['owner_id']!=owner_id or row['deleted_at'] is not None:
                    raise HTTPException(422,'wallet_reservation_mismatch')
                if payload.kind in ('usage','redeem') and row['status']!='completed':
                    raise HTTPException(409,'wallet_reservation_incomplete')
            append(db,owner_id,kind=payload.kind,minutes=payload.minutes_delta,points=payload.points_delta,
                   note=payload.note,actor=actor,key=idempotency_key,digest=digest,
                   effective_date=payload.effective_date,reservation_id=payload.reservation_id,bill_cents=payload.bill_cents,
                   redemption_use=payload.redemption_use or '',no_promotion=payload.no_promotion)
            return detail(db,owner_id,admin=True)

    @app.post('/studio-api/manage/members/{owner_id}/entries/{entry_id}/reverse')
    def reverse(owner_id:str,entry_id:int,payload:Reversal,idempotency_key:Annotated[str,Header()],actor=Depends(admin_actor)):
        validate_key(idempotency_key)
        digest=fingerprint(payload.model_dump() | {'owner_id':owner_id,'reverses':entry_id})
        with database() as db:
            db.execute('BEGIN IMMEDIATE')
            if repeated(db,idempotency_key,owner_id,digest): return detail(db,owner_id,admin=True)
            account=member(db,owner_id)
            if account['version']!=payload.version: raise HTTPException(409,'version_conflict')
            row=db.execute('SELECT * FROM studio_wallet_ledger WHERE id=? AND owner_id=?',(entry_id,owner_id)).fetchone()
            if row is None: raise HTTPException(404,'wallet_entry_missing')
            if row['reverses_id'] is not None or db.execute('SELECT 1 FROM studio_wallet_ledger WHERE reverses_id=?',(entry_id,)).fetchone():
                raise HTTPException(409,'wallet_already_reversed')
            append(db,owner_id,kind='reversal',minutes=-row['minutes_delta'],points=-row['points_delta'],note=payload.note,
                   actor=actor,key=idempotency_key,digest=digest,reservation_id=row['reservation_id'],reverses_id=entry_id)
            return detail(db,owner_id,admin=True)
