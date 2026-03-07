from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List


def _iter_docs(structured_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    candidates = [
        (structured_result.get("processing_summary_v2") or {}).get("documents"),
        (structured_result.get("processing_summary") or {}).get("documents"),
        structured_result.get("documents"),
        structured_result.get("documents_structured"),
    ]
    for docs in candidates:
        if isinstance(docs, list):
            return [d for d in docs if isinstance(d, dict)]
    return []


def build_day1_metrics(structured_result: Dict[str, Any]) -> Dict[str, Any]:
    docs = _iter_docs(structured_result if isinstance(structured_result, dict) else {})
    code_counter: Counter[str] = Counter()
    status_counter: Counter[str] = Counter()

    for doc in docs:
        status_counter[str(doc.get("extraction_status") or "unknown")] += 1
        runtime = doc.get("day1_runtime") if isinstance(doc.get("day1_runtime"), dict) else {}
        for code in runtime.get("errors") or []:
            if isinstance(code, str) and code:
                code_counter[code] += 1

    return {
        "documents_total": len(docs),
        "status_counts": dict(status_counter),
        "reason_code_counts": dict(code_counter),
        "ret_no_hit": int(code_counter.get("RET_NO_HIT", 0)),
        "ret_low_relevance": int(code_counter.get("RET_LOW_RELEVANCE", 0)),
    }
