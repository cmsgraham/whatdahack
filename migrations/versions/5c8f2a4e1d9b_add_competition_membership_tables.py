"""Add competition membership tables

Revision ID: 5c8f2a4e1d9b
Revises: 3a6f1c8e9d2b
Create Date: 2026-03-20 00:01:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "5c8f2a4e1d9b"
down_revision = "3a6f1c8e9d2b"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "competition_teams",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("competition_id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("joined_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["competition_id"],
            ["competitions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["team_id"],
            ["teams.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("competition_id", "team_id"),
    )

    op.create_table(
        "competition_users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("competition_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("joined_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["competition_id"],
            ["competitions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("competition_id", "user_id"),
    )


def downgrade():
    op.drop_table("competition_users")
    op.drop_table("competition_teams")
