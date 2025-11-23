from __future__ import annotations

import re

from typing import Dict, Any, List, Optional, Tuple

from .docs_46a_parser import parse_46a_block
from .clauses_47a_parser import parse_47a_block
from .hs_code_extractor import extract_hs_codes
from ..parsers.swift_mt700 import parse_mt700_core

LC_NO_RE = re.compile(r"\b(?:LC|L/C|Letter of Credit).*?\b(?:No\.?|Number)\s*[:\-]?\s*([A-Z0-9\-\/]+)", re.I | re.S)
AMOUNT_RE = re.compile(r"\b(?:amount|lc amount|face value)\b[^\d]*([\d.,]+)", re.I)
INCOTERM_RE = re.compile(r"\b(?:Incoterm|Trade Term)\b[^A-Z0-9]*(EXW|FCA|CPT|CIP|DAP|DPU|DDP|FAS|FOB|CFR|CIF)\b[^\n]*", re.I)
PORT_LOAD_RE = re.compile(r"(?:Port of Loading|POL|Loading Port)\s*[:\-]?\s*([^\n]+)", re.I)
PORT_DISC_RE = re.compile(r"(?:Port of Discharge|POD|Discharge Port|Destination Port)\s*[:\-]?\s*([^\n]+)", re.I)
APPLICANT_RE = re.compile(r"\bApplicant\b[^\S\r\n]*[:\-]?\s*(.*?)(?:\n{1,2}|$)", re.I)
BENEFICIARY_RE = re.compile(r"\bBeneficiary\b[^\S\r\n]*[:\-]?\s*(.*?)(?:\n{1,2}|$)", re.I)

def _strip(s: Optional[str]) -> Optional[str]:
    return s.strip() if isinstance(s, str) else s

def _first(rx: re.Pattern, text: str) -> Optional[str]:
    m = rx.search(text or "")
    return _strip(m.group(1)) if m else None

def _amount(text: str) -> Optional[str]:
    v = _first(AMOUNT_RE, text)
    if not v:
        return None
    return v.replace(",", "")

def _parse_parties(text: str) -> Tuple[Optional[str], Optional[str]]:
    a = _first(APPLICANT_RE, text)
    b = _first(BENEFICIARY_RE, text)
    return a, b

def extract_lc_structured(raw_text: str) -> Dict[str, Any]:
    """
    Top-level extraction orchestrator. Works with LC PDFs converted to text or OCR text.

    Returns a clean, structured dict (no messy narrative blobs).
    """

    text = raw_text or ""

    # 1) Try SWIFT MT700 core first (if present)
    mt = parse_mt700_core(text)

    # 2) Generic fields (fallback or supplement)
    lc_number = mt.get("number") or _first(LC_NO_RE, text)
    amount_raw = mt.get("amount") or _amount(text)
    incoterm_line = mt.get("incoterm_line") or _first(INCOTERM_RE, text)
    pol = mt.get("ports", {}).get("loading") or _first(PORT_LOAD_RE, text)
    pod = mt.get("ports", {}).get("discharge") or _first(PORT_DISC_RE, text)
    applicant_line, beneficiary_line = _parse_parties(text)
    applicant = mt.get("applicant") or ({"name": _strip(applicant_line)} if applicant_line else None)
    beneficiary = mt.get("beneficiary") or ({"name": _strip(beneficiary_line)} if beneficiary_line else None)

    # 3) Parse documentary sections (46A & 47A), plus goods normalization + HS codes
    docs46a = parse_46a_block(text)
    clauses47a = parse_47a_block(text)
    goods = docs46a.get("goods", [])
    hs_codes = extract_hs_codes("\n".join([g.get("line", "") for g in goods]) + "\n" + text)

    # 4) Compose structured result (NO large narrative blobs here)
    lc_structured: Dict[str, Any] = {
        "number": lc_number,
        "amount": {"value": amount_raw} if amount_raw else None,
        "applicant": applicant,
        "beneficiary": beneficiary,
        "ports": {"loading": _strip(pol), "discharge": _strip(pod)},
        "incoterm": _strip(incoterm_line),
        "goods": goods,
        "hs_codes": hs_codes,
        "documents_required": docs46a.get("documents_required", []),
        "clauses_47a": clauses47a.get("conditions", []),
        "ucp_reference": mt.get("ucp_reference") or "UCP LATEST VERSION",
        "timeline": {
            "latest_shipment": docs46a.get("latest_shipment"),
            "issue_date": mt.get("issue_date"),
            "expiry_date": mt.get("expiry_date"),
        },
        "source": {
            "parsers": ["mt700_core", "regex_core", "46A_parser", "47A_parser", "hs_code_extractor"],
            "version": "lc_extractor_v1",
        },
    }

    # Cleanup None keys
    return {k: v for k, v in lc_structured.items() if v not in (None, [], {})}
