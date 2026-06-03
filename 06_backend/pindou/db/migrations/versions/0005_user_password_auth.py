"""add password auth for web users

Revision ID: 0005_user_password_auth
Revises: 0004_email_login
Create Date: 2026-06-02
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0005_user_password_auth"
down_revision = "0004_email_login"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("password_hash", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "password_hash")
