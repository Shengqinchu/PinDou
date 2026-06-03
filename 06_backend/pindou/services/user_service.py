"""User profile, consent, and quota service."""

from __future__ import annotations

import hashlib
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from pindou.db.models import ConsentLog, DailyQuota, User, utc_now
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
        return {
            "user_id": user.user_id,
            "free_credits_remaining": user.free_credits_remaining,
            "paid_credits": user.paid_credits,
            "monthly_card_expires_at": user.monthly_card_expires_at.isoformat()
            if user.monthly_card_expires_at
            else None,
        }

    def grant_credits(self, *, user_id: str, credits: int) -> User:
        user = self.get_user(user_id)
        if user is None:
            raise ValueError(f"User does not exist: {user_id}")
        user.paid_credits += credits
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
        user.monthly_card_expires_at = base + timedelta(days=days)
        self.session.commit()
        self.session.refresh(user)
        return user


def email_openid(email: str) -> str:
    digest = hashlib.sha256(email.lower().strip().encode("utf-8")).hexdigest()[:24]
    return f"email_{digest}"


def _email_nickname(email: str) -> str:
    local_part = email.split("@", 1)[0].strip()
    return local_part[:32] or "PinDou 用户"
