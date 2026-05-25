"""Minimal admin API routes with separate authentication."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

from pindou.api.deps import CurrentAdmin, DbSession
from pindou.api.errors import ApiException, ErrorCode
from pindou.api.payment import ConfirmOrderRequest, confirm_order_for_admin
from pindou.api.security import admin_credentials_match, create_access_token
from pindou.db.models import CDK, Order, User
from pindou.services.cdk_service import CDKService

router = APIRouter(prefix="/admin", tags=["admin"])


class AdminLoginRequest(BaseModel):
    username: str
    password: str


class BatchGenerateCDKRequest(BaseModel):
    cdk_type: str = Field(pattern="^(single_use|monthly_card|credit_pack_5|credit_pack_10)$")
    value: int = Field(ge=1)
    count: int = Field(default=1, ge=1, le=500)
    sales_channel: str | None = None
    batch_id: str | None = None
    expires_at: str | None = None


class AdjustCreditsRequest(BaseModel):
    free_credits_remaining: int | None = Field(default=None, ge=0)
    paid_credits: int | None = Field(default=None, ge=0)


@router.post("/login")
def admin_login(payload: AdminLoginRequest) -> dict:
    """管理员登录，返回独立 admin JWT。"""
    if not admin_credentials_match(payload.username, payload.password):
        raise ApiException(401, ErrorCode.ADMIN_REQUIRED, "管理员账号或密码不正确。")
    return {"token": create_access_token(subject=payload.username, is_admin=True)}


@router.get("/orders")
def list_orders(
    _: CurrentAdmin,
    db: DbSession,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[dict]:
    """后台订单列表，用于客服确认支付。"""
    orders = list(db.scalars(select(Order).order_by(Order.created_at.desc()).offset(offset).limit(limit)))
    return [order.to_frontend_dict() | {"order_no": order.order_no} for order in orders]


@router.post("/payment/confirm")
def admin_confirm_payment(payload: ConfirmOrderRequest, _: CurrentAdmin, db: DbSession) -> dict:
    """客服后台手动确认订单支付。"""
    return confirm_order_for_admin(payload, db)


@router.post("/cdk/batch_generate")
def batch_generate_cdk(payload: BatchGenerateCDKRequest, _: CurrentAdmin, db: DbSession) -> dict:
    """批量生成 18 位安全字典 CDK。"""
    service = CDKService(db)
    cdks: list[CDK] = []
    expires_at = datetime.fromisoformat(payload.expires_at) if payload.expires_at else None
    for _index in range(payload.count):
        cdks.append(
            service.create_cdk(
                cdk_type=payload.cdk_type,
                value=payload.value,
                sales_channel=payload.sales_channel,
                batch_id=payload.batch_id,
                created_by="admin",
                expires_at=expires_at,
            )
        )
    return {
        "cdks": [
            {"cdk_code": cdk.code, "cdk_type": cdk.type, "value": cdk.value, "status": cdk.status}
            for cdk in cdks
        ]
    }


@router.get("/users")
def list_users(
    _: CurrentAdmin,
    db: DbSession,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[dict]:
    """后台用户列表，含手动调整额度入口所需字段。"""
    users = list(db.scalars(select(User).order_by(User.created_at.desc()).offset(offset).limit(limit)))
    return [user.to_frontend_dict() for user in users]


@router.post("/users/{user_id}/credits")
def adjust_user_credits(
    user_id: str,
    payload: AdjustCreditsRequest,
    _: CurrentAdmin,
    db: DbSession,
) -> dict:
    """后台手动调整用户免费 / 付费额度。"""
    user = db.scalar(select(User).where(User.openid == user_id))
    if user is None:
        raise ApiException(404, ErrorCode.USER_NOT_FOUND, "没有找到这个用户。")
    if payload.free_credits_remaining is not None:
        user.free_credits_remaining = payload.free_credits_remaining
    if payload.paid_credits is not None:
        user.paid_credits = payload.paid_credits
    db.commit()
    db.refresh(user)
    return user.to_frontend_dict()
