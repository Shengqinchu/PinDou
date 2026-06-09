"""CDK generation and redemption service."""

from __future__ import annotations

import logging
import secrets
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from pindou.db.models import CDK, EntitlementGrant, User, as_aware_utc, utc_now
from pindou.services.credit_service import (
    AI_GENERATION_POINT_COST,
    extend_membership,
    extend_membership_for_owner,
    grant_points,
)
from pindou.services.rate_limit_service import RateLimitExceeded, RateLimitRule, consume_rate_limits


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


class CDKService:
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
        user_id: str | None = None,
        owner_type: str | None = None,
        owner_id: str | None = None,
        ip: str | None = None,
        now: datetime | None = None,
    ) -> CDK:
        timestamp = as_aware_utc(now) or utc_now()
        normalized_owner_type = owner_type or ("user" if user_id else "")
        normalized_owner_id = owner_id or user_id or ""
        if normalized_owner_type not in {"user", "device"} or not normalized_owner_id:
            raise ValueError("CDK redemption requires a user or device owner.")

        actor_key = f"{normalized_owner_type}:{normalized_owner_id}"
        self._record_attempt(actor_key=actor_key, ip=ip, now=timestamp)

        user: User | None = None
        if normalized_owner_type == "user":
            user = self.session.scalar(select(User).where(User.openid == normalized_owner_id))
            if user is None:
                raise ValueError(f"User does not exist: {normalized_owner_id}")

        normalized_code = code.strip().upper()
        cdk = self.session.get(CDK, normalized_code)
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

        updated = self.session.execute(
            update(CDK)
            .where(CDK.code == normalized_code, CDK.status == "active")
            .values(
                status="redeemed",
                redeemed_by=user.user_id if user is not None else None,
                redeemed_owner_type=normalized_owner_type,
                redeemed_owner_id=normalized_owner_id,
                redeemed_at=timestamp,
                redemption_ip=ip,
            )
        )
        if updated.rowcount != 1:
            self.session.rollback()
            current = self.session.get(CDK, normalized_code)
            if current is not None and current.status == "redeemed":
                raise CDKAlreadyRedeemedError("CDK has already been redeemed.")
            raise CDKInvalidError("CDK is not active.")

        try:
            self._apply_entitlement(
                owner_type=normalized_owner_type,
                owner_id=normalized_owner_id,
                user=user,
                cdk=cdk,
                now=timestamp,
            )
            self._record_user_entitlement_grant(user=user, cdk=cdk, now=timestamp)
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise CDKAlreadyRedeemedError("CDK has already been redeemed.") from exc

        redeemed = self.session.get(CDK, normalized_code)
        if redeemed is None:
            raise CDKInvalidError("CDK does not exist.")
        return redeemed

    def _record_attempt(self, *, actor_key: str, ip: str | None, now: datetime) -> None:
        try:
            consume_rate_limits(
                self.session,
                [
                    RateLimitRule("cdk_redeem:actor:minute", actor_key, limit=4, window_seconds=60),
                    RateLimitRule("cdk_redeem:ip:10m", ip, limit=5, window_seconds=10 * 60),
                ],
                now=now,
            )
        except RateLimitExceeded as exc:
            logger.warning("CDK redemption rate limited: actor=%s ip=%s scope=%s", actor_key, ip, exc.scope)
            raise CDKRateLimitError("CDK redemption rate limited.") from exc

    def _apply_entitlement(
        self,
        *,
        owner_type: str,
        owner_id: str,
        user: User | None,
        cdk: CDK,
        now: datetime,
    ) -> None:
        timestamp = as_aware_utc(now) or utc_now()
        if cdk.type in {"membership", "monthly_card"}:
            days = cdk.value if cdk.value > 1 else 30
            if owner_type == "user":
                if user is None:
                    raise ValueError(f"User does not exist: {owner_id}")
                extend_membership(
                    self.session,
                    user=user,
                    days=days,
                    source_type="cdk",
                    source_id=cdk.code,
                    idempotency_key=f"cdk:{cdk.code}:membership",
                    now=timestamp,
                )
            else:
                extend_membership_for_owner(
                    self.session,
                    owner_type=owner_type,
                    owner_id=owner_id,
                    days=days,
                    source_type="cdk",
                    source_id=cdk.code,
                    idempotency_key=f"cdk:{cdk.code}:membership:{owner_type}:{owner_id}",
                    now=timestamp,
                )
            return

        if cdk.type == "points":
            grant_points(
                self.session,
                owner_type=owner_type,
                owner_id=owner_id,
                amount=max(0, cdk.value),
                kind="paid",
                source_type="cdk",
                source_id=cdk.code,
                idempotency_key=f"cdk:{cdk.code}:points:{owner_type}:{owner_id}",
            )
            return

        if cdk.type in {"single_use", "credit_pack_5", "credit_pack_10"}:
            grant_points(
                self.session,
                owner_type=owner_type,
                owner_id=owner_id,
                amount=max(0, cdk.value) * AI_GENERATION_POINT_COST,
                kind="paid",
                source_type="legacy_cdk",
                source_id=cdk.code,
                idempotency_key=f"legacy_cdk:{cdk.code}:points:{owner_type}:{owner_id}",
            )
            return

        raise CDKInvalidError(f"Unsupported CDK type: {cdk.type}")

    def _record_user_entitlement_grant(self, *, user: User | None, cdk: CDK, now: datetime) -> None:
        if user is None:
            return
        if cdk.type in {"membership", "monthly_card"}:
            return
        if self.session.scalar(
            select(EntitlementGrant).where(EntitlementGrant.source_type == "cdk", EntitlementGrant.source_id == cdk.code)
        ):
            return
        self.session.add(
            EntitlementGrant(
                source_type="cdk",
                source_id=cdk.code,
                user_id=user.user_id,
                entitlement_type=cdk.type,
                value=cdk.value,
                created_at=now,
            )
        )
