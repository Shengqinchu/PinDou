"""User login, profile, and consent API routes."""

from __future__ import annotations

import hashlib

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from pindou.api.deps import CurrentUser, DbSession
from pindou.api.errors import ApiException
from pindou.api.security import create_access_token
from pindou.api.request_meta import client_ip
from pindou.services.cdk_service import CDKAlreadyRedeemedError, CDKInvalidError, CDKRateLimitError, CDKService
from pindou.services.email_verification import EmailVerificationService, validate_email_or_raise
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


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    code: str = Field(min_length=6, max_length=6)
    password: str = Field(min_length=6, max_length=128)
    cdk: str | None = Field(default=None, max_length=64)


class EmailPasswordLoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=128)


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


@router.post("/register")
def register(payload: RegisterRequest, request: Request, db: DbSession) -> dict:
    """Web 邮箱 + 验证码 + 密码注册，可选 CDK 激活码。"""
    normalized_email = validate_email_or_raise(payload.email)
    user_service = UserService(db)
    existing_user = user_service.get_user_by_email(normalized_email)
    if existing_user is not None and existing_user.password_hash:
        raise ApiException(409, "EMAIL_ALREADY_REGISTERED", "该邮箱已注册，请登录。")

    verified_email = EmailVerificationService(db).verify_code(email=normalized_email, code=payload.code)
    user = user_service.register_or_complete_password_account(email=verified_email, password=payload.password)
    cdk_result = _try_redeem_register_cdk(
        db=db,
        cdk_code=payload.cdk,
        user_id=user.user_id,
        request_ip=client_ip(request),
    )
    db.refresh(user)
    return {
        "token": create_access_token(subject=user.user_id),
        "user": user.to_frontend_dict(),
        "cdk": cdk_result,
    }


@router.post("/email-login")
def email_password_login(payload: EmailPasswordLoginRequest, db: DbSession) -> dict:
    """Web 邮箱 + 密码登录。"""
    normalized_email = validate_email_or_raise(payload.email)
    user_service = UserService(db)
    user = user_service.get_user_by_email(normalized_email)
    if user is None or not user.password_hash:
        raise ApiException(404, "EMAIL_NOT_REGISTERED", "邮箱未注册，请先注册。")
    authed_user = user_service.authenticate_email_password(email=normalized_email, password=payload.password)
    if authed_user is None:
        raise ApiException(401, "PASSWORD_INVALID", "密码不正确，请重新输入。")
    return {"token": create_access_token(subject=authed_user.user_id), "user": authed_user.to_frontend_dict()}


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


def _try_redeem_register_cdk(*, db: DbSession, cdk_code: str | None, user_id: str, request_ip: str | None) -> dict:
    code = (cdk_code or "").strip()
    if not code:
        return {"success": False, "message_cn": "未填写激活码。"}
    try:
        cdk = CDKService(db).redeem(code=code, user_id=user_id, ip=request_ip)
    except CDKRateLimitError as exc:
        return {"success": False, "message_cn": "激活码尝试太频繁，账号已创建，可稍后在个人中心兑换。"}
    except CDKAlreadyRedeemedError as exc:
        return {"success": False, "message_cn": "该激活码已经被兑换过，账号已创建。"}
    except CDKInvalidError as exc:
        return {"success": False, "message_cn": "激活码不正确，账号已创建，可稍后再兑换。"}
    return {
        "success": True,
        "cdk_type": cdk.type,
        "value": cdk.value,
        "message_cn": "激活码已兑换，生成次数已到账。",
    }
