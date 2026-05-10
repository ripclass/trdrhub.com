"""Pricing restructure — billing tier values + data migration.

2026-05-10 clean-sheet pricing restructure (see
docs/superpowers/specs/2026-05-10-lcopilot-pricing-restructure-design.md).

``companies.tier`` is now the BILLING tier (7-value BusinessTier enum):
payg / solo / business / enterprise / agency_starter / agency_pro /
agency_enterprise. There is no DB-level enum or CHECK constraint on the
column (it's a plain ``varchar(20)``), so this migration only:

  1. Changes the column default from ``'sme'`` to ``'payg'`` (new
     un-onboarded companies start on pay-per-use).
  2. Rewrites existing rows: ``'sme'`` -> ``'business'``. ``'solo'`` and
     ``'enterprise'`` are already valid billing-tier strings, so they're
     left alone. Anything else (shouldn't exist) is also left alone and
     handled at read time by ``services.entitlements`` defaulting to
     ``business``.

Before the UPDATE, logs how many rows are on ``'sme'`` so the count is in
the migration output — if any are real paying customers, grandfather them
manually (bump to ``enterprise`` or set ``quota_limit`` to 50) before or
after this runs; ``business`` gives 25 LCs/mo vs the old ``sme`` 50.

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

    op.execute("UPDATE companies SET tier = 'business' WHERE tier = 'sme'")
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
    # Best-effort reverse of the data migration. 'business' rows that were
    # 'sme' before can't be distinguished from net-new 'business' rows, so
    # this maps all 'business' back to 'sme'. Acceptable for a rollback.
    op.execute("UPDATE companies SET tier = 'sme' WHERE tier = 'business'")
