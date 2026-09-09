"""Authing authorization-code login, linked to the existing email account.

Provider tokens never enter URLs or the browser. The callback validates state,
cookie, PKCE and OIDC claims before linking or asking the generator to issue its
ordinary customer JWT. Linking never merges by nickname or unverified email.
"""
from __future__ import annotations
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import time
import uuid
from dataclasses import dataclass
from functools import lru_cache
from typing import Literal
from urllib.parse import urlencode, urlsplit, unquote
from urllib.request import Request as URLRequest, build_opener
from urllib.error import HTTPError, URLError

import jwt
from fastapi import Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, ConfigDict, Field
from customer_auth import NoRedirect, limit, public_user, require_customer

COOKIE='puppy_wechat_browser'
FLOW_LIFETIME=900
CALLBACK='/studio-api/auth/wechat/callback'
_database=None


@dataclass(frozen=True)
class Config:
    app_id:str
    issuer:str
    secret:str
    bridge_key:str
    backend:str
    origins:tuple[str,...]
    enabled:bool
    secure:bool=True


def config():
    return Config(os.getenv('STUDIO_AUTHING_APP_ID',''),os.getenv('STUDIO_AUTHING_ISSUER','').rstrip('/'),
        os.getenv('STUDIO_AUTHING_APP_SECRET',''),os.getenv('PINDOU_STUDIO_AUTH_BRIDGE_KEY',''),
        os.getenv('STUDIO_ADMIN_ORIGIN','http://127.0.0.1:8000').rstrip('/'),
        tuple(x.strip() for x in os.getenv('STUDIO_PUBLIC_ORIGINS','https://pindoupuppy.com,https://www.pindoupuppy.com').split(',') if x.strip()),
        os.getenv('STUDIO_WECHAT_ENABLED','0')=='1',os.getenv('STUDIO_AUTH_COOKIE_SECURE','1')!='0')


def available():
    c=config()
    parsed=urlsplit(c.issuer)
    return bool(c.enabled and c.app_id and c.secret and len(c.bridge_key)>=32 and parsed.scheme=='https'
                and parsed.hostname and parsed.hostname.endswith('.authing.cn') and not parsed.username and not parsed.query)


def initialize(database):
    with database() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS studio_oauth_flows (
          state_hash TEXT PRIMARY KEY,browser_hash TEXT NOT NULL,nonce TEXT NOT NULL,verifier TEXT NOT NULL,
          origin TEXT NOT NULL,return_to TEXT NOT NULL,created_at INTEGER NOT NULL,expires_at INTEGER NOT NULL,
          status TEXT NOT NULL,subject TEXT NOT NULL DEFAULT '',bound_user TEXT NOT NULL DEFAULT '',link_user TEXT NOT NULL DEFAULT '',
          result TEXT NOT NULL DEFAULT '',error TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS studio_auth_identities (
          issuer TEXT NOT NULL,app_id TEXT NOT NULL,subject TEXT NOT NULL,user_id TEXT NOT NULL,
          created_at INTEGER NOT NULL,PRIMARY KEY(issuer,app_id,subject),UNIQUE(issuer,app_id,user_id)
        );
        ''')
        if 'link_user' not in {r[1] for r in db.execute('PRAGMA table_info(studio_oauth_flows)')}:
            db.execute("ALTER TABLE studio_oauth_flows ADD COLUMN link_user TEXT NOT NULL DEFAULT ''")


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def safe_return(value):
    decoded=unquote(value)
    path=urlsplit(value)
    if (not value.startswith('/') or value.startswith('//') or '\\' in decoded or
        any(ord(x)<32 for x in decoded) or path.scheme or path.netloc or
        path.path.startswith(('/studio-api','/api','/auth/'))):
        raise HTTPException(422,'wechat_return_invalid')
    if not re.fullmatch(r'/(?:visit|upload|tutorial|loading|works|details|shop|journal(?:/[A-Za-z0-9_-]+)?|account|(?:reservation|editor|result)/[A-Za-z0-9_-]+)?',path.path):
        raise HTTPException(422,'wechat_return_invalid')
    return value


def origin_of(request):
    origin=str(request.base_url).rstrip('/')
    if origin not in config().origins:
        raise HTTPException(400,'wechat_origin_invalid')
    return origin


def same_origin(request):
    origin=origin_of(request)
    if request.headers.get('origin')!=origin:
        raise HTTPException(403,'wechat_origin_invalid')
    return origin


def flow_for(db,state,request):
    if not re.fullmatch(r'[A-Za-z0-9_-]{43}',state): raise HTTPException(400,'wechat_flow_expired')
    row=db.execute('SELECT * FROM studio_oauth_flows WHERE state_hash=?',(digest(state),)).fetchone()
    cookie=request.cookies.get(COOKIE,'')
    if not row or row['expires_at']<int(time.time()) or not cookie or not hmac.compare_digest(row['browser_hash'],digest(cookie)):
        raise HTTPException(400,'wechat_flow_expired')
    if row['origin']!=origin_of(request): raise HTTPException(403,'wechat_origin_invalid')
    return row


def fetch_json(url,body=None,headers=None,form=False):
    data=None if body is None else (urlencode(body).encode() if form else json.dumps(body,sort_keys=True,separators=(',',':')).encode())
    req=URLRequest(url,data=data,headers={'Accept':'application/json','Content-Type':'application/x-www-form-urlencoded' if form else 'application/json',**(headers or {})})
    try:
        with build_opener(NoRedirect()).open(req,timeout=15) as response:
            raw=response.read(128001)
            if len(raw)>128000: raise ValueError()
            result=json.loads(raw)
            if not isinstance(result,dict): raise ValueError()
            return result
    except (HTTPError,URLError,TimeoutError,OSError,ValueError,HTTPException):
        raise HTTPException(503,'wechat_provider_unavailable') from None


@lru_cache(maxsize=8)
def signing_keys(issuer,bucket):
    return fetch_json(issuer+'/.well-known/jwks.json').get('keys',[])


def verify_id_token(token,nonce):
    c=config()
    try:
        header=jwt.get_unverified_header(token)
        algorithm=header.get('alg')
        if algorithm=='RS256':
            keys=signing_keys(c.issuer,int(time.time())//300)
            key=next((k for k in keys if k.get('kid')==header.get('kid') and k.get('kty')=='RSA' and k.get('use','sig')=='sig'),None)
            if key is None:
                signing_keys.cache_clear()
                keys=signing_keys(c.issuer,int(time.time())//300)
                key=next((k for k in keys if k.get('kid')==header.get('kid') and k.get('kty')=='RSA' and k.get('use','sig')=='sig'),None)
            if key is None: raise ValueError()
            signing_key=jwt.PyJWK.from_dict(key,algorithm='RS256').key
        elif algorithm=='HS256':
            # Authing can issue HS256 ID tokens. This uses the app secret only,
            # never an RSA public key supplied in a header or a token URL.
            signing_key=c.secret
        else: raise ValueError()
        claims=jwt.decode(token,signing_key,algorithms=[algorithm],issuer=c.issuer,audience=c.app_id,
                          leeway=15,options={'require':['exp','iat','iss','aud','sub','nonce']})
        if not isinstance(claims['sub'],str) or not 1<=len(claims['sub'])<=128: raise ValueError()
        if claims['iss']!=c.issuer or claims.get('azp',c.app_id)!=c.app_id: raise ValueError()
        if isinstance(claims['aud'],list) and len(claims['aud'])>1 and claims.get('azp')!=c.app_id: raise ValueError()
        if not isinstance(claims['nonce'],str) or not hmac.compare_digest(claims['nonce'],nonce): raise ValueError()
        return claims['sub']
    except (jwt.PyJWTError,ValueError,TypeError,KeyError,StopIteration):
        raise HTTPException(400,'wechat_identity_invalid') from None


def shared_session(user_id):
    c=config()
    payload={'user_id':user_id,'issued_at':int(time.time()),'nonce':uuid.uuid4().hex,'audience':'pindou-studio-customer'}
    signature=hmac.new(c.bridge_key.encode(),json.dumps(payload,sort_keys=True,separators=(',',':')).encode(),hashlib.sha256).hexdigest()
    result=fetch_json(c.backend+'/api/v1/studio-session/exchange',payload,{'X-Studio-Signature':signature})
    profile=result.get('user');token=result.get('token')
    if not isinstance(profile,dict) or not isinstance(token,str) or not 1<=len(token)<=5000:
        raise HTTPException(503,'wechat_provider_unavailable')
    customer=public_user(profile)
    if customer['id']!=user_id: raise HTTPException(400,'wechat_identity_invalid')
    return {'token':token,'user':customer,'shared_user':profile}


class Start(BaseModel):
    model_config=ConfigDict(extra='forbid')
    return_to:str=Field(default='/',max_length=600)
    mode:Literal['login','link']='login'


class FlowAction(BaseModel):
    model_config=ConfigDict(extra='forbid')
    state:str=Field(pattern=r'^[A-Za-z0-9_-]{43}$')


def register(app,database):
    global _database
    _database=database

    @app.post('/studio-api/auth/wechat/start')
    def start(payload:Start,request:Request,response:Response):
        if not available(): raise HTTPException(503,'wechat_not_configured')
        origin=same_origin(request);target=safe_return(payload.return_to)
        link_user=require_customer(request,request.headers.get('authorization'))['id'] if payload.mode=='link' else ''
        limit(request,'wechat-start',12,600)
        cookie=request.cookies.get(COOKIE,'')
        if not re.fullmatch(r'[A-Za-z0-9_-]{43}',cookie): cookie=secrets.token_urlsafe(32)
        state,nonce,verifier=(secrets.token_urlsafe(32) for _ in range(3))
        challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
        now=int(time.time())
        with database() as db:
            db.execute('DELETE FROM studio_oauth_flows WHERE expires_at<?',(now,))
            db.execute('INSERT INTO studio_oauth_flows(state_hash,browser_hash,nonce,verifier,origin,return_to,created_at,expires_at,status,link_user) VALUES(?,?,?,?,?,?,?,?,?,?)',
                       (digest(state),digest(cookie),nonce,verifier,origin,target,now,now+FLOW_LIFETIME,'pending',link_user))
        response.set_cookie(COOKIE,cookie,max_age=FLOW_LIFETIME,httponly=True,secure=config().secure,samesite='lax',path='/studio-api/auth/wechat')
        c=config()
        url=c.issuer+'/auth?'+urlencode({'client_id':c.app_id,'redirect_uri':origin+CALLBACK,'response_type':'code','response_mode':'query',
            'scope':'openid','state':state,'nonce':nonce,'code_challenge':challenge,'code_challenge_method':'S256','prompt':'login'})
        return {'url':url}

    @app.get(CALLBACK)
    def callback(request:Request,state:str='',code:str='',error:str=''):
        if not available(): raise HTTPException(503,'wechat_not_configured')
        with database() as db:
            db.execute('BEGIN IMMEDIATE');row=flow_for(db,state,request)
            if row['status']!='pending': raise HTTPException(409,'wechat_flow_used')
            db.execute("UPDATE studio_oauth_flows SET status='exchanging' WHERE state_hash=?",(row['state_hash'],))
        try:
            if error or not code or len(code)>6000: raise HTTPException(400,'wechat_cancelled')
            c=config()
            tokens=fetch_json(c.issuer+'/token',{'grant_type':'authorization_code','code':code,'client_id':c.app_id,
                  'client_secret':c.secret,'redirect_uri':row['origin']+CALLBACK,'code_verifier':row['verifier']},form=True)
            token=tokens.get('id_token')
            if not isinstance(token,str) or len(token)>16000: raise HTTPException(400,'wechat_identity_invalid')
            subject=verify_id_token(token,row['nonce'])
            with database() as db:
                binding=db.execute('SELECT user_id FROM studio_auth_identities WHERE issuer=? AND app_id=? AND subject=?',(c.issuer,c.app_id,subject)).fetchone()
            if row['link_user']:
                with database() as db:
                    db.execute('BEGIN IMMEDIATE')
                    existing=db.execute('SELECT user_id,subject FROM studio_auth_identities WHERE issuer=? AND app_id=? AND (subject=? OR user_id=?)',(c.issuer,c.app_id,subject,row['link_user'])).fetchall()
                    if any(b['user_id']!=row['link_user'] or b['subject']!=subject for b in existing):
                        raise HTTPException(409,'wechat_binding_conflict')
                    db.execute('INSERT OR IGNORE INTO studio_auth_identities VALUES(?,?,?,?,?)',(c.issuer,c.app_id,subject,row['link_user'],int(time.time())))
                    db.execute("UPDATE studio_oauth_flows SET subject=?,status='linked',bound_user=?,verifier='',nonce='' WHERE state_hash=?",(subject,row['link_user'],row['state_hash']))
                return RedirectResponse(row['origin']+'/auth/wechat?'+urlencode({'state':state}),status_code=303,headers={'Cache-Control':'no-store','Referrer-Policy':'no-referrer'})
            session=shared_session(binding['user_id']) if binding else None
            with database() as db:
                db.execute("UPDATE studio_oauth_flows SET subject=?,status=?,result=?,verifier='',nonce='' WHERE state_hash=?",
                           (subject,'ready' if session else 'needs_email',json.dumps(session) if session else '',row['state_hash']))
        except HTTPException as exc:
            with database() as db:
                db.execute("UPDATE studio_oauth_flows SET status='failed',error=?,verifier='',nonce='' WHERE state_hash=?",(str(exc.detail),row['state_hash']))
        return RedirectResponse(row['origin']+'/auth/wechat?'+urlencode({'state':state}),status_code=303,
                                headers={'Cache-Control':'no-store','Referrer-Policy':'no-referrer'})

    @app.get('/studio-api/auth/wechat/flow')
    def flow(request:Request,state:str):
        with database() as db:
            row=flow_for(db,state,request)
            return {'status':row['status'],'error':row['error'],'return_to':row['return_to']}

    @app.post('/studio-api/auth/wechat/bind')
    def bind(payload:FlowAction,request:Request,customer=Depends(require_customer)):
        same_origin(request)
        c=config()
        with database() as db:
            db.execute('BEGIN IMMEDIATE');row=flow_for(db,payload.state,request)
            if row['status']!='needs_email' or not row['subject']: raise HTTPException(409,'wechat_flow_used')
            if row['link_user'] and row['link_user']!=customer['id']: raise HTTPException(409,'wechat_binding_conflict')
            existing=db.execute('SELECT user_id FROM studio_auth_identities WHERE issuer=? AND app_id=? AND subject=?',(c.issuer,c.app_id,row['subject'])).fetchone()
            another=db.execute('SELECT subject FROM studio_auth_identities WHERE issuer=? AND app_id=? AND user_id=?',(c.issuer,c.app_id,customer['id'])).fetchone()
            if (existing and existing['user_id']!=customer['id']) or (another and another['subject']!=row['subject']):
                raise HTTPException(409,'wechat_binding_conflict')
            db.execute('INSERT OR IGNORE INTO studio_auth_identities VALUES(?,?,?,?,?)',(c.issuer,c.app_id,row['subject'],customer['id'],int(time.time())))
            db.execute("UPDATE studio_oauth_flows SET status='linked',bound_user=? WHERE state_hash=?",(customer['id'],row['state_hash']))
        return {'status':'linked','return_to':row['return_to']}

    @app.post('/studio-api/auth/wechat/finish')
    def finish(payload:FlowAction,request:Request):
        same_origin(request)
        with database() as db:
            db.execute('BEGIN IMMEDIATE');row=flow_for(db,payload.state,request)
            if row['status']!='ready' or not row['result']: raise HTTPException(409,'wechat_flow_used')
            session=json.loads(row['result'])
            db.execute("UPDATE studio_oauth_flows SET status='consumed',result='',subject='' WHERE state_hash=?",(row['state_hash'],))
        import wallet
        wallet.remember_customer(session['user'])
        return session|{'return_to':row['return_to']}

    @app.get('/studio-api/auth/wechat/binding')
    def binding(customer=Depends(require_customer)):
        c=config()
        with database() as db:
            row=db.execute('SELECT created_at FROM studio_auth_identities WHERE issuer=? AND app_id=? AND user_id=?',(c.issuer,c.app_id,customer['id'])).fetchone()
        return {'linked':bool(row)}
