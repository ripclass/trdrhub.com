"""
Two-Stage Extraction Pipeline

Stage 1: AI Extraction (high recall, may have errors)
Stage 2: Deterministic Validation (high precision, catches errors)

Each field gets a confidence score and extraction status:
- "trusted": High AI confidence + passes validation
- "review": Medium confidence or validation issue
- "untrusted": Low confidence or fails validation
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from app.reference_data.ports import get_port_registry
from app.reference_data.currencies import get_currency_registry
from app.reference_data.countries import get_country_registry

logger = logging.getLogger(__name__)


class ExtractionStatus(str, Enum):
    """Status of an extracted field."""
    TRUSTED = "trusted"      # High confidence + validated
    REVIEW = "review"        # Needs human review
    UNTRUSTED = "untrusted"  # Low confidence or failed validation
    MISSING = "missing"      # Not extracted


class FieldType(str, Enum):
    """Types of fields with specific validation rules."""
    LC_NUMBER = "lc_number"
    AMOUNT = "amount"
    CURRENCY = "currency"
    DATE = "date"
    PORT = "port"
    COUNTRY = "country"
    PARTY_NAME = "party_name"
    BANK_NAME = "bank_name"
    SWIFT_CODE = "swift_code"
    GOODS_DESCRIPTION = "goods"
    QUANTITY = "quantity"
    DOCUMENT_NUMBER = "document_number"
    TEXT = "text"


@dataclass
class ExtractedField:
    """A field extracted from a document."""
    name: str
    field_type: FieldType
    raw_value: Any
    normalized_value: Any = None
    ai_confidence: float = 0.0
    validation_score: float = 0.0
    status: ExtractionStatus = ExtractionStatus.MISSING
    issues: List[str] = field(default_factory=list)
    source_document: str = ""
    source_location: str = ""  # Page, bbox, etc.
    
    @property
    def final_confidence(self) -> float:
        """Combined confidence from AI and validation."""
        return (self.ai_confidence * 0.6) + (self.validation_score * 0.4)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.field_type.value,
            "raw_value": self.raw_value,
            "normalized_value": self.normalized_value,
            "ai_confidence": round(self.ai_confidence, 3),
            "validation_score": round(self.validation_score, 3),
            "final_confidence": round(self.final_confidence, 3),
            "status": self.status.value,
            "issues": self.issues,
        }


class FieldValidator:
    """Deterministic validator for extracted fields."""
    
    def __init__(self):
        self._port_registry = get_port_registry()
        self._currency_registry = get_currency_registry()
        self._country_registry = get_country_registry()
    
    def validate(self, field: ExtractedField) -> Tuple[float, List[str]]:
        """
        Validate an extracted field.
        
        Returns:
            (validation_score, issues)
            - validation_score: 0.0 to 1.0
            - issues: List of validation issues found
        """
        if field.raw_value is None:
            return 0.0, ["No value extracted"]
        
        validator_map = {
            FieldType.LC_NUMBER: self._validate_lc_number,
            FieldType.AMOUNT: self._validate_amount,
            FieldType.CURRENCY: self._validate_currency,
            FieldType.DATE: self._validate_date,
            FieldType.PORT: self._validate_port,
            FieldType.COUNTRY: self._validate_country,
            FieldType.SWIFT_CODE: self._validate_swift,
            FieldType.PARTY_NAME: self._validate_party_name,
            FieldType.GOODS_DESCRIPTION: self._validate_goods,
        }
        
        validator = validator_map.get(field.field_type, self._validate_text)
        return validator(field)
    
    def _validate_lc_number(self, field: ExtractedField) -> Tuple[float, List[str]]:
        """Validate LC number format."""
        value = str(field.raw_value).strip()
        issues = []
        
        # Basic format check
        if len(value) < 5:
            issues.append("LC number too short")
            return 0.3, issues
        
        if len(value) > 35:
            issues.append("LC number too long (max 35 chars per MT700)")
            return 0.5, issues
        
        # Check for common patterns
        if re.match(r'^[A-Z0-9/-]{5,35}$', value, re.I):
            field.normalized_value = value.upper()
            return 1.0, []
        
        # Has unusual characters
        if re.search(r'[^A-Z0-9/-]', value, re.I):
            issues.append("LC number contains unusual characters")
            return 0.6, issues
        
        return 0.8, issues
    
    def _validate_amount(self, field: ExtractedField) -> Tuple[float, List[str]]:
        """Validate monetary amount."""
        value = field.raw_value
        issues = []
        
        # Try to parse as number
        if isinstance(value, (int, float)):
            numeric = float(value)
        else:
            # Remove currency symbols, commas, spaces
            cleaned = re.sub(r'[^\d.]', '', str(value))
            try:
                numeric = float(cleaned)
            except ValueError:
                issues.append("Cannot parse amount as number")
                return 0.0, issues
        
        # Sanity checks
        if numeric <= 0:
            issues.append("Amount must be positive")
            return 0.2, issues
        
        if numeric > 1_000_000_000:
            issues.append("Amount unusually large (>1B)")
            return 0.5, issues
        
        field.normalized_value = round(numeric, 2)
        return 1.0, []
    
    def _validate_currency(self, field: ExtractedField) -> Tuple[float, List[str]]:
        """Validate currency code using ISO 4217."""
        value = str(field.raw_value).strip().upper()
        issues = []
        
        normalized = self._currency_registry.normalize(value)
        if normalized:
            field.normalized_value = normalized
            return 1.0, []
        
        # Partial match attempt
        if len(value) == 3 and value.isalpha():
            issues.append(f"Unknown currency code: {value}")
            return 0.3, issues
        
        issues.append("Invalid currency format")
        return 0.0, issues
    
    def _validate_date(self, field: ExtractedField) -> Tuple[float, List[str]]:
        """Validate date formats."""
        from datetime import datetime
        
        value = str(field.raw_value).strip()
        issues = []
        
        # Common date formats
        formats = [
            "%Y-%m-%d",
            "%d-%m-%Y",
            "%d/%m/%Y",
            "%m/%d/%Y",
            "%Y%m%d",
            "%d %b %Y",
            "%d %B %Y",
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(value, fmt)
                field.normalized_value = dt.strftime("%Y-%m-%d")
                
                # Sanity check: not too far in past or future
                now = datetime.now()
                years_diff = abs((dt - now).days) / 365
                if years_diff > 5:
                    issues.append("Date is more than 5 years from now")
                    return 0.7, issues
                
                return 1.0, []
            except ValueError:
                continue
        
        issues.append("Cannot parse date")
        return 0.0, issues
    
    def _validate_port(self, field: ExtractedField) -> Tuple[float, List[str]]:
        """Validate port using UN/LOCODE registry."""
        value = str(field.raw_value).strip()
        issues = []
        
        port = self._port_registry.resolve(value)
        if port:
            field.normalized_value = port.full_name
            return 1.0, []
        
        # Partial match - might be a valid port we don't have
        if len(value) >= 3:
            issues.append(f"Port not found in UN/LOCODE: {value}")
            return 0.5, issues
        
        issues.append("Port name too short")
        return 0.2, issues
    
    def _validate_country(self, field: ExtractedField) -> Tuple[float, List[str]]:
        """Validate country using ISO 3166."""
        value = str(field.raw_value).strip()
        issues = []
        
        country = self._country_registry.resolve(value)
        if country:
            field.normalized_value = country.name
            return 1.0, []
        
        issues.append(f"Country not found: {value}")
        return 0.3, issues
    
    def _validate_swift(self, field: ExtractedField) -> Tuple[float, List[str]]:
        """Validate SWIFT/BIC code format."""
        value = str(field.raw_value).strip().upper()
        issues = []
        
        # SWIFT codes are 8 or 11 characters
        if len(value) not in [8, 11]:
            issues.append("SWIFT code must be 8 or 11 characters")
            return 0.3, issues
        
        # Format: AAAABBCC or AAAABBCCDDD
        if not re.match(r'^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$', value):
            issues.append("Invalid SWIFT code format")
            return 0.4, issues
        
        field.normalized_value = value
        return 1.0, []
    
    def _validate_party_name(self, field: ExtractedField) -> Tuple[float, List[str]]:
        """Validate party/company name."""
        value = str(field.raw_value).strip()
        issues = []
        
        if len(value) < 3:
            issues.append("Party name too short")
            return 0.2, issues
        
        if len(value) > 200:
            issues.append("Party name too long")
            return 0.6, issues
        
        # Check for suspicious patterns
        if re.match(r'^[0-9]+$', value):
            issues.append("Party name appears to be only numbers")
            return 0.1, issues
        
        field.normalized_value = value.title() if value.isupper() else value
        return 0.9, []  # Can't fully validate names
    
    def _validate_goods(self, field: ExtractedField) -> Tuple[float, List[str]]:
        """Validate goods description."""
        value = str(field.raw_value).strip()
        issues = []
        
        if len(value) < 10:
            issues.append("Goods description too short")
            return 0.3, issues
        
        # Check for HS code (good sign)
        if re.search(r'\b\d{4,6}\.\d{2}\b', value):
            field.normalized_value = value
            return 1.0, []
        
        field.normalized_value = value
        return 0.8, []  # Can't fully validate descriptions
    
    def _validate_text(self, field: ExtractedField) -> Tuple[float, List[str]]:
        """Generic text validation."""
        value = str(field.raw_value).strip()
        
        if not value:
            return 0.0, ["Empty value"]
        
        field.normalized_value = value
        return 0.7, []  # Generic text, moderate confidence


class TwoStageExtractor:
    """
    Two-stage extraction pipeline.
    
    Stage 1: AI extraction with confidence scores
    Stage 2: Deterministic validation and normalization
    """
    
    # Confidence thresholds
    TRUSTED_THRESHOLD = 0.8
    REVIEW_THRESHOLD = 0.5
    
    def __init__(self):
        self.validator = FieldValidator()
    
    def process(
        self,
        ai_extraction: Dict[str, Any],
        document_type: str = "unknown",
    ) -> Dict[str, ExtractedField]:
        """
        Process AI extraction results through validation.
        
        Args:
            ai_extraction: Dict of field_name -> {value, confidence, ...}
            document_type: Type of document (lc, invoice, bl, etc.)
            
        Returns:
            Dict of field_name -> ExtractedField with status
        """
        results: Dict[str, ExtractedField] = {}
        
        # Map document type to expected fields
        field_types = self._get_field_types(document_type)
        
        for field_name, extraction in ai_extraction.items():
            # Get field type
            field_type = field_types.get(field_name, FieldType.TEXT)
            
            # Extract value and confidence
            if isinstance(extraction, dict):
                raw_value = extraction.get("value") or extraction.get("text")
                ai_confidence = float(extraction.get("confidence", 0.5))
            else:
                raw_value = extraction
                ai_confidence = 0.5  # Default confidence for raw values
            
            # Create field object
            field = ExtractedField(
                name=field_name,
                field_type=field_type,
                raw_value=raw_value,
                ai_confidence=ai_confidence,
                source_document=document_type,
            )
            
            # Stage 2: Validate
            validation_score, issues = self.validator.validate(field)
            field.validation_score = validation_score
            field.issues = issues
            
            # Determine status
            field.status = self._determine_status(field)
            
            results[field_name] = field
            
            logger.debug(
                "Field %s: AI=%.2f, Val=%.2f, Final=%.2f, Status=%s",
                field_name, ai_confidence, validation_score, 
                field.final_confidence, field.status.value
            )
        
        return results
    
    def _determine_status(self, field: ExtractedField) -> ExtractionStatus:
        """Determine extraction status based on confidence and validation."""
        final = field.final_confidence
        
        # High confidence and no validation issues
        if final >= self.TRUSTED_THRESHOLD and not field.issues:
            return ExtractionStatus.TRUSTED
        
        # Medium confidence or minor issues
        if final >= self.REVIEW_THRESHOLD:
            return ExtractionStatus.REVIEW
        
        # Low confidence or major issues
        return ExtractionStatus.UNTRUSTED
    
    def _get_field_types(self, document_type: str) -> Dict[str, FieldType]:
        """Get expected field types for a document type."""
        lc_fields = {
            "lc_number": FieldType.LC_NUMBER,
            "documentary_credit_number": FieldType.LC_NUMBER,
            "lc_amount": FieldType.AMOUNT,
            "amount": FieldType.AMOUNT,
            "currency": FieldType.CURRENCY,
            "currency_code": FieldType.CURRENCY,
            "expiry_date": FieldType.DATE,
            "date_of_expiry": FieldType.DATE,
            "issue_date": FieldType.DATE,
            "latest_shipment_date": FieldType.DATE,
            "port_of_loading": FieldType.PORT,
            "port_of_discharge": FieldType.PORT,
            "place_of_destination": FieldType.PORT,
            "applicant": FieldType.PARTY_NAME,
            "applicant_name": FieldType.PARTY_NAME,
            "beneficiary": FieldType.PARTY_NAME,
            "beneficiary_name": FieldType.PARTY_NAME,
            "issuing_bank": FieldType.BANK_NAME,
            "advising_bank": FieldType.BANK_NAME,
            "issuing_bank_swift": FieldType.SWIFT_CODE,
            "advising_bank_swift": FieldType.SWIFT_CODE,
            "goods_description": FieldType.GOODS_DESCRIPTION,
            "goods": FieldType.GOODS_DESCRIPTION,
            "country_of_origin": FieldType.COUNTRY,
        }
        
        invoice_fields = {
            "invoice_number": FieldType.DOCUMENT_NUMBER,
            "invoice_date": FieldType.DATE,
            "invoice_amount": FieldType.AMOUNT,
            "amount": FieldType.AMOUNT,
            "currency": FieldType.CURRENCY,
            "lc_reference": FieldType.LC_NUMBER,
            "lc_number": FieldType.LC_NUMBER,
            "seller": FieldType.PARTY_NAME,
            "buyer": FieldType.PARTY_NAME,
            "goods_description": FieldType.GOODS_DESCRIPTION,
            "country_of_origin": FieldType.COUNTRY,
        }
        
        bl_fields = {
            "bl_number": FieldType.DOCUMENT_NUMBER,
            "bill_of_lading_number": FieldType.DOCUMENT_NUMBER,
            "shipper": FieldType.PARTY_NAME,
            "consignee": FieldType.PARTY_NAME,
            "notify_party": FieldType.PARTY_NAME,
            "port_of_loading": FieldType.PORT,
            "port_of_discharge": FieldType.PORT,
            "vessel_name": FieldType.TEXT,
            "shipped_on_board_date": FieldType.DATE,
            "goods_description": FieldType.GOODS_DESCRIPTION,
        }
        
        document_map = {
            "lc": lc_fields,
            "letter_of_credit": lc_fields,
            "invoice": invoice_fields,
            "commercial_invoice": invoice_fields,
            "bl": bl_fields,
            "bill_of_lading": bl_fields,
        }
        
        return document_map.get(document_type.lower(), {})
    
    def get_extraction_summary(
        self,
        fields: Dict[str, ExtractedField],
    ) -> Dict[str, Any]:
        """Get summary statistics for extraction results."""
        total = len(fields)
        if total == 0:
            return {"total": 0, "trusted": 0, "review": 0, "untrusted": 0}
        
        trusted = sum(1 for f in fields.values() if f.status == ExtractionStatus.TRUSTED)
        review = sum(1 for f in fields.values() if f.status == ExtractionStatus.REVIEW)
        untrusted = sum(1 for f in fields.values() if f.status == ExtractionStatus.UNTRUSTED)
        missing = sum(1 for f in fields.values() if f.status == ExtractionStatus.MISSING)
        
        avg_confidence = sum(f.final_confidence for f in fields.values()) / total
        
        return {
            "total": total,
            "trusted": trusted,
            "review": review,
            "untrusted": untrusted,
            "missing": missing,
            "trusted_rate": trusted / total,
            "avg_confidence": round(avg_confidence, 3),
            "needs_review": review > 0 or untrusted > 0,
        }


# Convenience function
def two_stage_extract(
    ai_results: Dict[str, Any],
    document_type: str = "unknown",
) -> Tuple[Dict[str, ExtractedField], Dict[str, Any]]:
    """
    Run two-stage extraction on AI results.
    
    Returns:
        (fields_dict, summary_dict)
    """
    extractor = TwoStageExtractor()
    fields = extractor.process(ai_results, document_type)
    summary = extractor.get_extraction_summary(fields)
    return fields, summary

