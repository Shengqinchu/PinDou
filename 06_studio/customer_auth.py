"""Share the generator's verified email accounts without copying its user/password DB."""
from __future__ import annotations

import hashlib
import json
import re
import time
from typing import Annotated
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request as URLRequest, build_opener

from fastapi import Header, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

_database = None
_origin = "http://127.0.0.1:8000"
PATHS = {"profile", "email/send-code", "email/verify", "email-login", "register"}
EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise HTTPException(503, "account_unavailable")


def initialize(database):
    with database() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS studio_auth_limits (
          scope TEXT NOT NULL, actor TEXT NOT NULL, bucket INTEGER NOT NULL,
          count INTEGER NOT NULL, PRIMARY KEY(scope,actor,bucket)
        );
        """)


def limit(request: Request, scope: str, maximum: int, seconds: int, identifier: str = ""):
    actor = hashlib.sha256((identifier or (request.client.host if request.client else "unknown")).encode()).hexdigest()
    bucket = int(time.time()) // seconds
    with _database() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT count FROM studio_auth_limits WHERE scope=? AND actor=? AND bucket=?", (scope, actor, bucket)).fetchone()
        if row and row[0] >= maximum:
            raise HTTPException(429, "account_rate_limited", headers={"Retry-After": str(seconds)})
        db.execute("DELETE FROM studio_auth_limits WHERE scope=? AND bucket<?", (scope,bucket-1))
        db.execute("INSERT INTO studio_auth_limits VALUES(?,?,?,1) ON CONFLICT(scope,actor,bucket) DO UPDATE SET count=count+1", (scope,actor,bucket))


def upstream(path: str, request: Request, body=None, token: str = "") -> dict:
    if path not in PATHS:
        raise HTTPException(503, "account_unavailable")
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    # Uvicorn only accepts forwarding information from our loopback Nginx.
    headers["X-Forwarded-For"] = request.client.host if request.client else "unknown"
    if token:
        headers["Authorization"] = "Bearer " + token
    req = URLRequest(_origin + "/api/v1/user/" + path, headers=headers,
                     data=json.dumps(body).encode() if body is not None else None)
    try:
        with build_opener(NoRedirect()).open(req, timeout=15) as response:
            data=json.loads(response.read(64000))
            if not isinstance(data,dict): raise ValueError()
            return data
    except HTTPError as exc:
        try: data=json.loads(exc.read(16000))
        except (ValueError,TypeError): data={}
        if not isinstance(data,dict):data={}
        code=data.get("error",{}).get("code") if isinstance(data.get("error"),dict) else data.get("error",data.get("code"))
        mapped={
            "EMAIL_CODE_INVALID":"account_code_invalid", "EMAIL_CODE_EXPIRED":"account_code_expired",
            "EMAIL_CODE_ATTEMPTS_EXCEEDED":"account_rate_limited", "EMAIL_CODE_RATE_LIMITED":"account_rate_limited",
            "EMAIL_ALREADY_REGISTERED":"account_already_registered", "EMAIL_NOT_REGISTERED":"account_password_invalid",
            "PASSWORD_INVALID":"account_password_invalid", "EMAIL_SEND_FAILED":"account_email_unavailable",
            "VALIDATION_ERROR":"account_check_details",
        }.get(code)
        if exc.code==429: raise HTTPException(429,"account_rate_limited") from None
        if path=="profile" and exc.code in (401,403,404): raise HTTPException(401,"account_login_required") from None
        if path=="email-login" and exc.code in (400,401,404): raise HTTPException(401,"account_password_invalid") from None
        raise HTTPException(exc.code if 400<=exc.code<500 else 503, mapped or ("account_check_details" if exc.code==422 else "account_unavailable")) from None
    except (URLError,TimeoutError,OSError,ValueError):
        raise HTTPException(503,"account_unavailable") from None


def public_user(data: dict) -> dict:
    ident = data.get("user_id")
    email = data.get("email") or ''
    # Profiles come from the authenticated generator API. Only its signed
    # Authing bridge can create this namespace; legacy wx_ stubs remain denied.
    if (not isinstance(ident,str) or not 1 <= len(ident) <= 128 or not isinstance(email,str)
        or not (EMAIL.fullmatch(email) or (not email and re.fullmatch(r'wechat_authing_[a-f0-9]{64}',ident)))):
        raise HTTPException(401,"account_email_required")
    avatar=data.get("avatar")
    return {"id":ident,"email":email,"nickname":str(data.get("nickname") or "")[:80],
            "avatar":avatar if isinstance(avatar,str) and len(avatar)<=2048 else ""}


def require_customer(request: Request, authorization: Annotated[str | None, Header()] = None) -> dict:
    if not authorization or not authorization.startswith("Bearer ") or len(authorization)>5000:
        raise HTTPException(401,"account_login_required")
    customer=public_user(upstream("profile",request,token=authorization[7:]))
    import wallet
    wallet.remember_customer(customer)
    return customer


class EmailInput(BaseModel):
    model_config=ConfigDict(extra="forbid")
    email: str = Field(min_length=3,max_length=255)

    @field_validator("email")
    @classmethod
    def normalize(cls,value):
        value=value.strip().lower()
        if not EMAIL.fullmatch(value):raise ValueError("Invalid email")
        return value


class CodeInput(EmailInput):
    code: str = Field(pattern=r"^\d{6}$")


class RegisterInput(CodeInput):
    password: str = Field(min_length=6,max_length=128)


class PasswordInput(EmailInput):
    password: str = Field(min_length=1,max_length=128)


class PasswordRegistration(EmailInput):
    password: str = Field(min_length=6,max_length=128)


def signed_in(path, payload, request):
    limit(request,"login-ip",30,600)
    limit(request,"login-email",10,600,payload.email)
    result=upstream(path,request,payload.model_dump())
    token=result.get("token")
    if not isinstance(token,str) or not 1<=len(token)<=5000:
        raise HTTPException(503,"account_unavailable")
    profile=result.get("user")
    if not isinstance(profile,dict):raise HTTPException(503,"account_unavailable")
    customer=public_user(profile)
    import wallet
    wallet.remember_customer(customer)
    return {"token":token,"user":customer,"shared_user":profile}


def register(app, database, origin):
    global _database,_origin
    _database=database;_origin=origin.rstrip("/")

    @app.get("/studio-api/auth/options")
    def options():
        import authing_login
        return {"email":False,"password":True,"recovery":True,"wechat":authing_login.available(),"phone":False}

    @app.get("/studio-api/auth/me")
    def me(request: Request, authorization: Annotated[str | None,Header()]=None):
        return {"user":require_customer(request,authorization)}

    @app.post("/studio-api/auth/send-code")
    def send_code(payload: EmailInput,request: Request):
        raise HTTPException(410,"account_code_login_disabled")

    @app.post("/studio-api/auth/code-login")
    def code_login(payload: CodeInput,request: Request):
        raise HTTPException(410,"account_code_login_disabled")

    @app.post("/studio-api/auth/password-login")
    def password_login(payload: PasswordInput,request: Request):
        return signed_in("email-login",payload,request)

    @app.post('/studio-api/auth/password-register')
    def password_register(payload:PasswordRegistration,request:Request):
        import authing_login,wallet
        authing_login.same_origin(request)
        limit(request,'register-ip-minute',3,60);limit(request,'register-ip-day',30,86400)
        limit(request,'register-email-hour',5,3600,payload.email)
        result=authing_login.account_action('password_register',**payload.model_dump(),ip=request.client.host if request.client else 'unknown')
        wallet.remember_customer(result['user'])
        return result

    @app.post("/studio-api/auth/register")
    def create(payload: RegisterInput,request: Request):
        raise HTTPException(410,"account_code_login_disabled")

    @app.post('/studio-api/auth/recovery/send-code')
    def recovery_code(payload:EmailInput,request:Request):
        import authing_login
        authing_login.same_origin(request)
        limit(request,'recovery-ip-minute',3,60);limit(request,'recovery-email-hour',5,3600,payload.email)
        return authing_login.account_action('recovery_send',email=payload.email,ip=request.client.host if request.client else 'unknown')

    @app.post('/studio-api/auth/recovery/reset-password')
    def recovery_reset(payload:RegisterInput,request:Request):
        import authing_login
        authing_login.same_origin(request)
        limit(request,'recovery-reset-ip',20,600);limit(request,'recovery-reset-email',10,600,payload.email)
        return authing_login.account_action('recovery_reset',**payload.model_dump())
