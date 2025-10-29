"""
Main rules engine that orchestrates document validation.
"""

import time
from datetime import datetime, timezone
from typing import List, Dict, Any
from uuid import UUID

from sqlalchemy.orm import Session

from .models import DocumentValidationSummary, ValidationResult, FieldComparison
from .extractors import DocumentFieldExtractor
from .fatal_four import FatalFourValidator
from ..models import ValidationSession, Document, Discrepancy, DocumentType
from ..ocr.base import OCRResult


class RulesEngine:
    """Main rules engine for document validation."""
    
    def __init__(self, db: Session):
        self.db = db
        self.field_extractor = DocumentFieldExtractor()
        self.fatal_four_validator = FatalFourValidator()
    
    async def validate_session(self, session: ValidationSession) -> DocumentValidationSummary:
        """
        Validate all documents in a session and create discrepancy records.
        
        Args:
            session: The validation session to process
            
        Returns:
            DocumentValidationSummary with all validation results
        """
        start_time = time.time()
        
        # Get all documents for this session
        documents = self.db.query(Document).filter(
            Document.validation_session_id == session.id,
            Document.deleted_at.is_(None)
        ).all()
        
        if not documents:
            return self._create_empty_summary(session.id, start_time)
        
        # Group documents by type
        doc_dict = {doc.document_type: doc for doc in documents}
        
        # Extract fields from each document type
        lc_fields = []
        invoice_fields = []
        bl_fields = []
        
        if DocumentType.LETTER_OF_CREDIT.value in doc_dict:
            lc_doc = doc_dict[DocumentType.LETTER_OF_CREDIT.value]
            if lc_doc.ocr_text:
                lc_fields = self.field_extractor.extract_fields(
                    lc_doc.ocr_text,
                    DocumentType.LETTER_OF_CREDIT,
                    lc_doc.ocr_confidence or 0.8
                )
        
        if DocumentType.COMMERCIAL_INVOICE.value in doc_dict:
            invoice_doc = doc_dict[DocumentType.COMMERCIAL_INVOICE.value]
            if invoice_doc.ocr_text:
                invoice_fields = self.field_extractor.extract_fields(
                    invoice_doc.ocr_text,
                    DocumentType.COMMERCIAL_INVOICE,
                    invoice_doc.ocr_confidence or 0.8
                )
        
        if DocumentType.BILL_OF_LADING.value in doc_dict:
            bl_doc = doc_dict[DocumentType.BILL_OF_LADING.value]
            if bl_doc.ocr_text:
                bl_fields = self.field_extractor.extract_fields(
                    bl_doc.ocr_text,
                    DocumentType.BILL_OF_LADING,
                    bl_doc.ocr_confidence or 0.8
                )
        
        # Store extracted fields in documents
        self._update_document_extracted_fields(doc_dict, lc_fields, invoice_fields, bl_fields)
        
        # Run Fatal Four validation
        validation_results = self.fatal_four_validator.validate_documents(
            lc_fields, invoice_fields, bl_fields
        )
        
        # Create field comparisons for Cross-Check Matrix
        field_comparisons = self.fatal_four_validator.create_field_comparisons(
            lc_fields, invoice_fields, bl_fields
        )
        
        # Create discrepancy records for failed validations
        await self._create_discrepancy_records(session, validation_results)
        
        # Calculate summary statistics
        total_rules = len(validation_results)
        passed_rules = len([r for r in validation_results if r.status.value == "passed"])
        failed_rules = len([r for r in validation_results if r.status.value == "failed"])
        warnings = len([r for r in validation_results if r.status.value == "warning"])
        
        critical_issues = len([r for r in validation_results if r.rule.severity.value == "critical" and r.status.value == "failed"])
        major_issues = len([r for r in validation_results if r.rule.severity.value == "major" and r.status.value == "failed"])
        minor_issues = len([r for r in validation_results if r.rule.severity.value == "minor" and r.status.value == "failed"])
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return DocumentValidationSummary(
            session_id=session.id,
            total_rules=total_rules,
            passed_rules=passed_rules,
            failed_rules=failed_rules,
            warnings=warnings,
            critical_issues=critical_issues,
            major_issues=major_issues,
            minor_issues=minor_issues,
            validation_results=validation_results,
            field_comparisons=field_comparisons,
            processing_time_ms=processing_time,
            validated_at=datetime.now(timezone.utc)
        )
    
    def _create_empty_summary(self, session_id: UUID, start_time: float) -> DocumentValidationSummary:
        """Create empty validation summary when no documents found."""
        processing_time = int((time.time() - start_time) * 1000)
        
        return DocumentValidationSummary(
            session_id=session_id,
            total_rules=0,
            passed_rules=0,
            failed_rules=0,
            warnings=0,
            critical_issues=0,
            major_issues=0,
            minor_issues=0,
            validation_results=[],
            field_comparisons=[],
            processing_time_ms=processing_time,
            validated_at=datetime.now(timezone.utc)
        )
    
    def _update_document_extracted_fields(
        self,
        doc_dict: Dict[str, Document],
        lc_fields: List,
        invoice_fields: List,
        bl_fields: List
    ):
        """Update documents with extracted field data."""
        
        if DocumentType.LETTER_OF_CREDIT.value in doc_dict:
            doc = doc_dict[DocumentType.LETTER_OF_CREDIT.value]
            doc.extracted_fields = {
                "fields": [
                    {
                        "field_name": f.field_name,
                        "field_type": f.field_type.value,
                        "value": f.value,
                        "confidence": f.confidence
                    }
                    for f in lc_fields
                ],
                "extracted_at": datetime.now(timezone.utc).isoformat()
            }
        
        if DocumentType.COMMERCIAL_INVOICE.value in doc_dict:
            doc = doc_dict[DocumentType.COMMERCIAL_INVOICE.value]
            doc.extracted_fields = {
                "fields": [
                    {
                        "field_name": f.field_name,
                        "field_type": f.field_type.value,
                        "value": f.value,
                        "confidence": f.confidence
                    }
                    for f in invoice_fields
                ],
                "extracted_at": datetime.now(timezone.utc).isoformat()
            }
        
        if DocumentType.BILL_OF_LADING.value in doc_dict:
            doc = doc_dict[DocumentType.BILL_OF_LADING.value]
            doc.extracted_fields = {
                "fields": [
                    {
                        "field_name": f.field_name,
                        "field_type": f.field_type.value,
                        "value": f.value,
                        "confidence": f.confidence
                    }
                    for f in bl_fields
                ],
                "extracted_at": datetime.now(timezone.utc).isoformat()
            }
        
        # Commit the extracted fields to database
        self.db.commit()
    
    async def _create_discrepancy_records(
        self, 
        session: ValidationSession, 
        validation_results: List[ValidationResult]
    ):
        """Create database records for validation discrepancies."""
        
        for result in validation_results:
            if result.status.value == "failed":
                # Map validation result to discrepancy type
                discrepancy_type = self._map_to_discrepancy_type(result)
                
                discrepancy = Discrepancy(
                    validation_session_id=session.id,
                    discrepancy_type=discrepancy_type.value,
                    severity=result.rule.severity.value,
                    rule_name=result.rule.rule_name,
                    field_name=result.rule.field_type.value,
                    expected_value=result.expected_value,
                    actual_value=result.actual_value,
                    description=result.message,
                    source_document_types=[doc.value for doc in result.affected_documents]
                )
                
                self.db.add(discrepancy)
        
        # Commit all discrepancies
        self.db.commit()
    
    def _map_to_discrepancy_type(self, result: ValidationResult) -> Any:
        """Map validation result to discrepancy type."""
        from ..models import DiscrepancyType
        
        field_type = result.rule.field_type.value
        
        if field_type == "date":
            return DiscrepancyType.DATE_MISMATCH
        elif field_type == "amount":
            return DiscrepancyType.AMOUNT_MISMATCH
        elif field_type == "party":
            return DiscrepancyType.PARTY_MISMATCH
        elif field_type == "port":
            return DiscrepancyType.PORT_MISMATCH
        else:
            return DiscrepancyType.INVALID_FORMAT
    
    async def process_ocr_results(
        self, 
        session: ValidationSession,
        ocr_results: List[OCRResult]
    ):
        """Process OCR results and update document records."""
        
        for ocr_result in ocr_results:
            # Find the corresponding document
            document = self.db.query(Document).filter(
                Document.validation_session_id == session.id,
                Document.id == ocr_result.document_id
            ).first()
            
            if document:
                # Update document with OCR results
                document.ocr_text = ocr_result.full_text
                document.ocr_confidence = ocr_result.overall_confidence
                document.ocr_processed_at = datetime.now(timezone.utc)
        
        self.db.commit()