"""User login, profile, and consent API routes."""

from __future__ import annotations

import hashlib

from fastapi import APIRouter
from pydantic import BaseModel, Field

from pindou.api.deps import CurrentUser, DbSession
from pindou.api.security import create_access_token
from pindou.services.user_service import UserService

router = APIRouter(prefix="/user", tags=["user"])


class LoginRequest(BaseModel):
    code: str = Field(min_length=1)
    nickname: str | None = None
    avatar: str | None = None


class ConsentRequest(BaseModel):
    type: str = Field(pattern="^(privacy|sensitive)$")


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
