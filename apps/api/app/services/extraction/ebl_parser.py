"""
Electronic Bill of Lading (eBL) Parser

Parses electronic Bills of Lading from major eBL platforms and standards:

1. DCSA eBL Standard (Digital Container Shipping Association)
   - Used by: Maersk, MSC, Hapag-Lloyd, CMA CGM, ONE, Evergreen, Yang Ming, HMM
   - Format: JSON-LD with schema.org vocabulary
   - Standard: DCSA eBL v3.0

2. BOLERO eBL
   - Used by: HSBC, Standard Chartered, major commodity traders
   - Format: XML with BOLERO DTD
   - Governed by: Bolero International Ltd

3. essDOCS eBL (CargoDocs)
   - Used by: Shell, BP, Cargill, Trafigura
   - Format: XML with essDOCS schema
   - Platform: CargoDocs

4. TradeLens eBL (IBM/Maersk - now deprecated but files may exist)
   - Format: JSON
   - Note: Platform shutdown in 2022, but historical files may need parsing

5. WaveBL
   - Format: JSON with blockchain reference
   - Used by: ZIM, smaller carriers

Usage:
    from app.services.extraction.ebl_parser import parse_ebl, detect_ebl_format
    
    format_type = detect_ebl_format(content)
    result = parse_ebl(content)
"""

import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import re
import logging

logger = logging.getLogger(__name__)


@dataclass
class EBLParseResult:
    """Result of eBL parsing."""
    success: bool
    format_type: str  # "dcsa", "bolero", "essdocs", "wavelbl", "unknown"
    platform: str  # "DCSA", "BOLERO", "essDOCS", "WaveBL", etc.
    extracted_fields: Dict[str, Any] = field(default_factory=dict)
    raw_content: str = ""
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    confidence: float = 1.0
    blockchain_ref: Optional[str] = None
    digital_signature_valid: Optional[bool] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "format_type": self.format_type,
            "platform": self.platform,
            "extracted_fields": self.extracted_fields,
            "errors": self.errors,
            "warnings": self.warnings,
            "confidence": self.confidence,
            "blockchain_ref": self.blockchain_ref,
            "digital_signature_valid": self.digital_signature_valid,
            "_source_format": f"eBL ({self.platform})",
            "_extraction_method": "ebl_parser",
        }


# ============================================================================
# FORMAT DETECTION
# ============================================================================

def detect_ebl_format(content: str) -> Tuple[str, str]:
    """
    Detect the eBL format and platform.
    
    Returns:
        Tuple of (format_type, platform_name)
    """
    if not content or not content.strip():
        return "unknown", "Unknown"
    
    content_stripped = content.strip()
    
    # Check for JSON formats (DCSA, WaveBL, TradeLens)
    if content_stripped.startswith("{") or content_stripped.startswith("["):
        try:
            data = json.loads(content)
            
            # DCSA eBL detection
            if isinstance(data, dict):
                # DCSA v3.0 uses @context with schema.org
                if "@context" in data or "transportDocumentReference" in data:
                    return "dcsa", "DCSA"
                
                # DCSA document indicators
                dcsa_keys = [
                    "shippingInstructions", "transportDocument", 
                    "billOfLadingNumber", "carrierBookingReference",
                    "issuingParty", "receivingParty"
                ]
                if any(k in data for k in dcsa_keys):
                    return "dcsa", "DCSA"
                
                # WaveBL detection
                if "blockchainTxId" in data or "waveBLRef" in data:
                    return "wavebl", "WaveBL"
                
                # TradeLens detection
                if "tradeLensId" in data or "ibmBlockchain" in data:
                    return "tradelens", "TradeLens"
                
                # Generic JSON eBL
                if "billOfLading" in data or "b/l" in str(data).lower():
                    return "json_generic", "Generic JSON"
                    
        except json.JSONDecodeError:
            pass
    
    # Check for XML formats (BOLERO, essDOCS)
    if content_stripped.startswith("<?xml") or content_stripped.startswith("<"):
        # BOLERO detection
        bolero_indicators = [
            "bolero", "BOLERO", "BoleroInternational",
            "BOLMessage", "BillOfLading xmlns",
            "bolero.net", "www.bolero.net"
        ]
        if any(ind in content for ind in bolero_indicators):
            return "bolero", "BOLERO"
        
        # essDOCS detection
        essdocs_indicators = [
            "essdocs", "CargoDocs", "essDOCS",
            "cargodocs.com", "EssDocs",
            "ElectronicBL", "eBLDocument"
        ]
        if any(ind in content for ind in essdocs_indicators):
            return "essdocs", "essDOCS"
        
        # CargoX detection
        if "cargox" in content.lower() or "CargoX" in content:
            return "cargox", "CargoX"
        
        # Generic XML B/L
        if "BillOfLading" in content or "TransportDocument" in content:
            return "xml_generic", "Generic XML"
    
    return "unknown", "Unknown"


def is_ebl_document(content: str) -> bool:
    """
    Check if content appears to be an electronic Bill of Lading.
    """
    format_type, _ = detect_ebl_format(content)
    return format_type != "unknown"


# ============================================================================
# DCSA eBL PARSER (Digital Container Shipping Association)
# ============================================================================

class DCSAParser:
    """
    Parser for DCSA eBL standard (v3.0).
    
    DCSA is the primary standard for container shipping eBLs.
    Adopted by: Maersk, MSC, Hapag-Lloyd, CMA CGM, ONE, Evergreen, etc.
    """
    
    # Field mapping: DCSA path → Internal field name
    FIELD_MAPPING = {
        # Document identification
        "transportDocumentReference": "bl_number",
        "billOfLadingNumber": "bl_number",
        "shippingInstructionsReference": "booking_reference",
        "carrierBookingReference": "booking_reference",
        
        # Carrier
        "carrierCode": "carrier_code",
        "carrierCodeListProvider": "carrier_code_type",
        "issuingParty.partyName": "carrier_name",
        "issuingParty.identifyingCodes": "carrier_ids",
        
        # Shipper
        "shipper.partyName": "shipper_name",
        "shipper.address.street": "shipper_street",
        "shipper.address.city": "shipper_city",
        "shipper.address.country": "shipper_country",
        "shipper.partyContactDetails": "shipper_contact",
        
        # Consignee
        "consignee.partyName": "consignee_name",
        "consignee.address.street": "consignee_street",
        "consignee.address.city": "consignee_city",
        "consignee.address.country": "consignee_country",
        "consignee.isToOrder": "to_order",
        
        # Notify Party
        "notifyParty.partyName": "notify_party_name",
        "notifyParty.address": "notify_party_address",
        
        # Vessel & Voyage
        "transportPlan.vesselName": "vessel_name",
        "transportPlan.vesselIMONumber": "vessel_imo",
        "transportPlan.voyageNumber": "voyage_number",
        "preCarriageBy": "pre_carriage_by",
        "onCarriageBy": "on_carriage_by",
        
        # Ports & Places
        "placeOfReceipt.locationName": "place_of_receipt",
        "placeOfReceipt.UNLocationCode": "place_of_receipt_code",
        "portOfLoading.locationName": "port_of_loading",
        "portOfLoading.UNLocationCode": "port_of_loading_code",
        "portOfDischarge.locationName": "port_of_discharge",
        "portOfDischarge.UNLocationCode": "port_of_discharge_code",
        "placeOfDelivery.locationName": "place_of_delivery",
        "placeOfDelivery.UNLocationCode": "place_of_delivery_code",
        
        # Dates
        "onBoardDate": "shipped_on_board_date",
        "shippedOnBoardDate": "shipped_on_board_date",
        "issueDate": "issue_date",
        "receivedForShipmentDate": "received_for_shipment_date",
        
        # Cargo
        "descriptionOfGoods": "goods_description",
        "cargoItems": "cargo_items",
        "numberOfPackages": "number_of_packages",
        "packageCode": "package_type_code",
        "weight.value": "gross_weight",
        "weight.unit": "weight_unit",
        "volume.value": "volume",
        "volume.unit": "volume_unit",
        
        # Container
        "utilizedTransportEquipments": "containers",
        "containerNumber": "container_number",
        "sealNumber": "seal_number",
        "containerSize": "container_size",
        "containerType": "container_type",
        
        # Freight
        "freightPaymentTermCode": "freight_terms",
        "isFreightPrepaid": "freight_prepaid",
        "declaredValue": "declared_value",
        "declaredValueCurrency": "declared_value_currency",
        
        # B/L clauses
        "termsAndConditions": "terms_and_conditions",
        "clauses": "bl_clauses",
        "shippersOwnsContainer": "shipper_owned_container",
        
        # Number of originals
        "numberOfOriginals": "number_of_originals",
        "numberOfCopies": "number_of_copies",
        
        # Digital signature
        "digitalSignature": "digital_signature",
        "signatureTimestamp": "signature_timestamp",
    }
    
    def parse(self, content: str) -> EBLParseResult:
        """Parse DCSA eBL JSON."""
        result = EBLParseResult(
            success=False,
            format_type="dcsa",
            platform="DCSA",
            raw_content=content,
        )
        
        try:
            data = json.loads(content)
            extracted = {}
            
            # Extract fields using dot notation mapping
            for dcsa_path, internal_name in self.FIELD_MAPPING.items():
                value = self._get_nested_value(data, dcsa_path)
                if value is not None:
                    extracted[internal_name] = value
            
            # Process containers
            containers = data.get("utilizedTransportEquipments", [])
            if containers:
                extracted["containers"] = self._parse_containers(containers)
                extracted["container_count"] = len(containers)
            
            # Process cargo items
            cargo_items = data.get("cargoItems", [])
            if cargo_items:
                extracted["cargo_items"] = self._parse_cargo_items(cargo_items)
            
            # Calculate totals
            extracted = self._calculate_totals(extracted, data)
            
            # Build composite fields
            extracted = self._build_composite_fields(extracted)
            
            # Check for blockchain/digital signature
            if "digitalSignature" in data:
                result.digital_signature_valid = True  # Would need actual verification
            if "blockchainReference" in data:
                result.blockchain_ref = data.get("blockchainReference")
            
            result.extracted_fields = extracted
            result.success = bool(extracted.get("bl_number"))
            
            logger.info(f"DCSA eBL parsed: {len(extracted)} fields extracted")
            
        except json.JSONDecodeError as e:
            result.errors.append(f"JSON parse error: {str(e)}")
        except Exception as e:
            result.errors.append(f"DCSA parse error: {str(e)}")
            logger.error(f"DCSA parse error: {e}", exc_info=True)
        
        return result
    
    def _get_nested_value(self, data: Dict, path: str) -> Any:
        """Get value from nested dictionary using dot notation."""
        parts = path.split(".")
        current = data
        
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list) and current:
                current = current[0].get(part) if isinstance(current[0], dict) else None
            else:
                return None
            
            if current is None:
                return None
        
        return current
    
    def _parse_containers(self, containers: List[Dict]) -> List[Dict]:
        """Parse container/equipment details."""
        parsed = []
        for container in containers:
            parsed.append({
                "container_number": container.get("equipmentReference") or container.get("containerNumber"),
                "seal_numbers": container.get("seals", []),
                "size_type": container.get("ISOEquipmentCode"),
                "is_shipper_owned": container.get("isShipperOwned", False),
                "weight": container.get("weight", {}).get("value"),
                "weight_unit": container.get("weight", {}).get("unit"),
                "tare_weight": container.get("tareWeight", {}).get("value"),
            })
        return parsed
    
    def _parse_cargo_items(self, items: List[Dict]) -> List[Dict]:
        """Parse cargo item details."""
        parsed = []
        for item in items:
            parsed.append({
                "description": item.get("descriptionOfGoods"),
                "hs_code": item.get("HSCode") or item.get("hsCode"),
                "packages": item.get("numberOfPackages"),
                "package_type": item.get("packageCode"),
                "gross_weight": item.get("weight", {}).get("value"),
                "volume": item.get("volume", {}).get("value"),
            })
        return parsed
    
    def _calculate_totals(self, extracted: Dict, data: Dict) -> Dict:
        """Calculate aggregate values."""
        # Total packages
        if "cargo_items" in extracted:
            total_packages = sum(
                item.get("packages", 0) or 0 
                for item in extracted["cargo_items"]
            )
            if total_packages:
                extracted["total_packages"] = total_packages
        
        # Total weight
        if "containers" in extracted:
            total_weight = sum(
                c.get("weight", 0) or 0 
                for c in extracted["containers"]
            )
            if total_weight:
                extracted["total_gross_weight"] = total_weight
        
        return extracted
    
    def _build_composite_fields(self, extracted: Dict) -> Dict:
        """Build composite display fields."""
        # Full shipper
        shipper_parts = [
            extracted.get("shipper_name", ""),
            extracted.get("shipper_street", ""),
            extracted.get("shipper_city", ""),
            extracted.get("shipper_country", ""),
        ]
        if any(shipper_parts):
            extracted["shipper"] = ", ".join(p for p in shipper_parts if p)
        
        # Full consignee
        consignee_parts = [
            extracted.get("consignee_name", ""),
            extracted.get("consignee_street", ""),
            extracted.get("consignee_city", ""),
            extracted.get("consignee_country", ""),
        ]
        if any(consignee_parts):
            extracted["consignee"] = ", ".join(p for p in consignee_parts if p)
        
        # B/L type
        if extracted.get("to_order"):
            extracted["bl_type"] = "To Order"
        else:
            extracted["bl_type"] = "Straight"
        
        # Freight terms display
        freight_code = extracted.get("freight_terms", "")
        freight_mapping = {
            "PRE": "Freight Prepaid",
            "COL": "Freight Collect",
            "PPD": "Prepaid",
            "CLT": "Collect",
        }
        if freight_code in freight_mapping:
            extracted["freight_terms_display"] = freight_mapping[freight_code]
        
        return extracted


# ============================================================================
# BOLERO eBL PARSER
# ============================================================================

class BoleroParser:
    """
    Parser for BOLERO eBL format.
    
    BOLERO (Bill of Lading Electronic Registry Organisation) is one of the
    oldest eBL platforms, widely used in commodity trading and banking.
    """
    
    # XML Element → Internal field mapping
    FIELD_MAPPING = {
        "BLNumber": "bl_number",
        "BookingReference": "booking_reference",
        "VesselName": "vessel_name",
        "VoyageNumber": "voyage_number",
        "PortOfLoading": "port_of_loading",
        "PortOfDischarge": "port_of_discharge",
        "PlaceOfReceipt": "place_of_receipt",
        "PlaceOfDelivery": "place_of_delivery",
        "ShipperName": "shipper_name",
        "ShipperAddress": "shipper_address",
        "ConsigneeName": "consignee_name",
        "ConsigneeAddress": "consignee_address",
        "NotifyPartyName": "notify_party_name",
        "NotifyPartyAddress": "notify_party_address",
        "GoodsDescription": "goods_description",
        "GrossWeight": "gross_weight",
        "NetWeight": "net_weight",
        "Measurement": "volume",
        "NumberOfPackages": "number_of_packages",
        "ContainerNumber": "container_number",
        "SealNumber": "seal_number",
        "FreightTerms": "freight_terms",
        "OnBoardDate": "shipped_on_board_date",
        "IssueDate": "issue_date",
        "IssuePlace": "issue_place",
        "NumberOfOriginals": "number_of_originals",
        "CarrierName": "carrier_name",
    }
    
    def parse(self, content: str) -> EBLParseResult:
        """Parse BOLERO eBL XML."""
        result = EBLParseResult(
            success=False,
            format_type="bolero",
            platform="BOLERO",
            raw_content=content,
        )
        
        try:
            root = ET.fromstring(content)
            extracted = {}
            
            # Extract fields from XML
            for elem_name, field_name in self.FIELD_MAPPING.items():
                elem = self._find_element(root, elem_name)
                if elem is not None and elem.text:
                    extracted[field_name] = elem.text.strip()
            
            # Extract containers
            containers = self._extract_containers(root)
            if containers:
                extracted["containers"] = containers
                extracted["container_count"] = len(containers)
            
            # Extract cargo items
            cargo_items = self._extract_cargo_items(root)
            if cargo_items:
                extracted["cargo_items"] = cargo_items
            
            # Build composite fields
            extracted = self._build_composite_fields(extracted)
            
            # Check for BOLERO signature
            sig_elem = self._find_element(root, "DigitalSignature")
            if sig_elem is not None:
                result.digital_signature_valid = True
            
            result.extracted_fields = extracted
            result.success = bool(extracted.get("bl_number"))
            
            logger.info(f"BOLERO eBL parsed: {len(extracted)} fields extracted")
            
        except ET.ParseError as e:
            result.errors.append(f"XML parse error: {str(e)}")
        except Exception as e:
            result.errors.append(f"BOLERO parse error: {str(e)}")
            logger.error(f"BOLERO parse error: {e}", exc_info=True)
        
        return result
    
    def _find_element(self, root: ET.Element, name: str) -> Optional[ET.Element]:
        """Find element by local name, ignoring namespace."""
        for elem in root.iter():
            local_name = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
            if local_name == name:
                return elem
        return None
    
    def _extract_containers(self, root: ET.Element) -> List[Dict]:
        """Extract container information."""
        containers = []
        for elem in root.iter():
            local_name = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
            if local_name in ("Container", "Equipment", "ContainerDetails"):
                container = {}
                for child in elem:
                    child_name = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                    if child.text:
                        container[child_name.lower()] = child.text.strip()
                if container:
                    containers.append(container)
        return containers
    
    def _extract_cargo_items(self, root: ET.Element) -> List[Dict]:
        """Extract cargo/goods items."""
        items = []
        for elem in root.iter():
            local_name = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
            if local_name in ("CargoItem", "GoodsItem", "Cargo"):
                item = {}
                for child in elem:
                    child_name = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                    if child.text:
                        item[child_name.lower()] = child.text.strip()
                if item:
                    items.append(item)
        return items
    
    def _build_composite_fields(self, extracted: Dict) -> Dict:
        """Build composite fields for display."""
        # Full shipper
        if extracted.get("shipper_name"):
            parts = [extracted.get("shipper_name"), extracted.get("shipper_address")]
            extracted["shipper"] = ", ".join(p for p in parts if p)
        
        # Full consignee
        if extracted.get("consignee_name"):
            parts = [extracted.get("consignee_name"), extracted.get("consignee_address")]
            extracted["consignee"] = ", ".join(p for p in parts if p)
        
        return extracted


# ============================================================================
# essDOCS eBL PARSER (CargoDocs)
# ============================================================================

class EssDocsParser:
    """
    Parser for essDOCS (CargoDocs) eBL format.
    
    essDOCS is widely used in energy, oil & gas, and bulk commodity trading.
    """
    
    FIELD_MAPPING = {
        "BillOfLadingNumber": "bl_number",
        "BookingNumber": "booking_reference",
        "VesselName": "vessel_name",
        "VoyageNo": "voyage_number",
        "LoadPort": "port_of_loading",
        "DischargePort": "port_of_discharge",
        "Shipper": "shipper_name",
        "ShipperAddress": "shipper_address",
        "Consignee": "consignee_name",
        "ConsigneeAddress": "consignee_address",
        "NotifyParty": "notify_party_name",
        "CargoDescription": "goods_description",
        "GrossWeight": "gross_weight",
        "NetWeight": "net_weight",
        "Quantity": "quantity",
        "ContainerNo": "container_number",
        "SealNo": "seal_number",
        "FreightPayableAt": "freight_payable_at",
        "DateOfShipment": "shipped_on_board_date",
        "DateOfIssue": "issue_date",
        "PlaceOfIssue": "issue_place",
        "OriginalBLCount": "number_of_originals",
        "Carrier": "carrier_name",
    }
    
    def parse(self, content: str) -> EBLParseResult:
        """Parse essDOCS eBL XML."""
        result = EBLParseResult(
            success=False,
            format_type="essdocs",
            platform="essDOCS",
            raw_content=content,
        )
        
        try:
            root = ET.fromstring(content)
            extracted = {}
            
            # Extract fields
            for elem_name, field_name in self.FIELD_MAPPING.items():
                elem = self._find_element(root, elem_name)
                if elem is not None and elem.text:
                    extracted[field_name] = elem.text.strip()
            
            # Extract containers
            containers = self._extract_containers(root)
            if containers:
                extracted["containers"] = containers
            
            # essDOCS specific: extract CargoDocs reference
            cargodocs_ref = self._find_element(root, "CargoDocsReference")
            if cargodocs_ref is not None and cargodocs_ref.text:
                extracted["cargodocs_reference"] = cargodocs_ref.text.strip()
            
            result.extracted_fields = extracted
            result.success = bool(extracted.get("bl_number"))
            
            logger.info(f"essDOCS eBL parsed: {len(extracted)} fields extracted")
            
        except ET.ParseError as e:
            result.errors.append(f"XML parse error: {str(e)}")
        except Exception as e:
            result.errors.append(f"essDOCS parse error: {str(e)}")
        
        return result
    
    def _find_element(self, root: ET.Element, name: str) -> Optional[ET.Element]:
        """Find element by local name."""
        for elem in root.iter():
            local_name = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
            if local_name == name:
                return elem
        return None
    
    def _extract_containers(self, root: ET.Element) -> List[Dict]:
        """Extract container information."""
        containers = []
        for elem in root.iter():
            local_name = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
            if "Container" in local_name:
                container = {}
                for child in elem:
                    child_name = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                    if child.text:
                        container[child_name.lower()] = child.text.strip()
                if container:
                    containers.append(container)
        return containers


# ============================================================================
# WaveBL Parser (Blockchain-based)
# ============================================================================

class WaveBLParser:
    """
    Parser for WaveBL (Wave) eBL format.
    
    WaveBL uses blockchain technology for document authenticity.
    Used by ZIM and other carriers.
    """
    
    def parse(self, content: str) -> EBLParseResult:
        """Parse WaveBL JSON."""
        result = EBLParseResult(
            success=False,
            format_type="wavebl",
            platform="WaveBL",
            raw_content=content,
        )
        
        try:
            data = json.loads(content)
            extracted = {}
            
            # WaveBL field mapping
            field_mapping = {
                "blNumber": "bl_number",
                "bookingReference": "booking_reference",
                "vesselName": "vessel_name",
                "voyageNumber": "voyage_number",
                "portOfLoading": "port_of_loading",
                "portOfDischarge": "port_of_discharge",
                "shipper": "shipper",
                "consignee": "consignee",
                "notifyParty": "notify_party",
                "goodsDescription": "goods_description",
                "grossWeight": "gross_weight",
                "containerNumbers": "containers",
                "dateOfShipment": "shipped_on_board_date",
                "issueDate": "issue_date",
                "carrier": "carrier_name",
            }
            
            for wave_key, internal_key in field_mapping.items():
                if wave_key in data:
                    extracted[internal_key] = data[wave_key]
            
            # Extract blockchain reference
            if "blockchainTxId" in data:
                result.blockchain_ref = data["blockchainTxId"]
                extracted["blockchain_tx_id"] = data["blockchainTxId"]
            
            if "waveBLRef" in data:
                extracted["wave_reference"] = data["waveBLRef"]
            
            result.extracted_fields = extracted
            result.success = bool(extracted.get("bl_number"))
            
        except json.JSONDecodeError as e:
            result.errors.append(f"JSON parse error: {str(e)}")
        except Exception as e:
            result.errors.append(f"WaveBL parse error: {str(e)}")
        
        return result


# ============================================================================
# MAIN PARSER INTERFACE
# ============================================================================

# Parser registry
PARSERS = {
    "dcsa": DCSAParser(),
    "bolero": BoleroParser(),
    "essdocs": EssDocsParser(),
    "wavebl": WaveBLParser(),
}


def parse_ebl(content: str, force_format: Optional[str] = None) -> EBLParseResult:
    """
    Parse an electronic Bill of Lading.
    
    Automatically detects the format and uses the appropriate parser.
    
    Args:
        content: Raw eBL content (JSON or XML)
        force_format: Force a specific parser ("dcsa", "bolero", "essdocs", "wavebl")
        
    Returns:
        EBLParseResult with extracted B/L fields
    """
    if force_format:
        format_type = force_format
        platform = force_format.upper()
    else:
        format_type, platform = detect_ebl_format(content)
    
    logger.info(f"Parsing eBL: format={format_type}, platform={platform}")
    
    if format_type in PARSERS:
        return PARSERS[format_type].parse(content)
    
    # Return empty result for unknown formats
    return EBLParseResult(
        success=False,
        format_type=format_type,
        platform=platform,
        raw_content=content,
        errors=[f"No parser available for format: {format_type}"],
    )


def get_supported_ebl_formats() -> List[Dict[str, str]]:
    """Get list of supported eBL formats."""
    return [
        {
            "format": "dcsa",
            "name": "DCSA eBL",
            "description": "Digital Container Shipping Association standard",
            "carriers": "Maersk, MSC, Hapag-Lloyd, CMA CGM, ONE, Evergreen, Yang Ming, HMM",
        },
        {
            "format": "bolero",
            "name": "BOLERO eBL",
            "description": "Bill of Lading Electronic Registry Organisation",
            "carriers": "Various (bank-centric platform)",
        },
        {
            "format": "essdocs",
            "name": "essDOCS (CargoDocs)",
            "description": "CargoDocs electronic documentation platform",
            "carriers": "Shell, BP, Cargill, Trafigura",
        },
        {
            "format": "wavebl",
            "name": "WaveBL",
            "description": "Blockchain-based eBL platform",
            "carriers": "ZIM, various",
        },
    ]

