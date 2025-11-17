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
    
    LABEL_BREAK_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9\s/()\-]{2,}[:：]")

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
        elif document_type == DocumentType.PACKING_LIST:
            fields.extend(self._extract_packing_list_fields(ocr_text, confidence))
        elif document_type == DocumentType.CERTIFICATE_OF_ORIGIN:
            fields.extend(self._extract_certificate_of_origin_fields(ocr_text, confidence))
        elif document_type == DocumentType.INSURANCE_CERTIFICATE:
            fields.extend(self._extract_insurance_certificate_fields(ocr_text, confidence))
        elif document_type == DocumentType.INSPECTION_CERTIFICATE:
            fields.extend(self._extract_inspection_certificate_fields(ocr_text, confidence))
        
        return fields
    
    def _extract_lc_fields(self, text: str, confidence: float) -> List[ExtractedField]:
        """Extract fields specific to Letter of Credit."""
        fields = []
        
        # LC Number
        lc_number = self._extract_pattern(text, r'(?:L/C|LC)\s*(?:NO\.?|NUMBER)[:\s]*([A-Z0-9\-\/]+)', 1)
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
        applicant = self._extract_pattern(text, r'(?:APPLICANT|BUYER|IMPORTER)[:\s]*([^\n]+)', 1)
        if applicant:
            fields.append(ExtractedField(
                field_name="applicant",
                field_type=FieldType.PARTY,
                value=applicant.strip(),
                confidence=confidence,
                document_type=DocumentType.LETTER_OF_CREDIT
            ))
        
        # Beneficiary (Seller)
        beneficiary = self._extract_pattern(text, r'(?:BENEFICIARY|SELLER|EXPORTER)[:\s]*([^\n]+)', 1)
        if beneficiary:
            fields.append(ExtractedField(
                field_name="beneficiary",
                field_type=FieldType.PARTY,
                value=beneficiary.strip(),
                confidence=confidence,
                document_type=DocumentType.LETTER_OF_CREDIT
            ))
        
        # Goods description
        goods_description = self._extract_label_block(
            text,
            [
                r'(?:DESCRIPTION OF GOODS|GOODS DESCRIPTION|MERCHANDISE)[:\s]*(.+)',
                r'(?:GOODS|PRODUCTS)[:\s]*(.+)'
            ]
        )
        if goods_description:
            fields.append(ExtractedField(
                field_name="goods_description",
                field_type=FieldType.TEXT,
                value=goods_description,
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
        lines = [line.strip() for line in text.splitlines()]
        
        invoice_number = self._extract_label_value(
            text,
            lines,
            label_patterns=[
                r'(?:INVOICE|INV\.?)\s*(?:NO\.?|NUMBER)',
                r'INVOICE\s*#'
            ],
            inline_capture=r'(?:INVOICE|INV\.?)\s*(?:NO\.?|NUMBER)\s*[:\-]?\s*([A-Z0-9-]+)'
        )
        if invoice_number:
            fields.append(ExtractedField(
                field_name="invoice_number",
                field_type=FieldType.TEXT,
                value=invoice_number,
                confidence=confidence,
                document_type=DocumentType.COMMERCIAL_INVOICE
            ))
        
        invoice_date = self._extract_label_value(
            text,
            lines,
            label_patterns=[
                r'INVOICE\s+DATE',
                r'DATE'
            ],
            inline_capture=r'(?:INVOICE\s+DATE|DATE)\s*[:\-]?\s*([0-9A-Za-z ,./-]+)'
        )
        if invoice_date:
            fields.append(ExtractedField(
                field_name="invoice_date",
                field_type=FieldType.DATE,
                value=invoice_date,
                confidence=confidence,
                document_type=DocumentType.COMMERCIAL_INVOICE
            ))
        else:
            invoice_date_field = self._extract_date_field(text, r'(?:INVOICE DATE|DATE)[:\s]*([^\n]+)')
            if invoice_date_field:
                fields.append(ExtractedField(
                    field_name="invoice_date",
                    field_type=FieldType.DATE,
                    value=invoice_date_field,
                    confidence=confidence,
                    document_type=DocumentType.COMMERCIAL_INVOICE
                ))

        invoice_amount = self._extract_label_value(
            text,
            lines,
            label_patterns=[
                r'(?:TOTAL|INVOICE)\s+AMOUNT',
                r'AMOUNT\s+DUE',
                r'TOTAL\s+\(FOR TESTING\)'
            ],
            inline_capture=r'(?:TOTAL|INVOICE)\s+AMOUNT\s*[:\-]?\s*([0-9,.\sA-Za-z]+)'
        )
        if not invoice_amount:
            invoice_amount = self._extract_amount_field(text)
        if invoice_amount:
            invoice_amount = self._normalize_amount_string(invoice_amount)
        if invoice_amount:
            fields.append(ExtractedField(
                field_name="invoice_amount",
                field_type=FieldType.AMOUNT,
                value=invoice_amount,
                confidence=confidence,
                document_type=DocumentType.COMMERCIAL_INVOICE
            ))
        
        consignee = self._extract_label_value(
            text,
            lines,
            label_patterns=[
                r'CONSIGNEE',
                r'SHIP\s+TO'
            ]
        )
        if consignee:
            fields.append(ExtractedField(
                field_name="consignee",
                field_type=FieldType.PARTY,
                value=consignee.strip(),
                confidence=confidence,
                document_type=DocumentType.COMMERCIAL_INVOICE
            ))
        
        buyer = self._extract_label_value(
            text,
            lines,
            label_patterns=[
                r'(?:BUYER|IMPORTER|APPLICANT)',
                r'BUYER\s*\(APPLICANT\)'
            ]
        )
        if buyer:
            fields.append(ExtractedField(
                field_name="buyer",
                field_type=FieldType.PARTY,
                value=buyer.strip(),
                confidence=confidence,
                document_type=DocumentType.COMMERCIAL_INVOICE
            ))
        
        product_description = self._extract_label_block(
            text,
            [
                r'(?:DESCRIPTION|GOODS DESCRIPTION|PRODUCT DESCRIPTION)[:\s]*(.+)',
                r'(?:LINE\s+ITEMS|ITEMS)[:\s]*(.+)'
            ]
        )
        if product_description:
            fields.append(ExtractedField(
                field_name="product_description",
                field_type=FieldType.TEXT,
                value=product_description,
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

    def _extract_packing_list_fields(self, text: str, confidence: float) -> List[ExtractedField]:
        fields = []
        total_packages = self._extract_pattern(text, r'(?:TOTAL\s+PACKAGES|NO\.?\s+OF\s+PACKAGES|PACKAGES)[:\s]*([^\n]+)', 1)
        if total_packages:
            fields.append(ExtractedField(
                field_name="total_packages",
                field_type=FieldType.TEXT,
                value=total_packages.strip(),
                confidence=confidence,
                document_type=DocumentType.PACKING_LIST,
            ))

        gross_weight = self._extract_pattern(text, r'(?:GROSS\s+WEIGHT|G\.W\.)[:\s]*([^\n]+)', 1)
        if gross_weight:
            fields.append(ExtractedField(
                field_name="gross_weight",
                field_type=FieldType.TEXT,
                value=gross_weight.strip(),
                confidence=confidence,
                document_type=DocumentType.PACKING_LIST,
            ))

        net_weight = self._extract_pattern(text, r'(?:NET\s+WEIGHT|N\.W\.)[:\s]*([^\n]+)', 1)
        if net_weight:
            fields.append(ExtractedField(
                field_name="net_weight",
                field_type=FieldType.TEXT,
                value=net_weight.strip(),
                confidence=confidence,
                document_type=DocumentType.PACKING_LIST,
            ))

        dimensions = self._extract_pattern(text, r'(?:DIMENSIONS|MEASUREMENTS)[:\s]*([^\n]+)', 1)
        if dimensions:
            fields.append(ExtractedField(
                field_name="dimensions",
                field_type=FieldType.TEXT,
                value=dimensions.strip(),
                confidence=confidence,
                document_type=DocumentType.PACKING_LIST,
            ))

        return fields

    def _extract_certificate_of_origin_fields(self, text: str, confidence: float) -> List[ExtractedField]:
        fields = []
        certificate_number = self._extract_pattern(text, r'(?:CERTIFICATE\s+NO\.?|CERTIFICATE\s+NUMBER)[:\s]*([^\n]+)', 1)
        if certificate_number:
            fields.append(ExtractedField(
                field_name="certificate_number",
                field_type=FieldType.TEXT,
                value=certificate_number.strip(),
                confidence=confidence,
                document_type=DocumentType.CERTIFICATE_OF_ORIGIN,
            ))

        origin_country = self._extract_pattern(text, r'(?:COUNTRY\s+OF\s+ORIGIN|ORIGIN)[:\s]*([^\n]+)', 1)
        if origin_country:
            fields.append(ExtractedField(
                field_name="origin_country",
                field_type=FieldType.TEXT,
                value=origin_country.strip(),
                confidence=confidence,
                document_type=DocumentType.CERTIFICATE_OF_ORIGIN,
            ))

        issuing_authority = self._extract_pattern(text, r'(?:ISSUED\s+BY|CHAMBER\s+OF\s+COMMERCE)[:\s]*([^\n]+)', 1)
        if issuing_authority:
            fields.append(ExtractedField(
                field_name="issuing_authority",
                field_type=FieldType.TEXT,
                value=issuing_authority.strip(),
                confidence=confidence,
                document_type=DocumentType.CERTIFICATE_OF_ORIGIN,
            ))

        issue_date = self._extract_date_field(text, r'(?:DATE\s+OF\s+ISSUE|ISSUE\s+DATE)[:\s]*([^\n]+)')
        if issue_date:
            fields.append(ExtractedField(
                field_name="issue_date",
                field_type=FieldType.DATE,
                value=issue_date,
                confidence=confidence,
                document_type=DocumentType.CERTIFICATE_OF_ORIGIN,
            ))

        return fields

    def _extract_insurance_certificate_fields(self, text: str, confidence: float) -> List[ExtractedField]:
        fields = []
        policy_number = self._extract_pattern(text, r'(?:POLICY\s+NO\.?|POLICY\s+NUMBER)[:\s]*([^\n]+)', 1)
        if policy_number:
            fields.append(ExtractedField(
                field_name="policy_number",
                field_type=FieldType.TEXT,
                value=policy_number.strip(),
                confidence=confidence,
                document_type=DocumentType.INSURANCE_CERTIFICATE,
            ))

        insured_amount = self._extract_amount_field(text)
        if insured_amount:
            fields.append(ExtractedField(
                field_name="insured_amount",
                field_type=FieldType.AMOUNT,
                value=self._normalize_amount_string(insured_amount),
                confidence=confidence,
                document_type=DocumentType.INSURANCE_CERTIFICATE,
            ))

        insurer = self._extract_pattern(text, r'(?:INSURER|UNDERWRITER|INSURANCE\s+COMPANY)[:\s]*([^\n]+)', 1)
        if insurer:
            fields.append(ExtractedField(
                field_name="insurer",
                field_type=FieldType.TEXT,
                value=insurer.strip(),
                confidence=confidence,
                document_type=DocumentType.INSURANCE_CERTIFICATE,
            ))

        validity = self._extract_date_field(text, r'(?:VALID\s+UNTIL|EXPIRY\s+DATE)[:\s]*([^\n]+)')
        if validity:
            fields.append(ExtractedField(
                field_name="valid_until",
                field_type=FieldType.DATE,
                value=validity,
                confidence=confidence,
                document_type=DocumentType.INSURANCE_CERTIFICATE,
            ))

        return fields

    def _extract_inspection_certificate_fields(self, text: str, confidence: float) -> List[ExtractedField]:
        fields = []
        inspector = self._extract_pattern(text, r'(?:INSPECTION\s+COMPANY|AGENCY|INSPECTOR)[:\s]*([^\n]+)', 1)
        if inspector:
            fields.append(ExtractedField(
                field_name="inspection_company",
                field_type=FieldType.TEXT,
                value=inspector.strip(),
                confidence=confidence,
                document_type=DocumentType.INSPECTION_CERTIFICATE,
            ))

        inspection_date = self._extract_date_field(text, r'(?:INSPECTION\s+DATE|DATE\s+OF\s+INSPECTION)[:\s]*([^\n]+)')
        if inspection_date:
            fields.append(ExtractedField(
                field_name="inspection_date",
                field_type=FieldType.DATE,
                value=inspection_date,
                confidence=confidence,
                document_type=DocumentType.INSPECTION_CERTIFICATE,
            ))

        findings = self._extract_label_block(text, [
            r'(?:FINDINGS|OBSERVATIONS|RESULTS)[:\s]*(.+)',
        ])
        if findings:
            fields.append(ExtractedField(
                field_name="inspection_results",
                field_type=FieldType.TEXT,
                value=findings,
                confidence=confidence,
                document_type=DocumentType.INSPECTION_CERTIFICATE,
            ))

        return fields
    
    def _extract_pattern(self, text: str, pattern: str, group: int = 0) -> Optional[str]:
        """Extract text using regex pattern."""
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(group).strip()
        return None
    
    def _extract_label_block(self, text: str, patterns: List[str]) -> Optional[str]:
        """Extract multi-line block following a label."""
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                captured = match.group(1).strip()
                if captured:
                    # If captured contains another label, trim
                    lines = captured.splitlines()
                    cleaned_lines = []
                    for line in lines:
                        stripped = line.strip()
                        if not stripped:
                            break
                        if self.LABEL_BREAK_PATTERN.match(stripped):
                            break
                        cleaned_lines.append(stripped)
                    if cleaned_lines:
                        return " ".join(cleaned_lines)
                # Fallback to next line
                end = match.end()
                remainder = text[end:].splitlines()
                for line in remainder:
                    stripped = line.strip()
                    if not stripped:
                        continue
                    if self.LABEL_BREAK_PATTERN.match(stripped):
                        break
                    return stripped
        return None

    def _extract_label_value(
        self,
        text: str,
        lines: List[str],
        label_patterns: List[str],
        inline_capture: Optional[str] = None,
    ) -> Optional[str]:
        """
        Extract value that might appear on the same line as a label or on the next non-empty line.
        This helps with table-based invoices where labels and values are on separate lines.
        """
        if inline_capture:
            match = re.search(inline_capture, text, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                if value:
                    return value

        for i, line in enumerate(lines):
            for pattern in label_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    match_inline = re.search(pattern + r'\s*[:\-]?\s*(.+)$', line, re.IGNORECASE)
                    if match_inline:
                        inline_value = match_inline.group(1).strip()
                        if inline_value:
                            return inline_value
                    for j in range(i + 1, min(i + 6, len(lines))):
                        candidate = lines[j].strip()
                        if candidate:
                            return candidate
        return None

    def _normalize_amount_string(self, raw_value: str) -> str:
        """Normalize amount strings like '167,176.20 USD' -> '167176.20'."""
        cleaned = raw_value.replace("USD", "").replace(",", " ").strip()
        match = re.search(r'([0-9]+(?:[., ][0-9]+)?)', cleaned)
        if match:
            numeric = match.group(1).replace(" ", "").replace(",", "")
            return numeric
        return raw_value.strip()
    
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
