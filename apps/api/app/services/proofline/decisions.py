"""Proofline recommendation and reviewer-approved final-decision guards."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Iterable, Optional

from sqlalchemy.orm import Session

from app.models import ProoflineDecisionValue, TradeCase, TradeCaseDecision


AuditLogger = Callable[..., Any]
FINAL_DECISION_TYPE = "final"
RECOMMENDATION_TYPE = "recommendation"
UNRESOLVED_FINDING_STATES = {
    "open",
    "acknowledged",
    "customer_action_required",
    "unable_to_resolve",
}
UNAVAILABLE_REQUIRED_CHECK_STATES = {
    "unable_to_assess",
    "evidence_incomplete",
    "pending_review",
}


class DecisionGuardError(ValueError):
    """A decision would violate a launch safety invariant."""


def _decision_value(value: ProoflineDecisionValue | str) -> str:
    try:
        return (
            value.value
            if isinstance(value, ProoflineDecisionValue)
            else ProoflineDecisionValue(value).value
        )
    except ValueError as exc:
        raise DecisionGuardError(f"Unknown Proofline decision: {value!r}") from exc


def record_decision(
    db: Session,
    trade_case: TradeCase,
    *,
    decision: ProoflineDecisionValue | str,
    decision_type: str,
    summary: str,
    reason: str,
    reviewer_user_id: Optional[Any],
    idempotency_key: str,
    system_version: str,
    findings: Iterable[Any] = (),
    checks: Iterable[Any] = (),
    contributing_finding_ids: Optional[list[str]] = None,
    evidence_references: Optional[list[dict[str, Any]]] = None,
    rule_references: Optional[list[dict[str, Any]]] = None,
    unresolved_issues: Optional[list[dict[str, Any]]] = None,
    required_actions: Optional[list[dict[str, Any]]] = None,
    override_reason: Optional[str] = None,
    report_version: Optional[int] = None,
    audit_logger: Optional[AuditLogger] = None,
    now: Optional[datetime] = None,
) -> TradeCaseDecision:
    if decision_type not in {RECOMMENDATION_TYPE, FINAL_DECISION_TYPE}:
        raise DecisionGuardError("Decision type must be recommendation or final")
    if not idempotency_key or not idempotency_key.strip():
        raise DecisionGuardError("A non-empty idempotency key is required")
    if not summary.strip() or not reason.strip():
        raise DecisionGuardError("Decision summary and reason are required")

    existing = (
        db.query(TradeCaseDecision)
        .filter(
            TradeCaseDecision.trade_case_id == trade_case.id,
            TradeCaseDecision.idempotency_key == idempotency_key,
        )
        .first()
    )
    if existing is not None:
        return existing

    value = _decision_value(decision)
    is_final = decision_type == FINAL_DECISION_TYPE
    if is_final and getattr(trade_case, "payment_status", None) == "paid" and reviewer_user_id is None:
        raise DecisionGuardError("A paid Proofline final decision requires reviewer identity")

    prior_recommendation = getattr(trade_case, "recommended_decision", None)
    is_override = is_final and prior_recommendation is not None and prior_recommendation != value
    if is_override and not (override_reason and override_reason.strip()):
        raise DecisionGuardError("A reviewer override reason is required")

    if value == ProoflineDecisionValue.CLEAR.value:
        critical = [
            item
            for item in findings
            if getattr(item, "severity", None) == "critical"
            and getattr(item, "visibility", "customer") == "customer"
            and getattr(item, "status", "open") in UNRESOLVED_FINDING_STATES
        ]
        if critical:
            raise DecisionGuardError("CLEAR is not allowed with an unresolved critical finding")

        unavailable = [
            item
            for item in checks
            if getattr(item, "applicable", True)
            and getattr(item, "required", True)
            and getattr(item, "state", None) in UNAVAILABLE_REQUIRED_CHECK_STATES
        ]
        if unavailable:
            modules = ", ".join(sorted({getattr(item, "module", "unknown") for item in unavailable}))
            raise DecisionGuardError(
                f"CLEAR is not allowed while a required check is unavailable: {modules}"
            )

    latest = (
        db.query(TradeCaseDecision)
        .filter(TradeCaseDecision.trade_case_id == trade_case.id)
        .order_by(TradeCaseDecision.version_number.desc())
        .first()
    )
    version_number = (latest.version_number + 1) if latest is not None else 1
    timestamp = now or datetime.now(timezone.utc)

    record = TradeCaseDecision(
        company_id=trade_case.company_id,
        trade_case_id=trade_case.id,
        version_number=version_number,
        decision_type=decision_type,
        decision=value,
        summary=summary.strip(),
        reason=reason.strip(),
        contributing_finding_ids=contributing_finding_ids or [],
        evidence_references=evidence_references or [],
        rule_references=rule_references or [],
        unresolved_issues=unresolved_issues or [],
        required_actions=required_actions or [],
        previous_recommendation=prior_recommendation,
        override_reason=override_reason.strip() if override_reason else None,
        reviewer_user_id=reviewer_user_id,
        system_version=system_version,
        report_version=report_version,
        idempotency_key=idempotency_key,
        decided_at=timestamp,
    )
    db.add(record)

    if is_final:
        trade_case.final_decision = value
        trade_case.final_decision_at = timestamp
    else:
        trade_case.recommended_decision = value

    if audit_logger is not None:
        audit_logger(
            action="proofline_decision_recorded",
            user_id=reviewer_user_id,
            resource_type="proofline_trade_case",
            resource_id=str(trade_case.id),
            request_data={"decision_type": decision_type, "decision": value},
            audit_metadata={
                "version": version_number,
                "previous_recommendation": prior_recommendation,
                "override_reason": override_reason,
                "idempotency_key": idempotency_key,
            },
        )
    return record


__all__ = ["DecisionGuardError", "record_decision"]

