"""Payment and customer-service QR API routes."""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import urlparse

import requests
from fastapi import APIRouter, Query, Request
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel

from pindou.api.deps import CurrentUser, DbSession
from pindou.api.errors import ApiException, ErrorCode
from pindou.config import get_settings
from pindou.db.models import Order, utc_now
from pindou.services.hupijiao_service import HupijiaoError, HupijiaoService
from pindou.services.payment_service import (
    InvalidOrderTransitionError,
    ORDER_STATUS_PAID,
    ORDER_STATUS_PAID_HUPIJIAO,
    ORDER_STATUS_PENDING_HUPIJIAO,
    PaymentService,
)
from pindou.services.user_service import UserService

router = APIRouter(prefix="/payment", tags=["payment"])
webhook_router = APIRouter(prefix="/webhook", tags=["webhook"])
logger = logging.getLogger(__name__)


DEV_MOCK_WEBHOOK_SECRET = "pindou-dev-hupijiao-mock-secret"

SKU_CATALOG: dict[str, dict[str, Any]] = {
    "single_9.9": {
        "amount": Decimal("9.90"),
        "title": "PinDou 单次高级图纸",
        "entitlement": "credits",
        "credits": 1,
    },
    "monthly_28": {
        "amount": Decimal("28.00"),
        "title": "PinDou 月卡",
        "entitlement": "monthly_card",
        "days": 30,
    },
    "custom_99": {
        "amount": Decimal("99.00"),
        "title": "PinDou 人工精修",
        "entitlement": "manual_polish",
    },
}

SKU_ALIASES = {
    "single_use": "single_9.9",
    "monthly_card": "monthly_28",
    "manual_polish": "custom_99",
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
    """创建虎皮椒支付码订单并返回前端 Order 类型。"""
    sku = normalize_sku(payload.sku_id or payload.sku)
    if sku not in SKU_CATALOG:
        raise ApiException(422, ErrorCode.VALIDATION_ERROR, "请选择有效的购买档位。")
    item = SKU_CATALOG[sku]
    service = PaymentService(db)
    order = service.create_order(
        user_id=current_user.user_id,
        sku=sku,
        amount_cny=item["amount"],
        artwork_id=payload.artwork_id,
        status=ORDER_STATUS_PENDING_HUPIJIAO,
        payment_method="hupijiao_qr",
        payment_provider="hupijiao",
    )
    hupijiao = build_hupijiao_service()
    try:
        payment = hupijiao.create_order(
            amount=item["amount"],
            sku=sku,
            callback_url=get_settings().hupijiao_callback_url,
            order_no=order.order_no,
            title=item["title"],
        )
    except HupijiaoError as exc:
        try:
            service.transition_order(order_no=order.order_no, status="cancelled")
        except InvalidOrderTransitionError:
            pass
        raise ApiException(502, ErrorCode.ORDER_PAID_TIMEOUT, "虎皮椒下单失败，请稍后再试。") from exc

    order.qr_code_path = payment.qr_code_url
    db.commit()
    db.refresh(order)
    frontend_qr_url = payment.qr_code_url if payment.is_mock else f"/payment/order/{order.order_no}/qr.png"
    response = order.to_frontend_dict()
    response.update(
        {
            "order_no": order.order_no,
            "qr_code_url": frontend_qr_url,
            "expires_at": payment.expires_at.isoformat(),
            "payment_provider": "hupijiao",
            "is_mock_payment": payment.is_mock,
        }
    )
    return response


@router.post("/customer-service/order/create")
def create_customer_service_order(payload: CreateOrderRequest, current_user: CurrentUser, db: DbSession) -> dict:
    """创建客服扫码兜底订单。"""
    sku = normalize_sku(payload.sku_id or payload.sku)
    if sku not in SKU_CATALOG:
        raise ApiException(422, ErrorCode.VALIDATION_ERROR, "请选择有效的购买档位。")
    order = PaymentService(db).create_order(
        user_id=current_user.user_id,
        sku=sku,
        amount_cny=SKU_CATALOG[sku]["amount"],
        artwork_id=payload.artwork_id,
        qr_code_path=get_settings().customer_service_qr_url,
    )
    response = order.to_frontend_dict()
    response["payment_provider"] = "customer_service"
    return response


@router.get("/order/{order_ref}/qr.png")
def get_hupijiao_order_qr(order_ref: str, db: DbSession) -> Response:
    """Proxy Hupijiao QR images through our domain so Mini Program devices can load them."""
    order = _find_order(order_ref, db)
    if order.payment_provider != "hupijiao":
        raise ApiException(404, ErrorCode.ORDER_NOT_FOUND, "没有找到这个支付二维码。")

    qr_url = order.qr_code_path or ""
    parsed = urlparse(qr_url)
    if parsed.scheme not in {"http", "https"}:
        raise ApiException(404, ErrorCode.ORDER_NOT_FOUND, "这个订单还没有可用的支付二维码。")

    try:
        upstream = requests.get(qr_url, timeout=15)
        upstream.raise_for_status()
    except requests.RequestException as exc:
        logger.exception(
            "Failed to proxy Hupijiao QR image order_no=%s host=%s",
            order.order_no,
            parsed.netloc,
        )
        raise ApiException(502, ErrorCode.ORDER_PAID_TIMEOUT, "二维码加载失败，请重新打开支付页。") from exc

    media_type = upstream.headers.get("content-type") or "image/png"
    return Response(
        content=upstream.content,
        media_type=media_type,
        headers={"Cache-Control": "no-store"},
    )


@router.get("/order/{order_ref}")
def get_order_status(order_ref: str, current_user: CurrentUser, db: DbSession) -> dict:
    """按 order_id 或 order_no 查询订单状态。"""
    order = _find_user_order(order_ref, current_user.user_id, db)
    refresh_hupijiao_order_if_needed(order, db)
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
        target_status = ORDER_STATUS_PAID_HUPIJIAO if order.payment_provider == "hupijiao" else ORDER_STATUS_PAID
        updated = service.transition_order(
            order_no=order.order_no,
            status=target_status,
            handler=payload.handler,
        )
    except InvalidOrderTransitionError as exc:
        raise ApiException(409, ErrorCode.INVALID_ORDER_STATUS, "订单状态无法确认支付。") from exc
    if updated.payment_provider == "hupijiao":
        grant_order_entitlement(updated, db)
    return updated.to_frontend_dict()


@webhook_router.post("/hupijiao")
async def hupijiao_webhook(request: Request, db: DbSession) -> PlainTextResponse:
    """虎皮椒支付回调：验签后幂等发放权益。"""
    params = await parse_hupijiao_payload(request)
    service = build_hupijiao_service()
    if not service.verify_webhook(params):
        return PlainTextResponse("fail", status_code=400)

    order_no = str(params.get("trade_order_id") or "")
    gateway_status = str(params.get("status") or "")
    if not order_no:
        return PlainTextResponse("fail", status_code=400)
    order = PaymentService(db).get_order(order_no)
    if order is None:
        return PlainTextResponse("fail", status_code=404)
    if not amounts_match(order.amount_cny, params.get("total_fee")):
        return PlainTextResponse("fail", status_code=400)

    if gateway_status == "OD" and order.status == ORDER_STATUS_PENDING_HUPIJIAO:
        paid_at = parse_timestamp(params.get("time"))
        paid = PaymentService(db).transition_order(
            order_no=order.order_no,
            status=ORDER_STATUS_PAID_HUPIJIAO,
            paid_at=paid_at,
        )
        grant_order_entitlement(paid, db)
    elif gateway_status in {"CD", "UD"} and order.status == ORDER_STATUS_PENDING_HUPIJIAO:
        PaymentService(db).transition_order(order_no=order.order_no, status="cancelled")

    return PlainTextResponse("success")


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


def normalize_sku(sku: str | None) -> str:
    if not sku:
        return ""
    return SKU_ALIASES.get(sku, sku)


def build_hupijiao_service() -> HupijiaoService:
    settings = get_settings()
    app_secret = secret_value(settings.hupijiao_app_secret)
    webhook_secret = secret_value(settings.hupijiao_webhook_secret)
    if settings.is_development and not (webhook_secret or app_secret):
        webhook_secret = DEV_MOCK_WEBHOOK_SECRET
    return HupijiaoService(
        app_id=settings.hupijiao_app_id,
        app_secret=app_secret,
        webhook_secret=webhook_secret,
        api_base_url=settings.hupijiao_api_base_url,
        dev_qr_url=settings.customer_service_qr_url,
    )


def secret_value(secret) -> str | None:
    return secret.get_secret_value() if secret else None


async def parse_hupijiao_payload(request: Request) -> dict[str, Any]:
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        payload = await request.json()
    else:
        payload = dict(await request.form())
    return {str(key): value for key, value in payload.items()}


def amounts_match(expected: Decimal, actual: Any) -> bool:
    if actual in {None, ""}:
        return True
    try:
        actual_decimal = Decimal(str(actual)).quantize(Decimal("0.01"))
        expected_decimal = Decimal(expected).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return False
    return actual_decimal == expected_decimal


def parse_timestamp(value: Any) -> datetime | None:
    if value in {None, ""}:
        return None
    try:
        return datetime.fromtimestamp(int(value), tz=utc_now().tzinfo)
    except (TypeError, ValueError, OSError):
        return None


def grant_order_entitlement(order: Order, db: DbSession) -> None:
    item = SKU_CATALOG.get(order.sku)
    if item is None:
        return
    users = UserService(db)
    if item["entitlement"] == "credits":
        users.grant_credits(user_id=order.user_id, credits=int(item["credits"]))
    elif item["entitlement"] == "monthly_card":
        users.extend_monthly_card(user_id=order.user_id, days=int(item["days"]))


def refresh_hupijiao_order_if_needed(order: Order, db: DbSession) -> None:
    if order.payment_provider != "hupijiao" or order.status != ORDER_STATUS_PENDING_HUPIJIAO:
        return
    service = build_hupijiao_service()
    if not service.is_configured:
        return
    try:
        result = service.query_order(order.order_no)
    except HupijiaoError:
        return
    if result.status == "paid":
        paid = PaymentService(db).transition_order(
            order_no=order.order_no,
            status=ORDER_STATUS_PAID_HUPIJIAO,
            paid_at=result.paid_at,
        )
        grant_order_entitlement(paid, db)
    elif result.status == "cancelled":
        PaymentService(db).transition_order(order_no=order.order_no, status="cancelled")
