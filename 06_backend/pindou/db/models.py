"""SQLAlchemy ORM models for PinDou Phase 2."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy import JSON as SAJSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def as_aware_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def uuid_hex() -> str:
    return uuid.uuid4().hex


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    openid: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    nickname: Mapped[str] = mapped_column(String(128), default="")
    avatar: Mapped[str] = mapped_column(String(512), default="")
    free_credits_remaining: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    paid_credits: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    monthly_card_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    privacy_consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sensitive_consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    artworks: Mapped[list[Artwork]] = relationship(back_populates="user", cascade="all, delete-orphan")
    orders: Mapped[list[Order]] = relationship(back_populates="user", cascade="all, delete-orphan")

    @property
    def user_id(self) -> str:
        return self.openid

    def to_frontend_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "email": self.email,
            "nickname": self.nickname,
            "avatar": self.avatar,
            "created_at": iso_or_none(self.created_at),
            "free_credits_remaining": self.free_credits_remaining,
            "paid_credits": self.paid_credits,
            "monthly_card_expires_at": iso_or_none(self.monthly_card_expires_at),
            "privacy_consent_at": iso_or_none(self.privacy_consent_at),
            "sensitive_consent_at": iso_or_none(self.sensitive_consent_at),
        }


class EmailCode(Base):
    __tablename__ = "email_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    code_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    request_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)


class Artwork(Base):
    __tablename__ = "artworks"

    artwork_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=uuid_hex)
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.openid"), index=True, nullable=False)
    original_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    preview_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    pattern_json: Mapped[dict[str, Any]] = mapped_column(SAJSON, nullable=False)
    style_preset: Mapped[str] = mapped_column(String(64), nullable=False)
    size_preset: Mapped[str] = mapped_column(String(32), nullable=False)
    tier: Mapped[str] = mapped_column(String(32), default="basic", nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_paid_unlocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True, nullable=False)
    original_deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="artworks")

    @property
    def original_image_url(self) -> str | None:
        return self.original_path

    @property
    def original_image_deleted_at(self) -> datetime | None:
        return self.original_deleted_at

    @property
    def preview_url(self) -> str:
        return self.preview_path

    @property
    def pattern_data(self) -> dict[str, Any]:
        return self.pattern_json

    def to_frontend_dict(self) -> dict[str, Any]:
        metadata = self.pattern_data.get("metadata", {}) if isinstance(self.pattern_data, dict) else {}
        return {
            "artwork_id": self.artwork_id,
            "user_id": self.user_id,
            "created_at": iso_or_none(self.created_at),
            "original_image_url": self.original_image_url,
            "original_image_deleted_at": iso_or_none(self.original_image_deleted_at),
            "style_preset": self.style_preset,
            "size_preset": self.size_preset,
            "preview_url": self.preview_url,
            "thumbnail_url": metadata.get("thumbnail_url") or self.preview_url,
            "pattern_data": self.pattern_data,
            "title": self.title,
            "is_paid_unlocked": self.is_paid_unlocked,
        }


class GenerationJob(Base):
    __tablename__ = "generation_jobs"

    job_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=uuid_hex)
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.openid"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True, nullable=False)
    mode: Mapped[str] = mapped_column(String(32), default="ai", nullable=False)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stage: Mapped[str] = mapped_column(String(64), default="queued", nullable=False)
    message_cn: Mapped[str] = mapped_column(String(255), default="已提交，正在排队。", nullable=False)
    result_json: Mapped[dict[str, Any] | None] = mapped_column(SAJSON, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message_cn: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def to_frontend_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "job_id": self.job_id,
            "status": self.status,
            "mode": self.mode,
            "progress": self.progress,
            "stage": self.stage,
            "message_cn": self.message_cn,
            "created_at": iso_or_none(self.created_at),
            "updated_at": iso_or_none(self.updated_at),
            "completed_at": iso_or_none(self.completed_at),
        }
        if self.result_json is not None:
            payload["result"] = self.result_json
        if self.status == "failed":
            payload["error"] = {
                "code": self.error_code or "GENERATION_FAILED",
                "message_cn": self.error_message_cn or self.message_cn,
            }
        return payload


class Order(Base):
    __tablename__ = "orders"

    order_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=uuid_hex)
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.openid"), index=True, nullable=False)
    order_no: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    sku: Mapped[str] = mapped_column(String(64), nullable=False)
    amount_cny: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True, nullable=False)
    payment_method: Mapped[str] = mapped_column(String(64), default="wechat_qr_via_cs", nullable=False)
    payment_provider: Mapped[str] = mapped_column(String(64), default="customer_service", nullable=False)
    qr_code_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    artwork_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("artworks.artwork_id"), nullable=True)
    cdk_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    customer_service_handler: Mapped[str | None] = mapped_column(String(128), nullable=True)

    user: Mapped[User] = relationship(back_populates="orders")

    def to_frontend_dict(self) -> dict[str, Any]:
        frontend_status = {
            "pending_cs_qr": "pending",
            "pending_qr": "pending",
            "paid_confirmed": "paid_confirmed",
            "paid_via_hupijiao": "paid_confirmed",
            "cancelled": "failed",
            "refunded": "failed",
        }.get(self.status, self.status)
        return {
            "order_id": self.order_id,
            "user_id": self.user_id,
            "created_at": iso_or_none(self.created_at),
            "sku": self.sku,
            "amount_cny": float(self.amount_cny),
            "status": frontend_status,
            "payment_method": self.payment_method,
            "payment_provider": self.payment_provider,
            "order_no": self.order_no,
            "qr_code_url": self.qr_code_path,
            "artwork_id": self.artwork_id,
        }


class CDK(Base):
    __tablename__ = "cdks"

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    value: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", index=True, nullable=False)
    redeemed_by: Mapped[str | None] = mapped_column(String(128), ForeignKey("users.openid"), nullable=True)
    redeemed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sales_channel: Mapped[str | None] = mapped_column(String(128), nullable=True)
    batch_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    created_by: Mapped[str] = mapped_column(String(128), default="system", nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    redemption_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)

    @property
    def cdk_code(self) -> str:
        return self.code

    @property
    def cdk_type(self) -> str:
        return self.type


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    actor_role: Mapped[str] = mapped_column(String(32), nullable=False)
    action: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    before_json: Mapped[dict[str, Any] | None] = mapped_column(SAJSON, nullable=True)
    after_json: Mapped[dict[str, Any] | None] = mapped_column(SAJSON, nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True, nullable=False)


class ConsentLog(Base):
    __tablename__ = "consent_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.openid"), index=True, nullable=False)
    consent_type: Mapped[str] = mapped_column(String(32), nullable=False)
    consented_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)


class DailyQuota(Base):
    __tablename__ = "daily_quotas"
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_daily_quota_user_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(128), ForeignKey("users.openid"), index=True, nullable=False)
    date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    script_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    script_ad_continued: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    white_bg_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    white_bg_ad_continued: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


def iso_or_none(value: datetime | None) -> str | None:
    return value.isoformat() if value else None
