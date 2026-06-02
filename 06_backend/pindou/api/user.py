"""User login, profile, and consent API routes."""

from __future__ import annotations

import hashlib

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from pindou.api.deps import CurrentUser, DbSession
from pindou.api.security import create_access_token
from pindou.api.request_meta import client_ip
from pindou.services.email_verification import EmailVerificationService
from pindou.services.user_service import UserService

router = APIRouter(prefix="/user", tags=["user"])


class LoginRequest(BaseModel):
    code: str = Field(min_length=1)
    nickname: str | None = None
    avatar: str | None = None


class ConsentRequest(BaseModel):
    type: str = Field(pattern="^(privacy|sensitive)$")


class EmailSendCodeRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)


class EmailVerifyRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    code: str = Field(min_length=6, max_length=6)


@router.post("/login")
def login(payload: LoginRequest, db: DbSession) -> dict:
    """微信 code 登录；Phase 2 本地开发用 code 派生稳定 openid。"""
    openid = "wx_" + hashlib.sha256(payload.code.encode("utf-8")).hexdigest()[:24]
    user = UserService(db).register_or_login(
        openid=openid,
        nickname=payload.nickname,
        avatar=payload.avatar,
    )
    return {"token": create_access_token(subject=user.user_id), "user": user.to_frontend_dict()}


@router.post("/email/send-code")
async def send_email_code(payload: EmailSendCodeRequest, request: Request, db: DbSession) -> dict:
    """H5 邮箱登录/注册第一步：发送 6 位验证码。"""
    return await EmailVerificationService(db).send_code(
        email=payload.email,
        request_ip=client_ip(request),
    )


@router.post("/email/verify")
def verify_email_code(payload: EmailVerifyRequest, db: DbSession) -> dict:
    """H5 邮箱登录/注册第二步：验证通过后返回普通用户 JWT。"""
    email = EmailVerificationService(db).verify_code(email=payload.email, code=payload.code)
    user = UserService(db).register_or_login_email(email=email)
    return {"token": create_access_token(subject=user.user_id), "user": user.to_frontend_dict()}


@router.get("/me")
@router.get("/profile")
def get_profile(current_user: CurrentUser) -> dict:
    """返回前端 User 类型，含额度与 consent 时间。"""
    return current_user.to_frontend_dict()


@router.post("/consent")
def submit_consent(payload: ConsentRequest, current_user: CurrentUser, db: DbSession) -> dict:
    """记录隐私或敏感个人信息处理同意留痕。"""
    consent = UserService(db).record_consent(user_id=current_user.user_id, consent_type=payload.type)
    return {"success": True, "consent_at": consent.consented_at.isoformat()}
