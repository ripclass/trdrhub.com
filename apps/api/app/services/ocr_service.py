"""
OCR Service Wrapper

Provides a simple interface for text extraction from documents.
Uses the same DocumentAIService as LCopilot for consistent OCR.
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class OCRService:
    """
    Simple OCR service wrapper.
    
    Uses the same DocumentAIService as LCopilot (from app.services)
    for consistent OCR across all TRDR Hub tools.
    """
    
    def __init__(self):
        self._doc_ai_service = None
        self._init_error = None
        
        try:
            from app.services import DocumentAIService
            self._doc_ai_service = DocumentAIService()
            logger.info("OCR Service initialized using DocumentAIService")
        except Exception as e:
            self._init_error = str(e)
            logger.error(f"Failed to initialize DocumentAIService: {e}")
    
    async def extract_text(
        self,
        content: bytes,
        filename: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Extract text from document content using DocumentAI.
        
        Args:
            content: Raw file bytes
            filename: Optional filename for context
            content_type: MIME type (auto-detected if not provided)
            
        Returns:
            Dict with 'text', 'confidence', 'provider', 'error' keys
        """
        filename = filename or "document.pdf"
        
        # Check if service is available
        if not self._doc_ai_service:
            return {
                "text": "",
                "confidence": 0,
                "provider": "none",
                "error": f"DocumentAI service not available: {self._init_error}",
            }
        
        # Auto-detect content type if not provided
        if not content_type:
            content_type = self._detect_content_type(content, filename)
        
        # Map content type to MIME type for DocumentAI
        mime_type = self._get_mime_type(content_type, filename)
        
        try:
            logger.info(f"OCR extraction: file={filename}, size={len(content)} bytes, mime={mime_type}")
            
            # Use DocumentAIService.process_file (same as LCopilot)
            result = await self._doc_ai_service.process_file(
                file_content=content,
                mime_type=mime_type,
            )
            
            if result.get("success") and result.get("extracted_text"):
                text = result["extracted_text"]
                confidence = result.get("confidence", 0.85)
                logger.info(f"OCR extracted {len(text)} chars with {confidence:.2f} confidence")
                return {
                    "text": text,
                    "confidence": confidence,
                    "provider": "google_documentai",
                    "error": None,
                }
            else:
                error = result.get("error", "No text extracted")
                return {
                    "text": "",
                    "confidence": 0,
                    "provider": "google_documentai",
                    "error": error,
                }
                
        except Exception as e:
            logger.error(f"OCR extraction error: {e}", exc_info=True)
            return {
                "text": "",
                "confidence": 0,
                "provider": "google_documentai",
                "error": f"OCR failed: {str(e)}",
            }
    
    def _detect_content_type(self, content: bytes, filename: str) -> str:
        """Detect content type from file header or extension."""
        # Check magic bytes
        if content[:4] == b'%PDF':
            return 'application/pdf'
        if content[:8] == b'\x89PNG\r\n\x1a\n':
            return 'image/png'
        if content[:2] == b'\xff\xd8':
            return 'image/jpeg'
        if content[:4] in (b'II*\x00', b'MM\x00*'):
            return 'image/tiff'
        
        # Fall back to extension
        ext = filename.lower().split('.')[-1] if '.' in filename else ''
        extension_map = {
            'pdf': 'application/pdf',
            'png': 'image/png',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'tiff': 'image/tiff',
            'tif': 'image/tiff',
        }
        
        return extension_map.get(ext, 'application/octet-stream')
    
    def _get_mime_type(self, content_type: str, filename: str) -> str:
        """Convert content type to DocumentAI-compatible MIME type."""
        mime_map = {
            'application/pdf': 'application/pdf',
            'image/png': 'image/png',
            'image/jpeg': 'image/jpeg',
            'image/jpg': 'image/jpeg',
            'image/tiff': 'image/tiff',
        }
        
        if content_type in mime_map:
            return mime_map[content_type]
        
        # Fallback based on extension
        ext = filename.lower().split('.')[-1] if '.' in filename else ''
        ext_mime_map = {
            'pdf': 'application/pdf',
            'png': 'image/png',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'tiff': 'image/tiff',
            'tif': 'image/tiff',
        }
        
        return ext_mime_map.get(ext, 'application/pdf')
    
    async def health_check(self) -> bool:
        """Check if OCR service is available."""
        return self._doc_ai_service is not None


# Singleton instance
_service_instance: Optional[OCRService] = None


def get_ocr_service() -> OCRService:
    """Get or create the OCR service instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = OCRService()
    return _service_instance
