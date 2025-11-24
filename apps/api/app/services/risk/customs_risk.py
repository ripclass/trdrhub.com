from __future__ import annotations

from typing import Any, Dict, List


def compute_customs_risk(structured_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Lightweight heuristic risk score derived from Option-E structured_result.
    """

    lc_structured = structured_result.get("lc_structured", {}) or {}
    documents = structured_result.get("documents_structured", []) or []
    score = 0
    flags: List[str] = []

    mt700_fields = lc_structured.get("mt700", {}).get("blocks", {}) or {}
    goods = lc_structured.get("goods") or []

    if not mt700_fields.get("20"):
        score += 15
        flags.append("missing_lc_reference")
    if not mt700_fields.get("32B"):
        score += 15
        flags.append("missing_amount")
    if not goods:
        score += 10
        flags.append("missing_goods_lines")
    if not lc_structured.get("clauses"):
        score += 5
        flags.append("missing_clauses")

    # document coverage
    required_types = {"letter_of_credit", "commercial_invoice", "bill_of_lading"}
    present_types = {doc.get("document_type") for doc in documents}
    for required in required_types:
        if required not in present_types:
            score += 10
            flags.append(f"missing_{required}")

    score = max(0, min(100, score))
    if score >= 50:
        tier = "high"
    elif score >= 25:
        tier = "medium"
    else:
        tier = "low"

    return {"score": score, "tier": tier, "flags": flags}
