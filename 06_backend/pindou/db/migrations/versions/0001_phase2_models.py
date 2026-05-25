"""create phase2 core tables

Revision ID: 0001_phase2_models
Revises:
Create Date: 2026-05-25
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0001_phase2_models"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("openid", sa.String(length=128), nullable=False),
        sa.Column("nickname", sa.String(length=128), nullable=False),
        sa.Column("avatar", sa.String(length=512), nullable=False),
        sa.Column("free_credits_remaining", sa.Integer(), nullable=False),
        sa.Column("paid_credits", sa.Integer(), nullable=False),
        sa.Column("monthly_card_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("privacy_consent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sensitive_consent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("openid", name="uq_users_openid"),
    )
    op.create_index("ix_users_openid", "users", ["openid"])

    op.create_table(
        "artworks",
        sa.Column("artwork_id", sa.String(length=64), primary_key=True),
        sa.Column("user_id", sa.String(length=128), sa.ForeignKey("users.openid"), nullable=False),
        sa.Column("original_path", sa.String(length=1024), nullable=True),
        sa.Column("preview_path", sa.String(length=1024), nullable=False),
        sa.Column("pattern_json", sa.JSON(), nullable=False),
        sa.Column("style_preset", sa.String(length=64), nullable=False),
        sa.Column("size_preset", sa.String(length=32), nullable=False),
        sa.Column("tier", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("is_paid_unlocked", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("original_deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_artworks_user_id", "artworks", ["user_id"])
    op.create_index("ix_artworks_created_at", "artworks", ["created_at"])

    op.create_table(
        "orders",
        sa.Column("order_id", sa.String(length=64), primary_key=True),
        sa.Column("user_id", sa.String(length=128), sa.ForeignKey("users.openid"), nullable=False),
        sa.Column("order_no", sa.String(length=64), nullable=False),
        sa.Column("sku", sa.String(length=64), nullable=False),
        sa.Column("amount_cny", sa.Numeric(10, 2), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("payment_method", sa.String(length=64), nullable=False),
        sa.Column("qr_code_path", sa.String(length=1024), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("artwork_id", sa.String(length=64), sa.ForeignKey("artworks.artwork_id"), nullable=True),
        sa.Column("cdk_code", sa.String(length=32), nullable=True),
        sa.Column("customer_service_handler", sa.String(length=128), nullable=True),
        sa.UniqueConstraint("order_no", name="uq_orders_order_no"),
    )
    op.create_index("ix_orders_user_id", "orders", ["user_id"])
    op.create_index("ix_orders_order_no", "orders", ["order_no"])
    op.create_index("ix_orders_status", "orders", ["status"])

    op.create_table(
        "cdks",
        sa.Column("code", sa.String(length=32), primary_key=True),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("redeemed_by", sa.String(length=128), sa.ForeignKey("users.openid"), nullable=True),
        sa.Column("redeemed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sales_channel", sa.String(length=128), nullable=True),
        sa.Column("batch_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("redemption_ip", sa.String(length=64), nullable=True),
        sa.Column("notes", sa.Text(), nullable=False),
    )
    op.create_index("ix_cdks_status", "cdks", ["status"])
    op.create_index("ix_cdks_batch_id", "cdks", ["batch_id"])

    op.create_table(
        "consent_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(length=128), sa.ForeignKey("users.openid"), nullable=False),
        sa.Column("consent_type", sa.String(length=32), nullable=False),
        sa.Column("consented_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ip", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
    )
    op.create_index("ix_consent_logs_user_id", "consent_logs", ["user_id"])

    op.create_table(
        "daily_quotas",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(length=128), sa.ForeignKey("users.openid"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("script_used", sa.Integer(), nullable=False),
        sa.Column("script_ad_continued", sa.Integer(), nullable=False),
        sa.Column("white_bg_used", sa.Integer(), nullable=False),
        sa.Column("white_bg_ad_continued", sa.Integer(), nullable=False),
        sa.UniqueConstraint("user_id", "date", name="uq_daily_quota_user_date"),
    )
    op.create_index("ix_daily_quotas_user_id", "daily_quotas", ["user_id"])
    op.create_index("ix_daily_quotas_date", "daily_quotas", ["date"])


def downgrade() -> None:
    op.drop_index("ix_daily_quotas_date", table_name="daily_quotas")
    op.drop_index("ix_daily_quotas_user_id", table_name="daily_quotas")
    op.drop_table("daily_quotas")
    op.drop_index("ix_consent_logs_user_id", table_name="consent_logs")
    op.drop_table("consent_logs")
    op.drop_index("ix_cdks_batch_id", table_name="cdks")
    op.drop_index("ix_cdks_status", table_name="cdks")
    op.drop_table("cdks")
    op.drop_index("ix_orders_status", table_name="orders")
    op.drop_index("ix_orders_order_no", table_name="orders")
    op.drop_index("ix_orders_user_id", table_name="orders")
    op.drop_table("orders")
    op.drop_index("ix_artworks_created_at", table_name="artworks")
    op.drop_index("ix_artworks_user_id", table_name="artworks")
    op.drop_table("artworks")
    op.drop_index("ix_users_openid", table_name="users")
    op.drop_table("users")
