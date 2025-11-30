"""
OCR Service Wrapper

Provides a simple interface for text extraction from documents.
Wraps the OCR factory for reuse across the application.
"""

import logging
from typing import Dict, Any, Optional
from uuid import uuid4

from app.ocr.factory import get_ocr_factory

logger = logging.getLogger(__name__)


class OCRService:
    """
    Simple OCR service wrapper.
    
    Provides easy text extraction from documents without
    needing to manage adapters directly.
    """
    
    def __init__(self):
        self._factory = get_ocr_factory()
    
    async def extract_text(
        self,
        content: bytes,
        filename: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Extract text from document content.
        
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
        
        try:
            adapter = await self._factory.get_adapter()
            document_id = uuid4()
            
            logger.info(
                f"OCR extraction: provider={adapter.provider_name}, "
                f"file={filename}, size={len(content)} bytes"
            )
            
            # Use extract_text_from_bytes for simple text extraction
            text = await adapter.extract_text_from_bytes(
                file_bytes=content,
                filename=filename,
                content_type=content_type,
                document_id=document_id,
            )
            
            return {
                "text": text,
                "confidence": 0.85,  # Default confidence
                "provider": adapter.provider_name,
                "error": None,
            }
            
        except NotImplementedError:
            # Try process_file_bytes as fallback
            try:
                adapter = await self._factory.get_adapter()
                document_id = uuid4()
                
                result = await adapter.process_file_bytes(
                    file_bytes=content,
                    filename=filename,
                    content_type=content_type,
                    document_id=document_id,
                )
                
                return {
                    "text": result.full_text,
                    "confidence": result.overall_confidence,
                    "provider": result.provider,
                    "error": result.error,
                }
                
            except Exception as e:
                logger.error(f"OCR processing failed: {e}", exc_info=True)
                return {
                    "text": "",
                    "confidence": 0,
                    "provider": "unknown",
                    "error": str(e),
                }
                
        except Exception as e:
            logger.error(f"OCR extraction error: {e}", exc_info=True)
            return {
                "text": "",
                "confidence": 0,
                "provider": "unknown",
                "error": str(e),
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

