"""add order payment provider

Revision ID: 0002_order_payment_provider
Revises: 0001_phase2_models
Create Date: 2026-05-26
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0002_order_payment_provider"
down_revision = "0001_phase2_models"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column(
            "payment_provider",
            sa.String(length=64),
            nullable=False,
            server_default="customer_service",
        ),
    )


def downgrade() -> None:
    op.drop_column("orders", "payment_provider")
