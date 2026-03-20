"""Fix solve uniqueness constraints to scope by competition_id

Revision ID: b1c2d3e4f5a6
Revises: a1b2c3d4e5f6
Create Date: 2026-03-20 14:00:00.000000

Problem
-------
The original Solves table had two-column unique constraints:
    (challenge_id, user_id)  – prevents a user solving the same challenge twice
    (challenge_id, team_id)  – prevents a team solving the same challenge twice

These constraints are globally scoped, meaning a user who solves challenge #5
in Competition A is permanently blocked from solving challenge #5 in Competition
B (UNIQUE violation on INSERT).

Fix
---
1. Add a `competition_id` column to the `solves` table that mirrors the value
   already stored in the parent `submissions` row.  The column_property mapping
   in the ORM ensures both columns are written atomically.

2. Copy existing competition_id values from submissions → solves.

3. Drop the old two-column unique indexes (MySQL auto-named them `challenge_id`
   and `challenge_id_2`).

4. Create new three-column unique constraints:
     uq_solves_challenge_user_comp  (challenge_id, user_id, competition_id)
     uq_solves_challenge_team_comp  (challenge_id, team_id, competition_id)

Note on NULL competition_id
---------------------------
MySQL/MariaDB treats each NULL as distinct in unique indexes, so the DB-level
constraint does NOT enforce uniqueness when competition_id is NULL (legacy
challenges with no competition).  For those rows the application-level
already-solved check (which scopes by competition_id when non-NULL) provides
the safeguard.

Downgrade warning
-----------------
The downgrade restores the two-column constraints, which may fail if the data
already contains a user/team that solved the same challenge in two different
competitions.  In that case, manually deduplicate before downgrading.
"""

import sqlalchemy as sa
from alembic import op

revision = "b1c2d3e4f5a6"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()

    # ------------------------------------------------------------------
    # 1. Add competition_id column to solves (idempotent: skip if exists)
    # ------------------------------------------------------------------
    col_exists = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'solves' "
            "AND COLUMN_NAME = 'competition_id'"
        )
    ).scalar()

    if not col_exists:
        op.add_column(
            "solves",
            sa.Column("competition_id", sa.Integer(), nullable=True),
        )

        # ------------------------------------------------------------------
        # 2. Populate from parent submissions table (only needed when new)
        # ------------------------------------------------------------------
        bind.execute(
            sa.text(
                "UPDATE solves s "
                "INNER JOIN submissions sub ON s.id = sub.id "
                "SET s.competition_id = sub.competition_id"
            )
        )

    # ------------------------------------------------------------------
    # 3. Drop old two-column unique indexes (auto-named by MySQL/MariaDB)
    #    Discovered names on live DB: challenge_id  and  challenge_id_2
    #    Use INFORMATION_SCHEMA to find them safely in case names differ.
    # ------------------------------------------------------------------
    result = bind.execute(
        sa.text(
            "SELECT INDEX_NAME "
            "FROM information_schema.STATISTICS "
            "WHERE TABLE_SCHEMA = DATABASE() "
            "  AND TABLE_NAME = 'solves' "
            "  AND NON_UNIQUE = 0 "
            "  AND INDEX_NAME != 'PRIMARY' "
            "GROUP BY INDEX_NAME "
            "HAVING SUM(COLUMN_NAME = 'competition_id') = 0"
        )
    )
    for row in result:
        idx_name = row[0]
        bind.execute(
            sa.text(f"ALTER TABLE solves DROP INDEX `{idx_name}`")
        )

    # ------------------------------------------------------------------
    # 4. Create new three-column unique constraints
    # ------------------------------------------------------------------
    op.create_unique_constraint(
        "uq_solves_challenge_user_comp",
        "solves",
        ["challenge_id", "user_id", "competition_id"],
    )
    op.create_unique_constraint(
        "uq_solves_challenge_team_comp",
        "solves",
        ["challenge_id", "team_id", "competition_id"],
    )

    # ------------------------------------------------------------------
    # 5. Add FK constraint (idempotent: skip if already exists)
    # ------------------------------------------------------------------
    fk_exists = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM information_schema.KEY_COLUMN_USAGE "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'solves' "
            "AND CONSTRAINT_NAME = 'fk_solves_competition_id'"
        )
    ).scalar()

    if not fk_exists:
        op.create_foreign_key(
            "fk_solves_competition_id",
            "solves",
            "competitions",
            ["competition_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade():
    # Remove FK first
    op.drop_constraint("fk_solves_competition_id", "solves", type_="foreignkey")

    # Remove three-column constraints
    op.drop_constraint("uq_solves_challenge_user_comp", "solves", type_="unique")
    op.drop_constraint("uq_solves_challenge_team_comp", "solves", type_="unique")

    # Restore original two-column constraints (may fail on multi-competition data)
    op.create_unique_constraint(None, "solves", ["challenge_id", "user_id"])
    op.create_unique_constraint(None, "solves", ["challenge_id", "team_id"])

    # Drop the added column
    op.drop_column("solves", "competition_id")
