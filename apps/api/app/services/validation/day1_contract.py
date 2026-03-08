from __future__ import annotations

from typing import Any, Dict, List

from app.services.validation.day1_configs import load_day1_reason_codes
from app.services.validation.day1_telemetry import build_day1_metrics


def _extract_documents_with_source(structured_result: Dict[str, Any]) -> tuple[List[Dict[str, Any]], str]:
    candidates = [
        ("processing_summary_v2.documents", (structured_result.get("processing_summary_v2") or {}).get("documents")),
        ("processing_summary.documents", (structured_result.get("processing_summary") or {}).get("documents")),
        ("documents", structured_result.get("documents")),
    ]
    for source, docs in candidates:
        if isinstance(docs, list):
            return [d for d in docs if isinstance(d, dict)], source
    return [], "none"


def enforce_day1_response_contract(structured_result: Dict[str, Any]) -> Dict[str, Any]:
    """Apply Day-1 response hardening without breaking legacy response format.

    - Ensures runtime extraction safety flags are surfaced.
    - Downgrades unsafe per-document success states.
    - Adds machine-readable contract block + warnings.
    """
    if not isinstance(structured_result, dict):
        return structured_result

    docs, documents_source = _extract_documents_with_source(structured_result)
    reason_cfg = load_day1_reason_codes()
    allowed = set((reason_cfg.get("reason_code_enum_v1") or {}).get("values") or [])

    warnings = list(structured_result.get("_contract_warnings") or [])
    violations: List[Dict[str, Any]] = []
    per_doc_debug: List[Dict[str, Any]] = []

    for doc in docs:
        runtime = doc.get("day1_runtime") if isinstance(doc.get("day1_runtime"), dict) else {}
        if not runtime and isinstance(doc.get("day1Runtime"), dict):
            runtime = doc.get("day1Runtime")
        coverage = int(runtime.get("coverage") or 0)
        threshold = int(runtime.get("threshold") or 5)
        schema_ok = bool(runtime.get("schema_ok", True))
        errors = runtime.get("errors") if isinstance(runtime.get("errors"), list) else []

        status_before = str(doc.get("extraction_status") or "unknown")
        if status_before == "success" and (coverage < threshold or not schema_ok):
            doc["extraction_status"] = "partial"
            doc.setdefault("downgrade_reason", "day1_contract_guard")
        status_after = str(doc.get("extraction_status") or status_before)

        doc_violation_codes: List[str] = []
        if coverage < threshold:
            violations.append({
                "document": doc.get("filename"),
                "code": "QA_REQUIRED_FIELD_EMPTY",
                "detail": f"coverage {coverage}/{threshold}",
            })
            doc_violation_codes.append("QA_REQUIRED_FIELD_EMPTY")
        if not schema_ok:
            violations.append({
                "document": doc.get("filename"),
                "code": "PRM_OUTPUT_SCHEMA_VIOLATION",
                "detail": "day1 schema check failed",
            })
            doc_violation_codes.append("PRM_OUTPUT_SCHEMA_VIOLATION")

        for code in errors:
            if isinstance(code, str) and code not in allowed:
                violations.append({
                    "document": doc.get("filename"),
                    "code": "SYS_UNKNOWN",
                    "detail": f"unmapped_reason_code:{code}",
                })
                doc_violation_codes.append("SYS_UNKNOWN")

        per_doc_debug.append({
            "filename": doc.get("filename"),
            "document_type": doc.get("document_type"),
            "runtime_present": bool(runtime),
            "coverage": coverage,
            "threshold": threshold,
            "active_fields": runtime.get("active_fields") if isinstance(runtime.get("active_fields"), list) else [],
            "schema_ok": schema_ok,
            "fallback_stage": runtime.get("fallback_stage"),
            "errors": [str(code) for code in errors if isinstance(code, str)],
            "extraction_status_before": status_before,
            "extraction_status_after": status_after,
            "contract_violation_codes": sorted(set(doc_violation_codes)),
        })

    status = "pass"
    if violations:
        status = "review"

    contract_block = {
        "version": "1.0.0",
        "status": status,
        "violations": violations,
        "documents_checked": len(docs),
    }
    structured_result["_day1_contract"] = contract_block
    structured_result["_day1_contract_debug"] = {
        "documents_source": documents_source,
        "documents_checked": len(docs),
        "per_doc": per_doc_debug,
    }

    metrics = build_day1_metrics(structured_result)
    structured_result["_day1_metrics"] = metrics

    if violations:
        warnings.append(f"day1_contract: {len(violations)} violations")
    warnings.append(
        f"day1_metrics: RET_NO_HIT={metrics.get('ret_no_hit', 0)} RET_LOW_RELEVANCE={metrics.get('ret_low_relevance', 0)}"
    )
    structured_result["_contract_warnings"] = warnings

    return structured_result
