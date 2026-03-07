from __future__ import annotations

import asyncio
import importlib
import os
import sys
import types
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
API_DIR = ROOT / "apps" / "api"

if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

os.environ["DEBUG"] = "0"

FACTORY_MODULE = importlib.import_module("app.ocr.factory")


class _FakeAdapter:
    def __init__(
        self,
        provider_name: str,
        *,
        healthy: bool = True,
        result_error: str | None = None,
        raise_on_process: bool = False,
    ):
        self._provider_name = provider_name
        self._healthy = healthy
        self._result_error = result_error
        self._raise_on_process = raise_on_process
        self.process_calls = 0

    @property
    def provider_name(self) -> str:
        return self._provider_name

    async def health_check(self) -> bool:
        return self._healthy

    async def process_document(self, s3_bucket: str, s3_key: str, document_id):
        self.process_calls += 1
        if self._raise_on_process:
            raise RuntimeError(f"{self._provider_name}_process_failed")
        return SimpleNamespace(
            provider=self._provider_name,
            error=self._result_error,
            full_text="" if self._result_error else f"text:{self._provider_name}",
            s3_bucket=s3_bucket,
            s3_key=s3_key,
            document_id=document_id,
        )


def _configure_settings(monkeypatch, **overrides) -> None:
    defaults = {
        "USE_STUBS": False,
        "STUB_SCENARIO": "lc_happy.json",
        "USE_DEEPSEEK_OCR": False,
        "DEEPSEEK_OCR_MODEL_NAME": "deepseek-ai/deepseek-ocr",
        "DEEPSEEK_OCR_DEVICE": None,
        "GOOGLE_CLOUD_PROJECT": "project-id",
        "GOOGLE_DOCUMENTAI_PROCESSOR_ID": "processor-id",
        "OCR_PROVIDER_ORDER": ["gdocai", "textract"],
    }
    defaults.update(overrides)
    for key, value in defaults.items():
        monkeypatch.setattr(FACTORY_MODULE.settings, key, value)


def _build_factory(monkeypatch, *, google=None, textract=None, deepseek=None, settings_overrides=None):
    settings_overrides = settings_overrides or {}
    _configure_settings(monkeypatch, **settings_overrides)
    monkeypatch.setattr(FACTORY_MODULE, "GoogleDocumentAIAdapter", google or (lambda: _FakeAdapter("google_documentai")))
    monkeypatch.setattr(FACTORY_MODULE, "AWSTextractAdapter", textract or (lambda: _FakeAdapter("aws_textract")))
    monkeypatch.setattr(FACTORY_MODULE, "DeepSeekOCRAdapter", deepseek or (lambda **kwargs: _FakeAdapter("deepseek_ocr")))
    FACTORY_MODULE._ocr_factory = None
    return FACTORY_MODULE.OCRFactory()


def test_both_providers_initialized_when_both_are_available(monkeypatch):
    factory = _build_factory(monkeypatch)
    assert factory.configured_providers[:2] == ["google_documentai", "aws_textract"]
    assert factory.initialized_providers == ["google_documentai", "aws_textract"]


def test_provider_order_respects_ocr_provider_order(monkeypatch):
    factory = _build_factory(monkeypatch, settings_overrides={"OCR_PROVIDER_ORDER": ["textract", "gdocai"]})
    adapter = asyncio.run(factory.get_adapter())
    assert adapter.provider_name == "aws_textract"
    assert factory.initialized_providers == ["aws_textract", "google_documentai"]


def test_fallback_to_textract_when_google_unhealthy(monkeypatch):
    google = _FakeAdapter("google_documentai", healthy=False)
    textract = _FakeAdapter("aws_textract", healthy=True)
    factory = _build_factory(
        monkeypatch,
        google=lambda: google,
        textract=lambda: textract,
    )

    adapter = asyncio.run(factory.get_adapter())

    assert adapter.provider_name == "aws_textract"
    assert factory.selected_provider == "aws_textract"
    assert factory.fallback_activated is True
    assert factory.fallback_count == 1


def test_fallback_to_google_when_textract_unhealthy(monkeypatch):
    google = _FakeAdapter("google_documentai", healthy=True)
    textract = _FakeAdapter("aws_textract", healthy=False)
    factory = _build_factory(
        monkeypatch,
        google=lambda: google,
        textract=lambda: textract,
        settings_overrides={"OCR_PROVIDER_ORDER": ["textract", "gdocai"]},
    )

    adapter = asyncio.run(factory.get_adapter())

    assert adapter.provider_name == "google_documentai"
    assert factory.selected_provider == "google_documentai"
    assert factory.fallback_activated is True
    assert factory.fallback_count == 1


def test_only_one_provider_available(monkeypatch):
    factory = _build_factory(
        monkeypatch,
        google=lambda: (_ for _ in ()).throw(RuntimeError("google init failed")),
        textract=lambda: _FakeAdapter("aws_textract", healthy=True),
    )

    adapter = asyncio.run(factory.get_adapter())

    assert factory.initialized_providers == ["aws_textract"]
    assert adapter.provider_name == "aws_textract"


def test_returns_first_initialized_provider_when_no_provider_is_healthy(monkeypatch):
    google = _FakeAdapter("google_documentai", healthy=False)
    textract = _FakeAdapter("aws_textract", healthy=False)
    factory = _build_factory(
        monkeypatch,
        google=lambda: google,
        textract=lambda: textract,
    )

    adapter = asyncio.run(factory.get_adapter())

    assert adapter.provider_name == "google_documentai"
    assert factory.selected_provider == "google_documentai"
    assert factory.fallback_activated is True
    assert factory.fallback_count == 1


def test_process_document_with_fallback_uses_next_provider_after_runtime_error(monkeypatch):
    google = _FakeAdapter("google_documentai", healthy=True, raise_on_process=True)
    textract = _FakeAdapter("aws_textract", healthy=True)
    factory = _build_factory(
        monkeypatch,
        google=lambda: google,
        textract=lambda: textract,
    )

    result = asyncio.run(
        factory.process_document_with_fallback(
            s3_bucket="docs",
            s3_key="invoice.pdf",
            document_id="doc-1",
        )
    )

    assert result.provider == "aws_textract"
    assert google.process_calls == 1
    assert textract.process_calls == 1
    assert factory.selected_provider == "aws_textract"
    assert factory.fallback_activated is True
    assert factory.fallback_count == 1


def test_stub_mode_is_unchanged(monkeypatch):
    fake_stub_module = types.ModuleType("app.stubs.ocr_stub")

    class StubOCRAdapter(_FakeAdapter):
        def __init__(self):
            super().__init__("stub_ocr", healthy=True)

    fake_stub_module.StubOCRAdapter = StubOCRAdapter
    monkeypatch.setitem(sys.modules, "app.stubs.ocr_stub", fake_stub_module)

    factory = _build_factory(monkeypatch, settings_overrides={"USE_STUBS": True})
    adapter = asyncio.run(factory.get_adapter())

    assert factory.initialized_providers == ["stub_ocr"]
    assert adapter.provider_name == "stub_ocr"
    assert factory.fallback_activated is False


def test_alias_mapping_correctness():
    assert FACTORY_MODULE.OCRFactory.resolve_provider_name("gdocai") == "google_documentai"
    assert FACTORY_MODULE.OCRFactory.resolve_provider_name("textract") == "aws_textract"
    assert FACTORY_MODULE.OCRFactory.resolve_provider_name("deepseek") == "deepseek_ocr"
