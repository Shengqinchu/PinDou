"""Quota and consent guards for Phase 2 API endpoints."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from pindou.api.errors import ApiException, ErrorCode
from pindou.db.models import DailyQuota, User, utc_now


SCRIPT_DAILY_FREE_LIMIT = 3
WHITE_BG_DAILY_FREE_LIMIT = 1


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


def consume_script_quota(session: Session, user: User) -> None:
    quota = get_or_create_quota(session, user.user_id)
    if quota.script_used >= SCRIPT_DAILY_FREE_LIMIT + quota.script_ad_continued:
        raise ApiException(429, ErrorCode.QUOTA_EXCEEDED, "今日快速生成次数已用完，可以稍后通过激励视频续次。")
    quota.script_used += 1
    session.commit()


def consume_white_bg_quota(session: Session, user: User) -> None:
    quota = get_or_create_quota(session, user.user_id)
    if quota.white_bg_used >= WHITE_BG_DAILY_FREE_LIMIT + quota.white_bg_ad_continued:
        raise ApiException(429, ErrorCode.QUOTA_EXCEEDED, "今日自动去白底次数已用完。")
    quota.white_bg_used += 1
    session.commit()


def consume_ai_credit(session: Session, user: User) -> None:
    now = utc_now()
    if has_ai_credit(user, now=now):
        if user.monthly_card_expires_at is not None and user.monthly_card_expires_at > now:
            return
        if user.paid_credits > 0:
            user.paid_credits -= 1
            session.commit()
            return
        if user.free_credits_remaining > 0:
            user.free_credits_remaining -= 1
            session.commit()
            return
    raise ApiException(429, ErrorCode.QUOTA_EXCEEDED, "您的 AI 额度不足，去充值或兑换一些额度吧。")


def require_ai_credit_available(user: User) -> None:
    if not has_ai_credit(user):
        raise ApiException(429, ErrorCode.QUOTA_EXCEEDED, "您的 AI 额度不足，去充值或兑换一些额度吧。")


def has_ai_credit(user: User, *, now=None) -> bool:
    now = now or utc_now()
    if user.monthly_card_expires_at is not None and user.monthly_card_expires_at > now:
        return True
    if user.paid_credits > 0:
        return True
    if user.free_credits_remaining > 0:
        return True
    return False
