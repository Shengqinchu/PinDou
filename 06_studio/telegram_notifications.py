"""Telegram owner alerts and short-lived, admin-initiated recipient pairing."""
from __future__ import annotations

import hashlib
import html
import json
import os
import re
import secrets
import tempfile
import time
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener

from fastapi import Depends, HTTPException
from pydantic import BaseModel, ConfigDict, SecretStr

import owner_notifications as outbox

TOKEN_PATTERN = re.compile(r'[0-9]{5,20}:[A-Za-z0-9_-]{30,100}\Z')
BOT_USERNAME = re.compile(r'[A-Za-z0-9_]{5,64}\Z')
COPY_PATH = Path(__file__).with_name('telegram-notification-copy.json')
if not COPY_PATH.exists():
    COPY_PATH = Path(__file__).resolve().parents[1]/'05_studio/src/content/telegram-notifications.json'


def initialize(database):
    with database() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS studio_telegram_settings (
          id INTEGER PRIMARY KEY CHECK(id=1), enabled INTEGER NOT NULL DEFAULT 0,
          bot_id INTEGER NOT NULL DEFAULT 0, bot_username TEXT NOT NULL DEFAULT '',
          chat_id TEXT NOT NULL DEFAULT '', chat_label TEXT NOT NULL DEFAULT '',
          language TEXT NOT NULL DEFAULT 'zh', version INTEGER NOT NULL DEFAULT 1,
          blocked_until REAL NOT NULL DEFAULT 0, update_offset INTEGER NOT NULL DEFAULT 0
        );
        INSERT OR IGNORE INTO studio_telegram_settings(id) VALUES(1);
        CREATE TABLE IF NOT EXISTS studio_telegram_bindings (
          id TEXT PRIMARY KEY, token_hash TEXT NOT NULL, bot_id INTEGER NOT NULL,
          settings_version INTEGER NOT NULL, created_at REAL NOT NULL, expires_at REAL NOT NULL,
          last_check REAL NOT NULL DEFAULT 0, consumed INTEGER NOT NULL DEFAULT 0
        );
        """)


def settings_for(db):
    return dict(db.execute('SELECT * FROM studio_telegram_settings WHERE id=1').fetchone())


def secret_path(db):
    return outbox.secret_path(db).with_name('telegram-secret.json')


def read_token(db):
    try:
        token = json.loads(secret_path(db).read_text(encoding='utf-8')).get('token','')
    except (OSError, ValueError, AttributeError):
        return ''
    return token if isinstance(token,str) and TOKEN_PATTERN.fullmatch(token) else ''


def write_token(db, token):
    path = secret_path(db)
    descriptor, temporary = tempfile.mkstemp(prefix='.telegram-', dir=path.parent)
    try:
        with os.fdopen(descriptor,'w',encoding='utf-8') as stream:
            os.chmod(temporary,0o600)
            json.dump({'token':token},stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary,path)
    finally:
        if os.path.exists(temporary):os.unlink(temporary)


def api(token, method, payload=None):
    if not TOKEN_PATTERN.fullmatch(token):
        return {'ok':False,'error':'telegram_token_invalid','retry':False}
    if method not in {'getMe','getWebhookInfo','getUpdates','sendMessage'}:
        raise ValueError('Unsupported Telegram method')
    request = Request('https://api.telegram.org/bot'+token+'/'+method,
        data=json.dumps(payload or {},ensure_ascii=False).encode(),method='POST',
        headers={'Content-Type':'application/json','User-Agent':'PinDouStudio/1.0'})
    status = 200
    try:
        try:
            with build_opener(outbox.NoRedirect()).open(request,timeout=12) as response:
                data=json.loads(response.read(1024*1024))
        except HTTPError as exc:
            status=exc.code
            try:data=json.loads(exc.read(65536))
            except (ValueError,OSError):data={}
        if not isinstance(data,dict):raise ValueError('Invalid Telegram response')
        if status==200 and data.get('ok') is True:
            return {'ok':True,'result':data.get('result')}
        code=data.get('error_code',status)
        if code==429:
            parameters=data.get('parameters') or {}
            delay=parameters.get('retry_after',60) if isinstance(parameters,dict) else 60
            delay=max(1,min(86400,delay)) if isinstance(delay,int) else 60
            return {'ok':False,'error':'telegram_rate_limit','retry':True,'delay':delay}
        error={401:'telegram_token_invalid',404:'telegram_token_invalid',403:'telegram_blocked',409:'telegram_in_use'}.get(code,'telegram_rejected')
        return {'ok':False,'error':error,'retry':isinstance(code,int) and code>=500}
    except (URLError,TimeoutError,OSError,ValueError):
        return {'ok':False,'error':'telegram_network_error','retry':True}


def result_or_error(response):
    if not response['ok']:
        raise HTTPException(502,response['error'])
    return response['result']


def clean(value):
    return re.sub(r'[\x00-\x1f\x7f]',' ',str(value))[:100]


def deliver(token, chat_id, job, language):
    lang=1 if language=='en' else 0
    copy=json.loads(COPY_PATH.read_text(encoding='utf-8'))
    common=json.loads(outbox.COPY_PATH.read_text(encoding='utf-8'))
    title=copy['message_test'][lang] if job['kind']=='test' else common['message_'+job['kind']][lang]
    lines=['<b>'+html.escape(title)+'</b>']
    if job['reservation_id']:
        data=json.loads(job['payload']);booking=data['booking']
        if booking.get('plan') == 'patch':
            lines.append(html.escape(common['message_patch'][lang]))
        for key,value in (
            ('message_time',f"{booking['date']} {booking['start']}–{booking['end']}"),
            ('message_guests',booking['guests']),('message_name',data['name']),
            ('message_reference',job['reservation_id']),
        ):
            lines.append('<b>'+html.escape(common[key][lang])+':</b> '+html.escape(clean(value)))
        lines.append(common['message_timezone'][lang])
    else:
        lines.append(html.escape(copy['message_test_body'][lang]))
    response=api(token,'sendMessage',{
        'chat_id':chat_id,'text':'\n\n'.join(lines),'parse_mode':'HTML',
        'disable_notification':False,'link_preview_options':{'is_disabled':True},
        'reply_markup':{'inline_keyboard':[[{'text':common['message_open'][lang],
            'url':'https://pindoupuppy.com/manage?view=reservations'}]]},
    })
    if not response['ok']:return response
    message=response.get('result')
    if not isinstance(message,dict) or not isinstance(message.get('message_id'),int):
        return {'ok':False,'error':'telegram_rejected','retry':False}
    return {'ok':True,'provider_id':str(message['message_id'])}


class Settings(BaseModel):
    model_config=ConfigDict(extra='forbid')
    version:int
    enabled:bool=False
    language:str='zh'
    token:SecretStr|None=None


class PairRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    id:uuid.UUID


def register(app,database,admin_actor):
    @app.get('/studio-api/manage/telegram-notifications')
    def status(_actor=Depends(admin_actor)):
        with database() as db:
            current=settings_for(db)
            rows=db.execute("SELECT * FROM studio_owner_notifications WHERE channel='telegram' ORDER BY created_at DESC,id DESC LIMIT 30").fetchall()
            configured=bool(read_token(db))
        return {k:current[k] for k in ('enabled','language','version','bot_username','chat_label')} | {
            'configured':configured,'connected':bool(current['chat_id']), 'items':[outbox.public_job(row) for row in rows]}

    @app.put('/studio-api/manage/telegram-notifications')
    def configure(payload:Settings,_actor=Depends(admin_actor)):
        if payload.language not in ('zh','en'):raise HTTPException(422,'notification_settings_invalid')
        token=payload.token.get_secret_value().strip() if payload.token else ''
        if token and not TOKEN_PATTERN.fullmatch(token):raise HTTPException(422,'telegram_token_invalid')
        with database() as db:
            if settings_for(db)['version']!=payload.version:raise HTTPException(409,'version_conflict')
        identity=None
        if token:
            identity=result_or_error(api(token,'getMe'))
            if not isinstance(identity,dict) or identity.get('is_bot') is not True or not isinstance(identity.get('id'),int) or not BOT_USERNAME.fullmatch(identity.get('username','')):
                raise HTTPException(422,'telegram_token_invalid')
            webhook=result_or_error(api(token,'getWebhookInfo'))
            if not isinstance(webhook,dict) or webhook.get('url'):
                raise HTTPException(409,'telegram_in_use')
        with database() as db:
            db.execute('BEGIN IMMEDIATE')
            current=settings_for(db)
            if current['version']!=payload.version:raise HTTPException(409,'version_conflict')
            changed=identity is not None and identity['id']!=current['bot_id']
            if payload.enabled and not changed and not ((token or read_token(db)) and current['chat_id']):
                raise HTTPException(409,'telegram_not_bound')
            if token:write_token(db,token)
            if changed:
                db.execute("UPDATE studio_telegram_settings SET bot_id=?,bot_username=?,chat_id='',chat_label='',update_offset=0,blocked_until=0 WHERE id=1",(identity['id'],identity['username']))
            db.execute('UPDATE studio_telegram_settings SET enabled=?,language=?,version=version+1,blocked_until=CASE WHEN ? THEN 0 ELSE blocked_until END WHERE id=1',
                       (False if changed else payload.enabled,payload.language,bool(token)))
            db.execute('DELETE FROM studio_telegram_bindings WHERE consumed=0')
        return status(_actor)

    @app.post('/studio-api/manage/telegram-notifications/bind')
    def start_binding(_actor=Depends(admin_actor)):
        with database() as db:
            db.execute('BEGIN IMMEDIATE')
            current=settings_for(db)
            if not read_token(db):raise HTTPException(409,'telegram_not_configured')
            token=secrets.token_urlsafe(24);ident=str(uuid.uuid4());stamp=time.time()
            db.execute('DELETE FROM studio_telegram_bindings WHERE consumed=0 OR expires_at<?',(stamp-86400,))
            db.execute('INSERT INTO studio_telegram_bindings(id,token_hash,bot_id,settings_version,created_at,expires_at) VALUES(?,?,?,?,?,?)',
                       (ident,hashlib.sha256(token.encode()).hexdigest(),current['bot_id'],current['version'],stamp,stamp+600))
        return {'id':ident,'url':'https://t.me/'+current['bot_username']+'?start='+token,'expires_at':stamp+600}

    @app.post('/studio-api/manage/telegram-notifications/bind/check')
    def check_binding(payload:PairRequest,_actor=Depends(admin_actor)):
        stamp=time.time()
        with database() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT * FROM studio_telegram_bindings WHERE id=?',(str(payload.id),)).fetchone()
            if not row:raise HTTPException(409,'telegram_binding_expired')
            current=settings_for(db)
            if row['consumed']:return {'connected':True,'settings':status(_actor)}
            if row['expires_at']<=stamp:raise HTTPException(409,'telegram_binding_expired')
            if row['settings_version']!=current['version'] or row['bot_id']!=current['bot_id']:raise HTTPException(409,'version_conflict')
            if row['last_check']>stamp-12:return {'connected':False}
            db.execute('UPDATE studio_telegram_bindings SET last_check=? WHERE id=?',(stamp,str(payload.id)))
            token=read_token(db);expected=dict(row)
        # Do not take over a pre-existing webhook or infer the owner from the first /start.
        updates=result_or_error(api(token,'getUpdates',{'offset':current['update_offset'],'timeout':5,'limit':100,'allowed_updates':['message']}))
        if not isinstance(updates,list):raise HTTPException(502,'telegram_rejected')
        match=None;offset=current['update_offset']
        for update in updates:
            if not isinstance(update,dict):continue
            if isinstance(update.get('update_id'),int):offset=max(offset,update['update_id']+1)
            message=update.get('message') or {}
            chat=message.get('chat') or {};sender=message.get('from') or {}
            text=message.get('text','')
            if not isinstance(text,str) or not text.startswith('/start '):continue
            challenge=text[7:].strip()
            if (chat.get('type')=='private' and isinstance(chat.get('id'),int) and chat['id']>0
                and chat['id']==sender.get('id') and not sender.get('is_bot')
                and isinstance(message.get('date'),int) and message['date']>=int(expected['created_at'])-2
                and secrets.compare_digest(hashlib.sha256(challenge.encode()).hexdigest(),expected['token_hash'])):
                match=(str(chat['id']),clean(' '.join(filter(None,[sender.get('first_name',''),sender.get('last_name','')]))))
                break
        with database() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT * FROM studio_telegram_bindings WHERE id=?',(str(payload.id),)).fetchone()
            latest=settings_for(db)
            if not row or row['expires_at']<=time.time():raise HTTPException(409,'telegram_binding_expired')
            if row['consumed']:return {'connected':True,'settings':status(_actor)}
            if latest['version']!=expected['settings_version']:raise HTTPException(409,'version_conflict')
            db.execute('UPDATE studio_telegram_settings SET update_offset=MAX(update_offset,?) WHERE id=1',(offset,))
            if match:
                db.execute('UPDATE studio_telegram_settings SET chat_id=?,chat_label=?,enabled=1,version=version+1 WHERE id=1',match)
                db.execute('UPDATE studio_telegram_bindings SET consumed=1 WHERE id=?',(str(payload.id),))
                outbox.enqueue(db,'test',event_key='bind:'+str(payload.id),channel='telegram')
        return {'connected':bool(match),'settings':status(_actor) if match else None}

    @app.post('/studio-api/manage/telegram-notifications/test',status_code=202)
    def test_message(payload:outbox.TestRequest,_actor=Depends(admin_actor)):
        with database() as db:
            db.execute('BEGIN IMMEDIATE')
            current=settings_for(db)
            if not current['enabled'] or not current['chat_id'] or not read_token(db):raise HTTPException(409,'telegram_not_bound')
            key='test:'+str(payload.request_id)
            replay=db.execute('SELECT * FROM studio_owner_notifications WHERE event_key=?',('telegram:'+key,)).fetchone()
            if replay:return outbox.public_job(replay)
            recent=db.execute("SELECT count(*) FROM studio_owner_notifications WHERE channel='telegram' AND kind='test' AND created_at>?",(time.time()-3600,)).fetchone()[0]
            if recent>=3:raise HTTPException(429,'notification_test_limit')
            return outbox.public_job(outbox.enqueue(db,'test',event_key=key,channel='telegram'))

    @app.post('/studio-api/manage/telegram-notifications/{ident}/retry')
    def retry_message(ident:str,_actor=Depends(admin_actor)):
        with database() as db:
            db.execute('BEGIN IMMEDIATE')
            current=settings_for(db)
            if not current['enabled'] or not current['chat_id'] or not read_token(db):raise HTTPException(409,'telegram_not_bound')
            row=db.execute("SELECT * FROM studio_owner_notifications WHERE id=? AND channel='telegram'",(ident,)).fetchone()
            if not row:raise HTTPException(404,'notification_not_found')
            if row['state'] in ('queued','retry','sending'):return outbox.public_job(row)
            if row['state']!='failed' or row['expires_at']<=time.time() or row['attempts']>=outbox.MAX_ATTEMPTS:raise HTTPException(409,'notification_not_retryable')
            db.execute("UPDATE studio_owner_notifications SET state='queued',next_attempt=?,updated_at=? WHERE id=?",(time.time(),time.time(),ident))
            return outbox.public_job(db.execute('SELECT * FROM studio_owner_notifications WHERE id=?',(ident,)).fetchone())
