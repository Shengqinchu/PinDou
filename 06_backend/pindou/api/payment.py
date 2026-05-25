"""Payment and customer-service QR API routes."""

from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel

from pindou.api.deps import CurrentUser, DbSession
from pindou.api.errors import ApiException, ErrorCode
from pindou.config import get_settings
from pindou.services.payment_service import (
    InvalidOrderTransitionError,
    ORDER_STATUS_PAID,
    PaymentService,
)

router = APIRouter(prefix="/payment", tags=["payment"])


SKU_AMOUNTS = {
    "single_9.9": 9.9,
    "monthly_28": 28.0,
    "custom_99": 99.0,
}


class CreateOrderRequest(BaseModel):
    sku_id: str | None = None
    sku: str | None = None
    artwork_id: str | None = None


class ConfirmOrderRequest(BaseModel):
    order_no: str | None = None
    order_id: str | None = None
    handler: str | None = None


@router.post("/order")
@router.post("/order/create")
def create_order(payload: CreateOrderRequest, current_user: CurrentUser, db: DbSession) -> dict:
    """创建客服扫码订单并返回前端 Order 类型。"""
    sku = payload.sku_id or payload.sku
    if sku not in SKU_AMOUNTS:
        raise ApiException(422, ErrorCode.VALIDATION_ERROR, "请选择有效的购买档位。")
    order = PaymentService(db).create_order(
        user_id=current_user.user_id,
        sku=sku,
        amount_cny=SKU_AMOUNTS[sku],
        artwork_id=payload.artwork_id,
        qr_code_path=get_settings().customer_service_qr_url,
    )
    return order.to_frontend_dict()


@router.get("/order/{order_ref}")
def get_order_status(order_ref: str, current_user: CurrentUser, db: DbSession) -> dict:
    """按 order_id 或 order_no 查询订单状态。"""
    order = _find_user_order(order_ref, current_user.user_id, db)
    return {"status": order.to_frontend_dict()["status"]}


@router.get("/customer-service")
def get_customer_service_qr(
    current_user: CurrentUser,
    db: DbSession,
    order_id: str = Query(...),
) -> dict:
    """返回客服微信二维码信息。"""
    order = _find_user_order(order_id, current_user.user_id, db)
    settings = get_settings()
    return {
        "qr_url": order.qr_code_path or settings.customer_service_qr_url,
        "wx_id": settings.customer_service_wx_id,
        "order_id": order.order_id,
    }


def confirm_order_for_admin(payload: ConfirmOrderRequest, db: DbSession) -> dict:
    service = PaymentService(db)
    order_ref = payload.order_no or payload.order_id
    if not order_ref:
        raise ApiException(422, ErrorCode.VALIDATION_ERROR, "缺少订单号。")
    order = _find_order(order_ref, db)
    try:
        updated = service.transition_order(
            order_no=order.order_no,
            status=ORDER_STATUS_PAID,
            handler=payload.handler,
        )
    except InvalidOrderTransitionError as exc:
        raise ApiException(409, ErrorCode.INVALID_ORDER_STATUS, "订单状态无法确认支付。") from exc
    return updated.to_frontend_dict()


def _find_user_order(order_ref: str, user_id: str, db: DbSession):
    order = _find_order(order_ref, db)
    if order.user_id != user_id:
        raise ApiException(404, ErrorCode.ORDER_NOT_FOUND, "没有找到这个订单。")
    return order


def _find_order(order_ref: str, db: DbSession):
    from sqlalchemy import select
    from pindou.db.models import Order

    order = db.get(Order, order_ref) or db.scalar(select(Order).where(Order.order_no == order_ref))
    if order is None:
        raise ApiException(404, ErrorCode.ORDER_NOT_FOUND, "没有找到这个订单。")
    return order
