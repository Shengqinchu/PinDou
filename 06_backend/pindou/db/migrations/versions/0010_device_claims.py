"""add one-time anonymous device claims

Revision ID: 0010_device_claims
Revises: 0009_actor_owned_artworks
Create Date: 2026-06-08
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0010_device_claims"
down_revision = "0009_actor_owned_artworks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "device_claims",
        sa.Column("device_id", sa.String(length=128), primary_key=True),
        sa.Column("claimed_by_user_id", sa.String(length=128), sa.ForeignKey("users.openid"), nullable=False),
        sa.Column("idempotency_key", sa.String(length=160), nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("migration_summary_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("idempotency_key", name="uq_device_claims_idempotency_key"),
    )
    op.create_index("ix_device_claims_claimed_by_user", "device_claims", ["claimed_by_user_id"])


def downgrade() -> None:
    op.drop_index("ix_device_claims_claimed_by_user", table_name="device_claims")
    op.drop_table("device_claims")
