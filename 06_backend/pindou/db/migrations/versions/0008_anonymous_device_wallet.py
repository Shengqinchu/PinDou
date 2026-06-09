"""add anonymous device wallet support

Revision ID: 0008_anonymous_device_wallet
Revises: 0007_credit_ledger_membership
Create Date: 2026-06-08
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0008_anonymous_device_wallet"
down_revision = "0007_credit_ledger_membership"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "membership_grants",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("owner_type", sa.String(length=16), nullable=False, server_default="user"),
        sa.Column("owner_id", sa.String(length=128), nullable=False),
        sa.Column("days", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_id", sa.String(length=128), nullable=False),
        sa.Column("idempotency_key", sa.String(length=160), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("idempotency_key", name="uq_membership_grants_idempotency_key"),
    )
    op.create_index("ix_membership_grants_owner_type", "membership_grants", ["owner_type"])
    op.create_index("ix_membership_grants_owner_id", "membership_grants", ["owner_id"])
    op.create_index("ix_membership_grants_source_type", "membership_grants", ["source_type"])
    op.create_index("ix_membership_grants_source_id", "membership_grants", ["source_id"])
    op.create_index("ix_membership_grants_expires_at", "membership_grants", ["expires_at"])
    op.create_index(
        "ix_membership_grants_owner_active",
        "membership_grants",
        ["owner_type", "owner_id", "expires_at"],
    )

    op.add_column("cdks", sa.Column("redeemed_owner_type", sa.String(length=16), nullable=True))
    op.add_column("cdks", sa.Column("redeemed_owner_id", sa.String(length=128), nullable=True))
    op.create_index("ix_cdks_redeemed_owner_type", "cdks", ["redeemed_owner_type"])
    op.create_index("ix_cdks_redeemed_owner_id", "cdks", ["redeemed_owner_id"])
    op.execute(
        """
        UPDATE cdks
        SET redeemed_owner_type = 'user',
            redeemed_owner_id = redeemed_by
        WHERE redeemed_by IS NOT NULL
          AND redeemed_owner_type IS NULL
          AND redeemed_owner_id IS NULL
        """
    )


def downgrade() -> None:
    op.drop_index("ix_cdks_redeemed_owner_id", table_name="cdks")
    op.drop_index("ix_cdks_redeemed_owner_type", table_name="cdks")
    op.drop_column("cdks", "redeemed_owner_id")
    op.drop_column("cdks", "redeemed_owner_type")
    op.drop_index("ix_membership_grants_owner_active", table_name="membership_grants")
    op.drop_index("ix_membership_grants_expires_at", table_name="membership_grants")
    op.drop_index("ix_membership_grants_source_id", table_name="membership_grants")
    op.drop_index("ix_membership_grants_source_type", table_name="membership_grants")
    op.drop_index("ix_membership_grants_owner_id", table_name="membership_grants")
    op.drop_index("ix_membership_grants_owner_type", table_name="membership_grants")
    op.drop_table("membership_grants")
