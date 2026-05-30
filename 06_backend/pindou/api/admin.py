"""Admin API routes with role checks and audit visibility."""

from __future__ import annotations

import csv
import io
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select

from pindou.api.deps import DbSession, require_role
from pindou.api.errors import ApiException, ErrorCode
from pindou.api.payment import ConfirmOrderRequest, SKU_CATALOG
from pindou.api.security import admin_credentials_diagnostics, admin_credentials_match, create_access_token
from pindou.config import get_settings
from pindou.db.models import AdminAuditLog, Artwork, CDK, Order, User, iso_or_none, utc_now
from pindou.services.admin_audit_service import write_audit
from pindou.services.cdk_service import CDKService


router = APIRouter(prefix="/admin", tags=["admin"])
logger = logging.getLogger(__name__)

ADMIN_ROLES = ("admin", "operator", "viewer")
AdminReadActor = Annotated[dict[str, Any], Depends(require_role(*ADMIN_ROLES))]
AdminOnlyActor = Annotated[dict[str, Any], Depends(require_role("admin"))]
MANUAL_PAYMENT_CONFIRMED_STATUS = "manual_payment_confirmed"
PAID_STATUSES = {"paid_confirmed", "paid_via_hupijiao"}
ORDER_GRANT_ACTION = "admin.order.grant_entitlement"

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
    delta_free: int | None = None
    delta_paid: int | None = None
    set_monthly_card_days: int | None = Field(default=None, ge=0)
    reason: str = Field(min_length=1, max_length=500)


class ReasonRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class CreateCDKBatchRequest(BaseModel):
    type: str = Field(pattern="^(single_use|monthly_card|credit_pack_5|credit_pack_10)$")
    value: int = Field(ge=1)
    count: int = Field(default=1, ge=1, le=500)
    sales_channel: str | None = None
    expires_at: str | None = None
    notes: str | None = None
    reason: str = Field(min_length=1, max_length=500)


@router.post("/login")
def admin_login(payload: AdminLoginRequest, request: Request, db: DbSession) -> dict:
    """管理员登录，返回带 role=admin 的独立 JWT。"""
    username = payload.username.strip()
    source_ip = client_ip(request)
    if not admin_credentials_match(username, payload.password):
        logger.warning(
            "admin_login_failed source_ip=%s request_id=%s diagnostics=%s",
            source_ip,
            request.headers.get("x-request-id"),
            admin_credentials_diagnostics(username, payload.password),
        )
        raise ApiException(401, ErrorCode.ADMIN_REQUIRED, "管理员账号或密码不正确。")

    audit_id = write_audit(
        actor_id=username,
        actor_role="admin",
        action="admin.login",
        resource_type="admin_session",
        resource_id=username,
        before=None,
        after={"result": "success", "source_ip": source_ip},
        reason="admin login success",
        request_id=request.headers.get("x-request-id"),
        session=db,
    )
    return {
        "token": create_access_token(subject=username, is_admin=True, role="admin"),
        "role": "admin",
        "audit_id": audit_id,
    }


@router.get("/dashboard")
def get_dashboard(_actor: AdminReadActor, db: DbSession) -> dict:
    """后台 Dashboard 只读汇总。"""
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    total_users = int(db.scalar(select(func.count()).select_from(User)) or 0)
    total_orders = int(db.scalar(select(func.count()).select_from(Order)) or 0)
    today_orders = int(db.scalar(select(func.count()).select_from(Order).where(Order.created_at >= today_start)) or 0)
    paid_orders = int(db.scalar(select(func.count()).select_from(Order).where(Order.status.in_(PAID_STATUSES))) or 0)
    failed_orders = int(
        db.scalar(
            select(func.count())
            .select_from(Order)
            .where(Order.status.in_(("cancelled", "refunded", MANUAL_PAYMENT_CONFIRMED_STATUS)))
        )
        or 0
    )
    webhook_anomalies = int(
        db.scalar(
            select(func.count())
            .select_from(AdminAuditLog)
            .where(
                AdminAuditLog.action == "payment.webhook",
                or_(
                    AdminAuditLog.after_json["signature_passed"].as_boolean() == False,  # noqa: E712
                    AdminAuditLog.after_json["amount_matched"].as_boolean() == False,  # noqa: E712
                ),
            )
        )
        or 0
    )
    recent_since = datetime.now(timezone.utc) - timedelta(days=7)
    dangerous_prefixes = (
        "admin.order.confirm_payment_fact",
        "admin.order.grant_entitlement",
        "admin.user.adjust_credits",
        "admin.cdk.batch_generate",
    )
    recent_dangerous_actions = int(
        db.scalar(
            select(func.count())
            .select_from(AdminAuditLog)
            .where(AdminAuditLog.action.in_(dangerous_prefixes), AdminAuditLog.created_at >= recent_since)
        )
        or 0
    )
    success_rate = round(paid_orders / total_orders, 4) if total_orders else 0.0
    return {
        "total_users": total_users,
        "today_orders": today_orders,
        "payment_success_rate": success_rate,
        "abnormal_orders": failed_orders + webhook_anomalies,
        "recent_dangerous_actions": recent_dangerous_actions,
        "links": {
            "abnormal_order_statuses": ["cancelled", "refunded", MANUAL_PAYMENT_CONFIRMED_STATUS],
        },
    }


@router.get("/orders")
def list_orders(
    _actor: AdminReadActor,
    db: DbSession,
    status: str | None = Query(default=None),
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=50, ge=1, le=200),
) -> dict:
    """分页查询订单，支持 status 与 order_no/user_id 搜索。"""
    clauses = []
    if status:
        clauses.append(Order.status == status)
    if search:
        term = f"%{search.strip()}%"
        clauses.append(or_(Order.order_no.ilike(term), Order.user_id.ilike(term)))

    total_stmt = select(func.count()).select_from(Order)
    stmt = select(Order)
    if clauses:
        total_stmt = total_stmt.where(*clauses)
        stmt = stmt.where(*clauses)
    total = int(db.scalar(total_stmt) or 0)
    orders = list(
        db.scalars(
            stmt.order_by(Order.created_at.desc(), Order.order_no.desc()).offset(offset_for(page, size)).limit(size)
        )
    )
    return paged_response([order_payload(order) for order in orders], total, page, size)


@router.get("/orders/{order_no}")
def get_order_detail(order_no: str, _actor: AdminReadActor, db: DbSession) -> dict:
    """订单详情，含虎皮椒 webhook 审计日志摘要。"""
    order = db.scalar(select(Order).where(Order.order_no == order_no))
    if order is None:
        raise ApiException(404, ErrorCode.ORDER_NOT_FOUND, "没有找到这个订单。")
    webhook_logs = order_webhook_logs(db, order.order_no)
    return order_payload(order) | {"webhook": webhook_summary(webhook_logs)}


@router.post("/orders/{order_no}/confirm-payment-fact")
def confirm_payment_fact(
    order_no: str,
    payload: ReasonRequest,
    request: Request,
    actor: AdminOnlyActor,
    db: DbSession,
) -> dict:
    """第一步：仅确认已收到款，不发放权益。"""
    reason = clean_reason(payload.reason)
    order = get_order_by_no(order_no, db)
    before = order_snapshot(order)
    result = "confirmed"
    changed = False

    if order.status == MANUAL_PAYMENT_CONFIRMED_STATUS:
        result = "already_confirmed"
    elif order.status in PAID_STATUSES:
        result = "already_paid"
    elif order.status in {"cancelled", "refunded"}:
        raise ApiException(409, ErrorCode.INVALID_ORDER_STATUS, "已取消或已退款订单不能人工确认收款。")
    else:
        order.status = MANUAL_PAYMENT_CONFIRMED_STATUS
        changed = True

    after = order_snapshot(order)
    audit_id = audit_admin_action(
        db=db,
        actor=actor,
        action="admin.order.confirm_payment_fact",
        resource_type="order",
        resource_id=order.order_no,
        before=before,
        after={"order": after, "result": result, "changed": changed},
        reason=reason,
        request_id=request.headers.get("x-request-id"),
    )
    db.refresh(order)
    return {
        "order": order_payload(order),
        "audit_id": audit_id,
        "changed": changed,
        "message": "收款事实已确认。" if changed else "订单收款事实已确认，无需重复修改。",
    }


@router.post("/orders/{order_no}/grant-entitlement")
def grant_order_entitlement_for_admin(
    order_no: str,
    payload: ReasonRequest,
    request: Request,
    actor: AdminOnlyActor,
    db: DbSession,
) -> dict:
    """第二步：在收款事实确认后发放订单权益。"""
    reason = clean_reason(payload.reason)
    order = get_order_by_no(order_no, db)
    if order.status not in {MANUAL_PAYMENT_CONFIRMED_STATUS, *PAID_STATUSES}:
        raise ApiException(409, ErrorCode.INVALID_ORDER_STATUS, "订单必须先确认收款事实，或已处于已支付状态，才能发放权益。")

    before = {
        "order": order_snapshot(order),
        "entitlement": entitlement_subject_snapshot(order, db),
    }
    if has_entitlement_grant_record(db, order.order_no):
        after = {
            "order": order_snapshot(order),
            "entitlement": entitlement_subject_snapshot(order, db),
            "result": "already_granted",
            "granted": False,
        }
        audit_id = audit_admin_action(
            db=db,
            actor=actor,
            action=ORDER_GRANT_ACTION,
            resource_type="order",
            resource_id=order.order_no,
            before=before,
            after=after,
            reason=reason,
            request_id=request.headers.get("x-request-id"),
        )
        return {
            "order": order_payload(order),
            "entitlement": after["entitlement"],
            "audit_id": audit_id,
            "granted": False,
            "message": "订单权益已发放过，本次未重复发放。",
        }

    entitlement = apply_order_entitlement(order, db)
    order.status = "paid_via_hupijiao" if order.payment_provider == "hupijiao" else "paid_confirmed"
    order.paid_at = order.paid_at or utc_now()
    after = {
        "order": order_snapshot(order),
        "entitlement": entitlement_subject_snapshot(order, db),
        "result": "granted",
        "granted": True,
        "grant": entitlement,
    }
    audit_id = audit_admin_action(
        db=db,
        actor=actor,
        action=ORDER_GRANT_ACTION,
        resource_type="order",
        resource_id=order.order_no,
        before=before,
        after=after,
        reason=reason,
        request_id=request.headers.get("x-request-id"),
    )
    db.refresh(order)
    return {
        "order": order_payload(order),
        "entitlement": after["entitlement"],
        "audit_id": audit_id,
        "granted": True,
        "message": "订单权益已发放。",
    }


@router.get("/cdks/export.csv")
def export_cdks_csv(
    _actor: AdminOnlyActor,
    db: DbSession,
    batch_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
) -> StreamingResponse:
    """导出 CDK CSV。"""
    clauses = []
    if batch_id:
        clauses.append(CDK.batch_id == batch_id)
    if status:
        clauses.append(CDK.status == status)
    stmt = select(CDK)
    if clauses:
        stmt = stmt.where(*clauses)
    cdks = list(db.scalars(stmt.order_by(CDK.created_at.desc(), CDK.code.asc())))

    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["code", "type", "value", "status", "sales_channel", "batch_id", "redeemed_by", "redeemed_at", "created_at"])
    for cdk in cdks:
        writer.writerow(
            [
                cdk.code,
                cdk.type,
                cdk.value,
                cdk.status,
                cdk.sales_channel or "",
                cdk.batch_id or "",
                cdk.redeemed_by or "",
                iso_or_none(cdk.redeemed_at) or "",
                iso_or_none(cdk.created_at) or "",
            ]
        )
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="pindou-cdks.csv"'},
    )


@router.get("/cdks")
def list_cdks(
    _actor: AdminReadActor,
    db: DbSession,
    status: str | None = Query(default=None),
    cdk_type: str | None = Query(default=None, alias="type"),
    batch_id: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=50, ge=1, le=200),
) -> dict:
    """分页查询 CDK。"""
    clauses = []
    if status:
        clauses.append(CDK.status == status)
    if cdk_type:
        clauses.append(CDK.type == cdk_type)
    if batch_id:
        clauses.append(CDK.batch_id == batch_id)

    total_stmt = select(func.count()).select_from(CDK)
    stmt = select(CDK)
    if clauses:
        total_stmt = total_stmt.where(*clauses)
        stmt = stmt.where(*clauses)
    total = int(db.scalar(total_stmt) or 0)
    cdks = list(db.scalars(stmt.order_by(CDK.created_at.desc(), CDK.code.asc()).offset(offset_for(page, size)).limit(size)))
    return paged_response([cdk_payload(cdk) for cdk in cdks], total, page, size)


@router.get("/users")
def list_users(
    _actor: AdminReadActor,
    db: DbSession,
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=50, ge=1, le=200),
) -> dict:
    """分页查询用户，含作品数。"""
    clauses = []
    if search:
        term = f"%{search.strip()}%"
        clauses.append(or_(User.openid.ilike(term), User.nickname.ilike(term)))

    total_stmt = select(func.count()).select_from(User)
    if clauses:
        total_stmt = total_stmt.where(*clauses)
    total = int(db.scalar(total_stmt) or 0)

    artwork_counts = (
        select(Artwork.user_id, func.count(Artwork.artwork_id).label("artwork_count"))
        .group_by(Artwork.user_id)
        .subquery()
    )
    stmt = select(User, func.coalesce(artwork_counts.c.artwork_count, 0)).outerjoin(
        artwork_counts,
        artwork_counts.c.user_id == User.openid,
    )
    if clauses:
        stmt = stmt.where(*clauses)
    rows = db.execute(stmt.order_by(User.created_at.desc(), User.id.desc()).offset(offset_for(page, size)).limit(size))
    return paged_response([user_payload(user, int(artwork_count)) for user, artwork_count in rows], total, page, size)


@router.get("/users/{openid}")
def get_user_detail(openid: str, _actor: AdminReadActor, db: DbSession) -> dict:
    """用户详情，含最近 10 单与作品数。"""
    user = db.scalar(select(User).where(User.openid == openid))
    if user is None:
        raise ApiException(404, ErrorCode.USER_NOT_FOUND, "没有找到这个用户。")
    artwork_count = int(db.scalar(select(func.count()).select_from(Artwork).where(Artwork.user_id == openid)) or 0)
    recent_orders = list(
        db.scalars(
            select(Order)
            .where(Order.user_id == openid)
            .order_by(Order.created_at.desc(), Order.order_no.desc())
            .limit(10)
        )
    )
    return user_payload(user, artwork_count) | {"recent_orders": [order_payload(order) for order in recent_orders]}


@router.get("/artworks")
def list_artworks(
    _actor: AdminReadActor,
    db: DbSession,
    user_id: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=50, ge=1, le=200),
) -> dict:
    """分页查询作品，legacy_preview 标记旧静态路径。"""
    clauses = []
    if user_id:
        clauses.append(Artwork.user_id == user_id)

    total_stmt = select(func.count()).select_from(Artwork)
    stmt = select(Artwork)
    if clauses:
        total_stmt = total_stmt.where(*clauses)
        stmt = stmt.where(*clauses)
    total = int(db.scalar(total_stmt) or 0)
    artworks = list(
        db.scalars(
            stmt.order_by(Artwork.created_at.desc(), Artwork.artwork_id.desc()).offset(offset_for(page, size)).limit(size)
        )
    )
    return paged_response([artwork_payload(artwork) for artwork in artworks], total, page, size)


@router.get("/config")
def get_admin_config(_actor: AdminReadActor) -> dict:
    """只读配置概览；敏感项只返回状态或环境变量引用。"""
    settings = get_settings()
    return {
        "public": {
            "app_env": settings.app_env,
            "app_name": settings.app_name,
            "cors_allow_origins": settings.cors_allow_origins,
            "storage_backend": settings.storage_backend,
            "customer_service_wx_id": settings.customer_service_wx_id,
            "customer_service_qr_url": settings.customer_service_qr_url,
            "hupijiao_callback_url": settings.hupijiao_callback_url,
            "hupijiao_api_base_url": settings.hupijiao_api_base_url,
            "cos": {
                "bucket_configured": bool(settings.cos_bucket),
                "region": settings.cos_region,
                "public_base_url_configured": bool(settings.cos_public_base_url),
            },
            "reverse_proxy_health_url": settings.reverse_proxy_health_url,
            "reverse_proxy_check_interval_seconds": settings.reverse_proxy_check_interval_seconds,
            "expired_original_retention_days": settings.expired_original_retention_days,
        },
        "sensitive": {
            "DATABASE_URL": database_state(settings.database_url),
            "JWT_SECRET": secret_state(settings.jwt_secret, "JWT_SECRET"),
            "ADMIN_PASSWORD_HASH": secret_state(settings.admin_password_hash, "ADMIN_PASSWORD_HASH"),
            "COS_SECRET_ID": secret_state(settings.cos_secret_id, "COS_SECRET_ID"),
            "COS_SECRET_KEY": secret_state(settings.cos_secret_key, "COS_SECRET_KEY"),
            "WECHAT_MP_APPSECRET": secret_state(settings.wechat_mp_appsecret, "WECHAT_MP_APPSECRET"),
            "XIAOCHI_GPT_API_KEY": secret_state(settings.xiaochi_gpt_api_key, "XIAOCHI_GPT_API_KEY"),
            "XIAOCHI_TEXT_API_KEY": secret_state(settings.xiaochi_text_api_key, "XIAOCHI_TEXT_API_KEY"),
            "HUPIJIAO_APP_SECRET": secret_state(settings.hupijiao_app_secret, "HUPIJIAO_APP_SECRET"),
            "HUPIJIAO_WEBHOOK_SECRET": secret_state(settings.hupijiao_webhook_secret, "HUPIJIAO_WEBHOOK_SECRET"),
        },
    }


@router.get("/audit-logs")
def list_audit_logs(
    _actor: AdminReadActor,
    db: DbSession,
    action: str | None = Query(default=None),
    resource_type: str | None = Query(default=None),
    actor_id: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=50, ge=1, le=200),
) -> dict:
    """分页查询后台审计日志。"""
    clauses = []
    if action:
        clauses.append(AdminAuditLog.action == action)
    if resource_type:
        clauses.append(AdminAuditLog.resource_type == resource_type)
    if actor_id:
        clauses.append(AdminAuditLog.actor_id == actor_id)

    total_stmt = select(func.count()).select_from(AdminAuditLog)
    stmt = select(AdminAuditLog)
    if clauses:
        total_stmt = total_stmt.where(*clauses)
        stmt = stmt.where(*clauses)
    total = int(db.scalar(total_stmt) or 0)
    logs = list(
        db.scalars(
            stmt.order_by(AdminAuditLog.created_at.desc(), AdminAuditLog.id.desc())
            .offset(offset_for(page, size))
            .limit(size)
        )
    )
    return paged_response([audit_payload(log) for log in logs], total, page, size)


@router.post("/payment/confirm")
def admin_confirm_payment(_payload: ConfirmOrderRequest, _actor: AdminOnlyActor) -> dict:
    """Legacy one-step payment confirmation is disabled until Batch 2 two-step flow."""
    raise ApiException(403, ErrorCode.INVALID_ORDER_STATUS, "危险支付补发已禁用，请使用 Batch 2 两步补发接口。")


@router.post("/cdk/batch_generate")
def batch_generate_cdk(_payload: BatchGenerateCDKRequest, _actor: AdminOnlyActor) -> dict:
    """Legacy CDK generation is disabled until Batch 2 reason + audit flow."""
    raise ApiException(403, ErrorCode.ADMIN_REQUIRED, "CDK 批量生成需要 reason 和审计，将在 Batch 2 接口开放。")


@router.post("/cdks/batch")
def create_cdk_batch(
    payload: CreateCDKBatchRequest,
    request: Request,
    actor: AdminOnlyActor,
    db: DbSession,
) -> dict:
    """批量生成 CDK，写入审计并返回本批 codes。"""
    reason = clean_reason(payload.reason)
    batch_id = f"cdk_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(4)}"
    expires_at = parse_optional_datetime(payload.expires_at)
    codes: list[str] = []
    for _index in range(payload.count):
        code = generate_unique_cdk_code(db)
        cdk = CDK(
            code=code,
            type=payload.type,
            value=payload.value,
            status="active",
            sales_channel=payload.sales_channel,
            batch_id=batch_id,
            created_by=actor_id(actor),
            expires_at=expires_at,
            notes=payload.notes or "",
        )
        db.add(cdk)
        codes.append(code)

    audit_id = audit_admin_action(
        db=db,
        actor=actor,
        action="admin.cdk.batch_generate",
        resource_type="cdk_batch",
        resource_id=batch_id,
        before=None,
        after={
            "batch_id": batch_id,
            "count": payload.count,
            "type": payload.type,
            "value": payload.value,
            "sales_channel": payload.sales_channel,
            "expires_at": iso_or_none(expires_at),
            "notes": payload.notes or "",
        },
        reason=reason,
        request_id=request.headers.get("x-request-id"),
    )
    return {"codes": codes, "batch_id": batch_id, "audit_id": audit_id}


@router.post("/users/{user_id}/credits")
def adjust_user_credits(
    user_id: str,
    payload: AdjustCreditsRequest,
    request: Request,
    actor: AdminOnlyActor,
    db: DbSession,
) -> dict:
    """调整用户额度或月卡，必须 reason + 审计。"""
    reason = clean_reason(payload.reason)
    if payload.delta_free is None and payload.delta_paid is None and payload.set_monthly_card_days is None:
        raise ApiException(422, ErrorCode.VALIDATION_ERROR, "至少提供一个额度或月卡调整字段。")

    user = db.scalar(select(User).where(User.openid == user_id))
    if user is None:
        raise ApiException(404, ErrorCode.USER_NOT_FOUND, "没有找到这个用户。")
    before = user_credit_snapshot(user)

    if payload.delta_free is not None:
        user.free_credits_remaining += payload.delta_free
    if payload.delta_paid is not None:
        user.paid_credits += payload.delta_paid
    if user.free_credits_remaining < 0 or user.paid_credits < 0:
        raise ApiException(400, ErrorCode.VALIDATION_ERROR, "调整后额度不能为负数。")
    if payload.set_monthly_card_days is not None:
        user.monthly_card_expires_at = (
            None if payload.set_monthly_card_days == 0 else utc_now() + timedelta(days=payload.set_monthly_card_days)
        )

    after = user_credit_snapshot(user)
    audit_id = audit_admin_action(
        db=db,
        actor=actor,
        action="admin.user.adjust_credits",
        resource_type="user",
        resource_id=user.openid,
        before=before,
        after=after,
        reason=reason,
        request_id=request.headers.get("x-request-id"),
    )
    db.refresh(user)
    return {"user": user_credit_snapshot(user), "audit_id": audit_id}


def get_order_by_no(order_no: str, db: DbSession) -> Order:
    order = db.scalar(select(Order).where(Order.order_no == order_no))
    if order is None:
        raise ApiException(404, ErrorCode.ORDER_NOT_FOUND, "没有找到这个订单。")
    return order


def clean_reason(reason: str) -> str:
    normalized = reason.strip()
    if not normalized:
        raise ApiException(422, ErrorCode.VALIDATION_ERROR, "危险操作必须填写 reason。")
    return normalized


def audit_admin_action(
    *,
    db: DbSession,
    actor: dict[str, Any],
    action: str,
    resource_type: str,
    resource_id: str | None,
    before: Any | None,
    after: Any | None,
    reason: str,
    request_id: str | None,
) -> int:
    return write_audit(
        actor_id=actor_id(actor),
        actor_role=actor_role(actor),
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        before=before,
        after=after,
        reason=reason,
        request_id=request_id,
        session=db,
    )


def actor_id(actor: dict[str, Any]) -> str:
    return str(actor.get("sub") or "admin")


def actor_role(actor: dict[str, Any]) -> str:
    return str(actor.get("role") or "admin")


def order_snapshot(order: Order) -> dict[str, Any]:
    return {
        "order_id": order.order_id,
        "order_no": order.order_no,
        "user_id": order.user_id,
        "sku": order.sku,
        "amount_cny": str(order.amount_cny),
        "status": order.status,
        "payment_method": order.payment_method,
        "payment_provider": order.payment_provider,
        "paid_at": iso_or_none(order.paid_at),
        "artwork_id": order.artwork_id,
        "cdk_code": order.cdk_code,
    }


def user_credit_snapshot(user: User) -> dict[str, Any]:
    return {
        "user_id": user.user_id,
        "free_credits_remaining": user.free_credits_remaining,
        "paid_credits": user.paid_credits,
        "monthly_card_expires_at": iso_or_none(user.monthly_card_expires_at),
    }


def entitlement_subject_snapshot(order: Order, db: DbSession) -> dict[str, Any]:
    item = SKU_CATALOG.get(order.sku)
    if item is None:
        return {"type": "unknown", "sku": order.sku}
    entitlement = item["entitlement"]
    if entitlement in {"credits", "monthly_card"}:
        user = db.scalar(select(User).where(User.openid == order.user_id))
        return {"type": entitlement, "user": user_credit_snapshot(user)} if user else {"type": entitlement, "user": None}
    if entitlement == "manual_polish":
        artwork = db.get(Artwork, order.artwork_id) if order.artwork_id else None
        return {
            "type": entitlement,
            "artwork": {
                "artwork_id": artwork.artwork_id,
                "is_paid_unlocked": artwork.is_paid_unlocked,
            }
            if artwork
            else None,
        }
    return {"type": entitlement}


def apply_order_entitlement(order: Order, db: DbSession) -> dict[str, Any]:
    item = SKU_CATALOG.get(order.sku)
    if item is None:
        raise ApiException(422, ErrorCode.VALIDATION_ERROR, "订单 SKU 未配置权益，无法发放。")
    entitlement = item["entitlement"]
    if entitlement == "credits":
        user = db.scalar(select(User).where(User.openid == order.user_id))
        if user is None:
            raise ApiException(404, ErrorCode.USER_NOT_FOUND, "没有找到这个用户。")
        credits = int(item["credits"])
        user.paid_credits += credits
        return {"type": "credits", "credits": credits, "user_id": user.user_id}
    if entitlement == "monthly_card":
        user = db.scalar(select(User).where(User.openid == order.user_id))
        if user is None:
            raise ApiException(404, ErrorCode.USER_NOT_FOUND, "没有找到这个用户。")
        days = int(item["days"])
        now = utc_now()
        current_expires = user.monthly_card_expires_at
        if current_expires and current_expires.tzinfo is None:
            current_expires = current_expires.replace(tzinfo=now.tzinfo)
        base = current_expires if current_expires and current_expires > now else now
        user.monthly_card_expires_at = base + timedelta(days=days)
        return {"type": "monthly_card", "days": days, "user_id": user.user_id}
    if entitlement == "manual_polish":
        if not order.artwork_id:
            raise ApiException(422, ErrorCode.VALIDATION_ERROR, "人工精修订单缺少 artwork_id，无法解锁作品。")
        artwork = db.get(Artwork, order.artwork_id)
        if artwork is None:
            raise ApiException(404, ErrorCode.ARTWORK_NOT_FOUND, "没有找到这个作品。")
        artwork.is_paid_unlocked = True
        return {"type": "manual_polish", "artwork_id": artwork.artwork_id, "is_paid_unlocked": True}
    raise ApiException(422, ErrorCode.VALIDATION_ERROR, "订单权益类型暂不支持。")


def has_entitlement_grant_record(db: DbSession, order_no: str) -> bool:
    audit = db.scalar(
        select(AdminAuditLog.id).where(
            AdminAuditLog.action == ORDER_GRANT_ACTION,
            AdminAuditLog.resource_type == "order",
            AdminAuditLog.resource_id == order_no,
        )
    )
    if audit is not None:
        return True
    webhook_paid = db.scalar(
        select(AdminAuditLog.id).where(
            AdminAuditLog.action == "payment.webhook",
            AdminAuditLog.resource_type == "order",
            AdminAuditLog.resource_id == order_no,
            AdminAuditLog.after_json["result"].as_string() == "paid",
        )
    )
    return webhook_paid is not None


def parse_optional_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise ApiException(422, ErrorCode.VALIDATION_ERROR, "expires_at 必须是 ISO datetime。") from exc


def generate_unique_cdk_code(db: DbSession) -> str:
    while True:
        code = CDKService.generate_code()
        if db.get(CDK, code) is None:
            return code


def order_payload(order: Order) -> dict[str, Any]:
    return order.to_frontend_dict() | {
        "raw_status": order.status,
        "paid_at": iso_or_none(order.paid_at),
        "payment_provider": order.payment_provider,
        "cdk_code": order.cdk_code,
        "customer_service_handler": order.customer_service_handler,
    }


def cdk_payload(cdk: CDK) -> dict[str, Any]:
    return {
        "code": cdk.code,
        "type": cdk.type,
        "value": cdk.value,
        "status": cdk.status,
        "redeemed_by": cdk.redeemed_by,
        "redeemed_at": iso_or_none(cdk.redeemed_at),
        "sales_channel": cdk.sales_channel,
        "batch_id": cdk.batch_id,
        "created_at": iso_or_none(cdk.created_at),
        "created_by": cdk.created_by,
        "expires_at": iso_or_none(cdk.expires_at),
        "redemption_ip": cdk.redemption_ip,
        "notes": cdk.notes,
    }


def user_payload(user: User, artwork_count: int) -> dict[str, Any]:
    return user.to_frontend_dict() | {"artwork_count": artwork_count}


def artwork_payload(artwork: Artwork) -> dict[str, Any]:
    return {
        "artwork_id": artwork.artwork_id,
        "user_id": artwork.user_id,
        "created_at": iso_or_none(artwork.created_at),
        "preview_path": artwork.preview_path,
        "original_path": artwork.original_path,
        "style_preset": artwork.style_preset,
        "size_preset": artwork.size_preset,
        "tier": artwork.tier,
        "title": artwork.title,
        "is_paid_unlocked": artwork.is_paid_unlocked,
        "original_deleted_at": iso_or_none(artwork.original_deleted_at),
        "legacy_preview": artwork.preview_path.startswith("/static/"),
    }


def order_webhook_logs(db: DbSession, order_no: str) -> list[AdminAuditLog]:
    return list(
        db.scalars(
            select(AdminAuditLog)
            .where(
                AdminAuditLog.action == "payment.webhook",
                AdminAuditLog.resource_type == "order",
                AdminAuditLog.resource_id == order_no,
            )
            .order_by(AdminAuditLog.created_at.desc(), AdminAuditLog.id.desc())
            .limit(50)
        )
    )


def webhook_summary(logs: list[AdminAuditLog]) -> dict[str, Any]:
    callback_logs = [audit_payload(log) for log in logs]
    latest = callback_logs[0]["after"] if callback_logs else {}
    return {
        "signature_passed": latest.get("signature_passed"),
        "amount_matched": latest.get("amount_matched"),
        "duplicate_callback": any(bool(item["after"].get("duplicate_callback")) for item in callback_logs),
        "callback_logs": callback_logs,
    }


def audit_payload(log: AdminAuditLog) -> dict[str, Any]:
    return {
        "id": log.id,
        "actor_id": log.actor_id,
        "actor_role": log.actor_role,
        "action": log.action,
        "resource_type": log.resource_type,
        "resource_id": log.resource_id,
        "before": log.before_json,
        "after": log.after_json or {},
        "reason": log.reason,
        "request_id": log.request_id,
        "created_at": iso_or_none(log.created_at),
    }


def paged_response(items: list[dict[str, Any]], total: int, page: int, size: int) -> dict:
    return {"items": items, "total": total, "page": page, "size": size}


def offset_for(page: int, size: int) -> int:
    return (page - 1) * size


def secret_state(secret: Any | None, env_name: str) -> dict[str, Any]:
    value = secret.get_secret_value() if secret else None
    return {"env": env_name, "configured": bool(value)}


def database_state(database_url: str) -> dict[str, Any]:
    parsed = urlsplit(database_url)
    return {
        "env": "DATABASE_URL",
        "configured": bool(database_url),
        "scheme": parsed.scheme or None,
        "password_configured": bool(parsed.password),
        "host_configured": bool(parsed.hostname),
        "database_configured": bool(parsed.path and parsed.path != "/"),
    }


def client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    return request.client.host if request.client else "unknown"
