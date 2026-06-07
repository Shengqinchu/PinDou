"""Point ledger and membership entitlement service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from pindou.api.errors import ApiException, ErrorCode
from pindou.db.models import CreditGrant, CreditTransaction, EntitlementGrant, User, as_aware_utc, utc_now

AI_GENERATION_POINT_COST = 128
REGISTER_GIFT_POINTS = 188
REGISTER_GIFT_DAYS = 7

POINT_SKUS: dict[str, dict[str, Any]] = {
    "points_trial_099": {
        "amount": "0.99",
        "title": "PinDou 体验积分包",
        "points": 200,
        "badge": None,
        "subtitle": "先试一张 AI",
    },
    "points_standard_990": {
        "amount": "9.90",
        "title": "PinDou 标准积分包",
        "points": 1200,
        "badge": "最受欢迎",
        "subtitle": "日常够用，更划算",
    },
    "points_value_2990": {
        "amount": "29.90",
        "title": "PinDou 超值积分包",
        "points": 4000,
        "badge": "单价最低",
        "subtitle": "一次充够，最省",
    },
}

MEMBERSHIP_SKUS: dict[str, dict[str, Any]] = {
    "membership_week_990": {
        "amount": "9.90",
        "title": "PinDou 普通图纸周卡",
        "days": 7,
        "gift_points": 588,
        "badge": None,
        "subtitle": "普通图纸一周无限",
    },
    "membership_month_1990": {
        "amount": "19.90",
        "title": "PinDou 普通图纸月卡",
        "days": 30,
        "gift_points": 1888,
        "badge": "最受欢迎",
        "subtitle": "普通无限 + 1888 积分",
    },
    "membership_season_4990": {
        "amount": "49.90",
        "title": "PinDou 普通图纸季卡",
        "days": 90,
        "gift_points": 6888,
        "badge": "单价最低",
        "subtitle": "长期最省",
    },
}


@dataclass(frozen=True)
class CreditBalance:
    available: int
    reserved: int
    paid: int
    gift: int
    next_expiring_at: datetime | None = None


@dataclass(frozen=True)
class ReservationResult:
    reservation_key: str
    amount: int


def active_membership_expires_at(user: User, *, now: datetime | None = None) -> datetime | None:
    timestamp = as_aware_utc(now) or utc_now()
    expires_at = as_aware_utc(user.membership_expires_at or user.monthly_card_expires_at)
    if expires_at is not None and expires_at > timestamp:
        return expires_at
    return None


def has_active_membership(user: User, *, now: datetime | None = None) -> bool:
    return active_membership_expires_at(user, now=now) is not None


def get_credit_balance(
    session: Session,
    *,
    owner_type: str = "user",
    owner_id: str,
    now: datetime | None = None,
) -> CreditBalance:
    timestamp = as_aware_utc(now) or utc_now()
    grants = list(_active_grants(session, owner_type=owner_type, owner_id=owner_id, now=timestamp))
    def usable_remaining(grant: CreditGrant) -> int:
        expires_at = as_aware_utc(grant.expires_at)
        if expires_at is not None and expires_at <= timestamp:
            return 0
        return max(0, grant.amount_remaining)

    available = sum(usable_remaining(grant) for grant in grants)
    reserved = sum(max(0, grant.amount_reserved) for grant in grants)
    paid = sum(usable_remaining(grant) for grant in grants if grant.kind == "paid")
    gift = sum(usable_remaining(grant) for grant in grants if grant.kind == "gift")
    expiring = [
        as_aware_utc(grant.expires_at)
        for grant in grants
        if grant.kind == "gift" and grant.amount_remaining > 0 and as_aware_utc(grant.expires_at) is not None
    ]
    expiring = [value for value in expiring if value is not None]
    return CreditBalance(
        available=available,
        reserved=reserved,
        paid=paid,
        gift=gift,
        next_expiring_at=min(expiring) if expiring else None,
    )


def grant_points(
    session: Session,
    *,
    owner_type: str = "user",
    owner_id: str,
    amount: int,
    kind: str,
    source_type: str,
    source_id: str,
    idempotency_key: str | None = None,
    expires_at: datetime | None = None,
    now: datetime | None = None,
) -> CreditGrant:
    if amount <= 0:
        raise ValueError("Granted points must be positive.")
    if kind not in {"paid", "gift"}:
        raise ValueError("Credit grant kind must be 'paid' or 'gift'.")

    timestamp = as_aware_utc(now) or utc_now()
    key = idempotency_key or f"{source_type}:{source_id}:points:{owner_type}:{owner_id}"
    existing = session.scalar(select(CreditGrant).where(CreditGrant.idempotency_key == key))
    if existing is not None:
        _sync_user_ai_credit_cache(session, owner_type=owner_type, owner_id=owner_id, now=timestamp)
        return existing

    grant = CreditGrant(
        owner_type=owner_type,
        owner_id=owner_id,
        amount_original=amount,
        amount_remaining=amount,
        amount_reserved=0,
        kind=kind,
        source_type=source_type,
        source_id=source_id,
        idempotency_key=key,
        expires_at=as_aware_utc(expires_at),
        created_at=timestamp,
        updated_at=timestamp,
    )
    session.add(grant)
    session.flush()
    _add_transaction(
        session,
        owner_type=owner_type,
        owner_id=owner_id,
        direction="grant",
        amount=amount,
        source_type=source_type,
        source_id=source_id,
        idempotency_key=f"{key}:grant",
        metadata={"grant_kind": kind, "expires_at": grant.expires_at.isoformat() if grant.expires_at else None},
        now=timestamp,
    )
    _sync_user_ai_credit_cache(session, owner_type=owner_type, owner_id=owner_id, now=timestamp)
    return grant


def grant_registration_gift(session: Session, user: User, *, now: datetime | None = None) -> None:
    timestamp = as_aware_utc(now) or utc_now()
    grant_points(
        session,
        owner_id=user.user_id,
        amount=REGISTER_GIFT_POINTS,
        kind="gift",
        source_type="register_gift",
        source_id=user.user_id,
        idempotency_key=f"register_gift:{user.user_id}:points:v1",
        expires_at=timestamp + timedelta(days=REGISTER_GIFT_DAYS),
        now=timestamp,
    )


def ensure_legacy_paid_credit_grant(session: Session, user: User, *, now: datetime | None = None) -> None:
    if user.paid_credits <= 0:
        return
    existing_grant_id = session.scalar(
        select(CreditGrant.id)
        .where(CreditGrant.owner_type == "user", CreditGrant.owner_id == user.user_id)
        .limit(1)
    )
    if existing_grant_id is not None:
        return
    grant_points(
        session,
        owner_id=user.user_id,
        amount=user.paid_credits * AI_GENERATION_POINT_COST,
        kind="paid",
        source_type="legacy_paid_credits",
        source_id=user.user_id,
        idempotency_key=f"legacy_paid_credits:{user.user_id}:v1",
        now=now,
    )


def reserve_points(
    session: Session,
    *,
    owner_type: str = "user",
    owner_id: str,
    amount: int,
    reservation_key: str,
    source_type: str = "ai_generation",
    source_id: str | None = None,
    now: datetime | None = None,
) -> ReservationResult:
    if amount <= 0:
        raise ValueError("Reserved points must be positive.")
    timestamp = as_aware_utc(now) or utc_now()
    source = source_id or reservation_key
    existing = session.scalar(
        select(CreditTransaction).where(CreditTransaction.idempotency_key == f"{reservation_key}:reserve")
    )
    if existing is not None:
        return ReservationResult(reservation_key=reservation_key, amount=existing.amount)

    remaining = amount
    chunks: list[dict[str, int]] = []
    # A short retry loop handles SQLite's coarse locking and rowcount races in production DBs.
    for attempt in range(3):
        remaining = amount
        chunks.clear()
        grants = list(_spendable_grants(session, owner_type=owner_type, owner_id=owner_id, now=timestamp))
        for grant in grants:
            if remaining <= 0:
                break
            chunk = min(remaining, max(0, grant.amount_remaining))
            if chunk <= 0:
                continue
            updated = session.execute(
                update(CreditGrant)
                .where(CreditGrant.id == grant.id, CreditGrant.amount_remaining >= chunk)
                .values(
                    amount_remaining=CreditGrant.amount_remaining - chunk,
                    amount_reserved=CreditGrant.amount_reserved + chunk,
                    updated_at=timestamp,
                )
            )
            if updated.rowcount != 1:
                session.rollback()
                break
            chunks.append({"grant_id": int(grant.id), "amount": int(chunk)})
            remaining -= chunk
        if remaining <= 0:
            _add_transaction(
                session,
                owner_type=owner_type,
                owner_id=owner_id,
                direction="reserve",
                amount=amount,
                source_type=source_type,
                source_id=source,
                idempotency_key=f"{reservation_key}:reserve",
                metadata={"chunks": chunks},
                now=timestamp,
            )
            _sync_user_ai_credit_cache(session, owner_type=owner_type, owner_id=owner_id, now=timestamp)
            return ReservationResult(reservation_key=reservation_key, amount=amount)
        session.rollback()
        if attempt == 2:
            raise ApiException(429, ErrorCode.QUOTA_EXCEEDED, "AI 积分不足，兑换 CDK 或购买积分后再生成吧。")
    raise ApiException(429, ErrorCode.QUOTA_EXCEEDED, "AI 积分不足，兑换 CDK 或购买积分后再生成吧。")


def commit_reservation(
    session: Session,
    *,
    reservation_key: str,
    now: datetime | None = None,
) -> bool:
    timestamp = as_aware_utc(now) or utc_now()
    reserve_tx = _reservation_transaction(session, reservation_key)
    if reserve_tx is None:
        return False
    if session.scalar(select(CreditTransaction).where(CreditTransaction.idempotency_key == f"{reservation_key}:consume")):
        return False
    if session.scalar(select(CreditTransaction).where(CreditTransaction.idempotency_key == f"{reservation_key}:release")):
        return False
    chunks = _reservation_chunks(reserve_tx)
    for chunk in chunks:
        amount = int(chunk["amount"])
        updated = session.execute(
            update(CreditGrant)
            .where(CreditGrant.id == int(chunk["grant_id"]), CreditGrant.amount_reserved >= amount)
            .values(amount_reserved=CreditGrant.amount_reserved - amount, updated_at=timestamp)
        )
        if updated.rowcount != 1:
            session.rollback()
            return False
    _add_transaction(
        session,
        owner_type=reserve_tx.owner_type,
        owner_id=reserve_tx.owner_id,
        direction="consume",
        amount=reserve_tx.amount,
        source_type=reserve_tx.source_type,
        source_id=reserve_tx.source_id,
        idempotency_key=f"{reservation_key}:consume",
        metadata={"chunks": chunks},
        now=timestamp,
    )
    _sync_user_ai_credit_cache(session, owner_type=reserve_tx.owner_type, owner_id=reserve_tx.owner_id, now=timestamp)
    return True


def release_reservation(
    session: Session,
    *,
    reservation_key: str,
    now: datetime | None = None,
) -> bool:
    timestamp = as_aware_utc(now) or utc_now()
    reserve_tx = _reservation_transaction(session, reservation_key)
    if reserve_tx is None:
        return False
    if session.scalar(select(CreditTransaction).where(CreditTransaction.idempotency_key == f"{reservation_key}:release")):
        return False
    if session.scalar(select(CreditTransaction).where(CreditTransaction.idempotency_key == f"{reservation_key}:consume")):
        return False
    chunks = _reservation_chunks(reserve_tx)
    for chunk in chunks:
        amount = int(chunk["amount"])
        updated = session.execute(
            update(CreditGrant)
            .where(CreditGrant.id == int(chunk["grant_id"]), CreditGrant.amount_reserved >= amount)
            .values(
                amount_remaining=CreditGrant.amount_remaining + amount,
                amount_reserved=CreditGrant.amount_reserved - amount,
                updated_at=timestamp,
            )
        )
        if updated.rowcount != 1:
            session.rollback()
            return False
    _add_transaction(
        session,
        owner_type=reserve_tx.owner_type,
        owner_id=reserve_tx.owner_id,
        direction="release",
        amount=reserve_tx.amount,
        source_type=reserve_tx.source_type,
        source_id=reserve_tx.source_id,
        idempotency_key=f"{reservation_key}:release",
        metadata={"chunks": chunks},
        now=timestamp,
    )
    _sync_user_ai_credit_cache(session, owner_type=reserve_tx.owner_type, owner_id=reserve_tx.owner_id, now=timestamp)
    return True


def extend_membership(
    session: Session,
    *,
    user: User,
    days: int,
    source_type: str,
    source_id: str,
    idempotency_key: str,
    now: datetime | None = None,
) -> datetime:
    if days <= 0:
        raise ValueError("Membership days must be positive.")
    timestamp = as_aware_utc(now) or utc_now()
    existing = session.scalar(select(EntitlementGrant).where(EntitlementGrant.source_type == source_type, EntitlementGrant.source_id == source_id))
    if existing is not None:
        return as_aware_utc(user.membership_expires_at or user.monthly_card_expires_at) or timestamp

    current_expires = as_aware_utc(user.membership_expires_at or user.monthly_card_expires_at)
    base = current_expires if current_expires and current_expires > timestamp else timestamp
    expires_at = base + timedelta(days=days)
    user.membership_expires_at = expires_at
    user.monthly_card_expires_at = expires_at
    session.add(
        EntitlementGrant(
            source_type=source_type,
            source_id=source_id,
            user_id=user.user_id,
            entitlement_type="membership",
            value=days,
            created_at=timestamp,
        )
    )
    session.add(user)
    return expires_at


def migrate_device_credits_to_user(
    session: Session,
    *,
    device_id: str,
    user_id: str,
    idempotency_key: str | None = None,
    now: datetime | None = None,
) -> int:
    timestamp = as_aware_utc(now) or utc_now()
    key = idempotency_key or f"device_migration:{device_id}:{user_id}:v1"
    if session.scalar(select(CreditTransaction).where(CreditTransaction.idempotency_key == key)):
        return 0
    grants = list(session.scalars(select(CreditGrant).where(CreditGrant.owner_type == "device", CreditGrant.owner_id == device_id)))
    moved = 0
    for grant in grants:
        grant.owner_type = "user"
        grant.owner_id = user_id
        grant.updated_at = timestamp
        moved += max(0, grant.amount_remaining) + max(0, grant.amount_reserved)
        session.add(grant)
    _add_transaction(
        session,
        owner_type="user",
        owner_id=user_id,
        direction="transfer_in",
        amount=moved,
        source_type="device_migration",
        source_id=device_id,
        idempotency_key=key,
        metadata={"device_id": device_id, "grant_count": len(grants)},
        now=timestamp,
    )
    _sync_user_ai_credit_cache(session, owner_type="user", owner_id=user_id, now=timestamp)
    return moved


def _active_grants(session: Session, *, owner_type: str, owner_id: str, now: datetime):
    return session.scalars(
        select(CreditGrant).where(
            CreditGrant.owner_type == owner_type,
            CreditGrant.owner_id == owner_id,
            (CreditGrant.amount_remaining > 0) | (CreditGrant.amount_reserved > 0),
            (CreditGrant.amount_reserved > 0) | (CreditGrant.expires_at.is_(None)) | (CreditGrant.expires_at > now),
        )
    )


def _spendable_grants(session: Session, *, owner_type: str, owner_id: str, now: datetime):
    return session.scalars(
        select(CreditGrant)
        .where(
            CreditGrant.owner_type == owner_type,
            CreditGrant.owner_id == owner_id,
            CreditGrant.amount_remaining > 0,
            (CreditGrant.expires_at.is_(None)) | (CreditGrant.expires_at > now),
        )
        .order_by(CreditGrant.expires_at.is_(None), CreditGrant.expires_at.asc(), CreditGrant.created_at.asc(), CreditGrant.id.asc())
    )


def _add_transaction(
    session: Session,
    *,
    owner_type: str,
    owner_id: str,
    direction: str,
    amount: int,
    source_type: str,
    source_id: str,
    idempotency_key: str,
    metadata: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> CreditTransaction:
    existing = session.scalar(select(CreditTransaction).where(CreditTransaction.idempotency_key == idempotency_key))
    if existing is not None:
        return existing
    timestamp = as_aware_utc(now) or utc_now()
    tx = CreditTransaction(
        owner_type=owner_type,
        owner_id=owner_id,
        direction=direction,
        amount=amount,
        balance_after=get_credit_balance(session, owner_type=owner_type, owner_id=owner_id, now=timestamp).available,
        source_type=source_type,
        source_id=source_id,
        idempotency_key=idempotency_key,
        metadata_json=metadata,
        created_at=timestamp,
    )
    session.add(tx)
    return tx


def _sync_user_ai_credit_cache(
    session: Session,
    *,
    owner_type: str,
    owner_id: str,
    now: datetime | None = None,
) -> None:
    if owner_type != "user":
        return
    balance = get_credit_balance(session, owner_type=owner_type, owner_id=owner_id, now=now)
    session.execute(
        update(User)
        .where(User.openid == owner_id)
        .values(paid_credits=balance.available // AI_GENERATION_POINT_COST)
    )


def _reservation_transaction(session: Session, reservation_key: str) -> CreditTransaction | None:
    return session.scalar(
        select(CreditTransaction).where(
            CreditTransaction.idempotency_key == f"{reservation_key}:reserve",
            CreditTransaction.direction == "reserve",
        )
    )


def _reservation_chunks(tx: CreditTransaction) -> list[dict[str, int]]:
    metadata = tx.metadata_json if isinstance(tx.metadata_json, dict) else {}
    chunks = metadata.get("chunks") if isinstance(metadata, dict) else None
    if not isinstance(chunks, list):
        return []
    normalized: list[dict[str, int]] = []
    for chunk in chunks:
        if not isinstance(chunk, dict):
            continue
        try:
            normalized.append({"grant_id": int(chunk["grant_id"]), "amount": int(chunk["amount"])})
        except (KeyError, TypeError, ValueError):
            continue
    return normalized
