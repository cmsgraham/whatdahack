"""Add avatar column to users

Revision ID: f2e3d4c5b6a7
Revises: e1f2a3b4c5d6
Create Date: 2026-03-23 14:00:00.000000

Adds users.avatar (TEXT, nullable) for storing base64-encoded profile images.
"""

import sqlalchemy as sa
from alembic import op

revision = "f2e3d4c5b6a7"
down_revision = "e1f2a3b4c5d6"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("avatar", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("users", "avatar")
