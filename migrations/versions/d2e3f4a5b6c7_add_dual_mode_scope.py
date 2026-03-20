"""Add dual-mode platform scope: challenges.scope + competition_solves table

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-03-20 18:00:00.000000

Changes
-------
1. challenges.scope (VARCHAR 16, NOT NULL, DEFAULT 'platform')
   Discriminator column for the dual-mode architecture.
   Values:
     'platform'    — evergreen challenge, visible from /challenges, scores to Solves
     'competition' — event-scoped challenge, scores to competition_solves

   Backfill: any challenge with competition_id IS NOT NULL → scope='competition'

2. competition_solves table (new)
   Stores solve events for competition-scoped challenges only.
   Platform challenges continue to use the existing solves table.

3. Data migration: move any existing Solves rows that belong to
   competition-scoped challenges (scope='competition') into competition_solves.
   In production as of 2026-03-20 no such rows exist (competition has not
   started), so this INSERT is a safe no-op.

Rollback: drop scope column, drop competition_solves table, no data recovery
for migrated solves (acceptable — competition hasn't started).
"""

import sqlalchemy as sa
from alembic import op

revision = "d2e3f4a5b6c7"
down_revision = "c1d2e3f4a5b6"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Add scope discriminator to challenges
    op.add_column(
        "challenges",
        sa.Column(
            "scope",
            sa.String(16),
            nullable=False,
            server_default="platform",
        ),
    )
    # Backfill: competition-owned challenges get scope='competition'
    op.execute(
        "UPDATE challenges SET scope = 'competition' WHERE competition_id IS NOT NULL"
    )

    # 2. Create competition_solves table
    op.create_table(
        "competition_solves",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "challenge_id",
            sa.Integer,
            sa.ForeignKey("challenges.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "competition_id",
            sa.Integer,
            sa.ForeignKey("competitions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "team_id",
            sa.Integer,
            sa.ForeignKey("teams.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "ip",
            sa.String(46),
            nullable=True,
        ),
        sa.Column(
            "provided",
            sa.Text,
            nullable=True,
        ),
        sa.Column(
            "date",
            sa.DateTime,
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("challenge_id", "user_id", name="uq_comp_solve_user"),
    )

    # 3. Migrate any existing solve rows for competition challenges into
    #    competition_solves so the old solves table never contains competition data.
    #    We join through submissions (parent table in joined-table inheritance) to
    #    access challenge_id, user_id, team_id, date from the solves row while
    #    getting competition_id, ip, provided from submissions.
    op.execute(
        """
        INSERT INTO competition_solves
            (challenge_id, competition_id, user_id, team_id, ip, provided, date)
        SELECT
            sub.challenge_id,
            sub.competition_id,
            sub.user_id,
            sub.team_id,
            sub.ip,
            sub.provided,
            sub.date
        FROM solves sol
        JOIN submissions sub ON sub.id = sol.id
        JOIN challenges c ON c.id = sub.challenge_id
        WHERE c.scope = 'competition'
          AND sub.competition_id IS NOT NULL
        """
    )

    # 4. Delete the migrated rows from solves (and submissions via CASCADE)
    #    Only delete rows that were successfully inserted above.
    op.execute(
        """
        DELETE sol FROM solves sol
        JOIN submissions sub ON sub.id = sol.id
        JOIN challenges c ON c.id = sub.challenge_id
        WHERE c.scope = 'competition'
          AND sub.competition_id IS NOT NULL
        """
    )


def downgrade():
    # Reverse: drop competition_solves, remove scope column.
    # Migrated solves are NOT restored (safe — prod had none at migration time).
    op.drop_table("competition_solves")
    op.drop_column("challenges", "scope")
