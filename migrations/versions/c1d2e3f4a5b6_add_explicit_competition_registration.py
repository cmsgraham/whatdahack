"""Add explicit competition registration tables

Revision ID: c1d2e3f4a5b6
Revises: b1c2d3e4f5a6
Create Date: 2026-03-20 15:00:00.000000

Changes
-------
1. competition_users.status (VARCHAR 16, NOT NULL, default 'joined')
   Added to the existing competition_users table so the registration state
   machine has a physical backing column.

   States:
     'joined'       — fully registered; may access challenges and submit flags
     'pending_team' — registered but team not yet selected (teams-mode only)

   Existing rows (pre-migration) are populated with 'joined' to preserve the
   behaviour of any users already in the table.

2. competition_team_members (new table)
   Per-competition team assignment, decoupled from the global Users.team_id FK.
   Allows the same user account to be on different teams across competitions.

   Columns:
     id             INT PK AUTO_INCREMENT
     competition_id INT FK → competitions.id ON DELETE CASCADE, NOT NULL
     team_id        INT FK → teams.id ON DELETE CASCADE, NOT NULL
     user_id        INT FK → users.id ON DELETE CASCADE, NOT NULL
     joined_at      DATETIME

   Constraints:
     UNIQUE (competition_id, user_id)  — one team per user per competition
"""

import datetime

import sqlalchemy as sa
from alembic import op

revision = "c1d2e3f4a5b6"
down_revision = "b1c2d3e4f5a6"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()

    # ------------------------------------------------------------------
    # 1. Add status column to competition_users (idempotent)
    # ------------------------------------------------------------------
    col_exists = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() "
            "AND TABLE_NAME = 'competition_users' "
            "AND COLUMN_NAME = 'status'"
        )
    ).scalar()

    if not col_exists:
        op.add_column(
            "competition_users",
            sa.Column(
                "status",
                sa.String(16),
                nullable=False,
                server_default="joined",
            ),
        )
        # Back-fill any rows created before this migration
        bind.execute(
            sa.text(
                "UPDATE competition_users SET status = 'joined' WHERE status IS NULL OR status = ''"
            )
        )

    # ------------------------------------------------------------------
    # 2. Create competition_team_members table (idempotent)
    # ------------------------------------------------------------------
    table_exists = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM information_schema.TABLES "
            "WHERE TABLE_SCHEMA = DATABASE() "
            "AND TABLE_NAME = 'competition_team_members'"
        )
    ).scalar()

    if not table_exists:
        op.create_table(
            "competition_team_members",
            sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
            sa.Column("competition_id", sa.Integer(), nullable=False),
            sa.Column("team_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column(
                "joined_at",
                sa.DateTime(),
                nullable=True,
                default=datetime.datetime.utcnow,
            ),
            sa.ForeignKeyConstraint(
                ["competition_id"],
                ["competitions.id"],
                ondelete="CASCADE",
                name="fk_ctm_competition_id",
            ),
            sa.ForeignKeyConstraint(
                ["team_id"],
                ["teams.id"],
                ondelete="CASCADE",
                name="fk_ctm_team_id",
            ),
            sa.ForeignKeyConstraint(
                ["user_id"],
                ["users.id"],
                ondelete="CASCADE",
                name="fk_ctm_user_id",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "competition_id",
                "user_id",
                name="uq_comp_team_member_user",
            ),
        )


def downgrade():
    bind = op.get_bind()

    # Drop competition_team_members if it exists
    table_exists = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM information_schema.TABLES "
            "WHERE TABLE_SCHEMA = DATABASE() "
            "AND TABLE_NAME = 'competition_team_members'"
        )
    ).scalar()
    if table_exists:
        op.drop_table("competition_team_members")

    # Drop status column from competition_users if it exists
    col_exists = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() "
            "AND TABLE_NAME = 'competition_users' "
            "AND COLUMN_NAME = 'status'"
        )
    ).scalar()
    if col_exists:
        op.drop_column("competition_users", "status")
