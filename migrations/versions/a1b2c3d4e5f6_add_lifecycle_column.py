"""Add lifecycle column to competitions

Revision ID: a1b2c3d4e5f6
Revises: 7e4d2c6a8f1b
Create Date: 2026-03-20 12:00:00.000000

Adds a `lifecycle` column to the competitions table.

Valid states:
    draft      — being set up, not yet announced
    scheduled  — announced, start time in the future
    active     — currently running
    ended      — time has passed; data preserved, scoreboard frozen
    archived   — hidden from all public views; historical record only

Existing competitions are bootstrapped:
    visible → active  (they were already public and running)
    hidden  → draft   (they were being set up)
"""
from alembic import op
import sqlalchemy as sa


revision = "a1b2c3d4e5f6"
down_revision = "7e4d2c6a8f1b"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "competitions",
        sa.Column(
            "lifecycle",
            sa.String(length=16),
            nullable=True,
            server_default="draft",
        ),
    )
    # Bootstrap lifecycle for pre-existing rows so no competition is left NULL.
    # visible → active  (was already public)
    # hidden  → draft   (was being set up)
    op.execute("UPDATE competitions SET lifecycle = 'active' WHERE state = 'visible'")
    op.execute(
        "UPDATE competitions SET lifecycle = 'draft' "
        "WHERE (lifecycle IS NULL OR lifecycle = '') AND state = 'hidden'"
    )


def downgrade():
    with op.batch_alter_table("competitions") as batch_op:
        batch_op.drop_column("lifecycle")
