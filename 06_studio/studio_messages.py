"""Account-owned customer conversations, independent of phone-number identity."""
import hashlib
import json
import time
import uuid
from fastapi import Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from customer_auth import require_customer


def initialize(database):
    with database() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS studio_conversations (
          id TEXT PRIMARY KEY, owner_id TEXT NOT NULL UNIQUE, name TEXT NOT NULL DEFAULT '',
          created_at REAL NOT NULL, updated_at REAL NOT NULL, customer_read INTEGER NOT NULL DEFAULT 0,
          staff_read INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT 'open');
        CREATE TABLE IF NOT EXISTS studio_conversation_messages (
          seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT NOT NULL UNIQUE, thread_id TEXT NOT NULL,
          sender_role TEXT NOT NULL, sender_id TEXT NOT NULL, body TEXT NOT NULL,
          reservation_id TEXT NOT NULL DEFAULT '', created_at REAL NOT NULL,
          request_key TEXT NOT NULL UNIQUE, request_hash TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS studio_conversation_sequence ON studio_conversation_messages(thread_id,seq);
        ''')


def ensure(db, owner, name=''):
    row=db.execute('SELECT * FROM studio_conversations WHERE owner_id=?',(owner,)).fetchone()
    if row:return row
    ident=uuid.uuid4().hex;now=time.time()
    db.execute('INSERT INTO studio_conversations(id,owner_id,name,created_at,updated_at) VALUES(?,?,?,?,?)',(ident,owner,name[:80],now,now))
    return db.execute('SELECT * FROM studio_conversations WHERE id=?',(ident,)).fetchone()


def append(db,thread,role,actor,body,key,reservation=''):
    digest=hashlib.sha256(json.dumps([thread['id'],role,body,reservation],ensure_ascii=False).encode()).hexdigest()
    old=db.execute('SELECT * FROM studio_conversation_messages WHERE request_key=?',(key,)).fetchone()
    if old:
        if old['request_hash']!=digest:raise HTTPException(409,'message_request_changed')
        return dict(old)
    if role!='system' and db.execute('SELECT count(*) FROM studio_conversation_messages WHERE sender_id=? AND created_at>?',(actor,time.time()-60)).fetchone()[0]>=15:
        raise HTTPException(429,'message_rate_limited')
    ident=uuid.uuid4().hex;stamp=time.time()
    db.execute('INSERT INTO studio_conversation_messages(id,thread_id,sender_role,sender_id,body,reservation_id,created_at,request_key,request_hash) VALUES(?,?,?,?,?,?,?,?,?)',
               (ident,thread['id'],role,actor,body,reservation,stamp,key,digest))
    db.execute("UPDATE studio_conversations SET updated_at=?,status=CASE WHEN ?='customer' THEN 'open' ELSE status END WHERE id=?",(stamp,role,thread['id']))
    result=dict(db.execute('SELECT * FROM studio_conversation_messages WHERE id=?',(ident,)).fetchone())
    if role in ('customer','staff'):
        import customer_notifications
        customer_notifications.on_message(db,thread,result)
    return result


def system_message(db,owner,name,body,key,reservation):
    return append(db,ensure(db,owner,name),'system','system',body,'event:'+key,reservation)


def message(row):
    return {k:row[k] for k in ('seq','id','sender_role','body','reservation_id','created_at')}


def view(db,thread,staff=False,after=0,before=0):
    if after<0 or before<0:raise HTTPException(422,'message_invalid_cursor')
    clause=' AND seq>?' if after else ' AND seq<?' if before else ''
    args=(thread['id'],after or before) if clause else (thread['id'],)
    rows=db.execute('SELECT * FROM studio_conversation_messages WHERE thread_id=?'+clause+' ORDER BY seq '+('ASC' if after else 'DESC')+' LIMIT 60',args).fetchall()
    if not after:rows=list(reversed(rows))
    last=db.execute('SELECT coalesce(max(seq),0) FROM studio_conversation_messages WHERE thread_id=?',(thread['id'],)).fetchone()[0]
    return {'thread':{'id':thread['id'],'name':thread['name'],'status':thread['status'],'last_seq':last},'items':[message(r) for r in rows],
            'has_older':bool(rows and db.execute('SELECT 1 FROM studio_conversation_messages WHERE thread_id=? AND seq<?',(thread['id'],rows[0]['seq'])).fetchone())}


class Send(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    content:str=Field(min_length=1,max_length=4000)
    request_id:uuid.UUID
    reservation_id:str=Field(default='',max_length=80)


class Read(BaseModel):
    seq:int=Field(ge=0,strict=True)


def check_reservation(db,owner,ident):
    if ident and not db.execute('SELECT 1 FROM studio_reservations WHERE id=? AND owner_id=? AND deleted_at IS NULL',(ident,owner)).fetchone():
        raise HTTPException(404,'reservation_not_found')


def unread_count(db):
    return db.execute("SELECT count(*) FROM studio_conversation_messages m JOIN studio_conversations t ON t.id=m.thread_id WHERE m.sender_role='customer' AND m.seq>t.staff_read").fetchone()[0]


def register(app,database,admin_actor):
    @app.get('/studio-api/auth/messages')
    def customer_messages(after:int=0,before:int=0,customer=Depends(require_customer)):
        with database() as db:
            thread=db.execute('SELECT * FROM studio_conversations WHERE owner_id=?',(customer['id'],)).fetchone()
            if not thread:return {'thread':None,'items':[],'has_older':False}
            return view(db,thread,after=after,before=before)

    @app.post('/studio-api/auth/messages',status_code=201)
    def customer_send(payload:Send,customer=Depends(require_customer)):
        with database() as db:
            db.execute('BEGIN IMMEDIATE');check_reservation(db,customer['id'],payload.reservation_id)
            thread=ensure(db,customer['id'],customer.get('nickname',''))
            value=append(db,thread,'customer',customer['id'],payload.content,'customer:'+customer['id']+':'+str(payload.request_id),payload.reservation_id)
            return message(value)

    @app.post('/studio-api/auth/messages/read')
    def customer_read(payload:Read,customer=Depends(require_customer)):
        with database() as db:
            row=db.execute('SELECT * FROM studio_conversations WHERE owner_id=?',(customer['id'],)).fetchone()
            if row:
                maximum=db.execute('SELECT coalesce(max(seq),0) FROM studio_conversation_messages WHERE thread_id=?',(row['id'],)).fetchone()[0]
                db.execute('UPDATE studio_conversations SET customer_read=max(customer_read,?) WHERE id=?',(min(payload.seq,maximum),row['id']))
        return {'ok':True}

    @app.get('/studio-api/manage/site-messages')
    def threads(query:str='',unread:bool=False,page:int=1,_actor=Depends(admin_actor)):
        if len(query)>120 or not 1<=page<=10000:raise HTTPException(422,'message_invalid_cursor')
        with database() as db:
            where=" WHERE (instr(lower(t.name),lower(?))>0 OR instr(lower(coalesce(m.name,'')),lower(?))>0)"
            if unread:where+=" AND EXISTS(SELECT 1 FROM studio_conversation_messages c WHERE c.thread_id=t.id AND c.sender_role='customer' AND c.seq>t.staff_read)"
            rows=db.execute("SELECT t.*,coalesce(m.name,t.name) AS customer_name FROM studio_conversations t LEFT JOIN studio_members m ON m.owner_id=t.owner_id"+where+' ORDER BY t.updated_at DESC LIMIT 40 OFFSET ?',(query,query,(page-1)*40)).fetchall()
            result=[]
            for row in rows:
                latest=db.execute('SELECT body,created_at FROM studio_conversation_messages WHERE thread_id=? ORDER BY seq DESC LIMIT 1',(row['id'],)).fetchone()
                count=db.execute("SELECT count(*) FROM studio_conversation_messages WHERE thread_id=? AND sender_role='customer' AND seq>?",(row['id'],row['staff_read'])).fetchone()[0]
                result.append({'id':row['id'],'name':row['customer_name'],'unread':count,'status':row['status'],'latest':dict(latest) if latest else None})
            return {'items':result,'page':page,'unread':unread_count(db)}

    def owned(db,ident):
        row=db.execute('SELECT * FROM studio_conversations WHERE id=?',(ident,)).fetchone()
        if not row:raise HTTPException(404,'message_thread_missing')
        return row

    @app.get('/studio-api/manage/site-messages/{ident}')
    def staff_messages(ident:str,after:int=0,before:int=0,_actor=Depends(admin_actor)):
        with database() as db:return view(db,owned(db,ident),True,after,before)

    @app.post('/studio-api/manage/site-messages/{ident}',status_code=201)
    def staff_send(ident:str,payload:Send,actor=Depends(admin_actor)):
        with database() as db:
            db.execute('BEGIN IMMEDIATE');thread=owned(db,ident);check_reservation(db,thread['owner_id'],payload.reservation_id)
            value=append(db,thread,'staff',actor,payload.content,'staff:'+actor+':'+str(payload.request_id),payload.reservation_id)
            return message(value)

    @app.post('/studio-api/manage/site-messages/{ident}/read')
    def staff_read(ident:str,payload:Read,_actor=Depends(admin_actor)):
        with database() as db:
            owned(db,ident);maximum=db.execute('SELECT coalesce(max(seq),0) FROM studio_conversation_messages WHERE thread_id=?',(ident,)).fetchone()[0]
            db.execute('UPDATE studio_conversations SET staff_read=max(staff_read,?) WHERE id=?',(min(payload.seq,maximum),ident))
        return {'ok':True}
