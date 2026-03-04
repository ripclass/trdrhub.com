from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

OPTION_E_VERSION = "structured_result_v1"
VALIDATION_CONTRACT_VERSION = "2026-02-27.p0"
EXTRACTION_CONFIDENCE_SUCCESS_THRESHOLD = 0.6


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _safe(value: Any, default: Any = None) -> Any:
    return value if value not in (None, "") else default


def _as_dict(value: Any) -> Dict[str, Any]:
    """Return a dict when possible; otherwise a safe empty mapping."""
    return value if isinstance(value, dict) else {}


def _read_text(value: Any) -> Optional[str]:
    if isinstance(value, str):
        val = value.strip()
        return val or None
    if isinstance(value, dict):
        nested = value.get("value")
        if isinstance(nested, str):
            val = nested.strip()
            return val or None
    return None


def _parse_swift_yymmdd(raw: Any) -> Optional[str]:
    value = _read_text(raw)
    if not value or len(value) != 6 or not value.isdigit():
        return None

    yy = int(value[:2])
    mm = int(value[2:4])
    dd = int(value[4:6])
    year = 2000 + yy if yy <= 69 else 1900 + yy
    try:
        return datetime(year, mm, dd).strftime("%Y-%m-%d")
    except ValueError:
        return None


def _recover_swapped_issue_date(issue_date: Optional[str], expiry_date: Optional[str]) -> Optional[str]:
    # Recover legacy inversion pattern like 2015-04-26 -> 2026-04-15 when expiry indicates 2026 horizon.
    if not issue_date or not expiry_date:
        return None
    if len(issue_date) != 10 or len(expiry_date) != 10:
        return None

    try:
        issue_dt = datetime.strptime(issue_date, "%Y-%m-%d")
        expiry_dt = datetime.strptime(expiry_date, "%Y-%m-%d")
    except ValueError:
        return None

    parts = issue_date.split("-")
    if len(parts) != 3:
        return None
    yyyy, mm, dd = parts
    if len(yyyy) != 4 or len(mm) != 2 or len(dd) != 2:
        return None

    candidate = f"20{dd}-{mm}-{yyyy[2:]}"
    try:
        candidate_dt = datetime.strptime(candidate, "%Y-%m-%d")
    except ValueError:
        return None

    if issue_dt.year <= expiry_dt.year - 5 and candidate_dt <= expiry_dt and candidate_dt.year >= expiry_dt.year - 2:
        return candidate
    return None


def _canonical_issue_date(extractor_outputs: Dict[str, Any], mt700_block: Dict[str, Any], timeline_dict: Dict[str, Any]) -> Optional[str]:
    explicit = _read_text(extractor_outputs.get("issue_date"))
    expiry = _read_text(extractor_outputs.get("expiry_date")) or _read_text(timeline_dict.get("expiry_date"))

    mt700_fields = mt700_block.get("fields") if isinstance(mt700_block.get("fields"), dict) else {}
    mt700_blocks = mt700_block.get("blocks") if isinstance(mt700_block.get("blocks"), dict) else {}

    swift_31c = (
        _parse_swift_yymmdd(mt700_blocks.get("31C"))
        or _parse_swift_yymmdd(mt700_block.get("31C"))
        or _parse_swift_yymmdd(mt700_fields.get("31C"))
    )
    if swift_31c:
        return swift_31c

    mt700_issue = _read_text(mt700_fields.get("date_of_issue")) or _read_text(mt700_block.get("date_of_issue"))
    if mt700_issue:
        return mt700_issue

    recovered = _recover_swapped_issue_date(explicit, expiry)
    if recovered:
        return recovered

    return explicit or _read_text(timeline_dict.get("issue_date"))


def _pluck_lc_type(extractor_outputs: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    extractor_outputs = _as_dict(extractor_outputs)
    if not extractor_outputs:
        return {
            "lc_type": "unknown",
            "lc_type_reason": "Extractor outputs not provided.",
            "lc_type_confidence": 0,
            "lc_type_source": "auto",
        }

    # Keep confidence as float (0-1 range) - frontend multiplies by 100 for display
    raw_confidence = _safe(extractor_outputs.get("lc_type_confidence"), 0) or 0
    # Ensure it's a float between 0-1 (some sources may pass percentage already)
    confidence = float(raw_confidence) if raw_confidence <= 1 else float(raw_confidence) / 100
    
    return {
        "lc_type": extractor_outputs.get("lc_type", "unknown"),
        "lc_type_reason": extractor_outputs.get("lc_type_reason", "Insufficient details."),
        "lc_type_confidence": confidence,
        "lc_type_source": extractor_outputs.get("lc_type_source", "auto"),
    }


def _has_usable_extracted_fields(extracted_fields: Any) -> bool:
    if not isinstance(extracted_fields, dict):
        return False
    for key, value in extracted_fields.items():
        if str(key).startswith("_"):
            continue
        if value not in (None, "", [], {}):
            return True
    return False


def _canonicalize_extraction_status(
    extraction_status: str,
    extracted_fields: Dict[str, Any],
    failed_reason: Optional[str],
    extraction_confidence: Optional[float],
) -> str:
    status = (extraction_status or "unknown").lower()
    has_fields = _has_usable_extracted_fields(extracted_fields)

    if status in {"failed", "error", "empty"}:
        if has_fields and extraction_confidence is not None and extraction_confidence >= EXTRACTION_CONFIDENCE_SUCCESS_THRESHOLD:
            return "success"
        if has_fields:
            return "partial"
        return "failed" if failed_reason else "partial"

    if status == "success":
        return "success"
    return "partial" if status in {"partial", "pending", "text_only", "unknown"} else "partial"


def _safe_int(value: Any, default: int = 0) -> int:
    """Coerce values to int without raising (Option-E payloads can be stringly)."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _derive_document_status(extraction_status: str, issues_count: int) -> str:
    """Canonical status derivation used by both summary and document rows."""
    status = (extraction_status or "unknown").lower()
    if status == "failed" or issues_count >= 3:
        return "error"
    if issues_count > 0 or status in {"partial", "pending", "text_only", "unknown"}:
        return "warning"
    return "success"


def _normalize_documents_structured(session_documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for idx, doc in enumerate(session_documents or []):
        raw_extraction_status = doc.get("extractionStatus") or doc.get("extraction_status") or "unknown"
        extracted_fields = doc.get("extractedFields") or doc.get("extracted_fields") or {}
        failed_reason = doc.get("failed_reason") or doc.get("extraction_error")
        confidence = doc.get("extraction_confidence")
        if confidence is None:
            confidence = doc.get("ocrConfidence") or doc.get("ocr_confidence")
        try:
            confidence_value = float(confidence) if confidence is not None else None
        except (TypeError, ValueError):
            confidence_value = None

        extraction_status = _canonicalize_extraction_status(
            str(raw_extraction_status),
            extracted_fields,
            failed_reason,
            confidence_value,
        )

        issues_count = _safe_int(
            doc.get("issues_count") or doc.get("issuesCount") or doc.get("discrepancyCount") or 0
        )
        derived_status = _derive_document_status(str(extraction_status), issues_count)
        normalized.append(
            {
                "document_id": doc.get("document_id") or doc.get("id") or str(uuid4()),
                "document_type": doc.get("documentType") or doc.get("type") or "supporting_document",
                "filename": doc.get("name") or doc.get("filename") or doc.get("original_filename") or f"Document {idx + 1}",
                "extraction_status": extraction_status,
                "status": derived_status,
                "issues_count": issues_count,
                "discrepancyCount": issues_count,
                "failed_reason": failed_reason,
                "extracted_fields": extracted_fields,
            }
        )
    return normalized


def _default_mt700() -> Dict[str, Any]:
    blocks = {
        "27": None,
        "31C": None,
        "40E": None,
        "32B": None,
        "41A": None,
        "41D": None,
        "44A": None,
        "44B": None,
        "44C": None,
        "44D": None,
        "44E": None,
        "44F": None,
        "45A": None,
        "46A": None,
        "47A": None,
        "71B": None,
        "78": None,
        "50": None,
        "59": None,
    }
    return {"blocks": blocks, "raw_text": None, "version": "mt700_v1"}


def _default_timeline(count: int) -> List[Dict[str, Any]]:
    return [
        {
            "title": "Documents Uploaded",
            "status": "success",
            "timestamp": _now_iso(),
            "description": f"{count} document(s) received",
        }
    ]


def build_unified_structured_result(
    session_documents: List[Dict[str, Any]],
    extractor_outputs: Optional[Dict[str, Any]] = None,
    legacy_payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Construct Option-E structured_result_v1 without relying on legacy helpers.
    Mirrors lc_structured.documents_structured to top-level documents_structured.
    """

    extractor_outputs = _as_dict(extractor_outputs)
    docs_structured = _normalize_documents_structured(session_documents or [])
    lc_type_fields = _pluck_lc_type(extractor_outputs)

    mt700_block = extractor_outputs.get("mt700") or _default_mt700()
    goods = extractor_outputs.get("goods", [])
    # Support both canonical name "additional_conditions" and legacy "clauses"
    clauses = (
        extractor_outputs.get("additional_conditions") or 
        extractor_outputs.get("clauses") or 
        extractor_outputs.get("clauses_47a") or 
        []
    )
    timeline_raw = extractor_outputs.get("timeline")
    timeline_dict = timeline_raw if isinstance(timeline_raw, dict) else {}
    if isinstance(timeline_raw, list) and timeline_raw:
        timeline = timeline_raw
    elif isinstance(timeline_raw, dict) and isinstance(timeline_raw.get("events"), list) and timeline_raw.get("events"):
        timeline = timeline_raw.get("events")
    else:
        timeline = _default_timeline(len(docs_structured))
    issues = extractor_outputs.get("issues", [])

    canonical_issue_date = _canonical_issue_date(extractor_outputs, mt700_block if isinstance(mt700_block, dict) else {}, timeline_dict)

    # Build dates object from extractor outputs
    dates = {
        "issue": canonical_issue_date,
        "expiry": extractor_outputs.get("expiry_date") or timeline_dict.get("expiry_date"),
        "latest_shipment": extractor_outputs.get("latest_shipment") or timeline_dict.get("latest_shipment"),
        "place_of_expiry": extractor_outputs.get("place_of_expiry"),
    }
    # Filter out None values from dates
    dates = {k: v for k, v in dates.items() if v is not None}
    
    lc_structured = {
        "mt700": mt700_block,
        "goods": goods,
        "clauses": clauses,
        "timeline": timeline,
        "documents_structured": docs_structured,
        "analytics": {
            "compliance_score": 100,
            "issue_counts": {"critical": 0, "major": 0, "medium": 0, "minor": 0},
        },
        # Add fields that frontend expects for LC Card rendering
        "number": extractor_outputs.get("number") or extractor_outputs.get("lc_number"),
        "lc_number": extractor_outputs.get("number") or extractor_outputs.get("lc_number"),
        "amount": extractor_outputs.get("amount"),
        "currency": extractor_outputs.get("currency"),
        "incoterm": extractor_outputs.get("incoterm"),
        "ucp_reference": extractor_outputs.get("ucp_reference"),
        "goods_description": extractor_outputs.get("goods_description"),
        "issue_date": canonical_issue_date,
        "applicant": extractor_outputs.get("applicant"),
        "beneficiary": extractor_outputs.get("beneficiary"),
        "ports": extractor_outputs.get("ports"),
        "additional_conditions": extractor_outputs.get("additional_conditions"),  # Canonical name
        "hs_codes": extractor_outputs.get("hs_codes"),
        "dates": dates if dates else None,
    }

    status_counts = {"success": 0, "warning": 0, "error": 0}
    total_issues = 0
    for doc in docs_structured:
        extraction_status = str(doc.get("extraction_status") or "unknown").lower()
        if extraction_status == "success":
            status_counts["success"] += 1
        elif extraction_status == "failed":
            status_counts["error"] += 1
        else:
            status_counts["warning"] += 1
        total_issues += int(doc.get("discrepancyCount") or 0)

    processing_summary = {
        "total_documents": len(docs_structured),
        "successful_extractions": status_counts["success"],
        "failed_extractions": status_counts["error"],
        "total_issues": total_issues,
        "severity_breakdown": {"critical": 0, "major": 0, "medium": 0, "minor": 0},
        "documents": len(docs_structured),
        "documents_found": len(docs_structured),
        "verified": status_counts["success"],
        "warnings": status_counts["warning"],
        "errors": status_counts["error"],
        "status_counts": dict(status_counts),
        "document_status": dict(status_counts),
        "compliance_rate": round((status_counts["success"] / len(docs_structured)) * 100) if docs_structured else 0,
        "processing_time_seconds": None,
        "processing_time_display": None,
        "processing_time_ms": None,
        "extraction_quality": None,
        "discrepancies": total_issues,
    }

    analytics = {
        "extraction_accuracy": None,
        "lc_compliance_score": None,
        "customs_ready_score": None,
        "documents_processed": len(docs_structured),
        "document_status_distribution": dict(status_counts),
        "document_processing": [],
        "performance_insights": [],
        "processing_time_display": None,
        "issue_counts": {"critical": 0, "major": 0, "medium": 0, "minor": 0},
        "compliance_score": 100,
        "customs_risk": None,
    }

    structured_result = {
        "version": OPTION_E_VERSION,
        "validation_contract_version": VALIDATION_CONTRACT_VERSION,
        **lc_type_fields,
        "lc_structured": lc_structured,
        "documents_structured": docs_structured,
        "issues": issues,
        "processing_summary": processing_summary,
        "analytics": analytics,
        "ai_enrichment": {"enabled": False, "notes": []},
    }

    return {"structured_result": structured_result}

