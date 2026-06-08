"""add credit ledger and membership state

Revision ID: 0007_credit_ledger_membership
Revises: 0006_security_rate_limits
Create Date: 2026-06-07
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0007_credit_ledger_membership"
down_revision = "0006_security_rate_limits"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("membership_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "generation_jobs",
        sa.Column("ai_points_reserved", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("generation_jobs", sa.Column("ai_credit_reservation_key", sa.String(length=128), nullable=True))

    op.create_table(
        "credit_grants",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("owner_type", sa.String(length=16), nullable=False, server_default="user"),
        sa.Column("owner_id", sa.String(length=128), nullable=False),
        sa.Column("amount_original", sa.Integer(), nullable=False),
        sa.Column("amount_remaining", sa.Integer(), nullable=False),
        sa.Column("amount_reserved", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("kind", sa.String(length=16), nullable=False, server_default="paid"),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_id", sa.String(length=128), nullable=False),
        sa.Column("idempotency_key", sa.String(length=160), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("idempotency_key", name="uq_credit_grants_idempotency_key"),
    )
    op.create_index("ix_credit_grants_owner_type", "credit_grants", ["owner_type"])
    op.create_index("ix_credit_grants_owner_id", "credit_grants", ["owner_id"])
    op.create_index("ix_credit_grants_source_type", "credit_grants", ["source_type"])
    op.create_index("ix_credit_grants_source_id", "credit_grants", ["source_id"])
    op.create_index("ix_credit_grants_expires_at", "credit_grants", ["expires_at"])
    op.create_index("ix_credit_grants_owner_active", "credit_grants", ["owner_type", "owner_id", "expires_at"])

    op.create_table(
        "credit_transactions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("owner_type", sa.String(length=16), nullable=False, server_default="user"),
        sa.Column("owner_id", sa.String(length=128), nullable=False),
        sa.Column("direction", sa.String(length=24), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("balance_after", sa.Integer(), nullable=True),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_id", sa.String(length=128), nullable=False),
        sa.Column("idempotency_key", sa.String(length=160), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("idempotency_key", name="uq_credit_transactions_idempotency_key"),
    )
    op.create_index("ix_credit_transactions_owner_type", "credit_transactions", ["owner_type"])
    op.create_index("ix_credit_transactions_owner_id", "credit_transactions", ["owner_id"])
    op.create_index("ix_credit_transactions_source_type", "credit_transactions", ["source_type"])
    op.create_index("ix_credit_transactions_source_id", "credit_transactions", ["source_id"])
    op.create_index("ix_credit_transactions_created_at", "credit_transactions", ["created_at"])

    op.execute("UPDATE users SET membership_expires_at = monthly_card_expires_at WHERE monthly_card_expires_at IS NOT NULL")
    bind = op.get_bind()
    dialect_name = bind.dialect.name
    if dialect_name == "sqlite":
        now_expr = "CURRENT_TIMESTAMP"
        metadata_expr = "json_object('legacy_paid_credits', paid_credits)"
        grant_key_expr = "'legacy_paid_credits:' || openid || ':v1'"
        transaction_key_expr = "'legacy_paid_credits:' || openid || ':v1:grant'"
    elif dialect_name in {"mysql", "mariadb"}:
        now_expr = "CURRENT_TIMESTAMP"
        metadata_expr = "JSON_OBJECT('legacy_paid_credits', paid_credits)"
        grant_key_expr = "CONCAT('legacy_paid_credits:', openid, ':v1')"
        transaction_key_expr = "CONCAT('legacy_paid_credits:', openid, ':v1:grant')"
    else:
        now_expr = "CURRENT_TIMESTAMP"
        metadata_expr = "json_build_object('legacy_paid_credits', paid_credits)"
        grant_key_expr = "'legacy_paid_credits:' || openid || ':v1'"
        transaction_key_expr = "'legacy_paid_credits:' || openid || ':v1:grant'"
    bind.exec_driver_sql(
        f"""
        INSERT INTO credit_grants (
            owner_type, owner_id, amount_original, amount_remaining, amount_reserved,
            kind, source_type, source_id, idempotency_key, expires_at, created_at, updated_at
        )
        SELECT
            'user',
            openid,
            paid_credits * 128,
            paid_credits * 128,
            0,
            'paid',
            'legacy_paid_credits',
            openid,
            {grant_key_expr},
            NULL,
            {now_expr},
            {now_expr}
        FROM users
        WHERE paid_credits > 0
        """
    )
    bind.exec_driver_sql(
        f"""
        INSERT INTO credit_transactions (
            owner_type, owner_id, direction, amount, balance_after,
            source_type, source_id, idempotency_key, metadata_json, created_at
        )
        SELECT
            'user',
            openid,
            'grant',
            paid_credits * 128,
            paid_credits * 128,
            'legacy_paid_credits',
            openid,
            {transaction_key_expr},
            {metadata_expr},
            {now_expr}
        FROM users
        WHERE paid_credits > 0
        """
    )


def downgrade() -> None:
    op.drop_index("ix_credit_transactions_created_at", table_name="credit_transactions")
    op.drop_index("ix_credit_transactions_source_id", table_name="credit_transactions")
    op.drop_index("ix_credit_transactions_source_type", table_name="credit_transactions")
    op.drop_index("ix_credit_transactions_owner_id", table_name="credit_transactions")
    op.drop_index("ix_credit_transactions_owner_type", table_name="credit_transactions")
    op.drop_table("credit_transactions")
    op.drop_index("ix_credit_grants_owner_active", table_name="credit_grants")
    op.drop_index("ix_credit_grants_expires_at", table_name="credit_grants")
    op.drop_index("ix_credit_grants_source_id", table_name="credit_grants")
    op.drop_index("ix_credit_grants_source_type", table_name="credit_grants")
    op.drop_index("ix_credit_grants_owner_id", table_name="credit_grants")
    op.drop_index("ix_credit_grants_owner_type", table_name="credit_grants")
    op.drop_table("credit_grants")
    op.drop_column("generation_jobs", "ai_credit_reservation_key")
    op.drop_column("generation_jobs", "ai_points_reserved")
    op.drop_column("users", "membership_expires_at")
