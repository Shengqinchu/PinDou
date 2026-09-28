"""Editable operational cash records, separate from customer wallet balances."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import time
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
import finance_fx

COPY_PATH = Path(__file__).with_name('business-copy.json')
if not COPY_PATH.exists():
    COPY_PATH = Path(__file__).resolve().parents[1] / '05_studio/src/content/business.json'


def words(key):
    return json.loads(COPY_PATH.read_text(encoding='utf-8'))[key]


def initialize(database):
    with database() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS studio_finance_categories (
          id TEXT PRIMARY KEY, zh TEXT NOT NULL, en TEXT NOT NULL,
          created_at REAL NOT NULL, actor TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS studio_finance_entries (
          id TEXT PRIMARY KEY, kind TEXT NOT NULL CHECK(kind IN ('income','expense')),
          category TEXT NOT NULL, occurred_on TEXT NOT NULL, customer_name TEXT NOT NULL DEFAULT '',
          items TEXT NOT NULL, amount_cents INTEGER CHECK(amount_cents IS NULL OR amount_cents>=0),
          payment_method TEXT NOT NULL DEFAULT '', note TEXT NOT NULL DEFAULT '',
          reservation_id TEXT UNIQUE, source TEXT NOT NULL, request_id TEXT UNIQUE,
          request_hash TEXT NOT NULL DEFAULT '', version INTEGER NOT NULL DEFAULT 1,
          created_at REAL NOT NULL, updated_at REAL NOT NULL, deleted_at REAL, actor TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS studio_finance_date ON studio_finance_entries(occurred_on,kind);
        CREATE TABLE IF NOT EXISTS studio_finance_events (
          id INTEGER PRIMARY KEY, entry_id TEXT NOT NULL, actor TEXT NOT NULL,
          action TEXT NOT NULL, created_at REAL NOT NULL, snapshot TEXT NOT NULL
        );
        CREATE TRIGGER IF NOT EXISTS studio_finance_history_update BEFORE UPDATE ON studio_finance_events
          BEGIN SELECT RAISE(ABORT,'finance history is append-only'); END;
        CREATE TRIGGER IF NOT EXISTS studio_finance_history_delete BEFORE DELETE ON studio_finance_events
          BEGIN SELECT RAISE(ABORT,'finance history is append-only'); END;
        """)
        columns={r['name'] for r in db.execute('PRAGMA table_info(studio_finance_entries)')}
        for name,definition in [('currency',"TEXT NOT NULL DEFAULT 'CAD'"),('fx_rate',"TEXT DEFAULT '1'"),
                                ('fx_date','TEXT'),('fx_source',"TEXT NOT NULL DEFAULT 'identity'"),('cad_amount_cents','INTEGER')]:
            if name not in columns:
                db.execute(f'ALTER TABLE studio_finance_entries ADD COLUMN {name} {definition}')
        if 'cad_amount_cents' not in columns:
            db.execute('UPDATE studio_finance_entries SET cad_amount_cents=amount_cents')
        finance_fx.initialize(db)
        for code in ('experience', 'finished', 'other'):
            zh,en = words(code)
            db.execute('INSERT OR IGNORE INTO studio_finance_categories VALUES(?,?,?,?,?)', (code,zh,en,time.time(),'initial'))
        # A completed visit has no trustworthy cash amount in the old schema.
        # Import a single editable draft, never infer payment from advertised rates.
        rows = db.execute("""SELECT * FROM studio_reservations r WHERE r.status='completed' AND r.deleted_at IS NULL
          AND NOT EXISTS(SELECT 1 FROM studio_finance_entries f WHERE f.reservation_id=r.id)""").fetchall()
        for row in rows:
            from_completed(db, row, 'completed-visit-import')


def public(row):
    result = dict(row)
    result['items'] = json.loads(result['items'])
    result.pop('request_hash',None);result.pop('request_id',None)
    result['needs_amount'] = result['amount_cents'] is None
    return result


def audit(db, ident, actor, action):
    row = db.execute('SELECT * FROM studio_finance_entries WHERE id=?',(ident,)).fetchone()
    db.execute('INSERT INTO studio_finance_events(entry_id,actor,action,created_at,snapshot) VALUES(?,?,?,?,?)',
        (ident,actor,action,time.time(),json.dumps(public(row),ensure_ascii=False)))


def from_completed(db, row, actor):
    if row['status']!='completed' or row['deleted_at']:
        return
    if db.execute('SELECT 1 FROM studio_finance_entries WHERE reservation_id=?',(row['id'],)).fetchone():
        return
    payload=json.loads(row['payload']);booking=payload['booking']
    item=words('patch' if booking.get('plan')=='patch' else 'duo4h' if payload.get('offer')=='duo4h' else 'day' if booking.get('plan')=='day' else 'hourly')[0]
    ident='FIN-'+uuid.uuid4().hex;stamp=time.time()
    db.execute("""INSERT OR IGNORE INTO studio_finance_entries
      (id,kind,category,occurred_on,customer_name,items,amount_cents,reservation_id,source,created_at,updated_at,actor)
      VALUES(?,'income','experience',?,?,?,NULL,?,'reservation',?,?,?)""",
      (ident,booking['date'],payload.get('name',''),json.dumps([item],ensure_ascii=False),row['id'],stamp,stamp,actor))
    if db.execute('SELECT 1 FROM studio_finance_entries WHERE id=?',(ident,)).fetchone():
        audit(db,ident,actor,'import')


def summary(db, start, end):
    row=db.execute("""SELECT
      coalesce(sum(CASE WHEN kind='income' THEN cad_amount_cents ELSE 0 END),0) AS income_cents,
      coalesce(sum(CASE WHEN kind='expense' THEN cad_amount_cents ELSE 0 END),0) AS expense_cents,
      sum(CASE WHEN amount_cents IS NULL THEN 1 ELSE 0 END) AS needs_amount
      FROM studio_finance_entries WHERE deleted_at IS NULL AND occurred_on>=? AND occurred_on<=?""",(start,end)).fetchone()
    result=dict(row);result['needs_amount']=result['needs_amount'] or 0;result['currency']='CAD'
    result['balance_cents']=result['income_cents']-result['expense_cents']
    result['categories']=[dict(r) for r in db.execute("""SELECT category,coalesce(sum(cad_amount_cents),0) AS amount_cents
      FROM studio_finance_entries WHERE deleted_at IS NULL AND kind='income' AND occurred_on>=? AND occurred_on<=? GROUP BY category""",(start,end))]
    return result


class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)


class Entry(Strict):
    kind: Literal['income','expense']
    category: str = Field(default='experience',max_length=64)
    occurred_on: date
    customer_name: str = Field(default='',max_length=120)
    items: list[str] = Field(min_length=1,max_length=50)
    amount_cents: int | None = Field(default=None,ge=0,le=100000000,strict=True)
    currency: Literal['CAD','CNY'] | None = None
    payment_method: str = Field(default='',max_length=80)
    note: str = Field(default='',max_length=1000)

    @field_validator('items')
    @classmethod
    def item_text(cls,values):
        values=[v.strip() for v in values]
        if any(not v or len(v)>200 or any(ord(c)<32 for c in v) for v in values):raise ValueError('Invalid item')
        return values


class NewEntry(Entry):
    request_id: uuid.UUID


class EditEntry(Entry):
    version: int = Field(ge=1,strict=True)


class RemoveEntry(Strict):
    version: int = Field(ge=1,strict=True)
    reason: str = Field(min_length=1,max_length=500)


class NewCategory(Strict):
    zh: str = Field(min_length=1,max_length=40)
    en: str = Field(min_length=1,max_length=60)


def category_for(db,payload):
    if payload.kind=='expense':return 'expense'
    if not db.execute('SELECT 1 FROM studio_finance_categories WHERE id=?',(payload.category,)).fetchone():
        raise HTTPException(422,'finance_category_invalid')
    return payload.category


def payment_method(value):
    for key in ('cash','transfer','wechat_alipay','stored'):
        if value.casefold() in [key,*[s.casefold() for s in words(key)]]:
            return key
    if value.casefold() in [s.casefold() for s in words('transfer_legacy')]+['e-transfer']:
        return 'transfer'
    return value


def entry_money(database,payload,old=None):
    if old and old['currency']=='CNY' and payload.currency is None:
        raise HTTPException(409,'finance_client_update_required')
    method=payment_method(payload.payment_method)
    currency=('CNY' if method=='wechat_alipay' else 'CAD') if payload.kind=='income' else (payload.currency or 'CAD')
    if payload.kind=='income' and payload.currency is not None and payload.currency!=currency:
        raise HTTPException(422,'finance_currency_mismatch')
    if currency=='CAD':
        return (currency,'1',None,'identity',payload.amount_cents,method)
    if payload.amount_cents is None:
        return (currency,None,None,'',None,method)
    if old and old['currency']=='CNY' and old['occurred_on']==payload.occurred_on.isoformat() and old['fx_rate']:
        rate={'rate':old['fx_rate'],'rate_date':old['fx_date'],'source':old['fx_source']}
    else:
        rate=finance_fx.quote(database,payload.occurred_on)
    return (currency,rate['rate'],rate['rate_date'],rate['source'],finance_fx.cad_cents(payload.amount_cents,rate['rate']),method)


def register(app,database,admin_actor):
    prefix='/studio-api/manage/finance'

    @app.get(prefix+'/exchange-rate')
    def exchange_rate(on:date,_actor=Depends(admin_actor)):
        return {'currency':'CNY',**finance_fx.quote(database,on)}

    @app.get(prefix)
    def entries(start:date|None=None,end:date|None=None,kind:Literal['all','income','expense']='all',category:str='',
                search:str='',page:int=1,needs_amount:bool=False,_actor=Depends(admin_actor)):
        today=datetime.now(ZoneInfo('America/Toronto')).date();start=start or today.replace(day=1);end=end or today
        if start>end or (end-start).days>3660 or len(search)>120 or len(category)>64 or not 1<=page<=100000:
            raise HTTPException(422,'finance_invalid_filter')
        clauses=['deleted_at IS NULL','occurred_on>=?','occurred_on<=?'];args=[start.isoformat(),end.isoformat()]
        if kind!='all':clauses.append('kind=?');args.append(kind)
        if category:clauses.append('category=?');args.append(category)
        if search:clauses.append('(instr(lower(customer_name),lower(?))>0 OR instr(lower(items),lower(?))>0)');args.extend([search,search])
        if needs_amount:clauses.append('amount_cents IS NULL')
        where=' WHERE '+' AND '.join(clauses)
        with database() as db:
            db.execute('BEGIN')
            total=db.execute('SELECT count(*) FROM studio_finance_entries'+where,args).fetchone()[0]
            rows=db.execute('SELECT * FROM studio_finance_entries'+where+' ORDER BY occurred_on DESC,created_at DESC,id LIMIT 40 OFFSET ?',(*args,(page-1)*40)).fetchall()
            return {'items':[public(r) for r in rows],'page':page,'total':total,'start':start.isoformat(),'end':end.isoformat(),
              'summary':summary(db,start.isoformat(),end.isoformat()),'categories':[dict(r) for r in db.execute('SELECT id,zh,en FROM studio_finance_categories ORDER BY created_at,id')]}

    @app.get(prefix+'/{ident}')
    def detail(ident:str,_actor=Depends(admin_actor)):
        with database() as db:
            row=db.execute('SELECT * FROM studio_finance_entries WHERE id=? AND deleted_at IS NULL',(ident,)).fetchone()
            if not row:raise HTTPException(404,'finance_entry_missing')
            history=[{'id':r['id'],'action':r['action'],'created_at':r['created_at'],'snapshot':json.loads(r['snapshot'])}
                     for r in db.execute('SELECT * FROM studio_finance_events WHERE entry_id=? ORDER BY id DESC LIMIT 30',(ident,))]
            return {'entry':public(row),'history':history}

    @app.post(prefix,status_code=201)
    def create(payload:NewEntry,actor=Depends(admin_actor)):
        digest=hashlib.sha256(payload.model_dump_json(exclude={'currency'} if payload.currency is None else set()).encode()).hexdigest();key=str(payload.request_id)
        with database() as db:
            old=db.execute('SELECT * FROM studio_finance_entries WHERE request_id=?',(key,)).fetchone()
            if old:
                if old['request_hash']!=digest:raise HTTPException(409,'finance_request_changed')
                return public(old)
        if payload.amount_cents is None:raise HTTPException(422,'finance_amount_required')
        currency,rate,rate_date,rate_source,cad_amount,method=entry_money(database,payload)
        with database() as db:
            db.execute('BEGIN IMMEDIATE')
            old=db.execute('SELECT * FROM studio_finance_entries WHERE request_id=?',(key,)).fetchone()
            if old:
                if old['request_hash']!=digest:raise HTTPException(409,'finance_request_changed')
                return public(old)
            if payload.amount_cents is None:raise HTTPException(422,'finance_amount_required')
            category=category_for(db,payload);ident='FIN-'+uuid.uuid4().hex;stamp=time.time()
            db.execute("""INSERT INTO studio_finance_entries(id,kind,category,occurred_on,customer_name,items,amount_cents,
              payment_method,note,source,request_id,request_hash,created_at,updated_at,actor,currency,fx_rate,fx_date,fx_source,cad_amount_cents)
              VALUES(?,?,?,?,?,?,?,?,?,'manual',?,?,?,?,?,?,?,?,?,?)""",(ident,payload.kind,category,payload.occurred_on.isoformat(),payload.customer_name,
              json.dumps(payload.items,ensure_ascii=False),payload.amount_cents,method,payload.note,key,digest,stamp,stamp,actor,currency,rate,rate_date,rate_source,cad_amount))
            audit(db,ident,actor,'create')
            return public(db.execute('SELECT * FROM studio_finance_entries WHERE id=?',(ident,)).fetchone())

    @app.put(prefix+'/{ident}')
    def edit(ident:str,payload:EditEntry,actor=Depends(admin_actor)):
        with database() as db:
            old=db.execute('SELECT * FROM studio_finance_entries WHERE id=? AND deleted_at IS NULL',(ident,)).fetchone()
            if not old:raise HTTPException(404,'finance_entry_missing')
            if old['version']!=payload.version:raise HTTPException(409,'version_conflict')
        currency,rate,rate_date,rate_source,cad_amount,method=entry_money(database,payload,old)
        with database() as db:
            db.execute('BEGIN IMMEDIATE')
            old=db.execute('SELECT * FROM studio_finance_entries WHERE id=? AND deleted_at IS NULL',(ident,)).fetchone()
            if not old:raise HTTPException(404,'finance_entry_missing')
            if old['version']!=payload.version:raise HTTPException(409,'version_conflict')
            if payload.amount_cents is None and (payload.kind=='expense' or old['source']!='reservation'):
                raise HTTPException(422,'finance_amount_required')
            category=category_for(db,payload)
            db.execute("""UPDATE studio_finance_entries SET kind=?,category=?,occurred_on=?,customer_name=?,items=?,amount_cents=?,
              payment_method=?,note=?,currency=?,fx_rate=?,fx_date=?,fx_source=?,cad_amount_cents=?,version=version+1,updated_at=?,actor=? WHERE id=?""",(payload.kind,category,payload.occurred_on.isoformat(),
              payload.customer_name,json.dumps(payload.items,ensure_ascii=False),payload.amount_cents,method,payload.note,currency,rate,rate_date,rate_source,cad_amount,time.time(),actor,ident))
            audit(db,ident,actor,'edit')
            return public(db.execute('SELECT * FROM studio_finance_entries WHERE id=?',(ident,)).fetchone())

    @app.delete(prefix+'/{ident}')
    def remove(ident:str,payload:RemoveEntry,actor=Depends(admin_actor)):
        with database() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT * FROM studio_finance_entries WHERE id=?',(ident,)).fetchone()
            if not row:raise HTTPException(404,'finance_entry_missing')
            if row['deleted_at']:return {'removed':True}
            if row['version']!=payload.version:raise HTTPException(409,'version_conflict')
            db.execute('UPDATE studio_finance_entries SET deleted_at=?,version=version+1,actor=? WHERE id=?',(time.time(),actor,ident))
            audit(db,ident,actor,'void:'+payload.reason)
        return {'removed':True}

    @app.post(prefix+'/categories',status_code=201)
    def new_category(payload:NewCategory,actor=Depends(admin_actor)):
        with database() as db:
            db.execute('BEGIN IMMEDIATE')
            existing=db.execute('SELECT id,zh,en FROM studio_finance_categories WHERE zh=? AND en=?',(payload.zh,payload.en)).fetchone()
            if existing:return dict(existing)
            if db.execute('SELECT count(*) FROM studio_finance_categories').fetchone()[0]>=40:raise HTTPException(422,'finance_category_limit')
            ident='category-'+uuid.uuid4().hex
            db.execute('INSERT INTO studio_finance_categories VALUES(?,?,?,?,?)',(ident,payload.zh,payload.en,time.time(),actor))
        return {'id':ident,**payload.model_dump()}
