"""Proofline trade-case aggregate.

Proofline orchestrates existing TRDRHub records.  These models deliberately
reference Company, User, ValidationSession, Document, and Report rather than
creating parallel identity, storage, validation, or reporting systems.
"""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from .base import Base


JSON_VALUE = JSON().with_variant(JSONB, "postgresql")


class PaymentArrangement(str, enum.Enum):
    LETTER_OF_CREDIT = "letter_of_credit"
    OPEN_ACCOUNT = "open_account"
    ADVANCE_TT = "advance_tt"
    PARTIAL_ADVANCE_BALANCE = "partial_advance_balance"
    DOCUMENTS_AGAINST_PAYMENT = "documents_against_payment"
    DOCUMENTS_AGAINST_ACCEPTANCE = "documents_against_acceptance"
    BUYER_LED_SUPPLY_CHAIN_FINANCE = "buyer_led_supply_chain_finance"
    FACTORING_RECEIVABLES_FINANCE = "factoring_receivables_finance"
    CONSIGNMENT = "consignment"
    OTHER = "other"


class TradeCaseStatus(str, enum.Enum):
    DRAFT = "draft"
    AWAITING_PAYMENT = "awaiting_payment"
    SUBMITTED = "submitted"
    PROCESSING = "processing"
    AUTOMATED_REVIEW_COMPLETE = "automated_review_complete"
    AWAITING_ANALYST_REVIEW = "awaiting_analyst_review"
    ACTION_REQUIRED = "action_required"
    CUSTOMER_RESUBMITTED = "customer_resubmitted"
    FINAL_REVIEW = "final_review"
    CLEARED = "cleared"
    CONDITIONALLY_CLEARED = "conditionally_cleared"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"
    CLOSED = "closed"


class ProoflineDecisionValue(str, enum.Enum):
    CLEAR = "CLEAR"
    CONDITIONAL_CLEARANCE = "CONDITIONAL_CLEARANCE"
    ACTION_REQUIRED = "ACTION_REQUIRED"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"
    BLOCKED = "BLOCKED"
    UNABLE_TO_ASSESS = "UNABLE_TO_ASSESS"


class ProoflineCheckState(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    CLEAR = "clear"
    ISSUE_FOUND = "issue_found"
    EVIDENCE_INCOMPLETE = "evidence_incomplete"
    NOT_APPLICABLE = "not_applicable"
    UNABLE_TO_ASSESS = "unable_to_assess"
    PENDING_REVIEW = "pending_review"


class ProoflineFindingStatus(str, enum.Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    CUSTOMER_ACTION_REQUIRED = "customer_action_required"
    CORRECTED = "corrected"
    ACCEPTED_EXCEPTION = "accepted_exception"
    FALSE_POSITIVE = "false_positive"
    RESOLVED = "resolved"
    UNABLE_TO_RESOLVE = "unable_to_resolve"


class TradeCase(Base):
    __tablename__ = "trade_cases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_reference = Column(String(32), nullable=False)
    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    customer_user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    owner_user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewer_user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    title = Column(String(255), nullable=False)
    payment_arrangement = Column(
        String(64), nullable=False, default=PaymentArrangement.LETTER_OF_CREDIT.value
    )
    status = Column(String(64), nullable=False, default=TradeCaseStatus.DRAFT.value)
    service_package_id = Column(String(64), nullable=True)
    recommended_decision = Column(String(40), nullable=True)
    final_decision = Column(String(40), nullable=True)

    origin_country = Column(String(2), nullable=True)
    destination_country = Column(String(2), nullable=True)
    currency = Column(String(3), nullable=True)
    amount = Column(Numeric(20, 2), nullable=True)
    shipment_date = Column(Date, nullable=True)
    expected_payment_date = Column(Date, nullable=True)
    payment_terms = Column(Text, nullable=True)
    transaction_details = Column(JSON_VALUE, nullable=False, default=dict)

    source_lcopilot_session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("validation_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    final_report_id = Column(
        UUID(as_uuid=True), ForeignKey("reports.id", ondelete="SET NULL"), nullable=True
    )

    payment_status = Column(String(24), nullable=True)
    stripe_checkout_session_id = Column(String(255), nullable=True)
    stripe_payment_intent_id = Column(String(255), nullable=True)
    amount_paid_cents = Column(Integer, nullable=True)
    correction_rounds_used = Column(Integer, nullable=False, default=0)

    submitted_at = Column(DateTime(timezone=True), nullable=True)
    processing_started_at = Column(DateTime(timezone=True), nullable=True)
    automated_review_completed_at = Column(DateTime(timezone=True), nullable=True)
    final_decision_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "company_id", "case_reference", name="uq_trade_cases_company_reference"
        ),
        Index(
            "ix_trade_cases_company_status_updated",
            "company_id",
            "status",
            "updated_at",
        ),
        Index(
            "ix_trade_cases_company_reviewer_status",
            "company_id",
            "reviewer_user_id",
            "status",
        ),
        Index("ix_trade_cases_lcopilot_source", "source_lcopilot_session_id"),
        CheckConstraint("correction_rounds_used >= 0", name="ck_trade_cases_rounds_nonnegative"),
    )


class TradeCaseParty(Base):
    __tablename__ = "trade_case_parties"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    trade_case_id = Column(
        UUID(as_uuid=True), ForeignKey("trade_cases.id", ondelete="CASCADE"), nullable=False
    )
    role = Column(String(64), nullable=False)
    name = Column(String(255), nullable=False)
    country_code = Column(String(2), nullable=True)
    linked_company_id = Column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="SET NULL"), nullable=True
    )
    identifiers = Column(JSON_VALUE, nullable=False, default=dict)
    contact_details = Column(JSON_VALUE, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_trade_case_parties_company_case", "company_id", "trade_case_id"),
        Index("ix_trade_case_parties_company_role", "company_id", "role"),
    )


class TradeCaseDocument(Base):
    __tablename__ = "trade_case_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    trade_case_id = Column(
        UUID(as_uuid=True), ForeignKey("trade_cases.id", ondelete="CASCADE"), nullable=False
    )
    document_id = Column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="RESTRICT"), nullable=False
    )
    logical_key = Column(String(128), nullable=False)
    document_type = Column(String(64), nullable=False)
    version_number = Column(Integer, nullable=False, default=1)
    supersedes_id = Column(
        UUID(as_uuid=True),
        ForeignKey("trade_case_documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    correction_round = Column(Integer, nullable=False, default=0)
    is_current = Column(Boolean, nullable=False, default=True)
    evidence_metadata = Column(JSON_VALUE, nullable=False, default=dict)
    uploaded_by_user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "trade_case_id",
            "logical_key",
            "version_number",
            name="uq_trade_case_document_version",
        ),
        Index(
            "ix_trade_case_documents_company_case_current",
            "company_id",
            "trade_case_id",
            "is_current",
        ),
        Index("ix_trade_case_documents_document", "document_id"),
        CheckConstraint("version_number > 0", name="ck_trade_case_documents_version_positive"),
        CheckConstraint("correction_round >= 0", name="ck_trade_case_documents_round_nonnegative"),
    )


class TradeCaseCheckRun(Base):
    __tablename__ = "trade_case_check_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    trade_case_id = Column(
        UUID(as_uuid=True), ForeignKey("trade_cases.id", ondelete="CASCADE"), nullable=False
    )
    module = Column(String(64), nullable=False)
    module_version = Column(String(64), nullable=True)
    state = Column(String(32), nullable=False, default=ProoflineCheckState.PENDING.value)
    applicable = Column(Boolean, nullable=False, default=True)
    applicability_reason = Column(Text, nullable=False)
    idempotency_key = Column(String(128), nullable=False)
    input_hash = Column(String(64), nullable=False)
    attempt_count = Column(Integer, nullable=False, default=0)
    source_record_type = Column(String(64), nullable=True)
    source_record_id = Column(String(128), nullable=True)
    result_summary = Column(JSON_VALUE, nullable=False, default=dict)
    error_code = Column(String(64), nullable=True)
    safe_error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "trade_case_id",
            "module",
            "idempotency_key",
            name="uq_trade_case_check_idempotency",
        ),
        Index(
            "ix_trade_case_checks_company_case_state",
            "company_id",
            "trade_case_id",
            "state",
        ),
        CheckConstraint("attempt_count >= 0", name="ck_trade_case_checks_attempt_nonnegative"),
    )


class ProoflineFinding(Base):
    __tablename__ = "proofline_findings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    trade_case_id = Column(
        UUID(as_uuid=True), ForeignKey("trade_cases.id", ondelete="CASCADE"), nullable=False
    )
    check_run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("trade_case_check_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_module = Column(String(64), nullable=False)
    source_finding_id = Column(String(160), nullable=False)
    source_detail_reference = Column(JSON_VALUE, nullable=False, default=dict)
    category = Column(String(96), nullable=False)
    severity = Column(String(16), nullable=False)
    title = Column(String(255), nullable=False)
    explanation = Column(Text, nullable=False)
    affected_entity = Column(String(255), nullable=True)
    affected_document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("trade_case_documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    affected_field = Column(String(128), nullable=True)
    expected = Column(Text, nullable=False)
    observed = Column(Text, nullable=False)
    suggested_correction = Column(Text, nullable=False)
    rule_reference = Column(JSON_VALUE, nullable=True)
    evidence_references = Column(JSON_VALUE, nullable=False, default=list)
    is_automated = Column(Boolean, nullable=False, default=True)
    visibility = Column(String(16), nullable=False, default="customer")
    status = Column(String(40), nullable=False, default=ProoflineFindingStatus.OPEN.value)
    reviewer_decision = Column(String(64), nullable=True)
    created_by_user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_by_user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "trade_case_id",
            "source_module",
            "source_finding_id",
            name="uq_proofline_finding_source",
        ),
        Index(
            "ix_proofline_findings_company_case_status",
            "company_id",
            "trade_case_id",
            "status",
        ),
        Index(
            "ix_proofline_findings_company_visibility_severity",
            "company_id",
            "visibility",
            "severity",
        ),
    )


class RemediationAction(Base):
    __tablename__ = "remediation_actions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    trade_case_id = Column(
        UUID(as_uuid=True), ForeignKey("trade_cases.id", ondelete="CASCADE"), nullable=False
    )
    finding_id = Column(
        UUID(as_uuid=True), ForeignKey("proofline_findings.id", ondelete="CASCADE"), nullable=False
    )
    requested_action = Column(Text, nullable=False)
    responsible_party = Column(String(128), nullable=True)
    requested_document_type = Column(String(64), nullable=True)
    due_at = Column(DateTime(timezone=True), nullable=True)
    customer_response = Column(Text, nullable=True)
    correction_document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("trade_case_documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolution_notes = Column(Text, nullable=True)
    status = Column(String(40), nullable=False, default="requested")
    correction_round = Column(Integer, nullable=False, default=1)
    requested_by_user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    resolved_by_user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index(
            "ix_remediation_actions_company_case_status",
            "company_id",
            "trade_case_id",
            "status",
        ),
        CheckConstraint("correction_round > 0", name="ck_remediation_round_positive"),
    )


class TradeCaseDecision(Base):
    __tablename__ = "trade_case_decisions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    trade_case_id = Column(
        UUID(as_uuid=True), ForeignKey("trade_cases.id", ondelete="CASCADE"), nullable=False
    )
    version_number = Column(Integer, nullable=False)
    decision_type = Column(String(24), nullable=False)
    decision = Column(String(40), nullable=False)
    summary = Column(Text, nullable=False)
    reason = Column(Text, nullable=False)
    contributing_finding_ids = Column(JSON_VALUE, nullable=False, default=list)
    evidence_references = Column(JSON_VALUE, nullable=False, default=list)
    rule_references = Column(JSON_VALUE, nullable=False, default=list)
    unresolved_issues = Column(JSON_VALUE, nullable=False, default=list)
    required_actions = Column(JSON_VALUE, nullable=False, default=list)
    previous_recommendation = Column(String(40), nullable=True)
    override_reason = Column(Text, nullable=True)
    reviewer_user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    system_version = Column(String(64), nullable=False)
    report_version = Column(Integer, nullable=True)
    idempotency_key = Column(String(128), nullable=False)
    decided_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "trade_case_id", "version_number", name="uq_trade_case_decision_version"
        ),
        UniqueConstraint(
            "trade_case_id", "idempotency_key", name="uq_trade_case_decision_idempotency"
        ),
        Index(
            "ix_trade_case_decisions_company_case",
            "company_id",
            "trade_case_id",
            "version_number",
        ),
        CheckConstraint("version_number > 0", name="ck_trade_case_decision_version_positive"),
    )


class TradeCaseEvent(Base):
    __tablename__ = "trade_case_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    trade_case_id = Column(
        UUID(as_uuid=True), ForeignKey("trade_cases.id", ondelete="CASCADE"), nullable=False
    )
    event_type = Column(String(64), nullable=False)
    from_status = Column(String(64), nullable=True)
    to_status = Column(String(64), nullable=True)
    actor_type = Column(String(16), nullable=False)
    actor_user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reason = Column(Text, nullable=True)
    details = Column(JSON_VALUE, nullable=False, default=dict)
    idempotency_key = Column(String(128), nullable=False)
    occurred_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "trade_case_id", "idempotency_key", name="uq_trade_case_event_idempotency"
        ),
        Index(
            "ix_trade_case_events_company_case_time",
            "company_id",
            "trade_case_id",
            "occurred_at",
        ),
    )


class BuyerRequirement(Base):
    __tablename__ = "buyer_requirements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    buyer_reference = Column(String(255), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    applicable_party_type = Column(String(64), nullable=True)
    product_scope = Column(JSON_VALUE, nullable=False, default=dict)
    jurisdiction = Column(String(64), nullable=True)
    required_document_type = Column(String(64), nullable=True)
    required_credential_type = Column(String(128), nullable=True)
    approved_issuer_type = Column(String(128), nullable=True)
    validity_period_days = Column(Integer, nullable=True)
    severity = Column(String(16), nullable=False, default="medium")
    effective_date = Column(Date, nullable=False)
    version = Column(Integer, nullable=False, default=1)
    is_active = Column(Boolean, nullable=False, default=True)
    rulhub_mapping = Column(JSON_VALUE, nullable=True)
    created_by_user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "buyer_reference",
            "title",
            "version",
            name="uq_buyer_requirement_version",
        ),
        Index(
            "ix_buyer_requirements_company_buyer_active",
            "company_id",
            "buyer_reference",
            "is_active",
        ),
        CheckConstraint("version > 0", name="ck_buyer_requirement_version_positive"),
    )


PAYMENT_ARRANGEMENT_VALUES = tuple(item.value for item in PaymentArrangement)
TRADE_CASE_STATUS_VALUES = tuple(item.value for item in TradeCaseStatus)
PROOFLINE_DECISION_VALUES = tuple(item.value for item in ProoflineDecisionValue)
PROOFLINE_CHECK_STATE_VALUES = tuple(item.value for item in ProoflineCheckState)
PROOFLINE_FINDING_STATUS_VALUES = tuple(item.value for item in ProoflineFindingStatus)

