"""CDK generation and redemption service."""

from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import ClassVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from pindou.db.models import CDK, User, as_aware_utc, utc_now


logger = logging.getLogger(__name__)

SAFE_CDK_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


class CDKServiceError(Exception):
    """Base class for CDK service errors."""


class CDKRateLimitError(CDKServiceError):
    """Raised when a user exceeds PRD §6.5 redemption limits."""


class CDKInvalidError(CDKServiceError):
    """Raised when a CDK does not exist or is unavailable."""


class CDKAlreadyRedeemedError(CDKServiceError):
    """Raised when a one-time CDK has already been redeemed."""


@dataclass(frozen=True)
class RedeemAttempt:
    user_id: str
    ip: str | None
    attempted_at: datetime


class CDKService:
    _attempts: ClassVar[list[RedeemAttempt]] = []

    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def generate_code(length: int = 18) -> str:
        return "".join(secrets.choice(SAFE_CDK_ALPHABET) for _ in range(length))

    def create_cdk(
        self,
        *,
        cdk_type: str,
        value: int,
        code: str | None = None,
        sales_channel: str | None = None,
        batch_id: str | None = None,
        created_by: str = "system",
        expires_at: datetime | None = None,
        notes: str = "",
    ) -> CDK:
        cdk = CDK(
            code=(code or self.generate_code()).upper(),
            type=cdk_type,
            value=value,
            sales_channel=sales_channel,
            batch_id=batch_id,
            created_by=created_by,
            expires_at=expires_at,
            notes=notes,
        )
        self.session.add(cdk)
        self.session.commit()
        self.session.refresh(cdk)
        return cdk

    def redeem(
        self,
        *,
        code: str,
        user_id: str,
        ip: str | None = None,
        now: datetime | None = None,
    ) -> CDK:
        timestamp = as_aware_utc(now) or utc_now()
        self._record_attempt(user_id=user_id, ip=ip, now=timestamp)

        user = self.session.scalar(select(User).where(User.openid == user_id))
        if user is None:
            raise ValueError(f"User does not exist: {user_id}")

        cdk = self.session.get(CDK, code.strip().upper())
        if cdk is None:
            raise CDKInvalidError("CDK does not exist.")
        if cdk.status == "redeemed":
            raise CDKAlreadyRedeemedError("CDK has already been redeemed.")
        if cdk.status != "active":
            raise CDKInvalidError(f"CDK is not active: {cdk.status}")
        cdk_expires_at = as_aware_utc(cdk.expires_at)
        if cdk_expires_at is not None and cdk_expires_at <= timestamp:
            cdk.status = "expired"
            self.session.commit()
            raise CDKInvalidError("CDK has expired.")

        self._apply_entitlement(user=user, cdk=cdk, now=timestamp)
        cdk.status = "redeemed"
        cdk.redeemed_by = user_id
        cdk.redeemed_at = timestamp
        cdk.redemption_ip = ip
        self.session.commit()
        self.session.refresh(cdk)
        return cdk

    def _record_attempt(self, *, user_id: str, ip: str | None, now: datetime) -> None:
        ten_minutes_ago = now - timedelta(minutes=10)
        one_minute_ago = now - timedelta(minutes=1)
        CDKService._attempts = [
            attempt for attempt in CDKService._attempts if attempt.attempted_at >= ten_minutes_ago
        ]
        CDKService._attempts.append(RedeemAttempt(user_id=user_id, ip=ip, attempted_at=now))

        user_recent = [
            attempt
            for attempt in CDKService._attempts
            if attempt.user_id == user_id and attempt.attempted_at >= one_minute_ago
        ]
        if len(user_recent) > 3:
            raise CDKRateLimitError("Same user may redeem at most 3 CDKs per minute.")

        if ip:
            ip_recent = [
                attempt
                for attempt in CDKService._attempts
                if attempt.ip == ip and attempt.attempted_at >= ten_minutes_ago
            ]
            if len(ip_recent) >= 5:
                logger.warning(
                    "Suspicious CDK redemption velocity: ip=%s attempts=%s within 10 minutes.",
                    ip,
                    len(ip_recent),
                )

    @staticmethod
    def _apply_entitlement(*, user: User, cdk: CDK, now: datetime) -> None:
        timestamp = as_aware_utc(now) or utc_now()
        if cdk.type == "monthly_card":
            days = cdk.value if cdk.value > 1 else 30
            current_expiry = as_aware_utc(user.monthly_card_expires_at)
            base = current_expiry if current_expiry and current_expiry > timestamp else timestamp
            user.monthly_card_expires_at = base + timedelta(days=days)
            return

        if cdk.type in {"single_use", "credit_pack_5", "credit_pack_10"}:
            user.paid_credits += max(0, cdk.value)
            return

        raise CDKInvalidError(f"Unsupported CDK type: {cdk.type}")
