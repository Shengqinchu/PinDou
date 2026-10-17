"""API dependencies for DB sessions and authentication."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Iterator
from collections.abc import Callable
from typing import Annotated, Any

from fastapi import Cookie, Depends, Header, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from pindou.api.errors import ApiException, ErrorCode
from pindou.api.security import TokenError, decode_access_token
from pindou.db.models import User
from pindou.db.session import get_session
from pindou.services.device_identity import (
    DEVICE_COOKIE_NAME,
    DEVICE_HEADER_NAME,
    DeviceIdentity,
    issue_device_identity,
    parse_device_identity,
    set_device_cookie,
)
from pindou.services.device_migration_service import is_device_claimed


def get_db() -> Iterator[Session]:
    yield from get_session()


DbSession = Annotated[Session, Depends(get_db)]


@dataclass(frozen=True)
class Actor:
    owner_type: str
    owner_id: str
    user: User | None = None
    device: DeviceIdentity | None = None

    @property
    def is_anonymous(self) -> bool:
        return self.user is None


def bearer_token(authorization: str | None = Header(default=None, alias="Authorization")) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise ApiException(401, ErrorCode.AUTH_REQUIRED, "请先登录后再继续。")
    return authorization.removeprefix("Bearer ").strip()


def get_current_user(token: Annotated[str, Depends(bearer_token)], db: DbSession) -> User:
    return get_current_user_from_token(token, db)


def get_current_actor(
    response: Response,
    db: DbSession,
    authorization: str | None = Header(default=None, alias="Authorization"),
    device_header: str | None = Header(default=None, alias=DEVICE_HEADER_NAME),
    device_cookie: str | None = Cookie(default=None, alias=DEVICE_COOKIE_NAME),
) -> Actor:
    if authorization:
        if not authorization.startswith("Bearer "):
            raise ApiException(401, ErrorCode.AUTH_REQUIRED, "登录已过期，请重新登录。")
        token = authorization.removeprefix("Bearer ").strip()
        user = get_current_user_from_token(token, db)
        return Actor(owner_type="user", owner_id=user.user_id, user=user)

    identity = _first_unclaimed_device_identity(db, device_header, device_cookie)
    if identity is None:
        identity = issue_device_identity()
    set_device_cookie(response, identity)
    return Actor(owner_type="device", owner_id=identity.device_id, device=identity)


def get_current_user_from_token(token: str, db: Session) -> User:
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


def _first_unclaimed_device_identity(db: Session, *tokens: str | None) -> DeviceIdentity | None:
    for raw_token in tokens:
        identity = parse_device_identity(raw_token)
        if identity is not None and not is_device_claimed(db, identity.device_id):
            return identity
    return None


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
CurrentActor = Annotated[Actor, Depends(get_current_actor)]
CurrentAdmin = Annotated[dict, Depends(get_current_admin)]
