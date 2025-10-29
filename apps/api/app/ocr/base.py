"""
Base OCR adapter interface and models.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from uuid import UUID


@dataclass
class BoundingBox:
    """Bounding box coordinates for text elements."""
    x1: float
    y1: float
    x2: float
    y2: float
    page: int = 1


@dataclass
class OCRTextElement:
    """Individual text element extracted by OCR."""
    text: str
    confidence: float
    bounding_box: Optional[BoundingBox] = None
    element_type: str = "word"  # word, line, paragraph, etc.


@dataclass
class OCRResult:
    """Result from OCR processing."""
    document_id: UUID
    full_text: str
    overall_confidence: float
    elements: List[OCRTextElement]
    metadata: Dict[str, Any]
    processing_time_ms: int
    provider: str
    error: Optional[str] = None


class OCRAdapter(ABC):
    """Abstract base class for OCR adapters."""
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the OCR provider."""
        pass
    
    @abstractmethod
    async def process_document(
        self, 
        s3_bucket: str, 
        s3_key: str,
        document_id: UUID
    ) -> OCRResult:
        """
        Process a document and extract text.
        
        Args:
            s3_bucket: S3 bucket containing the document
            s3_key: S3 key of the document
            document_id: Unique identifier for the document
        
        Returns:
            OCRResult containing extracted text and metadata
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the OCR service is available."""
        pass