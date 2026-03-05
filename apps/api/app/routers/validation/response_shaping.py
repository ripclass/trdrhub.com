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
