"""User profile, consent, and quota service."""

from __future__ import annotations

import hashlib
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from pindou.config import get_settings
from pindou.db.models import ConsentLog, DailyQuota, User, utc_now
from pindou.services.credit_service import (
    AI_GENERATION_POINT_COST,
    REGISTER_GIFT_DAYS,
    REGISTER_GIFT_POINTS,
    get_credit_balance,
    ensure_legacy_paid_credit_grant,
    grant_points,
    grant_registration_gift,
)
from pindou.services.password_auth import hash_password, verify_password


class UserService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_user(self, user_id: str) -> User | None:
        return self.session.scalar(select(User).where(User.openid == user_id))

    def get_user_by_email(self, email: str) -> User | None:
        return self.session.scalar(select(User).where(User.email == email.lower().strip()))

    def register_or_login(
        self,
        *,
        openid: str,
        nickname: str | None = None,
        avatar: str | None = None,
    ) -> User:
        user = self.get_user(openid)
        if user is None:
            user = User(openid=openid, nickname=nickname or "", avatar=avatar or "")
            self.session.add(user)
            self.session.flush()
            grant_registration_gift(self.session, user)
        else:
            if nickname is not None:
                user.nickname = nickname
            if avatar is not None:
                user.avatar = avatar
        self.session.commit()
        self.session.refresh(user)
        return user

    def register_or_login_email(self, *, email: str) -> User:
        normalized_email = email.lower().strip()
        openid = email_openid(normalized_email)
        user = self.get_user_by_email(normalized_email) or self.get_user(openid)
        if user is None:
            user = User(
                openid=openid,
                email=normalized_email,
                nickname=_email_nickname(normalized_email),
                avatar="",
            )
            self.session.add(user)
            self.session.flush()
            grant_registration_gift(self.session, user)
        else:
            user.email = normalized_email
            if not user.nickname:
                user.nickname = _email_nickname(normalized_email)
        self.session.commit()
        self.session.refresh(user)
        return user

    def register_or_complete_password_account(self, *, email: str, password: str) -> User:
        normalized_email = email.lower().strip()
        user = self.register_or_login_email(email=normalized_email)
        user.password_hash = hash_password(password)
        self.session.commit()
        self.session.refresh(user)
        return user

    def authenticate_email_password(self, *, email: str, password: str) -> User | None:
        user = self.get_user_by_email(email)
        if user is None or not verify_password(password, user.password_hash):
            return None
        return user

    def record_consent(
        self,
        *,
        user_id: str,
        consent_type: str,
        ip: str | None = None,
        user_agent: str | None = None,
        consented_at: datetime | None = None,
    ) -> ConsentLog:
        user = self.get_user(user_id)
        if user is None:
            raise ValueError(f"User does not exist: {user_id}")

        timestamp = consented_at or utc_now()
        consent = ConsentLog(
            user_id=user_id,
            consent_type=consent_type,
            consented_at=timestamp,
            ip=ip,
            user_agent=user_agent,
        )
        self.session.add(consent)

        if consent_type in {"privacy", "privacy_policy"}:
            user.privacy_consent_at = timestamp
        elif consent_type in {"sensitive", "sensitive_data"}:
            user.sensitive_consent_at = timestamp

        self.session.commit()
        self.session.refresh(consent)
        return consent

    def get_or_create_daily_quota(self, *, user_id: str, quota_date: date | None = None) -> DailyQuota:
        target_date = quota_date or date.today()
        quota = self.session.scalar(
            select(DailyQuota).where(DailyQuota.user_id == user_id, DailyQuota.date == target_date)
        )
        if quota is None:
            quota = DailyQuota(user_id=user_id, date=target_date)
            self.session.add(quota)
            self.session.commit()
            self.session.refresh(quota)
        return quota

    def credit_summary(self, user_id: str) -> dict[str, int | str | None]:
        user = self.get_user(user_id)
        if user is None:
            raise ValueError(f"User does not exist: {user_id}")
        ai_balance = get_credit_balance(self.session, owner_id=user.user_id)
        email = (user.email or "").strip().lower()
        return {
            "user_id": user.user_id,
            "free_credits_remaining": user.free_credits_remaining,
            "normal_trial_remaining": user.free_credits_remaining,
            "paid_credits": user.paid_credits,
            "ai_points_balance": ai_balance.available,
            "ai_points_paid": ai_balance.paid,
            "ai_points_gift": ai_balance.gift,
            "ai_points_reserved": ai_balance.reserved,
            "ai_generation_cost_points": AI_GENERATION_POINT_COST,
            "register_gift_points": REGISTER_GIFT_POINTS,
            "register_gift_days": REGISTER_GIFT_DAYS,
            "is_unlimited_account": bool(email and email in get_settings().unlimited_credit_email_set),
            "membership_expires_at": user.membership_expires_at.isoformat()
            if user.membership_expires_at
            else None,
            "monthly_card_expires_at": user.monthly_card_expires_at.isoformat()
            if user.monthly_card_expires_at
            else None,
        }

    def grant_credits(self, *, user_id: str, credits: int) -> User:
        user = self.get_user(user_id)
        if user is None:
            raise ValueError(f"User does not exist: {user_id}")
        ensure_legacy_paid_credit_grant(self.session, user)
        grant_points(
            self.session,
            owner_id=user.user_id,
            amount=credits * AI_GENERATION_POINT_COST,
            kind="paid",
            source_type="legacy_user_service_grant",
            source_id=f"{user.user_id}:{credits}:{utc_now().timestamp()}",
        )
        self.session.commit()
        self.session.refresh(user)
        return user

    def extend_monthly_card(self, *, user_id: str, days: int = 30, now: datetime | None = None) -> User:
        user = self.get_user(user_id)
        if user is None:
            raise ValueError(f"User does not exist: {user_id}")
        timestamp = now or utc_now()
        current_expires = user.monthly_card_expires_at
        if current_expires and current_expires.tzinfo is None:
            current_expires = current_expires.replace(tzinfo=timestamp.tzinfo)
        base = current_expires if current_expires and current_expires > timestamp else timestamp
        expires_at = base + timedelta(days=days)
        user.monthly_card_expires_at = expires_at
        user.membership_expires_at = expires_at
        self.session.commit()
        self.session.refresh(user)
        return user


def email_openid(email: str) -> str:
    digest = hashlib.sha256(email.lower().strip().encode("utf-8")).hexdigest()[:24]
    return f"email_{digest}"


def _email_nickname(email: str) -> str:
    local_part = email.split("@", 1)[0].strip()
    return local_part[:32] or "PinDou 用户"
