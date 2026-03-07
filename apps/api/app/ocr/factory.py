"""
OCR factory for creating and managing OCR adapters.
"""

import logging
from typing import Callable, Dict, List, Optional

from .base import OCRAdapter, OCRResult
from .google_documentai import GoogleDocumentAIAdapter
from .aws_textract import AWSTextractAdapter
from .deepseek_ocr import DeepSeekOCRAdapter
from ..config import settings


logger = logging.getLogger(__name__)

_PROVIDER_ALIASES = {
    "gdocai": "google_documentai",
    "google": "google_documentai",
    "google_documentai": "google_documentai",
    "textract": "aws_textract",
    "aws": "aws_textract",
    "aws_textract": "aws_textract",
    "deepseek": "deepseek_ocr",
    "deepseek_ocr": "deepseek_ocr",
    "stub": "stub_ocr",
    "stub_ocr": "stub_ocr",
}


class OCRFactory:
    """Factory for creating and managing OCR adapters with fallback support."""

    def __init__(self):
        self._primary_adapter: Optional[OCRAdapter] = None
        self._fallback_adapter: Optional[OCRAdapter] = None
        self._adapters: List[OCRAdapter] = []
        self._adapter_map: Dict[str, OCRAdapter] = {}
        self._configured_providers: List[str] = []
        self._last_selected_provider: Optional[str] = None
        self._last_fallback_count: int = 0
        self._last_fallback_activated: bool = False
        self._initialize_adapters()

    @classmethod
    def resolve_provider_name(cls, provider_name: Optional[str]) -> str:
        normalized = str(provider_name or "").strip().lower()
        return _PROVIDER_ALIASES.get(normalized, normalized)

    @property
    def configured_providers(self) -> List[str]:
        return list(self._configured_providers)

    @property
    def initialized_providers(self) -> List[str]:
        return [adapter.provider_name for adapter in self.get_ordered_adapters()]

    @property
    def selected_provider(self) -> Optional[str]:
        return self._last_selected_provider

    @property
    def fallback_count(self) -> int:
        return self._last_fallback_count

    @property
    def fallback_activated(self) -> bool:
        return self._last_fallback_activated

    def _initialize_adapters(self):
        """Initialize available OCR adapters based on configuration."""
        if settings.USE_STUBS:
            from ..stubs.ocr_stub import StubOCRAdapter

            stub_adapter = StubOCRAdapter()
            self._configured_providers = [stub_adapter.provider_name]
            self._register_adapter(stub_adapter)
            self._update_primary_and_fallback()
            logger.info(
                "OCR factory initialized stub_mode=%s configured_providers=%s initialized_providers=%s",
                True,
                self._configured_providers,
                self.initialized_providers,
            )
            return

        self._configured_providers = self._resolve_configured_provider_order()

        if settings.USE_DEEPSEEK_OCR:
            self._try_initialize_provider(
                "deepseek_ocr",
                lambda: DeepSeekOCRAdapter(
                    model_name=settings.DEEPSEEK_OCR_MODEL_NAME,
                    device=settings.DEEPSEEK_OCR_DEVICE,
                ),
            )

        if settings.GOOGLE_CLOUD_PROJECT and settings.GOOGLE_DOCUMENTAI_PROCESSOR_ID:
            self._try_initialize_provider("google_documentai", GoogleDocumentAIAdapter)
        else:
            logger.info("OCR provider not configured provider=%s", "google_documentai")

        self._try_initialize_provider("aws_textract", AWSTextractAdapter)

        self._update_primary_and_fallback()
        logger.info(
            "OCR factory initialized configured_providers=%s initialized_providers=%s",
            self._configured_providers,
            self.initialized_providers,
        )

        if not self._adapters:
            logger.error(
                "No OCR adapters initialized configured_providers=%s google_project_set=%s google_processor_set=%s",
                self._configured_providers,
                bool(settings.GOOGLE_CLOUD_PROJECT),
                bool(settings.GOOGLE_DOCUMENTAI_PROCESSOR_ID),
            )
            raise RuntimeError("No OCR adapters could be initialized - check OCR provider configuration")

    def _resolve_configured_provider_order(self) -> List[str]:
        configured: List[str] = []

        for provider_name in settings.OCR_PROVIDER_ORDER or []:
            resolved = self.resolve_provider_name(provider_name)
            if resolved and resolved not in configured:
                configured.append(resolved)

        if settings.USE_DEEPSEEK_OCR and "deepseek_ocr" not in configured:
            configured.append("deepseek_ocr")
        if settings.GOOGLE_CLOUD_PROJECT and settings.GOOGLE_DOCUMENTAI_PROCESSOR_ID and "google_documentai" not in configured:
            configured.append("google_documentai")
        if "aws_textract" not in configured:
            configured.append("aws_textract")

        return configured

    def _try_initialize_provider(self, provider_name: str, builder: Callable[[], OCRAdapter]) -> None:
        try:
            adapter = builder()
            self._register_adapter(adapter)
            logger.info("OCR provider initialized provider=%s", provider_name)
        except Exception as exc:
            logger.warning(
                "OCR provider initialization failed provider=%s error_type=%s message=%s",
                provider_name,
                type(exc).__name__,
                str(exc),
            )

    def _register_adapter(self, adapter: OCRAdapter) -> None:
        provider_name = adapter.provider_name
        if provider_name in self._adapter_map:
            return
        self._adapter_map[provider_name] = adapter
        self._adapters.append(adapter)

    def _update_primary_and_fallback(self) -> None:
        ordered_adapters = self.get_ordered_adapters()
        self._primary_adapter = ordered_adapters[0] if ordered_adapters else None
        self._fallback_adapter = ordered_adapters[1] if len(ordered_adapters) > 1 else None

    def _record_selection(self, provider_name: str, fallback_count: int) -> None:
        self._last_selected_provider = provider_name
        self._last_fallback_count = max(0, int(fallback_count))
        self._last_fallback_activated = self._last_fallback_count > 0
        logger.info(
            "OCR provider selected selected_provider=%s configured_providers=%s initialized_providers=%s fallback_count=%s fallback_activated=%s",
            provider_name,
            self._configured_providers,
            self.initialized_providers,
            self._last_fallback_count,
            self._last_fallback_activated,
        )

    def get_ordered_adapters(self, prefer_fallback: bool = False) -> List[OCRAdapter]:
        ordered: List[OCRAdapter] = []
        seen = set()

        for provider_name in self._configured_providers:
            adapter = self._adapter_map.get(provider_name)
            if adapter and provider_name not in seen:
                ordered.append(adapter)
                seen.add(provider_name)

        for adapter in self._adapters:
            if adapter.provider_name not in seen:
                ordered.append(adapter)
                seen.add(adapter.provider_name)

        if prefer_fallback and len(ordered) > 1:
            return ordered[1:] + ordered[:1]
        return ordered

    async def get_adapter(self, prefer_fallback: bool = False) -> OCRAdapter:
        """
        Get an OCR adapter, with optional fallback preference.

        Args:
            prefer_fallback: If True and fallback is available, prefer trying non-primary providers first

        Returns:
            OCRAdapter instance
        """
        ordered_adapters = self.get_ordered_adapters(prefer_fallback=prefer_fallback)
        if not ordered_adapters:
            raise RuntimeError("No OCR adapters available")

        for index, adapter in enumerate(ordered_adapters):
            try:
                if await adapter.health_check():
                    self._record_selection(adapter.provider_name, index)
                    return adapter
            except Exception as exc:
                logger.warning(
                    "OCR provider health check failed provider=%s error_type=%s message=%s",
                    adapter.provider_name,
                    type(exc).__name__,
                    str(exc),
                )

        fallback_count = max(0, len(ordered_adapters) - 1)
        self._record_selection(ordered_adapters[0].provider_name, fallback_count)
        logger.warning(
            "No healthy OCR providers; returning first initialized provider selected_provider=%s",
            ordered_adapters[0].provider_name,
        )
        return ordered_adapters[0]

    async def process_document_with_fallback(
        self,
        *,
        s3_bucket: str,
        s3_key: str,
        document_id,
        prefer_fallback: bool = False,
    ) -> OCRResult:
        """Process an S3-backed document, falling through providers deterministically on health or runtime errors."""
        ordered_adapters = self.get_ordered_adapters(prefer_fallback=prefer_fallback)
        if not ordered_adapters:
            raise RuntimeError("No OCR adapters available")

        fallback_count = 0
        last_result: Optional[OCRResult] = None

        for adapter in ordered_adapters:
            provider_name = adapter.provider_name
            try:
                if not await adapter.health_check():
                    logger.warning("OCR provider unhealthy during process provider=%s", provider_name)
                    fallback_count += 1
                    continue
            except Exception as exc:
                logger.warning(
                    "OCR provider health check failed during process provider=%s error_type=%s message=%s",
                    provider_name,
                    type(exc).__name__,
                    str(exc),
                )
                fallback_count += 1
                continue

            try:
                result = await adapter.process_document(
                    s3_bucket=s3_bucket,
                    s3_key=s3_key,
                    document_id=document_id,
                )
            except Exception as exc:
                logger.warning(
                    "OCR provider process failed provider=%s error_type=%s message=%s",
                    provider_name,
                    type(exc).__name__,
                    str(exc),
                )
                fallback_count += 1
                continue

            if result and not result.error:
                self._record_selection(provider_name, fallback_count)
                return result

            last_result = result
            logger.warning("OCR provider returned error provider=%s", provider_name)
            fallback_count += 1

        if last_result is not None:
            self._record_selection(last_result.provider or ordered_adapters[0].provider_name, fallback_count)
            return last_result

        raise RuntimeError("No healthy OCR adapters available")

    async def get_healthy_adapters(self) -> List[OCRAdapter]:
        """Get list of healthy OCR adapters in configured order."""
        healthy_adapters: List[OCRAdapter] = []

        for adapter in self.get_ordered_adapters():
            try:
                if await adapter.health_check():
                    healthy_adapters.append(adapter)
            except Exception as exc:
                logger.warning(
                    "OCR provider health check failed provider=%s error_type=%s message=%s",
                    adapter.provider_name,
                    type(exc).__name__,
                    str(exc),
                )

        return healthy_adapters

    def get_all_adapters(self) -> List[OCRAdapter]:
        """Get all configured adapters regardless of health status."""
        return self.get_ordered_adapters()

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
