# apps/api/app/services/extraction/iso20022_lc_extractor.py
"""
Enhanced ISO 20022 LC Extraction with AI Fallback.

ISO 20022 is the new global standard for financial messaging (replacing MT700).
This module provides:
1. Multi-schema support (tsrv, tsin, tsmt messages)
2. Confidence scoring
3. AI fallback for malformed XML
4. Field validation

ISO 20022 LC Message Types:
- tsrv.001 - Undertaking Issuance (Standby LC)
- tsin.001 - Documentary Credit Notification
- tsmt.014 - Documentary Credit Issuance
- tsmt.015 - Documentary Credit Amendment
"""

import re
import logging
import xml.etree.ElementTree as ET
from typing import Dict, Any, Optional, List, Tuple

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

logger = logging.getLogger(__name__)


class ISO20022ParseError(Exception):
    """Raised when an ISO 20022 LC payload cannot be parsed."""
    pass


# =====================================================================
# ISO 20022 SCHEMA DETECTION
# =====================================================================

# Known ISO 20022 LC-related namespaces and root elements
ISO20022_LC_SCHEMAS = {
    # Undertaking (Standby LC)
    "UndtkgIssnc": "tsrv.001",
    "UndtkgAmdmnt": "tsrv.003",
    
    # Documentary Credit
    "DocCdtIssnc": "tsin.001",
    "DocCdtNtfctn": "tsin.002",
    
    # Trade Services Management
    "DocCrdtIssnc": "tsmt.014",
    "DocCrdtAmdmnt": "tsmt.015",
    "DocCrdtNotfctn": "tsmt.016",
    
    # Generic Trade Instrument (common in simplified implementations)
    "TradInstr": "generic",
}

DOCUMENTARY_CREDIT_SCHEMAS = {"tsin.001", "tsin.002", "tsmt.014", "tsmt.015", "tsmt.016"}
UNDERTAKING_SCHEMAS = {"tsrv.001", "tsrv.003"}
LEGACY_WORKFLOW_ALIASES = {"import", "export", "draft", "unknown"}

ISO_FORM_CODE_TO_LC_TYPE = {
    "IRVC": "irrevocable",
    "RVOC": "revocable",
}


def detect_iso20022_schema(xml_text: str) -> Tuple[Optional[str], float]:
    """
    Detect which ISO 20022 schema the XML uses.
    
    Returns:
        (schema_type, confidence)
    """
    if not xml_text or "<" not in xml_text:
        return None, 0.0

    namespace_match = re.search(r"urn:iso:std:iso:20022:tech:xsd:((?:tsrv|tsmt|tsin)\.\d{3})", xml_text, re.IGNORECASE)
    if namespace_match:
        return namespace_match.group(1).lower(), 0.96
    
    # Check for known root elements
    for element, schema in ISO20022_LC_SCHEMAS.items():
        if f"<{element}" in xml_text or f":{element}" in xml_text:
            return schema, 0.95
    
    # Check for ISO 20022 namespace
    if "iso20022" in xml_text.lower() or "urn:iso:std:iso:20022" in xml_text:
        return "unknown_iso20022", 0.7
    
    # Check for common ISO 20022 elements
    iso_elements = ["BIC", "IBAN", "Ccy", "Amt", "CtryOfRes", "PstlAdr"]
    matches = sum(1 for elem in iso_elements if f"<{elem}" in xml_text or f":{elem}>" in xml_text)
    if matches >= 3:
        return "probable_iso20022", 0.6
    
    return None, 0.0


# =====================================================================
# ENHANCED ISO 20022 PARSER
# =====================================================================

def extract_iso20022_lc_enhanced(xml_text: str) -> Dict[str, Any]:
    """
    Enhanced ISO 20022 LC parser with multi-schema support.
    
    Supports:
    - tsrv.001 (Undertaking/Standby LC)
    - tsin.001 (Documentary Credit)
    - tsmt.014 (LC Issuance)
    - Generic TradInstr format
    """
    if not xml_text or not xml_text.strip():
        raise ISO20022ParseError("Empty XML text")
    
    # Detect schema
    schema_type, detection_confidence = detect_iso20022_schema(xml_text)
    
    if not schema_type:
        raise ISO20022ParseError("Not recognized as ISO 20022 LC format")
    
    logger.info(f"ISO 20022 schema detected: {schema_type} (confidence: {detection_confidence})")
    
    # ISO 20022 PDFs often embed the XML inside non-XML prose (headers,
    # footers, bank instructions).  Extract just the <Document>…</Document>
    # portion so ElementTree can parse it.
    doc_match = re.search(r'(<Document\b[^>]*>.*?</Document\s*>)', xml_text, re.DOTALL)
    if doc_match:
        xml_text = doc_match.group(1)

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise ISO20022ParseError(f"Invalid XML: {exc}") from exc
    
    # Initialize context
    lc_context: Dict[str, Any] = {
        "format": "iso20022",
        "schema": schema_type,
        "_detection_confidence": detection_confidence,
    }
    
    # Try different extraction strategies based on schema
    if schema_type.startswith("tsrv."):
        _extract_undertaking(root, lc_context)
    elif schema_type.startswith("tsin.") or schema_type.startswith("tsmt."):
        _extract_documentary_credit(root, lc_context)
    else:
        # Generic/fallback extraction
        _extract_generic_trade_instrument(root, lc_context)
    
    _populate_iso_lc_type(root, lc_context)
    lc_context["lc_classification"] = build_lc_classification(lc_context)
    if not lc_context.get("required_document_types"):
        required_codes = [
            str(entry.get("code")).strip()
            for entry in lc_context["lc_classification"].get("required_documents", [])
            if isinstance(entry, dict) and str(entry.get("code") or "").strip()
        ]
        if required_codes:
            lc_context["required_document_types"] = required_codes

    # Calculate extraction confidence
    lc_context["_extraction_confidence"] = _calculate_iso20022_confidence(lc_context)
    lc_context["_extraction_method"] = "iso20022_structured"
    
    return lc_context


def _extract_undertaking(root: ET.Element, context: Dict[str, Any]) -> None:
    """Extract from Undertaking (Standby LC) schema."""
    # Find undertaking details
    undtkg = _find_descendant(root, "Undtkg") or _find_descendant(root, "UndtkgDtls")
    
    if undtkg:
        # Reference/ID
        ref = _get_text(undtkg, "Id") or _get_text(undtkg, "UndtkgId")
        if ref:
            context["number"] = ref
        
        # Amount
        amt = _find_descendant(undtkg, "Amt") or _find_descendant(undtkg, "UndtkgAmt")
        if amt is not None:
            _extract_amount(amt, context)
        
        # Applicant (Instructing Party)
        applicant = _find_descendant(undtkg, "Applcnt") or _find_descendant(undtkg, "InstrngPty")
        if applicant:
            context["applicant"] = _parse_party_info(applicant)
        
        # Beneficiary
        beneficiary = _find_descendant(undtkg, "Bnfcry")
        if beneficiary:
            context["beneficiary"] = _parse_party_info(beneficiary)
        
        # Issuer (Issuing Bank)
        issuer = _find_descendant(undtkg, "Issr") or _find_descendant(undtkg, "IssgBk")
        if issuer:
            context["issuing_bank"] = _parse_party_info(issuer)
        
        # Dates
        expiry = _get_text(undtkg, "XpryDt") or _get_text(undtkg, "ExpiryDt")
        if expiry:
            context.setdefault("dates", {})["expiry"] = expiry

    # Fill in the MT700 mandatory fields that aren't covered by the
    # undertaking-specific extraction above (sequence_of_total, issue_date,
    # applicable_rules, available_with/by, additional_conditions,
    # period_for_presentation).
    _extract_mt700_mandatory_equivalents(root, context)


def _first_descendant(root: ET.Element, *local_names: str) -> Optional[ET.Element]:
    """Return the first descendant matching any of the local names.

    Uses explicit `is not None` checks instead of element truthiness — a
    leaf element like `<LcAmt Ccy="USD">458750.00</LcAmt>` has no children
    and evaluates as falsy under `or`-chains, which is the ElementTree
    truthiness gotcha that was silently skipping amount extraction before.
    """
    for name in local_names:
        elem = _find_descendant(root, name)
        if elem is not None:
            return elem
    return None


def _extract_documentary_credit(root: ET.Element, context: Dict[str, Any]) -> None:
    """Extract from Documentary Credit schema (tsin/tsmt)."""
    # Find LC details block
    lc_dtls = _first_descendant(root, "DocCdtDtls", "DocCrdtDtls", "LCDtls", "TradInstr")

    if lc_dtls is not None:
        # LC Reference
        ref = (
            _get_text(lc_dtls, "DocCdtId")
            or _get_text(lc_dtls, "LCId")
            or _get_text(lc_dtls, "InstrId")
            or _get_text(lc_dtls, "Id")
        )
        if ref:
            context["number"] = ref

        form = _first_descendant(lc_dtls, "DocCdtFrm", "DocCrdtFrm")
        if form is not None:
            form_code = _get_text(form, "Cd") or _get_text(form, "Prtry") or _element_text(form)
            normalized_form = _normalize_iso_form_of_credit(form_code)
            if normalized_form:
                context["form_of_doc_credit"] = normalized_form

        # Amount — must use _first_descendant because <LcAmt> is a leaf
        # element and ElementTree treats leaves as falsy in `or`-chains.
        amt = _first_descendant(lc_dtls, "LcAmt", "DocCdtAmt", "TtlAmt", "Amt")
        if amt is not None:
            _extract_amount(amt, context)

        # Applicant (Buyer/Orderer)
        applicant = _first_descendant(lc_dtls, "Applcnt", "Buyer", "Ordrr")
        if applicant is not None:
            context["applicant"] = _parse_party_info(applicant)

        # Beneficiary (Seller)
        beneficiary = _first_descendant(lc_dtls, "Bnfcry", "Seller")
        if beneficiary is not None:
            context["beneficiary"] = _parse_party_info(beneficiary)

        # Issuing Bank
        issuing_bank = _first_descendant(lc_dtls, "IssgBk", "IssuingBank", "IssrBk")
        if issuing_bank is not None:
            context["issuing_bank"] = _parse_party_info(issuing_bank)

        # Advising Bank
        advising_bank = _first_descendant(lc_dtls, "AdvsgBk", "AdvisingBank")
        if advising_bank is not None:
            context["advising_bank"] = _parse_party_info(advising_bank)
    else:
        # Flat/simplified ISO schema — elements are direct children of root,
        # not nested under DocCdtDtls / LCDtls wrappers.  Common in
        # trade-settlement messages (tsmt.*) and simplified implementations.
        ref = (
            _get_descendant_text(root, "TxId")
            or _get_descendant_text(root, "InstrId")
            or _get_descendant_text(root, "DocCdtId")
            or _get_descendant_text(root, "Id")
        )
        if ref:
            context["number"] = ref

        amt = _first_descendant(root, "TtlAmt", "LcAmt", "DocCdtAmt", "Amt")
        if amt is not None:
            _extract_amount(amt, context)

        applicant = _first_descendant(root, "Applcnt", "Buyer", "Ordrr")
        if applicant is not None:
            context["applicant"] = _parse_party_info(applicant)

        beneficiary = _first_descendant(root, "Bnfcry", "Seller")
        if beneficiary is not None:
            context["beneficiary"] = _parse_party_info(beneficiary)

        issuing_bank = _first_descendant(root, "IssgBk", "IssuingBank", "IssrBk")
        if issuing_bank is not None:
            context["issuing_bank"] = _parse_party_info(issuing_bank)

        advising_bank = _first_descendant(root, "AdvsgBk", "AdvisingBank")
        if advising_bank is not None:
            context["advising_bank"] = _parse_party_info(advising_bank)

    # Terms and Conditions
    terms = _first_descendant(root, "TermsAndConds", "TermsAndCond", "LCTerms")
    if terms is not None:
        _extract_terms(terms, context)

    # Shipment Details
    shipment = _first_descendant(root, "ShipmntDtls", "ShipmentRoute", "Shipment")
    if shipment is not None:
        _extract_shipment(shipment, context)

    # Goods
    goods = _first_descendant(root, "Goods", "GoodsDtls")
    if goods is not None:
        _extract_goods(goods, context)

    _extract_required_documents(root, context)

    # ----- Flat-element fallbacks for simplified ISO schemas -----
    # When standard wrapper elements (TermsAndConds, ShipmntDtls, Goods)
    # are absent, look for flat elements directly under root.

    if not context.get("dates", {}).get("latest_shipment") and "latest_shipment_date" not in context:
        latest_ship = _get_descendant_text(root, "LatstShipmntDt") or _get_descendant_text(root, "LtstShipmntDt")
        if latest_ship:
            context.setdefault("dates", {})["latest_shipment"] = latest_ship.strip()
            context["latest_shipment_date"] = latest_ship.strip()

    if not context.get("dates", {}).get("expiry"):
        expiry = _get_descendant_text(root, "XpryDt") or _get_descendant_text(root, "ExpiryDt")
        if expiry:
            context.setdefault("dates", {})["expiry"] = expiry.strip()
            context["expiry_date"] = expiry.strip()

    if not context.get("ports", {}).get("loading") and "port_of_loading" not in context:
        pol = _get_descendant_text(root, "LodgPort") or _get_descendant_text(root, "PortOfLoading") or _get_descendant_text(root, "PortOfLdg")
        if pol:
            context.setdefault("ports", {})["loading"] = pol.strip()
            context["port_of_loading"] = pol.strip()

    if not context.get("ports", {}).get("discharge") and "port_of_discharge" not in context:
        pod = _get_descendant_text(root, "DschrgPort") or _get_descendant_text(root, "PortOfDischarge") or _get_descendant_text(root, "PortOfDschg")
        if pod:
            context.setdefault("ports", {})["discharge"] = pod.strip()
            context["port_of_discharge"] = pod.strip()

    if not context.get("goods_description"):
        goods_desc = _get_descendant_text(root, "GoodsDesc") or _get_descendant_text(root, "GdsDesc")
        if goods_desc:
            context["goods_description"] = goods_desc.strip()

    if not context.get("incoterm"):
        incoterm_text = _get_descendant_text(root, "IncoTerm") or _get_descendant_text(root, "Incoterms") or _get_descendant_text(root, "Incoterm")
        if incoterm_text:
            context["incoterm"] = _normalize_incoterm(incoterm_text)

    if not context.get("documents_required"):
        reqrd_docs = _get_descendant_text(root, "ReqrdDocs") or _get_descendant_text(root, "DocReqrd")
        if reqrd_docs:
            # Pipe-delimited or newline-delimited list
            parts = [p.strip() for p in re.split(r'[|\n]', reqrd_docs) if p.strip()]
            if parts:
                context["documents_required"] = parts

    # Fill in the MT700 mandatory fields the rest of this function doesn't
    # cover (Field 27, 31C, 40E, 41a, 47A, 48).
    _extract_mt700_mandatory_equivalents(root, context)


def _extract_generic_trade_instrument(root: ET.Element, context: Dict[str, Any]) -> None:
    """Fallback extraction for generic TradInstr format."""
    trad_instr = _find_descendant(root, "TradInstr")
    
    if not trad_instr:
        # Try to find any element with LC-like content
        for elem in root.iter():
            local = _local_name(elem.tag)
            if local in ("InstrId", "LCId", "DocCdtId"):
                context["number"] = elem.text
            elif local in ("LcAmt", "Amt", "Amount"):
                _extract_amount(elem, context)
            elif local in ("Buyer", "Applcnt", "Applicant"):
                context["applicant"] = _parse_party_info(elem)
            elif local in ("Seller", "Bnfcry", "Beneficiary"):
                context["beneficiary"] = _parse_party_info(elem)
        return
    
    # Standard TradInstr extraction
    instr_id = _get_text(trad_instr, "InstrId")
    if instr_id:
        context["number"] = instr_id
    
    amt = _find_descendant(trad_instr, "LcAmt")
    if amt is not None:
        _extract_amount(amt, context)
    
    buyer = _find_descendant(trad_instr, "Buyer")
    if buyer:
        context["applicant"] = _parse_party_info(buyer)
    
    seller = _find_descendant(trad_instr, "Seller")
    if seller:
        context["beneficiary"] = _parse_party_info(seller)
    
    issuing_bank = _find_descendant(trad_instr, "IssuingBank")
    if issuing_bank:
        context["issuing_bank"] = _parse_party_info(issuing_bank)
    
    terms = _find_descendant(trad_instr, "TermsAndCond")
    if terms:
        _extract_terms(terms, context)

    # Fill in the MT700 mandatory fields not covered above.
    _extract_mt700_mandatory_equivalents(root, context)


def _populate_iso_lc_type(root: ET.Element, context: Dict[str, Any]) -> None:
    """
    Preserve only workflow-compatible legacy lc_type values.

    ISO schema/type/form signals belong in canonical lc_classification, not the
    backward-compatible lc_type workflow alias.
    """
    candidate = str(context.get("lc_type") or "").strip().lower()
    if candidate in LEGACY_WORKFLOW_ALIASES:
        context["lc_type"] = candidate
        context["lc_type_reason"] = context.get("lc_type_reason") or "Preserved workflow alias from ISO context."
        context["lc_type_confidence"] = float(context.get("lc_type_confidence") or 0.0)
        context["lc_type_source"] = context.get("lc_type_source") or "legacy_compatibility"
        return

    for key in ("lc_type", "lc_type_reason", "lc_type_confidence", "lc_type_source"):
        context.pop(key, None)


def _extract_iso_lc_type_signal(root: ET.Element) -> Optional[str]:
    """Extract the strongest LC-type signal from ISO XML."""
    type_node = _find_descendant(root, "DocCdtTp") or _find_descendant(root, "DocCrdtTp")
    if type_node is not None:
        explicit = _get_text(type_node, "Prtry") or _get_text(type_node, "Cd")
        if explicit:
            return explicit

    form_node = _find_descendant(root, "DocCdtFrm") or _find_descendant(root, "DocCrdtFrm")
    if form_node is not None:
        form_code = _get_text(form_node, "Cd")
        if form_code:
            return form_code

    availability_node = _find_descendant(root, "AvlblBy")
    if availability_node is not None:
        availability_code = _get_text(availability_node, "Cd")
        if availability_code:
            return availability_code

    payment_node = _find_descendant(root, "PmtTerms")
    if payment_node is not None:
        payment_code = _get_text(payment_node, "Cd")
        if payment_code:
            return payment_code

    return None


def _normalize_iso_lc_type(value: Optional[str]) -> Optional[str]:
    """Normalize ISO XML type/form codes into LCopilot's existing LC labels."""
    if not value:
        return None

    raw = str(value).strip()
    upper = raw.upper()
    lowered = raw.lower()

    if upper in ISO_FORM_CODE_TO_LC_TYPE:
        return ISO_FORM_CODE_TO_LC_TYPE[upper]
    if upper == "SIGU" or "sight" in lowered:
        return "sight"
    if upper == "DEFR" or "deferred" in lowered:
        return "deferred"
    if upper in {"ACCP", "USAN"} or "usance" in lowered or "acceptance" in lowered:
        return "usance"
    if "standby" in lowered or "sblc" in lowered or "undertaking" in lowered:
        return "standby"
    if "transferable" in lowered or "transfer" in lowered:
        return "transferable"
    if "irrevocable" in lowered:
        return "irrevocable"
    if "revocable" in lowered:
        return "revocable"
    if "documentary" in lowered or "doc credit" in lowered or "doccrdt" in lowered or "doccdt" in lowered:
        return "documentary"

    return None


def _normalize_iso_form_of_credit(value: Optional[str]) -> Optional[str]:
    if not value:
        return None

    upper = str(value).strip().upper()
    if upper == "IRVC":
        return "IRREVOCABLE"
    if upper == "RVOC":
        return "REVOCABLE"
    if "IRREVOCABLE" in upper:
        return "IRREVOCABLE"
    if "REVOCABLE" in upper:
        return "REVOCABLE"
    return None


# =====================================================================
# HELPER FUNCTIONS
# =====================================================================

_ISO_AVAILABLE_BY_CODE_MAP = {
    "PYMT": "PAYMENT",
    "PYMNT": "PAYMENT",
    "PAYMENT": "PAYMENT",
    "ACCP": "ACCEPTANCE",
    "ACPT": "ACCEPTANCE",
    "ACCEPTANCE": "ACCEPTANCE",
    "NEGO": "NEGOTIATION",
    "NEGOTIATION": "NEGOTIATION",
    "DFRD": "DEFERRED PAYMENT",
    "DEFERRED": "DEFERRED PAYMENT",
    "DEFRD": "DEFERRED PAYMENT",
    "MIXD": "MIXED PAYMENT",
    "MIXED": "MIXED PAYMENT",
}


def _normalize_iso_applicable_rules(code: Optional[str], version: Optional[str]) -> Optional[str]:
    """Turn an ISO 20022 <ApplRules> code + version into an MT700 Field 40E value.

    Examples:
      code="UCP", version="600"     -> "UCP600"
      code="UCP"                    -> "UCP LATEST VERSION"
      code="ISP", version="98"      -> "ISP98"
      code="URDG", version="758"    -> "URDG758"
      code=None, version=None       -> None
    """
    code_clean = (code or "").strip().upper()
    version_clean = (version or "").strip()
    if not code_clean and not version_clean:
        return None
    if code_clean and version_clean:
        # "UCP" + "600" -> "UCP600"; leave whitespace in for multi-word rules.
        if code_clean.isalpha() and version_clean.isdigit():
            return f"{code_clean}{version_clean}"
        return f"{code_clean} {version_clean}".strip()
    if code_clean:
        return f"{code_clean} LATEST VERSION"
    return version_clean or None


def _parse_iso_available_by(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    normalized = str(value).strip().upper()
    return _ISO_AVAILABLE_BY_CODE_MAP.get(normalized, normalized or None)


def _coerce_iso_presentation_period_days(value: Optional[str]) -> Optional[int]:
    """Accept '21', 'P21D' (ISO 8601 duration), '21 DAYS', etc."""
    if value is None:
        return None
    s = str(value).strip().upper()
    if not s:
        return None
    # ISO 8601 duration form: P21D, P2W, etc.
    if s.startswith("P") and "D" in s:
        try:
            digits = s[1:].rstrip("D")
            return int(digits)
        except ValueError:
            pass
    if s.startswith("P") and "W" in s:
        try:
            digits = s[1:].rstrip("W")
            return int(digits) * 7
        except ValueError:
            pass
    # Plain "21" / "21 DAYS"
    lead = "".join(ch for ch in s if ch.isdigit())
    if lead:
        try:
            return int(lead[:6])
        except ValueError:
            return None
    return None


def _extract_mt700_mandatory_equivalents(root: ET.Element, context: Dict[str, Any]) -> None:
    """Populate the 6 MT700 mandatory fields the legacy extractor missed.

    Covers:
      - Field 27  (sequence_of_total)        — from <MsgPgntn> or <SeqNb>
      - Field 31C (issue_date)               — from <IsseDt> / <IssueDate>
                                                / <DtAndPlcOfIsse>
      - Field 40E (applicable_rules)         — from <ApplRules> / <ApplcblRules>
      - Field 41a (available_with/by)        — from <AvlblWth> / <AvlblBy>
      - Field 47A (additional_conditions)    — from <AddtlCondtns> / <SpclTerms>
      - Field 48  (period_for_presentation)  — from <PresntnPrd> / <PrsttnPrd>

    Every field is best-effort. Missing elements are silently skipped — we
    write a key only when we actually found something, so downstream
    consumers can cleanly tell "unknown" (key absent) from "explicitly blank".
    """

    # ---- Field 27: Sequence of Total ----
    # ISO 20022 has no direct equivalent. tsmt messages use <MsgPgntn> with
    # <PgNb> and <LastPgInd>. Translate that to MT700 "page/total".
    pagination = _first_descendant(root, "MsgPgntn", "MsgPagntn")
    if pagination is not None:
        page_nb = _get_text(pagination, "PgNb")
        last_page = _get_text(pagination, "LastPgInd")
        if page_nb:
            page_num = page_nb.strip()
            if last_page and last_page.strip().lower() in {"true", "yes", "1"}:
                context["sequence_of_total"] = f"{page_num}/{page_num}"
            else:
                # Unknown total — just emit the page number with an open
                # total so downstream knows this isn't necessarily "1/1".
                context["sequence_of_total"] = f"{page_num}/?"
    # Fall back to a flat SeqNb element.
    if "sequence_of_total" not in context:
        seq_nb = _get_descendant_text(root, "SeqNb") or _get_descendant_text(root, "SeqNo")
        if seq_nb:
            context["sequence_of_total"] = seq_nb.strip()

    # ---- Field 31C: Issue Date (and optional issue place) ----
    issue_date = (
        _get_descendant_text(root, "IsseDt")
        or _get_descendant_text(root, "IssueDate")
        or _get_descendant_text(root, "IssDt")
        or _get_descendant_text(root, "DtOfIsse")
    )
    if not issue_date:
        # <DtAndPlcOfIsse><Dt>2026-04-15</Dt><Plc>NEW YORK</Plc></DtAndPlcOfIsse>
        issue_block = _first_descendant(root, "DtAndPlcOfIsse", "DateAndPlaceOfIssue")
        if issue_block is not None:
            issue_date = _get_text(issue_block, "Dt") or _get_text(issue_block, "Date")
            issue_place = _get_text(issue_block, "Plc") or _get_text(issue_block, "Place")
            if issue_place:
                context.setdefault("dates", {})["issue_place"] = issue_place.strip()
    if issue_date:
        context["issue_date"] = issue_date.strip()
        context.setdefault("dates", {})["issue_date"] = issue_date.strip()

    # ---- Field 40E: Applicable Rules ----
    rules_elem = _first_descendant(root, "ApplRules", "ApplcblRules", "Rules")
    if rules_elem is not None:
        # Two common shapes:
        #   <ApplRules><Cd>UCP</Cd><Vrsn>600</Vrsn></ApplRules>
        #   <ApplRules><Prtry>UCP LATEST VERSION</Prtry></ApplRules>
        code = _get_text(rules_elem, "Cd") or _get_text(rules_elem, "Code")
        version = _get_text(rules_elem, "Vrsn") or _get_text(rules_elem, "Version")
        prtry = _get_text(rules_elem, "Prtry") or _get_text(rules_elem, "Proprietary")
        normalized_rules = _normalize_iso_applicable_rules(code, version)
        if not normalized_rules and prtry:
            normalized_rules = prtry.strip()
        if not normalized_rules:
            # Fall back to the element's own text content if it was a leaf.
            leaf_text = (rules_elem.text or "").strip()
            normalized_rules = leaf_text or None
        if normalized_rules:
            context["applicable_rules"] = normalized_rules

    # ---- Field 41a: Available With / Available By ----
    avlbl_with = _first_descendant(root, "AvlblWth", "AvailableWith")
    if avlbl_with is not None:
        # <AvlblWth> is usually a party; parse name + BIC.
        party_info = _parse_party_info(avlbl_with)
        if party_info:
            context["available_with"] = party_info

    avlbl_by = _first_descendant(root, "AvlblBy", "AvailableBy")
    if avlbl_by is not None:
        by_code = _get_text(avlbl_by, "Cd") or _get_text(avlbl_by, "Code")
        by_prtry = _get_text(avlbl_by, "Prtry") or _get_text(avlbl_by, "Proprietary")
        by_text = by_code or by_prtry or (avlbl_by.text or "").strip() or None
        normalized_by = _parse_iso_available_by(by_text)
        if normalized_by:
            context["available_by"] = normalized_by

    # ---- Field 47A: Additional Conditions (free-text rules list) ----
    conditions: List[str] = []
    for condition_name in ("AddtlCondtns", "AddlCondtns", "AdditionalConditions", "SpclTerms", "SpclCond", "OthrInstrs"):
        for elem in root.iter():
            if _local_name(elem.tag) != condition_name:
                continue
            # Either free-text content or repeating <Txt> / <Cond> children.
            inline_text = (elem.text or "").strip()
            if inline_text:
                conditions.append(inline_text)
            for child in elem:
                child_name = _local_name(child.tag)
                if child_name in ("Txt", "Text", "Cond", "Condition"):
                    child_text = _element_text(child).strip()
                    if child_text:
                        conditions.append(child_text)
    if conditions:
        # De-dupe preserving order
        seen: set = set()
        deduped: List[str] = []
        for c in conditions:
            if c not in seen:
                deduped.append(c)
                seen.add(c)
        context["additional_conditions"] = deduped

    # ---- Field 48: Period for Presentation ----
    period_text = (
        _get_descendant_text(root, "PresntnPrd")
        or _get_descendant_text(root, "PrsttnPrd")
        or _get_descendant_text(root, "PresentationPeriod")
        or _get_descendant_text(root, "PresntnPeriod")
        or _get_descendant_text(root, "PrdForPresn")
    )
    if period_text:
        period_days = _coerce_iso_presentation_period_days(period_text)
        if period_days is not None:
            context["period_for_presentation"] = period_days
            context["period_for_presentation_days"] = period_days


def _extract_amount(amt_elem: ET.Element, context: Dict[str, Any]) -> None:
    """Extract amount and currency from amount element."""
    value = amt_elem.text
    if value:
        try:
            # Clean and parse amount
            clean_value = value.strip().replace(",", "").replace(" ", "")
            context.setdefault("amount", {})["value"] = float(clean_value)
        except (ValueError, TypeError):
            context.setdefault("amount", {})["value"] = value
    
    # Currency from attribute
    currency = (
        amt_elem.attrib.get("Ccy") or
        amt_elem.attrib.get("ccy") or
        amt_elem.attrib.get("currency") or
        amt_elem.attrib.get("Currency")
    )
    if currency:
        context.setdefault("amount", {})["currency"] = currency
        context["currency"] = currency


def _extract_terms(terms: ET.Element, context: Dict[str, Any]) -> None:
    """Extract terms and conditions."""
    dates = {}
    
    # Latest shipment date
    latest_ship = (
        _get_text(terms, "LatestShipDt") or
        _get_text(terms, "LtstShipmntDt") or
        _get_text(terms, "LastShipDate")
    )
    if latest_ship:
        dates["latest_shipment"] = latest_ship
    
    # Expiry date
    expiry = (
        _get_text(terms, "ExpiryDt") or
        _get_text(terms, "XpryDt") or
        _get_text(terms, "ExpDate")
    )
    if expiry:
        dates["expiry"] = expiry
    
    # Place of expiry
    place = _get_text(terms, "PlaceOfExpiry") or _get_text(terms, "XpryPlc")
    if place:
        dates["place_of_expiry"] = place
    
    if dates:
        context["dates"] = dates
    
    # Incoterm
    incoterm = _get_text(terms, "IncoTerm") or _get_text(terms, "Incoterms")
    if incoterm:
        context["incoterm"] = _normalize_incoterm(incoterm)
    
    # Partial shipments
    partial = _get_text(terms, "PrtlShipmnt") or _get_text(terms, "PartialShipment")
    if partial:
        context["partial_shipments"] = partial.upper()
    
    # Transshipment
    tranship = _get_text(terms, "Trnshpmnt") or _get_text(terms, "Transshipment")
    if tranship:
        context["transshipment"] = tranship.upper()


def _extract_shipment(shipment: ET.Element, context: Dict[str, Any]) -> None:
    """Extract shipment details."""
    ports = {}
    
    # Port of loading
    pol = (
        _get_text(shipment, "PortOfLoading") or
        _get_text(shipment, "PortOfLdg") or
        _get_text(shipment, "LoadingPort")
    )
    if pol:
        ports["loading"] = pol
    
    # Port of discharge
    pod = (
        _get_text(shipment, "PortOfDischarge") or
        _get_text(shipment, "PortOfDschg") or
        _get_text(shipment, "DischargePort")
    )
    if pod:
        ports["discharge"] = pod
    
    if ports:
        context["ports"] = ports


def _extract_goods(goods: ET.Element, context: Dict[str, Any]) -> None:
    """Extract goods information."""
    goods_items = []
    descriptions = []
    
    # Find line items
    for item in goods.iter():
        local = _local_name(item.tag)
        if local in ("LineItm", "GoodsItm", "Item"):
            desc = _get_text(item, "Desc") or _get_text(item, "Description")
            hs_code = _get_text(item, "HSCode") or _get_text(item, "HsCode")
            qty = _get_text(item, "Qty") or _get_text(item, "Quantity")
            
            if desc:
                descriptions.append(desc)
                goods_items.append({
                    "description": desc,
                    "hs_code": hs_code,
                    "quantity": qty,
                })
    
    if descriptions:
        context["goods_description"] = "; ".join(descriptions)
    if goods_items:
        context["goods_items"] = goods_items


def _extract_required_documents(root: ET.Element, context: Dict[str, Any]) -> None:
    """Extract ISO DocsReqrd entries into raw document requirement fields."""
    documents_required: List[str] = []

    for elem in root.iter():
        local = _local_name(elem.tag)
        if local not in ("DocsReqrd", "DocReqrd", "ReqdDoc"):
            continue

        descriptions: List[str] = []
        for child in elem.iter():
            child_local = _local_name(child.tag)
            if child_local in ("Desc", "Description", "DocDesc", "Narrative", "Txt"):
                text = _element_text(child)
                if text:
                    descriptions.append(text)

        if not descriptions:
            aggregate = _element_text(elem)
            if aggregate:
                descriptions.append(aggregate)

        for description in descriptions:
            normalized = description.strip()
            if normalized and normalized not in documents_required:
                documents_required.append(normalized)

    if documents_required:
        context["documents_required"] = documents_required


def _parse_party_info(party_elem: ET.Element) -> Dict[str, Any]:
    """Parse party information (applicant, beneficiary, bank)."""
    info = {}
    
    # Name - try multiple paths
    name = (
        _get_text(party_elem, "Nm") or
        _get_text(party_elem, "Name") or
        _get_text(party_elem, "FullNm") or
        _get_descendant_text(party_elem, "Nm")
    )
    if name:
        info["name"] = name
    
    # BIC
    bic = _get_text(party_elem, "BIC") or _get_text(party_elem, "BICFI")
    if bic:
        info["bic"] = bic
    
    # Address
    addr = _find_descendant(party_elem, "PstlAdr") or _find_descendant(party_elem, "Adr")
    if addr:
        street = _get_text(addr, "StrtNm") or _get_text(addr, "AdrLine")
        city = _get_text(addr, "TwnNm") or _get_text(addr, "City")
        country = _get_text(addr, "Ctry") or _get_text(addr, "CtryOfRes")
        
        addr_parts = [p for p in [street, city, country] if p]
        if addr_parts:
            info["address"] = ", ".join(addr_parts)
        if country:
            info["country"] = country
    
    return info if info else None


def _find_descendant(root: ET.Element, local_name: str) -> Optional[ET.Element]:
    """Find first descendant with matching local name."""
    for elem in root.iter():
        if _local_name(elem.tag) == local_name:
            return elem
    return None


def _get_text(parent: ET.Element, child_name: str) -> Optional[str]:
    """Get text content of a child element."""
    for child in parent:
        if _local_name(child.tag) == child_name:
            return child.text.strip() if child.text else None
    return None


def _get_descendant_text(root: ET.Element, local_name: str) -> Optional[str]:
    """Get text from first descendant with matching name."""
    elem = _find_descendant(root, local_name)
    return elem.text.strip() if elem is not None and elem.text else None


def _element_text(root: ET.Element) -> str:
    """Return concatenated text for an element and its descendants."""
    parts = [part.strip() for part in root.itertext() if isinstance(part, str) and part.strip()]
    return " ".join(parts)


def _local_name(tag: str) -> str:
    """Extract local name from possibly namespaced tag."""
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _normalize_incoterm(value: str) -> Optional[str]:
    """Normalize incoterm value."""
    if not value:
        return None
    
    upper = value.upper().strip()
    valid_incoterms = {
        "EXW", "FCA", "CPT", "CIP", "DAP", "DPU", "DDP",
        "FAS", "FOB", "CFR", "CIF"
    }
    
    # Extract incoterm from value
    for term in valid_incoterms:
        if term in upper:
            return term
    
    return upper if len(upper) <= 10 else None


def _calculate_iso20022_confidence(context: Dict[str, Any]) -> float:
    """Calculate extraction confidence score."""
    # Critical fields
    critical = ["number", "amount"]
    critical_found = sum(1 for f in critical if context.get(f))
    
    # Important fields
    important = ["applicant", "beneficiary", "currency"]
    important_found = sum(1 for f in important if context.get(f))
    
    # Optional fields
    optional = ["issuing_bank", "dates", "ports", "incoterm"]
    optional_found = sum(1 for f in optional if context.get(f))
    
    # Schema detection confidence
    detection_conf = context.get("_detection_confidence", 0.5)
    
    # Calculate weighted score
    critical_score = (critical_found / len(critical)) * 0.40
    important_score = (important_found / len(important)) * 0.25
    optional_score = (optional_found / len(optional)) * 0.15
    detection_score = detection_conf * 0.20
    
    return round(critical_score + important_score + optional_score + detection_score, 2)


# =====================================================================
# ASYNC EXTRACTION WITH AI FALLBACK
# =====================================================================

async def extract_iso20022_with_ai_fallback(
    xml_text: str,
    ai_threshold: float = 0.5,
) -> Dict[str, Any]:
    """
    Extract ISO 20022 LC with AI fallback for malformed XML.
    
    Args:
        xml_text: The XML content
        ai_threshold: Use AI if confidence is below this
    
    Returns:
        Extracted LC context with confidence metadata
    """
    # Try structured extraction first
    try:
        result = extract_iso20022_lc_enhanced(xml_text)
        confidence = result.get("_extraction_confidence", 0.0)
        
        logger.info(f"ISO 20022 structured extraction: confidence={confidence}")
        
        if confidence >= ai_threshold:
            return result
            
    except ISO20022ParseError as e:
        logger.warning(f"ISO 20022 parse error: {e}")
        result = {"_extraction_method": "iso20022_failed"}
        confidence = 0.0
    except Exception as e:
        logger.error(f"ISO 20022 extraction error: {e}", exc_info=True)
        result = {"_extraction_method": "iso20022_error"}
        confidence = 0.0
    
    # AI fallback
    logger.info(f"Using AI fallback for ISO 20022 (confidence {confidence} < threshold {ai_threshold})")
    
    try:
        from .ai_lc_extractor import extract_lc_with_ai, convert_ai_to_lc_structure
        
        # Strip XML tags for AI processing (it works better with plain text)
        plain_text = _xml_to_plain_text(xml_text)
        
        ai_result, ai_confidence, provider = await extract_lc_with_ai(plain_text)
        
        if ai_confidence > confidence:
            ai_structured = convert_ai_to_lc_structure(ai_result)
            ai_structured["format"] = "iso20022"
            ai_structured["_extraction_method"] = "iso20022_ai_fallback"
            ai_structured["_extraction_confidence"] = ai_confidence
            ai_structured["_ai_provider"] = provider
            
            # Merge any fields from structured extraction
            for key, value in result.items():
                if key not in ai_structured and value and not key.startswith("_"):
                    ai_structured[key] = value
            
            return ai_structured
    except Exception as e:
        logger.error(f"AI fallback for ISO 20022 failed: {e}", exc_info=True)
    
    # Return whatever we have
    return result


def _xml_to_plain_text(xml_text: str) -> str:
    """Convert XML to plain text for AI processing."""
    # Extract embedded XML first (same logic as the structured parser).
    doc_match = re.search(r'(<Document\b[^>]*>.*?</Document\s*>)', xml_text, re.DOTALL)
    if doc_match:
        xml_text = doc_match.group(1)

    try:
        root = ET.fromstring(xml_text)
        texts = []
        for elem in root.iter():
            local = _local_name(elem.tag)
            # Preserve currency attribute so downstream AI sees it.
            ccy = elem.attrib.get("Ccy") or elem.attrib.get("ccy")
            if elem.text and elem.text.strip():
                line = f"{local}: {elem.text.strip()}"
                if ccy:
                    line += f" (Currency: {ccy})"
                texts.append(line)
            elif ccy:
                texts.append(f"{local}: Currency={ccy}")
        return "\n".join(texts)
    except Exception:
        # Fallback: strip tags with regex but preserve Ccy attributes first.
        # Pull currency attributes before stripping tags.
        ccy_match = re.search(r'Ccy\s*=\s*["\'](\w{3})["\']', xml_text)
        text = re.sub(r'<[^>]+>', ' ', xml_text)
        text = re.sub(r'\s+', ' ', text)
        if ccy_match:
            text = f"Currency: {ccy_match.group(1)}\n{text.strip()}"
        return text.strip()

