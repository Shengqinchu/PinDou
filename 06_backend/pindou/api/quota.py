"""Quota and consent guards for Phase 2 API endpoints."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from pindou.api.errors import ApiException, ErrorCode
from pindou.config import get_settings
from pindou.db.models import DailyQuota, User, as_aware_utc
from pindou.services.credit_service import (
    AI_GENERATION_POINT_COST,
    active_membership_expires_at,
    ensure_legacy_paid_credit_grant,
    get_credit_balance,
    release_reservation,
    reserve_points,
)


def require_sensitive_consent(user: User) -> None:
    if user.sensitive_consent_at is None:
        raise ApiException(403, ErrorCode.CONSENT_REQUIRED, "请先同意敏感个人信息处理说明，再上传或处理照片。")


def require_privacy_consent(user: User) -> None:
    if user.privacy_consent_at is None:
        raise ApiException(403, ErrorCode.CONSENT_REQUIRED, "请先同意隐私政策后再继续。")


def get_or_create_quota(session: Session, user_id: str, quota_date: date | None = None) -> DailyQuota:
    target_date = quota_date or date.today()
    quota = session.scalar(
        select(DailyQuota).where(DailyQuota.user_id == user_id, DailyQuota.date == target_date)
    )
    if quota is None:
        quota = DailyQuota(user_id=user_id, date=target_date)
        session.add(quota)
        session.flush()
    return quota


def has_unlimited_credit(user: User) -> bool:
    email = (user.email or "").strip().lower()
    return bool(email and email in get_settings().unlimited_credit_email_set)


def consume_script_quota(session: Session, user: User) -> bool:
    if has_unlimited_credit(user):
        return False
    if active_membership_expires_at(user) is not None:
        return False
    result = session.execute(
        update(User)
        .where(User.openid == user.user_id, User.free_credits_remaining > 0)
        .values(free_credits_remaining=User.free_credits_remaining - 1)
    )
    if result.rowcount != 1:
        session.rollback()
        raise ApiException(429, ErrorCode.QUOTA_EXCEEDED, "普通额度不足，开通时间卡后可不限次生成。")
    session.commit()
    session.refresh(user)
    return True


def refund_script_quota(session: Session, user_id: str, *, consumed: bool = True) -> None:
    if not consumed:
        return
    session.execute(
        update(User)
        .where(User.openid == user_id)
        .values(free_credits_remaining=User.free_credits_remaining + 1)
    )
    session.commit()


def consume_white_bg_quota(session: Session, user: User) -> None:
    # White-background cleanup is part of a generation now; only normal/AI credits are user-facing.
    return


def consume_ai_credit(session: Session, user: User, *, reservation_key: str) -> str | None:
    """Reserve 128 AI points. Time cards never satisfy AI generation cost."""
    if has_unlimited_credit(user):
        return None
    ensure_legacy_paid_credit_grant(session, user)
    reserve_points(
        session,
        owner_id=user.user_id,
        amount=AI_GENERATION_POINT_COST,
        reservation_key=reservation_key,
    )
    session.commit()
    return reservation_key


def refund_ai_credit(session: Session, user_id: str, *, reservation_key: str | None = None) -> None:
    _ = user_id
    if not reservation_key:
        return
    release_reservation(session, reservation_key=reservation_key)
    session.commit()


def require_ai_credit_available(session: Session, user: User) -> None:
    if has_unlimited_credit(user):
        return
    ensure_legacy_paid_credit_grant(session, user)
    if get_credit_balance(session, owner_id=user.user_id).available < AI_GENERATION_POINT_COST:
        raise ApiException(429, ErrorCode.QUOTA_EXCEEDED, "AI 积分不足，兑换 CDK 或购买积分后再生成吧。")


def has_ai_credit(session: Session, user: User, *, now=None) -> bool:
    if has_unlimited_credit(user):
        return True
    ensure_legacy_paid_credit_grant(session, user, now=as_aware_utc(now))
    return get_credit_balance(session, owner_id=user.user_id, now=as_aware_utc(now)).available >= AI_GENERATION_POINT_COST
