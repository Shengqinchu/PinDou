"""Admin API routes with role checks and audit visibility."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated, Any
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select

from pindou.api.deps import DbSession, require_role
from pindou.api.errors import ApiException, ErrorCode
from pindou.api.payment import ConfirmOrderRequest
from pindou.api.security import admin_credentials_match, create_access_token
from pindou.config import get_settings
from pindou.db.models import AdminAuditLog, Artwork, CDK, Order, User, iso_or_none
from pindou.services.admin_audit_service import write_audit


router = APIRouter(prefix="/admin", tags=["admin"])

ADMIN_ROLES = ("admin", "operator", "viewer")
AdminReadActor = Annotated[dict[str, Any], Depends(require_role(*ADMIN_ROLES))]
AdminOnlyActor = Annotated[dict[str, Any], Depends(require_role("admin"))]

LOGIN_FAILURE_WINDOW = timedelta(minutes=10)
LOGIN_FAILURE_LIMIT = 5
_LOGIN_FAILURES: dict[str, list[datetime]] = {}


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
def admin_login(payload: AdminLoginRequest, request: Request, db: DbSession) -> dict:
    """管理员登录，返回带 role=admin 的独立 JWT。"""
    username = payload.username.strip()
    source_ip = client_ip(request)
    now = datetime.now(timezone.utc)
    if login_is_limited(source_ip, username, now):
        raise ApiException(429, "ADMIN_LOGIN_RATE_LIMITED", "管理员登录失败次数过多，请稍后再试。")
    if not admin_credentials_match(username, payload.password):
        record_login_failure(source_ip, username, now)
        raise ApiException(401, ErrorCode.ADMIN_REQUIRED, "管理员账号或密码不正确。")

    clear_login_failures(source_ip, username)
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


@router.post("/payment/confirm")
def admin_confirm_payment(_payload: ConfirmOrderRequest, _actor: AdminOnlyActor) -> dict:
    """Legacy one-step payment confirmation is disabled until Batch 2 two-step flow."""
    raise ApiException(403, ErrorCode.INVALID_ORDER_STATUS, "危险支付补发已禁用，请使用 Batch 2 两步补发接口。")


@router.post("/cdk/batch_generate")
def batch_generate_cdk(_payload: BatchGenerateCDKRequest, _actor: AdminOnlyActor) -> dict:
    """Legacy CDK generation is disabled until Batch 2 reason + audit flow."""
    raise ApiException(403, ErrorCode.ADMIN_REQUIRED, "CDK 批量生成需要 reason 和审计，将在 Batch 2 接口开放。")


@router.post("/users/{user_id}/credits")
def adjust_user_credits(_user_id: str, _payload: AdjustCreditsRequest, _actor: AdminOnlyActor) -> dict:
    """Legacy credit adjustment is disabled until Batch 2 reason + audit flow."""
    raise ApiException(403, ErrorCode.ADMIN_REQUIRED, "额度调整需要 reason 和审计，将在 Batch 2 接口开放。")


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


def login_keys(source_ip: str, username: str) -> tuple[str, str]:
    normalized_username = username.strip().lower() or "unknown"
    return f"ip:{source_ip}", f"account:{normalized_username}"


def login_is_limited(source_ip: str, username: str, now: datetime) -> bool:
    return any(len(pruned_login_failures(key, now)) >= LOGIN_FAILURE_LIMIT for key in login_keys(source_ip, username))


def record_login_failure(source_ip: str, username: str, now: datetime) -> None:
    for key in login_keys(source_ip, username):
        failures = pruned_login_failures(key, now)
        failures.append(now)
        _LOGIN_FAILURES[key] = failures


def clear_login_failures(source_ip: str, username: str) -> None:
    for key in login_keys(source_ip, username):
        _LOGIN_FAILURES.pop(key, None)


def pruned_login_failures(key: str, now: datetime) -> list[datetime]:
    cutoff = now - LOGIN_FAILURE_WINDOW
    failures = [value for value in _LOGIN_FAILURES.get(key, []) if value >= cutoff]
    _LOGIN_FAILURES[key] = failures
    return failures
