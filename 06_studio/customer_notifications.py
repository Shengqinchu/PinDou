"""Transactional booking notices with per-account choices and dated delivery jobs."""
from __future__ import annotations
import asyncio
import hashlib
import html
import json
import os
import re
import secrets
import time
import uuid
from datetime import datetime,timedelta
from pathlib import Path
from urllib.request import Request as URLRequest,urlopen
from urllib.error import HTTPError
from zoneinfo import ZoneInfo
from fastapi import Depends,HTTPException,Request
from pydantic import BaseModel,ConfigDict,Field
from customer_auth import require_customer
import miniapp_login as mini
import owner_wechat
import sms_inbox
import studio_messages

COPY=Path(__file__).with_name('customer-notification-copy.json')
if not COPY.exists():COPY=Path(__file__).resolve().parents[1]/'05_studio/src/content/customer-notifications.json'
PROFILE=Path(__file__).with_name('studio-profile.json')
if not PROFILE.exists():PROFILE=Path(__file__).resolve().parents[1]/'05_studio/src/content/studio-profile.json'
KINDS=('confirmed','cancelled','reminder')
BOOKING_KINDS=('pending',)+KINDS
ZONE=ZoneInfo('America/Toronto')
DELIVERY_LOCALE='en'


def english_display_name(value):
    """Keep an English notice English when a booking name uses another script."""
    name=' '.join(str(value or '').split())[:80]
    return name if name and name.isascii() and name.isprintable() else 'Hello'


def words(key,locale='zh'):
    return json.loads(COPY.read_text(encoding='utf-8'))[key][locale=='en']


def initialize(database):
    with database() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS studio_customer_notification_preferences (
          owner_id TEXT PRIMARY KEY, email TEXT NOT NULL DEFAULT '', phone TEXT NOT NULL DEFAULT '',
          email_enabled INTEGER NOT NULL DEFAULT 0, sms_enabled INTEGER NOT NULL DEFAULT 0,
          version INTEGER NOT NULL DEFAULT 1, updated_at REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS studio_booking_notification_choices (
          reservation_id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, email TEXT NOT NULL, phone TEXT NOT NULL,
          email_enabled INTEGER NOT NULL, sms_enabled INTEGER NOT NULL, locale TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS studio_customer_notification_templates (
          kind TEXT PRIMARY KEY, template_id TEXT NOT NULL, title TEXT NOT NULL, fields TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS studio_customer_wechat_grants (
          owner_id TEXT NOT NULL, app_id TEXT NOT NULL, openid TEXT NOT NULL, kind TEXT NOT NULL,
          template_id TEXT NOT NULL, grants INTEGER NOT NULL DEFAULT 0,
          PRIMARY KEY(owner_id,app_id,kind));
        CREATE TABLE IF NOT EXISTS studio_customer_wechat_nonces (
          hash TEXT PRIMARY KEY, owner_id TEXT NOT NULL, app_id TEXT NOT NULL, openid TEXT NOT NULL,
          templates TEXT NOT NULL, expires_at REAL NOT NULL, result TEXT NOT NULL DEFAULT '');
        CREATE TABLE IF NOT EXISTS studio_customer_notification_jobs (
          id TEXT PRIMARY KEY, event_key TEXT NOT NULL, reservation_id TEXT NOT NULL, owner_id TEXT NOT NULL,
          kind TEXT NOT NULL, channel TEXT NOT NULL, recipient TEXT NOT NULL, payload TEXT NOT NULL,
          state TEXT NOT NULL, due_at REAL NOT NULL, expires_at REAL NOT NULL, next_attempt REAL NOT NULL,
          attempts INTEGER NOT NULL DEFAULT 0, lease_until REAL NOT NULL DEFAULT 0,
          provider_id TEXT NOT NULL DEFAULT '', error TEXT NOT NULL DEFAULT '', created_at REAL NOT NULL,
          updated_at REAL NOT NULL, UNIQUE(event_key,channel));
        CREATE INDEX IF NOT EXISTS studio_customer_notification_due ON studio_customer_notification_jobs(state,next_attempt,due_at);
        ''')
        templates_path=Path(os.getenv('STUDIO_CUSTOMER_TEMPLATES_FILE','/opt/pindou/studio/shared/customer-notification-templates.json'))
        if templates_path.is_file():
            configured=json.loads(templates_path.read_text(encoding='utf-8'))
            if configured.get('app_id')!=mini.config().app_id:raise ValueError('Notification template app mismatch')
            for item in configured['templates']:
                if item['kind'] not in KINDS or not re.fullmatch(r'[A-Za-z0-9_-]{20,160}',item['template_id']):raise ValueError('Invalid notification template')
                db.execute('INSERT INTO studio_customer_notification_templates VALUES(?,?,?,?) ON CONFLICT(kind) DO UPDATE SET template_id=excluded.template_id,title=excluded.title,fields=excluded.fields',
                  (item['kind'],item['template_id'],item['title'],json.dumps(item['fields'])))


def preferences(db,owner,customer=None):
    profile=db.execute('SELECT contact_method,contact FROM studio_booking_profiles WHERE owner_id=?',(owner,)).fetchone()
    member=db.execute('SELECT email FROM studio_members WHERE owner_id=?',(owner,)).fetchone()
    email=(profile['contact'] if profile and profile['contact_method']=='email' else (customer or {}).get('email') or (member['email'] if member else '') or '')
    if not re.fullmatch(r'[^\s<>@]+@[^\s<>@]+\.[^\s<>@]+',email):email=''
    number=''
    if profile and profile['contact_method']=='phone':
        try:number=sms_inbox.phone(profile['contact'])
        except HTTPException:pass
    row=db.execute('SELECT * FROM studio_customer_notification_preferences WHERE owner_id=?',(owner,)).fetchone()
    if row:
        value=dict(row);value.pop('owner_id');value['email_enabled']=bool(value['email_enabled']);value['sms_enabled']=bool(value['sms_enabled'])
        if not value['email'] and email:value.update(email=email,email_enabled=True)
        if not value['phone'] and number:value.update(phone=number,sms_enabled=True)
        return value
    return {'email':email,'phone':number,'email_enabled':bool(email),'sms_enabled':bool(number),'version':0,'updated_at':0}


def start_time(booking):
    return datetime.fromisoformat(booking['date']+'T'+booking['start']).replace(tzinfo=ZONE).timestamp()


def delivery_payload(job,payload):
    """Render unsent notices from the current English copy, including legacy queued jobs."""
    if job.get('attempts',0)>0 and job.get('state') not in ('waiting_config','waiting_subscription'):
        return payload  # Preserve provider idempotency for deliveries that may have reached a provider.
    kind=job['kind'];url=payload['url']
    if kind in BOOKING_KINDS:
        booking=payload['booking'];url='https://pindoupuppy.com/reservation/'+job['reservation_id']
        channel=job['channel']
        contact_key={'sms':'contact_by_sms','email':'contact_by_email'}.get(channel,'contact_on_booking_page')
        fields={'name':payload.get('name',''),'display_name':english_display_name(payload.get('name')),
          'contact_instruction':words(contact_key,DELIVERY_LOCALE),
          'date':booking['date'],'start':booking['start'],'end':booking['end'],
          'guests':booking['guests'],'guest_label':'guest' if booking['guests']==1 else 'guests',
          'address':json.loads(PROFILE.read_text(encoding='utf-8'))['address'],'url':url}
        body_key=kind+'_'+job['channel']+'_body' if kind=='confirmed' and job['channel'] in ('sms','email') else kind+'_body'
    else:
        fields={'url':url};body_key=kind+'_body'
    return payload|{'title':words(kind+'_title',DELIVERY_LOCALE),
      'body':words(body_key,DELIVERY_LOCALE).format(**fields),'url':url,'locale':DELIVERY_LOCALE,'kind':kind}


def render(row,kind):
    value=json.loads(row['payload']);url='https://pindoupuppy.com/reservation/'+row['id']
    payload={'url':url,'booking':value['booking'],'name':value.get('name',''),'kind':kind}
    return delivery_payload({'kind':kind,'channel':'site','reservation_id':row['id']},payload)


def enqueue(db,row,kind,due=None):
    choices=db.execute('SELECT * FROM studio_booking_notification_choices WHERE reservation_id=?',(row['id'],)).fetchone()
    if not choices:return
    stamp=time.time();booking=json.loads(row['payload'])['booking'];begins=start_time(booking)
    expires=stamp+86400 if kind=='cancelled' else min(stamp+86400,begins)
    if kind=='reminder':expires=begins
    due=stamp if due is None else due
    if expires<=due:return
    event=kind+':'+row['id']+':'+str(row['version']);payload=render(row,kind)
    if kind!='reminder':studio_messages.system_message(db,row['owner_id'],payload['name'],payload['title']+'\n'+payload['body'],event,row['id'])
    destinations=[]
    if choices['email_enabled'] and choices['email']:destinations.append(('email',choices['email']))
    if choices['sms_enabled'] and choices['phone']:destinations.append(('sms',choices['phone']))
    if kind in KINDS:
        identity=db.execute('SELECT 1 FROM studio_miniapp_identities WHERE user_id=? AND app_id=?',(row['owner_id'],mini.config().app_id)).fetchone()
        if identity:destinations.append(('wechat',''))
    for channel,recipient in destinations:
        channel_payload=delivery_payload({'kind':kind,'channel':channel,'reservation_id':row['id']},payload)
        db.execute('''INSERT OR IGNORE INTO studio_customer_notification_jobs
          (id,event_key,reservation_id,owner_id,kind,channel,recipient,payload,state,due_at,expires_at,next_attempt,created_at,updated_at)
          VALUES(?,?,?,?,?,?,?,?,'queued',?,?,?,?,?)''',
          (uuid.uuid4().hex,event,row['id'],row['owner_id'],kind,channel,recipient,json.dumps(channel_payload,ensure_ascii=False),due,expires,due,stamp,stamp))


def on_reservation(db,kind,row):
    if not row['owner_id']:return
    if kind=='created':
        pref=preferences(db,row['owner_id']);locale=json.loads(row['payload']).get('locale','zh')
        db.execute('INSERT OR IGNORE INTO studio_booking_notification_choices VALUES(?,?,?,?,?,?,?)',
          (row['id'],row['owner_id'],pref['email'],pref['phone'],int(pref['email_enabled']),int(pref['sms_enabled']),locale))
        enqueue(db,row,'pending')
    elif kind in ('confirmed','cancelled'):
        db.execute("UPDATE studio_customer_notification_jobs SET state='skipped',error='superseded',updated_at=? WHERE reservation_id=? AND state IN ('queued','retry','waiting_subscription','waiting_config')",(time.time(),row['id']))
        enqueue(db,row,kind)
        if kind=='confirmed':
            due=start_time(json.loads(row['payload'])['booking'])-7200
            if due>time.time():enqueue(db,row,'reminder',due)


def valid_job(db,job):
    if job['kind'] in ('reply','customer_message'):
        payload=json.loads(job['payload'])
        thread=db.execute('SELECT * FROM studio_conversations WHERE id=?',(payload['thread_id'],)).fetchone()
        if not thread or job['expires_at']<=time.time():return False
        if job['kind']=='customer_message':
            settings=db.execute('SELECT * FROM studio_sms_settings WHERE id=1').fetchone()
            return bool(settings and settings['owner_enabled'] and settings['owner_phone']==job['recipient'] and thread['staff_read']<payload['seq'])
        if thread['owner_id']!=job['owner_id'] or thread['customer_read']>=payload['seq']:return False
        pref=preferences(db,job['owner_id']);field='email' if job['channel']=='email' else 'phone'
        return bool(pref[job['channel']+'_enabled'] and pref[field]==job['recipient'])
    row=db.execute('SELECT * FROM studio_reservations WHERE id=?',(job['reservation_id'],)).fetchone()
    if not row or row['owner_id']!=job['owner_id'] or job['expires_at']<=time.time():return False
    wanted={'pending':'pending','confirmed':'confirmed','reminder':'confirmed','cancelled':'cancelled'}[job['kind']]
    if row['status']!=wanted or (row['deleted_at'] and wanted!='cancelled'):return False
    payload=json.loads(job['payload']);current=json.loads(row['payload'])
    if current['booking']!=payload['booking']:return False
    if job['channel'] in ('email','sms'):
        pref=preferences(db,job['owner_id']);field='email' if job['channel']=='email' else 'phone'
        if not pref[job['channel']+'_enabled'] or pref[field]!=job['recipient']:return False
    return True


def valid_sms(db,job):
    if not job['request_key'].startswith('customer-notice:'):return True
    row=db.execute('SELECT * FROM studio_customer_notification_jobs WHERE id=?',(job['request_key'].split(':',1)[1],)).fetchone()
    return bool(row and valid_job(db,row))


def on_message(db,thread,message):
    """Notify only if a new reply remains unread after a short grace period."""
    stamp=time.time();role=message['sender_role'];owner=thread['owner_id']
    if role not in ('staff','customer'):return
    kind='reply' if role=='staff' else 'customer_message'
    url='https://pindoupuppy.com/messages' if role=='staff' else 'https://pindoupuppy.com/manage?view=messages'
    payload=delivery_payload({'kind':kind,'channel':'sms','reservation_id':''},
      {'url':url,'thread_id':thread['id'],'seq':message['seq'],'name':thread['name']})
    destinations=[]
    if role=='staff':
        pref=preferences(db,owner)
        if pref['email_enabled'] and pref['email']:destinations.append(('email',pref['email']))
        if pref['sms_enabled'] and pref['phone']:destinations.append(('sms',pref['phone']))
    else:
        settings=db.execute('SELECT * FROM studio_sms_settings WHERE id=1').fetchone()
        if settings and settings['owner_enabled'] and settings['owner_phone']:destinations.append(('owner_sms',settings['owner_phone']))
    # Newer replies replace waiting alerts for the same conversation/channel.
    for channel,recipient in destinations:
        db.execute("UPDATE studio_customer_notification_jobs SET state='skipped',error='superseded',updated_at=? WHERE owner_id=? AND kind=? AND channel=? AND state IN ('queued','retry','waiting_config')",(stamp,owner,kind,channel))
        db.execute('''INSERT OR IGNORE INTO studio_customer_notification_jobs
          (id,event_key,reservation_id,owner_id,kind,channel,recipient,payload,state,due_at,expires_at,next_attempt,created_at,updated_at)
          VALUES(?,?,?,?,?,?,?,?,'queued',?,?,?,?,?)''',
          (uuid.uuid4().hex,'message:'+message['id'],'',owner,kind,channel,recipient,json.dumps(payload,ensure_ascii=False),stamp+60,stamp+3600,stamp+60,stamp,stamp))


def email_credentials():
    return os.getenv('STUDIO_EMAIL_API_KEY',''),os.getenv('STUDIO_EMAIL_FROM','')


def send_email(job,payload):
    key,sender=email_credentials()
    if not key or not sender:return ('waiting_config','email_unconfigured','')
    title=html.escape(payload['title'])
    parts=re.split(r'(https://pindoupuppy\.com/[A-Za-z0-9/_?&=%#.\-]+)',payload['body'])
    body=''.join('<a href="'+html.escape(part,quote=True)+'">'+html.escape(part)+'</a>'
      if part.startswith('https://pindoupuppy.com/') else html.escape(part) for part in parts).replace('\n','<br>')
    markup=f'<div style="max-width:560px;margin:auto;padding:24px;font:16px/1.7 Arial,sans-serif;color:#26343d"><h2>{title}</h2><p>{body}</p></div>'
    data={'from':sender,'to':[job['recipient']],'subject':words('place',DELIVERY_LOCALE)+' · '+payload['title'],
      'text':payload['title']+'\n'+payload['body'],'html':markup}
    request=URLRequest('https://api.resend.com/emails',data=json.dumps(data).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json','User-Agent':'PinDouStudio/1.0','Idempotency-Key':'booking-'+job['id']})
    try:
        with urlopen(request,timeout=12) as response:result=json.loads(response.read(64000))
        return ('accepted','',str(result.get('id',''))[:160])
    except HTTPError as error:
        return ('retry' if error.code==429 or error.code>=500 else 'failed','email_provider_'+str(error.code),'')
    except Exception:return ('retry','email_network_error','')


def wechat_message(job,payload,template,grant):
    fields=json.loads(template['fields']);booking=payload['booking'];locale=DELIVERY_LOCALE
    text=lambda value:re.sub(r'[\x00-\x1f\x7f]',' ',str(value))[:20]
    values={'place':text(words('place',locale)),'start':booking['date']+' '+booking['start'],
      'end':booking['date']+' '+booking['end'],'service':text(words('day' if booking['plan']=='day' else 'hourly',locale)),
      'note':text(words('card_'+job['kind'],locale).format(
        guests=booking['guests'],guest_label='guest' if booking['guests']==1 else 'guests'))}
    return {'touser':grant['openid'],'template_id':template['template_id'],
      'page':'pages/studio/reservation?id='+job['reservation_id'],'miniprogram_state':{'release':'formal','trial':'trial','develop':'developer'}[mini.config().environment],
      'lang':'en_US','data':{key:{'value':values[value]} for key,value in fields.items()}}


def process_one(database):
    now=time.time()
    with database() as db:
        db.execute('BEGIN IMMEDIATE')
        db.execute("UPDATE studio_customer_notification_jobs SET state=CASE WHEN channel='email' THEN 'retry' ELSE 'unknown' END,error='interrupted',next_attempt=?,updated_at=? WHERE state='sending' AND lease_until<?",(now,now,now))
        # Reflect the transport's observed state without initiating another send.
        db.execute("UPDATE studio_customer_notification_jobs SET state=coalesce((SELECT CASE WHEN s.state IN ('delivered','sent','failed','unknown','skipped') THEN s.state ELSE 'handed_off' END FROM studio_sms_jobs s WHERE s.id=provider_id),'handed_off') WHERE channel IN ('sms','owner_sms') AND state='handed_off'")
        row=db.execute("SELECT * FROM studio_customer_notification_jobs WHERE state IN ('queued','retry','waiting_config','waiting_subscription') AND due_at<=? AND next_attempt<=? ORDER BY due_at,created_at LIMIT 1",(now,now)).fetchone()
        if not row:return False
        job=dict(row)
        if not valid_job(db,job):
            db.execute("UPDATE studio_customer_notification_jobs SET state='skipped',error='superseded',updated_at=? WHERE id=?",(now,job['id']));return True
        payload=json.loads(job['payload'])
        current=delivery_payload(job,payload)
        if current!=payload:
            payload=current
            db.execute('UPDATE studio_customer_notification_jobs SET payload=?,updated_at=? WHERE id=?',
              (json.dumps(payload,ensure_ascii=False),now,job['id']))
        if job['channel'] in ('sms','owner_sms'):
            bridge=db.execute("SELECT * FROM studio_sms_bridges WHERE role=? AND enabled=1 AND send_enabled=1",('owner_alert' if job['channel']=='owner_sms' else 'customer',)).fetchone()
            if not bridge:
                db.execute("UPDATE studio_customer_notification_jobs SET state='waiting_config',error='sms_unavailable',next_attempt=? WHERE id=?",(now+60,job['id']));return True
            ident=''
            if job['channel']=='sms':
                thread=sms_inbox.ensure_thread(db,job['recipient'],payload['name'],reservation_id=job['reservation_id'])
                ident=uuid.uuid4().hex
                cur=db.execute("INSERT INTO studio_sms_messages(id,thread_id,bridge_id,direction,source,channel,content,created_at,state) VALUES(?,?,?,'outbound','notification','SMS',?,?,'queued')",(ident,thread['id'],bridge['id'],payload['title']+'\n'+payload['body'],now))
                db.execute('UPDATE studio_sms_threads SET last_seq=?,updated_at=? WHERE id=?',(cur.lastrowid,now,thread['id']))
            smsjob=sms_inbox.queue_job(db,bridge['id'],job['recipient'],payload['title']+'\n'+payload['body'],request_key='customer-notice:'+job['id'],message_id=ident,reservation_id=job['reservation_id'])
            db.execute('UPDATE studio_sms_jobs SET expires_at=min(expires_at,?) WHERE id=?',(job['expires_at'],smsjob['id']))
            db.execute("UPDATE studio_customer_notification_jobs SET state='handed_off',provider_id=?,updated_at=? WHERE id=?",(smsjob['id'],now,job['id']));return True
        template=grant=None
        if job['channel']=='wechat':
            template=db.execute('SELECT * FROM studio_customer_notification_templates WHERE kind=?',(job['kind'],)).fetchone()
            if template:grant=db.execute('SELECT * FROM studio_customer_wechat_grants WHERE owner_id=? AND app_id=? AND kind=? AND template_id=? AND grants>0',(job['owner_id'],mini.config().app_id,job['kind'],template['template_id'])).fetchone()
            if not template or not grant:
                db.execute("UPDATE studio_customer_notification_jobs SET state='waiting_subscription',error='wechat_subscription_required',next_attempt=? WHERE id=?",(now+60,job['id']));return True
            template,grant=dict(template),dict(grant)
            db.execute('UPDATE studio_customer_wechat_grants SET grants=grants-1 WHERE owner_id=? AND app_id=? AND kind=?',(job['owner_id'],grant['app_id'],job['kind']))
        db.execute("UPDATE studio_customer_notification_jobs SET state='sending',attempts=attempts+1,lease_until=?,updated_at=? WHERE id=?",(now+90,now,job['id']))
    if job['channel']=='email':state,error,ident=send_email(job,payload)
    else:
        state,error,ident='unknown','wechat_network_error',''
        try:
            result=owner_wechat.provider('cgi-bin/message/subscribe/send',wechat_message(job,payload,template,grant))
            if type(result.get('errcode')) is int:
                state='accepted' if result['errcode']==0 else 'failed';error='' if state=='accepted' else 'wechat_'+str(result['errcode']);ident=str(result.get('msgid',''))[:160]
        except Exception:pass
    with database() as db:
        if error=='wechat_43101':db.execute('UPDATE studio_customer_wechat_grants SET grants=0 WHERE owner_id=? AND app_id=? AND kind=?',(job['owner_id'],grant['app_id'],job['kind']))
        if state=='retry' and job['attempts']>=5:state='failed'
        db.execute("UPDATE studio_customer_notification_jobs SET state=?,error=?,provider_id=?,next_attempt=?,lease_until=0,updated_at=? WHERE id=? AND state='sending'",(state,error,ident,time.time()+min(3600,30*2**min(job['attempts'],6)),time.time(),job['id']))
    return True


async def worker(database):
    while True:
        try:worked=await asyncio.to_thread(process_one,database)
        except Exception:worked=False
        await asyncio.sleep(0.25 if worked else 3)


class PreferenceUpdate(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    email:str=Field(default='',max_length=180)
    phone:str=Field(default='',max_length=40)
    email_enabled:bool=False
    sms_enabled:bool=False
    version:int=Field(ge=0,strict=True)


class Subscription(BaseModel):
    nonce:str=Field(pattern=r'^[A-Za-z0-9_-]{43}$')
    results:dict[str,str]


def register(app,database,admin_actor):
    @app.get('/studio-api/auth/notifications')
    def get_preferences(customer=Depends(require_customer)):
        with database() as db:return preferences(db,customer['id'],customer)

    @app.put('/studio-api/auth/notifications')
    def put_preferences(payload:PreferenceUpdate,customer=Depends(require_customer)):
        email=payload.email if re.fullmatch(r'[^\s<>@]+@[^\s<>@]+\.[^\s<>@]+',payload.email) else ''
        number=''
        if payload.phone:
            try:number=sms_inbox.phone(payload.phone)
            except HTTPException:pass
        if payload.email_enabled and not email or payload.sms_enabled and not number:raise HTTPException(422,'notification_contact_invalid')
        with database() as db:
            db.execute('BEGIN IMMEDIATE');current=preferences(db,customer['id'])
            if current['version']!=payload.version:raise HTTPException(409,'notification_preferences_changed')
            db.execute('''INSERT INTO studio_customer_notification_preferences VALUES(?,?,?,?,?,1,?)
              ON CONFLICT(owner_id) DO UPDATE SET email=excluded.email,phone=excluded.phone,email_enabled=excluded.email_enabled,
              sms_enabled=excluded.sms_enabled,version=studio_customer_notification_preferences.version+1,updated_at=excluded.updated_at''',
              (customer['id'],email,number,int(payload.email_enabled),int(payload.sms_enabled),time.time()))
            db.execute('UPDATE studio_booking_notification_choices SET email=?,phone=?,email_enabled=?,sms_enabled=? WHERE owner_id=?',
              (email,number,int(payload.email_enabled),int(payload.sms_enabled),customer['id']))
            for channel,address,enabled in [('email',email,payload.email_enabled),('sms',number,payload.sms_enabled)]:
                db.execute("UPDATE studio_customer_notification_jobs SET recipient=?,state=?,updated_at=? WHERE owner_id=? AND kind='reminder' AND channel=? AND due_at>? AND attempts=0 AND state IN ('queued','waiting_config')",
                  (address,'queued' if enabled else 'skipped',time.time(),customer['id'],channel,time.time()))
            return preferences(db,customer['id'])

    @app.post('/studio-api/auth/notifications/wechat/session')
    def wechat_session(request:Request,customer=Depends(require_customer)):
        with database() as db:
            ticket=mini.ticket_for(db,request)
            identity=db.execute('SELECT user_id FROM studio_miniapp_identities WHERE app_id=? AND openid=?',(ticket['app_id'],ticket['openid'])).fetchone()
            if not identity or identity['user_id']!=customer['id']:raise HTTPException(403,'notification_wechat_unavailable')
            templates=[dict(r) for r in db.execute('SELECT kind,template_id,title FROM studio_customer_notification_templates WHERE kind IN (\'confirmed\',\'cancelled\',\'reminder\') ORDER BY kind')]
            nonce=secrets.token_urlsafe(32);stamp=time.time()
            db.execute('DELETE FROM studio_customer_wechat_nonces WHERE expires_at<?',(stamp-86400,))
            if db.execute('SELECT count(*) FROM studio_customer_wechat_nonces WHERE owner_id=? AND expires_at>?',(customer['id'],stamp)).fetchone()[0]>=30:raise HTTPException(429,'notification_wechat_unavailable')
            db.execute('INSERT INTO studio_customer_wechat_nonces(hash,owner_id,app_id,openid,templates,expires_at) VALUES(?,?,?,?,?,?)',
              (hashlib.sha256(nonce.encode()).hexdigest(),customer['id'],ticket['app_id'],ticket['openid'],json.dumps(templates),stamp+300))
            return {'nonce':nonce,'templates':templates}

    @app.post('/studio-api/auth/notifications/wechat/subscribe')
    def subscribe(payload:Subscription,customer=Depends(require_customer)):
        with database() as db:
            db.execute('BEGIN IMMEDIATE');row=db.execute('SELECT * FROM studio_customer_wechat_nonces WHERE hash=? AND owner_id=?',(hashlib.sha256(payload.nonce.encode()).hexdigest(),customer['id'])).fetchone()
            if not row or row['expires_at']<time.time():raise HTTPException(409,'notification_wechat_expired')
            templates=json.loads(row['templates']);ids={t['template_id'] for t in templates};result=json.dumps(payload.results,sort_keys=True)
            if not set(payload.results).issubset(ids) or any(v not in ('accept','reject','ban') for v in payload.results.values()):raise HTTPException(422,'notification_wechat_unavailable')
            if row['result']:
                if row['result']!=result:raise HTTPException(409,'notification_wechat_expired')
                return {'ok':True}
            db.execute('UPDATE studio_customer_wechat_nonces SET result=? WHERE hash=?',(result,row['hash']))
            for template in templates:
                choice=payload.results.get(template['template_id'])
                if choice is None:continue
                db.execute('''INSERT INTO studio_customer_wechat_grants VALUES(?,?,?,?,?,?) ON CONFLICT(owner_id,app_id,kind)
                  DO UPDATE SET openid=excluded.openid,template_id=excluded.template_id,
                  grants=CASE WHEN ? THEN min(100,CASE WHEN template_id=excluded.template_id THEN grants ELSE 0 END+1) ELSE 0 END''',
                  (customer['id'],row['app_id'],row['openid'],template['kind'],template['template_id'],1 if choice=='accept' else 0,choice=='accept'))
            db.execute("UPDATE studio_customer_notification_jobs SET state='queued',next_attempt=? WHERE owner_id=? AND state='waiting_subscription'",(time.time(),customer['id']))
            return {'ok':True}

    @app.get('/studio-api/manage/customer-notifications')
    def delivery_status(_actor=Depends(admin_actor)):
        with database() as db:
            items=[dict(r) for r in db.execute('SELECT id,reservation_id,kind,channel,state,error,attempts,created_at,updated_at FROM studio_customer_notification_jobs ORDER BY created_at DESC LIMIT 80')]
            templates=[dict(r) for r in db.execute('SELECT kind,title FROM studio_customer_notification_templates')]
            return {'items':items,'templates':templates,'email_configured':all(email_credentials())}
