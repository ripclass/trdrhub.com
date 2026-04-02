"""
Response Shaping Module

Helpers for assembling response summaries and timelines.
Extracted from validate.py to preserve behavior.
"""

import os
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.services.facts import materialize_document_fact_graphs_v1 as _materialize_document_fact_graphs_v1
from app.services.requirements import (
    materialize_document_requirements_graphs_v1 as _materialize_document_requirements_graphs_v1,
    resolve_case_requirements_graph_v1 as _resolve_case_requirements_graph_v1,
)
from app.services.resolution import build_resolution_queue_v1 as _build_resolution_queue_payload

from .utilities import format_duration, normalize_issue_severity


EXPOSURE_DIAGNOSTICS_V1_ENV = "LCCOPILOT_EXPOSURE_DIAGNOSTICS_V1_ENABLED"
_MAX_STAGE_ATTEMPTS = 8
_MAX_REASON_CODES = 24
_MAX_STAGE_SCORE_STAGES = 8
_MAX_STAGE_SCORE_KEYS = 8
_SAFE_REASON_CODE_RE = re.compile(r"^[A-Z0-9_]{2,64}$")


def exposure_diagnostics_v1_enabled() -> bool:
    raw = str(os.getenv(EXPOSURE_DIAGNOSTICS_V1_ENV, "1") or "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _sanitize_reason_codes(values: Optional[List[Any]]) -> List[str]:
    codes: List[str] = []
    for value in values or []:
        text = str(value or "").strip()
        if not text:
            continue
        if _SAFE_REASON_CODE_RE.fullmatch(text):
            if text not in codes:
                codes.append(text)
        if len(codes) >= _MAX_REASON_CODES:
            break
    return codes


def _normalize_stage_scores(value: Any) -> Dict[str, Dict[str, float]]:
    if not isinstance(value, dict):
        return {}
    normalized: Dict[str, Dict[str, float]] = {}
    for stage_name in list(value.keys())[:_MAX_STAGE_SCORE_STAGES]:
        stage_payload = value.get(stage_name)
        if not isinstance(stage_payload, dict):
            continue
        score_map: Dict[str, float] = {}
        for key in list(stage_payload.keys())[:_MAX_STAGE_SCORE_KEYS]:
            score_value = stage_payload.get(key)
            if isinstance(score_value, bool):
                score_map[str(key)] = 1.0 if score_value else 0.0
            elif isinstance(score_value, (int, float)):
                score_map[str(key)] = round(float(score_value), 4)
        normalized[str(stage_name)] = score_map
    return normalized


def _extract_stage_error_code(value: Any) -> Optional[str]:
    entries = value if isinstance(value, list) else [value]
    codes = _sanitize_reason_codes(entries)
    return codes[0] if codes else None


def build_extraction_debug(document: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not exposure_diagnostics_v1_enabled():
        return None
    if not isinstance(document, dict):
        return None

    artifacts = (
        document.get("extraction_artifacts_v1")
        if isinstance(document.get("extraction_artifacts_v1"), dict)
        else {}
    )
    critical_field_states = (
        document.get("critical_field_states")
        if isinstance(document.get("critical_field_states"), dict)
        else document.get("criticalFieldStates")
        if isinstance(document.get("criticalFieldStates"), dict)
        else {}
    )
    review_reasons = document.get("review_reasons") or document.get("reviewReasons") or []
    if not artifacts and not critical_field_states and not review_reasons:
        return None

    attempted_stages = artifacts.get("attempted_stages") if isinstance(artifacts.get("attempted_stages"), list) else []
    stage_errors = artifacts.get("stage_errors") if isinstance(artifacts.get("stage_errors"), dict) else {}
    text_length_by_stage = artifacts.get("text_length_by_stage") if isinstance(artifacts.get("text_length_by_stage"), dict) else {}
    provider_attempts = artifacts.get("provider_attempts") if isinstance(artifacts.get("provider_attempts"), list) else []

    stage_attempts: List[Dict[str, Any]] = []
    if provider_attempts:
        for entry in provider_attempts[:_MAX_STAGE_ATTEMPTS]:
            if not isinstance(entry, dict):
                continue
            stage_attempts.append(
                {
                    "stage": str(entry.get("stage") or entry.get("provider") or "ocr_provider_primary"),
                    "provider": str(entry.get("provider") or "") or None,
                    "text_length": int(entry.get("text_len") or entry.get("text_length") or 0),
                    "error_code": _extract_stage_error_code(entry.get("error_code") or entry.get("error")),
                    "input_mime": str(entry.get("input_mime") or "") or None,
                    "normalized_mime": str(entry.get("normalized_mime") or "") or None,
                    "retry_used": bool(entry.get("retry_used")),
                }
            )
    else:
        for stage_name in attempted_stages[:_MAX_STAGE_ATTEMPTS]:
            stage_attempts.append(
                {
                    "stage": str(stage_name),
                    "text_length": int(text_length_by_stage.get(stage_name) or 0),
                    "error_code": _extract_stage_error_code(stage_errors.get(stage_name)),
                }
            )

    selected_stage = artifacts.get("selected_stage") or artifacts.get("final_stage")
    if not stage_attempts and selected_stage:
        stage_attempts.append(
            {
                "stage": str(selected_stage),
                "text_length": int(artifacts.get("final_text_length") or 0),
                "error_code": _extract_stage_error_code(artifacts.get("error_code")),
            }
        )

    found_fields = sum(1 for state in critical_field_states.values() if state == "found")
    total_fields = len(critical_field_states)
    coverage = round(found_fields / total_fields, 3) if total_fields else None
    reason_codes = _sanitize_reason_codes(
        list(artifacts.get("canonical_reason_codes") or [])
        + list(artifacts.get("reason_codes") or [])
        + list(review_reasons or [])
    )

    return {
        "selected_stage": str(selected_stage) if selected_stage else None,
        "selected_stage_rationale": artifacts.get("stage_selection_rationale") if isinstance(artifacts.get("stage_selection_rationale"), dict) else None,
        "stage_scores": _normalize_stage_scores(artifacts.get("stage_scores")),
        "stage_attempts": stage_attempts,
        "critical_field_states": dict(critical_field_states),
        "reason_codes": reason_codes,
        "coverage": coverage,
    }


def _uses_fact_resolution_contract(document: Dict[str, Any]) -> bool:
    fact_graph = document.get("fact_graph_v1") or document.get("factGraphV1")
    return isinstance(fact_graph, dict) and bool(fact_graph)


def _is_legacy_extraction_review_reason(reason: Any) -> bool:
    text = str(reason or "").strip()
    if not text:
        return False
    upper = text.upper()
    lower = text.lower()
    if upper in {
        "FIELD_NOT_FOUND",
        "FORMAT_INVALID",
        "EVIDENCE_MISSING",
        "LOW_CONFIDENCE",
        "LOW_CONFIDENCE_CRITICAL",
        "CROSS_FIELD_CONFLICT",
        "OCR_EMPTY_RESULT",
        "OCR_TIMEOUT",
        "OCR_AUTH_ERROR",
        "OCR_UNSUPPORTED_FORMAT",
        "PARSE_FAILED",
    }:
        return True
    if lower == "review_required":
        return True
    if lower.startswith("missing:"):
        return True
    if lower.endswith("_missing_critical_fields"):
        return True
    if lower.startswith("critical_") and (
        lower.endswith("_missing")
        or lower.endswith("_parse_failed")
        or "low_confidence" in lower
    ):
        return True
    if lower.startswith("cross_field_"):
        return True
    if "parse_failed" in lower or "low_confidence" in lower or "sparse_text" in lower:
        return True
    return False


def _has_runtime_extraction_review_signal(document: Dict[str, Any]) -> bool:
    if not isinstance(document, dict):
        return False

    if bool(document.get("review_required") or document.get("reviewRequired")):
        return True

    extraction_status = str(
        document.get("extraction_status")
        or document.get("extractionStatus")
        or document.get("status")
        or ""
    ).strip().lower()
    critical_field_states = (
        document.get("critical_field_states")
        if isinstance(document.get("critical_field_states"), dict)
        else document.get("criticalFieldStates")
        if isinstance(document.get("criticalFieldStates"), dict)
        else {}
    )
    missing_critical_fields = any(
        str(state or "").strip().lower() == "missing"
        for state in critical_field_states.values()
    )

    artifacts = (
        document.get("extraction_artifacts_v1")
        if isinstance(document.get("extraction_artifacts_v1"), dict)
        else document.get("extractionArtifactsV1")
        if isinstance(document.get("extractionArtifactsV1"), dict)
        else {}
    )
    selected_stage = str(
        artifacts.get("selected_stage") or artifacts.get("final_stage") or ""
    ).strip().lower()
    degraded_selection_stages = {"binary_metadata_scrape"}
    severe_reason_codes = {
        "field_not_found",
        "ocr_auth_error",
        "ocr_auth_failure",
        "ocr_empty_result",
        "ocr_provider_unavailable",
        "parse_failed",
        "parser_empty_output",
        "low_confidence",
        "low_confidence_critical",
    }
    reason_codes = {
        str(reason or "").strip().lower()
        for key in ("canonical_reason_codes", "reason_codes", "review_reasons", "reviewReasons")
        for reason in (artifacts.get(key) or [])
        if str(reason or "").strip()
    }

    return bool(
        reason_codes.intersection(severe_reason_codes)
        or selected_stage in degraded_selection_stages
        or (
            missing_critical_fields
            and extraction_status in {"partial", "warning", "error", "parse_failed", "text_only", "unknown"}
        )
    )


def sanitize_public_document_contract_v1(document: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(document, dict):
        return document

    sanitized = dict(document)
    if not _uses_fact_resolution_contract(sanitized):
        return sanitized

    raw_review_reasons = sanitized.get("review_reasons") or sanitized.get("reviewReasons") or []
    review_reasons = [
        str(reason).strip()
        for reason in raw_review_reasons
        if str(reason or "").strip() and not _is_legacy_extraction_review_reason(reason)
    ]
    review_required = (
        bool(review_reasons)
        and bool(sanitized.get("review_required") or sanitized.get("reviewRequired"))
    ) or _has_runtime_extraction_review_signal(sanitized)

    sanitized["missing_required_fields"] = []
    sanitized["missingRequiredFields"] = []
    sanitized["parse_complete"] = None
    sanitized["parseComplete"] = None
    sanitized["parse_completeness"] = None
    sanitized["parseCompleteness"] = None
    sanitized["required_fields_found"] = None
    sanitized["requiredFieldsFound"] = None
    sanitized["required_fields_total"] = None
    sanitized["requiredFieldsTotal"] = None
    sanitized["review_required"] = review_required
    sanitized["reviewRequired"] = review_required
    sanitized["review_reasons"] = review_reasons
    sanitized["reviewReasons"] = list(review_reasons)
    return sanitized


def attach_extraction_observability(documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not exposure_diagnostics_v1_enabled():
        return documents

    for document in documents or []:
        if not isinstance(document, dict):
            continue
        extraction_debug = build_extraction_debug(document)
        if not extraction_debug:
            continue
        document["extraction_debug"] = extraction_debug
        document["extractionDebug"] = extraction_debug
    return documents


def build_extraction_diagnostics(
    documents: List[Dict[str, Any]],
    extraction_core_bundle: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    if not exposure_diagnostics_v1_enabled():
        return None

    unresolved_fields: List[str] = []
    failure_reasons: List[str] = []
    coverage_values: List[float] = []
    critical_fields_evaluated = 0
    critical_fields_unresolved = 0
    review_required_documents = 0

    for document in documents or []:
        if not isinstance(document, dict):
            continue
        extraction_debug = document.get("extraction_debug") if isinstance(document.get("extraction_debug"), dict) else build_extraction_debug(document)
        if not extraction_debug:
            continue
        if bool(document.get("review_required") or document.get("reviewRequired")):
            review_required_documents += 1
        critical_states = extraction_debug.get("critical_field_states") if isinstance(extraction_debug.get("critical_field_states"), dict) else {}
        critical_fields_evaluated += len(critical_states)
        for field_name, state in critical_states.items():
            if state != "found":
                critical_fields_unresolved += 1
                unresolved_fields.append(str(field_name))
        coverage = extraction_debug.get("coverage")
        if isinstance(coverage, (int, float)):
            coverage_values.append(float(coverage))
        failure_reasons.extend(extraction_debug.get("reason_codes") or [])

    if isinstance(extraction_core_bundle, dict):
        meta = extraction_core_bundle.get("meta") if isinstance(extraction_core_bundle.get("meta"), dict) else {}
        if isinstance(meta.get("review_required_count"), int):
            review_required_documents = int(meta.get("review_required_count"))

    return {
        "version": "extraction_diagnostics_v1",
        "unresolved_critical_fields": sorted(dict.fromkeys(unresolved_fields))[:50],
        "failure_reasons": _sanitize_reason_codes(failure_reasons),
        "review_gate_inputs": {
            "documents_evaluated": len([doc for doc in documents or [] if isinstance(doc, dict)]),
            "review_required_documents": review_required_documents,
            "critical_fields_evaluated": critical_fields_evaluated,
            "critical_fields_unresolved": critical_fields_unresolved,
            "average_coverage": round(sum(coverage_values) / len(coverage_values), 3) if coverage_values else None,
        },
    }


def build_workflow_stage(
    documents: List[Dict[str, Any]],
    *,
    validation_status: Optional[str] = None,
) -> Dict[str, Any]:
    normalized_documents = [doc for doc in (documents or []) if isinstance(doc, dict)]
    if not normalized_documents:
        return {
            "stage": "upload",
            "provisional_validation": True,
            "ready_for_final_validation": False,
            "unresolved_documents": 0,
            "unresolved_fields": 0,
            "summary": "Upload the LC and supporting documents to begin extraction and validation.",
        }

    materialize_document_fact_graphs_v1(normalized_documents)

    queue_unresolved_documents = 0
    queue_unresolved_fields = 0
    try:
        queue_payload = _build_resolution_queue_payload(normalized_documents)
        queue_summary = (
            queue_payload.get("summary")
            if isinstance(queue_payload, dict) and isinstance(queue_payload.get("summary"), dict)
            else {}
        )
        queue_documents = queue_summary.get("unresolved_documents")
        if isinstance(queue_documents, int):
            queue_unresolved_documents = max(0, queue_documents)
        queue_total_items = queue_summary.get("total_items")
        if isinstance(queue_total_items, int):
            queue_unresolved_fields = max(0, queue_total_items)
    except Exception:
        queue_unresolved_documents = 0
        queue_unresolved_fields = 0

    unresolved_documents = queue_unresolved_documents
    unresolved_fields = queue_unresolved_fields
    lane_counts: Dict[str, int] = {}
    for document in normalized_documents:
        extraction_lane = str(
            document.get("extraction_lane")
            or document.get("extractionLane")
            or "unknown"
        ).strip() or "unknown"
        lane_counts[extraction_lane] = lane_counts.get(extraction_lane, 0) + 1

        document_fact_graph = document.get("fact_graph_v1") or document.get("factGraphV1")
        if isinstance(document_fact_graph, dict):
            continue

        extraction_resolution = (
            document.get("extraction_resolution")
            if isinstance(document.get("extraction_resolution"), dict)
            else document.get("extractionResolution")
            if isinstance(document.get("extractionResolution"), dict)
            else {}
        )
        if not extraction_resolution:
            continue

        required = bool(extraction_resolution.get("required"))
        unresolved_count = extraction_resolution.get("unresolved_count")
        if not isinstance(unresolved_count, int):
            unresolved_count = extraction_resolution.get("unresolvedCount")
        if not isinstance(unresolved_count, int):
            fields = extraction_resolution.get("fields")
            unresolved_count = len(fields) if isinstance(fields, list) else 0

        if required or unresolved_count > 0:
            unresolved_documents += 1
            unresolved_fields += max(0, unresolved_count)

    if unresolved_documents > 0 or unresolved_fields > 0:
        summary = (
            f"{unresolved_documents} document{'s' if unresolved_documents != 1 else ''} "
            f"still need{'' if unresolved_documents != 1 else 's'} "
            f"{unresolved_fields} field{'s' if unresolved_fields != 1 else ''} confirmed "
            "before validation should be treated as final."
        )
        stage = "extraction_resolution"
    else:
        status_text = str(validation_status or "").strip().lower()
        if status_text in {"blocked", "review", "partial"}:
            summary = (
                "Extraction is sufficiently resolved. Remaining items belong to documentary "
                "validation or policy review, not parser uncertainty."
            )
        else:
            summary = (
                "Extraction is sufficiently resolved. Validation findings reflect the current "
                "confirmed document set."
            )
        stage = "validation_results"

    return {
        "stage": stage,
        "provisional_validation": stage != "validation_results",
        "ready_for_final_validation": stage == "validation_results",
        "unresolved_documents": unresolved_documents,
        "unresolved_fields": unresolved_fields,
        "document_lane_counts": lane_counts,
        "summary": summary,
    }


def summarize_document_statuses(documents: List[Dict[str, Any]]) -> Dict[str, int]:
    counts = {"success": 0, "warning": 0, "error": 0}
    for doc in documents:
        status = (doc.get("status") or "success").lower()
        if status not in counts:
            counts[status] = 0
        counts[status] += 1
    return counts


def build_processing_summary(
    document_summaries: List[Dict[str, Any]],
    processing_seconds: float,
    total_discrepancies: int,
) -> Dict[str, Any]:
    status_counts = summarize_document_statuses(document_summaries)
    total_docs = len(document_summaries)
    verified = status_counts.get("success", 0)
    warnings = status_counts.get("warning", 0)
    errors = status_counts.get("error", 0)
    compliance_rate = 0
    if total_docs:
        compliance_rate = max(0, round((verified / total_docs) * 100))

    # Calculate extraction quality from OCR confidence
    confidences = [
        doc.get("ocrConfidence")
        for doc in document_summaries
        if isinstance(doc.get("ocrConfidence"), (int, float))
    ]
    if confidences:
        extraction_quality = round(sum(confidences) / len(confidences) * 100)
    else:
        # Fallback: estimate quality based on status distribution
        extraction_quality = max(
            80,
            100 - warnings * 5 - errors * 10
        )

    # Convert processing time to milliseconds
    processing_time_ms = round(processing_seconds * 1000)

    return {
        # --- Document counts ---
        "documents": total_docs,  # backward compatibility
        "documents_found": total_docs,  # Frontend expects this field
        "total_documents": total_docs,  # Explicit field for frontend

        # --- Validation/Extraction ---
        "verified": verified,
        "warnings": warnings,
        "errors": errors,
        "successful_extractions": verified,  # Frontend checks this field
        "failed_extractions": errors,  # Frontend checks this field
        "compliance_rate": compliance_rate,
        "processing_time_seconds": round(processing_seconds, 2),
        "processing_time_display": format_duration(processing_seconds),
        "processing_time_ms": processing_time_ms,  # NEW — milliseconds version
        "extraction_quality": extraction_quality,  # NEW — OCR quality score (0-100)
        "discrepancies": total_discrepancies,
        "status_counts": status_counts,
        # FIX: Also send as document_status for frontend SummaryStrip compatibility
        "document_status": status_counts,
    }


def build_bank_submission_verdict(
    critical_count: int,
    major_count: int,
    minor_count: int,
    compliance_score: float,
    all_issues: List[Any],
) -> Dict[str, Any]:
    """
    Build a bank submission verdict with GO/NO-GO recommendation.

    This helps exporters understand if their documents are ready
    for bank submission or what actions are required first.
    """
    # Determine verdict
    if critical_count > 0:
        verdict = "REJECT"
        verdict_color = "red"
        verdict_message = "Documents will be REJECTED by bank"
        recommendation = "Do NOT submit to bank until critical issues are resolved."
    elif major_count > 2:
        verdict = "HOLD"
        verdict_color = "orange"
        verdict_message = "High risk of discrepancy notice"
        recommendation = "Consider resolving major issues before submission to avoid discrepancy fees."
    elif major_count > 0:
        verdict = "CAUTION"
        verdict_color = "yellow"
        verdict_message = "Minor corrections recommended"
        recommendation = "Documents may be accepted with discrepancy notice. Consider corrections."
    else:
        verdict = "SUBMIT"
        verdict_color = "green"
        verdict_message = "Documents appear compliant"
        recommendation = "Documents are ready for bank submission."

    # Build action items from critical and major issues
    def _issue_value(issue: Any, *keys: str) -> Any:
        if isinstance(issue, dict):
            for key in keys:
                if key in issue and issue.get(key) is not None:
                    return issue.get(key)
            return None
        for key in keys:
            value = getattr(issue, key, None)
            if value is not None:
                return value
        return None

    def _first_text(items: Any, *, exclude_lc: bool = False) -> Optional[str]:
        if isinstance(items, str):
            candidate = items.strip()
            if candidate and (not exclude_lc or candidate.lower() != "letter of credit"):
                return candidate
            return None
        if isinstance(items, list):
            for item in items:
                candidate = str(item or "").strip()
                if candidate and (not exclude_lc or candidate.lower() != "letter of credit"):
                    return candidate
        return None

    action_items = []
    for issue in all_issues:
        if hasattr(issue, 'severity'):
            severity = issue.severity.value if hasattr(issue.severity, 'value') else str(issue.severity)
        elif isinstance(issue, dict):
            severity = issue.get("severity", "")
        else:
            continue

        if severity in ["critical", "major"]:
            title = _issue_value(issue, "title", "message") or "Unknown issue"
            action = _issue_value(issue, "suggestion", "suggested_fix") or "Review and correct"
            requirement_source = str(_issue_value(issue, "requirement_source") or "").strip().lower()
            requirement_kind = str(_issue_value(issue, "requirement_kind") or "").strip().lower()
            requirement_text = str(_issue_value(issue, "requirement_text") or "").strip()
            affected_doc = _first_text(
                _issue_value(issue, "affected_document_names", "affected_documents"),
                exclude_lc=True,
            )
            related_doc = _first_text(
                _issue_value(issue, "document_names", "documents", "document_name", "document_type"),
                exclude_lc=True,
            )
            doc_label = affected_doc or related_doc or "the document"

            if requirement_source == "requirements_graph_v1" and requirement_kind == "document_exact_wording":
                title = f"Add LC-required statement to {doc_label}"
                if not str(action).strip():
                    if requirement_text:
                        action = (
                            f"Update {doc_label} to include the exact LC-required statement "
                            f"'{requirement_text}' or seek an LC amendment before presentation."
                        )
                    else:
                        action = (
                            f"Update {doc_label} to include the LC-required statement "
                            "or seek an LC amendment before presentation."
                        )

            action_items.append({
                "priority": "critical" if severity == "critical" else "high",
                "issue": title,
                "action": action,
            })

    # Calculate estimated fee if discrepant
    discrepancy_fee = 75.00 if (critical_count + major_count) > 0 else 0.00

    return {
        "verdict": verdict,
        "verdict_color": verdict_color,
        "verdict_message": verdict_message,
        "recommendation": recommendation,
        "can_submit": verdict in ["SUBMIT", "CAUTION"],
        "will_be_rejected": verdict == "REJECT",
        "estimated_discrepancy_fee": discrepancy_fee,
        "issue_summary": {
            "critical": critical_count,
            "major": major_count,
            "minor": minor_count,
            "total": critical_count + major_count + minor_count,
        },
        "action_items": action_items[:5],  # Top 5 action items
        "action_items_count": len(action_items),
    }


def build_processing_timeline(
    document_summaries: List[Dict[str, Any]],
    processing_summary: Dict[str, Any],
) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    doc_count = len(document_summaries)
    now = datetime.utcnow()
    stages = [
        ("Documents Uploaded", "success", f"{doc_count} document(s) received"),
        ("LC Terms Extracted", "success", "Structured LC context generated"),
        ("Document Cross-Check", "success", "Validated trade docs against LC terms"),
        (
            "Customs Pack Generated",
            "warning" if processing_summary.get("warnings") else "success",
            "Bundle prepared for customs clearance",
        ),
    ]

    for index, (title, status, description) in enumerate(stages):
        events.append(
            {
                "title": title,
                "status": status,
                "description": description,
                "timestamp": (now - timedelta(seconds=max(5, (len(stages) - index) * 5))).isoformat() + "Z",
            }
        )
    return events


def compose_processing_summary(
    documents: List[Dict[str, Any]],
    issues: List[Dict[str, Any]],
    severity_counts: Optional[Dict[str, int]] = None,
) -> Dict[str, Any]:
    total_docs = len(documents)
    successful = sum(
        1 for doc in documents if (doc.get("extraction_status") or "").lower() == "success"
    )
    failed = total_docs - successful
    severity_breakdown = severity_counts or count_issue_severity(issues)

    return {
        "total_documents": total_docs,
        "successful_extractions": successful,
        "failed_extractions": failed,
        "total_issues": len(issues),
        "severity_breakdown": severity_breakdown,
    }


def count_issue_severity(issues: List[Dict[str, Any]]) -> Dict[str, int]:
    counts = {"critical": 0, "major": 0, "medium": 0, "minor": 0}
    for issue in issues:
        severity = normalize_issue_severity(issue.get("severity"))
        if severity in counts:
            counts[severity] += 1
        else:
            counts["minor"] += 1
    return counts


# =============================================================================
# Contract Builders (Phase A)
# =============================================================================

def _normalize_doc_status(
    value: Optional[str],
    extraction_status: Optional[str],
    parse_complete: Optional[bool] = None,
    *,
    ignore_parse_complete: bool = False,
) -> str:
    status = (value or "").lower().strip()
    if status in {"success", "warning", "error"}:
        if not ignore_parse_complete and status == "success" and parse_complete is False:
            return "warning"
        return status
    extraction = (extraction_status or "").lower().strip()
    if extraction in {"success", "completed"}:
        return "success" if ignore_parse_complete or parse_complete is not False else "warning"
    if extraction in {"failed", "error", "empty"}:
        return "error"
    if extraction in {"partial", "text_only", "pending", "unknown", "parse_failed"}:
        return "warning"
    return "warning"


def build_document_extraction_v1(documents: List[Dict[str, Any]]) -> Dict[str, Any]:
    materialize_document_requirements_graphs_v1(documents)
    normalized_docs: List[Dict[str, Any]] = []
    for doc in documents or []:
        extraction_status = (
            doc.get("extractionStatus")
            or doc.get("extraction_status")
            or doc.get("status")
            or "unknown"
        )
        parse_complete = doc.get("parse_complete")
        if parse_complete is None:
            parse_complete = doc.get("parseComplete")
        if parse_complete is not None:
            parse_complete = bool(parse_complete)
        uses_fact_resolution = _uses_fact_resolution_contract(doc)
        public_document = sanitize_public_document_contract_v1(doc)

        status = _normalize_doc_status(
            doc.get("status"),
            extraction_status,
            parse_complete,
            ignore_parse_complete=uses_fact_resolution,
        )
        normalized_docs.append(
            {
                "document_id": doc.get("id") or doc.get("document_id") or doc.get("documentId"),
                "document_type": doc.get("documentType") or doc.get("document_type") or doc.get("type"),
                "filename": doc.get("name") or doc.get("filename"),
                "status": status,
                "extraction_status": extraction_status,
                "extracted_fields": doc.get("extractedFields") or doc.get("extracted_fields") or {},
                "field_details": doc.get("field_details") or doc.get("fieldDetails") or doc.get("_field_details") or {},
                "fact_graph_v1": doc.get("fact_graph_v1") or doc.get("factGraphV1"),
                "factGraphV1": doc.get("factGraphV1") or doc.get("fact_graph_v1"),
                "requirements_graph_v1": doc.get("requirements_graph_v1") or doc.get("requirementsGraphV1"),
                "requirementsGraphV1": doc.get("requirementsGraphV1") or doc.get("requirements_graph_v1"),
                "extraction_lane": doc.get("extraction_lane") or doc.get("extractionLane"),
                "extractionLane": doc.get("extractionLane") or doc.get("extraction_lane"),
                "extraction_resolution": doc.get("extraction_resolution") or doc.get("extractionResolution"),
                "extractionResolution": doc.get("extractionResolution") or doc.get("extraction_resolution"),
                "issues_count": doc.get("discrepancyCount")
                or doc.get("issues_count")
                or doc.get("issuesCount")
                or 0,
                "ocr_confidence": doc.get("ocrConfidence") or doc.get("ocr_confidence"),
                "parse_complete": public_document.get("parse_complete"),
                "parse_completeness": public_document.get("parse_completeness"),
                "missing_required_fields": public_document.get("missing_required_fields") or [],
                "required_fields_found": public_document.get("required_fields_found"),
                "required_fields_total": public_document.get("required_fields_total"),
                "review_required": bool(public_document.get("review_required") or public_document.get("reviewRequired")),
                "review_reasons": public_document.get("review_reasons") or public_document.get("reviewReasons") or [],
                "critical_field_states": doc.get("critical_field_states") or doc.get("criticalFieldStates") or {},
                "extraction_artifacts_v1": doc.get("extraction_artifacts_v1") or doc.get("extractionArtifactsV1") or {},
                "extraction_debug": doc.get("extraction_debug") or doc.get("extractionDebug"),
                "day1_runtime": doc.get("day1_runtime") if isinstance(doc.get("day1_runtime"), dict) else {},
            }
        )

    status_counts = summarize_document_statuses(
        [{"status": d.get("status")} for d in normalized_docs]
    )

    return {
        "version": "document_extraction_v1",
        "documents": normalized_docs,
        "summary": {
            "total_documents": len(normalized_docs),
            "status_counts": status_counts,
        },
    }


def materialize_document_fact_graphs_v1(documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return _materialize_document_fact_graphs_v1(documents)


def materialize_document_requirements_graphs_v1(documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return _materialize_document_requirements_graphs_v1(documents)


def build_requirements_graph_v1(documents: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    materialize_document_requirements_graphs_v1(documents)
    return _resolve_case_requirements_graph_v1(documents)


def _empty_resolution_queue_v1() -> Dict[str, Any]:
    return {
        "version": "resolution_queue_v1",
        "items": [],
        "summary": {
            "total_items": 0,
            "user_resolvable_items": 0,
            "unresolved_documents": 0,
            "document_counts": {},
        },
    }


def _normalize_resolution_queue_for_workflow_stage(
    queue_payload: Optional[Dict[str, Any]],
    workflow_stage: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    stage = str((workflow_stage or {}).get("stage") or "").strip().lower()
    if stage == "validation_results":
        return _empty_resolution_queue_v1()
    if isinstance(queue_payload, dict):
        return queue_payload
    return _empty_resolution_queue_v1()


def build_resolution_queue_v1(
    documents: List[Dict[str, Any]],
    *,
    workflow_stage: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    materialize_document_fact_graphs_v1(documents)
    materialize_document_requirements_graphs_v1(documents)
    return _normalize_resolution_queue_for_workflow_stage(
        _build_resolution_queue_payload(documents),
        workflow_stage,
    )


def build_fact_resolution_v1(
    documents: List[Dict[str, Any]],
    *,
    workflow_stage: Optional[Dict[str, Any]] = None,
    resolution_queue: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    materialize_document_fact_graphs_v1(documents)
    materialize_document_requirements_graphs_v1(documents)
    effective_workflow_stage = (
        workflow_stage
        if isinstance(workflow_stage, dict)
        else build_workflow_stage(documents)
    )
    queue_payload = _normalize_resolution_queue_for_workflow_stage(
        (
            resolution_queue
            if isinstance(resolution_queue, dict)
            else build_resolution_queue_v1(
                documents,
                workflow_stage=effective_workflow_stage,
            )
        ),
        effective_workflow_stage,
    )

    queue_items = (
        queue_payload.get("items")
        if isinstance(queue_payload.get("items"), list)
        else []
    )
    queue_by_document_id: Dict[str, List[Dict[str, Any]]] = {}
    queue_by_filename: Dict[str, List[Dict[str, Any]]] = {}
    for item in queue_items:
        if not isinstance(item, dict):
            continue
        document_id = str(item.get("document_id") or "").strip()
        filename = str(item.get("filename") or "").strip().lower()
        if document_id:
            queue_by_document_id.setdefault(document_id, []).append(item)
        if filename:
            queue_by_filename.setdefault(filename, []).append(item)

    fact_resolution_document_types = {
        "letter_of_credit",
        "swift_message",
        "lc_application",
        "bank_guarantee",
        "standby_letter_of_credit",
        "commercial_invoice",
        "proforma_invoice",
        "draft_bill_of_exchange",
        "promissory_note",
        "payment_receipt",
        "debit_note",
        "credit_note",
        "bill_of_lading",
        "ocean_bill_of_lading",
        "charter_party_bill_of_lading",
        "house_bill_of_lading",
        "master_bill_of_lading",
        "sea_waybill",
        "air_waybill",
        "multimodal_transport_document",
        "combined_transport_document",
        "railway_consignment_note",
        "road_transport_document",
        "forwarders_certificate_of_receipt",
        "forwarder_certificate_of_receipt",
        "delivery_order",
        "mates_receipt",
        "shipping_company_certificate",
        "warehouse_receipt",
        "cargo_manifest",
        "courier_or_post_receipt_or_certificate_of_posting",
        "packing_list",
        "certificate_of_origin",
        "gsp_form_a",
        "eur1_movement_certificate",
        "customs_declaration",
        "export_license",
        "import_license",
        "phytosanitary_certificate",
        "fumigation_certificate",
        "health_certificate",
        "veterinary_certificate",
        "sanitary_certificate",
        "cites_permit",
        "radiation_certificate",
        "insurance_certificate",
        "insurance_policy",
        "beneficiary_certificate",
        "beneficiary_statement",
        "manufacturer_certificate",
        "manufacturers_certificate",
        "conformity_certificate",
        "certificate_of_conformity",
        "non_manipulation_certificate",
        "halal_certificate",
        "kosher_certificate",
        "organic_certificate",
        "inspection_certificate",
        "pre_shipment_inspection",
        "quality_certificate",
        "weight_certificate",
        "weight_list",
        "measurement_certificate",
        "analysis_certificate",
        "lab_test_report",
        "sgs_certificate",
        "bureau_veritas_certificate",
        "intertek_certificate",
    }
    contract_documents: List[Dict[str, Any]] = []
    unresolved_documents = 0
    total_items = 0
    user_resolvable_items = 0

    for document in documents or []:
        if not isinstance(document, dict):
            continue
        document_type = str(
            document.get("document_type")
            or document.get("documentType")
            or document.get("type")
            or ""
        ).strip().lower()
        if document_type not in fact_resolution_document_types:
            continue

        document_id = str(
            document.get("document_id")
            or document.get("documentId")
            or document.get("id")
            or ""
        ).strip()
        filename = str(document.get("filename") or document.get("name") or "").strip()
        document_fact_graph = document.get("fact_graph_v1") or document.get("factGraphV1")
        resolution_items = list(queue_by_document_id.get(document_id) or [])
        if not resolution_items and filename:
            resolution_items = list(queue_by_filename.get(filename.lower()) or [])
        if (
            document_type in {
                "letter_of_credit",
                "swift_message",
                "lc_application",
                "bank_guarantee",
                "standby_letter_of_credit",
            }
            and not isinstance(document_fact_graph, dict)
            and not resolution_items
        ):
            continue

        unresolved_count = len(resolution_items)
        resolution_required = unresolved_count > 0
        if resolution_required:
            unresolved_documents += 1
            total_items += unresolved_count
            user_resolvable_items += sum(
                1
                for item in resolution_items
                if bool(item.get("resolvable_by_user", True))
            )

        contract_documents.append(
            {
                "document_id": document_id,
                "document_type": document_type,
                "filename": filename or None,
                "resolution_required": resolution_required,
                "ready_for_validation": not resolution_required,
                "unresolved_count": unresolved_count,
                "summary": (
                    f"{unresolved_count} field{'s' if unresolved_count != 1 else ''} "
                    "still need confirmation before document validation input is treated as final."
                    if resolution_required
                    else "Document facts required for validation are resolved."
                ),
                "fact_graph_v1": document_fact_graph,
                "requirements_graph_v1": document.get("requirements_graph_v1") or document.get("requirementsGraphV1"),
                "resolution_items": resolution_items,
            }
        )

    return {
        "version": "fact_resolution_v1",
        "workflow_stage": effective_workflow_stage,
        "documents": contract_documents,
        "summary": {
            "total_documents": len(contract_documents),
            "unresolved_documents": unresolved_documents,
            "total_items": total_items,
            "user_resolvable_items": user_resolvable_items,
            "ready_for_validation": unresolved_documents == 0,
        },
    }


def build_issue_provenance_v1(issues: List[Dict[str, Any]]) -> Dict[str, Any]:
    provenance: List[Dict[str, Any]] = []
    for idx, issue in enumerate(issues or []):
        issue_id = str(issue.get("id") or issue.get("rule") or issue.get("rule_id") or f"issue-{idx}")
        ruleset_domain = issue.get("ruleset_domain") or issue.get("rulesetDomain")
        source = issue.get("source")
        if not source and ruleset_domain:
            source = "crossdoc" if "crossdoc" in str(ruleset_domain) else "ruleset"
        if not source:
            source = "unknown"

        document_ids = (
            issue.get("document_ids")
            or issue.get("documentIds")
            or issue.get("document_id")
            or issue.get("documentId")
            or []
        )
        if not isinstance(document_ids, list):
            document_ids = [document_ids]
        document_types = (
            issue.get("document_types")
            or issue.get("documentTypes")
            or issue.get("document_type")
            or issue.get("documentType")
            or []
        )
        if not isinstance(document_types, list):
            document_types = [document_types]
        document_names = (
            issue.get("documents")
            or issue.get("document_names")
            or issue.get("documentNames")
            or issue.get("document")
            or issue.get("document_name")
            or issue.get("documentName")
            or []
        )
        if not isinstance(document_names, list):
            document_names = [document_names]

        provenance_item = {
            "issue_id": issue_id,
            "source": source,
            "ruleset_domain": ruleset_domain,
            "rule": issue.get("rule") or issue.get("rule_id"),
            "severity": issue.get("severity"),
            "document_ids": document_ids,
            "document_types": document_types,
            "document_names": document_names,
        }
        if issue.get("decision_status") is not None:
            provenance_item["decision_status"] = issue.get("decision_status")
        if issue.get("reason_code") is not None:
            provenance_item["reason_code"] = issue.get("reason_code")
        if issue.get("decision") is not None:
            provenance_item["decision"] = issue.get("decision")

        provenance.append(provenance_item)

    return {
        "version": "issue_provenance_v1",
        "total_issues": len(provenance),
        "issues": provenance,
    }


def build_processing_summary_v2(
    processing_summary: Optional[Dict[str, Any]],
    documents: List[Dict[str, Any]],
    issues: List[Dict[str, Any]],
    compliance_rate: Optional[float] = None,
) -> Dict[str, Any]:
    summary = dict(processing_summary or {})

    status_counts = summary.get("status_counts") or summary.get("document_status")
    if not status_counts:
        status_counts = summarize_document_statuses(documents or [])

    if not isinstance(status_counts, dict):
        status_counts = {"success": 0, "warning": 0, "error": 0}

    status_counts = {
        "success": int(status_counts.get("success", 0) or 0),
        "warning": int(status_counts.get("warning", 0) or 0),
        "error": int(status_counts.get("error", 0) or 0),
    }

    sum_counts = status_counts["success"] + status_counts["warning"] + status_counts["error"]

    total_documents = summary.get("total_documents") or summary.get("documents") or len(documents or [])
    if sum_counts > 0:
        total_documents = sum_counts

    verified = status_counts["success"]
    warnings = status_counts["warning"]
    errors = status_counts["error"]

    total_issues = len(issues or [])
    if total_issues == 0:
        total_issues = summary.get("total_issues") or summary.get("discrepancies") or 0

    # Enforce severity parity based on actual issues
    severity_breakdown = count_issue_severity(issues or [])

    compliance = summary.get("compliance_rate")
    if compliance is None and compliance_rate is not None:
        compliance = compliance_rate
    if compliance is None:
        compliance = 0

    return {
        "version": "processing_summary_v2",
        "total_documents": int(total_documents or 0),
        "documents": int(total_documents or 0),
        "documents_found": int(total_documents or 0),
        "verified": int(verified or 0),
        "warnings": int(warnings or 0),
        "errors": int(errors or 0),
        "successful_extractions": int(verified or 0),
        "failed_extractions": int(errors or 0),
        "total_issues": int(total_issues or 0),
        "discrepancies": int(total_issues or 0),
        "severity_breakdown": severity_breakdown,
        "status_counts": status_counts,
        "document_status": status_counts,
        "compliance_rate": int(round(compliance)) if isinstance(compliance, (int, float)) else 0,
        "processing_time_seconds": summary.get("processing_time_seconds"),
        "processing_time_display": summary.get("processing_time_display"),
        "processing_time_ms": summary.get("processing_time_ms"),
        "extraction_quality": summary.get("extraction_quality"),
    }


def build_public_validation_envelope(
    *,
    job_id: str,
    structured_result: Dict[str, Any],
    telemetry: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build the public validation response envelope.

    The canonical truth lives inside structured_result, but the public API also
    mirrors key contract/readiness surfaces at the top level so immediate
    /api/validate and persisted /api/results/{job_id} stay aligned.
    """
    envelope: Dict[str, Any] = {
        "job_id": str(job_id),
        "jobId": str(job_id),
        "structured_result": structured_result,
        "telemetry": telemetry or {},
    }

    if not isinstance(structured_result, dict):
        return envelope

    validation_contract = (
        structured_result.get("validation_contract_v1")
        if isinstance(structured_result.get("validation_contract_v1"), dict)
        else {}
    )
    effective_submission = (
        structured_result.get("effective_submission_eligibility")
        if isinstance(structured_result.get("effective_submission_eligibility"), dict)
        else structured_result.get("submission_eligibility")
        if isinstance(structured_result.get("submission_eligibility"), dict)
        else {}
    )
    raw_submission = (
        structured_result.get("raw_submission_eligibility")
        if isinstance(structured_result.get("raw_submission_eligibility"), dict)
        else None
    )
    bank_verdict = (
        structured_result.get("bank_verdict")
        if isinstance(structured_result.get("bank_verdict"), dict)
        else None
    )

    final_verdict = (
        structured_result.get("final_verdict")
        or validation_contract.get("final_verdict")
    )
    ruleset_verdict = (
        structured_result.get("ruleset_verdict")
        or validation_contract.get("ruleset_verdict")
    )

    if validation_contract:
        envelope["validation_contract_v1"] = validation_contract
    if bank_verdict:
        envelope["bank_verdict"] = bank_verdict
    if effective_submission:
        envelope["submission_eligibility"] = effective_submission
        envelope["effective_submission_eligibility"] = effective_submission
        can_submit = effective_submission.get("can_submit")
        if isinstance(can_submit, bool):
            envelope["submission_can_submit"] = can_submit
        reasons = effective_submission.get("reasons")
        if isinstance(reasons, list):
            envelope["submission_reasons"] = reasons
    if raw_submission:
        envelope["raw_submission_eligibility"] = raw_submission
    if final_verdict:
        envelope["final_verdict"] = final_verdict
    if ruleset_verdict:
        envelope["ruleset_verdict"] = ruleset_verdict

    return envelope
