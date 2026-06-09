"""Unified wallet endpoints for account and anonymous device actors."""

from __future__ import annotations

from fastapi import APIRouter

from pindou.api.deps import CurrentActor, DbSession
from pindou.services.credit_service import (
    AI_GENERATION_POINT_COST,
    REGISTER_GIFT_DAYS,
    REGISTER_GIFT_POINTS,
    active_membership_expires_at_for_owner,
    get_credit_balance,
)
from pindou.services.user_service import UserService

router = APIRouter(prefix="/wallet", tags=["wallet"])


@router.get("/profile")
def get_wallet_profile(actor: CurrentActor, db: DbSession) -> dict:
    """Return the active wallet for the signed-in user or anonymous device."""
    if actor.user is not None:
        payload = UserService(db).credit_summary(actor.user.user_id)
        payload.update(
            {
                "owner_type": "user",
                "owner_id": actor.user.user_id,
                "is_anonymous": False,
                "device_token": None,
                "device_token_expires_at": None,
            }
        )
        return payload

    balance = get_credit_balance(db, owner_type="device", owner_id=actor.owner_id)
    membership_expires_at = active_membership_expires_at_for_owner(
        db,
        owner_type="device",
        owner_id=actor.owner_id,
    )
    return {
        "owner_type": "device",
        "owner_id": actor.owner_id,
        "device_id": actor.owner_id,
        "is_anonymous": True,
        "device_token": actor.device.token if actor.device else None,
        "device_token_expires_at": actor.device.expires_at.isoformat() if actor.device else None,
        "free_credits_remaining": 0,
        "normal_trial_remaining": 0,
        "paid_credits": balance.available // AI_GENERATION_POINT_COST,
        "ai_points_balance": balance.available,
        "ai_points_paid": balance.paid,
        "ai_points_gift": balance.gift,
        "ai_points_reserved": balance.reserved,
        "ai_generation_cost_points": AI_GENERATION_POINT_COST,
        "register_gift_points": REGISTER_GIFT_POINTS,
        "register_gift_days": REGISTER_GIFT_DAYS,
        "is_unlimited_account": False,
        "membership_expires_at": membership_expires_at.isoformat() if membership_expires_at else None,
        "monthly_card_expires_at": membership_expires_at.isoformat() if membership_expires_at else None,
    }
