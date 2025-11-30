"""
OCR factory for creating and managing OCR adapters.
"""

import os
from typing import List, Optional

from .base import OCRAdapter
from .google_documentai import GoogleDocumentAIAdapter
from .aws_textract import AWSTextractAdapter
from .deepseek_ocr import DeepSeekOCRAdapter
from ..config import settings


class OCRFactory:
    """Factory for creating and managing OCR adapters with fallback support."""
    
    def __init__(self):
        self._primary_adapter: Optional[OCRAdapter] = None
        self._fallback_adapter: Optional[OCRAdapter] = None
        self._adapters: List[OCRAdapter] = []
        
        self._initialize_adapters()
    
    def _initialize_adapters(self):
        """Initialize available OCR adapters based on configuration."""
        
        # Check if we should use stubs
        if settings.USE_STUBS:
            from ..stubs.ocr_stub import StubOCRAdapter
            stub_adapter = StubOCRAdapter()
            self._adapters.append(stub_adapter)
            self._primary_adapter = stub_adapter
            print(f"Stub OCR adapter configured (scenario: {settings.STUB_SCENARIO})")
            return
        
        # Initialize real adapters
        # Priority order: DeepSeek OCR > Google Document AI > AWS Textract
        
        # Try to initialize DeepSeek OCR (if enabled)
        if settings.USE_DEEPSEEK_OCR:
            try:
                deepseek_adapter = DeepSeekOCRAdapter(
                    model_name=settings.DEEPSEEK_OCR_MODEL_NAME,
                    device=settings.DEEPSEEK_OCR_DEVICE
                )
                self._adapters.append(deepseek_adapter)
                if not self._primary_adapter:
                    self._primary_adapter = deepseek_adapter
                    print("DeepSeek OCR configured as primary OCR provider")
            except Exception as e:
                print(f"Failed to initialize DeepSeek OCR: {e}")
        
        # Try to initialize Google Document AI
        try:
            if (settings.GOOGLE_CLOUD_PROJECT and 
                settings.GOOGLE_DOCUMENTAI_PROCESSOR_ID):
                print(f"Initializing Google Document AI: project={settings.GOOGLE_CLOUD_PROJECT}, processor={settings.GOOGLE_DOCUMENTAI_PROCESSOR_ID}")
                google_adapter = GoogleDocumentAIAdapter()
                self._adapters.append(google_adapter)
                if not self._primary_adapter:
                    self._primary_adapter = google_adapter
                    print("✓ Google Document AI configured as primary OCR provider")
                elif not self._fallback_adapter:
                    self._fallback_adapter = google_adapter
                    print("✓ Google Document AI configured as fallback OCR provider")
            else:
                print(f"Google Document AI NOT configured: project={settings.GOOGLE_CLOUD_PROJECT}, processor={settings.GOOGLE_DOCUMENTAI_PROCESSOR_ID}")
        except Exception as e:
            print(f"✗ Failed to initialize Google Document AI: {e}")
            import traceback
            traceback.print_exc()
        
        # Try to initialize AWS Textract (fallback)
        # Only use Textract if DocumentAI is NOT configured (to avoid subscription errors)
        if not (settings.GOOGLE_CLOUD_PROJECT and settings.GOOGLE_DOCUMENTAI_PROCESSOR_ID):
            try:
                # AWS credentials are typically available via IAM roles or environment
                aws_adapter = AWSTextractAdapter()
                self._adapters.append(aws_adapter)
                if not self._primary_adapter:
                    self._primary_adapter = aws_adapter
                    print("AWS Textract configured as primary OCR provider")
                elif not self._fallback_adapter:
                    self._fallback_adapter = aws_adapter
                    print("AWS Textract configured as fallback OCR provider")
            except Exception as e:
                print(f"Failed to initialize AWS Textract: {e}")
        else:
            print("Skipping AWS Textract - Google DocumentAI is configured")
        
        if not self._adapters:
            print("ERROR: No OCR adapters initialized!")
            print(f"  - GOOGLE_CLOUD_PROJECT: {'set' if settings.GOOGLE_CLOUD_PROJECT else 'NOT SET'}")
            print(f"  - GOOGLE_DOCUMENTAI_PROCESSOR_ID: {'set' if settings.GOOGLE_DOCUMENTAI_PROCESSOR_ID else 'NOT SET'}")
            print(f"  - GOOGLE_APPLICATION_CREDENTIALS_JSON: {'set' if getattr(settings, 'GOOGLE_APPLICATION_CREDENTIALS_JSON', None) else 'NOT SET'}")
            raise RuntimeError("No OCR adapters could be initialized - check Google Document AI credentials")
    
    async def get_adapter(self, prefer_fallback: bool = False) -> OCRAdapter:
        """
        Get an OCR adapter, with optional fallback preference.
        
        Args:
            prefer_fallback: If True and fallback is available, use fallback adapter
        
        Returns:
            OCRAdapter instance
        """
        if prefer_fallback and self._fallback_adapter:
            # Check if fallback is healthy
            if await self._fallback_adapter.health_check():
                return self._fallback_adapter
        
        # Use primary adapter
        if self._primary_adapter and await self._primary_adapter.health_check():
            return self._primary_adapter
        
        # Fallback if primary is unhealthy
        if self._fallback_adapter and await self._fallback_adapter.health_check():
            return self._fallback_adapter
        
        # If we reach here, no adapters are healthy
        # Return primary adapter anyway - let it fail gracefully
        if self._primary_adapter:
            return self._primary_adapter
        
        raise RuntimeError("No healthy OCR adapters available")
    
    async def get_healthy_adapters(self) -> List[OCRAdapter]:
        """Get list of healthy OCR adapters."""
        healthy_adapters = []
        
        for adapter in self._adapters:
            if await adapter.health_check():
                healthy_adapters.append(adapter)
        
        return healthy_adapters
    
    def get_all_adapters(self) -> List[OCRAdapter]:
        """Get all configured adapters regardless of health status."""
        return self._adapters.copy()
    
    @property
    def primary_provider(self) -> Optional[str]:
        """Get the name of the primary OCR provider."""
        return self._primary_adapter.provider_name if self._primary_adapter else None
    
    @property
    def fallback_provider(self) -> Optional[str]:
        """Get the name of the fallback OCR provider."""
        return self._fallback_adapter.provider_name if self._fallback_adapter else None


# Global OCR factory instance
_ocr_factory: Optional[OCRFactory] = None


def get_ocr_factory() -> OCRFactory:
    """Get the global OCR factory instance."""
    global _ocr_factory
    if _ocr_factory is None:
        _ocr_factory = OCRFactory()
    return _ocr_factory