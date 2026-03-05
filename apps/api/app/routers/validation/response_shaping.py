"""
Response Shaping Module

Helpers for assembling response summaries and timelines.
Extracted from validate.py to preserve behavior.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .utilities import format_duration, normalize_issue_severity


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
    action_items = []
    for issue in all_issues:
        if hasattr(issue, 'severity'):
            severity = issue.severity.value if hasattr(issue.severity, 'value') else str(issue.severity)
        elif isinstance(issue, dict):
            severity = issue.get("severity", "")
        else:
            continue

        if severity in ["critical", "major"]:
            if hasattr(issue, 'title'):
                title = issue.title
            elif isinstance(issue, dict):
                title = issue.get("title", issue.get("message", "Unknown issue"))
            else:
                continue

            if hasattr(issue, 'suggestion'):
                action = issue.suggestion
            elif isinstance(issue, dict):
                action = issue.get("suggestion", issue.get("suggested_fix", "Review and correct"))
            else:
                action = "Review and correct"

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

def _normalize_doc_status(value: Optional[str], extraction_status: Optional[str]) -> str:
    status = (value or "").lower().strip()
    if status in {"success", "warning", "error"}:
        return status
    extraction = (extraction_status or "").lower().strip()
    if extraction in {"success", "completed"}:
        return "success"
    if extraction in {"failed", "error", "empty"}:
        return "error"
    if extraction in {"partial", "text_only", "pending", "unknown"}:
        return "warning"
    return "warning"


def build_document_extraction_v1(documents: List[Dict[str, Any]]) -> Dict[str, Any]:
    normalized_docs: List[Dict[str, Any]] = []
    for doc in documents or []:
        extraction_status = (
            doc.get("extractionStatus")
            or doc.get("extraction_status")
            or doc.get("status")
            or "unknown"
        )
        status = _normalize_doc_status(doc.get("status"), extraction_status)
        normalized_docs.append(
            {
                "document_id": doc.get("id") or doc.get("document_id") or doc.get("documentId"),
                "document_type": doc.get("documentType") or doc.get("document_type") or doc.get("type"),
                "filename": doc.get("name") or doc.get("filename"),
                "status": status,
                "extraction_status": extraction_status,
                "extracted_fields": doc.get("extractedFields") or doc.get("extracted_fields") or {},
                "issues_count": doc.get("discrepancyCount")
                or doc.get("issues_count")
                or doc.get("issuesCount")
                or 0,
                "ocr_confidence": doc.get("ocrConfidence") or doc.get("ocr_confidence"),
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

        document_ids = issue.get("document_ids") or issue.get("document_id") or []
        if not isinstance(document_ids, list):
            document_ids = [document_ids]
        document_types = issue.get("document_types") or issue.get("document_type") or []
        if not isinstance(document_types, list):
            document_types = [document_types]
        document_names = issue.get("documents") or issue.get("document_names") or []
        if not isinstance(document_names, list):
            document_names = [document_names]

        provenance.append(
            {
                "issue_id": issue_id,
                "source": source,
                "ruleset_domain": ruleset_domain,
                "rule": issue.get("rule") or issue.get("rule_id"),
                "severity": issue.get("severity"),
                "document_ids": document_ids,
                "document_types": document_types,
                "document_names": document_names,
            }
        )

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
