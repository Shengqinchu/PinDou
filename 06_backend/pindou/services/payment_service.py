"""Customer-service QR payment state machine."""

from __future__ import annotations

import secrets
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from pindou.db.models import Order, utc_now


ORDER_STATUS_PENDING = "pending_cs_qr"
ORDER_STATUS_PENDING_HUPIJIAO = "pending_qr"
ORDER_STATUS_PAID = "paid_confirmed"
ORDER_STATUS_PAID_HUPIJIAO = "paid_via_hupijiao"
ORDER_STATUS_CANCELLED = "cancelled"
ORDER_STATUS_REFUNDED = "refunded"

ORDER_STATUS_TRANSITIONS = {
    ORDER_STATUS_PENDING: {ORDER_STATUS_PAID, ORDER_STATUS_CANCELLED},
    ORDER_STATUS_PENDING_HUPIJIAO: {ORDER_STATUS_PAID_HUPIJIAO, ORDER_STATUS_CANCELLED},
    ORDER_STATUS_PAID: {ORDER_STATUS_REFUNDED},
    ORDER_STATUS_PAID_HUPIJIAO: {ORDER_STATUS_REFUNDED},
    ORDER_STATUS_CANCELLED: set(),
    ORDER_STATUS_REFUNDED: set(),
}


class InvalidOrderTransitionError(ValueError):
    pass


class PaymentService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_order(
        self,
        *,
        user_id: str,
        sku: str,
        amount_cny: Decimal | float | str,
        artwork_id: str | None = None,
        qr_code_path: str | None = None,
        cdk_code: str | None = None,
        status: str = ORDER_STATUS_PENDING,
        payment_method: str = "wechat_qr_via_cs",
        payment_provider: str = "customer_service",
    ) -> Order:
        order = Order(
            user_id=user_id,
            order_no=generate_order_no(),
            sku=sku,
            amount_cny=Decimal(str(amount_cny)),
            status=status,
            payment_method=payment_method,
            payment_provider=payment_provider,
            qr_code_path=qr_code_path,
            artwork_id=artwork_id,
            cdk_code=cdk_code,
        )
        self.session.add(order)
        self.session.commit()
        self.session.refresh(order)
        return order

    def get_order(self, order_no: str) -> Order | None:
        return self.session.scalar(select(Order).where(Order.order_no == order_no))

    def transition_order(
        self,
        *,
        order_no: str,
        status: str,
        handler: str | None = None,
        paid_at: datetime | None = None,
    ) -> Order:
        order = self.get_order(order_no)
        if order is None:
            raise ValueError(f"Order does not exist: {order_no}")
        allowed = ORDER_STATUS_TRANSITIONS.get(order.status, set())
        if status not in allowed:
            raise InvalidOrderTransitionError(f"Cannot transition order from {order.status} to {status}.")

        order.status = status
        if status in {ORDER_STATUS_PAID, ORDER_STATUS_PAID_HUPIJIAO}:
            order.paid_at = paid_at or utc_now()
            if handler:
                order.customer_service_handler = handler
        self.session.commit()
        self.session.refresh(order)
        return order


def generate_order_no(now: datetime | None = None) -> str:
    timestamp = (now or utc_now()).strftime("%Y%m%d%H%M%S")
    return f"PD{timestamp}{secrets.token_hex(4).upper()}"
