"""
OCR Service Wrapper

Provides a simple interface for text extraction from documents.
Uses the SAME DocumentAIService as LCopilot for guaranteed consistent OCR behavior.
"""

import logging
import os
import json
import tempfile
from typing import Dict, Any, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


def _setup_google_credentials():
    """
    Set up Google Cloud credentials from environment variable.
    
    On Render, credentials are stored as JSON in GOOGLE_APPLICATION_CREDENTIALS_JSON.
    This function writes them to a temp file and sets GOOGLE_APPLICATION_CREDENTIALS.
    """
    # Skip if already set
    if os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
        return
    
    # Check for JSON credentials in env var
    credentials_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    if credentials_json:
        try:
            creds_data = json.loads(credentials_json)
            temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
            json.dump(creds_data, temp_file)
            temp_file.close()
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = temp_file.name
            logger.info(f"Google credentials set from GOOGLE_APPLICATION_CREDENTIALS_JSON")
        except Exception as e:
            logger.warning(f"Failed to parse Google credentials JSON: {e}")


class OCRService:
    """
    Simple OCR service wrapper.
    
    Uses the SAME DocumentAIService that LCopilot uses (apps/api/app/services.py)
    to guarantee identical behavior and avoid protobuf deserialization issues.
    """
    
    def __init__(self):
        self._documentai_service = None
        self._init_error = None
        
        try:
            # Set up Google Cloud credentials first (from Render env var)
            _setup_google_credentials()
            
            # Use the EXACT SAME DocumentAIService that LCopilot uses
            # This guarantees identical behavior since LCopilot's OCR works!
            from app.services import DocumentAIService
            self._documentai_service = DocumentAIService()
            logger.info("OCR Service initialized using LCopilot's DocumentAIService")
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
        Extract text from document content using DocumentAIService.
        
        Args:
            content: Raw file bytes
            filename: Optional filename for context
            content_type: MIME type (auto-detected if not provided)
            
        Returns:
            Dict with 'text', 'confidence', 'provider', 'error' keys
        """
        filename = filename or "document.pdf"
        
        # Check if service is available
        if not self._documentai_service:
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
            logger.info(f"OCR extraction: file={filename}, size={len(content)} bytes, provider=google_documentai")
            
            # Use DocumentAIService.process_file - the EXACT same method LCopilot uses
            result = await self._documentai_service.process_file(
                file_content=content,
                mime_type=content_type,
            )
            
            if not result.get("success"):
                error_msg = result.get("error", "Unknown OCR error")
                logger.warning(f"OCR returned error: {error_msg}")
                return {
                    "text": result.get("extracted_text", ""),
                    "confidence": result.get("overall_confidence", 0),
                    "provider": "google_documentai",
                    "error": error_msg,
                }
            
            extracted_text = result.get("extracted_text", "")
            confidence = result.get("overall_confidence", 0)
            
            logger.info(f"OCR extracted {len(extracted_text)} chars with {confidence:.2f} confidence")
            return {
                "text": extracted_text,
                "confidence": confidence,
                "provider": "google_documentai",
                "error": None,
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
        
        return extension_map.get(ext, 'application/pdf')
    
    async def health_check(self) -> bool:
        """Check if OCR service is available."""
        if not self._documentai_service:
            return False
        # DocumentAIService is available if it was initialized successfully
        return True


# Singleton instance
_service_instance: Optional[OCRService] = None


def get_ocr_service() -> OCRService:
    """Get or create the OCR service instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = OCRService()
    return _service_instance
