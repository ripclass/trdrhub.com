from __future__ import annotations

from typing import Any, Dict, List

from app.services.validation.day1_configs import load_day1_reason_codes
from app.services.validation.day1_telemetry import build_day1_metrics


def _extract_documents(structured_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    candidates = [
        (structured_result.get("processing_summary_v2") or {}).get("documents"),
        (structured_result.get("processing_summary") or {}).get("documents"),
        structured_result.get("documents"),
    ]
    for docs in candidates:
        if isinstance(docs, list):
            return [d for d in docs if isinstance(d, dict)]
    return []


def enforce_day1_response_contract(structured_result: Dict[str, Any]) -> Dict[str, Any]:
    """Apply Day-1 response hardening without breaking legacy response format.

    - Ensures runtime extraction safety flags are surfaced.
    - Downgrades unsafe per-document success states.
    - Adds machine-readable contract block + warnings.
    """
    if not isinstance(structured_result, dict):
        return structured_result

    docs = _extract_documents(structured_result)
    reason_cfg = load_day1_reason_codes()
    allowed = set((reason_cfg.get("reason_code_enum_v1") or {}).get("values") or [])

    warnings = list(structured_result.get("_contract_warnings") or [])
    violations: List[Dict[str, Any]] = []

    for doc in docs:
        runtime = doc.get("day1_runtime") if isinstance(doc.get("day1_runtime"), dict) else {}
        if not runtime and isinstance(doc.get("day1Runtime"), dict):
            runtime = doc.get("day1Runtime")
        coverage = int(runtime.get("coverage") or 0)
        threshold = int(runtime.get("threshold") or 5)
        schema_ok = bool(runtime.get("schema_ok", True))
        errors = runtime.get("errors") if isinstance(runtime.get("errors"), list) else []

        status = str(doc.get("extraction_status") or "unknown")
        if status == "success" and (coverage < threshold or not schema_ok):
            doc["extraction_status"] = "partial"
            doc.setdefault("downgrade_reason", "day1_contract_guard")

        if coverage < threshold:
            violations.append({
                "document": doc.get("filename"),
                "code": "QA_REQUIRED_FIELD_EMPTY",
                "detail": f"coverage {coverage}/{threshold}",
            })
        if not schema_ok:
            violations.append({
                "document": doc.get("filename"),
                "code": "PRM_OUTPUT_SCHEMA_VIOLATION",
                "detail": "day1 schema check failed",
            })

        for code in errors:
            if isinstance(code, str) and code not in allowed:
                violations.append({
                    "document": doc.get("filename"),
                    "code": "SYS_UNKNOWN",
                    "detail": f"unmapped_reason_code:{code}",
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

    metrics = build_day1_metrics(structured_result)
    structured_result["_day1_metrics"] = metrics

    if violations:
        warnings.append(f"day1_contract: {len(violations)} violations")
    warnings.append(
        f"day1_metrics: RET_NO_HIT={metrics.get('ret_no_hit', 0)} RET_LOW_RELEVANCE={metrics.get('ret_low_relevance', 0)}"
    )
    structured_result["_contract_warnings"] = warnings

    return structured_result
