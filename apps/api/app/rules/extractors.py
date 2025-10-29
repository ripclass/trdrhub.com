"""
Field extraction utilities for different document types.
"""

import re
from datetime import datetime
from typing import Dict, List, Optional
from decimal import Decimal, InvalidOperation

from .models import ExtractedField, FieldType, DocumentType


class DocumentFieldExtractor:
    """Extracts structured fields from OCR text for different document types."""
    
    # Common patterns for field extraction
    DATE_PATTERNS = [
        r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b',  # MM/DD/YYYY or DD/MM/YYYY
        r'\b(\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{2,4})\b',
        r'\b(\d{2,4}[/-]\d{1,2}[/-]\d{1,2})\b',  # YYYY/MM/DD
    ]
    
    AMOUNT_PATTERNS = [
        r'(?:USD|US\$|\$)\s*([0-9,]+\.?\d*)',  # USD amounts
        r'([0-9,]+\.?\d*)\s*(?:USD|US\$|\$)',  # Amount followed by USD
        r'AMOUNT[:\s]*([0-9,]+\.?\d*)',  # Amount field
        r'TOTAL[:\s]*(?:USD|US\$|\$)?\s*([0-9,]+\.?\d*)',  # Total amount
    ]
    
    PORT_PATTERNS = [
        r'(?:PORT OF LOADING|POL)[:\s]*([A-Z][A-Za-z\s,]+)',
        r'(?:PORT OF DISCHARGE|POD)[:\s]*([A-Z][A-Za-z\s,]+)',
        r'(?:DESTINATION|DEST\.?)[:\s]*([A-Z][A-Za-z\s,]+)',
    ]
    
    def extract_fields(
        self, 
        ocr_text: str, 
        document_type: DocumentType,
        confidence: float = 0.8
    ) -> List[ExtractedField]:
        """
        Extract structured fields from OCR text based on document type.
        
        Args:
            ocr_text: Raw OCR text from document
            document_type: Type of document (LC, Invoice, BL)
            confidence: Overall OCR confidence score
            
        Returns:
            List of extracted fields
        """
        fields = []
        
        if document_type == DocumentType.LETTER_OF_CREDIT:
            fields.extend(self._extract_lc_fields(ocr_text, confidence))
        elif document_type == DocumentType.COMMERCIAL_INVOICE:
            fields.extend(self._extract_invoice_fields(ocr_text, confidence))
        elif document_type == DocumentType.BILL_OF_LADING:
            fields.extend(self._extract_bl_fields(ocr_text, confidence))
        
        return fields
    
    def _extract_lc_fields(self, text: str, confidence: float) -> List[ExtractedField]:
        """Extract fields specific to Letter of Credit."""
        fields = []
        
        # LC Number
        lc_number = self._extract_pattern(text, r'(?:L/C|LC)\s*(?:NO\.?|NUMBER)[:\s]*([A-Z0-9-]+)', 1)
        if lc_number:
            fields.append(ExtractedField(
                field_name="lc_number",
                field_type=FieldType.TEXT,
                value=lc_number,
                confidence=confidence,
                document_type=DocumentType.LETTER_OF_CREDIT,
                raw_text=lc_number
            ))
        
        # Issue Date
        issue_date = self._extract_date_field(text, r'(?:ISSUE DATE|DATE OF ISSUE)[:\s]*([^\n]+)')
        if issue_date:
            fields.append(ExtractedField(
                field_name="issue_date",
                field_type=FieldType.DATE,
                value=issue_date,
                confidence=confidence,
                document_type=DocumentType.LETTER_OF_CREDIT
            ))
        
        # Expiry Date
        expiry_date = self._extract_date_field(text, r'(?:EXPIRY DATE|EXPIRY)[:\s]*([^\n]+)')
        if expiry_date:
            fields.append(ExtractedField(
                field_name="expiry_date",
                field_type=FieldType.DATE,
                value=expiry_date,
                confidence=confidence,
                document_type=DocumentType.LETTER_OF_CREDIT
            ))
        
        # LC Amount
        lc_amount = self._extract_amount_field(text)
        if lc_amount:
            fields.append(ExtractedField(
                field_name="lc_amount",
                field_type=FieldType.AMOUNT,
                value=lc_amount,
                confidence=confidence,
                document_type=DocumentType.LETTER_OF_CREDIT
            ))
        
        # Applicant (Buyer)
        applicant = self._extract_pattern(text, r'(?:APPLICANT|BUYER)[:\s]*([^\n]+)', 1)
        if applicant:
            fields.append(ExtractedField(
                field_name="applicant",
                field_type=FieldType.PARTY,
                value=applicant.strip(),
                confidence=confidence,
                document_type=DocumentType.LETTER_OF_CREDIT
            ))
        
        # Beneficiary (Seller)
        beneficiary = self._extract_pattern(text, r'(?:BENEFICIARY|SELLER)[:\s]*([^\n]+)', 1)
        if beneficiary:
            fields.append(ExtractedField(
                field_name="beneficiary",
                field_type=FieldType.PARTY,
                value=beneficiary.strip(),
                confidence=confidence,
                document_type=DocumentType.LETTER_OF_CREDIT
            ))
        
        # Port of Loading
        pol = self._extract_port_field(text, r'(?:PORT OF LOADING|POL)[:\s]*([^\n]+)')
        if pol:
            fields.append(ExtractedField(
                field_name="port_of_loading",
                field_type=FieldType.PORT,
                value=pol,
                confidence=confidence,
                document_type=DocumentType.LETTER_OF_CREDIT
            ))
        
        # Port of Discharge
        pod = self._extract_port_field(text, r'(?:PORT OF DISCHARGE|POD)[:\s]*([^\n]+)')
        if pod:
            fields.append(ExtractedField(
                field_name="port_of_discharge",
                field_type=FieldType.PORT,
                value=pod,
                confidence=confidence,
                document_type=DocumentType.LETTER_OF_CREDIT
            ))
        
        return fields
    
    def _extract_invoice_fields(self, text: str, confidence: float) -> List[ExtractedField]:
        """Extract fields specific to Commercial Invoice."""
        fields = []
        
        # Invoice Number
        invoice_number = self._extract_pattern(text, r'(?:INVOICE|INV\.?)\s*(?:NO\.?|NUMBER)[:\s]*([A-Z0-9-]+)', 1)
        if invoice_number:
            fields.append(ExtractedField(
                field_name="invoice_number",
                field_type=FieldType.TEXT,
                value=invoice_number,
                confidence=confidence,
                document_type=DocumentType.COMMERCIAL_INVOICE
            ))
        
        # Invoice Date
        invoice_date = self._extract_date_field(text, r'(?:INVOICE DATE|DATE)[:\s]*([^\n]+)')
        if invoice_date:
            fields.append(ExtractedField(
                field_name="invoice_date",
                field_type=FieldType.DATE,
                value=invoice_date,
                confidence=confidence,
                document_type=DocumentType.COMMERCIAL_INVOICE
            ))
        
        # Invoice Amount
        invoice_amount = self._extract_amount_field(text)
        if invoice_amount:
            fields.append(ExtractedField(
                field_name="invoice_amount",
                field_type=FieldType.AMOUNT,
                value=invoice_amount,
                confidence=confidence,
                document_type=DocumentType.COMMERCIAL_INVOICE
            ))
        
        # Consignee
        consignee = self._extract_pattern(text, r'(?:CONSIGNEE|SHIP TO)[:\s]*([^\n]+)', 1)
        if consignee:
            fields.append(ExtractedField(
                field_name="consignee",
                field_type=FieldType.PARTY,
                value=consignee.strip(),
                confidence=confidence,
                document_type=DocumentType.COMMERCIAL_INVOICE
            ))
        
        return fields
    
    def _extract_bl_fields(self, text: str, confidence: float) -> List[ExtractedField]:
        """Extract fields specific to Bill of Lading."""
        fields = []
        
        # B/L Number
        bl_number = self._extract_pattern(text, r'(?:B/L|BILL OF LADING)\s*(?:NO\.?|NUMBER)[:\s]*([A-Z0-9-]+)', 1)
        if bl_number:
            fields.append(ExtractedField(
                field_name="bl_number",
                field_type=FieldType.TEXT,
                value=bl_number,
                confidence=confidence,
                document_type=DocumentType.BILL_OF_LADING
            ))
        
        # B/L Date
        bl_date = self._extract_date_field(text, r'(?:B/L DATE|DATE)[:\s]*([^\n]+)')
        if bl_date:
            fields.append(ExtractedField(
                field_name="bl_date",
                field_type=FieldType.DATE,
                value=bl_date,
                confidence=confidence,
                document_type=DocumentType.BILL_OF_LADING
            ))
        
        # Shipper
        shipper = self._extract_pattern(text, r'(?:SHIPPER)[:\s]*([^\n]+)', 1)
        if shipper:
            fields.append(ExtractedField(
                field_name="shipper",
                field_type=FieldType.PARTY,
                value=shipper.strip(),
                confidence=confidence,
                document_type=DocumentType.BILL_OF_LADING
            ))
        
        # Consignee
        consignee = self._extract_pattern(text, r'(?:CONSIGNEE)[:\s]*([^\n]+)', 1)
        if consignee:
            fields.append(ExtractedField(
                field_name="consignee",
                field_type=FieldType.PARTY,
                value=consignee.strip(),
                confidence=confidence,
                document_type=DocumentType.BILL_OF_LADING
            ))
        
        # Port of Loading
        pol = self._extract_port_field(text, r'(?:PORT OF LOADING|POL)[:\s]*([^\n]+)')
        if pol:
            fields.append(ExtractedField(
                field_name="port_of_loading",
                field_type=FieldType.PORT,
                value=pol,
                confidence=confidence,
                document_type=DocumentType.BILL_OF_LADING
            ))
        
        # Port of Discharge
        pod = self._extract_port_field(text, r'(?:PORT OF DISCHARGE|POD)[:\s]*([^\n]+)')
        if pod:
            fields.append(ExtractedField(
                field_name="port_of_discharge",
                field_type=FieldType.PORT,
                value=pod,
                confidence=confidence,
                document_type=DocumentType.BILL_OF_LADING
            ))
        
        return fields
    
    def _extract_pattern(self, text: str, pattern: str, group: int = 0) -> Optional[str]:
        """Extract text using regex pattern."""
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(group).strip()
        return None
    
    def _extract_date_field(self, text: str, specific_pattern: str = None) -> Optional[str]:
        """Extract and normalize date field."""
        patterns = [specific_pattern] if specific_pattern else []
        patterns.extend(self.DATE_PATTERNS)
        
        for pattern in patterns:
            if pattern:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    date_str = match.group(1).strip()
                    # Basic date normalization - could be enhanced
                    return date_str
        
        return None
    
    def _extract_amount_field(self, text: str) -> Optional[str]:
        """Extract and normalize amount field."""
        for pattern in self.AMOUNT_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(',', '')
                try:
                    # Validate it's a valid decimal
                    Decimal(amount_str)
                    return amount_str
                except InvalidOperation:
                    continue
        
        return None
    
    def _extract_port_field(self, text: str, specific_pattern: str = None) -> Optional[str]:
        """Extract port field."""
        patterns = [specific_pattern] if specific_pattern else []
        patterns.extend(self.PORT_PATTERNS)
        
        for pattern in patterns:
            if pattern:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    port_str = match.group(1).strip()
                    # Basic port name cleanup
                    return port_str
        
        return None