"""add actor ownership to artworks and generation jobs

Revision ID: 0009_actor_owned_artworks
Revises: 0008_anonymous_device_wallet
Create Date: 2026-06-08
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0009_actor_owned_artworks"
down_revision = "0008_anonymous_device_wallet"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("artworks") as batch_op:
        batch_op.alter_column("user_id", existing_type=sa.String(length=128), nullable=True)
        batch_op.add_column(sa.Column("owner_type", sa.String(length=16), nullable=False, server_default="user"))
        batch_op.add_column(sa.Column("owner_id", sa.String(length=128), nullable=True))
    op.execute(
        """
        UPDATE artworks
        SET owner_type = 'user',
            owner_id = user_id
        WHERE owner_id IS NULL
          AND user_id IS NOT NULL
        """
    )
    op.create_index("ix_artworks_owner_type", "artworks", ["owner_type"])
    op.create_index("ix_artworks_owner_id", "artworks", ["owner_id"])
    op.create_index("ix_artworks_owner_created", "artworks", ["owner_type", "owner_id", "created_at"])

    with op.batch_alter_table("generation_jobs") as batch_op:
        batch_op.alter_column("user_id", existing_type=sa.String(length=128), nullable=True)
        batch_op.add_column(sa.Column("owner_type", sa.String(length=16), nullable=False, server_default="user"))
        batch_op.add_column(sa.Column("owner_id", sa.String(length=128), nullable=True))
    op.execute(
        """
        UPDATE generation_jobs
        SET owner_type = 'user',
            owner_id = user_id
        WHERE owner_id IS NULL
          AND user_id IS NOT NULL
        """
    )
    op.create_index("ix_generation_jobs_owner_type", "generation_jobs", ["owner_type"])
    op.create_index("ix_generation_jobs_owner_id", "generation_jobs", ["owner_id"])
    op.create_index("ix_generation_jobs_owner_created", "generation_jobs", ["owner_type", "owner_id", "created_at"])


def downgrade() -> None:
    op.execute("DELETE FROM generation_jobs WHERE user_id IS NULL")
    op.drop_index("ix_generation_jobs_owner_created", table_name="generation_jobs")
    op.drop_index("ix_generation_jobs_owner_id", table_name="generation_jobs")
    op.drop_index("ix_generation_jobs_owner_type", table_name="generation_jobs")
    with op.batch_alter_table("generation_jobs") as batch_op:
        batch_op.drop_column("owner_id")
        batch_op.drop_column("owner_type")
        batch_op.alter_column("user_id", existing_type=sa.String(length=128), nullable=False)

    op.execute("DELETE FROM artworks WHERE user_id IS NULL")
    op.drop_index("ix_artworks_owner_created", table_name="artworks")
    op.drop_index("ix_artworks_owner_id", table_name="artworks")
    op.drop_index("ix_artworks_owner_type", table_name="artworks")
    with op.batch_alter_table("artworks") as batch_op:
        batch_op.drop_column("owner_id")
        batch_op.drop_column("owner_type")
        batch_op.alter_column("user_id", existing_type=sa.String(length=128), nullable=False)
