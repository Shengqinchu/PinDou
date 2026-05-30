"""API dependencies for DB sessions and authentication."""

from __future__ import annotations

from collections.abc import Iterator
from collections.abc import Callable
from typing import Annotated, Any

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.orm import Session

from pindou.api.errors import ApiException, ErrorCode
from pindou.api.security import TokenError, decode_access_token
from pindou.db.models import User
from pindou.db.session import get_session


def get_db() -> Iterator[Session]:
    yield from get_session()


DbSession = Annotated[Session, Depends(get_db)]


def bearer_token(authorization: str | None = Header(default=None, alias="Authorization")) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise ApiException(401, ErrorCode.AUTH_REQUIRED, "请先登录后再继续。")
    return authorization.removeprefix("Bearer ").strip()


def get_current_user(token: Annotated[str, Depends(bearer_token)], db: DbSession) -> User:
    try:
        payload = decode_access_token(token)
    except TokenError as exc:
        raise ApiException(401, ErrorCode.AUTH_REQUIRED, "登录已过期，请重新登录。") from exc

    user_id = str(payload.get("sub") or "")
    user = None
    if user_id:
        user = db.scalar(select(User).where(User.openid == user_id))
    if user is None:
        raise ApiException(401, ErrorCode.AUTH_REQUIRED, "登录用户不存在，请重新登录。")
    return user


def get_current_admin(token: Annotated[str, Depends(bearer_token)]) -> dict:
    try:
        payload = decode_access_token(token)
    except TokenError as exc:
        raise ApiException(401, ErrorCode.AUTH_REQUIRED, "管理员登录已过期，请重新登录。") from exc
    role = _role_from_payload(payload)
    if role != "admin":
        raise ApiException(403, ErrorCode.ADMIN_REQUIRED, "当前角色无权访问，需要角色：admin。")
    payload["role"] = role
    return payload


def require_role(*allowed_roles: str) -> Callable[[str], dict[str, Any]]:
    allowed = set(allowed_roles)

    def dependency(token: Annotated[str, Depends(bearer_token)]) -> dict[str, Any]:
        try:
            payload = decode_access_token(token)
        except TokenError as exc:
            raise ApiException(401, ErrorCode.AUTH_REQUIRED, "管理员登录已过期，请重新登录。") from exc
        role = _role_from_payload(payload)
        if role not in allowed:
            allowed_label = " / ".join(sorted(allowed)) or "未配置"
            raise ApiException(403, ErrorCode.ADMIN_REQUIRED, f"当前角色 {role} 无权访问，需要角色：{allowed_label}。")
        payload["role"] = role
        return payload

    return dependency


def _role_from_payload(payload: dict[str, Any]) -> str:
    role = str(payload.get("role") or "").strip()
    if role:
        return role
    return "admin" if payload.get("admin") else "user"


CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentAdmin = Annotated[dict, Depends(get_current_admin)]
