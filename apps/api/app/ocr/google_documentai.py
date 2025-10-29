"""
Google Document AI OCR adapter implementation.
"""

import os
import time
from typing import Dict, List, Any
from uuid import UUID

try:
    from google.cloud import documentai
    from google.cloud.exceptions import GoogleCloudError
except ImportError:
    # Mock Google Cloud imports for environments without credentials
    class GoogleCloudError(Exception):
        pass
    documentai = None

from .base import OCRAdapter, OCRResult, OCRTextElement, BoundingBox


class GoogleDocumentAIAdapter(OCRAdapter):
    """Google Document AI OCR adapter."""
    
    def __init__(self):
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = os.getenv("GOOGLE_DOCUMENTAI_LOCATION", "us")
        self.processor_id = os.getenv("GOOGLE_DOCUMENTAI_PROCESSOR_ID")
        
        if not all([self.project_id, self.processor_id]):
            raise ValueError("Google Document AI credentials not configured")
        
        self.client = documentai.DocumentProcessorServiceClient()
        self.processor_name = self.client.processor_path(
            self.project_id, self.location, self.processor_id
        )
    
    @property
    def provider_name(self) -> str:
        return "google_documentai"
    
    async def process_document(
        self, 
        s3_bucket: str, 
        s3_key: str,
        document_id: UUID
    ) -> OCRResult:
        """Process document using Google Document AI."""
        start_time = time.time()
        
        try:
            # Download document from S3
            import boto3
            s3_client = boto3.client('s3')
            
            # Get document content
            response = s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
            document_content = response['Body'].read()
            
            # Determine MIME type
            content_type = response.get('ContentType', 'application/pdf')
            if content_type.startswith('image/'):
                mime_type = content_type
            else:
                mime_type = 'application/pdf'
            
            # Create Document AI request
            raw_document = documentai.RawDocument(
                content=document_content,
                mime_type=mime_type
            )
            
            request = documentai.ProcessRequest(
                name=self.processor_name,
                raw_document=raw_document
            )
            
            # Process the document
            result = self.client.process_document(request=request)
            document = result.document
            
            # Extract text and elements
            full_text = document.text
            elements = []
            overall_confidence = 0.0
            confidence_sum = 0.0
            confidence_count = 0
            
            # Process pages and extract text elements
            for page_idx, page in enumerate(document.pages):
                # Process paragraphs
                for paragraph in page.paragraphs:
                    para_text = self._extract_text(document.text, paragraph.layout.text_anchor)
                    confidence = paragraph.layout.confidence
                    
                    if confidence > 0:
                        confidence_sum += confidence
                        confidence_count += 1
                    
                    # Get bounding box
                    bbox = None
                    if paragraph.layout.bounding_poly:
                        bbox = self._extract_bounding_box(
                            paragraph.layout.bounding_poly, 
                            page_idx + 1
                        )
                    
                    elements.append(OCRTextElement(
                        text=para_text,
                        confidence=confidence,
                        bounding_box=bbox,
                        element_type="paragraph"
                    ))
            
            # Calculate overall confidence
            if confidence_count > 0:
                overall_confidence = confidence_sum / confidence_count
            
            processing_time = int((time.time() - start_time) * 1000)
            
            return OCRResult(
                document_id=document_id,
                full_text=full_text,
                overall_confidence=overall_confidence,
                elements=elements,
                metadata={
                    "page_count": len(document.pages),
                    "mime_type": mime_type,
                    "processor_version": result.processor_version
                },
                processing_time_ms=processing_time,
                provider=self.provider_name
            )
            
        except GoogleCloudError as e:
            processing_time = int((time.time() - start_time) * 1000)
            return OCRResult(
                document_id=document_id,
                full_text="",
                overall_confidence=0.0,
                elements=[],
                metadata={"error_type": "GoogleCloudError"},
                processing_time_ms=processing_time,
                provider=self.provider_name,
                error=str(e)
            )
        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            return OCRResult(
                document_id=document_id,
                full_text="",
                overall_confidence=0.0,
                elements=[],
                metadata={"error_type": type(e).__name__},
                processing_time_ms=processing_time,
                provider=self.provider_name,
                error=str(e)
            )
    
    def _extract_text(self, document_text: str, text_anchor) -> str:
        """Extract text from document using text anchor."""
        if not text_anchor.text_segments:
            return ""
        
        text = ""
        for segment in text_anchor.text_segments:
            start_idx = int(segment.start_index) if segment.start_index else 0
            end_idx = int(segment.end_index) if segment.end_index else len(document_text)
            text += document_text[start_idx:end_idx]
        
        return text
    
    def _extract_bounding_box(self, bounding_poly, page: int) -> BoundingBox:
        """Extract bounding box from bounding polygon."""
        vertices = bounding_poly.vertices
        if not vertices:
            return BoundingBox(0, 0, 0, 0, page)
        
        x_coords = [v.x for v in vertices if hasattr(v, 'x')]
        y_coords = [v.y for v in vertices if hasattr(v, 'y')]
        
        if not x_coords or not y_coords:
            return BoundingBox(0, 0, 0, 0, page)
        
        return BoundingBox(
            x1=min(x_coords),
            y1=min(y_coords),
            x2=max(x_coords),
            y2=max(y_coords),
            page=page
        )
    
    async def health_check(self) -> bool:
        """Check Google Document AI service health."""
        try:
            # Test with a minimal request to check service availability
            # This is a placeholder - in production you might want to use
            # a dedicated health check processor or endpoint
            return True
        except Exception:
            return False