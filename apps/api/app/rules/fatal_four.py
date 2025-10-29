"""
Fatal Four validation rules implementation.

The "Fatal Four" are the critical validation checks:
1. Dates - Ensure dates are consistent and within valid ranges
2. Amounts - Verify amounts match across documents  
3. Parties - Check party information consistency
4. Ports - Validate port information matches
"""

import re
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import List, Dict, Optional
from difflib import SequenceMatcher

from .models import (
    ValidationRule, ValidationResult, ValidationStatus, 
    ExtractedField, FieldType, FieldComparison,
    DocumentType
)
from ..models import DiscrepancySeverity, DiscrepancyType


class FatalFourValidator:
    """Validator for the Fatal Four critical checks."""
    
    def __init__(self):
        self.rules = self._initialize_rules()
    
    def _initialize_rules(self) -> List[ValidationRule]:
        """Initialize the Fatal Four validation rules."""
        return [
            # Date validation rules
            ValidationRule(
                rule_id="FF001",
                rule_name="LC Expiry Date Future",
                description="LC expiry date must be in the future",
                field_type=FieldType.DATE,
                severity=DiscrepancySeverity.CRITICAL
            ),
            ValidationRule(
                rule_id="FF002", 
                rule_name="Document Date Consistency",
                description="Document dates must be logically consistent",
                field_type=FieldType.DATE,
                severity=DiscrepancySeverity.MAJOR,
                is_cross_document=True
            ),
            ValidationRule(
                rule_id="FF003",
                rule_name="Invoice Date Before LC Expiry",
                description="Invoice date must be before LC expiry date",
                field_type=FieldType.DATE,
                severity=DiscrepancySeverity.CRITICAL,
                is_cross_document=True
            ),
            
            # Amount validation rules
            ValidationRule(
                rule_id="FF010",
                rule_name="LC Amount Match Invoice",
                description="Invoice amount must not exceed LC amount",
                field_type=FieldType.AMOUNT,
                severity=DiscrepancySeverity.CRITICAL,
                is_cross_document=True
            ),
            ValidationRule(
                rule_id="FF011",
                rule_name="Amount Format Valid",
                description="All amounts must be in valid numeric format",
                field_type=FieldType.AMOUNT,
                severity=DiscrepancySeverity.MAJOR
            ),
            
            # Party validation rules
            ValidationRule(
                rule_id="FF020",
                rule_name="Beneficiary Consistency",
                description="Beneficiary must match across LC and invoice",
                field_type=FieldType.PARTY,
                severity=DiscrepancySeverity.MAJOR,
                is_cross_document=True
            ),
            ValidationRule(
                rule_id="FF021",
                rule_name="Consignee Consistency", 
                description="Consignee must match across invoice and B/L",
                field_type=FieldType.PARTY,
                severity=DiscrepancySeverity.MAJOR,
                is_cross_document=True
            ),
            
            # Port validation rules
            ValidationRule(
                rule_id="FF030",
                rule_name="Port of Loading Consistency",
                description="Port of loading must match across documents",
                field_type=FieldType.PORT,
                severity=DiscrepancySeverity.MAJOR,
                is_cross_document=True
            ),
            ValidationRule(
                rule_id="FF031",
                rule_name="Port of Discharge Consistency",
                description="Port of discharge must match across documents",
                field_type=FieldType.PORT,
                severity=DiscrepancySeverity.MAJOR,
                is_cross_document=True
            )
        ]
    
    def validate_documents(
        self, 
        lc_fields: List[ExtractedField],
        invoice_fields: List[ExtractedField], 
        bl_fields: List[ExtractedField]
    ) -> List[ValidationResult]:
        """
        Validate documents against Fatal Four rules.
        
        Args:
            lc_fields: Fields extracted from Letter of Credit
            invoice_fields: Fields extracted from Commercial Invoice
            bl_fields: Fields extracted from Bill of Lading
            
        Returns:
            List of validation results
        """
        results = []
        
        # Create field lookup dictionaries
        lc_dict = {f.field_name: f for f in lc_fields}
        invoice_dict = {f.field_name: f for f in invoice_fields}  
        bl_dict = {f.field_name: f for f in bl_fields}
        
        # Run all validation rules
        for rule in self.rules:
            if rule.field_type == FieldType.DATE:
                results.extend(self._validate_dates(rule, lc_dict, invoice_dict, bl_dict))
            elif rule.field_type == FieldType.AMOUNT:
                results.extend(self._validate_amounts(rule, lc_dict, invoice_dict, bl_dict))
            elif rule.field_type == FieldType.PARTY:
                results.extend(self._validate_parties(rule, lc_dict, invoice_dict, bl_dict))
            elif rule.field_type == FieldType.PORT:
                results.extend(self._validate_ports(rule, lc_dict, invoice_dict, bl_dict))
        
        return results
    
    def create_field_comparisons(
        self,
        lc_fields: List[ExtractedField],
        invoice_fields: List[ExtractedField],
        bl_fields: List[ExtractedField]
    ) -> List[FieldComparison]:
        """Create cross-document field comparisons."""
        comparisons = []
        
        # Create field lookup dictionaries
        lc_dict = {f.field_name: f for f in lc_fields}
        invoice_dict = {f.field_name: f for f in invoice_fields}
        bl_dict = {f.field_name: f for f in bl_fields}
        
        # Define fields to compare across documents
        comparison_fields = [
            ("lc_amount", "invoice_amount", None, "Amount"),
            ("beneficiary", "consignee", "shipper", "Beneficiary/Shipper"),
            ("port_of_loading", "port_of_loading", "port_of_loading", "Port of Loading"),
            ("port_of_discharge", "port_of_discharge", "port_of_discharge", "Port of Discharge"),
            ("expiry_date", "invoice_date", "bl_date", "Key Dates")
        ]
        
        for lc_field, invoice_field, bl_field, display_name in comparison_fields:
            lc_extracted = lc_dict.get(lc_field)
            invoice_extracted = invoice_dict.get(invoice_field) 
            bl_extracted = bl_dict.get(bl_field)
            
            # Skip if no fields found
            if not any([lc_extracted, invoice_extracted, bl_extracted]):
                continue
            
            # Determine field type
            field_type = FieldType.TEXT
            if lc_extracted:
                field_type = lc_extracted.field_type
            elif invoice_extracted:
                field_type = invoice_extracted.field_type
            elif bl_extracted:
                field_type = bl_extracted.field_type
            
            # Check consistency
            values = []
            if lc_extracted and lc_extracted.value:
                values.append(lc_extracted.value)
            if invoice_extracted and invoice_extracted.value:
                values.append(invoice_extracted.value)
            if bl_extracted and bl_extracted.value:
                values.append(bl_extracted.value)
            
            is_consistent = True
            discrepancies = []
            
            if len(values) > 1:
                is_consistent, discrepancies = self._check_field_consistency(
                    values, field_type
                )
            
            comparisons.append(FieldComparison(
                field_name=display_name,
                field_type=field_type,
                lc_field=lc_extracted,
                invoice_field=invoice_extracted,
                bl_field=bl_extracted,
                is_consistent=is_consistent,
                discrepancies=discrepancies
            ))
        
        return comparisons
    
    def _validate_dates(
        self,
        rule: ValidationRule,
        lc_dict: Dict[str, ExtractedField],
        invoice_dict: Dict[str, ExtractedField],
        bl_dict: Dict[str, ExtractedField]
    ) -> List[ValidationResult]:
        """Validate date-related rules."""
        results = []
        
        if rule.rule_id == "FF001":  # LC Expiry Date Future
            expiry_field = lc_dict.get("expiry_date")
            if expiry_field and expiry_field.value:
                expiry_date = self._parse_date(expiry_field.value)
                if expiry_date:
                    if expiry_date <= datetime.now():
                        results.append(ValidationResult(
                            rule=rule,
                            status=ValidationStatus.FAILED,
                            message="LC has expired or expires today",
                            expected_value="Future date",
                            actual_value=expiry_field.value,
                            confidence=expiry_field.confidence,
                            affected_documents=[DocumentType.LETTER_OF_CREDIT]
                        ))
                    else:
                        results.append(ValidationResult(
                            rule=rule,
                            status=ValidationStatus.PASSED,
                            message="LC expiry date is valid",
                            actual_value=expiry_field.value,
                            confidence=expiry_field.confidence,
                            affected_documents=[DocumentType.LETTER_OF_CREDIT]
                        ))
        
        elif rule.rule_id == "FF003":  # Invoice Date Before LC Expiry
            expiry_field = lc_dict.get("expiry_date")
            invoice_date_field = invoice_dict.get("invoice_date")
            
            if expiry_field and invoice_date_field and expiry_field.value and invoice_date_field.value:
                expiry_date = self._parse_date(expiry_field.value)
                invoice_date = self._parse_date(invoice_date_field.value)
                
                if expiry_date and invoice_date:
                    if invoice_date > expiry_date:
                        results.append(ValidationResult(
                            rule=rule,
                            status=ValidationStatus.FAILED,
                            message="Invoice date is after LC expiry date",
                            expected_value=f"Before {expiry_field.value}",
                            actual_value=invoice_date_field.value,
                            affected_documents=[DocumentType.LETTER_OF_CREDIT, DocumentType.COMMERCIAL_INVOICE]
                        ))
                    else:
                        results.append(ValidationResult(
                            rule=rule,
                            status=ValidationStatus.PASSED,
                            message="Invoice date is before LC expiry",
                            affected_documents=[DocumentType.LETTER_OF_CREDIT, DocumentType.COMMERCIAL_INVOICE]
                        ))
        
        return results
    
    def _validate_amounts(
        self,
        rule: ValidationRule,
        lc_dict: Dict[str, ExtractedField],
        invoice_dict: Dict[str, ExtractedField], 
        bl_dict: Dict[str, ExtractedField]
    ) -> List[ValidationResult]:
        """Validate amount-related rules."""
        results = []
        
        if rule.rule_id == "FF010":  # LC Amount Match Invoice
            lc_amount_field = lc_dict.get("lc_amount")
            invoice_amount_field = invoice_dict.get("invoice_amount")
            
            if lc_amount_field and invoice_amount_field:
                lc_amount = self._parse_amount(lc_amount_field.value)
                invoice_amount = self._parse_amount(invoice_amount_field.value)
                
                if lc_amount is not None and invoice_amount is not None:
                    if invoice_amount > lc_amount:
                        results.append(ValidationResult(
                            rule=rule,
                            status=ValidationStatus.FAILED,
                            message="Invoice amount exceeds LC amount",
                            expected_value=f"<= {lc_amount}",
                            actual_value=str(invoice_amount),
                            affected_documents=[DocumentType.LETTER_OF_CREDIT, DocumentType.COMMERCIAL_INVOICE]
                        ))
                    else:
                        results.append(ValidationResult(
                            rule=rule,
                            status=ValidationStatus.PASSED,
                            message="Invoice amount is within LC amount",
                            affected_documents=[DocumentType.LETTER_OF_CREDIT, DocumentType.COMMERCIAL_INVOICE]
                        ))
        
        return results
    
    def _validate_parties(
        self,
        rule: ValidationRule,
        lc_dict: Dict[str, ExtractedField],
        invoice_dict: Dict[str, ExtractedField],
        bl_dict: Dict[str, ExtractedField]
    ) -> List[ValidationResult]:
        """Validate party-related rules."""
        results = []
        
        if rule.rule_id == "FF020":  # Beneficiary Consistency
            beneficiary = lc_dict.get("beneficiary")
            consignee = invoice_dict.get("consignee") 
            
            if beneficiary and consignee:
                similarity = self._calculate_text_similarity(
                    beneficiary.value or "", consignee.value or ""
                )
                
                if similarity < 0.7:  # 70% similarity threshold
                    results.append(ValidationResult(
                        rule=rule,
                        status=ValidationStatus.FAILED,
                        message="Beneficiary and consignee do not match",
                        expected_value=beneficiary.value,
                        actual_value=consignee.value,
                        confidence=min(beneficiary.confidence, consignee.confidence),
                        affected_documents=[DocumentType.LETTER_OF_CREDIT, DocumentType.COMMERCIAL_INVOICE]
                    ))
                else:
                    results.append(ValidationResult(
                        rule=rule,
                        status=ValidationStatus.PASSED,
                        message="Beneficiary and consignee match",
                        affected_documents=[DocumentType.LETTER_OF_CREDIT, DocumentType.COMMERCIAL_INVOICE]
                    ))
        
        elif rule.rule_id == "FF021":  # Consignee Consistency
            invoice_consignee = invoice_dict.get("consignee")
            bl_consignee = bl_dict.get("consignee")
            
            if invoice_consignee and bl_consignee:
                similarity = self._calculate_text_similarity(
                    invoice_consignee.value or "", bl_consignee.value or ""
                )
                
                if similarity < 0.7:
                    results.append(ValidationResult(
                        rule=rule,
                        status=ValidationStatus.FAILED,
                        message="Consignee does not match between invoice and B/L",
                        expected_value=invoice_consignee.value,
                        actual_value=bl_consignee.value,
                        affected_documents=[DocumentType.COMMERCIAL_INVOICE, DocumentType.BILL_OF_LADING]
                    ))
                else:
                    results.append(ValidationResult(
                        rule=rule,
                        status=ValidationStatus.PASSED,
                        message="Consignee matches between invoice and B/L",
                        affected_documents=[DocumentType.COMMERCIAL_INVOICE, DocumentType.BILL_OF_LADING]
                    ))
        
        return results
    
    def _validate_ports(
        self,
        rule: ValidationRule,
        lc_dict: Dict[str, ExtractedField],
        invoice_dict: Dict[str, ExtractedField],
        bl_dict: Dict[str, ExtractedField]
    ) -> List[ValidationResult]:
        """Validate port-related rules."""
        results = []
        
        if rule.rule_id == "FF030":  # Port of Loading Consistency
            fields_to_check = [
                ("lc", lc_dict.get("port_of_loading")),
                ("bl", bl_dict.get("port_of_loading"))
            ]
            
            valid_fields = [(name, field) for name, field in fields_to_check if field and field.value]
            
            if len(valid_fields) >= 2:
                ports = [field.value for _, field in valid_fields]
                is_consistent, discrepancies = self._check_port_consistency(ports)
                
                if not is_consistent:
                    results.append(ValidationResult(
                        rule=rule,
                        status=ValidationStatus.FAILED,
                        message="Port of loading does not match across documents",
                        expected_value=valid_fields[0][1].value,
                        actual_value=" | ".join([f.value for _, f in valid_fields[1:]]),
                        affected_documents=[DocumentType.LETTER_OF_CREDIT, DocumentType.BILL_OF_LADING]
                    ))
                else:
                    results.append(ValidationResult(
                        rule=rule,
                        status=ValidationStatus.PASSED,
                        message="Port of loading is consistent",
                        affected_documents=[DocumentType.LETTER_OF_CREDIT, DocumentType.BILL_OF_LADING]
                    ))
        
        return results
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string into datetime object."""
        if not date_str:
            return None
        
        date_formats = [
            "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d",
            "%m-%d-%Y", "%d-%m-%Y", "%Y-%m-%d",
            "%d %b %Y", "%d %B %Y",
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
        
        return None
    
    def _parse_amount(self, amount_str: str) -> Optional[Decimal]:
        """Parse amount string into Decimal."""
        if not amount_str:
            return None
        
        try:
            # Remove commas and currency symbols
            cleaned = re.sub(r'[,$]', '', amount_str.strip())
            return Decimal(cleaned)
        except (InvalidOperation, ValueError):
            return None
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text strings."""
        if not text1 or not text2:
            return 0.0
        
        return SequenceMatcher(None, text1.lower().strip(), text2.lower().strip()).ratio()
    
    def _check_field_consistency(self, values: List[str], field_type: FieldType) -> tuple[bool, List[str]]:
        """Check if field values are consistent across documents."""
        if len(values) <= 1:
            return True, []
        
        discrepancies = []
        
        if field_type == FieldType.AMOUNT:
            amounts = []
            for value in values:
                amount = self._parse_amount(value)
                if amount is not None:
                    amounts.append(amount)
            
            if len(amounts) >= 2:
                if not all(abs(a - amounts[0]) < Decimal('0.01') for a in amounts):
                    discrepancies.append("Amount values do not match")
                    return False, discrepancies
        
        elif field_type in [FieldType.PARTY, FieldType.PORT, FieldType.TEXT]:
            # Check text similarity
            for i in range(len(values)):
                for j in range(i + 1, len(values)):
                    similarity = self._calculate_text_similarity(values[i], values[j])
                    if similarity < 0.7:
                        discrepancies.append(f"Text mismatch: '{values[i]}' vs '{values[j]}'")
                        return False, discrepancies
        
        return True, discrepancies
    
    def _check_port_consistency(self, ports: List[str]) -> tuple[bool, List[str]]:
        """Check consistency of port names."""
        if len(ports) <= 1:
            return True, []
        
        discrepancies = []
        
        # Check similarity between all port pairs
        for i in range(len(ports)):
            for j in range(i + 1, len(ports)):
                similarity = self._calculate_text_similarity(ports[i], ports[j])
                if similarity < 0.8:  # Higher threshold for ports
                    discrepancies.append(f"Port mismatch: '{ports[i]}' vs '{ports[j]}'")
                    return False, discrepancies
        
        return True, discrepancies