"""Payment and customer-service QR API routes."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import urlparse

import requests
from fastapi import APIRouter, Query, Request
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from pindou.api.deps import CurrentUser, DbSession
from pindou.api.errors import ApiException, ErrorCode
from pindou.config import get_settings
from pindou.db.models import EntitlementGrant, Order, User, as_aware_utc, utc_now
from pindou.services.admin_audit_service import write_audit
from pindou.services.hupijiao_service import HupijiaoError, HupijiaoService, sanitize_payload
from pindou.services.payment_service import (
    InvalidOrderTransitionError,
    ORDER_STATUS_PAID,
    ORDER_STATUS_PAID_HUPIJIAO,
    ORDER_STATUS_PENDING_HUPIJIAO,
    PaymentService,
)

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
    order_no = str(params.get("trade_order_id") or "")
    gateway_status = str(params.get("status") or "")
    request_id = request.headers.get("x-request-id")
    signature_passed = service.verify_webhook(params)
    if not signature_passed:
        write_webhook_audit(
            db=db,
            order=None,
            order_no=order_no or None,
            params=params,
            signature_passed=False,
            amount_matched=None,
            duplicate_callback=False,
            result="signature_failed",
            request_id=request_id,
        )
        return PlainTextResponse("fail", status_code=400)

    if not order_no:
        write_webhook_audit(
            db=db,
            order=None,
            order_no=None,
            params=params,
            signature_passed=True,
            amount_matched=None,
            duplicate_callback=False,
            result="missing_order_no",
            request_id=request_id,
        )
        return PlainTextResponse("fail", status_code=400)
    order = PaymentService(db).get_order(order_no)
    if order is None:
        write_webhook_audit(
            db=db,
            order=None,
            order_no=order_no,
            params=params,
            signature_passed=True,
            amount_matched=None,
            duplicate_callback=False,
            result="order_not_found",
            request_id=request_id,
        )
        return PlainTextResponse("fail", status_code=404)
    amount_matched = amounts_match(order.amount_cny, params.get("total_fee"))
    if not amount_matched:
        write_webhook_audit(
            db=db,
            order=order,
            before_order=order_audit_snapshot(order),
            order_no=order.order_no,
            params=params,
            signature_passed=True,
            amount_matched=False,
            duplicate_callback=False,
            result="amount_mismatch",
            request_id=request_id,
        )
        return PlainTextResponse("fail", status_code=400)

    before_order_snapshot = order_audit_snapshot(order)
    result = "ignored"
    duplicate_callback = order.status != ORDER_STATUS_PENDING_HUPIJIAO
    if gateway_status == "OD" and order.status == ORDER_STATUS_PENDING_HUPIJIAO:
        paid_at = parse_timestamp(params.get("time"))
        paid = PaymentService(db).transition_order(
            order_no=order.order_no,
            status=ORDER_STATUS_PAID_HUPIJIAO,
            paid_at=paid_at,
        )
        grant_order_entitlement(paid, db)
        order = paid
        result = "paid"
        duplicate_callback = False
    elif gateway_status in {"CD", "UD"} and order.status == ORDER_STATUS_PENDING_HUPIJIAO:
        order = PaymentService(db).transition_order(order_no=order.order_no, status="cancelled")
        result = "cancelled"
        duplicate_callback = False

    write_webhook_audit(
        db=db,
        order=order,
        before_order=before_order_snapshot,
        order_no=order.order_no,
        params=params,
        signature_passed=True,
        amount_matched=True,
        duplicate_callback=duplicate_callback,
        result=result,
        request_id=request_id,
    )

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
        return False
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


def write_webhook_audit(
    *,
    db: DbSession,
    order: Order | None,
    order_no: str | None,
    params: dict[str, Any],
    signature_passed: bool,
    amount_matched: bool | None,
    duplicate_callback: bool,
    result: str,
    request_id: str | None,
    before_order: dict[str, Any] | None = None,
) -> int:
    order_snapshot = order_audit_snapshot(order) if order is not None else None
    return write_audit(
        actor_id="hupijiao",
        actor_role="system",
        action="payment.webhook",
        resource_type="order",
        resource_id=order_no,
        before={"order": before_order or order_snapshot} if (before_order or order_snapshot) else None,
        after={
            "result": result,
            "gateway_status": str(params.get("status") or ""),
            "signature_passed": signature_passed,
            "amount_matched": amount_matched,
            "duplicate_callback": duplicate_callback,
            "payload": sanitize_payload(params),
            "order": order_snapshot,
        },
        reason=f"hupijiao webhook {result}",
        request_id=request_id,
        session=db,
    )


def order_audit_snapshot(order: Order) -> dict[str, Any]:
    return {
        "order_id": order.order_id,
        "order_no": order.order_no,
        "user_id": order.user_id,
        "sku": order.sku,
        "amount_cny": str(order.amount_cny),
        "status": order.status,
        "payment_provider": order.payment_provider,
        "paid_at": order.paid_at.isoformat() if order.paid_at else None,
    }


def grant_order_entitlement(order: Order, db: DbSession) -> None:
    item = SKU_CATALOG.get(order.sku)
    if item is None:
        return
    entitlement = str(item["entitlement"])
    value = int(item.get("credits") or item.get("days") or 0)
    if entitlement not in {"credits", "monthly_card"}:
        return

    try:
        db.add(
            EntitlementGrant(
                source_type="order",
                source_id=order.order_no,
                user_id=order.user_id,
                entitlement_type=entitlement,
                value=value,
            )
        )
        if entitlement == "credits":
            updated = db.execute(
                update(User)
                .where(User.openid == order.user_id)
                .values(paid_credits=User.paid_credits + value)
            )
            if updated.rowcount != 1:
                raise ValueError(f"User does not exist: {order.user_id}")
        elif entitlement == "monthly_card":
            user = db.scalar(select(User).where(User.openid == order.user_id))
            if user is None:
                raise ValueError(f"User does not exist: {order.user_id}")
            now = utc_now()
            current_expires = as_aware_utc(user.monthly_card_expires_at)
            base = current_expires if current_expires and current_expires > now else now
            user.monthly_card_expires_at = base + timedelta(days=value)
            db.add(user)
        db.commit()
    except IntegrityError:
        db.rollback()


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
