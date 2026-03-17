from __future__ import annotations

import re

from typing import Dict, Any, List, Optional, Tuple

from .docs_46a_parser import parse_46a_block, extract_46a_text
from .clauses_47a_parser import parse_47a_block
from .hs_code_extractor import extract_hs_codes
from .goods_46a_parser import parse_goods_46a
try:
    from .lc_taxonomy import build_lc_classification
except ImportError:  # pragma: no cover - direct module loading in tests/scripts
    import importlib.util
    from pathlib import Path

    _lc_taxonomy_path = Path(__file__).with_name("lc_taxonomy.py")
    _lc_taxonomy_spec = importlib.util.spec_from_file_location("lc_taxonomy_fallback", _lc_taxonomy_path)
    if _lc_taxonomy_spec is None or _lc_taxonomy_spec.loader is None:
        raise
    _lc_taxonomy_module = importlib.util.module_from_spec(_lc_taxonomy_spec)
    _lc_taxonomy_spec.loader.exec_module(_lc_taxonomy_module)
    build_lc_classification = _lc_taxonomy_module.build_lc_classification
from .swift_mt700_full import parse_mt700_full
from ..parsers.swift_mt700 import parse_mt700_core  # Keep for fallback

LC_NO_RE = re.compile(r"\b(?:LC|L/C|Letter of Credit).*?\b(?:No\.?|Number)\s*[:\-]?\s*([A-Z0-9\-\/]+)", re.I | re.S)
AMOUNT_RE = re.compile(r"\b(?:amount|lc amount|face value)\b[^\d]*([\d.,]+)", re.I)
INCOTERM_RE = re.compile(r"\b(?:Incoterm|Trade Term)\b[^A-Z0-9]*(EXW|FCA|CPT|CIP|DAP|DPU|DDP|FAS|FOB|CFR|CIF)\b[^\n]*", re.I)
PORT_LOAD_RE = re.compile(r"(?:Port of Loading|POL|Loading Port)\s*[:\-]?\s*([^\n]+)", re.I)
PORT_DISC_RE = re.compile(r"(?:Port of Discharge|POD|Discharge Port|Destination Port)\s*[:\-]?\s*([^\n]+)", re.I)
APPLICANT_RE = re.compile(r"\bApplicant\b[^\S\r\n]*[:\-]?\s*(.*?)(?:\n{1,2}|$)", re.I)
BENEFICIARY_RE = re.compile(r"\bBeneficiary\b[^\S\r\n]*[:\-]?\s*(.*?)(?:\n{1,2}|$)", re.I)

# =====================================================================
# VALIDATION HELPERS - Reject garbage extraction results
# =====================================================================

# Common document words that should NOT be LC numbers
_LC_NUMBER_BLACKLIST = {
    "tify", "ify", "notify", "certify", "verify", "satisfy", "identify",
    "the", "and", "for", "from", "this", "that", "with", "document",
}

# Common document phrases that should NOT be party names
_PARTY_NAME_BLACKLIST_PATTERNS = [
    r"\bbl\s+to\s+show\b",  # "BL TO SHOW..."
    r"\bcertificate\s+confirming\b",  # "CERTIFICATE CONFIRMING..."
    r"\bdocuments?\s+must\b",  # "DOCUMENTS MUST..."
    r"\bshipment\b",
    r"\bpayment\b",
    r"\bfreight\b",
    r"\binvoice\b",
    r"\bbill\s+of\s+lading\b",
    r"^\s*[\.\,\-]\s*",  # Starts with punctuation
]
_PARTY_BLACKLIST_RE = re.compile("|".join(_PARTY_NAME_BLACKLIST_PATTERNS), re.I)

def _is_valid_lc_number(s: Optional[str]) -> bool:
    """Check if extracted LC number looks valid, not garbage."""
    if not s or not isinstance(s, str):
        return False
    s = s.strip().lower()
    if len(s) < 3:  # Too short
        return False
    if len(s) > 50:  # Too long
        return False
    if s in _LC_NUMBER_BLACKLIST:
        return False
    # Must have at least one digit (most LC numbers do)
    if not any(c.isdigit() for c in s):
        return False
    return True

def _is_valid_party_name(s: Optional[str]) -> bool:
    """Check if extracted party name looks valid, not garbage from document text."""
    if not s or not isinstance(s, str):
        return False
    s = s.strip()
    if len(s) < 3:  # Too short
        return False
    if len(s) > 200:  # Too long
        return False
    if _PARTY_BLACKLIST_RE.search(s):
        return False
    # Must have at least one letter
    if not any(c.isalpha() for c in s):
        return False
    return True

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


def _normalize_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    return re.sub(r"\s+", " ", str(value).strip().upper())


def _normalize_amount(value: Any) -> Optional[str]:
    if value is None:
        return None
    cleaned = re.sub(r"[^0-9.]", "", str(value))
    if not cleaned:
        return None
    try:
        return f"{float(cleaned):.2f}"
    except ValueError:
        return None


def _diagnose_candidates(
    candidates: List[Any],
    validator: Optional[Any] = None,
    normalizer: Optional[Any] = None,
) -> Dict[str, Any]:
    valid = []
    invalid = []
    normalized_values = []

    for candidate in candidates:
        if candidate is None or candidate == "":
            continue
        if validator and not validator(candidate):
            invalid.append(candidate)
            continue
        if normalizer:
            normalized = normalizer(candidate)
            if normalized is None:
                invalid.append(candidate)
                continue
            normalized_values.append(normalized)
        else:
            normalized_values.append(candidate)
        valid.append(candidate)

    conflict = len(set(normalized_values)) > 1 if normalized_values else False

    return {
        "candidates": [c for c in candidates if c not in (None, "")],
        "valid_candidates": valid,
        "invalid_candidates": invalid,
        "conflict": conflict,
    }


def _candidate_value(candidate: Any) -> Any:
    if isinstance(candidate, dict) and "value" in candidate:
        return candidate.get("value")
    return candidate


def _candidate_method(candidate: Any, fallback_method: str = "regex") -> str:
    if isinstance(candidate, dict):
        method = candidate.get("method")
        if method in {"ocr", "table", "kv", "llm", "regex"}:
            return method
    return fallback_method


def _has_evidence_in_text(value: Any, text: str) -> bool:
    if value is None:
        return False
    if isinstance(value, dict):
        for key in ("name", "value", "amount", "currency"):
            nested = value.get(key)
            if isinstance(nested, str) and nested.strip():
                return nested.strip().lower() in (text or "").lower()
        return False
    if isinstance(value, str):
        needle = value.strip()
        return bool(needle) and needle.lower() in (text or "").lower()
    return True


def _arbitrate_field(
    *,
    field: str,
    candidates: List[Any],
    raw_text: str,
    validator: Optional[Any] = None,
    normalizer: Optional[Any] = None,
    fallback_method: str = "regex",
) -> Tuple[Any, Dict[str, Any], Dict[str, Any]]:
    extracted_candidates = [_candidate_value(c) for c in candidates if _candidate_value(c) not in (None, "")]
    diag = _diagnose_candidates(extracted_candidates, validator=validator, normalizer=normalizer)

    valid_candidates = diag.get("valid_candidates") or []
    selected = valid_candidates[0] if valid_candidates else None
    selected_method = fallback_method
    for c in candidates:
        if _candidate_value(c) == selected:
            selected_method = _candidate_method(c, fallback_method=fallback_method)
            break

    # Strict rule order:
    # 1) conflict -> rejected/conflict_detected
    # 2) no candidate -> rejected/missing_in_source
    # 3) candidate exists but parse/validation fails -> retry/extraction_failed
    # 4) candidate valid and evidence-backed -> accepted
    if diag.get("conflict"):
        decision = {
            "field": field,
            "value": None,
            "status": "rejected",
            "reason_code": "conflict_detected",
            "evidence_present": False,
            "method": selected_method,
        }
        return None, diag, decision

    if not diag.get("candidates"):
        decision = {
            "field": field,
            "value": None,
            "status": "rejected",
            "reason_code": "missing_in_source",
            "evidence_present": False,
            "method": fallback_method,
        }
        return None, diag, decision

    if not valid_candidates:
        method = _candidate_method(candidates[0], fallback_method=fallback_method) if candidates else fallback_method
        decision = {
            "field": field,
            "value": None,
            "status": "retry",
            "reason_code": "extraction_failed",
            "evidence_present": False,
            "method": method,
        }
        return None, diag, decision

    evidence_present = _has_evidence_in_text(selected, raw_text)
    if not evidence_present:
        decision = {
            "field": field,
            "value": selected,
            "status": "retry",
            "reason_code": "extraction_failed",
            "evidence_present": False,
            "method": selected_method,
        }
        return None, diag, decision

    decision = {
        "field": field,
        "value": selected,
        "status": "accepted",
        "reason_code": "missing_in_source",
        "evidence_present": True,
        "method": selected_method,
    }
    return selected, diag, decision


def _is_unresolved_critical(decision: Dict[str, Any], field_spec: Dict[str, Any]) -> bool:
    if not field_spec.get("critical", False):
        return False
    status = str(decision.get("status") or "").lower()
    return status in {"retry", "rejected"}


def _upgrade_reason(current_reason: Optional[str], candidate_reason: Optional[str]) -> str:
    order = {
        "missing_in_source": 0,
        "extraction_failed": 1,
        "conflict_detected": 2,
    }
    cur = current_reason if current_reason in order else "missing_in_source"
    nxt = candidate_reason if candidate_reason in order else cur
    return cur if order[cur] >= order[nxt] else nxt


def _filter_candidates_by_methods(candidates: List[Any], allowed_methods: set[str]) -> List[Any]:
    return [c for c in (candidates or []) if _candidate_method(c) in allowed_methods]


def _retry_unresolved_critical_fields(
    *,
    field_decisions: Dict[str, Dict[str, Any]],
    field_diagnostics: Dict[str, Dict[str, Any]],
    field_candidates: Dict[str, List[Any]],
    field_specs: Dict[str, Dict[str, Any]],
    raw_text: str,
    llm_field_repair: Optional[Any] = None,
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]], Dict[str, Any]]:
    """Run bounded C2 retry orchestration for unresolved CRITICAL fields only."""
    updated_decisions: Dict[str, Dict[str, Any]] = {k: dict(v) for k, v in (field_decisions or {}).items()}
    updated_diagnostics: Dict[str, Dict[str, Any]] = {k: dict(v) for k, v in (field_diagnostics or {}).items()}
    recovered_values: Dict[str, Any] = {}

    for field, spec in (field_specs or {}).items():
        decision = dict(updated_decisions.get(field) or {"field": field})
        trace = {
            "attempted_passes": [],
            "final_pass_used": None,
            "recovered": False,
        }

        if not _is_unresolved_critical(decision, spec):
            decision["retry_trace"] = trace
            updated_decisions[field] = decision
            continue

        current_reason = decision.get("reason_code")
        passes = [
            ("table_kv_reparse", _filter_candidates_by_methods(field_candidates.get(field, []), {"table", "kv"})),
            ("regex_fallback", _filter_candidates_by_methods(field_candidates.get(field, []), {"regex"})),
            ("llm_field_repair", []),
        ]

        for pass_name, pass_candidates in passes:
            trace["attempted_passes"].append(pass_name)

            if pass_name == "llm_field_repair":
                repaired = None
                if llm_field_repair:
                    try:
                        repaired = llm_field_repair(field=field, raw_text=raw_text)
                    except Exception:
                        repaired = None
                pass_candidates = [{"value": repaired, "method": "llm"}] if repaired not in (None, "") else []

            value, diag, retry_decision = _arbitrate_field(
                field=field,
                candidates=pass_candidates,
                raw_text=raw_text,
                validator=spec.get("validator"),
                normalizer=spec.get("normalizer"),
                fallback_method=spec.get("fallback_method", "regex"),
            )

            if retry_decision.get("status") != "accepted":
                current_reason = _upgrade_reason(current_reason, retry_decision.get("reason_code"))
                retry_decision["reason_code"] = current_reason
            retry_decision["retry_trace"] = trace

            updated_diagnostics[field] = {**diag, "decision": retry_decision}
            updated_decisions[field] = retry_decision

            if retry_decision.get("status") == "accepted" and value is not None:
                trace["final_pass_used"] = pass_name
                trace["recovered"] = True
                retry_decision["retry_trace"] = trace
                updated_diagnostics[field] = {**diag, "decision": retry_decision}
                updated_decisions[field] = retry_decision
                recovered_values[field] = value
                break

        if not trace["recovered"]:
            updated_decisions[field]["retry_trace"] = trace
            if updated_diagnostics.get(field):
                updated_diagnostics[field]["decision"] = updated_decisions[field]

    return updated_decisions, updated_diagnostics, recovered_values

def extract_lc_structured(raw_text: str, llm_field_repair: Optional[Any] = None) -> Dict[str, Any]:
    """
    Top-level extraction orchestrator. Works with LC PDFs converted to text or OCR text.

    Returns a clean, structured dict (no messy narrative blobs).
    """

    text = raw_text or ""

    def _party_name(candidate: Any) -> Optional[str]:
        if candidate is None:
            return None
        if isinstance(candidate, dict):
            return candidate.get("name") or candidate.get("party") or candidate.get("value")
        return candidate

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
    
    # LC number - with validation to reject garbage
    lc_number_candidates = [
        {"value": mt_fields.get("reference"), "method": "kv"},
        {"value": (mt_core.get("number") if mt_core else None), "method": "kv"},
        {"value": _first(LC_NO_RE, text), "method": "regex"},
    ]
    lc_number, lc_number_diag, lc_number_decision = _arbitrate_field(
        field="lc_number",
        candidates=lc_number_candidates,
        raw_text=text,
        validator=_is_valid_lc_number,
        normalizer=_normalize_text,
        fallback_method="regex",
    )
    
    # Amount and Currency
    credit_amount = mt_fields.get("credit_amount")
    currency = None
    amount_candidates = []
    currency_candidates = []

    if credit_amount and isinstance(credit_amount, dict):
        amount_candidates.append({"value": credit_amount.get("amount"), "method": "kv"})
        currency_candidates.append({"value": credit_amount.get("currency"), "method": "kv"})
    amount_candidates.append({"value": mt_core.get("amount") if mt_core else None, "method": "kv"})
    amount_candidates.append({"value": _amount(text), "method": "regex"})
    currency_candidates.append({"value": mt_core.get("currency") if mt_core else None, "method": "kv"})

    amount_value, amount_diag, amount_decision = _arbitrate_field(
        field="amount",
        candidates=amount_candidates,
        raw_text=text,
        normalizer=_normalize_amount,
        fallback_method="regex",
    )
    currency, currency_diag, currency_decision = _arbitrate_field(
        field="currency",
        candidates=currency_candidates,
        raw_text=text,
        normalizer=_normalize_text,
        fallback_method="regex",
    )

    amount_raw = str(amount_value) if amount_value is not None else None
    
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
    
    # Applicant / Beneficiary - with validation to reject document text as names
    applicant_raw = mt_fields.get("applicant") or (mt_core.get("applicant") if mt_core else None)
    beneficiary_raw = mt_fields.get("beneficiary") or (mt_core.get("beneficiary") if mt_core else None)

    applicant_line, beneficiary_line = _parse_parties(text)

    applicant_candidates = [
        {"value": _party_name(mt_fields.get("applicant")), "method": "kv"},
        {"value": _party_name(mt_core.get("applicant") if mt_core else None), "method": "kv"},
        {"value": _party_name(applicant_line), "method": "regex"},
    ]
    beneficiary_candidates = [
        {"value": _party_name(mt_fields.get("beneficiary")), "method": "kv"},
        {"value": _party_name(mt_core.get("beneficiary") if mt_core else None), "method": "kv"},
        {"value": _party_name(beneficiary_line), "method": "regex"},
    ]

    if not applicant_raw or not beneficiary_raw:
        # Validate regex-extracted names to avoid garbage
        if applicant_line and not _is_valid_party_name(applicant_line):
            applicant_line = None
        if beneficiary_line and not _is_valid_party_name(beneficiary_line):
            beneficiary_line = None
        applicant = applicant_raw or ({"name": _strip(applicant_line)} if applicant_line else None)
        beneficiary = beneficiary_raw or ({"name": _strip(beneficiary_line)} if beneficiary_line else None)
    else:
        # Also validate MT700-extracted names (could still be garbage)
        applicant_name = _strip(applicant_raw) if isinstance(applicant_raw, str) else applicant_raw
        beneficiary_name = _strip(beneficiary_raw) if isinstance(beneficiary_raw, str) else beneficiary_raw
        
        if isinstance(applicant_name, str) and not _is_valid_party_name(applicant_name):
            applicant = None
        else:
            applicant = {"name": applicant_name} if isinstance(applicant_name, str) else applicant_name
            
        if isinstance(beneficiary_name, str) and not _is_valid_party_name(beneficiary_name):
            beneficiary = None
        else:
            beneficiary = {"name": beneficiary_name} if isinstance(beneficiary_name, str) else beneficiary_name

    applicant_value, applicant_diag, applicant_decision = _arbitrate_field(
        field="applicant",
        candidates=applicant_candidates,
        raw_text=text,
        validator=_is_valid_party_name,
        normalizer=_normalize_text,
        fallback_method="regex",
    )
    beneficiary_value, beneficiary_diag, beneficiary_decision = _arbitrate_field(
        field="beneficiary",
        candidates=beneficiary_candidates,
        raw_text=text,
        validator=_is_valid_party_name,
        normalizer=_normalize_text,
        fallback_method="regex",
    )

    if applicant_value is None:
        applicant = None
    elif isinstance(applicant, dict):
        applicant["name"] = _strip(str(applicant_value))
    else:
        applicant = {"name": _strip(str(applicant_value))}

    if beneficiary_value is None:
        beneficiary = None
    elif isinstance(beneficiary, dict):
        beneficiary["name"] = _strip(str(beneficiary_value))
    else:
        beneficiary = {"name": _strip(str(beneficiary_value))}

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
    
    # Filter out garbage goods items (single characters, too short, etc.)
    valid_goods_items = []
    for g in goods_items:
        desc = g.get("description", "") or g.get("line", "")
        if isinstance(desc, str) and len(desc.strip()) >= 5:  # Require at least 5 chars
            valid_goods_items.append(g)
    goods_items = valid_goods_items
    
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
    field_decisions = {
        "lc_number": lc_number_decision,
        "amount": amount_decision,
        "currency": currency_decision,
        "applicant": applicant_decision,
        "beneficiary": beneficiary_decision,
    }

    field_diagnostics = {
        "lc_number": {**lc_number_diag, "decision": lc_number_decision},
        "amount": {**amount_diag, "decision": amount_decision},
        "currency": {**currency_diag, "decision": currency_decision},
        "applicant": {**applicant_diag, "decision": applicant_decision},
        "beneficiary": {**beneficiary_diag, "decision": beneficiary_decision},
    }

    field_candidates = {
        "lc_number": lc_number_candidates,
        "amount": amount_candidates,
        "currency": currency_candidates,
        "applicant": applicant_candidates,
        "beneficiary": beneficiary_candidates,
    }
    field_specs = {
        "lc_number": {
            "critical": True,
            "validator": _is_valid_lc_number,
            "normalizer": _normalize_text,
            "fallback_method": "regex",
        },
        "amount": {
            "critical": True,
            "validator": None,
            "normalizer": _normalize_amount,
            "fallback_method": "regex",
        },
        "currency": {
            "critical": True,
            "validator": None,
            "normalizer": _normalize_text,
            "fallback_method": "regex",
        },
        "applicant": {
            "critical": True,
            "validator": _is_valid_party_name,
            "normalizer": _normalize_text,
            "fallback_method": "regex",
        },
        "beneficiary": {
            "critical": True,
            "validator": _is_valid_party_name,
            "normalizer": _normalize_text,
            "fallback_method": "regex",
        },
    }

    field_decisions, field_diagnostics, recovered_values = _retry_unresolved_critical_fields(
        field_decisions=field_decisions,
        field_diagnostics=field_diagnostics,
        field_candidates=field_candidates,
        field_specs=field_specs,
        raw_text=text,
        llm_field_repair=llm_field_repair,
    )

    if "lc_number" in recovered_values:
        lc_number = recovered_values["lc_number"]
    if "amount" in recovered_values:
        amount_value = recovered_values["amount"]
        amount_raw = str(amount_value) if amount_value is not None else None
    if "currency" in recovered_values:
        currency = recovered_values["currency"]
    if "applicant" in recovered_values:
        applicant = {"name": _strip(str(recovered_values["applicant"]))}
    if "beneficiary" in recovered_values:
        beneficiary = {"name": _strip(str(recovered_values["beneficiary"]))}

    lc_structured: Dict[str, Any] = {
        "number": lc_number,
        "raw_text": text,
        "amount": {"value": amount_raw, "currency": currency} if amount_raw else None,
        "currency": currency,  # Also expose at top level for easy access
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
        "additional_conditions": clauses47a.get("conditions", []),  # Canonical name for 47A
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
        "_field_diagnostics": field_diagnostics,
        "_field_decisions": field_decisions,
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
        # Include both fields and blocks for frontend compatibility
        # Frontend LcHeader expects mt700.blocks['20'], mt700.blocks['32B'], etc.
        lc_structured["mt700"] = {
            **mt_fields,
            "blocks": mt_full.get("blocks", {}),  # Frontend needs this
            "raw": mt_full.get("raw", {}),
        }
        lc_structured["mt700_raw"] = mt_full.get("raw", {})
        lc_classification = mt_fields.get("lc_classification", {})
        if lc_classification not in (None, "", [], {}):
            # Keep parser-native classification for diagnostics without overloading legacy lc_type.
            lc_structured["mt700_parser_classification"] = lc_classification
        
        # Promote commonly-used fields to top-level for compatibility
        if not lc_structured.get("applicant") and mt_fields.get("applicant"):
            lc_structured["applicant"] = {"name": _strip(mt_fields["applicant"])}
        if not lc_structured.get("beneficiary") and mt_fields.get("beneficiary"):
            lc_structured["beneficiary"] = {"name": _strip(mt_fields["beneficiary"])}
        if not lc_structured.get("amount") and credit_amount:
            lc_structured["amount"] = credit_amount

    lc_structured["schema"] = "mt700"
    lc_structured["message_type"] = "mt700"
    lc_structured["format"] = "mt700"
    lc_structured["_source_format"] = "mt700"
    lc_structured["_source_message_type"] = "mt700"

    # Cleanup None keys
    result = {k: v for k, v in lc_structured.items() if v not in (None, [], {})}
    result["lc_classification"] = build_lc_classification(result)
    
    # Calculate extraction confidence
    result["_extraction_confidence"] = _calculate_rule_based_confidence(result)
    result["_extraction_method"] = "rule_based"
    
    return result


def _calculate_rule_based_confidence(extracted: Dict[str, Any]) -> float:
    """
    Calculate confidence score for rule-based extraction.
    
    Returns a score between 0.0 and 1.0 based on critical fields extracted.
    """
    # Critical fields that MUST be present for a valid LC extraction
    critical_fields = ["number", "amount"]
    critical_count = sum(1 for f in critical_fields if extracted.get(f))
    
    # Important fields that should be present
    important_fields = ["applicant", "beneficiary", "currency"]
    important_count = sum(1 for f in important_fields if extracted.get(f))
    
    # Optional but valuable fields
    optional_fields = ["ports", "incoterm", "timeline", "ucp_reference"]
    optional_count = sum(1 for f in optional_fields if extracted.get(f))
    
    # Weight calculation: critical (50%), important (30%), optional (20%)
    critical_score = (critical_count / len(critical_fields)) * 0.50
    important_score = (important_count / len(important_fields)) * 0.30
    optional_score = (optional_count / len(optional_fields)) * 0.20
    
    return round(critical_score + important_score + optional_score, 2)


# =====================================================================
# ASYNC EXTRACTION WITH AI FALLBACK
# =====================================================================

async def extract_lc_structured_with_ai_fallback(
    raw_text: str,
    ai_threshold: float = 0.5,
    always_try_ai: bool = False,
) -> Dict[str, Any]:
    """
    Extract LC fields using rule-based parsers, with AI fallback.
    
    This is the RECOMMENDED extraction function that provides:
    1. Fast rule-based extraction (MT700, regex)
    2. AI fallback when confidence is low
    3. Best-of-both merging when AI improves results
    
    Args:
        raw_text: OCR/document text
        ai_threshold: Use AI if rule-based confidence is below this
        always_try_ai: Always run AI extraction (for comparison/merge)
    
    Returns:
        Extracted LC structure with confidence and method metadata
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Step 1: Try rule-based extraction first (fast, cheap)
    rule_result = extract_lc_structured(raw_text)
    rule_confidence = rule_result.get("_extraction_confidence", 0.0)
    
    logger.info(
        "LC Extraction (rule-based): confidence=%.2f critical_fields=%s",
        rule_confidence,
        bool(rule_result.get("number") and rule_result.get("amount"))
    )
    
    # Step 2: Decide if AI is needed
    needs_ai = rule_confidence < ai_threshold or always_try_ai
    
    if not needs_ai:
        logger.info("Rule-based extraction sufficient, skipping AI")
        return rule_result
    
    # Step 3: Run AI extraction
    logger.info("Running AI extraction (rule confidence %.2f < threshold %.2f)", rule_confidence, ai_threshold)
    
    try:
        from .ai_lc_extractor import extract_lc_with_ai, convert_ai_to_lc_structure
        
        ai_result, ai_confidence, provider = await extract_lc_with_ai(raw_text)
        
        logger.info(
            "AI extraction complete: provider=%s confidence=%.2f",
            provider, ai_confidence
        )
        
        if ai_confidence <= 0:
            # AI also failed, return rule-based result
            logger.warning("AI extraction also failed, using rule-based result")
            return rule_result
        
        # Convert AI result to standard structure
        ai_structured = convert_ai_to_lc_structure(ai_result)
        ai_structured["_extraction_confidence"] = ai_confidence
        ai_structured["_ai_provider"] = provider
        
        # Step 4: Merge or select best result
        if ai_confidence > rule_confidence:
            # AI did better - use AI result, merge in any rule-based extras
            logger.info("Using AI result (%.2f > %.2f)", ai_confidence, rule_confidence)
            final_result = _merge_extraction_results(ai_structured, rule_result)
            final_result["_extraction_method"] = "ai_primary"
        else:
            # Rule-based did better - use rule result, fill gaps with AI
            logger.info("Using rule-based result (%.2f >= %.2f)", rule_confidence, ai_confidence)
            final_result = _merge_extraction_results(rule_result, ai_structured)
            final_result["_extraction_method"] = "rule_primary_ai_enhanced"
        
        return final_result
        
    except ImportError as e:
        logger.warning(f"AI extraction not available: {e}")
        return rule_result
    except Exception as e:
        logger.error(f"AI extraction error: {e}", exc_info=True)
        return rule_result


def _merge_extraction_results(
    primary: Dict[str, Any],
    secondary: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Merge two extraction results, using primary values but filling gaps from secondary.
    """
    result = dict(primary)
    
    # Fields to potentially fill from secondary if missing in primary
    fill_fields = [
        "number", "amount", "currency", "applicant", "beneficiary",
        "ports", "incoterm", "issuing_bank", "advising_bank",
        "ucp_reference", "timeline", "goods", "goods_summary",
    ]
    
    for field in fill_fields:
        primary_val = primary.get(field)
        secondary_val = secondary.get(field)
        
        # If primary is missing but secondary has it, use secondary
        if (primary_val is None or primary_val == "" or primary_val == {}) and secondary_val:
            result[field] = secondary_val
            result.setdefault("_filled_from_secondary", []).append(field)
    
    return result
