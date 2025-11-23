from __future__ import annotations

import re

from typing import Dict, Any, List, Optional, Tuple

from .docs_46a_parser import parse_46a_block, extract_46a_text
from .clauses_47a_parser import parse_47a_block
from .hs_code_extractor import extract_hs_codes
from .goods_46a_parser import parse_goods_46a
from .swift_mt700_full import parse_mt700_full
from ..parsers.swift_mt700 import parse_mt700_core  # Keep for fallback

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

    # 1) Try SWIFT MT700 full parser first (if present)
    mt_full = None
    try:
        mt_full = parse_mt700_full(text)
    except Exception:
        mt_full = None

    # Fallback to core parser if full parser fails or returns empty
    mt_core = {}
    if not mt_full or not mt_full.get("fields"):
        try:
            mt_core = parse_mt700_core(text) or {}
        except Exception:
            mt_core = {}

    # Extract fields from full parser or fallback to core/generic
    mt_fields = mt_full.get("fields", {}) if mt_full else {}
    
    # LC number
    lc_number = (
        mt_fields.get("reference") or 
        (mt_core.get("number") if mt_core else None) or 
        _first(LC_NO_RE, text)
    )
    
    # Amount
    credit_amount = mt_fields.get("credit_amount")
    if credit_amount and isinstance(credit_amount, dict):
        amount_raw = str(credit_amount.get("amount", ""))
    else:
        amount_raw = (mt_core.get("amount") if mt_core else None) or _amount(text)
    
    # Incoterm
    incoterm_line = _first(INCOTERM_RE, text)
    
    # Ports
    shipment_details = mt_fields.get("shipment_details", {})
    pol_raw = shipment_details.get("port_of_loading_airport_of_departure")
    # Handle list values (repeatable tags)
    if isinstance(pol_raw, list):
        pol_raw = pol_raw[0] if pol_raw else None
    pol = (
        pol_raw or
        (mt_core.get("ports", {}) if mt_core else {}).get("loading") or
        _first(PORT_LOAD_RE, text)
    )
    pod_raw = shipment_details.get("port_of_discharge_airport_of_destination")
    # Handle list values (repeatable tags)
    if isinstance(pod_raw, list):
        pod_raw = pod_raw[0] if pod_raw else None
    pod = (
        pod_raw or
        (mt_core.get("ports", {}) if mt_core else {}).get("discharge") or
        _first(PORT_DISC_RE, text)
    )
    
    # Applicant / Beneficiary
    applicant_raw = mt_fields.get("applicant") or (mt_core.get("applicant") if mt_core else None)
    beneficiary_raw = mt_fields.get("beneficiary") or (mt_core.get("beneficiary") if mt_core else None)
    
    if not applicant_raw or not beneficiary_raw:
        applicant_line, beneficiary_line = _parse_parties(text)
        applicant = applicant_raw or ({"name": _strip(applicant_line)} if applicant_line else None)
        beneficiary = beneficiary_raw or ({"name": _strip(beneficiary_line)} if beneficiary_line else None)
    else:
        applicant = {"name": _strip(applicant_raw)} if isinstance(applicant_raw, str) else applicant_raw
        beneficiary = {"name": _strip(beneficiary_raw)} if isinstance(beneficiary_raw, str) else beneficiary_raw

    # 3) Parse documentary sections (46A & 47A), plus goods normalization + HS codes
    docs46a = parse_46a_block(text)
    clauses47a = parse_47a_block(text)
    
    # Extract goods using enhanced parser (46A/45A deep parsing)
    goods_items: List[Dict[str, Any]] = []
    try:
        terms_46a = extract_46a_text(text)  # Extract raw 46A/45A block text
        if terms_46a:
            goods_items = parse_goods_46a(terms_46a)
    except Exception:
        # Fallback to simple goods extraction if enhanced parser fails
        goods_items = docs46a.get("goods", [])
    
    # If enhanced parser returned empty, fallback to simple extraction
    if not goods_items:
        goods_items = docs46a.get("goods", [])
    
    # Extract HS codes from goods descriptions and full text
    hs_codes = extract_hs_codes("\n".join([
        g.get("description", "") or g.get("line", "") for g in goods_items
    ]) + "\n" + text)

    # Aggregate goods summary for UI/AI layers
    total_qty = 0.0
    units = set()
    for it in goods_items:
        qty = it.get("quantity")
        if qty and isinstance(qty, dict):
            total_qty += float(qty.get("value", 0))
            units.add(qty.get("unit", ""))
        elif isinstance(qty, (int, float)):
            total_qty += float(qty)

    # 4) Compose structured result (NO large narrative blobs here)
    lc_structured: Dict[str, Any] = {
        "number": lc_number,
        "amount": {"value": amount_raw} if amount_raw else None,
        "applicant": applicant,
        "beneficiary": beneficiary,
        "ports": {"loading": _strip(pol), "discharge": _strip(pod)},
        "incoterm": _strip(incoterm_line),
        "goods": goods_items,
        "goods_summary": {
            "items": len(goods_items),
            "total_quantity": total_qty if goods_items else 0,
            "units": sorted([u for u in units if u]),
        } if goods_items else None,
        "hs_codes": hs_codes,
        "documents_required": docs46a.get("documents_required", []),
        "clauses_47a": clauses47a.get("conditions", []),
        "ucp_reference": (
            mt_fields.get("applicable_rules") or
            (mt_core.get("ucp_reference") if mt_core else None) or
            "UCP LATEST VERSION"
        ),
        "timeline": {
            "latest_shipment": (
                shipment_details.get("latest_date_of_shipment") or
                docs46a.get("latest_shipment")
            ),
            "issue_date": (
                mt_fields.get("date_of_issue") or
                (mt_core.get("issue_date") if mt_core else None)
            ),
            "expiry_date": (
                mt_fields.get("expiry_details", {}).get("expiry_date_iso") or
                (mt_core.get("expiry_date") if mt_core else None)
            ),
        },
        "source": {
            "parsers": (
                ["mt700_full", "mt700_core", "regex_core", "46A_parser", "47A_parser", "goods_46a_parser", "hs_code_extractor"]
                if mt_full else
                ["mt700_core", "regex_core", "46A_parser", "47A_parser", "goods_46a_parser", "hs_code_extractor"]
            ),
            "version": "lc_extractor_v1",
        },
    }
    
    # Add MT700 full fields if available
    if mt_full:
        lc_structured["mt700"] = mt_fields
        lc_structured["mt700_raw"] = mt_full.get("raw", {})
        lc_structured["lc_type"] = mt_fields.get("lc_classification")
        
        # Promote commonly-used fields to top-level for compatibility
        if not lc_structured.get("applicant") and mt_fields.get("applicant"):
            lc_structured["applicant"] = {"name": _strip(mt_fields["applicant"])}
        if not lc_structured.get("beneficiary") and mt_fields.get("beneficiary"):
            lc_structured["beneficiary"] = {"name": _strip(mt_fields["beneficiary"])}
        if not lc_structured.get("amount") and credit_amount:
            lc_structured["amount"] = credit_amount

    # Cleanup None keys
    return {k: v for k, v in lc_structured.items() if v not in (None, [], {})}
