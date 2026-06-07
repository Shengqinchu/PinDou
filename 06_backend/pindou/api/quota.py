"""Quota and consent guards for Phase 2 API endpoints."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from pindou.api.errors import ApiException, ErrorCode
from pindou.config import get_settings
from pindou.db.models import DailyQuota, User, as_aware_utc, utc_now


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


def consume_script_quota(session: Session, user: User) -> None:
    if has_unlimited_credit(user):
        return
    result = session.execute(
        update(User)
        .where(User.openid == user.user_id, User.free_credits_remaining > 0)
        .values(free_credits_remaining=User.free_credits_remaining - 1)
    )
    if result.rowcount != 1:
        session.rollback()
        raise ApiException(429, ErrorCode.QUOTA_EXCEEDED, "普通额度不足，兑换 CDK 或购买额度后再生成吧。")
    session.commit()
    session.refresh(user)


def refund_script_quota(session: Session, user_id: str) -> None:
    session.execute(
        update(User)
        .where(User.openid == user_id)
        .values(free_credits_remaining=User.free_credits_remaining + 1)
    )
    session.commit()


def consume_white_bg_quota(session: Session, user: User) -> None:
    # White-background cleanup is part of a generation now; only normal/AI credits are user-facing.
    return


def consume_ai_credit(session: Session, user: User) -> bool:
    """Reserve one paid AI credit.

    Returns True when a paid credit was decremented and should be refunded if
    the paid AI generation fails. Unlimited and monthly-card users return False.
    """

    if has_unlimited_credit(user):
        return False
    now = utc_now()
    if has_ai_credit(user, now=now):
        monthly_card_expires_at = as_aware_utc(user.monthly_card_expires_at)
        if monthly_card_expires_at is not None and monthly_card_expires_at > now:
            return False
        result = session.execute(
            update(User)
            .where(User.openid == user.user_id, User.paid_credits > 0)
            .values(paid_credits=User.paid_credits - 1)
        )
        if result.rowcount == 1:
            session.commit()
            session.refresh(user)
            return True
        session.rollback()
    raise ApiException(429, ErrorCode.QUOTA_EXCEEDED, "AI 额度不足，兑换 CDK 或购买 AI 额度后再生成吧。")


def refund_ai_credit(session: Session, user_id: str) -> None:
    session.execute(update(User).where(User.openid == user_id).values(paid_credits=User.paid_credits + 1))
    session.commit()


def require_ai_credit_available(user: User) -> None:
    if has_unlimited_credit(user):
        return
    if not has_ai_credit(user):
        raise ApiException(429, ErrorCode.QUOTA_EXCEEDED, "AI 额度不足，兑换 CDK 或购买 AI 额度后再生成吧。")


def has_ai_credit(user: User, *, now=None) -> bool:
    now = as_aware_utc(now) or utc_now()
    monthly_card_expires_at = as_aware_utc(user.monthly_card_expires_at)
    if monthly_card_expires_at is not None and monthly_card_expires_at > now:
        return True
    if user.paid_credits > 0:
        return True
    return False
