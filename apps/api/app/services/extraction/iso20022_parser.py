"""
ISO20022 Trade Finance Message Parser

Parses ISO20022 XML messages for Documentary Credits (Letters of Credit).

Supported Message Types:
- trad.001.001.02: Documentary Credit Issuance
- trad.002.001.02: Documentary Credit Amendment
- trad.003.001.02: Documentary Credit Amendment Request
- tsmt.012.001.05: Baseline Report (BPO)

Usage:
    from app.services.extraction.iso20022_parser import ISO20022Parser
    
    parser = ISO20022Parser()
    result = parser.parse(xml_content)
    
    if result.success:
        lc_data = result.extracted_fields
        # {'lc_number': 'LC123', 'amount': 100000.00, ...}

Field Mapping:
    ISO20022 XPath → Internal Field Name
    See ISO20022_FIELD_MAPPING for complete mapping.
"""

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, date
import re
import logging

logger = logging.getLogger(__name__)


# ISO20022 Namespaces
NAMESPACES = {
    "trad001": "urn:iso:std:iso:20022:tech:xsd:trad.001.001.02",
    "trad002": "urn:iso:std:iso:20022:tech:xsd:trad.002.001.02",
    "trad003": "urn:iso:std:iso:20022:tech:xsd:trad.003.001.02",
    "tsmt012": "urn:iso:std:iso:20022:tech:xsd:tsmt.012.001.05",
    "head": "urn:iso:std:iso:20022:tech:xsd:head.001.001.01",
}

# Message type detection patterns
MESSAGE_TYPE_PATTERNS = {
    "trad.001": r"trad\.001\.\d{3}\.\d{2}",
    "trad.002": r"trad\.002\.\d{3}\.\d{2}",
    "trad.003": r"trad\.003\.\d{3}\.\d{2}",
    "tsmt.012": r"tsmt\.012\.\d{3}\.\d{2}",
}


@dataclass
class ISO20022ParseResult:
    """Result of ISO20022 parsing."""
    success: bool
    message_type: str = ""
    version: str = ""
    extracted_fields: Dict[str, Any] = field(default_factory=dict)
    raw_xml: str = ""
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    confidence: float = 1.0  # XML parsing is deterministic
    extraction_method: str = "iso20022_xml"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "message_type": self.message_type,
            "version": self.version,
            "extracted_fields": self.extracted_fields,
            "errors": self.errors,
            "warnings": self.warnings,
            "confidence": self.confidence,
            "extraction_method": self.extraction_method,
        }


class ISO20022Parser:
    """
    Parser for ISO20022 Trade Finance XML messages.
    
    Supports Documentary Credit (LC) messages and extracts
    fields into a normalized internal format.
    """
    
    # Field mapping: XPath (relative to document root) → Internal field name
    # These paths work for trad.001 (Documentary Credit Issuance)
    TRAD001_FIELD_MAPPING = {
        # LC Identification
        ".//DocCdtId/Id": "lc_number",
        ".//DocCdtId/Vrsn": "lc_version",
        ".//DocCdtId/IsseDt": "issue_date",
        
        # Form and Type
        ".//DocCdtTp/Cd": "lc_type_code",
        ".//DocCdtTp/Prtry": "lc_type_proprietary",
        ".//DocCdtFrm/Cd": "form_code",  # IRVC (Irrevocable), RVOC (Revocable)
        
        # Amounts
        ".//Amt/InstdAmt": "amount",
        ".//Amt/InstdAmt/@Ccy": "currency",
        ".//Amt/Tlrnc/PlusPct": "tolerance_plus_percent",
        ".//Amt/Tlrnc/MnsPct": "tolerance_minus_percent",
        
        # Dates
        ".//XpryDt/Dt": "expiry_date",
        ".//XpryDt/Plc": "expiry_place",
        ".//LatestShpmntDt": "latest_shipment_date",
        ".//ShpmntPrd/EarlstShpmntDt": "earliest_shipment_date",
        ".//ShpmntPrd/LatstShpmntDt": "latest_shipment_date_alt",
        
        # Parties - Applicant
        ".//Applcnt/Nm": "applicant_name",
        ".//Applcnt/PstlAdr/StrtNm": "applicant_street",
        ".//Applcnt/PstlAdr/TwnNm": "applicant_city",
        ".//Applcnt/PstlAdr/Ctry": "applicant_country",
        ".//Applcnt/Id/OrgId/AnyBIC": "applicant_bic",
        
        # Parties - Beneficiary
        ".//Bnfcry/Nm": "beneficiary_name",
        ".//Bnfcry/PstlAdr/StrtNm": "beneficiary_street",
        ".//Bnfcry/PstlAdr/TwnNm": "beneficiary_city",
        ".//Bnfcry/PstlAdr/Ctry": "beneficiary_country",
        ".//Bnfcry/Id/OrgId/AnyBIC": "beneficiary_bic",
        
        # Banks - Issuing Bank
        ".//IssgBk/FinInstnId/BICFI": "issuing_bank_bic",
        ".//IssgBk/FinInstnId/Nm": "issuing_bank_name",
        ".//IssgBk/FinInstnId/PstlAdr/TwnNm": "issuing_bank_city",
        ".//IssgBk/FinInstnId/PstlAdr/Ctry": "issuing_bank_country",
        
        # Banks - Advising Bank
        ".//AdvsgBk/FinInstnId/BICFI": "advising_bank_bic",
        ".//AdvsgBk/FinInstnId/Nm": "advising_bank_name",
        
        # Banks - Confirming Bank
        ".//ConfgBk/FinInstnId/BICFI": "confirming_bank_bic",
        ".//ConfgBk/FinInstnId/Nm": "confirming_bank_name",
        
        # Banks - Nominated Bank
        ".//NmntdBk/FinInstnId/BICFI": "nominated_bank_bic",
        ".//NmntdBk/FinInstnId/Nm": "nominated_bank_name",
        
        # Availability
        ".//AvlblWth/Cd": "available_with_code",
        ".//AvlblWth/FinInstnId/BICFI": "available_with_bank_bic",
        ".//AvlblBy/Cd": "available_by_code",  # SIGU (Sight), DEFR (Deferred), etc.
        
        # Payment Terms
        ".//PmtTerms/Cd": "payment_terms_code",
        ".//PmtTerms/NbOfDays": "payment_days",
        ".//DfrdPmtDtls/Desc": "deferred_payment_details",
        
        # Shipment Details
        ".//PlcOfTakngInChrg": "place_of_taking_in_charge",
        ".//PortOfLoadng": "port_of_loading",
        ".//PortOfDschrg": "port_of_discharge",
        ".//FnlDstn": "final_destination",
        ".//ShpmntTerms/Inctrm/Cd": "incoterm",
        ".//ShpmntTerms/Inctrm/Lctn": "incoterm_location",
        
        # Partial Shipment / Transhipment
        ".//PrtlShpmnt/Cd": "partial_shipment",  # ALLO (Allowed), NALL (Not Allowed)
        ".//TranShpmnt/Cd": "transhipment",  # ALLO (Allowed), NALL (Not Allowed)
        
        # Goods Description
        ".//GoodsDesc": "goods_description",
        ".//GoodsAndSvcs/Desc": "goods_services_description",
        
        # Documents Required
        ".//DocsReqrd/Desc": "documents_required_text",
        
        # Additional Conditions
        ".//AddtlConds": "additional_conditions",
        
        # Charges
        ".//Chrgs/Cd": "charges_code",  # BENE (Beneficiary), APPL (Applicant), SHAR (Shared)
        
        # Confirmation
        ".//ConfInstrs/Cd": "confirmation_instructions",  # CONF (Confirm), MAYW (May Add), WTHC (Without)
        
        # Reimbursement
        ".//ReimbBk/FinInstnId/BICFI": "reimbursing_bank_bic",
        ".//ReimbBk/FinInstnId/Nm": "reimbursing_bank_name",
        
        # Presentation Period
        ".//PresntnPrd/NbOfDays": "presentation_period_days",
        ".//PresntnPrd/Desc": "presentation_period_desc",
    }
    
    # Amendment-specific fields (trad.002)
    TRAD002_FIELD_MAPPING = {
        ".//AmdmntId/Id": "amendment_number",
        ".//AmdmntSeqNb": "amendment_sequence",
        ".//AmdmntDt": "amendment_date",
        ".//DocCdtId/Id": "lc_number",
        ".//IncrsAmt/InstdAmt": "increase_amount",
        ".//IncrsAmt/InstdAmt/@Ccy": "increase_currency",
        ".//DcrsAmt/InstdAmt": "decrease_amount",
        ".//NewXpryDt/Dt": "new_expiry_date",
        ".//NewLatestShpmntDt": "new_latest_shipment_date",
    }
    
    def __init__(self):
        self.namespaces = {}
    
    def detect_message_type(self, xml_content: str) -> Tuple[str, str]:
        """
        Detect the ISO20022 message type from XML content.
        
        Returns:
            Tuple of (message_type, version) e.g., ("trad.001", "001.02")
        """
        # Look for namespace declaration
        for msg_type, pattern in MESSAGE_TYPE_PATTERNS.items():
            match = re.search(pattern, xml_content)
            if match:
                full_version = match.group(0)
                version = full_version.replace(f"{msg_type}.", "")
                return msg_type, version
        
        return "", ""
    
    def is_iso20022_xml(self, content: str) -> bool:
        """
        Check if content is likely an ISO20022 XML document.
        """
        if not content or not content.strip().startswith("<?xml") and not content.strip().startswith("<"):
            return False
        
        # Check for ISO20022 namespace patterns
        iso20022_indicators = [
            "iso:std:iso:20022",
            "xmlns:trad",
            "xmlns:tsmt",
            "DocCdt",
            "DocumentaryCredit",
            "urn:iso:std:iso:20022:tech:xsd:trad",
        ]
        
        return any(indicator in content for indicator in iso20022_indicators)
    
    def parse(self, xml_content: str) -> ISO20022ParseResult:
        """
        Parse an ISO20022 XML document and extract LC fields.
        
        Args:
            xml_content: Raw XML string
            
        Returns:
            ISO20022ParseResult with extracted fields
        """
        result = ISO20022ParseResult(
            success=False,
            raw_xml=xml_content,
        )
        
        if not xml_content or not xml_content.strip():
            result.errors.append("Empty XML content")
            return result
        
        # Detect message type
        msg_type, version = self.detect_message_type(xml_content)
        result.message_type = msg_type
        result.version = version
        
        if not msg_type:
            result.errors.append("Could not detect ISO20022 message type")
            result.warnings.append("XML does not appear to be a recognized ISO20022 trade finance message")
            return result
        
        logger.info(f"Detected ISO20022 message: {msg_type} version {version}")
        
        try:
            # Parse XML
            root = ET.fromstring(xml_content)
            
            # Register namespaces
            self._register_namespaces(root)
            
            # Select field mapping based on message type
            if msg_type == "trad.001":
                field_mapping = self.TRAD001_FIELD_MAPPING
            elif msg_type == "trad.002":
                field_mapping = {**self.TRAD001_FIELD_MAPPING, **self.TRAD002_FIELD_MAPPING}
            else:
                field_mapping = self.TRAD001_FIELD_MAPPING
                result.warnings.append(f"Using default field mapping for {msg_type}")
            
            # Extract fields
            extracted = {}
            for xpath, field_name in field_mapping.items():
                value = self._extract_field(root, xpath)
                if value is not None:
                    extracted[field_name] = value
            
            # Post-process extracted fields
            extracted = self._post_process_fields(extracted)
            
            # Build composite fields
            extracted = self._build_composite_fields(extracted)
            
            # Extract list fields (documents, goods items)
            extracted["documents_required"] = self._extract_documents_list(root)
            extracted["goods_items"] = self._extract_goods_items(root)
            
            result.extracted_fields = extracted
            result.success = True
            
            logger.info(f"Successfully extracted {len(extracted)} fields from ISO20022 {msg_type}")
            
        except ET.ParseError as e:
            result.errors.append(f"XML parsing error: {str(e)}")
            logger.error(f"ISO20022 XML parse error: {e}")
        except Exception as e:
            result.errors.append(f"Extraction error: {str(e)}")
            logger.error(f"ISO20022 extraction error: {e}", exc_info=True)
        
        return result
    
    def _register_namespaces(self, root: ET.Element):
        """Extract and register namespaces from the root element."""
        # Get default namespace
        if root.tag.startswith("{"):
            ns_end = root.tag.find("}")
            default_ns = root.tag[1:ns_end]
            self.namespaces[""] = default_ns
            self.namespaces["ns"] = default_ns
    
    def _extract_field(self, root: ET.Element, xpath: str) -> Optional[str]:
        """
        Extract a single field value using XPath.
        
        Handles both element text and attribute values.
        """
        try:
            # Handle attribute extraction (e.g., .//Amt/@Ccy)
            if "/@" in xpath:
                element_path, attr_name = xpath.rsplit("/@", 1)
                element = self._find_element(root, element_path)
                if element is not None:
                    return element.get(attr_name)
                return None
            
            # Handle element text extraction
            element = self._find_element(root, xpath)
            if element is not None and element.text:
                return element.text.strip()
            
            return None
            
        except Exception as e:
            logger.debug(f"Could not extract {xpath}: {e}")
            return None
    
    def _find_element(self, root: ET.Element, xpath: str) -> Optional[ET.Element]:
        """
        Find an element, trying both with and without namespace.
        """
        # Try direct XPath first
        element = root.find(xpath)
        if element is not None:
            return element
        
        # Try with registered namespace
        if self.namespaces.get("ns"):
            ns_xpath = self._add_namespace_to_xpath(xpath, self.namespaces["ns"])
            element = root.find(ns_xpath)
            if element is not None:
                return element
        
        # Try iterating through all elements (fallback)
        tag_name = xpath.split("/")[-1].lstrip(".")
        for elem in root.iter():
            local_name = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
            if local_name == tag_name:
                return elem
        
        return None
    
    def _add_namespace_to_xpath(self, xpath: str, namespace: str) -> str:
        """Add namespace prefix to XPath elements."""
        parts = xpath.split("/")
        ns_parts = []
        for part in parts:
            if part and not part.startswith(".") and not part.startswith("@"):
                ns_parts.append(f"{{{namespace}}}{part}")
            else:
                ns_parts.append(part)
        return "/".join(ns_parts)
    
    def _post_process_fields(self, fields: Dict[str, Any]) -> Dict[str, Any]:
        """
        Post-process extracted fields for normalization.
        """
        # Convert amount to float
        if "amount" in fields:
            try:
                fields["amount"] = float(fields["amount"].replace(",", ""))
            except (ValueError, AttributeError):
                pass
        
        # Parse dates
        date_fields = [
            "issue_date", "expiry_date", "latest_shipment_date",
            "earliest_shipment_date", "amendment_date",
            "new_expiry_date", "new_latest_shipment_date"
        ]
        for date_field in date_fields:
            if date_field in fields:
                fields[date_field] = self._parse_date(fields[date_field])
        
        # Convert tolerance percentages to float
        for tol_field in ["tolerance_plus_percent", "tolerance_minus_percent"]:
            if tol_field in fields:
                try:
                    fields[tol_field] = float(fields[tol_field])
                except (ValueError, AttributeError):
                    pass
        
        # Map codes to human-readable values
        code_mappings = {
            "form_code": {"IRVC": "Irrevocable", "RVOC": "Revocable"},
            "available_by_code": {
                "SIGU": "Sight",
                "DEFR": "Deferred Payment",
                "ACCP": "Acceptance",
                "NEGO": "Negotiation",
                "MIXD": "Mixed Payment",
            },
            "partial_shipment": {"ALLO": "Allowed", "NALL": "Not Allowed"},
            "transhipment": {"ALLO": "Allowed", "NALL": "Not Allowed"},
            "charges_code": {"BENE": "Beneficiary", "APPL": "Applicant", "SHAR": "Shared"},
            "confirmation_instructions": {
                "CONF": "Confirm",
                "MAYW": "May Add",
                "WTHC": "Without",
            },
        }
        
        for field_name, mapping in code_mappings.items():
            if field_name in fields and fields[field_name] in mapping:
                code = fields[field_name]
                fields[f"{field_name}_display"] = mapping[code]
        
        return fields
    
    def _parse_date(self, date_str: str) -> str:
        """Parse various date formats to YYYY-MM-DD."""
        if not date_str:
            return ""
        
        # Already in correct format
        if re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
            return date_str
        
        # Try common formats
        formats = [
            "%Y%m%d",
            "%d%m%Y",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
        
        return date_str
    
    def _build_composite_fields(self, fields: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build composite fields from extracted data.
        """
        # Build full applicant address
        applicant_parts = [
            fields.get("applicant_name", ""),
            fields.get("applicant_street", ""),
            fields.get("applicant_city", ""),
            fields.get("applicant_country", ""),
        ]
        applicant_full = ", ".join(p for p in applicant_parts if p)
        if applicant_full:
            fields["applicant"] = applicant_full
        
        # Build full beneficiary address
        beneficiary_parts = [
            fields.get("beneficiary_name", ""),
            fields.get("beneficiary_street", ""),
            fields.get("beneficiary_city", ""),
            fields.get("beneficiary_country", ""),
        ]
        beneficiary_full = ", ".join(p for p in beneficiary_parts if p)
        if beneficiary_full:
            fields["beneficiary"] = beneficiary_full
        
        # Build issuing bank display name
        if fields.get("issuing_bank_name"):
            fields["issuing_bank"] = fields["issuing_bank_name"]
            if fields.get("issuing_bank_bic"):
                fields["issuing_bank"] += f" ({fields['issuing_bank_bic']})"
        elif fields.get("issuing_bank_bic"):
            fields["issuing_bank"] = fields["issuing_bank_bic"]
        
        # Build advising bank display name
        if fields.get("advising_bank_name"):
            fields["advising_bank"] = fields["advising_bank_name"]
            if fields.get("advising_bank_bic"):
                fields["advising_bank"] += f" ({fields['advising_bank_bic']})"
        elif fields.get("advising_bank_bic"):
            fields["advising_bank"] = fields["advising_bank_bic"]
        
        # Determine LC type
        lc_type = "unknown"
        if fields.get("lc_type_code"):
            lc_type = fields["lc_type_code"]
        elif fields.get("form_code_display"):
            lc_type = fields["form_code_display"]
        fields["lc_type"] = lc_type
        
        # Build amount display
        if fields.get("amount") and fields.get("currency"):
            fields["amount_display"] = f"{fields['currency']} {fields['amount']:,.2f}"
        
        # Build payment terms display
        payment_terms = fields.get("available_by_code_display", "")
        if fields.get("payment_days"):
            payment_terms += f" {fields['payment_days']} days"
        if payment_terms:
            fields["payment_terms"] = payment_terms
        
        return fields
    
    def _extract_documents_list(self, root: ET.Element) -> List[Dict[str, str]]:
        """
        Extract the list of required documents.
        """
        documents = []
        
        # Try finding DocsReqrd elements
        for doc_elem in root.iter():
            local_name = doc_elem.tag.split("}")[-1] if "}" in doc_elem.tag else doc_elem.tag
            
            if local_name in ("DocsReqrd", "DocReqrd", "ReqdDoc"):
                doc_text = self._get_element_text(doc_elem)
                if doc_text:
                    documents.append({
                        "description": doc_text,
                        "type": self._infer_document_type(doc_text),
                    })
        
        return documents
    
    def _extract_goods_items(self, root: ET.Element) -> List[Dict[str, Any]]:
        """
        Extract goods/services items.
        """
        items = []
        
        for elem in root.iter():
            local_name = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
            
            if local_name in ("GoodsAndSvcs", "GoodsItm", "LineItm"):
                item = {}
                
                for child in elem:
                    child_name = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                    if child.text:
                        item[child_name.lower()] = child.text.strip()
                
                if item:
                    items.append(item)
        
        return items
    
    def _get_element_text(self, element: ET.Element) -> str:
        """Get all text content from an element, including nested text."""
        texts = []
        if element.text:
            texts.append(element.text.strip())
        for child in element:
            child_text = self._get_element_text(child)
            if child_text:
                texts.append(child_text)
            if child.tail:
                texts.append(child.tail.strip())
        return " ".join(texts)
    
    def _infer_document_type(self, description: str) -> str:
        """
        Infer document type from description text.
        """
        desc_lower = description.lower()
        
        type_patterns = {
            "bill_of_lading": ["bill of lading", "b/l", "bl ", "ocean b/l"],
            "commercial_invoice": ["commercial invoice", "invoice"],
            "packing_list": ["packing list", "packing note"],
            "certificate_of_origin": ["certificate of origin", "c/o", "origin cert"],
            "insurance": ["insurance", "policy", "certificate of insurance"],
            "inspection_certificate": ["inspection", "sgs", "intertek", "survey"],
            "beneficiary_certificate": ["beneficiary cert", "beneficiary's cert"],
            "weight_certificate": ["weight cert", "weight list"],
            "analysis_certificate": ["analysis cert", "test cert"],
        }
        
        for doc_type, patterns in type_patterns.items():
            if any(p in desc_lower for p in patterns):
                return doc_type
        
        return "other"


# Singleton instance
_parser: Optional[ISO20022Parser] = None


def get_iso20022_parser() -> ISO20022Parser:
    """Get or create the ISO20022 parser singleton."""
    global _parser
    if _parser is None:
        _parser = ISO20022Parser()
    return _parser


def parse_iso20022_lc(xml_content: str) -> ISO20022ParseResult:
    """
    Convenience function to parse an ISO20022 LC document.
    
    Args:
        xml_content: Raw XML string
        
    Returns:
        ISO20022ParseResult with extracted fields
    """
    parser = get_iso20022_parser()
    return parser.parse(xml_content)


def is_iso20022_document(content: str) -> bool:
    """
    Check if content appears to be an ISO20022 XML document.
    
    Args:
        content: File content (string or bytes decoded)
        
    Returns:
        True if content appears to be ISO20022 XML
    """
    parser = get_iso20022_parser()
    return parser.is_iso20022_xml(content)

