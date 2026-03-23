from __future__ import annotations

from datetime import UTC, datetime
import ast
import re
from typing import Any, Dict, List, Optional
from uuid import uuid4

try:
    from .lc_taxonomy import build_lc_classification
except ImportError:  # pragma: no cover - direct module loading in tests/scripts
    import importlib.util
    from pathlib import Path

    _lc_taxonomy_path = Path(__file__).with_name("lc_taxonomy.py")
    _lc_taxonomy_spec = importlib.util.spec_from_file_location("lc_taxonomy_fallback", _lc_taxonomy_path)
    if _lc_taxonomy_spec is None or _lc_taxonomy_spec.loader is None:
        raise
    _lc_taxonomy_module = importlib.util.module_from_spec(_lc_taxonomy_spec)
    _lc_taxonomy_spec.loader.exec_module(_lc_taxonomy_module)
    build_lc_classification = _lc_taxonomy_module.build_lc_classification

OPTION_E_VERSION = "structured_result_v1"
LEGACY_WORKFLOW_LC_TYPES = {"import", "export", "draft", "unknown"}


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _safe(value: Any, default: Any = None) -> Any:
    return value if value not in (None, "") else default


def _coerce_text_sequence(value: Any) -> List[str]:
    if value in (None, "", [], {}):
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, tuple):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        trimmed = value.strip()
        if not trimmed:
            return []
        if trimmed.startswith("[") and trimmed.endswith("]"):
            try:
                parsed = ast.literal_eval(trimmed)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if str(item).strip()]
            except Exception:
                pass
        return [trimmed]
    return [str(value).strip()] if str(value).strip() else []


def _pluck_lc_type(extractor_outputs: Optional[Dict[str, Any]]) -> Dict[str, Any]:
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
        "lc_type": _safe(extractor_outputs.get("lc_type"), "unknown"),
        "lc_type_reason": _safe(extractor_outputs.get("lc_type_reason"), "Insufficient details."),
        "lc_type_confidence": confidence,
        "lc_type_source": _safe(extractor_outputs.get("lc_type_source"), "auto"),
    }


def _resolve_legacy_lc_type_fields(
    extractor_outputs: Optional[Dict[str, Any]],
    legacy_payload: Optional[Dict[str, Any]],
    lc_classification: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    extractor_outputs = extractor_outputs or {}
    legacy_payload = legacy_payload or {}
    base = _pluck_lc_type(extractor_outputs)

    workflow_orientation = ""
    if isinstance(lc_classification, dict):
        workflow_orientation = str(lc_classification.get("workflow_orientation") or "").strip().lower()

    if workflow_orientation in {"import", "export", "unknown"}:
        base["lc_type"] = workflow_orientation
        if str(extractor_outputs.get("lc_type") or "").strip().lower() not in LEGACY_WORKFLOW_LC_TYPES:
            base["lc_type_reason"] = "Derived from canonical workflow_orientation."
            base["lc_type_confidence"] = max(float(base.get("lc_type_confidence") or 0.0), 0.85)
            base["lc_type_source"] = "lc_classification"
        return base

    for raw in (
        legacy_payload.get("lc_type"),
        extractor_outputs.get("lc_type"),
    ):
        candidate = str(raw or "").strip().lower()
        if candidate in LEGACY_WORKFLOW_LC_TYPES:
            base["lc_type"] = candidate
            return base

    base["lc_type"] = "unknown"
    if workflow_orientation:
        base["lc_type_reason"] = "Canonical classification does not map to a legacy workflow alias."
        base["lc_type_confidence"] = max(float(base.get("lc_type_confidence") or 0.0), 0.5)
        base["lc_type_source"] = "lc_classification"
    return base


def _normalize_documents_structured(session_documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for idx, doc in enumerate(session_documents or []):
        extracted_fields = doc.get("extracted_fields") or doc.get("extractedFields") or {}
        extracted_fields_alt = doc.get("extractedFields") or doc.get("extracted_fields") or extracted_fields
        discrepancy_count = (
            doc.get("discrepancyCount")
            or doc.get("issues_count")
            or doc.get("issuesCount")
            or doc.get("discrepancy_count")
        )
        issues_count = (
            doc.get("issues_count")
            or doc.get("issuesCount")
            or doc.get("discrepancyCount")
            or doc.get("discrepancy_count")
        )
        ocr_confidence = doc.get("ocrConfidence") or doc.get("ocr_confidence")
        extraction_artifacts_v1 = doc.get("extraction_artifacts_v1") or {
            "version": "extraction_artifacts_v1",
            "raw_text": doc.get("raw_text") or doc.get("raw_text_preview") or "",
            "tables": [],
            "key_value_candidates": [],
            "spans": [],
            "bbox": [],
            "ocr_confidence": ocr_confidence,
        }

        normalized.append(
            {
                "document_id": doc.get("document_id") or doc.get("id") or str(uuid4()),
                "document_type": doc.get("documentType") or doc.get("type") or "supporting_document",
                "filename": doc.get("name") or doc.get("filename") or doc.get("original_filename") or f"Document {idx + 1}",
                "extraction_status": doc.get("extractionStatus") or doc.get("extraction_status") or "unknown",
                "extracted_fields": extracted_fields if extracted_fields is not None else {},
                "extractedFields": extracted_fields_alt if extracted_fields_alt is not None else {},
                "field_details": doc.get("field_details") or doc.get("fieldDetails") or doc.get("_field_details") or {},
                "fieldDetails": doc.get("fieldDetails") or doc.get("field_details") or doc.get("_field_details") or {},
                "discrepancyCount": discrepancy_count,
                "issues_count": issues_count,
                "ocrConfidence": ocr_confidence,
                "review_required": bool(doc.get("review_required") or doc.get("reviewRequired")),
                "reviewRequired": bool(doc.get("review_required") or doc.get("reviewRequired")),
                "review_reasons": doc.get("review_reasons") or doc.get("reviewReasons") or [],
                "reviewReasons": doc.get("review_reasons") or doc.get("reviewReasons") or [],
                "critical_field_states": doc.get("critical_field_states") or doc.get("criticalFieldStates") or {},
                "criticalFieldStates": doc.get("critical_field_states") or doc.get("criticalFieldStates") or {},
                "extraction_artifacts_v1": extraction_artifacts_v1,
            }
        )
    return normalized


def _default_mt700() -> Dict[str, Any]:
    blocks = {
        "27": None,
        "31C": None,
        "31D": None,
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


def _hydrate_mt700_from_extractor_outputs(extractor_outputs: Dict[str, Any]) -> Dict[str, Any]:
    mt700_source = extractor_outputs.get("mt700")
    mt700_payload = dict(mt700_source) if isinstance(mt700_source, dict) else {}
    default_blocks = _default_mt700()["blocks"]
    source_blocks = mt700_payload.get("blocks") if isinstance(mt700_payload.get("blocks"), dict) else {}
    source_raw_blocks = mt700_payload.get("raw") if isinstance(mt700_payload.get("raw"), dict) else {}
    if not source_raw_blocks and isinstance(extractor_outputs.get("mt700_raw"), dict):
        source_raw_blocks = extractor_outputs.get("mt700_raw") or {}
    hydrated_blocks: Dict[str, Any] = {
        key: source_blocks.get(key) if source_blocks.get(key) not in (None, "", [], {}) else source_raw_blocks.get(key)
        for key in default_blocks
    }
    raw_text = mt700_payload.get("raw_text") or extractor_outputs.get("raw_text")

    for key in default_blocks:
        if hydrated_blocks.get(key) not in (None, "", [], {}):
            continue
        if extractor_outputs.get(key) not in (None, "", [], {}):
            hydrated_blocks[key] = extractor_outputs.get(key)
            continue
        if mt700_payload.get(key) not in (None, "", [], {}):
            hydrated_blocks[key] = mt700_payload.get(key)
            continue
        if source_raw_blocks.get(key) not in (None, "", [], {}):
            hydrated_blocks[key] = source_raw_blocks.get(key)

    # Recover block values from raw SWIFT text when mt700 metadata is sparse.
    if raw_text and all(value in (None, "", [], {}) for value in hydrated_blocks.values()):
        for match in re.finditer(
            r"(?ms)^\s*:(\d{2}[A-Z]?):\s*(.*?)\s*(?=^\s*:\d{2}[A-Z]?:|\Z)",
            str(raw_text),
        ):
            field = str(match.group(1) or "").upper()
            if field not in hydrated_blocks:
                continue
            value = str(match.group(2) or "").strip()
            if value:
                hydrated_blocks[field] = value

    if hydrated_blocks.get("46A") in (None, "", [], {}):
        docs_required = _coerce_text_sequence(extractor_outputs.get("documents_required")) or _coerce_text_sequence(
            extractor_outputs.get("required_documents")
        )
        if docs_required:
            hydrated_blocks["46A"] = docs_required

    if hydrated_blocks.get("47A") in (None, "", [], {}):
        additional_conditions = _coerce_text_sequence(extractor_outputs.get("additional_conditions")) or _coerce_text_sequence(
            extractor_outputs.get("clauses")
        )
        if additional_conditions:
            hydrated_blocks["47A"] = additional_conditions

    has_block_content = any(value not in (None, "", [], {}) for value in hydrated_blocks.values())
    if not has_block_content and not raw_text:
        return _default_mt700()

    return {
        "blocks": hydrated_blocks,
        "raw_text": raw_text,
        "version": mt700_payload.get("version") or "mt700_v1",
    }


def _coerce_mt700_date_iso(value: Any) -> Optional[str]:
    text = str(value or "").strip()
    if not text:
        return None
    digits = re.sub(r"\D", "", text)
    if len(digits) < 6:
        return None
    try:
        return datetime.strptime(digits[:6], "%y%m%d").date().isoformat()
    except ValueError:
        return None


def _extract_mt700_timeline_dates(mt700_payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(mt700_payload, dict):
        return {}

    blocks = mt700_payload.get("blocks") if isinstance(mt700_payload.get("blocks"), dict) else {}
    raw_blocks = mt700_payload.get("raw") if isinstance(mt700_payload.get("raw"), dict) else {}
    raw_text = str(mt700_payload.get("raw_text") or "").strip()

    def _block_or_text(block_code: str) -> Optional[str]:
        block_value = blocks.get(block_code)
        if block_value not in (None, "", [], {}):
            return str(block_value).strip() or None
        block_value = raw_blocks.get(block_code)
        if block_value not in (None, "", [], {}):
            return str(block_value).strip() or None
        if not raw_text:
            return None
        match = re.search(rf"(?im)^\s*:{re.escape(block_code)}:\s*([^\r\n]+)", raw_text)
        if not match:
            return None
        value = str(match.group(1) or "").strip()
        return value or None

    issue_raw = _block_or_text("31C")
    expiry_raw = _block_or_text("31D")
    latest_raw = _block_or_text("44C")

    expiry_place = None
    expiry_match = re.match(r"^\s*\d{6}\s*([A-Za-z][A-Za-z\s\-.]{1,})\s*$", str(expiry_raw or "").strip())
    if expiry_match:
        expiry_place = str(expiry_match.group(1) or "").strip().upper() or None

    dates: Dict[str, Any] = {}
    if issue_date := _coerce_mt700_date_iso(issue_raw):
        dates["issue_date"] = issue_date
    if expiry_date := _coerce_mt700_date_iso(expiry_raw):
        dates["expiry_date"] = expiry_date
    if latest_shipment_date := _coerce_mt700_date_iso(latest_raw):
        dates["latest_shipment_date"] = latest_shipment_date
    if expiry_place:
        dates["place_of_expiry"] = expiry_place
    return dates


def _default_timeline(count: int) -> List[Dict[str, Any]]:
    return [
        {
            "title": "Documents Uploaded",
            "status": "success",
            "timestamp": _now_iso(),
            "description": f"{count} document(s) received",
        }
    ]


def _normalize_timeline(raw_timeline: Any, count: int) -> List[Dict[str, Any]]:
    if isinstance(raw_timeline, list):
        return raw_timeline or _default_timeline(count)
    if isinstance(raw_timeline, dict):
        events = raw_timeline.get("events")
        if isinstance(events, list):
            return events or _default_timeline(count)
    return _default_timeline(count)


def _timeline_metadata(raw_timeline: Any) -> Dict[str, Any]:
    if isinstance(raw_timeline, dict):
        return raw_timeline
    return {}


def build_unified_structured_result(
    session_documents: List[Dict[str, Any]],
    extractor_outputs: Optional[Dict[str, Any]] = None,
    legacy_payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Construct Option-E structured_result_v1 without relying on legacy helpers.
    Mirrors lc_structured.documents_structured to top-level documents_structured.
    """

    extractor_outputs = extractor_outputs or {}
    docs_structured = _normalize_documents_structured(session_documents or [])

    mt700_block = _hydrate_mt700_from_extractor_outputs(extractor_outputs)
    goods = extractor_outputs.get("goods", [])
    # Support both canonical name "additional_conditions" and legacy "clauses"
    clauses = (
        extractor_outputs.get("additional_conditions") or 
        extractor_outputs.get("clauses") or 
        extractor_outputs.get("clauses_47a") or 
        []
    )
    documents_required = (
        _coerce_text_sequence(extractor_outputs.get("documents_required"))
        or _coerce_text_sequence(extractor_outputs.get("required_documents"))
    )
    required_document_types = _coerce_text_sequence(extractor_outputs.get("required_document_types"))
    additional_conditions = _coerce_text_sequence(extractor_outputs.get("additional_conditions")) or _coerce_text_sequence(clauses)
    clauses = additional_conditions
    raw_timeline = extractor_outputs.get("timeline")
    timeline = _normalize_timeline(raw_timeline, len(docs_structured))
    timeline_meta = _timeline_metadata(raw_timeline)
    mt700_timeline_dates = _extract_mt700_timeline_dates(mt700_block)
    issues = extractor_outputs.get("issues", [])
    lc_classification = extractor_outputs.get("lc_classification")
    if not isinstance(lc_classification, dict):
        lc_classification = build_lc_classification(extractor_outputs, legacy_payload)
    lc_type_fields = _resolve_legacy_lc_type_fields(extractor_outputs, legacy_payload, lc_classification)
    required_documents_detailed = (
        extractor_outputs.get("required_documents_detailed")
        if isinstance(extractor_outputs.get("required_documents_detailed"), list)
        else (lc_classification or {}).get("required_documents")
    ) or []
    requirement_conditions = _coerce_text_sequence(
        extractor_outputs.get("requirement_conditions")
        or (lc_classification or {}).get("requirement_conditions")
    )
    unmapped_requirements = _coerce_text_sequence(
        extractor_outputs.get("unmapped_requirements")
        or (lc_classification or {}).get("unmapped_requirements")
    )

    # Build dates object from extractor outputs
    dates = {
        "issue": mt700_timeline_dates.get("issue_date")
        or extractor_outputs.get("issue_date")
        or timeline_meta.get("issue_date"),
        "expiry": mt700_timeline_dates.get("expiry_date")
        or extractor_outputs.get("expiry_date")
        or timeline_meta.get("expiry_date"),
        "latest_shipment": mt700_timeline_dates.get("latest_shipment_date")
        or extractor_outputs.get("latest_shipment")
        or extractor_outputs.get("latest_shipment_date")
        or timeline_meta.get("latest_shipment")
        or timeline_meta.get("latest_shipment_date"),
        "place_of_expiry": mt700_timeline_dates.get("place_of_expiry")
        or extractor_outputs.get("place_of_expiry"),
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
        "issue_date": dates.get("issue"),
        "expiry_date": dates.get("expiry"),
        "latest_shipment": dates.get("latest_shipment"),
        "latest_shipment_date": dates.get("latest_shipment"),
        "place_of_expiry": dates.get("place_of_expiry"),
        "amount": extractor_outputs.get("amount"),
        "currency": extractor_outputs.get("currency"),
        "incoterm": extractor_outputs.get("incoterm"),
        "ucp_reference": extractor_outputs.get("ucp_reference"),
        "goods_description": extractor_outputs.get("goods_description"),
        "applicant": extractor_outputs.get("applicant"),
        "beneficiary": extractor_outputs.get("beneficiary"),
        "ports": extractor_outputs.get("ports"),
        "lc_classification": lc_classification,
        "documents_required": documents_required,
        "required_document_types": required_document_types,
        "required_documents_detailed": required_documents_detailed,
        "requirement_conditions": requirement_conditions,
        "unmapped_requirements": unmapped_requirements,
        "additional_conditions": additional_conditions,
        "hs_codes": extractor_outputs.get("hs_codes"),
        "lc_type": lc_type_fields["lc_type"],
        "lc_type_reason": lc_type_fields["lc_type_reason"],
        "lc_type_confidence": lc_type_fields["lc_type_confidence"],
        "lc_type_source": lc_type_fields["lc_type_source"],
        "dates": dates if dates else None,
    }

    processing_summary = {
        "total_documents": len(docs_structured),
        "successful_extractions": 0,
        "failed_extractions": 0,
        "total_issues": len(issues),
        "severity_breakdown": {"critical": 0, "major": 0, "medium": 0, "minor": 0},
        "documents": len(docs_structured),
        "documents_found": len(docs_structured),
        "verified": len(docs_structured),
        "warnings": 0,
        "errors": 0,
        "compliance_rate": 100,
        "processing_time_seconds": None,
        "processing_time_display": None,
        "processing_time_ms": None,
        "extraction_quality": None,
        "discrepancies": None,
    }

    analytics = {
        "extraction_accuracy": None,
        "lc_compliance_score": None,
        "customs_ready_score": None,
        "documents_processed": len(docs_structured),
        "document_status_distribution": None,
        "document_processing": [],
        "performance_insights": [],
        "processing_time_display": None,
        "issue_counts": {"critical": 0, "major": 0, "medium": 0, "minor": 0},
        "compliance_score": 100,
        "customs_risk": None,
    }

    structured_result = {
        "version": OPTION_E_VERSION,
        **lc_type_fields,
        "lc_structured": lc_structured,
        "documents": docs_structured,
        "documents_structured": docs_structured,
        "issues": issues,
        "processing_summary": processing_summary,
        "analytics": analytics,
        "timeline": timeline,
        "ai_enrichment": {"enabled": False, "notes": []},
    }

    return {"structured_result": structured_result}

