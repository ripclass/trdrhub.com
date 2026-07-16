"""Add configurable Proofline service packages and payment snapshots.

Revision ID: 20260716_add_proofline_pricing
Revises: 20260716_add_proofline_document_session
Create Date: 2026-07-16
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260716_add_proofline_pricing"
down_revision = "20260716_add_proofline_document_session"
branch_labels = None
depends_on = None


JSONB = postgresql.JSONB(astext_type=sa.Text())
NOW = sa.func.now()


def upgrade() -> None:
    packages = op.create_table(
        "proofline_service_packages",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("package_type", sa.String(24), nullable=False, server_default="case"),
        sa.Column("billing_mode", sa.String(24), nullable=False, server_default="payment"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("amount_cents", sa.Integer(), nullable=True),
        sa.Column("price_label", sa.String(64), nullable=False),
        sa.Column("stripe_price_id", sa.String(255), nullable=True),
        sa.Column("included_documents", sa.Integer(), nullable=True),
        sa.Column("included_parties", sa.Integer(), nullable=True),
        sa.Column("included_correction_rounds", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("turnaround_class", sa.String(64), nullable=True),
        sa.Column("features", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("self_service_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.CheckConstraint("amount_cents IS NULL OR amount_cents >= 0", name="ck_proofline_package_amount"),
        sa.CheckConstraint("included_correction_rounds >= 0", name="ck_proofline_package_correction_rounds"),
    )
    op.create_index(
        "ix_proofline_packages_active_public_order",
        "proofline_service_packages",
        ["active", "is_public", "display_order"],
    )
    op.bulk_insert(
        packages,
        [
            {
                "id": "proofline_standard",
                "name": "Proofline Standard",
                "description": "Verified review for a standard trade case with one correction round.",
                "package_type": "case",
                "billing_mode": "payment",
                "currency": "USD",
                "amount_cents": 19900,
                "price_label": "$199 per trade case",
                "stripe_price_id": None,
                "included_documents": 12,
                "included_parties": 8,
                "included_correction_rounds": 1,
                "turnaround_class": "standard",
                "features": ["Human analyst verification", "Applicable TRDRHub checks", "One correction round", "Final clearance report"],
                "is_public": True,
                "self_service_enabled": True,
                "active": True,
                "display_order": 10,
            },
            {
                "id": "proofline_managed",
                "name": "Proofline Managed Clearance",
                "description": "Managed review for complex evidence, credentials, buyer requirements, and remediation.",
                "package_type": "case",
                "billing_mode": "payment",
                "currency": "USD",
                "amount_cents": 39900,
                "price_label": "From $399 per trade case",
                "stripe_price_id": None,
                "included_documents": 30,
                "included_parties": 16,
                "included_correction_rounds": 2,
                "turnaround_class": "managed",
                "features": ["Everything in Standard", "Credential and evidence-gap review", "Buyer requirements", "Two correction rounds"],
                "is_public": True,
                "self_service_enabled": True,
                "active": True,
                "display_order": 20,
            },
            {
                "id": "proofline_custom",
                "name": "Complex or urgent case",
                "description": "Manual scope and quote for unsupported urgency, volume, jurisdictions, or research.",
                "package_type": "case",
                "billing_mode": "manual",
                "currency": "USD",
                "amount_cents": None,
                "price_label": "Custom quote",
                "stripe_price_id": None,
                "included_documents": None,
                "included_parties": None,
                "included_correction_rounds": 0,
                "turnaround_class": "quoted",
                "features": ["Scoped review", "Confirmed turnaround", "Manual commercial agreement"],
                "is_public": True,
                "self_service_enabled": False,
                "active": True,
                "display_order": 30,
            },
            {
                "id": "trade_desk_starter",
                "name": "Trade Desk Starter",
                "description": "Negotiated monthly plan for up to ten standard cases.",
                "package_type": "recurring",
                "billing_mode": "manual",
                "currency": "USD",
                "amount_cents": 99900,
                "price_label": "$999 per month",
                "stripe_price_id": None,
                "included_documents": None,
                "included_parties": None,
                "included_correction_rounds": 1,
                "turnaround_class": "contract",
                "features": ["Up to 10 standard cases", "Manual sales activation"],
                "is_public": False,
                "self_service_enabled": False,
                "active": True,
                "display_order": 100,
            },
            {
                "id": "trade_desk_operations",
                "name": "Trade Desk Operations",
                "description": "Negotiated monthly plan for up to thirty standard cases.",
                "package_type": "recurring",
                "billing_mode": "manual",
                "currency": "USD",
                "amount_cents": 249900,
                "price_label": "$2,499 per month",
                "stripe_price_id": None,
                "included_documents": None,
                "included_parties": None,
                "included_correction_rounds": 1,
                "turnaround_class": "contract",
                "features": ["Up to 30 standard cases", "Manual sales activation"],
                "is_public": False,
                "self_service_enabled": False,
                "active": True,
                "display_order": 110,
            },
            {
                "id": "trade_desk_enterprise",
                "name": "Enterprise",
                "description": "Custom volume, SLA, integrations, and reviewer allocation.",
                "package_type": "recurring",
                "billing_mode": "manual",
                "currency": "USD",
                "amount_cents": None,
                "price_label": "Custom",
                "stripe_price_id": None,
                "included_documents": None,
                "included_parties": None,
                "included_correction_rounds": 0,
                "turnaround_class": "contract",
                "features": ["Custom volume", "Negotiated SLA", "Integration support"],
                "is_public": False,
                "self_service_enabled": False,
                "active": True,
                "display_order": 120,
            },
        ],
    )

    op.add_column("trade_cases", sa.Column("credit_amount_cents", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("trade_cases", sa.Column("payment_currency", sa.String(3), nullable=True))
    op.add_column("trade_cases", sa.Column("pricing_snapshot", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")))
    op.add_column("trade_cases", sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("trade_cases", sa.Column("refunded_at", sa.DateTime(timezone=True), nullable=True))
    op.create_check_constraint("ck_trade_cases_credit_nonnegative", "trade_cases", "credit_amount_cents >= 0")


def downgrade() -> None:
    op.drop_constraint("ck_trade_cases_credit_nonnegative", "trade_cases", type_="check")
    op.drop_column("trade_cases", "refunded_at")
    op.drop_column("trade_cases", "paid_at")
    op.drop_column("trade_cases", "pricing_snapshot")
    op.drop_column("trade_cases", "payment_currency")
    op.drop_column("trade_cases", "credit_amount_cents")
    op.drop_index("ix_proofline_packages_active_public_order", table_name="proofline_service_packages")
    op.drop_table("proofline_service_packages")
