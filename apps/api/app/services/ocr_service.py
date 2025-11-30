"""
OCR Service Wrapper

Provides a simple interface for text extraction from documents.
Wraps the OCR factory for reuse across the application.
Includes fallback extraction for when OCR APIs are unavailable.
"""

import io
import logging
from typing import Dict, Any, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

# Try to import OCR factory (may fail if not configured)
try:
    from app.ocr.factory import get_ocr_factory
    OCR_FACTORY_AVAILABLE = True
except Exception as e:
    logger.warning(f"OCR factory not available: {e}")
    OCR_FACTORY_AVAILABLE = False

# Try to import PDF extraction libraries
PYPDF_AVAILABLE = False
PYPDF_MODULE = None

try:
    from PyPDF2 import PdfReader
    PYPDF_AVAILABLE = True
    PYPDF_MODULE = "PyPDF2"
    logger.info("PyPDF2 available for PDF fallback extraction")
except ImportError:
    try:
        import pypdf
        PYPDF_AVAILABLE = True
        PYPDF_MODULE = "pypdf"
        logger.info("pypdf available for PDF fallback extraction")
    except ImportError:
        logger.warning("No PDF library available for fallback extraction")


class OCRService:
    """
    Simple OCR service wrapper.
    
    Provides easy text extraction from documents without
    needing to manage adapters directly.
    
    Includes fallback extraction for when OCR APIs are unavailable.
    """
    
    def __init__(self):
        self._factory = None
        if OCR_FACTORY_AVAILABLE:
            try:
                self._factory = get_ocr_factory()
            except Exception as e:
                logger.warning(f"Could not initialize OCR factory: {e}")
    
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
        
        # Try OCR factory first if available
        if self._factory:
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
                
                if text and text.strip():
                    return {
                        "text": text,
                        "confidence": 0.85,
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
                    
                    if result.full_text and result.full_text.strip():
                        return {
                            "text": result.full_text,
                            "confidence": result.overall_confidence,
                            "provider": result.provider,
                            "error": result.error,
                        }
                        
                except Exception as e:
                    logger.warning(f"OCR factory fallback failed: {e}")
                    
            except Exception as e:
                logger.warning(f"OCR extraction failed, trying fallback: {e}")
        
        # Fallback: Use PyPDF for PDF files
        if content_type == 'application/pdf' or filename.lower().endswith('.pdf'):
            logger.info("Using PyPDF fallback for PDF extraction")
            return await self._extract_pdf_fallback(content, filename)
        
        # No extraction possible
        logger.error(f"No extraction method available for {content_type}")
        return {
            "text": "",
            "confidence": 0,
            "provider": "none",
            "error": "No OCR service available and file is not a text-based PDF",
        }
    
    async def _extract_pdf_fallback(
        self,
        content: bytes,
        filename: str,
    ) -> Dict[str, Any]:
        """Extract text from PDF using PyPDF as fallback."""
        if not PYPDF_AVAILABLE:
            return {
                "text": "",
                "confidence": 0,
                "provider": "fallback",
                "error": "No PDF library available for extraction",
            }
        
        try:
            text_parts = []
            
            if PYPDF_MODULE == "PyPDF2":
                from PyPDF2 import PdfReader
                reader = PdfReader(io.BytesIO(content))
                for page in reader.pages:
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text_parts.append(page_text)
                    except Exception as e:
                        logger.warning(f"Failed to extract page text: {e}")
            else:
                import pypdf
                reader = pypdf.PdfReader(io.BytesIO(content))
                for page in reader.pages:
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text_parts.append(page_text)
                    except Exception as e:
                        logger.warning(f"Failed to extract page text: {e}")
            
            text = "\n\n".join(text_parts)
            
            if text and text.strip():
                logger.info(f"PDF fallback extracted {len(text)} chars from {filename} using {PYPDF_MODULE}")
                return {
                    "text": text,
                    "confidence": 0.7,  # Lower confidence for fallback
                    "provider": PYPDF_MODULE,
                    "error": None,
                }
            else:
                return {
                    "text": "",
                    "confidence": 0,
                    "provider": PYPDF_MODULE,
                    "error": "PDF appears to be image-based (scanned). OCR required but not available.",
                }
                
        except Exception as e:
            logger.error(f"PDF fallback extraction failed: {e}", exc_info=True)
            return {
                "text": "",
                "confidence": 0,
                "provider": "fallback",
                "error": f"PDF extraction failed: {str(e)}",
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

