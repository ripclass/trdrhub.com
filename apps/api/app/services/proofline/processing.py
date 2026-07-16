"""Proofline submission snapshots and persisted automated-review workflow."""

from __future__ import annotations

import logging
import os
from datetime import date
from decimal import Decimal
from typing import Any, Iterable, Mapping, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import (
    Document,
    ProoflineDecisionValue,
    ProoflineFinding,
    TradeCase,
    TradeCaseCheckRun,
    TradeCaseDocument,
    TradeCaseParty,
    TradeCaseStatus,
    ValidationSession,
)
from app.services.proofline.applicability import applicability_for
from app.services.proofline.decisions import record_decision
from app.services.proofline.orchestrator import canonical_input_hash, run_check
from app.services.proofline.state import transition_case


logger = logging.getLogger(__name__)
SYSTEM_VERSION = os.getenv("APP_VERSION", "proofline-v1")


class SubmissionValidationError(ValueError):
    """A draft is not ready to enter the paid service workflow."""


DOCUMENT_ALIASES = {
    "lc": "letter_of_credit",
    "letter_of_credit": "letter_of_credit",
    "commercial_invoice": "commercial_invoice",
    "invoice": "commercial_invoice",
    "bill_of_lading": "transport_document",
    "transport_document": "transport_document",
    "transport": "transport_document",
    "certificate_of_origin": "certificate_of_origin",
    "insurance_certificate": "insurance_document",
    "credit_insurance": "payment_risk_coverage",
}


def _serializable(value: Any) -> Any:
    if isinstance(value, (date, Decimal)):
        return value
    if isinstance(value, Mapping):
        return {str(key): _serializable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serializable(item) for item in value]
    return value


def _document_fields(document: Document | Any) -> dict[str, Any]:
    extracted = getattr(document, "extracted_fields", None) or {}
    if not isinstance(extracted, dict):
        return {}
    nested = extracted.get("fields")
    if isinstance(nested, dict):
        return _serializable(nested)
    return {
        str(key): _serializable(value)
        for key, value in extracted.items()
        if key not in {"proofline_classification", "extraction_status"}
    }


def build_case_context(
    trade_case: TradeCase | Any,
    *,
    parties: Iterable[TradeCaseParty | Any],
    documents: Iterable[tuple[TradeCaseDocument | Any, Document | Any]],
    source_lcopilot_result: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Create one bounded, deterministic snapshot for all source adapters."""
    details = dict(getattr(trade_case, "transaction_details", None) or {})
    party_rows = [
        {
            "id": str(party.id),
            "role": party.role,
            "name": party.name,
            "country_code": party.country_code,
            "identifiers": dict(getattr(party, "identifiers", None) or {}),
        }
        for party in parties
    ]
    document_map: dict[str, dict[str, Any]] = {}
    document_records: list[dict[str, Any]] = []
    role_fields: dict[str, dict[str, Any]] = {}
    for association, document in documents:
        if not bool(getattr(association, "is_current", True)):
            continue
        raw_type = str(
            getattr(association, "document_type", None)
            or getattr(document, "document_type", None)
            or "supporting_document"
        )
        canonical_type = DOCUMENT_ALIASES.get(raw_type, raw_type)
        fields = _document_fields(document)
        metadata = dict(getattr(association, "evidence_metadata", None) or {})
        evidence = {
            "association_id": str(association.id),
            "document_id": str(association.document_id),
            "version": int(getattr(association, "version_number", 1)),
            "filename": getattr(document, "original_filename", None),
            "hash": metadata.get("content_hash"),
            "ocr_confidence": getattr(document, "ocr_confidence", None),
        }
        document_map[canonical_type] = evidence
        role_fields[canonical_type] = fields
        document_records.append(
            {
                **evidence,
                "type": raw_type,
                "canonical_type": canonical_type,
                "fields": fields,
            }
        )

    payment_terms = details.get("payment_terms")
    if not isinstance(payment_terms, dict):
        payment_terms = {"description": getattr(trade_case, "payment_terms", None)}

    context: dict[str, Any] = {
        "trade_case_id": str(trade_case.id),
        "company_id": str(trade_case.company_id),
        "payment_arrangement": trade_case.payment_arrangement,
        "origin_country": trade_case.origin_country,
        "destination_country": trade_case.destination_country,
        "currency": trade_case.currency,
        "amount": trade_case.amount,
        "shipment_date": trade_case.shipment_date,
        "expected_payment_date": trade_case.expected_payment_date,
        "payment_terms": payment_terms,
        "parties": party_rows,
        "documents": document_map,
        "document_records": document_records,
        "source_lcopilot_session_id": (
            str(trade_case.source_lcopilot_session_id)
            if getattr(trade_case, "source_lcopilot_session_id", None)
            else None
        ),
        "source_lcopilot_result": source_lcopilot_result,
        **details,
    }
    context["purchase_order"] = role_fields.get("purchase_order", {})
    context["invoice"] = role_fields.get("commercial_invoice", {})
    context["lc"] = role_fields.get("letter_of_credit", {})
    context["bill_of_lading"] = role_fields.get("transport_document", {})
    context["documents_presence"] = {
        key: True for key in document_map
    }
    if "payment_risk_coverage" in document_map and not context.get("payment_risk_coverage"):
        context["payment_risk_coverage"] = document_map["payment_risk_coverage"]
    return context


def validate_submission_context(context: Mapping[str, Any]) -> None:
    problems: list[str] = []
    named_parties = [party for party in context.get("parties", []) if party.get("name")]
    if len(named_parties) < 2:
        problems.append("Add at least two parties to identify both sides of the transaction")
    if not context.get("documents"):
        problems.append("Upload at least one current document as case evidence")
    if (
        context.get("payment_arrangement") == "letter_of_credit"
        and "letter_of_credit" not in context.get("documents", {})
        and not context.get("source_lcopilot_result")
    ):
        problems.append("Add the letter of credit or link a completed LCopilot review")
    if problems:
        raise SubmissionValidationError("; ".join(problems))


def recommend_decision(*, checks: Iterable[Any], findings: Iterable[Any]) -> str:
    check_rows = list(checks)
    finding_rows = list(findings)
    unresolved = {"open", "acknowledged", "customer_action_required", "unable_to_resolve"}
    if any(
        getattr(item, "severity", None) == "critical"
        and getattr(item, "status", "open") in unresolved
        for item in finding_rows
    ):
        return ProoflineDecisionValue.BLOCKED.value
    if any(
        getattr(item, "applicable", True)
        and getattr(item, "required", True)
        and getattr(item, "state", None) in {"unable_to_assess", "pending_review"}
        for item in check_rows
    ):
        return ProoflineDecisionValue.MANUAL_REVIEW_REQUIRED.value
    if any(
        getattr(item, "state", None) in {"issue_found", "evidence_incomplete"}
        for item in check_rows
    ) or any(getattr(item, "status", "open") in unresolved for item in finding_rows):
        return ProoflineDecisionValue.ACTION_REQUIRED.value
    return ProoflineDecisionValue.CLEAR.value


def load_case_context(db: Session, trade_case: TradeCase) -> dict[str, Any]:
    parties = (
        db.query(TradeCaseParty)
        .filter(
            TradeCaseParty.company_id == trade_case.company_id,
            TradeCaseParty.trade_case_id == trade_case.id,
        )
        .order_by(TradeCaseParty.created_at.asc())
        .all()
    )
    documents = (
        db.query(TradeCaseDocument, Document)
        .join(Document, Document.id == TradeCaseDocument.document_id)
        .filter(
            TradeCaseDocument.company_id == trade_case.company_id,
            TradeCaseDocument.trade_case_id == trade_case.id,
            TradeCaseDocument.is_current.is_(True),
        )
        .all()
    )
    source_result = None
    if trade_case.source_lcopilot_session_id:
        source_session = (
            db.query(ValidationSession)
            .filter(
                ValidationSession.id == trade_case.source_lcopilot_session_id,
                ValidationSession.company_id == trade_case.company_id,
            )
            .first()
        )
        if source_session and isinstance(source_session.validation_results, dict):
            source_result = source_session.validation_results.get("structured_result")
    return build_case_context(
        trade_case,
        parties=parties,
        documents=documents,
        source_lcopilot_result=source_result,
    )


async def process_trade_case(
    db: Session,
    trade_case: TradeCase,
    *,
    adapters: Optional[Mapping[str, Any]] = None,
) -> TradeCase:
    """Run applicable modules idempotently and hand the case to an analyst."""
    from app.integrations.proofline.registry import build_adapter_registry

    if trade_case.status in {
        TradeCaseStatus.AUTOMATED_REVIEW_COMPLETE.value,
        TradeCaseStatus.AWAITING_ANALYST_REVIEW.value,
    }:
        return trade_case
    if trade_case.status in {
        TradeCaseStatus.SUBMITTED.value,
        TradeCaseStatus.CUSTOMER_RESUBMITTED.value,
    }:
        transition_case(
            db,
            trade_case,
            TradeCaseStatus.PROCESSING,
            actor_type="system",
            actor_user_id=None,
            reason="Proofline automated checks started",
            idempotency_key=f"processing:{trade_case.id}:{trade_case.correction_rounds_used}",
        )
        db.flush()
    if trade_case.status != TradeCaseStatus.PROCESSING.value:
        raise SubmissionValidationError("The trade case is not ready for automated processing")

    context = load_case_context(db, trade_case)
    validate_submission_context(context)
    registry = dict(adapters or build_adapter_registry())
    snapshot_hash = canonical_input_hash(context)
    current_checks: list[TradeCaseCheckRun] = []
    for applicability in applicability_for(trade_case.payment_arrangement, context=context):
        check_key = f"{trade_case.correction_rounds_used}:{snapshot_hash[:24]}:{applicability.module}"
        existing_check = (
            db.query(TradeCaseCheckRun)
            .filter(
                TradeCaseCheckRun.trade_case_id == trade_case.id,
                TradeCaseCheckRun.module == applicability.module,
                TradeCaseCheckRun.idempotency_key == check_key,
            )
            .first()
        )
        if existing_check is None:
            prior_findings = (
                db.query(ProoflineFinding)
                .filter(
                    ProoflineFinding.trade_case_id == trade_case.id,
                    ProoflineFinding.source_module == applicability.module,
                    ProoflineFinding.is_automated.is_(True),
                    ProoflineFinding.status.in_(("open", "acknowledged", "customer_action_required", "unable_to_resolve")),
                )
                .all()
            )
            for finding in prior_findings:
                finding.status = "resolved"
                finding.reviewer_decision = "superseded_by_correction_round"
        check_run = await run_check(
            db,
            trade_case=trade_case,
            applicability=applicability,
            context=context,
            adapter=registry.get(applicability.module),
            idempotency_key=check_key,
        )
        current_checks.append(check_run)
        db.flush()

    checks = current_checks
    findings = (
        db.query(ProoflineFinding)
        .filter(ProoflineFinding.trade_case_id == trade_case.id)
        .all()
    )
    recommendation = recommend_decision(checks=checks, findings=findings)
    record_decision(
        db,
        trade_case,
        decision=recommendation,
        decision_type="recommendation",
        summary="Automated Proofline review completed for analyst verification.",
        reason="Recommendation derived from applicable module states and unresolved findings.",
        reviewer_user_id=None,
        idempotency_key=f"recommendation:{trade_case.correction_rounds_used}:{snapshot_hash[:24]}",
        system_version=SYSTEM_VERSION,
        findings=findings,
        checks=checks,
        contributing_finding_ids=[str(item.id) for item in findings],
    )
    transition_case(
        db,
        trade_case,
        TradeCaseStatus.AUTOMATED_REVIEW_COMPLETE,
        actor_type="system",
        actor_user_id=None,
        reason="Applicable automated checks completed",
        idempotency_key=f"automated-complete:{trade_case.id}:{trade_case.correction_rounds_used}",
    )
    transition_case(
        db,
        trade_case,
        TradeCaseStatus.AWAITING_ANALYST_REVIEW,
        actor_type="system",
        actor_user_id=None,
        reason="Qualified analyst verification is required before customer delivery",
        idempotency_key=f"analyst-handoff:{trade_case.id}:{trade_case.correction_rounds_used}",
    )
    return trade_case


async def process_trade_case_by_id(*, case_id: UUID, company_id: UUID) -> None:
    """Background-task boundary with a fresh database session."""
    db = SessionLocal()
    try:
        trade_case = (
            db.query(TradeCase)
            .filter(
                TradeCase.id == case_id,
                TradeCase.company_id == company_id,
                TradeCase.deleted_at.is_(None),
            )
            .first()
        )
        if trade_case is None:
            return
        await process_trade_case(db, trade_case)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception(
            "Proofline background processing failed",
            extra={"trade_case_id": str(case_id), "company_id": str(company_id)},
        )
    finally:
        db.close()


__all__ = [
    "SubmissionValidationError",
    "build_case_context",
    "load_case_context",
    "process_trade_case",
    "process_trade_case_by_id",
    "recommend_decision",
    "validate_submission_context",
]
