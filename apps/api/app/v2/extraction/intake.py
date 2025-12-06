"""
Document Intake and Classification

Stage 1 of the V2 pipeline.
Target: <2 seconds for up to 10 documents
"""

import asyncio
import logging
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple
from io import BytesIO

from ..core.types import DocumentType, DocumentQuality

logger = logging.getLogger(__name__)

# Document type priority (LC first, then supporting docs)
DOC_PRIORITY = {
    DocumentType.LETTER_OF_CREDIT: 1,
    DocumentType.MT700: 1,
    DocumentType.COMMERCIAL_INVOICE: 2,
    DocumentType.BILL_OF_LADING: 3,
    DocumentType.PACKING_LIST: 4,
    DocumentType.INSURANCE_CERTIFICATE: 5,
    DocumentType.CERTIFICATE_OF_ORIGIN: 6,
    DocumentType.INSPECTION_CERTIFICATE: 7,
    DocumentType.WEIGHT_CERTIFICATE: 8,
    DocumentType.FUMIGATION_CERTIFICATE: 9,
    DocumentType.PHYTOSANITARY_CERTIFICATE: 10,
    DocumentType.BENEFICIARY_CERTIFICATE: 11,
    DocumentType.DRAFT: 12,
    DocumentType.UNKNOWN: 99,
}


@dataclass
class UploadedDocument:
    """Raw uploaded document."""
    file_data: bytes
    filename: str
    content_type: str
    size: int


@dataclass
class ClassifiedDocument:
    """Classified document with metadata."""
    id: str
    file_data: bytes
    filename: str
    content_type: str
    size: int
    
    document_type: DocumentType
    type_confidence: float
    priority: int
    estimated_pages: int
    quality_hint: DocumentQuality
    
    # Classification hints
    filename_hint: Optional[DocumentType]
    layout_hint: Optional[str]


class DocumentIntake:
    """
    Document intake and classification.
    
    Quickly classifies documents and assigns priorities
    for the processing pipeline.
    """
    
    MAX_DOCUMENTS = 10
    
    # Filename patterns for quick classification
    FILENAME_PATTERNS = {
        DocumentType.LETTER_OF_CREDIT: [
            r'lc[-_\s]?', r'letter[-_\s]?of[-_\s]?credit', r'mt[-_]?700',
            r'documentary[-_\s]?credit', r'l/c'
        ],
        DocumentType.MT700: [
            r'mt[-_]?700', r'swift'
        ],
        DocumentType.COMMERCIAL_INVOICE: [
            r'invoice', r'inv[-_]?', r'commercial[-_\s]?invoice', r'ci[-_]?'
        ],
        DocumentType.BILL_OF_LADING: [
            r'bl[-_]?', r'bill[-_\s]?of[-_\s]?lading', r'b/l', r'bol'
        ],
        DocumentType.PACKING_LIST: [
            r'packing[-_\s]?list', r'pl[-_]?', r'pack[-_]?list'
        ],
        DocumentType.INSURANCE_CERTIFICATE: [
            r'insurance', r'ins[-_]?cert', r'policy'
        ],
        DocumentType.CERTIFICATE_OF_ORIGIN: [
            r'coo[-_]?', r'origin', r'certificate[-_\s]?of[-_\s]?origin', r'c/o'
        ],
        DocumentType.INSPECTION_CERTIFICATE: [
            r'inspection', r'survey', r'quality[-_\s]?cert'
        ],
        DocumentType.WEIGHT_CERTIFICATE: [
            r'weight', r'weighment'
        ],
        DocumentType.DRAFT: [
            r'draft', r'bill[-_\s]?of[-_\s]?exchange'
        ],
    }
    
    # Text patterns for classification
    TEXT_PATTERNS = {
        DocumentType.LETTER_OF_CREDIT: [
            r'DOCUMENTARY CREDIT', r'FORM OF DOCUMENTARY CREDIT',
            r'IRREVOCABLE', r'UCP 600', r'BENEFICIARY', r'APPLICANT',
            r'ISSUING BANK', r'ADVISING BANK', r':40[A-E]:', r':20:',
        ],
        DocumentType.MT700: [
            r':27:', r':40[A-E]:', r':31C:', r':32B:', r':41[AD]:',
            r':42[ACMP]:', r':43[PT]:', r':44[A-L]:', r':45A:',
        ],
        DocumentType.COMMERCIAL_INVOICE: [
            r'INVOICE', r'COMMERCIAL INVOICE', r'TAX INVOICE',
            r'INVOICE NO', r'INVOICE DATE', r'SUBTOTAL', r'TOTAL',
        ],
        DocumentType.BILL_OF_LADING: [
            r'BILL OF LADING', r'B/L', r'SHIPPER', r'CONSIGNEE',
            r'NOTIFY PARTY', r'PORT OF LOADING', r'PORT OF DISCHARGE',
            r'VESSEL', r'VOYAGE', r'CONTAINER',
        ],
        DocumentType.PACKING_LIST: [
            r'PACKING LIST', r'CARTON', r'NET WEIGHT', r'GROSS WEIGHT',
            r'DIMENSIONS', r'CBM', r'PACKAGE',
        ],
        DocumentType.INSURANCE_CERTIFICATE: [
            r'INSURANCE', r'POLICY', r'INSURED VALUE', r'COVERAGE',
            r'PREMIUM', r'CLAIMS', r'110%',
        ],
        DocumentType.CERTIFICATE_OF_ORIGIN: [
            r'CERTIFICATE OF ORIGIN', r'ORIGIN', r'COUNTRY OF ORIGIN',
            r'MANUFACTURER', r'PRODUCED IN', r'MADE IN',
        ],
    }
    
    async def intake(
        self, 
        files: List[UploadedDocument]
    ) -> List[ClassifiedDocument]:
        """
        Intake and classify up to 10 documents.
        
        Args:
            files: List of uploaded documents
            
        Returns:
            List of classified documents sorted by priority
        """
        if len(files) > self.MAX_DOCUMENTS:
            raise ValueError(f"Maximum {self.MAX_DOCUMENTS} documents allowed, got {len(files)}")
        
        if not files:
            return []
        
        logger.info(f"Intake: Processing {len(files)} documents")
        
        # Classify all documents in parallel
        classified = await asyncio.gather(*[
            self._classify_document(doc, idx)
            for idx, doc in enumerate(files)
        ])
        
        # Sort by priority (LC first)
        classified.sort(key=lambda d: d.priority)
        
        logger.info(
            "Intake complete: %s",
            [(d.filename, d.document_type.value, d.type_confidence) for d in classified]
        )
        
        return classified
    
    async def _classify_document(
        self, 
        doc: UploadedDocument,
        index: int
    ) -> ClassifiedDocument:
        """Classify a single document."""
        import uuid
        
        doc_id = str(uuid.uuid4())[:8]
        
        # Quick classification using multiple signals
        filename_hint = self._classify_by_filename(doc.filename)
        
        # Get first page text for classification (lightweight OCR)
        first_page_text = await self._quick_ocr(doc.file_data)
        text_classification = self._classify_by_text(first_page_text)
        
        # Combine signals
        if filename_hint and text_classification and filename_hint == text_classification[0]:
            # Filename and text agree
            doc_type = filename_hint
            confidence = min(0.95, text_classification[1] + 0.1)
        elif text_classification:
            # Prefer text classification
            doc_type = text_classification[0]
            confidence = text_classification[1]
        elif filename_hint:
            # Fallback to filename
            doc_type = filename_hint
            confidence = 0.6
        else:
            doc_type = DocumentType.UNKNOWN
            confidence = 0.0
        
        # Estimate quality from first page text
        quality_hint = self._estimate_quality(first_page_text)
        
        # Estimate page count
        estimated_pages = max(1, doc.size // 50000)  # ~50KB per page
        
        return ClassifiedDocument(
            id=doc_id,
            file_data=doc.file_data,
            filename=doc.filename,
            content_type=doc.content_type,
            size=doc.size,
            document_type=doc_type,
            type_confidence=confidence,
            priority=DOC_PRIORITY.get(doc_type, 99),
            estimated_pages=estimated_pages,
            quality_hint=quality_hint,
            filename_hint=filename_hint,
            layout_hint=None,
        )
    
    def _classify_by_filename(self, filename: str) -> Optional[DocumentType]:
        """Classify document by filename patterns."""
        filename_lower = filename.lower()
        
        for doc_type, patterns in self.FILENAME_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, filename_lower, re.IGNORECASE):
                    return doc_type
        
        return None
    
    def _classify_by_text(
        self, 
        text: str
    ) -> Optional[Tuple[DocumentType, float]]:
        """Classify document by text content."""
        if not text:
            return None
        
        text_upper = text.upper()
        scores = {}
        
        for doc_type, patterns in self.TEXT_PATTERNS.items():
            matches = 0
            for pattern in patterns:
                if re.search(pattern, text_upper):
                    matches += 1
            
            if matches > 0:
                # Calculate score based on pattern matches
                score = min(0.9, 0.3 + (matches / len(patterns)) * 0.6)
                scores[doc_type] = score
        
        if not scores:
            return None
        
        # Return highest scoring type
        best_type = max(scores, key=scores.get)
        return (best_type, scores[best_type])
    
    def _estimate_quality(self, text: str) -> DocumentQuality:
        """Estimate document quality from OCR text."""
        if not text:
            return DocumentQuality.POOR
        
        # Count recognizable words vs garbage
        words = text.split()
        if not words:
            return DocumentQuality.VERY_POOR
        
        # Simple heuristic: ratio of dictionary-like words
        recognizable = sum(1 for w in words if len(w) > 2 and w.isalpha())
        ratio = recognizable / len(words)
        
        # Also check for common OCR errors
        garbage_patterns = [r'[^\x00-\x7F]{3,}', r'\d{10,}', r'[^a-zA-Z0-9\s]{5,}']
        garbage_count = sum(len(re.findall(p, text)) for p in garbage_patterns)
        
        if ratio > 0.8 and garbage_count < 5:
            return DocumentQuality.EXCELLENT
        elif ratio > 0.6 and garbage_count < 10:
            return DocumentQuality.GOOD
        elif ratio > 0.4:
            return DocumentQuality.MEDIUM
        elif ratio > 0.2:
            return DocumentQuality.POOR
        else:
            return DocumentQuality.VERY_POOR
    
    async def _quick_ocr(self, file_data: bytes) -> str:
        """
        Quick OCR of first page for classification.
        
        Uses low-resolution, fast processing.
        """
        try:
            # Try to extract text from PDF metadata or quick OCR
            # For now, return empty string - will be enhanced with actual OCR
            
            # Check if it's a PDF with extractable text
            if file_data[:4] == b'%PDF':
                # Try to extract text from PDF
                try:
                    from pdfminer.high_level import extract_text
                    text = extract_text(BytesIO(file_data), maxpages=1)
                    return text[:2000]  # First 2000 chars
                except Exception:
                    pass
            
            # For images or PDFs without text, would use actual OCR
            # This is a placeholder - actual implementation would use OCR
            return ""
            
        except Exception as e:
            logger.warning(f"Quick OCR failed: {e}")
            return ""

