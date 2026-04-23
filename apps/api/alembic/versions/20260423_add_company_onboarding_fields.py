"""Add Company onboarding fields: business_activities, tier, country default.

Backs the 3-question onboarding wizard (Q1 activities x Q2 country x Q3 tier).
See ONBOARDING_REFACTOR_RESUME.md (repo root) and memory/project_lcopilot_onboarding_redesign.md.

Atomic in the Stream A style:
  * ADD COLUMN with server_default backfills every existing row in one statement.
  * Follow-up UPDATEs promote better values from existing event_metadata JSONB where available.
  * CHECK constraints land last so backfill can't be rejected mid-flight.

Revision ID: 20260423_add_company_onboarding_fields
Revises: 20260422_add_workflow_type
Create Date: 2026-04-23
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260423_add_company_onboarding_fields"
down_revision = "20260422_add_workflow_type"
branch_labels = None
depends_on = None


ALLOWED_ACTIVITIES_SQL = "ARRAY['exporter','importer','agent','services']::text[]"
ALLOWED_TIERS_SQL = "('solo','sme','enterprise')"


def upgrade() -> None:
    # 1. Add business_activities as TEXT[] — all existing rows default to
    #    ['exporter']. Using sa.Text (not sa.String) so the resulting column
    #    is text[] not varchar[]; varchar[] would need an explicit ::text[]
    #    cast for the <@ operator in the CHECK constraint below.
    op.add_column(
        "companies",
        sa.Column(
            "business_activities",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("ARRAY['exporter']::text[]"),
        ),
    )

    # 2. Add tier — all existing rows default to 'sme'.
    op.add_column(
        "companies",
        sa.Column(
            "tier",
            sa.String(length=20),
            nullable=False,
            server_default="sme",
        ),
    )

    # 3. Country default — plan locks 'BD' as the backfill value.
    op.alter_column("companies", "country", server_default="BD")
    op.execute("UPDATE companies SET country = 'BD' WHERE country IS NULL")

    # 4. Backfill business_activities from legacy event_metadata->>business_type.
    #    Currently produced values: 'exporter', 'importer', 'both'. Guard for future
    #    'agent'/'services' values too, just in case something pre-seeded them.
    op.execute(
        """
        UPDATE companies
        SET business_activities = CASE
            WHEN event_metadata->>'business_type' = 'both'     THEN ARRAY['exporter','importer']::text[]
            WHEN event_metadata->>'business_type' = 'exporter' THEN ARRAY['exporter']::text[]
            WHEN event_metadata->>'business_type' = 'importer' THEN ARRAY['importer']::text[]
            WHEN event_metadata->>'business_type' = 'agent'    THEN ARRAY['agent']::text[]
            WHEN event_metadata->>'business_type' = 'services' THEN ARRAY['services']::text[]
            ELSE business_activities
        END
        WHERE event_metadata ? 'business_type'
        """
    )

    # 5. Backfill tier from legacy event_metadata->>company_size.
    op.execute(
        """
        UPDATE companies
        SET tier = event_metadata->>'company_size'
        WHERE event_metadata->>'company_size' IN ('solo','sme','enterprise')
        """
    )

    # 6. CHECK constraints — enum validity + non-empty array.
    op.create_check_constraint(
        "ck_companies_business_activities_valid",
        "companies",
        "business_activities <@ " + ALLOWED_ACTIVITIES_SQL
        + " AND array_length(business_activities, 1) >= 1",
    )
    op.create_check_constraint(
        "ck_companies_tier_valid",
        "companies",
        "tier IN " + ALLOWED_TIERS_SQL,
    )


def downgrade() -> None:
    op.drop_constraint("ck_companies_tier_valid", "companies", type_="check")
    op.drop_constraint("ck_companies_business_activities_valid", "companies", type_="check")
    op.drop_column("companies", "tier")
    op.drop_column("companies", "business_activities")
    op.alter_column("companies", "country", server_default=None)
