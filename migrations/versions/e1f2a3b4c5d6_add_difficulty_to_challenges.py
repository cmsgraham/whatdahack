"""Add difficulty column to challenges

Revision ID: e1f2a3b4c5d6
Revises: d2e3f4a5b6c7
Create Date: 2026-03-23 12:00:00.000000

Adds challenges.difficulty (VARCHAR 20, nullable).
Allowed values: 'easy', 'medium', 'hard', 'insane' (enforced in UI, not DB).
"""

import sqlalchemy as sa
from alembic import op

revision = "e1f2a3b4c5d6"
down_revision = "d2e3f4a5b6c7"


def upgrade():
    op.add_column(
        "challenges",
        sa.Column("difficulty", sa.String(20), nullable=True, server_default=None),
    )


def downgrade():
    op.drop_column("challenges", "difficulty")
