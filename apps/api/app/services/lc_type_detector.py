from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

LCFamily = str  # "mt" | "iso" | "unknown"


_MT_SIGNAL_WEIGHTS: Tuple[Tuple[re.Pattern[str], float, str], ...] = (
    (re.compile(r"(?m)^\s*:[0-9]{2}[A-Z]?:"), 3.0, "swift-tag-block"),
    (re.compile(r"\bMT\s?7(?:00|01|07|10|20|40|47|60|67|68|69|99)\b", re.IGNORECASE), 2.5, "mt7xx-message-type"),
    (re.compile(r"\bSWIFT\b", re.IGNORECASE), 1.5, "swift-keyword"),
    (re.compile(r"\{1:F01[A-Z0-9]{8}", re.IGNORECASE), 2.0, "swift-fin-header"),
)


_ISO_SIGNAL_WEIGHTS: Tuple[Tuple[re.Pattern[str], float, str], ...] = (
    (re.compile(r"<\?xml", re.IGNORECASE), 1.0, "xml-prolog"),
    (re.compile(r"<\s*Document\b", re.IGNORECASE), 2.0, "document-root"),
    (re.compile(r"urn:iso:std:iso:20022", re.IGNORECASE), 4.0, "iso20022-namespace"),
    (re.compile(r"\b(?:tsmt|camt|auth|pacs)\.\d{3}", re.IGNORECASE), 3.0, "iso-message-definition"),
    (re.compile(r"\bISO\s*20022\b", re.IGNORECASE), 2.0, "iso20022-keyword"),
    (re.compile(r"\bMX\b", re.IGNORECASE), 1.0, "mx-keyword"),
    (re.compile(r"<\s*(?:DocumentaryCredit|DocumentaryCreditNotification|DocumentaryCreditAmendment|Undertaking|ExpiryDate)\b", re.IGNORECASE), 3.0, "doc-credit-xml-components"),
    (re.compile(r"<\s*(?:Applicant|Beneficiary|IssuingBank|AdvisingBank|DocumentaryCreditNumber|ExpiryDt|Aplcnt|Bnfcry|IssgBk|AdvgBk)\b", re.IGNORECASE), 2.0, "party-xml-components"),
)


def _coalesce_text(lc_context: Dict[str, Any]) -> str:
    candidate_fields = [
        lc_context.get("raw_text"),
        lc_context.get("text"),
        lc_context.get("content"),
        lc_context.get("lc_text"),
        lc_context.get("message"),
    ]

    mt700 = lc_context.get("mt700")
    if isinstance(mt700, dict):
        candidate_fields.append(mt700.get("raw_text"))

    return "\n".join(str(v) for v in candidate_fields if isinstance(v, (str, bytes)) and v)


def _score_signals(text: str, signals: Tuple[Tuple[re.Pattern[str], float, str], ...]) -> Tuple[float, List[str]]:
    score = 0.0
    evidence: List[str] = []
    for pattern, weight, label in signals:
        if pattern.search(text):
            score += weight
            evidence.append(label)
    return score, evidence


def detect_lc_family(lc_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Detect the documentary-credit message family.

    Returns:
        {
          "family": "mt" | "iso" | "unknown",
          "confidence": float,
          "mt_score": float,
          "iso_score": float,
          "evidence": [str, ...],
        }
    """
    lc_context = lc_data or {}
    declared_format = str(lc_context.get("format") or "").strip().lower()

    text = _coalesce_text(lc_context)
    mt_score, mt_evidence = _score_signals(text, _MT_SIGNAL_WEIGHTS)
    iso_score, iso_evidence = _score_signals(text, _ISO_SIGNAL_WEIGHTS)

    if declared_format in {"mt700", "swift", "mt"}:
        mt_score += 2.0
        mt_evidence.append("declared-format-mt")
    elif declared_format in {"iso20022", "iso", "mx"}:
        iso_score += 2.0
        iso_evidence.append("declared-format-iso")

    family: LCFamily = "unknown"
    confidence = 0.0
    evidence: List[str] = []

    if iso_score >= 4.0 and iso_score > mt_score + 1.0:
        family = "iso"
        confidence = min(0.98, 0.45 + (iso_score - mt_score) * 0.08)
        evidence = iso_evidence
    elif mt_score >= 4.0 and mt_score > iso_score + 1.0:
        family = "mt"
        confidence = min(0.98, 0.45 + (mt_score - iso_score) * 0.08)
        evidence = mt_evidence

    return {
        "family": family,
        "confidence": round(confidence, 2),
        "mt_score": round(mt_score, 2),
        "iso_score": round(iso_score, 2),
        "evidence": evidence,
    }
