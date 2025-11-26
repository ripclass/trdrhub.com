# apps/api/app/services/extraction/swift_mt700_full.py

import re
from typing import Dict, Any, List, Tuple, Optional

# Support BOTH formats:
# 1. Raw SWIFT: ":20:VALUE" (colon-tag-colon)
# 2. Formatted:  "20: VALUE" (tag-colon-space) - common in PDF exports
_TAG = re.compile(r"(?m)^(?=:?\d{2}[A-Z]?:)")  # splits on lines starting with optional : then NN[A-Z]?:
_KV = re.compile(r"^:?(?P<tag>\d{2}[A-Z]?):[ ]?(?P<val>.*)$", re.S)  # optional leading colon, optional space after
_DATE = re.compile(r"^(\d{2})(\d{2})(\d{2})$")  # YYMMDD
# Handle both "USD458750.00" and "USD 458,750.00" formats
_CUR_AMT = re.compile(r"^(?P<cur>[A-Z]{3})[ ]?(?P<amt>[\d,\.]+)$")
_BIC = re.compile(r"^[A-Z0-9]{8}(?:[A-Z0-9]{3})?$")

# Tags we expect in MT700 (non-exhaustive but industrial-grade coverage)
EXPECTED_ORDER = [
    "20", "27", "40A", "40E", "31C", "31D", "50", "59",
    "32B", "39A", "39B", "41A", "41D",
    "42C", "42A", "42M", "42P",
    "44A", "44B", "44C", "44D", "44E", "44F",
    "45A", "46A", "47A", "71B",
    "48", "57A", "57D", "53A", "53D", "78", "72"
]

MULTILINE_TAGS = {"31D", "50", "59", "41D", "44A", "44B", "44C", "44D", "44E", "44F", "45A", "46A", "47A", "71B", "78", "72"}
REPEATABLE_TAGS = {"39A", "39B", "44A", "44B", "44C", "44D", "44E", "44F", "45A", "46A", "47A", "71B", "57A", "57D", "53A", "53D"}


def _iso_date_yyMMdd(s: str) -> Optional[str]:
    m = _DATE.match(s.strip())
    if not m:
        return None
    yy, mm, dd = m.groups()
    # heuristic: 20xx for years < 80; 19xx otherwise
    year = int(yy)
    yyyy = 2000 + year if year < 80 else 1900 + year
    return f"{yyyy:04d}-{int(mm):02d}-{int(dd):02d}"


def _parse_currency_amount(val: str) -> Dict[str, Any]:
    m = _CUR_AMT.match(val.replace(" ", ""))
    if not m:
        return {"currency": None, "amount": None, "raw": val.strip()}
    amt = m.group("amt").replace(",", "")
    try:
        amount = float(amt)
    except Exception:
        amount = None
    return {"currency": m.group("cur"), "amount": amount, "raw": val.strip()}


def _clean(v: str) -> str:
    return "\n".join(line.rstrip() for line in (v or "").strip().splitlines())


def _tokenize_mt(text: str) -> List[Tuple[str, str]]:
    """
    Tokenize an MT message body into [(tag, value)] preserving multiline values.
    """
    if not text:
        return []
    
    parts = _TAG.split(text)
    out: List[Tuple[str, str]] = []
    
    for part in parts:
        if not part.strip():
            continue
        lines = part.splitlines()
        first = lines[0]
        m = _KV.match(first)
        if not m:
            # sometimes the split yields a tail without a tag, skip
            continue
        tag = m.group("tag")
        val_first_line = m.group("val")
        rest = lines[1:]
        val = "\n".join([val_first_line] + rest)
        out.append((tag, val))
    
    return out


def _append_field(d: Dict[str, Any], tag: str, value: Any):
    if tag in REPEATABLE_TAGS:
        d.setdefault(tag, []).append(value)
    else:
        d[tag] = value


def parse_mt700_full(text: str) -> Dict[str, Any]:
    """
    Industrial-grade MT700 tokenizer + normalizer.
    Returns a structured dict with canonical keys.
    """
    toks = _tokenize_mt(text)
    raw: Dict[str, Any] = {}
    
    for tag, val in toks:
        val = _clean(val)
        _append_field(raw, tag, val)
    
    # Canonical mapping
    out: Dict[str, Any] = {
        "message_type": "MT700",
        "raw": raw,  # keep raw for traceability
        "blocks": raw,  # alias for frontend compatibility (LcHeader expects blocks)
        "fields": {},
    }
    
    F = out["fields"]
    
    # Core IDs
    F["reference"] = raw.get("20")
    F["sequence"] = raw.get("27")
    
    # Credit type / form
    F["form_of_doc_credit"] = raw.get("40A")  # e.g., IRREVOCABLE, TRANSFERABLE
    F["applicable_rules"] = raw.get("40E")  # e.g., UCPURR LATEST, UCP600
    
    # Dates
    F["date_of_issue"] = _iso_date_yyMMdd(raw.get("31C") or "") if raw.get("31C") else None
    F["expiry_details"] = {
        "expiry_place_and_date": raw.get("31D"),
        "expiry_date_iso": _iso_date_yyMMdd(raw.get("31D", "").split()[-1]) if raw.get("31D") else None,
    }
    
    # Applicant / Beneficiary (free-format)
    F["applicant"] = raw.get("50")
    F["beneficiary"] = raw.get("59")
    
    # Amount
    if raw.get("32B"):
        F["credit_amount"] = _parse_currency_amount(raw["32B"])
    else:
        F["credit_amount"] = None
    
    # Tolerance / max cr amt
    F["tolerance"] = raw.get("39A") if not isinstance(raw.get("39A"), list) else raw.get("39A")
    F["max_credit_amt"] = raw.get("39B") if not isinstance(raw.get("39B"), list) else raw.get("39B")
    
    # Available with / by
    avail = raw.get("41A") or raw.get("41D")
    F["available_with"] = {
        "by": "41A" if raw.get("41A") else ("41D" if raw.get("41D") else None),
        "details": avail
    }
    
    # Shipment terms
    F["shipment"] = {
        "drafts_at": raw.get("42C"),
        "drawee": raw.get("42A"),
        "partial_shipments": raw.get("43P") if "43P" in raw else None,
        "transshipment": raw.get("43T") if "43T" in raw else None,
    }
    
    # Period for presentation / mixed / deferred
    F["period_for_presentation"] = raw.get("48")
    F["mixed_payment_details"] = raw.get("42M")
    F["deferred_payment_details"] = raw.get("42P")
    
    # Shipment locations/dates
    F["shipment_details"] = {
        "place_of_taking_in_charge_dispatch_from": raw.get("44A"),
        "port_of_loading_airport_of_departure": raw.get("44E"),
        "port_of_discharge_airport_of_destination": raw.get("44F"),
        "place_of_final_destination_for_transport": raw.get("44B"),
        "latest_date_of_shipment": raw.get("44C"),
        "shipment_period": raw.get("44D"),
    }
    
    # Description / docs / addl conditions
    F["docs_required"] = raw.get("46A") if isinstance(raw.get("46A"), list) else raw.get("46A")
    F["description_of_goods"] = raw.get("45A") if isinstance(raw.get("45A"), list) else raw.get("45A")
    F["additional_conditions"] = raw.get("47A") if isinstance(raw.get("47A"), list) else raw.get("47A")
    
    # Charges
    F["charges"] = raw.get("71B") if isinstance(raw.get("71B"), list) else raw.get("71B")
    
    # Reimbursing/confirming/correspondents
    F["reimbursing_bank"] = raw.get("53A") or raw.get("53D")
    F["advising_bank"] = raw.get("57A") or raw.get("57D")
    
    # Instructions narrative
    F["instructions_to_paying_accepting_negotiating_bank"] = raw.get("78")
    F["sender_to_receiver_info"] = raw.get("72")
    
    # LC type heuristic
    F["lc_classification"] = _classify_lc(F)
    
    return out


def _classify_lc(F: Dict[str, Any]) -> Dict[str, Any]:
    """
    Lightweight heuristics: sight/usance/transferable/revolving/standby.
    """
    form = (F.get("form_of_doc_credit") or "").upper()
    addl = (F.get("additional_conditions") or "") if isinstance(F.get("additional_conditions"), str) else "\n".join(F.get("additional_conditions") or [])
    drafts = (F.get("shipment", {}).get("drafts_at") or "").upper()
    mixed = (F.get("mixed_payment_details") or "")
    
    types: List[str] = []
    
    if "TRANSFERABLE" in form or "TRANSFERABLE" in addl.upper():
        types.append("Transferable")
    if "REVOLV" in form or "REVOLV" in addl.upper():
        types.append("Revolving")
    if "STANDBY" in form or "ISP98" in (F.get("applicable_rules") or "").upper():
        types.append("Standby")
    if "SIGHT" in drafts or "AT SIGHT" in (mixed or "").upper():
        types.append("Sight")
    if re.search(r"\b(\d{1,3})\s*DAYS?\b", drafts) or re.search(r"\b(\d{1,3})\s*DAYS?\b", mixed.upper()):
        types.append("Usance")
    
    if not types:
        types.append("Unknown")
    
    return {"types": sorted(list(set(types)))}

