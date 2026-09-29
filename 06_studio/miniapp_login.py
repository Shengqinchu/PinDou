"""First-party WeChat mini-program identity and browser-bound QR approval.

WeChat codes are exchanged only by this server. A scan cannot itself create or
merge an account; existing-account binding requires a signed customer session.
"""
from __future__ import annotations

import base64
import hmac
import json
import os
import re
import secrets
import threading
import time
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request as URLRequest, build_opener

from fastapi import HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field

import authing_login as auth
import wallet
import account_recovery
from customer_auth import NoRedirect, limit, require_customer

LIFETIME=300
TICKET_LIFETIME=600
_access_lock=threading.Lock()
_access_cache={}


@dataclass(frozen=True)
class Config:
    app_id:str
    secret:str
    enabled:bool
    environment:str='release'


def config():
    return Config(os.getenv('STUDIO_MINIAPP_APP_ID',''),os.getenv('STUDIO_MINIAPP_APP_SECRET',''),
                  os.getenv('STUDIO_MINIAPP_ENABLED','0')=='1',os.getenv('STUDIO_MINIAPP_ENV','release'))


def available():
    c=config()
    return bool(c.enabled and re.fullmatch(r'wx[a-fA-F0-9]{16}',c.app_id) and len(c.secret)>=16
                and c.environment in ('release','trial','develop') and len(auth.config().bridge_key)>=32)


def initialize(database):
    with database() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS studio_miniapp_identities (
          app_id TEXT NOT NULL,openid TEXT NOT NULL,user_id TEXT NOT NULL,created_at INTEGER NOT NULL,
          PRIMARY KEY(app_id,openid),UNIQUE(app_id,user_id)
        );
        CREATE TABLE IF NOT EXISTS studio_miniapp_tickets (
          token_hash TEXT PRIMARY KEY,app_id TEXT NOT NULL,openid TEXT NOT NULL,expires_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS studio_miniapp_flows (
          state_hash TEXT PRIMARY KEY,scene_hash TEXT NOT NULL UNIQUE,browser_hash TEXT NOT NULL,
          app_id TEXT NOT NULL,origin TEXT NOT NULL,return_to TEXT NOT NULL,
          created_at INTEGER NOT NULL,expires_at INTEGER NOT NULL,status TEXT NOT NULL,
          link_user TEXT NOT NULL DEFAULT '',link_label TEXT NOT NULL DEFAULT '',openid TEXT NOT NULL DEFAULT '',
          display_code TEXT NOT NULL,result TEXT NOT NULL DEFAULT ''
        );
        ''')


def wx_request(path,body=None,params=None,binary=False,return_errors=False):
    url='https://api.weixin.qq.com/'+path
    if params:url+='?'+urlencode(params)
    request=URLRequest(url,data=None if body is None else json.dumps(body).encode(),
        headers={'Content-Type':'application/json','User-Agent':'PinDouStudio/1.0'})
    try:
        with build_opener(NoRedirect()).open(request,timeout=15) as response:
            data=response.read(600001)
        if len(data)>600000:raise ValueError()
        if binary and (data.startswith(b'\x89PNG\r\n\x1a\n') or data.startswith(b'\xff\xd8\xff')):
            return data
        result=json.loads(data)
        if not isinstance(result,dict):raise ValueError()
        if result.get('errcode') and not return_errors:
            error='miniapp_code_expired' if result['errcode'] in (40029,40163) else 'miniapp_provider_unavailable'
            raise HTTPException(400 if error=='miniapp_code_expired' else 503,error)
        if binary:raise ValueError()
        return result
    except (HTTPError,URLError,TimeoutError,OSError,ValueError):
        # URL exceptions contain the app secret or access token. Never log them.
        raise HTTPException(503,'miniapp_provider_unavailable') from None


def exchange_code(code):
    c=config()
    result=wx_request('sns/jscode2session',params={'appid':c.app_id,'secret':c.secret,'js_code':code,'grant_type':'authorization_code'})
    openid=result.get('openid')
    if not isinstance(openid,str) or not re.fullmatch(r'[A-Za-z0-9_-]{16,128}',openid):
        raise HTTPException(400,'wechat_identity_invalid')
    # session_key and unionid are not needed and never leave this function.
    return openid


def access_token():
    c=config();cache_key=(c.app_id,auth.digest(c.secret))
    with _access_lock:
        cached=_access_cache.get(cache_key)
        if cached and cached[1]>time.time()+60:return cached[0]
        result=wx_request('cgi-bin/stable_token',{'grant_type':'client_credential','appid':c.app_id,'secret':c.secret,'force_refresh':False})
        token=result.get('access_token');expires=result.get('expires_in')
        if not isinstance(token,str) or not 20<=len(token)<=1024 or not isinstance(expires,int) or expires<=60:
            raise HTTPException(503,'miniapp_provider_unavailable')
        _access_cache.clear();_access_cache[cache_key]=(token,time.time()+min(expires,7200))
        return token


def qr_image(scene):
    data=wx_request('wxa/getwxacodeunlimit',{'scene':scene,'page':'pages/auth/studio-confirm','width':360,
        'check_path':config().environment=='release','env_version':config().environment,
        'auto_color':False,'line_color':{'r':45,'g':50,'b':53}},params={'access_token':access_token()},binary=True)
    mime='image/png' if data.startswith(b'\x89PNG') else 'image/jpeg'
    return 'data:'+mime+';base64,'+base64.b64encode(data).decode()


def ensure_available():
    if not available():raise HTTPException(503,'miniapp_not_configured')


def ticket_for(db,request):
    token=request.headers.get('X-Pindou-Miniapp','')
    if not re.fullmatch(r'[A-Za-z0-9_-]{43}',token):raise HTTPException(401,'miniapp_session_expired')
    row=db.execute('SELECT * FROM studio_miniapp_tickets WHERE token_hash=?',(auth.digest(token),)).fetchone()
    if not row or row['app_id']!=config().app_id or row['expires_at']<=int(time.time()):
        raise HTTPException(401,'miniapp_session_expired')
    return row


def flow_for(db,state,request):
    row=db.execute('SELECT * FROM studio_miniapp_flows WHERE state_hash=?',(auth.digest(state),)).fetchone()
    cookie=request.cookies.get(auth.COOKIE,'')
    if not row or row['expires_at']<=int(time.time()) or row['app_id']!=config().app_id or not cookie or not hmac.compare_digest(row['browser_hash'],auth.digest(cookie)):
        raise HTTPException(400,'wechat_flow_expired')
    if row['origin']!=auth.origin_of(request):raise HTTPException(403,'wechat_origin_invalid')
    return row


def scan_flow(db,scene,ticket):
    row=db.execute('SELECT * FROM studio_miniapp_flows WHERE scene_hash=?',(auth.digest(scene),)).fetchone()
    if not row or row['app_id']!=ticket['app_id'] or row['expires_at']<=int(time.time()):
        raise HTTPException(400,'wechat_flow_expired')
    if row['openid'] and row['openid']!=ticket['openid']:raise HTTPException(409,'miniapp_other_scanner')
    return row


def identity(db,openid):
    return db.execute('SELECT user_id FROM studio_miniapp_identities WHERE app_id=? AND openid=?',(config().app_id,openid)).fetchone()


def bind_identity(db,openid,user_id):
    c=config()
    rows=db.execute('SELECT openid,user_id FROM studio_miniapp_identities WHERE app_id=? AND (openid=? OR user_id=?)',(c.app_id,openid,user_id)).fetchall()
    if any(row['user_id']!=user_id or row['openid']!=openid for row in rows):raise HTTPException(409,'wechat_binding_conflict')
    db.execute('INSERT OR IGNORE INTO studio_miniapp_identities VALUES(?,?,?,?)',(c.app_id,openid,user_id,int(time.time())))


def create_identity(db,openid):
    existing=identity(db,openid)
    if existing:return auth.shared_session(existing['user_id'])
    # Keep the bridge's existing internal user namespace. The hash is domain
    # separated from Authing subjects; no generator change or asset migration.
    subject_key=auth.digest('pindou-native-wechat-v1|'+config().app_id+'|'+openid)
    if account_recovery.retired(db,'wechat_authing_'+subject_key):
        raise HTTPException(409,'wechat_binding_conflict')
    result=auth.account_action('wechat_create',subject_key=subject_key)
    expected='wechat_authing_'+subject_key
    if result['user']['id']!=expected:raise HTTPException(400,'wechat_identity_invalid')
    bind_identity(db,openid,expected)
    return result


class Code(BaseModel):
    model_config=ConfigDict(extra='forbid')
    code:str=Field(min_length=3,max_length=256)


class Scan(BaseModel):
    model_config=ConfigDict(extra='forbid')
    scene:str=Field(pattern=r'^[A-Za-z0-9_-]{24}$')


class Confirm(Scan):
    approve:bool
    display_code:str=Field(pattern=r'^\d{4}$')


def register(app,database):
    prefix='/studio-api/auth/wechat/miniapp'

    @app.post(prefix+'/session')
    def session(payload:Code,request:Request):
        ensure_available();limit(request,'miniapp-session',30,600)
        openid=exchange_code(payload.code);token=secrets.token_urlsafe(32);now=int(time.time())
        with database() as db:
            db.execute('DELETE FROM studio_miniapp_tickets WHERE expires_at<=?',(now,))
            db.execute('INSERT INTO studio_miniapp_tickets VALUES(?,?,?,?)',(auth.digest(token),config().app_id,openid,now+TICKET_LIFETIME))
            linked=bool(identity(db,openid))
        return {'ticket':token,'linked':linked,'expires_in':TICKET_LIFETIME}

    @app.post(prefix+'/native/sign-in')
    def native_sign_in(request:Request):
        ensure_available()
        with database() as db:
            ticket=ticket_for(db,request);linked=identity(db,ticket['openid'])
        if not linked:raise HTTPException(409,'miniapp_account_required')
        result=auth.shared_session(linked['user_id'])
        wallet.remember_customer(result['user'])
        return result

    @app.post(prefix+'/native/bind')
    def native_bind(request:Request):
        ensure_available();customer=require_customer(request,request.headers.get('authorization'))
        with database() as db:
            db.execute('BEGIN IMMEDIATE');ticket=ticket_for(db,request)
            try:
                bind_identity(db,ticket['openid'],customer['id'])
            except HTTPException as exc:
                if exc.status_code!=409 or exc.detail!='wechat_binding_conflict':raise
                account_recovery.record_conflict(db,config().app_id,ticket['openid'],customer['id'])
                # Released native clients save the already-verified password
                # session only after this call. Keep that login usable without
                # overwriting either binding. Updated clients explain this result.
                return {'linked':False,'reason':'wechat_binding_conflict'}
        return {'linked':True}

    @app.post(prefix+'/native/create')
    def native_create(request:Request):
        ensure_available();limit(request,'miniapp-create',6,600)
        with database() as db:
            db.execute('BEGIN IMMEDIATE');ticket=ticket_for(db,request)
            result=create_identity(db,ticket['openid'])
        wallet.remember_customer(result['user'])
        return result

    @app.post(prefix+'/qr/start')
    def start(payload:auth.Start,request:Request,response:Response):
        ensure_available();origin=auth.same_origin(request);target=auth.safe_return(payload.return_to)
        customer=require_customer(request,request.headers.get('authorization')) if payload.mode=='link' else None
        limit(request,'miniapp-qr-start',12,600)
        state=secrets.token_urlsafe(32);scene=secrets.token_urlsafe(18)
        image=qr_image(scene);now=int(time.time())
        cookie=request.cookies.get(auth.COOKIE,'')
        if not re.fullmatch(r'[A-Za-z0-9_-]{43}',cookie):cookie=secrets.token_urlsafe(32)
        display_code=str(secrets.randbelow(9000)+1000)
        with database() as db:
            db.execute('DELETE FROM studio_miniapp_flows WHERE expires_at<=?',(now,))
            db.execute('''INSERT INTO studio_miniapp_flows(state_hash,scene_hash,browser_hash,app_id,origin,return_to,
                created_at,expires_at,status,link_user,link_label,display_code) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)''',
                (auth.digest(state),auth.digest(scene),auth.digest(cookie),config().app_id,origin,target,now,now+LIFETIME,
                 'qr_pending',customer['id'] if customer else '',customer['nickname'] if customer else '',display_code))
        response.set_cookie(auth.COOKIE,cookie,max_age=auth.FLOW_LIFETIME,httponly=True,secure=auth.config().secure,samesite='lax',path='/studio-api/auth/wechat')
        return {'state':state,'image':image,'expires_in':LIFETIME,'display_code':display_code,'provider':'miniapp'}

    @app.post(prefix+'/scan')
    def scan(payload:Scan,request:Request):
        ensure_available()
        with database() as db:
            db.execute('BEGIN IMMEDIATE');ticket=ticket_for(db,request);row=scan_flow(db,payload.scene,ticket)
            if row['status']=='qr_pending':
                db.execute("UPDATE studio_miniapp_flows SET status='qr_scanned',openid=? WHERE state_hash=?",(ticket['openid'],row['state_hash']))
            return {'status':'qr_scanned' if row['status']=='qr_pending' else row['status'],
                    'site':'pindoupuppy.com','mode':'link' if row['link_user'] else 'login','account':row['link_label'],'display_code':row['display_code']}

    @app.post(prefix+'/confirm')
    def confirm(payload:Confirm,request:Request):
        ensure_available()
        with database() as db:
            db.execute('BEGIN IMMEDIATE');ticket=ticket_for(db,request);row=scan_flow(db,payload.scene,ticket)
            if row['display_code']!=payload.display_code:raise HTTPException(400,'miniapp_confirmation_mismatch')
            if row['status'] in ('linked','ready','needs_email','consumed'):
                return {'status':'approved'}
            if row['status']!='qr_scanned':raise HTTPException(409,'wechat_flow_used')
            if not payload.approve:
                db.execute("UPDATE studio_miniapp_flows SET status='denied' WHERE state_hash=?",(row['state_hash'],))
                return {'status':'denied'}
            linked=identity(db,ticket['openid']);result=''
            if row['link_user']:
                bind_identity(db,ticket['openid'],row['link_user']);status='linked'
            elif linked:
                result=json.dumps(auth.shared_session(linked['user_id']));status='ready'
            else:status='needs_email'
            db.execute('UPDATE studio_miniapp_flows SET status=?,result=? WHERE state_hash=?',(status,result,row['state_hash']))
        return {'status':'approved'}

    @app.post(prefix+'/qr/poll')
    def poll(payload:auth.FlowAction,request:Request):
        ensure_available();auth.same_origin(request)
        with database() as db:row=flow_for(db,payload.state,request)
        return {'status':'failed' if row['status']=='denied' else row['status'],'error':'wechat_cancelled' if row['status']=='denied' else ''}

    @app.post(prefix+'/bind')
    def web_bind(payload:auth.FlowAction,request:Request):
        ensure_available();auth.same_origin(request);customer=require_customer(request,request.headers.get('authorization'))
        with database() as db:
            db.execute('BEGIN IMMEDIATE');row=flow_for(db,payload.state,request)
            if row['status']!='needs_email' or not row['openid'] or row['link_user']:raise HTTPException(409,'wechat_flow_used')
            bind_identity(db,row['openid'],customer['id'])
            db.execute("UPDATE studio_miniapp_flows SET status='linked',result='' WHERE state_hash=?",(row['state_hash'],))
        return {'linked':True}

    @app.post(prefix+'/create-account')
    def web_create(payload:auth.FlowAction,request:Request):
        ensure_available();auth.same_origin(request);limit(request,'miniapp-create',6,600)
        with database() as db:
            db.execute('BEGIN IMMEDIATE');row=flow_for(db,payload.state,request)
            if row['status']=='ready':return {'status':'ready'}
            if row['status']!='needs_email' or not row['openid'] or row['link_user']:raise HTTPException(409,'wechat_flow_used')
            result=create_identity(db,row['openid'])
            db.execute("UPDATE studio_miniapp_flows SET status='ready',result=? WHERE state_hash=?",(json.dumps(result),row['state_hash']))
        return {'status':'ready'}

    @app.post(prefix+'/finish')
    def finish(payload:auth.FlowAction,request:Request):
        ensure_available();auth.same_origin(request)
        with database() as db:
            db.execute('BEGIN IMMEDIATE');row=flow_for(db,payload.state,request)
            if row['status']!='ready' or not row['result']:raise HTTPException(409,'wechat_flow_used')
            result=json.loads(row['result']);result['return_to']=row['return_to']
            db.execute("UPDATE studio_miniapp_flows SET status='consumed',result='' WHERE state_hash=?",(row['state_hash'],))
        wallet.remember_customer(result['user'])
        return result

    @app.get(prefix+'/binding')
    def binding(request:Request):
        customer=require_customer(request,request.headers.get('authorization'))
        with database() as db:
            row=db.execute('SELECT 1 FROM studio_miniapp_identities WHERE app_id=? AND user_id=?',(config().app_id,customer['id'])).fetchone()
        return {'linked':bool(row)}
