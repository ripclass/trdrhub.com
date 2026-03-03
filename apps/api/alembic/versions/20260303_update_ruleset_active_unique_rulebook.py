"""Update active ruleset unique index to include rulebook

Revision ID: 20260303_update_ruleset_active_unique_rulebook
Revises: 20260302_merge_day3_validate_schema
Create Date: 2026-03-03 22:10:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260303_update_ruleset_active_unique_rulebook"
down_revision = "20260302_merge_day3_validate_schema"
branch_labels = None
depends_on = None


OLD_INDEX = "ix_rulesets_active_unique"
NEW_INDEX = "ix_rulesets_active_unique_rulebook"


def upgrade() -> None:
    # Backfill: ensure rulebook_version is populated (safety for legacy rows)
    op.execute(
        """
        UPDATE rulesets
        SET rulebook_version = 'unknown'
        WHERE rulebook_version IS NULL OR btrim(rulebook_version) = ''
        """
    )

    # Drop old unique index if it exists
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE indexname = '{OLD_INDEX}'
            ) THEN
                EXECUTE 'DROP INDEX IF EXISTS {OLD_INDEX}';
            END IF;
        END $$;
        """
    )

    # Create new unique index (domain, jurisdiction, rulebook_version) for active rulesets
    op.execute(
        f"""
        CREATE UNIQUE INDEX IF NOT EXISTS {NEW_INDEX}
        ON rulesets (domain, jurisdiction, rulebook_version)
        WHERE status = 'active'
        """
    )


def downgrade() -> None:
    # Drop new unique index if it exists
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE indexname = '{NEW_INDEX}'
            ) THEN
                EXECUTE 'DROP INDEX IF EXISTS {NEW_INDEX}';
            END IF;
        END $$;
        """
    )

    # Restore old unique index
    op.execute(
        f"""
        CREATE UNIQUE INDEX IF NOT EXISTS {OLD_INDEX}
        ON rulesets (domain, jurisdiction)
        WHERE status = 'active'
        """
    )
