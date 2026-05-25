"""API dependencies for DB sessions and authentication."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated

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
    if not payload.get("admin"):
        raise ApiException(403, ErrorCode.ADMIN_REQUIRED, "需要管理员权限。")
    return payload


CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentAdmin = Annotated[dict, Depends(get_current_admin)]
