"""Hybrid AI + rules arbitration (shadow and enforced modes)."""

from typing import Any, Dict, List, Optional

LOW_CONFIDENCE_THRESHOLD = 0.6


def _coerce_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        if isinstance(value, bool):
            return float(value)
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            normalized = value.replace(",", "").strip()
            if not normalized:
                return None
            return float(normalized)
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_verdict(verdict: Optional[str]) -> str:
    token = str(verdict or "").strip().lower()
    if token in {"submit", "pass", "approved", "ok"}:
        return "pass"
    if token in {"caution", "hold", "review", "warn", "warning"}:
        return "review"
    if token in {"reject", "blocked", "fail", "non_compliant"}:
        return "reject"
    return "review"


def compute_arbitration_decision(
    *,
    ai_verdict: Optional[str],
    ruleset_verdict: Optional[str],
    blocking_rules: Optional[List[str]] = None,
    extraction_confidence: Optional[float] = None,
    mode: str = "hybrid_shadow",
) -> Dict[str, Any]:
    """Compute arbitration outcome for shadow/enforced modes."""
    normalized_mode = str(mode or "hybrid_shadow").strip().lower()
    enforced = normalized_mode == "hybrid_enforced"

    ai_norm = normalize_verdict(ai_verdict)
    rules_norm = normalize_verdict(ruleset_verdict)
    blocking = [str(x) for x in (blocking_rules or []) if x]
    extraction_confidence_value = _coerce_float(extraction_confidence)

    if extraction_confidence_value is not None and extraction_confidence_value < LOW_CONFIDENCE_THRESHOLD:
        arbitration = "review"
        reason = "low_extraction_confidence"
    elif blocking:
        arbitration = "reject"
        reason = "rules_critical_fail"
    elif ai_norm == "reject" and rules_norm == "pass":
        arbitration = "review"
        reason = "ai_reject_rules_clean"
    elif ai_norm == "pass" and rules_norm == "pass":
        arbitration = "pass"
        reason = "ai_and_rules_pass"
    elif rules_norm == "reject":
        arbitration = "reject"
        reason = "rules_reject"
    else:
        arbitration = "review"
        reason = "default_review"

    return {
        "mode": normalized_mode,
        "enforced": enforced,
        "ai_verdict": ai_norm,
        "ruleset_verdict": rules_norm,
        "arbitration_verdict": arbitration,
        "arbitration_reason": reason,
        "blocking_rules": blocking,
        "extraction_confidence": extraction_confidence_value,
        "thresholds": {"low_extraction_confidence": LOW_CONFIDENCE_THRESHOLD},
        "enforcement_applied": enforced,
    }


def compute_shadow_arbitration(
    *,
    ai_verdict: Optional[str],
    ruleset_verdict: Optional[str],
    blocking_rules: Optional[List[str]] = None,
    extraction_confidence: Optional[float] = None,
    mode: str = "hybrid_shadow",
) -> Dict[str, Any]:
    """Backward-compatible wrapper kept for existing callers/tests."""
    return compute_arbitration_decision(
        ai_verdict=ai_verdict,
        ruleset_verdict=ruleset_verdict,
        blocking_rules=blocking_rules,
        extraction_confidence=extraction_confidence,
        mode=mode,
    )
