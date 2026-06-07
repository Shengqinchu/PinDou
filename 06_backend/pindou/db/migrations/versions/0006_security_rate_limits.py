"""add security state tables

Revision ID: 0006_security_rate_limits
Revises: 0005_user_password_auth
Create Date: 2026-06-06
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0006_security_rate_limits"
down_revision = "0005_user_password_auth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "generation_jobs",
        sa.Column("ai_credit_reserved", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "generation_jobs",
        sa.Column("ai_credit_refunded", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_table(
        "rate_limit_buckets",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("scope", sa.String(length=64), nullable=False),
        sa.Column("identity", sa.String(length=255), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_seconds", sa.Integer(), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "scope",
            "identity",
            "window_start",
            "window_seconds",
            name="uq_rate_limit_bucket",
        ),
    )
    op.create_index("ix_rate_limit_buckets_scope", "rate_limit_buckets", ["scope"])
    op.create_index("ix_rate_limit_buckets_identity", "rate_limit_buckets", ["identity"])
    op.create_index("ix_rate_limit_buckets_window_start", "rate_limit_buckets", ["window_start"])
    op.create_table(
        "entitlement_grants",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_id", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("entitlement_type", sa.String(length=32), nullable=False),
        sa.Column("value", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.openid"]),
        sa.UniqueConstraint("source_type", "source_id", name="uq_entitlement_grant_source"),
    )
    op.create_index("ix_entitlement_grants_source_type", "entitlement_grants", ["source_type"])
    op.create_index("ix_entitlement_grants_source_id", "entitlement_grants", ["source_id"])
    op.create_index("ix_entitlement_grants_user_id", "entitlement_grants", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_entitlement_grants_user_id", table_name="entitlement_grants")
    op.drop_index("ix_entitlement_grants_source_id", table_name="entitlement_grants")
    op.drop_index("ix_entitlement_grants_source_type", table_name="entitlement_grants")
    op.drop_table("entitlement_grants")
    op.drop_index("ix_rate_limit_buckets_window_start", table_name="rate_limit_buckets")
    op.drop_index("ix_rate_limit_buckets_identity", table_name="rate_limit_buckets")
    op.drop_index("ix_rate_limit_buckets_scope", table_name="rate_limit_buckets")
    op.drop_table("rate_limit_buckets")
    op.drop_column("generation_jobs", "ai_credit_refunded")
    op.drop_column("generation_jobs", "ai_credit_reserved")
