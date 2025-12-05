"""
Bank Format Registry

Manages bank-specific document format requirements.
Each bank may have different requirements for:
- Document layout and margins
- Required fields
- Specific wording
- Certification requirements
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class BankDocumentRequirement(str, Enum):
    """Types of bank document requirements"""
    FIELD_REQUIRED = "field_required"      # Field must be present
    FIELD_FORMAT = "field_format"          # Field must match format
    WORDING_EXACT = "wording_exact"        # Exact wording required
    CERTIFICATION = "certification"        # Special certification needed
    LAYOUT = "layout"                      # Layout specification


@dataclass
class BankFieldRequirement:
    """Requirement for a specific field"""
    field_name: str
    is_required: bool = True
    format_regex: Optional[str] = None
    exact_wording: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class BankDocumentFormat:
    """Bank-specific format for a document type"""
    document_type: str
    bank_code: str
    fields: List[BankFieldRequirement] = field(default_factory=list)
    header_requirements: Optional[str] = None
    footer_requirements: Optional[str] = None
    certification_text: Optional[str] = None
    special_instructions: Optional[str] = None


@dataclass
class BankProfile:
    """Complete bank profile with all format requirements"""
    code: str
    name: str
    country: str
    swift_code: Optional[str] = None
    document_formats: Dict[str, BankDocumentFormat] = field(default_factory=dict)
    general_requirements: List[str] = field(default_factory=list)
    contact_info: Optional[Dict[str, str]] = None


# ============== Bank Format Definitions ==============

BANK_PROFILES: Dict[str, BankProfile] = {
    # Standard Chartered Bank
    "SCB": BankProfile(
        code="SCB",
        name="Standard Chartered Bank",
        country="International",
        swift_code="SCBLSGSG",
        general_requirements=[
            "All documents must be original or certified true copies",
            "Beneficiary name must match LC exactly (no abbreviations)",
            "Port names must include country codes",
            "Invoice number must be referenced on all documents",
        ],
        document_formats={
            "commercial_invoice": BankDocumentFormat(
                document_type="commercial_invoice",
                bank_code="SCB",
                fields=[
                    BankFieldRequirement(
                        "invoice_number",
                        is_required=True,
                        format_regex=r"^[A-Z]{2,3}-\d{4,}$",
                        notes="Must follow format: XX-NNNN (e.g., INV-2024001)"
                    ),
                    BankFieldRequirement(
                        "lc_number",
                        is_required=True,
                        notes="LC reference must appear in header"
                    ),
                    BankFieldRequirement(
                        "goods_description",
                        is_required=True,
                        notes="Must match LC description exactly"
                    ),
                ],
                certification_text="WE HEREBY CERTIFY THAT THIS INVOICE IS TRUE AND CORRECT",
                header_requirements="LC number must appear within first 3 lines",
            ),
            "packing_list": BankDocumentFormat(
                document_type="packing_list",
                bank_code="SCB",
                fields=[
                    BankFieldRequirement(
                        "shipping_marks",
                        is_required=True,
                        notes="Must match marks on actual cargo"
                    ),
                    BankFieldRequirement(
                        "net_weight",
                        is_required=True,
                        format_regex=r"^\d+\.?\d*\s*(KG|MT)$",
                    ),
                ],
            ),
        }
    ),
    
    # HSBC Bank
    "HSBC": BankProfile(
        code="HSBC",
        name="HSBC",
        country="International",
        swift_code="HSBCHKHH",
        general_requirements=[
            "Documents must be in English or with certified English translation",
            "All amounts must be in figures and words",
            "Draft tenor must match LC terms exactly",
            "Shipping date must be clearly visible",
        ],
        document_formats={
            "commercial_invoice": BankDocumentFormat(
                document_type="commercial_invoice",
                bank_code="HSBC",
                fields=[
                    BankFieldRequirement(
                        "amount_in_words",
                        is_required=True,
                        notes="Total amount must be stated in words"
                    ),
                    BankFieldRequirement(
                        "incoterms",
                        is_required=True,
                        notes="Incoterms must be clearly stated with place"
                    ),
                ],
                certification_text="WE CERTIFY THAT THE ABOVE PARTICULARS ARE TRUE AND CORRECT",
            ),
            "bill_of_exchange": BankDocumentFormat(
                document_type="bill_of_exchange",
                bank_code="HSBC",
                fields=[
                    BankFieldRequirement(
                        "drawer_signature",
                        is_required=True,
                        notes="Must be signed by authorized signatory"
                    ),
                    BankFieldRequirement(
                        "payee_name",
                        is_required=True,
                        exact_wording="DRAWN ON ORDER OF",
                    ),
                ],
                special_instructions="Draft must be drawn on the applicant's bank",
            ),
        }
    ),
    
    # Citibank
    "CITI": BankProfile(
        code="CITI",
        name="Citibank",
        country="International",
        swift_code="CITIUS33",
        general_requirements=[
            "All documents must be dated and signed",
            "No alterations without authentication",
            "Copy documents must be marked COPY",
        ],
        document_formats={
            "commercial_invoice": BankDocumentFormat(
                document_type="commercial_invoice",
                bank_code="CITI",
                fields=[
                    BankFieldRequirement(
                        "beneficiary_declaration",
                        is_required=True,
                        exact_wording="We certify that the goods are of origin as stated",
                    ),
                ],
            ),
        }
    ),
    
    # Bangladesh Bank (Local)
    "BB": BankProfile(
        code="BB",
        name="Bangladesh Bank",
        country="Bangladesh",
        general_requirements=[
            "Export LC proceeds must be repatriated within prescribed time",
            "Customs clearance documents must accompany shipment docs",
            "EXP form must be submitted",
        ],
        document_formats={
            "commercial_invoice": BankDocumentFormat(
                document_type="commercial_invoice",
                bank_code="BB",
                fields=[
                    BankFieldRequirement(
                        "exp_number",
                        is_required=True,
                        notes="EXP form number must be referenced"
                    ),
                ],
                special_instructions="Must comply with Bangladesh Bank FE Circular requirements",
            ),
        }
    ),
    
    # State Bank of India
    "SBI": BankProfile(
        code="SBI",
        name="State Bank of India",
        country="India",
        swift_code="SBININBB",
        general_requirements=[
            "FEMA compliance required",
            "AD Code must be mentioned",
            "IEC number required for exports",
        ],
        document_formats={
            "commercial_invoice": BankDocumentFormat(
                document_type="commercial_invoice",
                bank_code="SBI",
                fields=[
                    BankFieldRequirement(
                        "iec_number",
                        is_required=True,
                        format_regex=r"^[A-Z0-9]{10}$",
                        notes="Import Export Code (10 characters)"
                    ),
                    BankFieldRequirement(
                        "ad_code",
                        is_required=True,
                        notes="Authorized Dealer Code"
                    ),
                ],
            ),
        }
    ),
    
    # Habib Bank Limited (Pakistan)
    "HBL": BankProfile(
        code="HBL",
        name="Habib Bank Limited",
        country="Pakistan",
        swift_code="HABORPKX",
        general_requirements=[
            "SBP regulations compliance",
            "Form E submission required",
            "NTN must be mentioned",
        ],
        document_formats={
            "commercial_invoice": BankDocumentFormat(
                document_type="commercial_invoice",
                bank_code="HBL",
                fields=[
                    BankFieldRequirement(
                        "ntn_number",
                        is_required=True,
                        notes="National Tax Number"
                    ),
                    BankFieldRequirement(
                        "form_e_number",
                        is_required=True,
                        notes="Form E reference number"
                    ),
                ],
            ),
        }
    ),
}


class BankFormatRegistry:
    """
    Registry for bank-specific document format requirements.
    
    Usage:
        registry = BankFormatRegistry()
        profile = registry.get_bank_profile("SCB")
        requirements = registry.get_document_requirements("SCB", "commercial_invoice")
    """
    
    def __init__(self):
        self._profiles = BANK_PROFILES
    
    def get_bank_profile(self, bank_code: str) -> Optional[BankProfile]:
        """Get complete bank profile"""
        return self._profiles.get(bank_code.upper())
    
    def get_document_requirements(
        self,
        bank_code: str,
        document_type: str
    ) -> Optional[BankDocumentFormat]:
        """Get requirements for a specific document type"""
        profile = self.get_bank_profile(bank_code)
        if not profile:
            return None
        return profile.document_formats.get(document_type)
    
    def list_banks(self) -> List[Dict[str, str]]:
        """List all registered banks"""
        return [
            {
                "code": p.code,
                "name": p.name,
                "country": p.country,
                "swift": p.swift_code or "",
            }
            for p in self._profiles.values()
        ]
    
    def list_banks_by_country(self, country: str) -> List[Dict[str, str]]:
        """List banks for a specific country"""
        return [
            {
                "code": p.code,
                "name": p.name,
                "swift": p.swift_code or "",
            }
            for p in self._profiles.values()
            if p.country.lower() == country.lower()
        ]
    
    def validate_document(
        self,
        bank_code: str,
        document_type: str,
        document_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Validate document data against bank requirements.
        
        Returns list of validation issues.
        """
        issues = []
        
        profile = self.get_bank_profile(bank_code)
        if not profile:
            return issues  # No specific requirements
        
        format_req = profile.document_formats.get(document_type)
        if not format_req:
            return issues
        
        # Check field requirements
        for field_req in format_req.fields:
            field_value = document_data.get(field_req.field_name)
            
            # Required check
            if field_req.is_required and not field_value:
                issues.append({
                    "field": field_req.field_name,
                    "type": "missing_required",
                    "message": f"{field_req.field_name} is required by {profile.name}",
                    "bank_code": bank_code,
                    "notes": field_req.notes,
                })
            
            # Format check
            if field_value and field_req.format_regex:
                import re
                if not re.match(field_req.format_regex, str(field_value)):
                    issues.append({
                        "field": field_req.field_name,
                        "type": "format_error",
                        "message": f"{field_req.field_name} format does not match bank requirements",
                        "expected_format": field_req.format_regex,
                        "bank_code": bank_code,
                    })
        
        return issues
    
    def get_certification_text(
        self,
        bank_code: str,
        document_type: str
    ) -> Optional[str]:
        """Get bank-required certification text for a document"""
        format_req = self.get_document_requirements(bank_code, document_type)
        if format_req:
            return format_req.certification_text
        return None
    
    def register_bank(self, profile: BankProfile):
        """Register a new bank profile"""
        self._profiles[profile.code] = profile
        logger.info(f"Registered bank profile: {profile.code} - {profile.name}")


# Singleton
_registry: Optional[BankFormatRegistry] = None


def get_bank_format_registry() -> BankFormatRegistry:
    global _registry
    if _registry is None:
        _registry = BankFormatRegistry()
    return _registry

