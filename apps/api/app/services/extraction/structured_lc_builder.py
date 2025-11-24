from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

OPTION_E_VERSION = "structured_result_v1"


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _safe(value: Any, default: Any = None) -> Any:
    return value if value not in (None, "") else default


def _pluck_lc_type(extractor_outputs: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not extractor_outputs:
        return {
            "lc_type": "unknown",
            "lc_type_reason": "Extractor outputs not provided.",
            "lc_type_confidence": 0,
            "lc_type_source": "auto",
        }

    return {
        "lc_type": extractor_outputs.get("lc_type", "unknown"),
        "lc_type_reason": extractor_outputs.get("lc_type_reason", "Insufficient details."),
        "lc_type_confidence": int(_safe(extractor_outputs.get("lc_type_confidence"), 0) or 0),
        "lc_type_source": extractor_outputs.get("lc_type_source", "auto"),
    }


def _normalize_documents_structured(session_documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for idx, doc in enumerate(session_documents or []):
        normalized.append(
            {
                "document_id": doc.get("document_id") or doc.get("id") or str(uuid4()),
                "document_type": doc.get("documentType") or doc.get("type") or "supporting_document",
                "filename": doc.get("name") or doc.get("filename") or doc.get("original_filename") or f"Document {idx + 1}",
                "extraction_status": doc.get("extractionStatus") or doc.get("extraction_status") or "unknown",
                "extracted_fields": doc.get("extractedFields") or doc.get("extracted_fields") or {},
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

    extractor_outputs = extractor_outputs or {}
    docs_structured = _normalize_documents_structured(session_documents or [])
    lc_type_fields = _pluck_lc_type(extractor_outputs)

    mt700_block = extractor_outputs.get("mt700") or _default_mt700()
    goods = extractor_outputs.get("goods", [])
    clauses = extractor_outputs.get("clauses", [])
    timeline = extractor_outputs.get("timeline") or _default_timeline(len(docs_structured))
    issues = extractor_outputs.get("issues", [])

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
        "documents_structured": docs_structured,
        "issues": issues,
        "processing_summary": processing_summary,
        "analytics": analytics,
        "ai_enrichment": {"enabled": False, "notes": []},
    }

    return {"structured_result": structured_result}

