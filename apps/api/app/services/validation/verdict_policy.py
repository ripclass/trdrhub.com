"""
Verdict Policy Layer

Ensures consistent verdict surfaces between structured_result and SME responses.
This module is intentionally isolated to avoid coupling with response builders.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


SME_STATUS_PASS = "PASS"
SME_STATUS_FIX_REQUIRED = "FIX_REQUIRED"
SME_STATUS_LIKELY_REJECT = "LIKELY_REJECT"
SME_STATUS_MISSING_DOCS = "MISSING_DOCS"

SME_STATUS_ORDER = {
    SME_STATUS_PASS: 0,
    SME_STATUS_FIX_REQUIRED: 1,
    SME_STATUS_LIKELY_REJECT: 2,
    SME_STATUS_MISSING_DOCS: 3,
}

BANK_TO_SME_STATUS = {
    "REJECT": SME_STATUS_LIKELY_REJECT,
    "HOLD": SME_STATUS_LIKELY_REJECT,
    "CAUTION": SME_STATUS_FIX_REQUIRED,
    "SUBMIT": SME_STATUS_PASS,
}


def normalize_bank_verdict(bank_verdict: Optional[Any]) -> Optional[str]:
    if not bank_verdict:
        return None
    if isinstance(bank_verdict, dict):
        verdict = bank_verdict.get("verdict")
    else:
        verdict = bank_verdict
    if not verdict:
        return None
    return str(verdict).strip().upper()


def base_sme_status(
    critical_count: int,
    major_count: int,
    minor_count: int,
    missing_docs_count: int,
) -> str:
    if missing_docs_count > 0:
        return SME_STATUS_MISSING_DOCS
    if critical_count > 0:
        return SME_STATUS_LIKELY_REJECT
    if major_count > 0:
        return SME_STATUS_FIX_REQUIRED
    if minor_count > 0:
        return SME_STATUS_FIX_REQUIRED
    return SME_STATUS_PASS


def resolve_sme_verdict_status(
    critical_count: int,
    major_count: int,
    minor_count: int,
    missing_docs_count: int,
    bank_verdict: Optional[Any] = None,
) -> str:
    """
    Resolve the SME verdict status, enforcing consistency with bank verdict.

    Returns one of: PASS, FIX_REQUIRED, LIKELY_REJECT, MISSING_DOCS.
    """
    base_status = base_sme_status(
        critical_count=critical_count,
        major_count=major_count,
        minor_count=minor_count,
        missing_docs_count=missing_docs_count,
    )

    normalized_bank = normalize_bank_verdict(bank_verdict)
    mapped_status = BANK_TO_SME_STATUS.get(normalized_bank) if normalized_bank else None
    if mapped_status:
        return _max_status(base_status, mapped_status)

    return base_status


def _max_status(left: str, right: str) -> str:
    left_score = SME_STATUS_ORDER.get(left, 0)
    right_score = SME_STATUS_ORDER.get(right, 0)
    return left if left_score >= right_score else right
