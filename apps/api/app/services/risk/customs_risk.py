from __future__ import annotations

from typing import Dict, Any, List

def compute_customs_risk(lc_data: Dict[str, Any], docs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Lightweight heuristic risk score for customs readiness.
    """
    score = 0
    flags: List[str] = []

    # Basic presence checks
    if not lc_data.get("number"):
        score += 15; flags.append("missing_lc_number")
    if not lc_data.get("amount"):
        score += 15; flags.append("missing_amount")
    ports = lc_data.get("ports") or {}
    if not ports.get("loading"):
        score += 10; flags.append("missing_port_loading")
    if not ports.get("discharge"):
        score += 10; flags.append("missing_port_discharge")
    if not lc_data.get("goods"):
        score += 10; flags.append("missing_goods_lines")
    if not lc_data.get("documents_required"):
        score += 8; flags.append("missing_documents_required")

    # HS code heuristic
    hs = lc_data.get("hs_codes", [])
    if not hs:
        score += 8; flags.append("missing_hs_codes")

    # Clip score 0-100
    score = max(0, min(100, score))
    tier = "low"
    if score >= 50:
        tier = "high"
    elif score >= 25:
        tier = "medium"

    return {"score": score, "tier": tier, "flags": flags}
