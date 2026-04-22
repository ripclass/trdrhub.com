"""
Bank precheck — tightened verdict layer over a completed validation.

The regular validation pipeline applies an examiner + veto at thresholds
calibrated for the importer's standard flow. A bank precheck asks:
"would this presentation survive a strict-mode bank examiner right now?"
so the thresholds are deliberately tighter. A single major finding that
would normally land as a review-needed warning escalates to review under
precheck; any critical lands as reject.

This is a deterministic computation over the existing findings set — it
does NOT re-run the LLM. The idea is to give the importer a fast,
cheap, tighter view without burning another pipeline run.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def _normalize_severity(value: Optional[str]) -> str:
    if not value:
        return "minor"
    low = str(value).strip().lower()
    if low in {"critical", "high", "fail", "blocker"}:
        return "critical"
    if low in {"major", "warning", "warn", "medium"}:
        return "major"
    if low in {"info", "informational", "advisory"}:
        return "info"
    return "minor"


def compute_precheck_verdict(findings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Return a dict ``{precheck_verdict, counts}`` for the given findings.

    Threshold ladder (deliberately tighter than the normal pipeline):
      * ≥1 critical   → reject
      * ≥2 major      → review
      * ≥3 minor      → review
      * 1 major only  → review  (normal pipeline treats this as pass)
      * otherwise     → approve
    """
    critical = 0
    major = 0
    minor = 0
    info = 0
    for f in findings or []:
        if not isinstance(f, dict):
            continue
        sev = _normalize_severity(f.get("severity"))
        if sev == "critical":
            critical += 1
        elif sev == "major":
            major += 1
        elif sev == "info":
            info += 1
        else:
            minor += 1

    if critical > 0:
        verdict = "reject"
    elif major >= 1 or minor >= 3:
        verdict = "review"
    else:
        verdict = "approve"

    return {
        "precheck_verdict": verdict,
        "counts": {
            "critical": critical,
            "major": major,
            "minor": minor,
            "info": info,
        },
    }


def build_memo(
    session: Any,
    verdict_payload: Dict[str, Any],
    bank_name: Optional[str],
    notes: Optional[str],
) -> str:
    counts = verdict_payload["counts"]
    lines = [
        "Bank Precheck Memo",
        f"Session: {getattr(session, 'id', '')}",
        f"Bank: {bank_name or '—'}",
        f"Verdict: {verdict_payload['precheck_verdict'].upper()}",
        (
            f"Findings: {counts['critical']} critical · "
            f"{counts['major']} major · {counts['minor']} minor"
        ),
    ]
    if notes:
        lines.append("")
        lines.append(f"Operator notes: {notes}")
    return "\n".join(lines)
