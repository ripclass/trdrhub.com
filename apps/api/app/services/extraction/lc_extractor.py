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
    
    # LC number - with validation to reject garbage
    lc_number_candidate = (
        mt_fields.get("reference") or 
        (mt_core.get("number") if mt_core else None) or 
        _first(LC_NO_RE, text)
    )
    lc_number = lc_number_candidate if _is_valid_lc_number(lc_number_candidate) else None
    
    # Amount and Currency
    credit_amount = mt_fields.get("credit_amount")
    currency = None
    if credit_amount and isinstance(credit_amount, dict):
        amount_raw = str(credit_amount.get("amount", ""))
        currency = credit_amount.get("currency")
    else:
        amount_raw = (mt_core.get("amount") if mt_core else None) or _amount(text)
        currency = mt_core.get("currency") if mt_core else None
    
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
    
    if not applicant_raw or not beneficiary_raw:
        applicant_line, beneficiary_line = _parse_parties(text)
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
    lc_structured: Dict[str, Any] = {
        "number": lc_number,
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
        # Extract lc_type as string from lc_classification.types array
        lc_classification = mt_fields.get("lc_classification", {})
        if isinstance(lc_classification, dict) and "types" in lc_classification:
            types_list = lc_classification.get("types", [])
            lc_structured["lc_type"] = ", ".join(types_list) if types_list else "unknown"
            lc_structured["lc_classification"] = lc_classification  # Keep original for reference
        else:
            lc_structured["lc_type"] = lc_classification if isinstance(lc_classification, str) else "unknown"
        
        # Promote commonly-used fields to top-level for compatibility
        if not lc_structured.get("applicant") and mt_fields.get("applicant"):
            lc_structured["applicant"] = {"name": _strip(mt_fields["applicant"])}
        if not lc_structured.get("beneficiary") and mt_fields.get("beneficiary"):
            lc_structured["beneficiary"] = {"name": _strip(mt_fields["beneficiary"])}
        if not lc_structured.get("amount") and credit_amount:
            lc_structured["amount"] = credit_amount

    # Cleanup None keys
    result = {k: v for k, v in lc_structured.items() if v not in (None, [], {})}
    
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
