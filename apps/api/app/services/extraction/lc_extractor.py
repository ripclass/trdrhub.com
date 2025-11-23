# apps/api/app/services/extraction/lc_extractor.py

from __future__ import annotations

import re

from dataclasses import dataclass, asdict

from typing import Dict, Any, Optional

# ----------- helpers

_ws = r"[ \t]*"

NL = r"(?:\r?\n)+"

def _clean(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    s = re.sub(r"[ \t]+", " ", s.strip())
    # kill form-feed or stray OCR control chars
    s = s.replace("\x0c", " ").replace("\f", " ")
    return s or None

def _find(pattern: str, text: str, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL) -> Optional[str]:
    m = re.search(pattern, text, flags)
    return _clean(m.group(1)) if m else None

def _capture_block(label_variants, text: str, stop_labels) -> Optional[str]:
    """
    Capture a multi-line block that starts at any of label_variants and stops
    at the next header in stop_labels or end of string.
    """
    lbl = r"|".join([re.escape(v) for v in label_variants])
    stop = r"|".join([re.escape(v) for v in stop_labels])
    pattern = rf"(?:^|{NL})(?:{lbl}){_ws}[:\-]?\s*(.+?)(?=(?:{NL}(?:{stop}){_ws}[:\-]?)|$)"
    m = re.search(pattern, text, re.IGNORECASE | re.DOTALL | re.MULTILINE)
    return _clean(m.group(1)) if m else None

def _country_from(addr: str) -> Optional[str]:
    if not addr:
        return None
    # last token heuristic
    tail = addr.split(",")[-1].strip()
    # common OCR mishaps normalized
    replacements = {
        "u s a": "USA",
        "u.s.a.": "USA",
        "u s": "US",
    }
    t = replacements.get(tail.lower(), tail)
    return t

_money = re.compile(r"(?<!\w)(?:USD|US\$|\$)?\s*([0-9]{1,3}(?:[, ]?[0-9]{3})*(?:\.[0-9]{2})?)", re.I)

# ----------- data model

@dataclass
class Party:
    name: Optional[str] = None
    address: Optional[str] = None
    country: Optional[str] = None

@dataclass
class Ports:
    loading: Optional[str] = None
    discharge: Optional[str] = None

@dataclass
class LCDates:
    issue: Optional[str] = None
    latest_shipment: Optional[str] = None
    expiry: Optional[str] = None

# ----------- core parser

class LCExtractor:
    """
    Parses OCR/plaintext of an LC PDF (export LC typical format or SWIFT MT700-like)
    into the structure our frontend expects.
    """

    H_LABELS = [
        "45A – Description of Goods",
        "45A-Description of Goods",
        "45A Description of Goods",
        "46A – Documents Required",
        "46A-Documents Required",
        "46A Documents Required",
        "47A – Additional Conditions",
        "47A-Additional Conditions",
        "47A Additional Conditions",
        "DESCRIPTION OF GOODS",
        "DOCUMENTS REQUIRED",
        "ADDITIONAL CONDITIONS",
    ]

    STOP_LABELS = [
        "45A", "46A", "47A",
        "INCOTERM", "INCOTERMS",
        "PORT OF LOADING", "PORT OF DISCHARGE",
        "APPLICANT", "BENEFICIARY",
        "AMOUNT", "LC NO", "LC NUMBER",
        "ISSUE DATE", "EXPIRY", "LATEST SHIPMENT",
        "UCP", "UCP600", "APPLICABLE RULES",
        "CHARGES", "PRESENTATION", "INSTRUCTIONS"
    ]

    def parse(self, text: str) -> Dict[str, Any]:
        t = text.replace("\r", "")
        # Normalize common header tokens
        t = re.sub(r"\u2013|\u2014|–|—", "-", t)  # dashes

        # Try to detect and parse SWIFT MT700 format
        mt700_data = None
        if re.search(r":\d{2}[A-Z]?:\s*", t):
            try:
                from app.services.parsers.swift_mt700 import parse_mt700
                mt700_data = parse_mt700(t)
            except Exception:
                # If MT700 parsing fails, continue with regular extraction
                pass

        # --- simple fields

        lc_number = _find(r"(?:^|[^A-Z])(?:LC(?: No\.?| Number)?|L/C(?: No\.?)?)\s*[:\-]?\s*([A-Z0-9\-\/]+)", t)
        if not lc_number:
            # fallback to pattern like EXP2026BD001 in text blob
            m = re.search(r"\b([A-Z]{2,4}\d{4,}[A-Z]{0,4}\d{0,4})\b", t)
            lc_number = _clean(m.group(1)) if m else None

        amount_raw = _find(r"(?:Amount|LC Amount|Face Value)\s*[:\-]?\s*(.+)", t)
        amount_val = None
        if amount_raw:
            m = _money.search(amount_raw)
            if m:
                amount_val = m.group(1).replace(" ", "").replace(",", "")

        # Applicant / Beneficiary blocks

        applicant_block = _capture_block(
            ["Applicant", "Applicant (Buyer)", "Applicant:"], t, self.STOP_LABELS
        )

        beneficiary_block = _capture_block(
            ["Beneficiary", "Beneficiary (Seller)", "Beneficiary:"], t, self.STOP_LABELS
        )

        applicant = Party(
            name=_find(r"^\s*Name\s*[:\-]\s*(.+)$", applicant_block or "", re.I | re.M) or
                 _find(r"^(.+?)(?:,|$)", applicant_block or "", re.I | re.M),
            address=_find(r"(?:Address|Addr)\s*[:\-]\s*(.+)", applicant_block or "") or _clean(applicant_block),
            country=_country_from(applicant_block or "")
        )

        beneficiary = Party(
            name=_find(r"^\s*Name\s*[:\-]\s*(.+)$", beneficiary_block or "", re.I | re.M) or
                 _find(r"^(.+?)(?:,|$)", beneficiary_block or "", re.I | re.M),
            address=_find(r"(?:Address|Addr)\s*[:\-]\s*(.+)", beneficiary_block or "") or _clean(beneficiary_block),
            country=_country_from(beneficiary_block or "")
        )

        # Ports

        port_loading = (
            _find(r"(?:Port of Loading|Loading Port)\s*[:\-]\s*(.+)", t)
            or _find(r"loading\s*[:\-]?\s*(.+)", t)
        )

        port_discharge = (
            _find(r"(?:Port of Discharge|Discharge Port|Destination Port)\s*[:\-]\s*(.+)", t)
            or _find(r"discharge\s*[:\-]?\s*(.+)", t)
        )

        ports = Ports(loading=port_loading, discharge=port_discharge)

        # Incoterm

        incoterm = _find(r"(?:INCOTERMS?|Trade Term)\s*[:\-]?\s*([A-Z]{3}.*?$)", t, re.I | re.M) \
                   or _find(r"\b(FOB|CIF|CFR|EXW|DAP|DDP)\b[^\n]*", t, re.I)

        # UCP reference

        ucp = _find(r"(?:UCP|Applicable Rules)\s*[:\-]?\s*(.+)", t) \
              or _find(r"\bUCP\s*600\b(?:.*?version.*?\b2007\b)?", t, re.I)

        # Dates

        dates = LCDates(
            issue=_find(r"(?:Issue Date|Date of Issue)\s*[:\-]\s*([0-9]{2,4}[^\n]+)", t),
            expiry=_find(r"(?:Expiry(?: Date)?)\s*[:\-]\s*([0-9]{2,4}[^\n]+)", t),
            latest_shipment=_find(r"(?:Latest Shipment|Latest Date of Shipment)\s*[:\-]\s*([0-9]{2,4}[^\n]+)", t),
        )

        # 45A / 46A / 47A blocks
        # If MT700 format detected, use parsed tags; otherwise use regex capture

        if mt700_data:
            goods_45a = mt700_data.get("45A") or _capture_block(
                ["45A - Description of Goods", "45A – Description of Goods", "45A Description of Goods", "DESCRIPTION OF GOODS"],
                t, self.STOP_LABELS
            )
            docs_46a = mt700_data.get("46A") or _capture_block(
                ["46A - Documents Required", "46A – Documents Required", "46A Documents Required", "DOCUMENTS REQUIRED"],
                t, self.STOP_LABELS
            )
            addl_47a = mt700_data.get("47A") or _capture_block(
                ["47A - Additional Conditions", "47A – Additional Conditions", "47A Additional Conditions", "ADDITIONAL CONDITIONS"],
                t, self.STOP_LABELS
            )
        else:
            goods_45a = _capture_block(
                ["45A - Description of Goods", "45A – Description of Goods", "45A Description of Goods", "DESCRIPTION OF GOODS"],
                t, self.STOP_LABELS
            )

            docs_46a = _capture_block(
                ["46A - Documents Required", "46A – Documents Required", "46A Documents Required", "DOCUMENTS REQUIRED"],
                t, self.STOP_LABELS
            )

            addl_47a = _capture_block(
                ["47A - Additional Conditions", "47A – Additional Conditions", "47A Additional Conditions", "ADDITIONAL CONDITIONS"],
                t, self.STOP_LABELS
            )

        # Cleanup obvious "bleed" (long paragraphs stuffed into wrong field)

        def _prune_block(s: Optional[str]) -> Optional[str]:
            if not s:
                return s
            s = re.sub(rf"\b(?:{ '|'.join([re.escape(x) for x in self.STOP_LABELS]) })\b.*$", "", s, flags=re.I | re.S)
            return _clean(s)

        goods_45a = _prune_block(goods_45a)
        docs_46a = _prune_block(docs_46a)
        addl_47a = _prune_block(addl_47a)

        # Parse 46A into structured items
        from app.services.extraction.docs_46a_parser import parse_docs_46A
        docs_structured = parse_docs_46A(docs_46a) if docs_46a else []

        # Parse 47A into structured tokens
        from app.services.extraction.clauses_47a_parser import tokenize_47a
        clauses_47a_structured = tokenize_47a(addl_47a) if addl_47a else []

        # Extract HS codes from LC text fields
        from app.services.extraction.hs_code_extractor import extract_hs_codes
        hs_codes = extract_hs_codes(
            goods_45a or "",
            docs_46a or "",
            addl_47a or ""
        )

        # Build final structure expected by UI

        result: Dict[str, Any] = {
            "number": lc_number,
            "amount": {"value": amount_val} if amount_val else None,
            "applicant": asdict(applicant) if any(asdict(applicant).values()) else None,
            "beneficiary": asdict(beneficiary) if any(asdict(beneficiary).values()) else None,
            "ports": asdict(ports) if any(asdict(ports).values()) else None,
            "ucp_reference": _clean(ucp),
            "dates": asdict(dates) if any(asdict(dates).values()) else None,
            "incoterm": _clean(incoterm),
            "goods_description": _clean(goods_45a),
            "clauses": {
                "documents_required_raw": _clean(docs_46a),
                "documents_structured": docs_structured,
                "additional_conditions_raw": _clean(addl_47a),
                "additional_conditions_structured": clauses_47a_structured,
            },
        }

        # Add HS codes to goods section if any found
        if hs_codes.get("hs_full"):
            result["goods"] = {"hs": hs_codes}

        # Strip empty keys for a clean payload
        return {k: v for k, v in result.items() if v not in (None, "", {})}

# ----------- public API

def extract_lc(text: str) -> Dict[str, Any]:
    """
    Entry point used by the validation pipeline.

    `text` is the full OCR/plaintext of the LC PDF.

    Returns a dict that matches the frontend "Extracted Data → LC" expectations.

    """
    return LCExtractor().parse(text)

