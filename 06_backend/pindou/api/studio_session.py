"""Loopback-only exchange for a Studio-verified, already-linked customer identity.

Studio never receives the generator signing secret. This narrowly scoped bridge
can only issue user sessions for existing accounts; it cannot create admins or
move assets. HMAC assertions expire quickly and have single-use nonces.
"""
from __future__ import annotations
import hashlib
import hmac
import json
import os
import time
import re
from typing import Annotated
from typing import Literal

from fastapi import APIRouter, Header, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from pindou.api.deps import DbSession
from pindou.api.errors import ApiException
from pindou.api.security import create_access_token
from pindou.api.user import user_payload
from pindou.db.models import User

router=APIRouter(prefix='/studio-session',tags=['studio-session'])


class Assertion(BaseModel):
    model_config=ConfigDict(extra='forbid')
    user_id: str=Field(min_length=1,max_length=128)
    issued_at: int=Field(strict=True)
    nonce: str=Field(pattern=r'^[a-f0-9]{32}$')
    audience: str=Field(pattern=r'^pindou-studio-customer$')


@router.post('/exchange')
def exchange(payload:Assertion,request:Request,db:DbSession,
             signature:Annotated[str,Header(alias='X-Studio-Signature')]=''):
    secret=os.getenv('PINDOU_STUDIO_AUTH_BRIDGE_KEY','')
    if len(secret)<32: raise ApiException(503,'STUDIO_SESSION_DISABLED','登录服务尚未配置。')
    if not request.client or request.client.host not in ('127.0.0.1','::1'):
        raise ApiException(403,'STUDIO_SESSION_FORBIDDEN','无法完成登录。')
    message=json.dumps(payload.model_dump(),sort_keys=True,separators=(',',':')).encode()
    expected=hmac.new(secret.encode(),message,hashlib.sha256).hexdigest()
    now=int(time.time())
    if not hmac.compare_digest(signature,expected) or not -5<=now-payload.issued_at<=30:
        raise ApiException(401,'STUDIO_SESSION_INVALID','登录验证已失效。')
    user=db.scalar(select(User).where(User.openid==payload.user_id))
    if user is None or (not user.email and not re.fullmatch(r'wechat_authing_[a-f0-9]{64}',user.openid)):
        raise ApiException(401,'STUDIO_SESSION_UNKNOWN','请先验证邮箱账号。')
    db.execute(text('CREATE TABLE IF NOT EXISTS studio_session_nonces (nonce TEXT PRIMARY KEY,created_at INTEGER NOT NULL)'))
    db.execute(text('DELETE FROM studio_session_nonces WHERE created_at<:cutoff'),{'cutoff':now-120})
    try:
        db.execute(text('INSERT INTO studio_session_nonces(nonce,created_at) VALUES(:nonce,:at)'),{'nonce':payload.nonce,'at':now})
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ApiException(409,'STUDIO_SESSION_REPLAY','登录验证已使用，请重新登录。') from None
    return {'token':create_access_token(subject=user.user_id,role='user',is_admin=False),'user':user_payload(db,user)}


class AccountAssertion(BaseModel):
    model_config=ConfigDict(extra='forbid')
    action:Literal['wechat_create','password_register','recovery_send','recovery_reset']
    issued_at:int=Field(strict=True)
    nonce:str=Field(pattern=r'^[a-f0-9]{32}$')
    audience:Literal['pindou-studio-account']
    subject_key:str|None=Field(default=None,pattern=r'^[a-f0-9]{64}$')
    email:str|None=Field(default=None,min_length=3,max_length=254)
    ip:str|None=Field(default=None,max_length=64)
    code:str|None=Field(default=None,pattern=r'^\d{6}$')
    password:str|None=Field(default=None,min_length=6,max_length=128)


@router.post('/account')
async def account(payload:AccountAssertion,request:Request,db:DbSession,
                  signature:Annotated[str,Header(alias='X-Studio-Signature')]=''):
    secret=os.getenv('PINDOU_STUDIO_AUTH_BRIDGE_KEY','')
    if len(secret)<32:raise ApiException(503,'STUDIO_SESSION_DISABLED','登录服务尚未配置。')
    if not request.client or request.client.host not in ('127.0.0.1','::1'):
        raise ApiException(403,'STUDIO_SESSION_FORBIDDEN','无法完成登录。')
    message=json.dumps(payload.model_dump(exclude_unset=True),sort_keys=True,separators=(',',':')).encode()
    expected=hmac.new(secret.encode(),message,hashlib.sha256).hexdigest();now=int(time.time())
    if not hmac.compare_digest(signature,expected) or not -5<=now-payload.issued_at<=30:
        raise ApiException(401,'STUDIO_SESSION_INVALID','登录验证已失效。')
    db.execute(text('CREATE TABLE IF NOT EXISTS studio_session_nonces (nonce TEXT PRIMARY KEY,created_at INTEGER NOT NULL)'))
    db.execute(text('DELETE FROM studio_session_nonces WHERE created_at<:cutoff'),{'cutoff':now-120})
    try:
        db.execute(text('INSERT INTO studio_session_nonces VALUES(:nonce,:at)'),{'nonce':payload.nonce,'at':now});db.commit()
    except IntegrityError:
        db.rollback();raise ApiException(409,'STUDIO_SESSION_REPLAY','登录验证已使用，请重试。') from None
    from pindou.services import studio_accounts
    if payload.action=='wechat_create' and payload.subject_key:
        user=studio_accounts.wechat_account(db,payload.subject_key)
        return {'token':create_access_token(subject=user.user_id,role='user',is_admin=False),'user':user_payload(db,user)}
    if payload.action=='password_register' and payload.email and payload.password and payload.ip:
        user=studio_accounts.password_account(db,payload.email,payload.password,payload.ip)
        if isinstance(user,dict):return user
        return {'token':create_access_token(subject=user.user_id,role='user',is_admin=False),'user':user_payload(db,user)}
    if payload.action=='recovery_send' and payload.email and payload.ip:
        return await studio_accounts.send_recovery(db,payload.email,payload.ip)
    if payload.action=='recovery_reset' and payload.email and payload.code and payload.password:
        return studio_accounts.reset_password(db,payload.email,payload.code,payload.password)
    raise ApiException(422,'STUDIO_ACCOUNT_INVALID','请检查填写的信息。')
