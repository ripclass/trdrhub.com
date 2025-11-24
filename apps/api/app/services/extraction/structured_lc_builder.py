from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import uuid4

VERSION = "structured_result_v1"

DEFAULT_MT700_BLOCKS = [
    "20",
    "27",
    "31C",
    "31D",
    "40A",
    "40E",
    "50",
    "59",
    "32B",
    "39A",
    "39B",
    "41A",
    "41D",
    "44A",
    "44B",
    "44C",
    "44D",
    "44E",
    "44F",
    "45A",
    "46A",
    "47A",
    "71B",
    "78",
]


def build_unified_structured_result(
    session_documents: List[Dict[str, Any]],
    extractor_outputs: Optional[Dict[str, Any]],
    legacy_payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build Option-E structured_result_v1 payload without relying on legacy document merges.
    """

    legacy_payload = legacy_payload or {}
    extractor_outputs = extractor_outputs or {}

    documents_structured = _normalize_documents_structured(session_documents or [])
    issues = _normalize_issues(
        legacy_payload.get("issue_cards") or [],
        legacy_payload.get("discrepancies") or [],
    )
    processing_seconds = float(legacy_payload.get("processing_seconds") or 0.0)
    processing_summary = _compute_processing_summary(documents_structured, issues, processing_seconds)
    analytics = _compute_analytics(documents_structured, issues)

    lc_structured = {
        "mt700": _normalize_mt700(extractor_outputs),
        "goods": _normalize_goods(extractor_outputs),
        "clauses": _normalize_clauses(extractor_outputs),
        "timeline": _normalize_lc_timeline(extractor_outputs),
        "documents_structured": documents_structured,
        "analytics": analytics,
    }

    structured_result = {
        "version": VERSION,
        **_derive_lc_type(extractor_outputs, legacy_payload),
        "lc_structured": lc_structured,
        "documents_structured": documents_structured,
        "issues": issues,
        "processing_summary": processing_summary,
        "analytics": analytics,
        "ai_enrichment": _normalize_ai_payload(legacy_payload.get("ai_enrichment")),
    }

    return structured_result


def _derive_lc_type(
    extractor_outputs: Dict[str, Any],
    legacy_payload: Dict[str, Any],
) -> Dict[str, Any]:
    details = {
        "lc_type": "unknown",
        "lc_type_reason": None,
        "lc_type_confidence": 0,
        "lc_type_source": "auto",
    }

    lc_structured = extractor_outputs or {}
    candidates = [legacy_payload.get("lc_type"), lc_structured.get("lc_type")]
    for candidate in candidates:
        if candidate:
            details["lc_type"] = candidate
            break

    details["lc_type_reason"] = legacy_payload.get("lc_type_reason") or lc_structured.get("lc_type_reason")
    details["lc_type_confidence"] = legacy_payload.get("lc_type_confidence") or lc_structured.get("lc_type_confidence") or 0
    details["lc_type_source"] = legacy_payload.get("lc_type_source") or lc_structured.get("lc_type_source") or "auto"
    return details


def _normalize_documents_structured(documents: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for index, doc in enumerate(documents):
        normalized.append(
            {
                "document_id": str(doc.get("document_id") or doc.get("id") or uuid4()),
                "document_type": doc.get("document_type") or doc.get("documentType") or "supporting_document",
                "filename": doc.get("filename") or doc.get("name") or doc.get("original_filename") or f"Document {index + 1}",
                "extraction_status": doc.get("extraction_status") or doc.get("extractionStatus") or "unknown",
                "extracted_fields": doc.get("extracted_fields") or doc.get("extractedFields") or {},
                "issues_count": doc.get("issues_count") or doc.get("discrepancyCount") or 0,
            }
        )
    return normalized


def _normalize_issues(
    issue_cards: List[Dict[str, Any]],
    discrepancies: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    seen_ids = set()

    def _append_issue(source: Dict[str, Any], fallback_title: str, issue_id: Optional[str]):
        if issue_id and issue_id in seen_ids:
            return
        if issue_id:
            seen_ids.add(issue_id)
        issues.append(
            {
                "id": issue_id or fallback_title,
                "rule": source.get("rule"),
                "title": source.get("title") or fallback_title,
                "severity": (source.get("severity") or "minor").lower(),
                "documents": source.get("documents") or source.get("document_names") or [],
                "expected": source.get("expected"),
                "found": source.get("found") or source.get("actual"),
                "suggested_fix": source.get("suggested_fix") or source.get("suggestion"),
                "description": source.get("description") or source.get("message") or "",
                "ucp_reference": source.get("ucp_reference") or source.get("reference"),
            }
        )

    for issue in issue_cards:
        issue_id = str(issue.get("id") or issue.get("rule") or uuid4())
        _append_issue(issue, "Issue", issue_id)

    for discrepancy in discrepancies:
        issue_id = str(discrepancy.get("id") or discrepancy.get("rule") or uuid4())
        _append_issue(discrepancy, discrepancy.get("title") or "Rule Failure", issue_id)

    return issues


def _compute_processing_summary(
    documents_structured: List[Dict[str, Any]],
    issues: List[Dict[str, Any]],
    processing_seconds: float,
) -> Dict[str, Any]:
    severity_breakdown = {"critical": 0, "major": 0, "medium": 0, "minor": 0}
    for issue in issues:
        severity = issue.get("severity") or "minor"
        if severity not in severity_breakdown:
            severity = "minor"
        severity_breakdown[severity] += 1

    total_documents = len(documents_structured)
    successful = sum(
        1 for doc in documents_structured if (doc.get("extraction_status") or "").lower() in {"success", "complete"}
    )
    failed = sum(
        1
        for doc in documents_structured
        if (doc.get("extraction_status") or "").lower() in {"error", "failed"}
    )

    return {
        "total_documents": total_documents,
        "successful_extractions": successful,
        "failed_extractions": failed,
        "total_issues": sum(severity_breakdown.values()),
        "severity_breakdown": severity_breakdown,
        "processing_time_seconds": round(processing_seconds, 2),
        "processing_time_display": _format_duration(processing_seconds),
    }


def _compute_analytics(
    documents_structured: List[Dict[str, Any]],
    issues: List[Dict[str, Any]],
) -> Dict[str, Any]:
    issue_counts = {"critical": 0, "major": 0, "medium": 0, "minor": 0}
    for issue in issues:
        severity = issue.get("severity") or "minor"
        if severity not in issue_counts:
            severity = "minor"
        issue_counts[severity] += 1

    compliance_penalty = (
        issue_counts["critical"] * 30
        + issue_counts["major"] * 20
        + issue_counts["medium"] * 10
        + issue_counts["minor"] * 5
    )
    compliance_score = max(0, min(100, 100 - compliance_penalty))

    document_risk = [
        {
            "document_id": doc.get("document_id"),
            "filename": doc.get("filename"),
            "risk": "high" if doc.get("issues_count", 0) >= 3 else "medium" if doc.get("issues_count", 0) >= 1 else "low",
        }
        for doc in documents_structured
    ]

    return {
        "compliance_score": compliance_score,
        "issue_counts": issue_counts,
        "document_risk": document_risk,
    }


def _normalize_mt700(extractor_outputs: Dict[str, Any]) -> Dict[str, Any]:
    fields = extractor_outputs.get("mt700") or extractor_outputs.get("fields") or {}
    raw = extractor_outputs.get("mt700_raw") or extractor_outputs.get("raw") or {}
    blocks = {tag: None for tag in DEFAULT_MT700_BLOCKS}

    shipment_details = fields.get("shipment_details") or extractor_outputs.get("shipment_details") or {}

    block_mapping = {
        "20": fields.get("reference"),
        "27": fields.get("sequence"),
        "31C": fields.get("date_of_issue"),
        "31D": fields.get("expiry_details", {}).get("expiry_place_and_date") if isinstance(fields.get("expiry_details"), dict) else fields.get("expiry_details"),
        "40A": fields.get("form_of_doc_credit"),
        "40E": fields.get("applicable_rules"),
        "50": fields.get("applicant"),
        "59": fields.get("beneficiary"),
        "32B": fields.get("credit_amount"),
        "39A": fields.get("tolerance"),
        "39B": fields.get("max_credit_amt"),
        "41A": fields.get("available_with"),
        "41D": fields.get("available_with"),
        "44A": shipment_details.get("place_of_taking_in_charge_dispatch_from"),
        "44B": shipment_details.get("place_of_final_destination_for_transport"),
        "44C": shipment_details.get("latest_date_of_shipment"),
        "44D": shipment_details.get("shipment_period"),
        "44E": shipment_details.get("port_of_loading_airport_of_departure"),
        "44F": shipment_details.get("port_of_discharge_airport_of_destination"),
        "45A": extractor_outputs.get("documents_required"),
        "46A": extractor_outputs.get("goods"),
        "47A": extractor_outputs.get("clauses_47a") or extractor_outputs.get("additional_conditions"),
        "71B": fields.get("charges"),
        "78": fields.get("instructions_to_paying_accepting_negotiating_bank"),
    }

    for tag, value in block_mapping.items():
        if value:
            blocks[tag] = value

    return {
        "blocks": blocks,
        "raw_text": extractor_outputs.get("raw_text"),
        "version": "mt700_v1",
    }


def _normalize_goods(extractor_outputs: Dict[str, Any]) -> List[Dict[str, Any]]:
    goods = extractor_outputs.get("goods") or []
    normalized: List[Dict[str, Any]] = []

    for item in goods:
        if not isinstance(item, dict):
            continue
        normalized.append(
            {
                "description": item.get("description") or item.get("line"),
                "quantity": item.get("quantity"),
                "unit": item.get("unit"),
                "hs_code": item.get("hs_code") or item.get("hsCode"),
                "unit_price": item.get("unit_price") or item.get("unitPrice"),
                "amount": item.get("amount"),
                "origin_country": item.get("origin_country") or item.get("originCountry"),
            }
        )

    return normalized


def _normalize_clauses(extractor_outputs: Dict[str, Any]) -> List[Dict[str, Any]]:
    clauses = extractor_outputs.get("clauses_47a") or extractor_outputs.get("additional_conditions") or []
    normalized: List[Dict[str, Any]] = []

    for clause in clauses:
        if isinstance(clause, dict):
            normalized.append(
                {
                    "code": clause.get("code") or clause.get("id") or "",
                    "title": clause.get("title") or clause.get("label") or "",
                    "text": clause.get("text") or clause.get("value") or "",
                    "source": clause.get("source") or "lc",
                }
            )
        else:
            normalized.append(
                {
                    "code": "",
                    "title": "",
                    "text": str(clause),
                    "source": "lc",
                }
            )

    return normalized


def _normalize_lc_timeline(extractor_outputs: Dict[str, Any]) -> List[Dict[str, Any]]:
    timeline = []
    extractor_timeline = extractor_outputs.get("timeline") or {}

    timeline_map = [
        ("issue_date", "LC Issued"),
        ("expiry_date", "Expiry Date"),
        ("latest_shipment", "Latest Shipment"),
    ]

    for key, title in timeline_map:
        value = extractor_timeline.get(key)
        if value:
            timeline.append(
                {
                    "title": title,
                    "status": "complete",
                    "timestamp": value,
                    "description": None,
                }
            )

    return timeline


def _normalize_ai_payload(ai_enrichment: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(ai_enrichment, dict):
        return {"enabled": False, "notes": []}
    payload = dict(ai_enrichment)
    payload.setdefault("enabled", False)
    payload.setdefault("notes", [])
    return payload


def _format_duration(duration_seconds: float) -> str:
    if duration_seconds < 60:
        return f"{int(duration_seconds)}s"
    minutes, seconds = divmod(int(duration_seconds), 60)
    if minutes < 60:
        return f"{minutes}m {seconds}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m"

