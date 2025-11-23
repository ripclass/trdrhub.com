# apps/api/app/services/risk/customs_risk.py

from typing import Dict, Any


def compute_customs_risk(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Rule-based quick score (0–100). Start simple; expand with models later.
    """
    score, reasons = 10, []  # base 10 (never zero)

    lc = result.get("lc_data", {})
    clauses = lc.get("clauses", {})
    addl = clauses.get("additional_conditions_structured", [])
    hs = lc.get("goods", {}).get("hs", {})
    ports = lc.get("ports", {})

    # HS diversity
    n_hs = len(hs.get("hs6", []))
    if n_hs == 0:
        score += 25
        reasons.append("no_hs_detected")
    elif n_hs > 3:
        score += 10
        reasons.append("multi_hs_mixture")

    # Sensitive clauses
    tokens = " ".join([t["code"] for item in addl for t in item.get("tokens", [])]) if addl else ""

    if "auth_corrections" in tokens:
        score += 5
        reasons.append("auth_corrections_required")

    if "third_party_docs" in tokens:
        score += 7
        reasons.append("third_party_docs_allowed")

    if "flag_restriction" in tokens:
        score += 4
        reasons.append("flag_restriction_present")

    # Ports mismatch heuristic
    if ports.get("loading") and ports.get("discharge"):
        if ports["loading"].split(",")[-1].strip().lower() == ports["discharge"].split(",")[-1].strip().lower():
            score += 8
            reasons.append("same_country_route")

    # Document coverage (missing docs => risk)
    # Check extracted_data for document presence
    extracted_docs = result.get("extracted_data", {})
    required_keys = ["invoice", "bill_of_lading", "packing_list", "certificate_of_origin"]
    missing = []
    
    for key in required_keys:
        # Check if document exists in extracted_data (can be dict or any truthy value)
        if key not in extracted_docs or not extracted_docs.get(key):
            missing.append(key)
    
    if missing:
        score += 15
        reasons.append(f"missing_docs:{','.join(missing)}")

    # Clamp
    score = max(0, min(100, score))
    rating = "low" if score < 25 else "medium" if score < 60 else "high"

    return {"score": score, "rating": rating, "reasons": reasons}

