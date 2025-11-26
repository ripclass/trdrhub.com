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
    "Document": "wrapper",
}


def detect_iso20022_schema(xml_text: str) -> Tuple[Optional[str], float]:
    """
    Detect which ISO 20022 schema the XML uses.
    
    Returns:
        (schema_type, confidence)
    """
    if not xml_text or "<" not in xml_text:
        return None, 0.0
    
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
    if schema_type in ("tsrv.001", "tsrv.003"):
        _extract_undertaking(root, lc_context)
    elif schema_type in ("tsin.001", "tsin.002", "tsmt.014", "tsmt.015", "tsmt.016"):
        _extract_documentary_credit(root, lc_context)
    else:
        # Generic/fallback extraction
        _extract_generic_trade_instrument(root, lc_context)
    
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


def _extract_documentary_credit(root: ET.Element, context: Dict[str, Any]) -> None:
    """Extract from Documentary Credit schema (tsin/tsmt)."""
    # Find LC details block
    lc_dtls = (
        _find_descendant(root, "DocCdtDtls") or
        _find_descendant(root, "DocCrdtDtls") or
        _find_descendant(root, "LCDtls") or
        _find_descendant(root, "TradInstr")
    )
    
    if lc_dtls:
        # LC Reference
        ref = (
            _get_text(lc_dtls, "DocCdtId") or
            _get_text(lc_dtls, "LCId") or
            _get_text(lc_dtls, "InstrId") or
            _get_text(lc_dtls, "Id")
        )
        if ref:
            context["number"] = ref
        
        # Amount
        amt = (
            _find_descendant(lc_dtls, "LcAmt") or
            _find_descendant(lc_dtls, "DocCdtAmt") or
            _find_descendant(lc_dtls, "Amt")
        )
        if amt is not None:
            _extract_amount(amt, context)
        
        # Applicant (Buyer/Orderer)
        applicant = (
            _find_descendant(lc_dtls, "Applcnt") or
            _find_descendant(lc_dtls, "Buyer") or
            _find_descendant(lc_dtls, "Ordrr")
        )
        if applicant:
            context["applicant"] = _parse_party_info(applicant)
        
        # Beneficiary (Seller)
        beneficiary = (
            _find_descendant(lc_dtls, "Bnfcry") or
            _find_descendant(lc_dtls, "Seller")
        )
        if beneficiary:
            context["beneficiary"] = _parse_party_info(beneficiary)
        
        # Issuing Bank
        issuing_bank = (
            _find_descendant(lc_dtls, "IssgBk") or
            _find_descendant(lc_dtls, "IssuingBank") or
            _find_descendant(lc_dtls, "IssrBk")
        )
        if issuing_bank:
            context["issuing_bank"] = _parse_party_info(issuing_bank)
        
        # Advising Bank
        advising_bank = (
            _find_descendant(lc_dtls, "AdvsgBk") or
            _find_descendant(lc_dtls, "AdvisingBank")
        )
        if advising_bank:
            context["advising_bank"] = _parse_party_info(advising_bank)
    
    # Terms and Conditions
    terms = (
        _find_descendant(root, "TermsAndConds") or
        _find_descendant(root, "TermsAndCond") or
        _find_descendant(root, "LCTerms")
    )
    if terms:
        _extract_terms(terms, context)
    
    # Shipment Details
    shipment = (
        _find_descendant(root, "ShipmntDtls") or
        _find_descendant(root, "ShipmentRoute") or
        _find_descendant(root, "Shipment")
    )
    if shipment:
        _extract_shipment(shipment, context)
    
    # Goods
    goods = _find_descendant(root, "Goods") or _find_descendant(root, "GoodsDtls")
    if goods:
        _extract_goods(goods, context)


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


# =====================================================================
# HELPER FUNCTIONS
# =====================================================================

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
    try:
        root = ET.fromstring(xml_text)
        texts = []
        for elem in root.iter():
            if elem.text and elem.text.strip():
                local = _local_name(elem.tag)
                texts.append(f"{local}: {elem.text.strip()}")
        return "\n".join(texts)
    except Exception:
        # Fallback: strip tags with regex
        text = re.sub(r'<[^>]+>', ' ', xml_text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

