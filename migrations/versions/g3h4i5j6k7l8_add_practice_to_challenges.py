"""Add practice column to challenges

Revision ID: g3h4i5j6k7l8
Revises: f2e3d4c5b6a7
Create Date: 2026-03-27 14:00:00.000000

Changes
-------
1. challenges.practice (BOOLEAN, NOT NULL, DEFAULT FALSE)
   When True, the challenge is a practice/introductory challenge:
   - Not counted in scoring / scoreboard
   - Listed on a separate Practice tab on the /challenges page
   - Domain/category grouping still applies
"""

import sqlalchemy as sa
from alembic import op

revision = "g3h4i5j6k7l8"
down_revision = "f2e3d4c5b6a7"


def upgrade():
    op.add_column(
        "challenges",
        sa.Column("practice", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade():
    op.drop_column("challenges", "practice")
