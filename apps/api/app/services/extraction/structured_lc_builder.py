from __future__ import annotations

from typing import Any, Dict, List, Optional
import copy
import datetime

VERSION = "structured_result_v1"


def _safe_get(d: Optional[dict], *path, default=None):
    cur = d or {}
    for p in path:
        if not isinstance(cur, dict) or p not in cur:
            return default
        cur = cur[p]
    return cur


def _now_iso() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _coalesce(*vals):
    for v in vals:
        if v not in (None, "", [], {}):
            return v
    return None


def _normalize_documents(documents: Optional[List[dict]]) -> List[dict]:
    docs = []
    if not documents:
        return docs
    for d in documents:
        docs.append({
            "document_id": d.get("id") or d.get("document_id"),
            "document_type": d.get("type") or d.get("documentType") or d.get("document_type"),
            "filename": d.get("name") or d.get("filename"),
            "extraction_status": d.get("extractionStatus") or d.get("extraction_status") or d.get("status"),
            "extracted_fields": d.get("extractedFields") or d.get("extracted_fields") or {},
            "issues_count": d.get("discrepancyCount") or d.get("issues_count") or 0,
        })
    return docs


def _normalize_issues(discrepancies: Optional[List[dict]], results: Optional[List[dict]], issue_cards: Optional[List[dict]]) -> List[dict]:
    out: List[dict] = []
    for bucket in (discrepancies or [], results or [], issue_cards or []):
        for r in bucket:
            out.append({
                "id": r.get("rule") or r.get("id") or r.get("code") or r.get("title"),
                "title": r.get("title") or r.get("rule") or "Issue",
                "severity": r.get("severity") or "minor",
                "documents": r.get("documents") or [],
                "expected": r.get("expected"),
                "found": r.get("found") or r.get("actual"),
                "suggested_fix": r.get("suggested_fix") or r.get("suggestion"),
                "description": r.get("description") or r.get("message"),
                "ucp_reference": r.get("ucp_reference"),
            })
    # de-dup by (id,title,severity)
    seen = set()
    uniq = []
    for i in out:
        key = (i.get("id"), i.get("title"), i.get("severity"))
        if key in seen:
            continue
        seen.add(key)
        uniq.append(i)
    return uniq


def _build_processing_summary(legacy_payload: dict) -> dict:
    # try legacy metrics
    ps = _safe_get(legacy_payload, "processing_summary") or {}
    total_docs = _coalesce(ps.get("documents"), ps.get("total_documents"), legacy_payload.get("total_documents"))
    success = _safe_get(legacy_payload, "document_status", "success") or _safe_get(legacy_payload, "document_status", "success")
    failed = _safe_get(legacy_payload, "document_status", "error")
    return {
        "total_documents": total_docs or (len(legacy_payload.get("documents") or []) or 0),
        "successful_extractions": success or 0,
        "failed_extractions": failed or 0,
        "total_issues": len(legacy_payload.get("discrepancies") or []),
        "severity_breakdown": {
            "critical": sum(1 for i in (legacy_payload.get("discrepancies") or []) if (i.get("severity") == "critical")),
            "major":    sum(1 for i in (legacy_payload.get("discrepancies") or []) if (i.get("severity") == "major")),
            "medium":   sum(1 for i in (legacy_payload.get("discrepancies") or []) if (i.get("severity") == "medium")),
            "minor":    sum(1 for i in (legacy_payload.get("discrepancies") or []) if (i.get("severity") == "minor")),
        },
    }


def _build_analytics(legacy_payload: dict, issues: List[dict]) -> dict:
    # Simple compliance score: 100 - (min(issues, 100)*2) bounded 0..100
    raw = 100 - min(len(issues), 100) * 2
    score = max(0, min(100, raw))
    # Try to pass through any richer analytics if present
    legacy = copy.deepcopy(legacy_payload.get("analytics") or {})
    legacy["compliance_score"] = legacy.get("compliance_score") or score
    # quick risk sketch per document
    doc_risk = []
    for d in (legacy_payload.get("documents") or []):
        risk = "low"
        if d.get("discrepancyCount", 0) >= 3:
            risk = "high"
        elif d.get("discrepancyCount", 0) >= 1:
            risk = "medium"
        doc_risk.append({
            "document_id": d.get("id"),
            "filename": d.get("name"),
            "risk": risk,
        })
    legacy["issue_counts"] = {
        "critical": sum(1 for x in issues if x.get("severity") == "critical"),
        "major":    sum(1 for x in issues if x.get("severity") == "major"),
        "medium":   sum(1 for x in issues if x.get("severity") == "medium"),
        "minor":    sum(1 for x in issues if x.get("severity") == "minor"),
    }
    legacy["document_risk"] = legacy.get("document_risk") or doc_risk
    return legacy


def _build_timeline(legacy_payload: dict) -> List[dict]:
    tl = []
    for e in (legacy_payload.get("timeline") or []):
        tl.append({
            "title": e.get("title") or e.get("label"),
            "label": e.get("label") or e.get("title"),
            "status": e.get("status") or "complete",
            "description": e.get("description"),
            "timestamp": e.get("timestamp"),
        })
    if not tl:
        tl = [
            {"title": "Upload Received", "label": "Upload Received", "status": "complete", "timestamp": _now_iso()},
            {"title": "Deterministic Rules", "label": "Deterministic Rules", "status": "complete", "timestamp": _now_iso()},
            {"title": "Issue Review Ready", "label": "Issue Review Ready", "status": "complete", "timestamp": _now_iso()},
        ]
    return tl


def build_unified_structured_result(
    *,
    extracted_data: Optional[dict],
    documents: Optional[List[dict]],
    discrepancies: Optional[List[dict]],
    results: Optional[List[dict]],
    issue_cards: Optional[List[dict]],
    lc_type_data: Optional[dict],
    ai_enrichment: Optional[dict],
    legacy_payload: dict,
) -> dict:
    # Choose lc_structured from extractor first, then legacy structured_result, then None.
    lc_structured = _coalesce(
        _safe_get(extracted_data, "lc_structured"),
        _safe_get(legacy_payload, "structured_result", "lc_structured"),
    )

    # Decompose extractor MT700/Goods/Clauses if present (Option-E)
    mt700 = _safe_get(lc_structured, "mt700") or _safe_get(lc_structured, "MT700")
    goods = _safe_get(lc_structured, "goods") or _safe_get(lc_structured, "goods_46a") or _safe_get(lc_structured, "goods_lines")
    clauses = _safe_get(lc_structured, "clauses") or _safe_get(lc_structured, "special_conditions")

    norm_docs = _normalize_documents(documents)
    issues = _normalize_issues(discrepancies, results, issue_cards)
    processing_summary = _build_processing_summary(legacy_payload)
    analytics = _build_analytics(legacy_payload, issues)
    timeline = _build_timeline(legacy_payload)

    lc_meta = {
        "lc_type": _safe_get(lc_type_data, "lc_type") or legacy_payload.get("lc_type"),
        "lc_type_reason": _safe_get(lc_type_data, "lc_type_reason") or legacy_payload.get("lc_type_reason"),
        "lc_type_confidence": _safe_get(lc_type_data, "lc_type_confidence") or legacy_payload.get("lc_type_confidence"),
        "lc_type_source": _safe_get(lc_type_data, "lc_type_source") or legacy_payload.get("lc_type_source"),
    }

    unified = {
        "version": VERSION,
        "lc_structured": lc_structured or {},
        "mt700": mt700 or {},
        "goods": goods or [],
        "clauses": clauses or [],
        "documents": norm_docs,
        "issues": issues,
        "processing_summary": processing_summary,
        "analytics": analytics,
        "timeline": timeline,
        "lc_meta": lc_meta,
        "ai_enrichment": ai_enrichment or legacy_payload.get("ai_enrichment"),
        # passthrough for consumers that expect these names:
        "extracted_documents": legacy_payload.get("extracted_documents") or {},
    }
    return unified

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

