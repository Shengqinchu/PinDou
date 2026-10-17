"""Anonymous device wallet and artwork migration to a registered user."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from pindou.db.models import (
    Artwork,
    CDK,
    CreditGrant,
    CreditTransaction,
    DeviceClaim,
    GenerationJob,
    MembershipGrant,
    User,
    as_aware_utc,
    utc_now,
)
from pindou.services.credit_service import AI_GENERATION_POINT_COST, get_credit_balance


@dataclass(frozen=True)
class DeviceMigrationResult:
    status: str
    device_id: str
    user_id: str
    migrated: bool
    moved_points: int = 0
    moved_credit_grants: int = 0
    moved_credit_transactions: int = 0
    moved_memberships: int = 0
    moved_artworks: int = 0
    moved_jobs: int = 0
    moved_cdks: int = 0
    claimed_by_user_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def device_claimed_by(session: Session, device_id: str) -> str | None:
    claim = session.get(DeviceClaim, device_id)
    return claim.claimed_by_user_id if claim is not None else None


def is_device_claimed(session: Session, device_id: str) -> bool:
    return device_claimed_by(session, device_id) is not None


def migrate_device_to_user(
    session: Session,
    *,
    device_id: str,
    user_id: str,
    now: datetime | None = None,
) -> DeviceMigrationResult:
    normalized_device_id = (device_id or "").strip()
    normalized_user_id = (user_id or "").strip()
    if not normalized_device_id or not normalized_user_id:
        return DeviceMigrationResult(
            status="skipped",
            device_id=normalized_device_id,
            user_id=normalized_user_id,
            migrated=False,
        )

    user = session.scalar(select(User).where(User.openid == normalized_user_id))
    if user is None:
        raise ValueError(f"User does not exist: {normalized_user_id}")

    existing_claim = session.get(DeviceClaim, normalized_device_id)
    if existing_claim is not None:
        status = "already_claimed_by_user" if existing_claim.claimed_by_user_id == normalized_user_id else "claimed_by_other"
        return DeviceMigrationResult(
            status=status,
            device_id=normalized_device_id,
            user_id=normalized_user_id,
            migrated=False,
            claimed_by_user_id=existing_claim.claimed_by_user_id,
        )

    timestamp = as_aware_utc(now) or utc_now()
    claim = DeviceClaim(
        device_id=normalized_device_id,
        claimed_by_user_id=normalized_user_id,
        idempotency_key=f"device_migration:{normalized_device_id}:{normalized_user_id}:v1",
        claimed_at=timestamp,
        created_at=timestamp,
    )
    session.add(claim)
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        raced_claim = session.get(DeviceClaim, normalized_device_id)
        claimed_by = raced_claim.claimed_by_user_id if raced_claim is not None else None
        status = "already_claimed_by_user" if claimed_by == normalized_user_id else "claimed_by_other"
        return DeviceMigrationResult(
            status=status,
            device_id=normalized_device_id,
            user_id=normalized_user_id,
            migrated=False,
            claimed_by_user_id=claimed_by,
        )

    moved_points = 0
    moved_credit_grants = 0
    for grant in session.scalars(
        select(CreditGrant).where(CreditGrant.owner_type == "device", CreditGrant.owner_id == normalized_device_id)
    ):
        moved_points += max(0, grant.amount_remaining) + max(0, grant.amount_reserved)
        grant.owner_type = "user"
        grant.owner_id = normalized_user_id
        grant.updated_at = timestamp
        session.add(grant)
        moved_credit_grants += 1

    moved_credit_transactions = _update_owner(
        session,
        CreditTransaction,
        device_id=normalized_device_id,
        user_id=normalized_user_id,
    )

    moved_memberships = 0
    latest_membership: datetime | None = None
    for membership in session.scalars(
        select(MembershipGrant).where(MembershipGrant.owner_type == "device", MembershipGrant.owner_id == normalized_device_id)
    ):
        membership.owner_type = "user"
        membership.owner_id = normalized_user_id
        session.add(membership)
        membership_expires_at = as_aware_utc(membership.expires_at)
        if membership_expires_at is not None and (latest_membership is None or membership_expires_at > latest_membership):
            latest_membership = membership_expires_at
        moved_memberships += 1

    if latest_membership is not None:
        user_membership = as_aware_utc(user.membership_expires_at or user.monthly_card_expires_at)
        if user_membership is None or latest_membership > user_membership:
            user.membership_expires_at = latest_membership
            user.monthly_card_expires_at = latest_membership

    moved_artworks = _move_artworks(session, device_id=normalized_device_id, user_id=normalized_user_id)
    moved_jobs = _move_jobs(session, device_id=normalized_device_id, user_id=normalized_user_id)
    moved_cdks = _move_redeemed_cdks(session, device_id=normalized_device_id, user_id=normalized_user_id)

    balance = get_credit_balance(session, owner_type="user", owner_id=normalized_user_id, now=timestamp)
    user.paid_credits = balance.available // AI_GENERATION_POINT_COST
    session.add(user)

    result = DeviceMigrationResult(
        status="migrated",
        device_id=normalized_device_id,
        user_id=normalized_user_id,
        migrated=True,
        moved_points=moved_points,
        moved_credit_grants=moved_credit_grants,
        moved_credit_transactions=moved_credit_transactions,
        moved_memberships=moved_memberships,
        moved_artworks=moved_artworks,
        moved_jobs=moved_jobs,
        moved_cdks=moved_cdks,
        claimed_by_user_id=normalized_user_id,
    )
    claim.migration_summary_json = result.to_dict()
    session.add(claim)
    session.commit()
    return result


def _update_owner(session: Session, model, *, device_id: str, user_id: str) -> int:
    updated = session.execute(
        update(model)
        .where(model.owner_type == "device", model.owner_id == device_id)
        .values(owner_type="user", owner_id=user_id)
    )
    return int(updated.rowcount or 0)


def _move_artworks(session: Session, *, device_id: str, user_id: str) -> int:
    updated = session.execute(
        update(Artwork)
        .where(Artwork.owner_type == "device", Artwork.owner_id == device_id)
        .values(owner_type="user", owner_id=user_id, user_id=user_id)
    )
    return int(updated.rowcount or 0)


def _move_jobs(session: Session, *, device_id: str, user_id: str) -> int:
    updated = session.execute(
        update(GenerationJob)
        .where(GenerationJob.owner_type == "device", GenerationJob.owner_id == device_id)
        .values(owner_type="user", owner_id=user_id, user_id=user_id)
    )
    return int(updated.rowcount or 0)


def _move_redeemed_cdks(session: Session, *, device_id: str, user_id: str) -> int:
    updated = session.execute(
        update(CDK)
        .where(CDK.redeemed_owner_type == "device", CDK.redeemed_owner_id == device_id)
        .values(redeemed_owner_type="user", redeemed_owner_id=user_id, redeemed_by=user_id)
    )
    return int(updated.rowcount or 0)
