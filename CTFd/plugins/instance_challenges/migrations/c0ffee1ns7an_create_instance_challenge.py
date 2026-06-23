"""Create instance_challenge table

Revision ID: c0ffee1ns7an
Revises:
Create Date: 2026-06-23 00:00:00.000000

"""
import sqlalchemy as sa

from CTFd.plugins.migrations import get_all_tables

revision = "c0ffee1ns7an"
down_revision = None
branch_labels = None
depends_on = None


def upgrade(op=None):
    tables = get_all_tables(op=op)
    if "instance_challenge" not in tables:
        op.create_table(
            "instance_challenge",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("instance_image", sa.Text(), nullable=True),
            sa.Column("connect_mode", sa.String(length=16), nullable=True),
            sa.Column("ttl_minutes", sa.Integer(), nullable=True),
            sa.Column("memory_mb", sa.Integer(), nullable=True),
            sa.Column("cpus", sa.String(length=8), nullable=True),
            sa.Column("pids", sa.Integer(), nullable=True),
            sa.Column("egress", sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(
                ["id"], ["challenges.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
        )


def downgrade(op=None):
    tables = get_all_tables(op=op)
    if "instance_challenge" in tables:
        op.drop_table("instance_challenge")
