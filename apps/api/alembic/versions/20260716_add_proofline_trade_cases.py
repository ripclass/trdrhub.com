"""Add Proofline trade cases, evidence lineage, findings, and review records.

Revision ID: 20260716_add_proofline_trade_cases
Revises: 20260703_add_payment_fields
Create Date: 2026-07-16
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260716_add_proofline_trade_cases"
down_revision = "20260703_add_payment_fields"
branch_labels = None
depends_on = None


UUID = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB(astext_type=sa.Text())
UUID_DEFAULT = sa.text("gen_random_uuid()")
NOW = sa.func.now()
EMPTY_OBJECT = sa.text("'{}'::jsonb")
EMPTY_ARRAY = sa.text("'[]'::jsonb")


def upgrade() -> None:
    op.create_table(
        "trade_cases",
        sa.Column("id", UUID, primary_key=True, server_default=UUID_DEFAULT),
        sa.Column("case_reference", sa.String(32), nullable=False),
        sa.Column(
            "company_id", UUID, sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "customer_user_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column(
            "owner_user_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column(
            "reviewer_user_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("payment_arrangement", sa.String(64), nullable=False),
        sa.Column("status", sa.String(64), nullable=False, server_default="draft"),
        sa.Column("service_package_id", sa.String(64), nullable=True),
        sa.Column("recommended_decision", sa.String(40), nullable=True),
        sa.Column("final_decision", sa.String(40), nullable=True),
        sa.Column("origin_country", sa.String(2), nullable=True),
        sa.Column("destination_country", sa.String(2), nullable=True),
        sa.Column("currency", sa.String(3), nullable=True),
        sa.Column("amount", sa.Numeric(20, 2), nullable=True),
        sa.Column("shipment_date", sa.Date(), nullable=True),
        sa.Column("expected_payment_date", sa.Date(), nullable=True),
        sa.Column("payment_terms", sa.Text(), nullable=True),
        sa.Column("transaction_details", JSONB, nullable=False, server_default=EMPTY_OBJECT),
        sa.Column(
            "source_lcopilot_session_id",
            UUID,
            sa.ForeignKey("validation_sessions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "final_report_id", UUID, sa.ForeignKey("reports.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("payment_status", sa.String(24), nullable=True),
        sa.Column("stripe_checkout_session_id", sa.String(255), nullable=True),
        sa.Column("stripe_payment_intent_id", sa.String(255), nullable=True),
        sa.Column("amount_paid_cents", sa.Integer(), nullable=True),
        sa.Column("correction_rounds_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("automated_review_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("final_decision_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("company_id", "case_reference", name="uq_trade_cases_company_reference"),
        sa.CheckConstraint("correction_rounds_used >= 0", name="ck_trade_cases_rounds_nonnegative"),
    )
    op.create_index(
        "ix_trade_cases_company_status_updated",
        "trade_cases",
        ["company_id", "status", "updated_at"],
    )
    op.create_index(
        "ix_trade_cases_company_reviewer_status",
        "trade_cases",
        ["company_id", "reviewer_user_id", "status"],
    )
    op.create_index(
        "ix_trade_cases_lcopilot_source", "trade_cases", ["source_lcopilot_session_id"]
    )

    op.create_table(
        "trade_case_parties",
        sa.Column("id", UUID, primary_key=True, server_default=UUID_DEFAULT),
        sa.Column(
            "company_id", UUID, sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "trade_case_id", UUID, sa.ForeignKey("trade_cases.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("role", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("country_code", sa.String(2), nullable=True),
        sa.Column(
            "linked_company_id", UUID, sa.ForeignKey("companies.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("identifiers", JSONB, nullable=False, server_default=EMPTY_OBJECT),
        sa.Column("contact_details", JSONB, nullable=False, server_default=EMPTY_OBJECT),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
    )
    op.create_index(
        "ix_trade_case_parties_company_case",
        "trade_case_parties",
        ["company_id", "trade_case_id"],
    )
    op.create_index(
        "ix_trade_case_parties_company_role", "trade_case_parties", ["company_id", "role"]
    )

    op.create_table(
        "trade_case_documents",
        sa.Column("id", UUID, primary_key=True, server_default=UUID_DEFAULT),
        sa.Column(
            "company_id", UUID, sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "trade_case_id", UUID, sa.ForeignKey("trade_cases.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "document_id", UUID, sa.ForeignKey("documents.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("logical_key", sa.String(128), nullable=False),
        sa.Column("document_type", sa.String(64), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "supersedes_id",
            UUID,
            sa.ForeignKey("trade_case_documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("correction_round", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("evidence_metadata", JSONB, nullable=False, server_default=EMPTY_OBJECT),
        sa.Column(
            "uploaded_by_user_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.UniqueConstraint(
            "trade_case_id", "logical_key", "version_number", name="uq_trade_case_document_version"
        ),
        sa.CheckConstraint("version_number > 0", name="ck_trade_case_documents_version_positive"),
        sa.CheckConstraint("correction_round >= 0", name="ck_trade_case_documents_round_nonnegative"),
    )
    op.create_index(
        "ix_trade_case_documents_company_case_current",
        "trade_case_documents",
        ["company_id", "trade_case_id", "is_current"],
    )
    op.create_index(
        "ix_trade_case_documents_document", "trade_case_documents", ["document_id"]
    )

    op.create_table(
        "trade_case_check_runs",
        sa.Column("id", UUID, primary_key=True, server_default=UUID_DEFAULT),
        sa.Column(
            "company_id", UUID, sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "trade_case_id", UUID, sa.ForeignKey("trade_cases.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("module", sa.String(64), nullable=False),
        sa.Column("module_version", sa.String(64), nullable=True),
        sa.Column("state", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("applicable", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("applicability_reason", sa.Text(), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("source_record_type", sa.String(64), nullable=True),
        sa.Column("source_record_id", sa.String(128), nullable=True),
        sa.Column("result_summary", JSONB, nullable=False, server_default=EMPTY_OBJECT),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("safe_error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.UniqueConstraint(
            "trade_case_id", "module", "idempotency_key", name="uq_trade_case_check_idempotency"
        ),
        sa.CheckConstraint("attempt_count >= 0", name="ck_trade_case_checks_attempt_nonnegative"),
    )
    op.create_index(
        "ix_trade_case_checks_company_case_state",
        "trade_case_check_runs",
        ["company_id", "trade_case_id", "state"],
    )

    op.create_table(
        "proofline_findings",
        sa.Column("id", UUID, primary_key=True, server_default=UUID_DEFAULT),
        sa.Column(
            "company_id", UUID, sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "trade_case_id", UUID, sa.ForeignKey("trade_cases.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "check_run_id",
            UUID,
            sa.ForeignKey("trade_case_check_runs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("source_module", sa.String(64), nullable=False),
        sa.Column("source_finding_id", sa.String(160), nullable=False),
        sa.Column("source_detail_reference", JSONB, nullable=False, server_default=EMPTY_OBJECT),
        sa.Column("category", sa.String(96), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("affected_entity", sa.String(255), nullable=True),
        sa.Column(
            "affected_document_id",
            UUID,
            sa.ForeignKey("trade_case_documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("affected_field", sa.String(128), nullable=True),
        sa.Column("expected", sa.Text(), nullable=False),
        sa.Column("observed", sa.Text(), nullable=False),
        sa.Column("suggested_correction", sa.Text(), nullable=False),
        sa.Column("rule_reference", JSONB, nullable=True),
        sa.Column("evidence_references", JSONB, nullable=False, server_default=EMPTY_ARRAY),
        sa.Column("is_automated", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("visibility", sa.String(16), nullable=False, server_default="customer"),
        sa.Column("status", sa.String(40), nullable=False, server_default="open"),
        sa.Column("reviewer_decision", sa.String(64), nullable=True),
        sa.Column(
            "created_by_user_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column(
            "reviewed_by_user_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.UniqueConstraint(
            "trade_case_id", "source_module", "source_finding_id", name="uq_proofline_finding_source"
        ),
    )
    op.create_index(
        "ix_proofline_findings_company_case_status",
        "proofline_findings",
        ["company_id", "trade_case_id", "status"],
    )
    op.create_index(
        "ix_proofline_findings_company_visibility_severity",
        "proofline_findings",
        ["company_id", "visibility", "severity"],
    )

    op.create_table(
        "remediation_actions",
        sa.Column("id", UUID, primary_key=True, server_default=UUID_DEFAULT),
        sa.Column(
            "company_id", UUID, sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "trade_case_id", UUID, sa.ForeignKey("trade_cases.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "finding_id", UUID, sa.ForeignKey("proofline_findings.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("requested_action", sa.Text(), nullable=False),
        sa.Column("responsible_party", sa.String(128), nullable=True),
        sa.Column("requested_document_type", sa.String(64), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("customer_response", sa.Text(), nullable=True),
        sa.Column(
            "correction_document_id",
            UUID,
            sa.ForeignKey("trade_case_documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(40), nullable=False, server_default="requested"),
        sa.Column("correction_round", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "requested_by_user_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column(
            "resolved_by_user_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.CheckConstraint("correction_round > 0", name="ck_remediation_round_positive"),
    )
    op.create_index(
        "ix_remediation_actions_company_case_status",
        "remediation_actions",
        ["company_id", "trade_case_id", "status"],
    )

    op.create_table(
        "trade_case_decisions",
        sa.Column("id", UUID, primary_key=True, server_default=UUID_DEFAULT),
        sa.Column(
            "company_id", UUID, sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "trade_case_id", UUID, sa.ForeignKey("trade_cases.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("decision_type", sa.String(24), nullable=False),
        sa.Column("decision", sa.String(40), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("contributing_finding_ids", JSONB, nullable=False, server_default=EMPTY_ARRAY),
        sa.Column("evidence_references", JSONB, nullable=False, server_default=EMPTY_ARRAY),
        sa.Column("rule_references", JSONB, nullable=False, server_default=EMPTY_ARRAY),
        sa.Column("unresolved_issues", JSONB, nullable=False, server_default=EMPTY_ARRAY),
        sa.Column("required_actions", JSONB, nullable=False, server_default=EMPTY_ARRAY),
        sa.Column("previous_recommendation", sa.String(40), nullable=True),
        sa.Column("override_reason", sa.Text(), nullable=True),
        sa.Column(
            "reviewer_user_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("system_version", sa.String(64), nullable=False),
        sa.Column("report_version", sa.Integer(), nullable=True),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.UniqueConstraint(
            "trade_case_id", "version_number", name="uq_trade_case_decision_version"
        ),
        sa.UniqueConstraint(
            "trade_case_id", "idempotency_key", name="uq_trade_case_decision_idempotency"
        ),
        sa.CheckConstraint("version_number > 0", name="ck_trade_case_decision_version_positive"),
    )
    op.create_index(
        "ix_trade_case_decisions_company_case",
        "trade_case_decisions",
        ["company_id", "trade_case_id", "version_number"],
    )

    op.create_table(
        "trade_case_events",
        sa.Column("id", UUID, primary_key=True, server_default=UUID_DEFAULT),
        sa.Column(
            "company_id", UUID, sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "trade_case_id", UUID, sa.ForeignKey("trade_cases.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("from_status", sa.String(64), nullable=True),
        sa.Column("to_status", sa.String(64), nullable=True),
        sa.Column("actor_type", sa.String(16), nullable=False),
        sa.Column(
            "actor_user_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("details", JSONB, nullable=False, server_default=EMPTY_OBJECT),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.UniqueConstraint(
            "trade_case_id", "idempotency_key", name="uq_trade_case_event_idempotency"
        ),
    )
    op.create_index(
        "ix_trade_case_events_company_case_time",
        "trade_case_events",
        ["company_id", "trade_case_id", "occurred_at"],
    )

    op.create_table(
        "buyer_requirements",
        sa.Column("id", UUID, primary_key=True, server_default=UUID_DEFAULT),
        sa.Column(
            "company_id", UUID, sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("buyer_reference", sa.String(255), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("applicable_party_type", sa.String(64), nullable=True),
        sa.Column("product_scope", JSONB, nullable=False, server_default=EMPTY_OBJECT),
        sa.Column("jurisdiction", sa.String(64), nullable=True),
        sa.Column("required_document_type", sa.String(64), nullable=True),
        sa.Column("required_credential_type", sa.String(128), nullable=True),
        sa.Column("approved_issuer_type", sa.String(128), nullable=True),
        sa.Column("validity_period_days", sa.Integer(), nullable=True),
        sa.Column("severity", sa.String(16), nullable=False, server_default="medium"),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("rulhub_mapping", JSONB, nullable=True),
        sa.Column(
            "created_by_user_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.UniqueConstraint(
            "company_id",
            "buyer_reference",
            "title",
            "version",
            name="uq_buyer_requirement_version",
        ),
        sa.CheckConstraint("version > 0", name="ck_buyer_requirement_version_positive"),
    )
    op.create_index(
        "ix_buyer_requirements_company_buyer_active",
        "buyer_requirements",
        ["company_id", "buyer_reference", "is_active"],
    )


def downgrade() -> None:
    op.drop_table("buyer_requirements")
    op.drop_table("trade_case_events")
    op.drop_table("trade_case_decisions")
    op.drop_table("remediation_actions")
    op.drop_table("proofline_findings")
    op.drop_table("trade_case_check_runs")
    op.drop_table("trade_case_documents")
    op.drop_table("trade_case_parties")
    op.drop_table("trade_cases")
