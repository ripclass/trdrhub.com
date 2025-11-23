from __future__ import annotations

from typing import Any, Dict, List, Optional

DEFAULT_MT700_BLOCKS = [
    "27",
    "31C",
    "40E",
    "50",
    "59",
    "32B",
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
    *,
    extracted_data: Optional[Dict[str, Any]],
    legacy_results_payload: Optional[Dict[str, Any]],
    extractor_outputs: Optional[Dict[str, Any]],
    lc_type_hint: Optional[Dict[str, Any]],
    session_documents: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Build the unified structured_result payload (structured_result_v1).
    """

    extracted_data = extracted_data or {}
    legacy_results_payload = legacy_results_payload or {}
    extractor_outputs = extractor_outputs or extracted_data.get("lc_structured") or {}

    documents_structured = normalize_documents_structured(
        session_documents,
        legacy_results_payload.get("documents"),
    )

    issues = normalize_issues(
        legacy_results_payload.get("issue_cards"),
        legacy_results_payload.get("discrepancies"),
    )

    lc_structured = {
        "mt700": normalize_mt700(extractor_outputs),
        "goods": normalize_goods(extractor_outputs, extracted_data),
        "clauses": normalize_clauses(extractor_outputs, legacy_results_payload),
        "timeline": normalize_timeline(extractor_outputs, legacy_results_payload),
        "documents_structured": documents_structured,
        "analytics": compute_lc_structured_analytics(legacy_results_payload, issues),
    }

    processing_summary = compute_processing_summary(legacy_results_payload, issues, documents_structured)
    analytics = compute_analytics(legacy_results_payload, issues)

    lc_type_details = derive_lc_type(extracted_data, extractor_outputs, lc_type_hint)

    ai_enrichment = legacy_results_payload.get("ai_enrichment") or legacy_results_payload.get("aiEnrichment")
    if not isinstance(ai_enrichment, dict):
        ai_enrichment = {"enabled": False, "notes": []}
    else:
        ai_enrichment.setdefault("enabled", False)
        ai_enrichment.setdefault("notes", [])

    return {
        "version": "structured_result_v1",
        **lc_type_details,
        "lc_structured": lc_structured,
        "issues": issues,
        "processing_summary": processing_summary,
        "analytics": analytics,
        "ai_enrichment": ai_enrichment,
    }


def derive_lc_type(
    extracted_data: Dict[str, Any],
    extractor_outputs: Dict[str, Any],
    lc_type_hint: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    details = {
        "lc_type": "unknown",
        "lc_type_reason": None,
        "lc_type_confidence": 0,
        "lc_type_source": "auto",
    }
    lc_structured = extracted_data.get("lc_structured") or extractor_outputs or {}

    candidates = [
        (lc_type_hint or {}).get("lc_type"),
        extracted_data.get("lc_type"),
        lc_structured.get("lc_type"),
    ]
    for candidate in candidates:
        if candidate:
            details["lc_type"] = candidate
            break

    details["lc_type_reason"] = (
        (lc_type_hint or {}).get("lc_type_reason")
        or extracted_data.get("lc_type_reason")
        or lc_structured.get("lc_type_reason")
    )
    details["lc_type_confidence"] = (
        (lc_type_hint or {}).get("lc_type_confidence")
        or extracted_data.get("lc_type_confidence")
        or lc_structured.get("lc_type_confidence")
        or 0
    )
    details["lc_type_source"] = (
        (lc_type_hint or {}).get("lc_type_source")
        or extracted_data.get("lc_type_source")
        or lc_structured.get("lc_type_source")
        or "auto"
    )
    return details


def normalize_mt700(extractor_outputs: Dict[str, Any]) -> Dict[str, Any]:
    fields = extractor_outputs.get("mt700") or extractor_outputs.get("fields") or {}
    raw = extractor_outputs.get("mt700_raw") or extractor_outputs.get("raw") or {}

    blocks = {tag: None for tag in DEFAULT_MT700_BLOCKS}

    shipment_details = fields.get("shipment_details") or {}

    block_mapping = {
        "27": fields.get("sequence"),
        "31C": fields.get("date_of_issue"),
        "40E": fields.get("applicable_rules"),
        "50": fields.get("applicant"),
        "59": fields.get("beneficiary"),
        "32B": fields.get("credit_amount"),
        "41A": (fields.get("available_with") or {}).get("details")
        if isinstance(fields.get("available_with"), dict)
        else None,
        "41D": (fields.get("available_with") or {}).get("details")
        if isinstance(fields.get("available_with"), dict)
        else None,
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


def normalize_goods(
    extractor_outputs: Dict[str, Any],
    extracted_data: Dict[str, Any],
) -> List[Dict[str, Any]]:
    goods = extractor_outputs.get("goods") or []
    if not goods:
        goods = (
            (extractor_outputs.get("documents_required") or {}).get("goods")
            or extracted_data.get("goods")
            or []
        )

    normalized = []

    for item in goods:
        if not isinstance(item, dict):
            continue
        normalized.append(
            {
                "description": item.get("description") or item.get("line"),
                "quantity": (item.get("quantity") or {}).get("value") if isinstance(item.get("quantity"), dict) else item.get("quantity"),
                "unit": (item.get("quantity") or {}).get("unit") if isinstance(item.get("quantity"), dict) else item.get("unit"),
                "hs_code": item.get("hs_code") or item.get("hsCode"),
                "unit_price": item.get("unit_price") or item.get("unitPrice"),
                "amount": item.get("amount"),
                "origin_country": item.get("origin_country") or item.get("originCountry"),
            }
        )

    return normalized


def normalize_clauses(
    extractor_outputs: Dict[str, Any],
    legacy_results_payload: Dict[str, Any],
) -> List[Dict[str, Any]]:
    clauses = extractor_outputs.get("clauses_47a") or extractor_outputs.get("additional_conditions") or []
    if not clauses:
        clauses = legacy_results_payload.get("clauses") or []

    normalized = []
    for clause in clauses:
        if isinstance(clause, dict):
            normalized.append(
                {
                    "code": clause.get("code") or clause.get("id") or "",
                    "title": clause.get("title") or clause.get("label") or "",
                    "text": clause.get("text") or clause.get("value") or clause.get("description") or "",
                    "source": clause.get("source") or "lc",
                }
            )
        else:
            normalized.append({"code": "", "title": "", "text": str(clause), "source": "lc"})
    return normalized


def normalize_timeline(
    extractor_outputs: Dict[str, Any],
    legacy_results_payload: Dict[str, Any],
) -> List[Dict[str, Any]]:
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
                {"title": title, "status": "complete", "timestamp": value, "description": None}
            )

    legacy_timeline = legacy_results_payload.get("timeline") or []
    if isinstance(legacy_timeline, list):
        for entry in legacy_timeline:
            if not isinstance(entry, dict):
                continue
            timeline.append(
                {
                    "title": entry.get("title") or entry.get("label"),
                    "status": entry.get("status") or entry.get("state") or "pending",
                    "timestamp": entry.get("timestamp"),
                    "description": entry.get("description") or entry.get("detail"),
                }
            )

    return timeline


def normalize_documents_structured(
    session_documents: Optional[List[Dict[str, Any]]],
    legacy_docs: Optional[List[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    documents_structured: List[Dict[str, Any]] = []

    if session_documents:
        for doc in session_documents:
            documents_structured.append(
                {
                    "document_id": str(doc.get("id") or doc.get("documentId") or doc.get("document_id") or ""),
                    "document_type": doc.get("document_type") or doc.get("documentType"),
                    "filename": doc.get("original_filename") or doc.get("filename") or doc.get("name"),
                    "extraction_status": doc.get("extraction_status") or doc.get("extractionStatus") or "unknown",
                    "extracted_fields": doc.get("extracted_fields") or doc.get("extractedFields") or {},
                }
            )

    if not documents_structured and isinstance(legacy_docs, list):
        for doc in legacy_docs:
            documents_structured.append(
                {
                    "document_id": str(doc.get("id") or ""),
                    "document_type": doc.get("documentType") or doc.get("type"),
                    "filename": doc.get("name") or doc.get("original_filename"),
                    "extraction_status": doc.get("extraction_status") or doc.get("status") or "unknown",
                    "extracted_fields": doc.get("extractedFields") or doc.get("extracted_fields") or {},
                }
            )

    return documents_structured


def normalize_issues(
    issue_cards: Optional[List[Dict[str, Any]]],
    discrepancies: Optional[List[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    seen_ids = set()

    for source in (issue_cards or []):
        issue_id = source.get("id") or source.get("rule") or source.get("title")
        if issue_id and issue_id in seen_ids:
            continue
        seen_ids.add(issue_id)
        issues.append(
            {
                "id": issue_id,
                "rule": source.get("rule"),
                "title": source.get("title"),
                "severity": source.get("severity") or "minor",
                "documents": source.get("documents") or ([source.get("documentName")] if source.get("documentName") else []),
                "expected": source.get("expected"),
                "found": source.get("actual") or source.get("found"),
                "suggested_fix": source.get("suggestion") or source.get("suggestedFix"),
                "description": source.get("description"),
                "ucp_reference": source.get("ucpReference"),
            }
        )

    for source in discrepancies or []:
        if source.get("not_applicable"):
            continue
        issue_id = source.get("id") or source.get("rule") or source.get("title")
        if issue_id and issue_id in seen_ids:
            continue
        seen_ids.add(issue_id)
        issues.append(
            {
                "id": issue_id,
                "rule": source.get("rule"),
                "title": source.get("title") or source.get("rule"),
                "severity": source.get("severity") or "minor",
                "documents": source.get("documents") or [],
                "expected": source.get("expected"),
                "found": source.get("found"),
                "suggested_fix": source.get("suggestedFix") or source.get("suggestion"),
                "description": source.get("message") or source.get("description"),
                "ucp_reference": source.get("ucp_reference"),
            }
        )

    return issues


def compute_lc_structured_analytics(
    legacy_results_payload: Dict[str, Any],
    issues: List[Dict[str, Any]],
) -> Dict[str, Any]:
    issue_counts = {"critical": 0, "major": 0, "medium": 0, "minor": 0}
    for issue in issues:
        severity = (issue.get("severity") or "minor").lower()
        if severity in issue_counts:
            issue_counts[severity] += 1
        else:
            issue_counts["minor"] += 1

    compliance_score = 100 - ((issue_counts["critical"] * 30) + (issue_counts["major"] * 20) + (issue_counts["medium"] * 10))
    compliance_score = max(0, min(100, compliance_score))

    return {"compliance_score": compliance_score, "issue_counts": issue_counts}


def compute_processing_summary(
    legacy_results_payload: Dict[str, Any],
    issues: List[Dict[str, Any]],
    documents_structured: List[Dict[str, Any]],
) -> Dict[str, Any]:
    severity_breakdown = {"critical": 0, "major": 0, "medium": 0, "minor": 0}
    for issue in issues:
        severity = (issue.get("severity") or "minor").lower()
        if severity in severity_breakdown:
            severity_breakdown[severity] += 1
        else:
            severity_breakdown["minor"] += 1

    processing_summary = {
        "total_documents": len(documents_structured),
        "successful_extractions": sum(1 for doc in documents_structured if doc.get("extraction_status") == "success"),
        "failed_extractions": sum(1 for doc in documents_structured if doc.get("extraction_status") not in {"success", "partial"}),
        "total_issues": sum(severity_breakdown.values()),
        "severity_breakdown": severity_breakdown,
    }

    legacy_summary = legacy_results_payload.get("processing_summary") or {}
    processing_summary.update({k: v for k, v in legacy_summary.items() if k not in processing_summary or processing_summary[k] in (None, 0)})

    return processing_summary


def compute_analytics(
    legacy_results_payload: Dict[str, Any],
    issues: List[Dict[str, Any]],
) -> Dict[str, Any]:
    analytics = legacy_results_payload.get("analytics") or {}
    if not isinstance(analytics, dict):
        analytics = {}

    compliance_score = analytics.get("lc_compliance_score") or analytics.get("compliance_score")
    if compliance_score is None:
        issue_penalty = len(issues) * 5
        compliance_score = max(0, 100 - issue_penalty)

    default_issue_counts = {"critical": 0, "major": 0, "medium": 0, "minor": 0}
    for issue in issues:
        severity = (issue.get("severity") or "minor").lower()
        if severity in default_issue_counts:
            default_issue_counts[severity] += 1
        else:
            default_issue_counts["minor"] += 1

    analytics.setdefault("issue_counts", default_issue_counts)
    analytics.setdefault("compliance_score", compliance_score)

    return analytics

