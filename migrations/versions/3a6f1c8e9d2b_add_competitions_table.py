"""Add competitions table

Revision ID: 3a6f1c8e9d2b
Revises: 48d8250d19bd
Create Date: 2026-03-20 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "3a6f1c8e9d2b"
down_revision = "48d8250d19bd"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "competitions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("state", sa.String(length=16), nullable=True),
        sa.Column("start", sa.DateTime(), nullable=True),
        sa.Column("end", sa.DateTime(), nullable=True),
        sa.Column("freeze", sa.DateTime(), nullable=True),
        sa.Column("user_mode", sa.String(length=16), nullable=True),
        sa.Column("team_size", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )


def downgrade():
    op.drop_table("competitions")
