"""DAY1 P0: ruleset hygiene updates (sanctions.eu rule_count + safe rulebook_version normalization)

Revision ID: 20260227_day1_p0_failclosed
Revises: 20251223_create_rules_audit_table
Create Date: 2026-02-27
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "20260227_day1_p0_failclosed"
down_revision = "20251223_create_rules_audit_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1) Fix sanctions.eu rule_count mismatch against actual active rules
    op.execute(
        """
        UPDATE rulesets rs
        SET rule_count = COALESCE(sub.active_count, 0)
        FROM (
            SELECT r.ruleset_id, COUNT(*)::int AS active_count
            FROM rules r
            WHERE r.is_active = true
            GROUP BY r.ruleset_id
        ) sub
        WHERE rs.id = sub.ruleset_id
          AND rs.domain = 'sanctions.eu'
          AND rs.rule_count IS DISTINCT FROM sub.active_count;
        """
    )

    op.execute(
        """
        UPDATE rulesets rs
        SET rule_count = 0
        WHERE rs.domain = 'sanctions.eu'
          AND NOT EXISTS (
              SELECT 1 FROM rules r
              WHERE r.ruleset_id = rs.id
                AND r.is_active = true
          )
          AND rs.rule_count IS DISTINCT FROM 0;
        """
    )

    # 2) Normalize known-safe rulebook_version typo/format variants
    op.execute(
        """
        UPDATE rulesets
        SET rulebook_version = CASE rulebook_version
            WHEN 'UCP 600:2007' THEN 'UCP600:2007'
            WHEN 'UCP-600:2007' THEN 'UCP600:2007'
            WHEN 'UCP600 2007' THEN 'UCP600:2007'
            WHEN 'ISBP 745:2013' THEN 'ISBP745:2013'
            WHEN 'ISBP-745:2013' THEN 'ISBP745:2013'
            WHEN 'URDG 758:2010' THEN 'URDG758:2010'
            WHEN 'URDG-758:2010' THEN 'URDG758:2010'
            ELSE rulebook_version
        END
        WHERE rulebook_version IN (
            'UCP 600:2007', 'UCP-600:2007', 'UCP600 2007',
            'ISBP 745:2013', 'ISBP-745:2013',
            'URDG 758:2010', 'URDG-758:2010'
        );
        """
    )


def downgrade() -> None:
    # No deterministic downgrade for data hygiene correction.
    pass
