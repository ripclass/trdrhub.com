"""Pricing restructure — billing tier values + data migration.

2026-05-10 clean-sheet pricing restructure (see
docs/superpowers/specs/2026-05-10-lcopilot-pricing-restructure-design.md).

``companies.tier`` is now the BILLING tier (7-value BusinessTier enum):
payg / solo / business / enterprise / agency_starter / agency_pro /
agency_enterprise. The column carries a CHECK constraint
``ck_companies_tier_valid`` (added in 20260423) that previously allowed
only ('solo','sme','enterprise'). This migration:

  1. Drops the old CHECK constraint.
  2. Rewrites existing rows: ``'sme'`` -> ``'business'``. ``'solo'`` and
     ``'enterprise'`` are already valid billing-tier strings; left alone.
  3. Re-creates the CHECK constraint allowing the 7 new tier values.
  4. Changes the column default from ``'sme'`` to ``'payg'`` (new
     un-onboarded companies start on pay-per-use).

Before the UPDATE, logs how many rows are on ``'sme'`` so the count is in
the migration output — if any are real paying customers, grandfather them
manually (bump to ``enterprise`` or set ``quota_limit`` to 50) after this
runs; ``business`` gives 25 LCs/mo vs the old ``sme`` 50.

Revision ID: 20260510_pricing_restructure_tier
Revises: 20260430_add_services_clients_time
Create Date: 2026-05-10
"""

import logging

from alembic import op
import sqlalchemy as sa


revision = "20260510_pricing_restructure_tier"
down_revision = "20260430_add_services_clients_time"
branch_labels = None
depends_on = None

logger = logging.getLogger("alembic.runtime.migration")

_OLD_TIERS_SQL = "('solo','sme','enterprise')"
_NEW_TIERS_SQL = (
    "('payg','solo','business','enterprise',"
    "'agency_starter','agency_pro','agency_enterprise')"
)


def upgrade() -> None:
    bind = op.get_bind()

    sme_count = bind.execute(
        sa.text("SELECT COUNT(*) FROM companies WHERE tier = 'sme'")
    ).scalar() or 0
    logger.info(
        "pricing_restructure: %d company row(s) on legacy tier 'sme' -> "
        "'business' (25 LCs/mo, was 50). Grandfather any real paying ones "
        "manually if needed.",
        sme_count,
    )

    # Drop the old constraint, rewrite data, re-add with the new value set.
    op.drop_constraint("ck_companies_tier_valid", "companies", type_="check")
    op.execute("UPDATE companies SET tier = 'business' WHERE tier = 'sme'")
    op.create_check_constraint(
        "ck_companies_tier_valid",
        "companies",
        "tier IN " + _NEW_TIERS_SQL,
    )
    op.alter_column(
        "companies",
        "tier",
        server_default="payg",
        existing_type=sa.String(length=20),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "companies",
        "tier",
        server_default="sme",
        existing_type=sa.String(length=20),
        existing_nullable=False,
    )
    op.drop_constraint("ck_companies_tier_valid", "companies", type_="check")
    # Best-effort reverse of the data migration. Map every value that isn't
    # in the old allowed set back to a legal one so the re-added constraint
    # holds: 'business' / 'payg' / 'agency_*' -> 'sme'.
    op.execute(
        "UPDATE companies SET tier = 'sme' WHERE tier NOT IN " + _OLD_TIERS_SQL
    )
    op.create_check_constraint(
        "ck_companies_tier_valid",
        "companies",
        "tier IN " + _OLD_TIERS_SQL,
    )
