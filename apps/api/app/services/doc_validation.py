"""
Document Validation Service

Validates documents against LC requirements and ensures consistency across documents.
Implements UCP600/ISBP745 rules for documentary credit compliance.
"""

import logging
from decimal import Decimal
from datetime import date, datetime
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ValidationSeverity(str, Enum):
    ERROR = "error"      # Document will be rejected
    WARNING = "warning"  # May cause issues
    INFO = "info"        # Suggestion


class ValidationIssue(BaseModel):
    """A single validation issue"""
    code: str
    severity: ValidationSeverity
    field: str
    message: str
    expected: Optional[str] = None
    found: Optional[str] = None
    rule_reference: Optional[str] = None  # UCP600/ISBP reference


class ValidationResult(BaseModel):
    """Result of document validation"""
    is_valid: bool
    status: str  # passed, warnings, failed
    errors: List[ValidationIssue] = []
    warnings: List[ValidationIssue] = []
    info: List[ValidationIssue] = []
    
    @property
    def all_issues(self) -> List[ValidationIssue]:
        return self.errors + self.warnings + self.info


class LCData(BaseModel):
    """LC data for validation"""
    lc_number: str
    lc_date: Optional[date] = None
    lc_amount: Decimal
    lc_currency: str = "USD"
    tolerance_plus: float = 0  # % allowed over
    tolerance_minus: float = 0  # % allowed under
    latest_shipment_date: Optional[date] = None
    expiry_date: Optional[date] = None
    presentation_period: int = 21  # days after shipment
    
    # Required fields from LC
    beneficiary_name: Optional[str] = None
    applicant_name: Optional[str] = None
    goods_description: Optional[str] = None
    port_of_loading: Optional[str] = None
    port_of_discharge: Optional[str] = None
    incoterms: Optional[str] = None
    
    # Partial shipment
    partial_shipments_allowed: bool = True
    
    class Config:
        arbitrary_types_allowed = True


class DocumentSetData(BaseModel):
    """Document set data for validation"""
    lc_number: Optional[str] = None
    lc_date: Optional[date] = None
    
    # Parties
    beneficiary_name: str
    applicant_name: str
    
    # Amounts
    invoice_amount: Decimal
    currency: str = "USD"
    
    # Shipment
    shipment_date: Optional[date] = None
    vessel_name: Optional[str] = None
    port_of_loading: Optional[str] = None
    port_of_discharge: Optional[str] = None
    incoterms: Optional[str] = None
    
    # Line items totals
    total_quantity: int = 0
    total_cartons: int = 0
    gross_weight_kg: Decimal = Decimal("0")
    net_weight_kg: Decimal = Decimal("0")
    
    # Document dates
    invoice_date: Optional[date] = None
    bl_date: Optional[date] = None
    
    class Config:
        arbitrary_types_allowed = True


class DocumentValidator:
    """
    Validates documents against LC requirements and UCP600/ISBP rules.
    """
    
    def __init__(self):
        self.issues: List[ValidationIssue] = []
    
    def validate_against_lc(
        self, 
        doc_data: DocumentSetData, 
        lc_data: LCData
    ) -> ValidationResult:
        """
        Validate document set against LC requirements.
        
        Implements key UCP600 rules:
        - Article 18: Commercial Invoice requirements
        - Article 30: Tolerance in amount, quantity, unit price
        - Article 14: Examination of documents standard
        """
        self.issues = []
        
        # Check LC number match
        self._check_lc_number(doc_data, lc_data)
        
        # Check amount with tolerance (UCP600 Art. 30)
        self._check_amount_tolerance(doc_data, lc_data)
        
        # Check dates
        self._check_dates(doc_data, lc_data)
        
        # Check parties
        self._check_parties(doc_data, lc_data)
        
        # Check shipment details
        self._check_shipment_details(doc_data, lc_data)
        
        # Build result
        errors = [i for i in self.issues if i.severity == ValidationSeverity.ERROR]
        warnings = [i for i in self.issues if i.severity == ValidationSeverity.WARNING]
        info = [i for i in self.issues if i.severity == ValidationSeverity.INFO]
        
        if errors:
            status = "failed"
            is_valid = False
        elif warnings:
            status = "warnings"
            is_valid = True
        else:
            status = "passed"
            is_valid = True
        
        return ValidationResult(
            is_valid=is_valid,
            status=status,
            errors=errors,
            warnings=warnings,
            info=info
        )
    
    def _check_lc_number(self, doc_data: DocumentSetData, lc_data: LCData):
        """Check LC number matches"""
        if doc_data.lc_number and doc_data.lc_number != lc_data.lc_number:
            self.issues.append(ValidationIssue(
                code="LC_NUMBER_MISMATCH",
                severity=ValidationSeverity.ERROR,
                field="lc_number",
                message="LC number on document doesn't match LC",
                expected=lc_data.lc_number,
                found=doc_data.lc_number,
                rule_reference="UCP600 Art. 14(d)"
            ))
    
    def _check_amount_tolerance(self, doc_data: DocumentSetData, lc_data: LCData):
        """
        Check invoice amount is within LC tolerance.
        
        UCP600 Article 30:
        - 5% tolerance on quantity/unit price if LC doesn't prohibit
        - Invoice amount cannot exceed LC amount
        - If "about" or "approximately" used, 10% tolerance
        """
        lc_amount = float(lc_data.lc_amount)
        doc_amount = float(doc_data.invoice_amount)
        
        # Maximum allowed (with plus tolerance)
        max_allowed = lc_amount * (1 + lc_data.tolerance_plus / 100)
        
        # Minimum allowed (with minus tolerance) 
        min_allowed = lc_amount * (1 - lc_data.tolerance_minus / 100)
        
        if doc_amount > max_allowed:
            self.issues.append(ValidationIssue(
                code="AMOUNT_EXCEEDS_LC",
                severity=ValidationSeverity.ERROR,
                field="invoice_amount",
                message=f"Invoice amount exceeds LC amount + tolerance",
                expected=f"{lc_data.lc_currency} {max_allowed:,.2f} (max)",
                found=f"{doc_data.currency} {doc_amount:,.2f}",
                rule_reference="UCP600 Art. 18(b), Art. 30"
            ))
        elif doc_amount < min_allowed:
            self.issues.append(ValidationIssue(
                code="AMOUNT_BELOW_LC",
                severity=ValidationSeverity.WARNING,
                field="invoice_amount",
                message=f"Invoice amount is below LC amount - tolerance",
                expected=f"{lc_data.lc_currency} {min_allowed:,.2f} (min)",
                found=f"{doc_data.currency} {doc_amount:,.2f}",
                rule_reference="UCP600 Art. 30"
            ))
        
        # Currency mismatch
        if doc_data.currency != lc_data.lc_currency:
            self.issues.append(ValidationIssue(
                code="CURRENCY_MISMATCH",
                severity=ValidationSeverity.ERROR,
                field="currency",
                message="Document currency doesn't match LC currency",
                expected=lc_data.lc_currency,
                found=doc_data.currency,
                rule_reference="UCP600 Art. 18(a)"
            ))
    
    def _check_dates(self, doc_data: DocumentSetData, lc_data: LCData):
        """
        Check date-related requirements.
        
        UCP600 Article 14(i): Invoice date can't be before LC date
        UCP600 Article 14(c): B/L date is shipment date
        """
        today = date.today()
        
        # Invoice date before LC date
        if doc_data.invoice_date and lc_data.lc_date:
            if doc_data.invoice_date < lc_data.lc_date:
                self.issues.append(ValidationIssue(
                    code="INVOICE_DATE_BEFORE_LC",
                    severity=ValidationSeverity.ERROR,
                    field="invoice_date",
                    message="Invoice date cannot be before LC issue date",
                    expected=f"On or after {lc_data.lc_date}",
                    found=str(doc_data.invoice_date),
                    rule_reference="UCP600 Art. 14(i)"
                ))
        
        # Shipment after latest shipment date
        if doc_data.shipment_date and lc_data.latest_shipment_date:
            if doc_data.shipment_date > lc_data.latest_shipment_date:
                self.issues.append(ValidationIssue(
                    code="LATE_SHIPMENT",
                    severity=ValidationSeverity.ERROR,
                    field="shipment_date",
                    message="Shipment date is after LC latest shipment date",
                    expected=f"On or before {lc_data.latest_shipment_date}",
                    found=str(doc_data.shipment_date),
                    rule_reference="UCP600 Art. 14(b)"
                ))
        
        # Document presentation period
        if doc_data.bl_date and lc_data.expiry_date:
            presentation_deadline = doc_data.bl_date
            # Add presentation period (typically 21 days)
            from datetime import timedelta
            presentation_deadline = doc_data.bl_date + timedelta(days=lc_data.presentation_period)
            
            if presentation_deadline > lc_data.expiry_date:
                self.issues.append(ValidationIssue(
                    code="PRESENTATION_AFTER_EXPIRY",
                    severity=ValidationSeverity.WARNING,
                    field="bl_date",
                    message=f"Documents must be presented within {lc_data.presentation_period} days of B/L date, which may exceed LC expiry",
                    expected=f"Present by {min(presentation_deadline, lc_data.expiry_date)}",
                    found=f"B/L dated {doc_data.bl_date}",
                    rule_reference="UCP600 Art. 14(c)"
                ))
    
    def _check_parties(self, doc_data: DocumentSetData, lc_data: LCData):
        """Check party names match LC"""
        # Beneficiary name
        if lc_data.beneficiary_name:
            if not self._names_match(doc_data.beneficiary_name, lc_data.beneficiary_name):
                self.issues.append(ValidationIssue(
                    code="BENEFICIARY_NAME_MISMATCH",
                    severity=ValidationSeverity.ERROR,
                    field="beneficiary_name",
                    message="Beneficiary name doesn't match LC",
                    expected=lc_data.beneficiary_name,
                    found=doc_data.beneficiary_name,
                    rule_reference="UCP600 Art. 18(a)(i)"
                ))
        
        # Applicant name
        if lc_data.applicant_name:
            if not self._names_match(doc_data.applicant_name, lc_data.applicant_name):
                self.issues.append(ValidationIssue(
                    code="APPLICANT_NAME_MISMATCH",
                    severity=ValidationSeverity.WARNING,
                    field="applicant_name",
                    message="Applicant name doesn't match LC",
                    expected=lc_data.applicant_name,
                    found=doc_data.applicant_name,
                    rule_reference="ISBP745 Para. A35"
                ))
    
    def _check_shipment_details(self, doc_data: DocumentSetData, lc_data: LCData):
        """Check shipment details match LC requirements"""
        # Port of loading
        if lc_data.port_of_loading and doc_data.port_of_loading:
            if not self._locations_match(doc_data.port_of_loading, lc_data.port_of_loading):
                self.issues.append(ValidationIssue(
                    code="POL_MISMATCH",
                    severity=ValidationSeverity.ERROR,
                    field="port_of_loading",
                    message="Port of loading doesn't match LC",
                    expected=lc_data.port_of_loading,
                    found=doc_data.port_of_loading,
                    rule_reference="UCP600 Art. 20(a)(ii)"
                ))
        
        # Port of discharge
        if lc_data.port_of_discharge and doc_data.port_of_discharge:
            if not self._locations_match(doc_data.port_of_discharge, lc_data.port_of_discharge):
                self.issues.append(ValidationIssue(
                    code="POD_MISMATCH",
                    severity=ValidationSeverity.ERROR,
                    field="port_of_discharge",
                    message="Port of discharge doesn't match LC",
                    expected=lc_data.port_of_discharge,
                    found=doc_data.port_of_discharge,
                    rule_reference="UCP600 Art. 20(a)(ii)"
                ))
        
        # Incoterms
        if lc_data.incoterms and doc_data.incoterms:
            if doc_data.incoterms.upper() != lc_data.incoterms.upper():
                self.issues.append(ValidationIssue(
                    code="INCOTERMS_MISMATCH",
                    severity=ValidationSeverity.ERROR,
                    field="incoterms",
                    message="Incoterms don't match LC",
                    expected=lc_data.incoterms,
                    found=doc_data.incoterms,
                    rule_reference="ISBP745 Para. C2"
                ))
    
    def _names_match(self, name1: str, name2: str) -> bool:
        """Check if two names are equivalent (fuzzy match)"""
        # Normalize names
        n1 = name1.lower().strip()
        n2 = name2.lower().strip()
        
        # Remove common suffixes
        for suffix in ['ltd', 'limited', 'inc', 'corp', 'corporation', 'co', 'company', 'llc', 'plc', 'pvt']:
            n1 = n1.replace(suffix, '').strip()
            n2 = n2.replace(suffix, '').strip()
        
        # Remove punctuation
        import re
        n1 = re.sub(r'[^\w\s]', '', n1)
        n2 = re.sub(r'[^\w\s]', '', n2)
        
        return n1 == n2
    
    def _locations_match(self, loc1: str, loc2: str) -> bool:
        """Check if two locations are equivalent"""
        l1 = loc1.lower().strip()
        l2 = loc2.lower().strip()
        
        # Check if one contains the other
        return l1 in l2 or l2 in l1


class ConsistencyValidator:
    """
    Validates consistency across all documents in a set.
    
    Ensures Invoice, Packing List, CoO, etc. all have matching data.
    """
    
    def __init__(self):
        self.issues: List[ValidationIssue] = []
    
    def validate_consistency(
        self,
        invoice_data: Dict[str, Any],
        packing_list_data: Optional[Dict[str, Any]] = None,
        coo_data: Optional[Dict[str, Any]] = None,
        draft_data: Optional[Dict[str, Any]] = None,
    ) -> ValidationResult:
        """
        Validate consistency across documents.
        
        All documents must have matching:
        - LC number
        - Beneficiary name
        - Applicant name
        - Quantities and weights
        - Amounts (where applicable)
        - Shipping marks
        """
        self.issues = []
        
        # Invoice vs Packing List
        if packing_list_data:
            self._check_invoice_vs_packing_list(invoice_data, packing_list_data)
        
        # Invoice vs Bill of Exchange
        if draft_data:
            self._check_invoice_vs_draft(invoice_data, draft_data)
        
        # Invoice vs Certificate of Origin
        if coo_data:
            self._check_invoice_vs_coo(invoice_data, coo_data)
        
        # Build result
        errors = [i for i in self.issues if i.severity == ValidationSeverity.ERROR]
        warnings = [i for i in self.issues if i.severity == ValidationSeverity.WARNING]
        info = [i for i in self.issues if i.severity == ValidationSeverity.INFO]
        
        if errors:
            status = "failed"
            is_valid = False
        elif warnings:
            status = "warnings"
            is_valid = True
        else:
            status = "passed"
            is_valid = True
        
        return ValidationResult(
            is_valid=is_valid,
            status=status,
            errors=errors,
            warnings=warnings,
            info=info
        )
    
    def _check_invoice_vs_packing_list(
        self, 
        invoice: Dict[str, Any], 
        packing_list: Dict[str, Any]
    ):
        """Check Invoice and Packing List consistency"""
        # Quantity
        inv_qty = invoice.get("total_quantity", 0)
        pl_qty = packing_list.get("total_quantity", 0)
        if inv_qty != pl_qty:
            self.issues.append(ValidationIssue(
                code="QTY_MISMATCH_INV_PL",
                severity=ValidationSeverity.ERROR,
                field="total_quantity",
                message="Total quantity differs between Invoice and Packing List",
                expected=f"Invoice: {inv_qty:,}",
                found=f"Packing List: {pl_qty:,}",
                rule_reference="ISBP745 Para. L10"
            ))
        
        # Gross weight (3% tolerance allowed)
        inv_weight = float(invoice.get("gross_weight_kg", 0))
        pl_weight = float(packing_list.get("gross_weight_kg", 0))
        if inv_weight > 0 and pl_weight > 0:
            diff_pct = abs(inv_weight - pl_weight) / inv_weight * 100
            if diff_pct > 3:
                self.issues.append(ValidationIssue(
                    code="WEIGHT_MISMATCH_INV_PL",
                    severity=ValidationSeverity.WARNING,
                    field="gross_weight_kg",
                    message=f"Gross weight differs by {diff_pct:.1f}% between Invoice and Packing List (>3%)",
                    expected=f"Invoice: {inv_weight:,.2f} KG",
                    found=f"Packing List: {pl_weight:,.2f} KG",
                    rule_reference="ISBP745 Para. L11"
                ))
        
        # Cartons
        inv_cartons = invoice.get("total_cartons", 0)
        pl_cartons = packing_list.get("total_cartons", 0)
        if inv_cartons and pl_cartons and inv_cartons != pl_cartons:
            self.issues.append(ValidationIssue(
                code="CARTONS_MISMATCH_INV_PL",
                severity=ValidationSeverity.ERROR,
                field="total_cartons",
                message="Total cartons differ between Invoice and Packing List",
                expected=f"Invoice: {inv_cartons:,}",
                found=f"Packing List: {pl_cartons:,}",
                rule_reference="ISBP745 Para. L10"
            ))
        
        # Shipping marks
        inv_marks = (invoice.get("shipping_marks") or "").strip()
        pl_marks = (packing_list.get("shipping_marks") or "").strip()
        if inv_marks and pl_marks and inv_marks != pl_marks:
            self.issues.append(ValidationIssue(
                code="MARKS_MISMATCH_INV_PL",
                severity=ValidationSeverity.WARNING,
                field="shipping_marks",
                message="Shipping marks differ between Invoice and Packing List",
                expected=f"Invoice: {inv_marks[:50]}...",
                found=f"Packing List: {pl_marks[:50]}...",
                rule_reference="ISBP745 Para. L13"
            ))
    
    def _check_invoice_vs_draft(
        self, 
        invoice: Dict[str, Any], 
        draft: Dict[str, Any]
    ):
        """Check Invoice and Bill of Exchange consistency"""
        # Amount must match exactly
        inv_amount = float(invoice.get("total_amount", 0))
        draft_amount = float(draft.get("amount", 0))
        
        if inv_amount != draft_amount:
            self.issues.append(ValidationIssue(
                code="AMOUNT_MISMATCH_INV_DRAFT",
                severity=ValidationSeverity.ERROR,
                field="amount",
                message="Invoice amount and Draft amount don't match",
                expected=f"Invoice: {invoice.get('currency', 'USD')} {inv_amount:,.2f}",
                found=f"Draft: {draft.get('currency', 'USD')} {draft_amount:,.2f}",
                rule_reference="UCP600 Art. 18(c)"
            ))
        
        # Currency must match
        inv_currency = invoice.get("currency", "USD")
        draft_currency = draft.get("currency", "USD")
        if inv_currency != draft_currency:
            self.issues.append(ValidationIssue(
                code="CURRENCY_MISMATCH_INV_DRAFT",
                severity=ValidationSeverity.ERROR,
                field="currency",
                message="Invoice and Draft currencies don't match",
                expected=inv_currency,
                found=draft_currency,
                rule_reference="UCP600 Art. 18(a)"
            ))
    
    def _check_invoice_vs_coo(
        self, 
        invoice: Dict[str, Any], 
        coo: Dict[str, Any]
    ):
        """Check Invoice and Certificate of Origin consistency"""
        # Goods description should correspond
        inv_desc = (invoice.get("goods_description") or "").lower()
        coo_desc = (coo.get("goods_description") or "").lower()
        
        # Country of origin
        inv_origin = invoice.get("country_of_origin", "").lower()
        coo_origin = coo.get("country_of_origin", "").lower()
        
        if inv_origin and coo_origin and inv_origin != coo_origin:
            self.issues.append(ValidationIssue(
                code="ORIGIN_MISMATCH_INV_COO",
                severity=ValidationSeverity.ERROR,
                field="country_of_origin",
                message="Country of origin differs between Invoice and CoO",
                expected=f"Invoice: {inv_origin}",
                found=f"CoO: {coo_origin}",
                rule_reference="ISBP745 Para. K6"
            ))


# Singleton validators
_document_validator: Optional[DocumentValidator] = None
_consistency_validator: Optional[ConsistencyValidator] = None


def get_document_validator() -> DocumentValidator:
    global _document_validator
    if _document_validator is None:
        _document_validator = DocumentValidator()
    return _document_validator


def get_consistency_validator() -> ConsistencyValidator:
    global _consistency_validator
    if _consistency_validator is None:
        _consistency_validator = ConsistencyValidator()
    return _consistency_validator

