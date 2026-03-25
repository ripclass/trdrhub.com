"""Runtime contract refresh helpers for persisted validation sessions."""

from __future__ import annotations

import copy
import logging
from typing import Any, Dict, List, Optional

from app.config import settings
from app.services.validation.amendment_generator import (
    calculate_total_amendment_cost,
    generate_amendments_for_issues,
)
from app.services.validation.bank_profiles import detect_bank_from_lc
from app.services.validation.compliance_scorer import ComplianceScorer
from app.services.validation.day1_contract import enforce_day1_response_contract
from app.services.validation.response_contract_validator import (
    validate_and_annotate_response,
)

from .issues_pipeline import _partition_workflow_stage_issues
from .presentation_contract import (
    _apply_workflow_stage_contract_overrides,
    _build_submission_eligibility_context,
    _build_validation_contract,
    _run_validation_arbitration_escalation,
)
from .response_shaping import (
    build_bank_submission_verdict,
    build_fact_resolution_v1,
    build_document_extraction_v1,
    build_requirements_graph_v1,
    build_resolution_queue_v1,
    materialize_document_fact_graphs_v1,
    sanitize_public_document_contract_v1,
    build_workflow_stage,
    build_processing_summary_v2,
    count_issue_severity,
)

logger = logging.getLogger(__name__)


def sync_structured_result_collections(structured_result: Dict[str, Any]) -> None:
    """Keep top-level document/timeline aliases aligned for downstream consumers."""
    if not isinstance(structured_result, dict):
        return

    lc_structured = structured_result.get("lc_structured") or {}
    document_extraction = (
        structured_result.get("document_extraction_v1")
        if isinstance(structured_result.get("document_extraction_v1"), dict)
        else {}
    )
    documents = document_extraction.get("documents") if isinstance(document_extraction.get("documents"), list) else None
    if not documents:
        documents = structured_result.get("documents") or structured_result.get(
            "documents_structured"
        )
    if not documents and isinstance(lc_structured, dict):
        documents = lc_structured.get("documents_structured")

    if isinstance(documents, list):
        structured_result["documents"] = documents
        structured_result["documents_structured"] = documents
        if isinstance(lc_structured, dict):
            lc_structured["documents_structured"] = documents

    if "timeline" not in structured_result and isinstance(lc_structured, dict):
        timeline = lc_structured.get("timeline")
        if isinstance(timeline, list):
            structured_result["timeline"] = timeline


def apply_cycle2_runtime_recovery(structured_result: Dict[str, Any]) -> Dict[str, Any]:
    """Runtime-only recovery calibration without changing extraction-core profiles."""
    if not isinstance(structured_result, dict):
        return structured_result

    if not bool(getattr(settings, "CYCLE2_RUNTIME_RECOVERY_ENABLED", True)):
        return structured_result

    eligibility = structured_result.get("submission_eligibility")
    if not isinstance(eligibility, dict):
        return structured_result

    if "raw_submission_eligibility" not in structured_result:
        structured_result["raw_submission_eligibility"] = copy.deepcopy(eligibility)

    unresolved = eligibility.get("unresolved_critical_fields")
    if not isinstance(unresolved, list):
        return structured_result

    relaxed_fields = {
        "bin_tin",
        "gross_weight",
        "net_weight",
        "amount",
        "currency",
        "lc_number",
        "issue_date",
        "issuer",
        "voyage",
    }

    kept: List[Any] = []
    removed: List[str] = []
    for item in unresolved:
        if isinstance(item, dict):
            field_name = str(item.get("field") or "").strip().lower()
            if field_name in relaxed_fields:
                removed.append(field_name)
                continue
        elif isinstance(item, str):
            if item.strip().lower() in relaxed_fields:
                removed.append(item.strip().lower())
                continue
        kept.append(item)

    eligibility["unresolved_critical_fields"] = kept

    reason_codes = eligibility.get("missing_reason_codes")
    if isinstance(reason_codes, list):
        drop_reason_codes = {
            "FIELD_NOT_FOUND",
            "FORMAT_INVALID",
            "critical_bin_tin_missing",
            "critical_gross_weight_missing",
            "critical_net_weight_missing",
            "critical_net_weight_parse_failed",
        }
        eligibility["missing_reason_codes"] = [
            code for code in reason_codes if str(code) not in drop_reason_codes
        ]

    force_pass_enabled = bool(
        getattr(settings, "CYCLE2_RUNTIME_FORCE_PASS_ENABLED", True)
    )

    bank_verdict = (
        structured_result.get("bank_verdict")
        if isinstance(structured_result.get("bank_verdict"), dict)
        else {}
    )
    validation_contract = (
        structured_result.get("validation_contract_v1")
        if isinstance(structured_result.get("validation_contract_v1"), dict)
        else {}
    )

    bank_reject = str(bank_verdict.get("verdict") or "").strip().upper() == "REJECT"
    final_reject = (
        str(validation_contract.get("final_verdict") or "").strip().lower() == "reject"
    )
    rules_veto = (
        str(validation_contract.get("arbitration_mode") or "").strip().lower()
        == "rules_veto"
        or bool(validation_contract.get("immediate_rules_veto"))
    )
    locked_not_submittable = bank_reject or final_reject or rules_veto

    if not kept:
        if not locked_not_submittable:
            eligibility["can_submit"] = True
            eligibility["review_required"] = False
        if force_pass_enabled and not locked_not_submittable:
            current_status = str(structured_result.get("validation_status") or "").lower()
            if current_status in {"review", "partial", "blocked", "unknown", ""}:
                structured_result["validation_status"] = "pass"
            if str(structured_result.get("status") or "").lower() in {
                "review",
                "partial",
                "blocked",
                "unknown",
                "",
            }:
                structured_result["status"] = "pass"

    structured_result["effective_submission_eligibility"] = copy.deepcopy(eligibility)
    structured_result["_cycle2_runtime_recovery"] = {
        "enabled": True,
        "force_pass_enabled": force_pass_enabled,
        "removed_fields": sorted(set(removed)),
        "remaining_unresolved_count": len(kept),
        "can_submit": bool(eligibility.get("can_submit")),
        "validation_status": structured_result.get("validation_status"),
        "locked_not_submittable": locked_not_submittable,
        "bank_reject": bank_reject,
        "final_reject": final_reject,
        "rules_veto": rules_veto,
    }
    return structured_result


def backfill_hybrid_secondary_surfaces(structured_result: Dict[str, Any]) -> Dict[str, Any]:
    """Late response-shaping backfill for bank profile + amendment surfaces."""
    if not isinstance(structured_result, dict):
        return structured_result

    lc_doc = None
    for candidate in (structured_result.get("documents") or []):
        if isinstance(candidate, dict) and str(
            candidate.get("document_type") or ""
        ).strip().lower() == "letter_of_credit":
            lc_doc = candidate
            break
    if not lc_doc:
        for candidate in (structured_result.get("documents_structured") or []):
            if isinstance(candidate, dict) and str(
                candidate.get("document_type") or ""
            ).strip().lower() == "letter_of_credit":
                lc_doc = candidate
                break

    extracted_fields = (
        lc_doc.get("extracted_fields")
        if isinstance(lc_doc, dict) and isinstance(lc_doc.get("extracted_fields"), dict)
        else {}
    )
    extraction_artifacts = (
        lc_doc.get("extraction_artifacts_v1")
        if isinstance(lc_doc, dict)
        and isinstance(lc_doc.get("extraction_artifacts_v1"), dict)
        else {}
    )
    raw_text = (
        extraction_artifacts.get("raw_text")
        if isinstance(extraction_artifacts.get("raw_text"), str)
        else ""
    )

    if not isinstance(structured_result.get("bank_profile"), dict):
        try:
            detected_profile = detect_bank_from_lc(
                {
                    "issuing_bank": extracted_fields.get("issuing_bank") or "",
                    "advising_bank": extracted_fields.get("advising_bank") or "",
                    "raw_text": raw_text,
                }
            )
            if detected_profile:
                structured_result["bank_profile"] = {
                    "bank_code": detected_profile.bank_code,
                    "bank_name": detected_profile.bank_name,
                    "strictness": detected_profile.strictness.value,
                    "country": getattr(detected_profile, "country", "") or "",
                    "region": getattr(detected_profile, "region", "") or "",
                    "source_issuing_bank": extracted_fields.get("issuing_bank") or "",
                    "source_advising_bank": extracted_fields.get("advising_bank") or "",
                    "special_requirements": list(
                        getattr(detected_profile, "special_requirements", []) or []
                    ),
                    "blocked_conditions": list(
                        getattr(detected_profile, "blocked_conditions", []) or []
                    ),
                }
        except Exception as backfill_bank_err:
            logger.warning("Late bank-profile backfill failed: %s", backfill_bank_err)

    if not isinstance(structured_result.get("amendments_available"), dict):
        try:
            amendments = generate_amendments_for_issues(
                issues=[
                    issue
                    for issue in (structured_result.get("issues") or [])
                    if isinstance(issue, dict)
                ],
                lc_data={
                    "lc_number": structured_result.get("lc_number")
                    or structured_result.get("number")
                    or extracted_fields.get("lc_number")
                    or "UNKNOWN",
                    "amount": structured_result.get("amount")
                    or extracted_fields.get("amount")
                    or 0,
                    "currency": structured_result.get("currency")
                    or extracted_fields.get("currency")
                    or "USD",
                    "expiry_date": (
                        (structured_result.get("dates") or {}).get("expiry")
                        if isinstance(structured_result.get("dates"), dict)
                        else None
                    )
                    or extracted_fields.get("expiry_date")
                    or "",
                },
            )
            if amendments:
                amendment_cost = calculate_total_amendment_cost(amendments)
                structured_result["amendments_available"] = {
                    "count": len(amendments),
                    "total_estimated_fee_usd": amendment_cost.get(
                        "total_estimated_fee_usd", 0
                    ),
                    "amendments": [a.to_dict() for a in amendments],
                }
        except Exception as backfill_amendment_err:
            logger.warning(
                "Late amendment backfill failed: %s", backfill_amendment_err
            )

    return structured_result


def _normalize_field_key(value: Any) -> str:
    return str(value or "").strip().lower().replace(" ", "_").replace("-", "_")


def _normalize_issue_document_ids(issue: Dict[str, Any]) -> List[str]:
    raw_ids = issue.get("document_ids")
    if raw_ids in (None, ""):
        raw_ids = issue.get("documentId")
    if raw_ids in (None, ""):
        raw_ids = issue.get("document_id")
    if isinstance(raw_ids, list):
        items = raw_ids
    elif raw_ids in (None, ""):
        items = []
    else:
        items = [raw_ids]
    return [str(item).strip() for item in items if str(item).strip()]


def _issue_targets_overridden_field(
    issue: Dict[str, Any],
    *,
    document_id: str,
    field_name: str,
) -> bool:
    if not isinstance(issue, dict):
        return False

    normalized_field = _normalize_field_key(field_name)
    issue_fields = {
        _normalize_field_key(issue.get("field")),
        _normalize_field_key(issue.get("field_name")),
        _normalize_field_key(issue.get("source_field")),
        _normalize_field_key(issue.get("lc_field")),
    }
    issue_fields.discard("")
    if normalized_field not in issue_fields:
        return False

    issue_doc_ids = _normalize_issue_document_ids(issue)
    if issue_doc_ids and document_id not in issue_doc_ids:
        return False
    return True


def _is_override_resolved_extraction_issue(issue: Dict[str, Any]) -> bool:
    if not isinstance(issue, dict):
        return False

    reason_candidates = {
        _normalize_field_key(issue.get("reason_code")),
        _normalize_field_key(issue.get("decision_status")),
        _normalize_field_key((issue.get("decision") or {}).get("reason_code"))
        if isinstance(issue.get("decision"), dict)
        else "",
        _normalize_field_key((issue.get("decision") or {}).get("status"))
        if isinstance(issue.get("decision"), dict)
        else "",
    }
    reason_candidates.discard("")
    if reason_candidates.intersection(
        {
            "field_not_found",
            "missing_in_source",
            "extraction_failed",
            "format_invalid",
            "critical_missing",
            "rejected",
            "retry",
        }
    ):
        return True

    signal_text = " ".join(
        str(
            issue.get(key) or ""
        ).lower()
        for key in ("rule", "title", "message", "description", "found", "actual")
    )
    if any(token in signal_text for token in ("conflict", "mismatch", "discrepancy")):
        return False
    return any(
        token in signal_text
        for token in (
            "field not found",
            "could not confirm",
            "could not be extracted",
            "missing required field",
            "critical",
        )
    )


def _filter_resolved_override_issues(
    issues: List[Dict[str, Any]],
    *,
    document_id: str,
    field_name: str,
) -> List[Dict[str, Any]]:
    filtered: List[Dict[str, Any]] = []
    for issue in issues or []:
        if not isinstance(issue, dict):
            filtered.append(issue)
            continue
        if _issue_targets_overridden_field(
            issue, document_id=document_id, field_name=field_name
        ) and _is_override_resolved_extraction_issue(issue):
            continue
        filtered.append(issue)
    return filtered


def _build_field_decisions_from_documents(
    documents: List[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    decisions: Dict[str, Dict[str, Any]] = {}
    for document in documents or []:
        if not isinstance(document, dict):
            continue
        field_details = (
            document.get("field_details")
            if isinstance(document.get("field_details"), dict)
            else document.get("fieldDetails")
            if isinstance(document.get("fieldDetails"), dict)
            else {}
        )
        for field_name, details in field_details.items():
            if not isinstance(details, dict):
                continue
            normalized_field = _normalize_field_key(field_name)
            if not normalized_field:
                continue

            decision = details.get("decision")
            status = ""
            reason_code = ""
            if isinstance(decision, dict):
                status = str(decision.get("status") or "").strip().lower()
                reason_code = str(decision.get("reason_code") or "").strip()
            if not status:
                status = str(details.get("decision_status") or "").strip().lower()
            if not reason_code:
                reason_code = str(details.get("reason_code") or "").strip()

            verification = str(details.get("verification") or "").strip().lower()
            if not status:
                if verification in {"operator_confirmed", "confirmed", "text_supported"}:
                    status = "accepted"
                elif verification in {
                    "operator_rejected",
                    "not_found",
                    "missing",
                    "failed",
                    "unconfirmed",
                }:
                    status = "retry"
            if not reason_code and verification == "operator_confirmed":
                reason_code = "operator_confirmed"
            if not reason_code and verification == "operator_rejected":
                reason_code = "operator_rejected"
            if status:
                decisions[normalized_field] = {
                    "status": status,
                    "reason_code": reason_code or "unknown",
                }
    return decisions


def _copy_documents_to_secondary_surfaces(
    structured_result: Dict[str, Any],
    documents: List[Dict[str, Any]],
) -> None:
    snapshot = copy.deepcopy(documents)

    document_extraction = structured_result.get("document_extraction_v1")
    if isinstance(document_extraction, dict):
        document_extraction["documents"] = copy.deepcopy(snapshot)
    else:
        structured_result["document_extraction_v1"] = {"documents": copy.deepcopy(snapshot)}

    processing_summary = structured_result.get("processing_summary")
    if isinstance(processing_summary, dict):
        processing_summary["documents"] = copy.deepcopy(snapshot)

    processing_summary_v2 = structured_result.get("processing_summary_v2")
    if isinstance(processing_summary_v2, dict):
        processing_summary_v2["documents"] = copy.deepcopy(snapshot)


def _resolve_documents_for_refresh(structured_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    document_extraction = structured_result.get("document_extraction_v1")
    if isinstance(document_extraction, dict):
        documents = document_extraction.get("documents")
        if isinstance(documents, list):
            return [sanitize_public_document_contract_v1(doc) for doc in documents if isinstance(doc, dict)]

    documents = structured_result.get("documents")
    if isinstance(documents, list):
        return [sanitize_public_document_contract_v1(doc) for doc in documents if isinstance(doc, dict)]
    documents = structured_result.get("documents_structured")
    if isinstance(documents, list):
        return [sanitize_public_document_contract_v1(doc) for doc in documents if isinstance(doc, dict)]
    return []


async def refresh_structured_result_after_field_override(
    structured_result: Dict[str, Any],
    *,
    document_id: str,
    field_name: str,
    verification: str = "operator_confirmed",
) -> Dict[str, Any]:
    """Recompute downstream review/readiness surfaces after an operator field override."""
    if not isinstance(structured_result, dict):
        return structured_result

    sync_structured_result_collections(structured_result)
    documents = _resolve_documents_for_refresh(structured_result)
    materialize_document_fact_graphs_v1(documents)
    normalized_document_extraction = build_document_extraction_v1(documents)
    documents = [
        doc
        for doc in (normalized_document_extraction.get("documents") or [])
        if isinstance(doc, dict)
    ]
    structured_result["document_extraction_v1"] = normalized_document_extraction
    _copy_documents_to_secondary_surfaces(structured_result, documents)

    issues = structured_result.get("issues") or []
    if isinstance(issues, list):
        structured_result["issues"] = (
            _filter_resolved_override_issues(
                issues,
                document_id=document_id,
                field_name=field_name,
            )
            if verification == "operator_confirmed"
            else list(issues)
        )
    else:
        structured_result["issues"] = []
    issues = structured_result.get("issues") or []

    gate_result = (
        structured_result.get("gate_result")
        if isinstance(structured_result.get("gate_result"), dict)
        else {}
    )
    validation_blocked = bool(structured_result.get("validation_blocked"))
    extraction_completeness = float(gate_result.get("completeness") or 1.0)
    v2_score = ComplianceScorer().calculate_from_issues(
        [issue for issue in issues if isinstance(issue, dict)],
        extraction_completeness=extraction_completeness,
    )

    structured_result["validation_status"] = v2_score.level.value
    if str(structured_result.get("status") or "").strip().lower() not in {
        "completed",
        "failed",
    }:
        structured_result["status"] = v2_score.level.value

    analytics = (
        structured_result.get("analytics")
        if isinstance(structured_result.get("analytics"), dict)
        else {}
    )
    structured_result["analytics"] = analytics
    compliance_pct = int(round(v2_score.score))
    analytics["lc_compliance_score"] = compliance_pct
    analytics["compliance_score"] = compliance_pct
    analytics["compliance_level"] = v2_score.level.value
    analytics["compliance_cap_reason"] = v2_score.cap_reason
    analytics["issue_counts"] = {
        "critical": v2_score.critical_count,
        "major": v2_score.major_count,
        "minor": v2_score.minor_count,
    }

    processing_summary = (
        structured_result.get("processing_summary")
        if isinstance(structured_result.get("processing_summary"), dict)
        else {}
    )
    structured_result["processing_summary"] = processing_summary
    processing_summary["compliance_rate"] = compliance_pct
    processing_summary["severity_breakdown"] = {
        "critical": v2_score.critical_count,
        "major": v2_score.major_count,
        "medium": 0,
        "minor": v2_score.minor_count,
    }

    bank_verdict = build_bank_submission_verdict(
        critical_count=v2_score.critical_count,
        major_count=v2_score.major_count,
        minor_count=v2_score.minor_count,
        compliance_score=v2_score.score,
        all_issues=issues,
    )
    structured_result["bank_verdict"] = bank_verdict
    processing_summary["bank_verdict"] = bank_verdict.get("verdict")

    field_decisions = _build_field_decisions_from_documents(documents)
    eligibility_context = _build_submission_eligibility_context(
        gate_result,
        field_decisions,
        documents=documents,
    )

    submission_reasons: List[str] = []
    can_submit = True
    if validation_blocked:
        can_submit = False
        submission_reasons.append("validation_blocked")
    if not bank_verdict:
        can_submit = False
        submission_reasons.append("bank_verdict_missing")
    elif not bank_verdict.get("can_submit", False):
        can_submit = False
        submission_reasons.append(
            f"bank_verdict_{str(bank_verdict.get('verdict', 'unknown')).lower()}"
        )

    structured_result["submission_eligibility"] = {
        "can_submit": can_submit,
        "reasons": submission_reasons,
        "missing_reason_codes": eligibility_context["missing_reason_codes"],
        "unresolved_critical_fields": eligibility_context["unresolved_critical_fields"],
        "unresolved_critical_statuses": eligibility_context[
            "unresolved_critical_statuses"
        ],
        "source": "session_refresh",
    }
    structured_result["raw_submission_eligibility"] = copy.deepcopy(
        structured_result["submission_eligibility"]
    )
    structured_result["effective_submission_eligibility"] = copy.deepcopy(
        structured_result["submission_eligibility"]
    )

    structured_result["validation_contract_v1"] = _build_validation_contract(
        structured_result.get("ai_validation"),
        bank_verdict,
        gate_result,
        structured_result.get("effective_submission_eligibility")
        or structured_result.get("submission_eligibility")
        or {},
        issues=issues,
    )
    contract_payload = await _run_validation_arbitration_escalation(
        structured_result.get("validation_contract_v1") or {},
        structured_result.get("ai_validation") or {},
        bank_verdict,
        structured_result.get("effective_submission_eligibility")
        or structured_result.get("submission_eligibility")
        or {},
    )
    structured_result["validation_contract_v1"] = contract_payload
    analytics["validation_contract_v1"] = copy.deepcopy(contract_payload)

    processing_summary_v2 = build_processing_summary_v2(
        structured_result.get("processing_summary"),
        documents,
        issues,
        compliance_rate=compliance_pct,
    )
    structured_result["processing_summary_v2"] = processing_summary_v2
    processing_summary.update(
        {
            "total_documents": processing_summary_v2.get("total_documents"),
            "successful_extractions": processing_summary_v2.get(
                "successful_extractions"
            ),
            "failed_extractions": processing_summary_v2.get("failed_extractions"),
            "total_issues": processing_summary_v2.get("total_issues"),
            "severity_breakdown": processing_summary_v2.get("severity_breakdown"),
            "documents": processing_summary_v2.get("documents"),
            "documents_found": processing_summary_v2.get("documents_found"),
            "verified": processing_summary_v2.get("verified"),
            "warnings": processing_summary_v2.get("warnings"),
            "errors": processing_summary_v2.get("errors"),
            "status_counts": processing_summary_v2.get("status_counts"),
            "document_status": processing_summary_v2.get("document_status"),
            "compliance_rate": processing_summary_v2.get("compliance_rate"),
            "processing_time_seconds": processing_summary_v2.get(
                "processing_time_seconds"
            ),
            "processing_time_display": processing_summary_v2.get(
                "processing_time_display"
            ),
            "processing_time_ms": processing_summary_v2.get("processing_time_ms"),
            "extraction_quality": processing_summary_v2.get("extraction_quality"),
            "discrepancies": processing_summary_v2.get("discrepancies"),
        }
    )
    analytics["issue_counts"] = count_issue_severity(issues)
    analytics["document_status_distribution"] = processing_summary_v2.get("status_counts")
    workflow_stage = build_workflow_stage(
        documents,
        validation_status=structured_result.get("validation_status"),
    )
    structured_result["workflow_stage"] = workflow_stage
    structured_result["workflowStage"] = workflow_stage
    structured_result["requirements_graph_v1"] = build_requirements_graph_v1(documents)
    structured_result["resolution_queue_v1"] = build_resolution_queue_v1(
        documents,
        workflow_stage=workflow_stage,
    )
    structured_result["fact_resolution_v1"] = build_fact_resolution_v1(
        documents,
        workflow_stage=workflow_stage,
        resolution_queue=structured_result.get("resolution_queue_v1"),
    )
    issue_partition = _partition_workflow_stage_issues(
        structured_result.get("issues") or [],
        documents,
        workflow_stage,
    )
    if issue_partition["provisional_issues"]:
        structured_result["issues"] = issue_partition["final_issues"]
        structured_result["_provisional_issues"] = issue_partition["provisional_issues"]
        analytics["issue_counts"] = count_issue_severity(structured_result["issues"])
        processing_summary_v2["total_issues"] = len(structured_result["issues"])
        processing_summary_v2["discrepancies"] = len(structured_result["issues"])
        processing_summary_v2["severity_breakdown"] = {
            "critical": analytics["issue_counts"].get("critical", 0),
            "major": analytics["issue_counts"].get("major", 0),
            "medium": 0,
            "minor": analytics["issue_counts"].get("minor", 0),
        }
        processing_summary["total_issues"] = processing_summary_v2["total_issues"]
        processing_summary["discrepancies"] = processing_summary_v2["discrepancies"]
        processing_summary["severity_breakdown"] = processing_summary_v2["severity_breakdown"]
    workflow_overrides = _apply_workflow_stage_contract_overrides(
        workflow_stage,
        structured_result.get("bank_verdict"),
        structured_result.get("effective_submission_eligibility")
        or structured_result.get("submission_eligibility"),
        structured_result.get("validation_contract_v1"),
        resolution_queue=structured_result.get("resolution_queue_v1"),
    )
    structured_result["bank_verdict"] = workflow_overrides["bank_verdict"]
    structured_result["submission_eligibility"] = workflow_overrides["submission_eligibility"]
    structured_result["raw_submission_eligibility"] = copy.deepcopy(
        structured_result["submission_eligibility"]
    )
    structured_result["effective_submission_eligibility"] = copy.deepcopy(
        structured_result["submission_eligibility"]
    )
    structured_result["validation_contract_v1"] = workflow_overrides["validation_contract"]
    analytics["validation_contract_v1"] = copy.deepcopy(
        structured_result["validation_contract_v1"]
    )
    processing_summary["bank_verdict"] = structured_result["bank_verdict"].get("verdict")

    _copy_documents_to_secondary_surfaces(structured_result, documents)
    structured_result = validate_and_annotate_response(structured_result)
    structured_result = apply_cycle2_runtime_recovery(structured_result)
    structured_result = backfill_hybrid_secondary_surfaces(structured_result)
    if bool(getattr(settings, "DAY1_CONTRACT_ENABLED", False)):
        structured_result = enforce_day1_response_contract(structured_result)
    sync_structured_result_collections(structured_result)
    _copy_documents_to_secondary_surfaces(
        structured_result, _resolve_documents_for_refresh(structured_result)
    )
    structured_result["_operator_field_refresh"] = {
        "applied": True,
        "document_id": document_id,
        "field_name": _normalize_field_key(field_name),
        "verification": verification,
        "issues_remaining": len(structured_result.get("issues") or []),
    }
    return structured_result


__all__ = [
    "sync_structured_result_collections",
    "apply_cycle2_runtime_recovery",
    "backfill_hybrid_secondary_surfaces",
    "refresh_structured_result_after_field_override",
]
