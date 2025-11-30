"""
OCR Service Wrapper

Provides a simple interface for text extraction from documents.
Uses the same OCR factory and adapters as LCopilot.
"""

import io
import logging
from typing import Dict, Any, Optional
from uuid import uuid4

from app.ocr.factory import get_ocr_factory

logger = logging.getLogger(__name__)


class OCRService:
    """
    Simple OCR service wrapper.
    
    Uses the same DocumentAI/Textract adapters as LCopilot
    for consistent OCR across all TRDR Hub tools.
    """
    
    def __init__(self):
        self._factory = get_ocr_factory()
        logger.info(f"OCR Service initialized - Primary: {self._factory.primary_provider}, Fallback: {self._factory.fallback_provider}")
    
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
        
        # Auto-detect content type if not provided
        if not content_type:
            content_type = self._detect_content_type(content, filename)
        
        document_id = uuid4()
        
        try:
            # Get OCR adapter (same as LCopilot uses)
            adapter = await self._factory.get_adapter()
            
            logger.info(
                f"OCR extraction: provider={adapter.provider_name}, "
                f"file={filename}, size={len(content)} bytes, type={content_type}"
            )
            
            # Use process_file_bytes (implemented by all adapters)
            result = await adapter.process_file_bytes(
                file_bytes=content,
                filename=filename,
                content_type=content_type,
                document_id=document_id,
            )
            
            if result.error:
                logger.warning(f"OCR returned error: {result.error}")
                return {
                    "text": result.full_text or "",
                    "confidence": result.overall_confidence,
                    "provider": result.provider,
                    "error": result.error,
                }
            
            if result.full_text and result.full_text.strip():
                logger.info(f"OCR extracted {len(result.full_text)} chars with {result.overall_confidence:.2f} confidence")
                return {
                    "text": result.full_text,
                    "confidence": result.overall_confidence,
                    "provider": result.provider,
                    "error": None,
                }
            else:
                return {
                    "text": "",
                    "confidence": 0,
                    "provider": result.provider,
                    "error": "No text extracted from document",
                }
                
        except NotImplementedError as e:
            logger.error(f"OCR adapter does not support file bytes: {e}")
            return {
                "text": "",
                "confidence": 0,
                "provider": "unknown",
                "error": f"OCR method not supported: {str(e)}",
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
        
        return extension_map.get(ext, 'application/octet-stream')
    
    async def health_check(self) -> bool:
        """Check if OCR service is available."""
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
