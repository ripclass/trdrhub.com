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

