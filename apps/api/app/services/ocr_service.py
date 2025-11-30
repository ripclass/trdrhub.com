"""
OCR Service Wrapper

Provides a simple interface for text extraction from documents.
Uses the same OCR Factory as LCopilot for consistent OCR across all TRDR Hub tools.
"""

import logging
from typing import Dict, Any, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class OCRService:
    """
    Simple OCR service wrapper.
    
    Uses the same OCR Factory as LCopilot (via get_ocr_factory)
    for consistent OCR and credential handling across all TRDR Hub tools.
    """
    
    def __init__(self):
        self._factory = None
        self._init_error = None
        
        try:
            from app.ocr.factory import get_ocr_factory
            self._factory = get_ocr_factory()
            primary = self._factory.primary_provider
            logger.info(f"OCR Service initialized using OCRFactory (primary: {primary})")
        except Exception as e:
            self._init_error = str(e)
            logger.error(f"Failed to initialize OCR Factory: {e}")
    
    async def extract_text(
        self,
        content: bytes,
        filename: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Extract text from document content using OCR Factory.
        
        Args:
            content: Raw file bytes
            filename: Optional filename for context
            content_type: MIME type (auto-detected if not provided)
            
        Returns:
            Dict with 'text', 'confidence', 'provider', 'error' keys
        """
        filename = filename or "document.pdf"
        
        # Check if factory is available
        if not self._factory:
            return {
                "text": "",
                "confidence": 0,
                "provider": "none",
                "error": f"OCR service not available: {self._init_error}",
            }
        
        # Auto-detect content type if not provided
        if not content_type:
            content_type = self._detect_content_type(content, filename)
        
        try:
            # Get adapter from factory (same as LCopilot does)
            adapter = await self._factory.get_adapter()
            logger.info(f"OCR extraction: file={filename}, size={len(content)} bytes, provider={adapter.provider_name}")
            
            # Use process_file_bytes method (same interface as LCopilot)
            result = await adapter.process_file_bytes(
                file_bytes=content,
                filename=filename,
                content_type=content_type,
                document_id=uuid4()  # Generate temp ID for this extraction
            )
            
            if result.error:
                logger.warning(f"OCR returned error: {result.error}")
                return {
                    "text": result.full_text or "",
                    "confidence": result.overall_confidence,
                    "provider": result.provider,
                    "error": result.error,
                }
            
            logger.info(f"OCR extracted {len(result.full_text)} chars with {result.overall_confidence:.2f} confidence")
            return {
                "text": result.full_text,
                "confidence": result.overall_confidence,
                "provider": result.provider,
                "error": None,
            }
                
        except Exception as e:
            logger.error(f"OCR extraction error: {e}", exc_info=True)
            return {
                "text": "",
                "confidence": 0,
                "provider": "unknown",
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
        
        return extension_map.get(ext, 'application/pdf')
    
    async def health_check(self) -> bool:
        """Check if OCR service is available."""
        if not self._factory:
            return False
        try:
            adapter = await self._factory.get_adapter()
            return await adapter.health_check()
        except Exception:
            return False


# Singleton instance
_service_instance: Optional[OCRService] = None


def get_ocr_service() -> OCRService:
    """Get or create the OCR service instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = OCRService()
    return _service_instance
