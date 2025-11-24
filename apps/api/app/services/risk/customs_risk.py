from __future__ import annotations

from typing import Any, Dict, List


def compute_customs_risk_from_option_e(structured_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute a lightweight customs readiness risk score using Option-E structured_result_v1.
    """

    lc_structured = structured_result.get("lc_structured") or {}
    mt_blocks = (lc_structured.get("mt700") or {}).get("blocks") or {}
    goods = lc_structured.get("goods") or []
    documents = (
        lc_structured.get("documents_structured")
        or structured_result.get("documents_structured")
        or []
    )

    flags: List[str] = []

    def _flag_missing(field: str, key: str) -> None:
        if not mt_blocks.get(key):
            flags.append(field)

    _flag_missing("missing_lc_number", "27")
    _flag_missing("missing_amount", "32B")
    _flag_missing("missing_port_loading", "44E")
    _flag_missing("missing_port_discharge", "44F")

    if not goods:
        flags.append("missing_goods_lines")

    required_types = {"commercial_invoice", "packing_list", "certificate_of_origin"}
    present_types = {doc.get("document_type") for doc in documents if doc.get("document_type")}
    for doc_type in required_types:
        if doc_type not in present_types:
            flags.append(f"missing_{doc_type}")

    base_score = 20
    score = base_score + min(80, 10 * len(flags))
    tier = "low"
    if score >= 67:
        tier = "high"
    elif score >= 34:
        tier = "med"

    return {"score": score, "tier": tier, "flags": flags}
