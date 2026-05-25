"""User profile, consent, and quota service."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from pindou.db.models import ConsentLog, DailyQuota, User, utc_now


class UserService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_user(self, user_id: str) -> User | None:
        return self.session.scalar(select(User).where(User.openid == user_id))

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
