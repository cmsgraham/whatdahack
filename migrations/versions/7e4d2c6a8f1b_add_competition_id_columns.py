"""Add competition_id columns to challenges, submissions, and awards

Revision ID: 7e4d2c6a8f1b
Revises: 5c8f2a4e1d9b
Create Date: 2026-03-20 00:02:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "7e4d2c6a8f1b"
down_revision = "5c8f2a4e1d9b"
branch_labels = None
depends_on = None


def upgrade():
    # All three columns are nullable — existing rows are unaffected.
    # A separate backfill step (flask init-default-competition) will populate them.
    op.add_column(
        "challenges",
        sa.Column(
            "competition_id",
            sa.Integer(),
            sa.ForeignKey("competitions.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    op.add_column(
        "submissions",
        sa.Column(
            "competition_id",
            sa.Integer(),
            sa.ForeignKey("competitions.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    op.add_column(
        "awards",
        sa.Column(
            "competition_id",
            sa.Integer(),
            sa.ForeignKey("competitions.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade():
    # MariaDB requires dropping the FK constraint before dropping the column.
    # Alembic does not auto-detect constraint names across all dialects, so we use
    # batch_alter_table which handles this portably.
    with op.batch_alter_table("awards") as batch_op:
        batch_op.drop_column("competition_id")

    with op.batch_alter_table("submissions") as batch_op:
        batch_op.drop_column("competition_id")

    with op.batch_alter_table("challenges") as batch_op:
        batch_op.drop_column("competition_id")
