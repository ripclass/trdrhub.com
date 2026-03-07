from __future__ import annotations

import ast
import asyncio
import logging
import os
import sys
import types
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
API_DIR = ROOT / "apps" / "api"

if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

os.environ["DEBUG"] = "0"

import app.routes.ocr_health as ocr_health_route  # noqa: E402
import app.services.ocr_diagnostics as ocr_diag  # noqa: E402


class _CaptureLogger:
    def __init__(self) -> None:
        self.info_messages: list[str] = []
        self.warning_messages: list[str] = []
        self.error_messages: list[str] = []

    @staticmethod
    def _render(message, *args) -> str:
        if args:
            try:
                return str(message) % args
            except Exception:
                return " ".join([str(message), *[str(arg) for arg in args]])
        return str(message)

    def log(self, _level, message, *args, **_kwargs):
        self.info_messages.append(self._render(message, *args))

    def info(self, message, *args, **_kwargs):
        self.info_messages.append(self._render(message, *args))

    def warning(self, message, *args, **_kwargs):
        self.warning_messages.append(self._render(message, *args))

    def error(self, message, *args, **_kwargs):
        self.error_messages.append(self._render(message, *args))

    def debug(self, message, *args, **_kwargs):
        self.info_messages.append(self._render(message, *args))


def _build_health_client(monkeypatch, snapshot_builder):
    app = FastAPI()
    app.include_router(ocr_health_route.router)
    monkeypatch.setattr(ocr_health_route.settings, "OCR_HEALTH_ENDPOINT_ENABLED", True)
    monkeypatch.setattr(ocr_health_route.settings, "OCR_HEALTH_TOKEN", "test-token")
    monkeypatch.setattr(ocr_health_route, "collect_ocr_health_snapshot", snapshot_builder)
    return TestClient(app)


def _load_validate_namespace(logger: _CaptureLogger | None = None) -> dict[str, object]:
    path = ROOT / "apps" / "api" / "app" / "routers" / "validate.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    wanted_funcs = {
        "_empty_extraction_artifacts_v1",
        "_ocr_compatibility_v1_enabled",
        "_ocr_adapter_runtime_payload_fix_v1_enabled",
        "_merge_text_sources",
        "_detect_input_mime_type",
        "_normalize_ocr_input",
        "_prepare_provider_ocr_payload",
        "_provider_runtime_limits",
        "_pdf_page_count",
        "_render_pdf_runtime_images",
        "_normalize_runtime_image_bytes",
        "_build_runtime_payload_entry",
        "_build_google_docai_payload_plan",
        "_build_textract_payload_plan",
        "_build_provider_runtime_payload_plan",
        "_build_provider_attempt_record",
        "_map_ocr_provider_error_code",
        "_try_ocr_providers",
    }
    selected = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in wanted_funcs
    ]
    module = ast.Module(
        body=ast.parse(
            "import asyncio\n"
            "import os\n"
            "import re\n"
            "from io import BytesIO\n"
            "from typing import Any, Dict, List, Optional, Tuple\n"
        ).body
        + selected,
        type_ignores=[],
    )
    namespace: dict[str, object] = {
        "logger": logger or _CaptureLogger(),
        "settings": SimpleNamespace(
            OCR_ENABLED=True,
            OCR_MAX_PAGES=10,
            OCR_MAX_BYTES=10 * 1024 * 1024,
            OCR_TIMEOUT_SEC=5,
            OCR_PROVIDER_ORDER=["gdocai"],
            OCR_NORMALIZATION_DPI=300,
            OCR_NORMALIZATION_SHIM_ENABLED=True,
        ),
        "TRACE_LOG_LEVEL": 15,
    }
    exec(compile(module, str(path), "exec"), namespace)
    return namespace


def _install_fake_factory(monkeypatch, adapters) -> None:
    fake_module = types.ModuleType("app.ocr.factory")

    class _Factory:
        def __init__(self, items):
            self._items = items
            self.configured_providers = [adapter.provider_name for adapter in items]

        def get_all_adapters(self):
            return list(self._items)

    fake_factory = _Factory(adapters)
    fake_module.get_ocr_factory = lambda: fake_factory
    monkeypatch.setitem(sys.modules, "app.ocr.factory", fake_module)


def test_patch_m_health_endpoint_returns_structured_provider_status(monkeypatch):
    monkeypatch.setattr(ocr_diag.settings, "OCR_RUNTIME_DIAGNOSTICS_ENABLED", True)
    monkeypatch.setattr(ocr_diag.settings, "USE_STUBS", False)
    monkeypatch.setattr(ocr_diag.settings, "GOOGLE_CLOUD_PROJECT", "project-1")
    monkeypatch.setattr(ocr_diag.settings, "GOOGLE_DOCUMENTAI_PROCESSOR_ID", "processor-1")
    monkeypatch.setattr(ocr_diag.settings, "OCR_PROVIDER_ORDER", ["gdocai", "textract"])
    registry = ocr_diag.get_ocr_diagnostics()
    registry.reset()
    registry.sync_from_settings()
    ocr_diag.record_ocr_provider_initialization("google_documentai", configured=True, initialized=True, healthy=True)
    ocr_diag.record_ocr_provider_initialization(
        "aws_textract",
        configured=True,
        initialized=False,
        healthy=False,
        error_code="OCR_AUTH_FAILURE",
        error_message="credential=abc123",
    )

    async def _snapshot(refresh_checks=True):
        return await ocr_diag.collect_ocr_health_snapshot(refresh_checks=False)

    client = _build_health_client(monkeypatch, _snapshot)
    response = client.get("/api/ocr/health", headers={"X-OCR-Health": "test-token"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["effective_provider_order"][:2] == ["google_documentai", "aws_textract"]
    assert payload["feature_flags"]["OCR_ENABLED"] is True
    assert payload["feature_flags"]["OCR_RUNTIME_DIAGNOSTICS_ENABLED"] is True
    google_state = next(entry for entry in payload["providers"] if entry["provider_name"] == "google_documentai")
    assert set(google_state) >= {
        "provider_name",
        "configured",
        "initialized",
        "healthy",
        "last_check_at",
        "last_error_code",
        "last_error_message_sanitized",
        "capabilities",
    }


def test_patch_m_health_endpoint_does_not_leak_secrets(monkeypatch):
    monkeypatch.setattr(ocr_diag.settings, "OCR_RUNTIME_DIAGNOSTICS_ENABLED", True)
    monkeypatch.setattr(ocr_diag.settings, "OCR_DIAGNOSTICS_MAX_ERRORS", 5)
    registry = ocr_diag.get_ocr_diagnostics()
    registry.reset()
    registry.sync_from_settings()
    ocr_diag.record_ocr_runtime_failure(
        "google_documentai",
        error_code="OCR_AUTH_FAILURE",
        error_message='api_key=super-secret-token private_key="-----BEGIN PRIVATE KEY-----ABC-----END PRIVATE KEY-----"',
        stage="ocr_provider_primary",
        attempt_number=1,
        normalized_mime="application/pdf",
        page_count=1,
        bytes_sent=10,
    )

    async def _snapshot(refresh_checks=True):
        return await ocr_diag.collect_ocr_health_snapshot(refresh_checks=False)

    client = _build_health_client(monkeypatch, _snapshot)
    response = client.get("/api/ocr/health", headers={"X-OCR-Health": "test-token"})

    assert response.status_code == 200
    serialized = response.text
    assert "super-secret-token" not in serialized
    assert "BEGIN PRIVATE KEY" not in serialized
    assert "[REDACTED]" in serialized


def test_patch_m_health_endpoint_recent_errors_are_bounded(monkeypatch):
    monkeypatch.setattr(ocr_diag.settings, "OCR_RUNTIME_DIAGNOSTICS_ENABLED", True)
    monkeypatch.setattr(ocr_diag.settings, "OCR_DIAGNOSTICS_MAX_ERRORS", 2)
    registry = ocr_diag.get_ocr_diagnostics()
    registry.reset()
    registry.sync_from_settings()
    for index in range(3):
        ocr_diag.record_ocr_runtime_failure(
            "aws_textract",
            error_code=f"OCR_UNKNOWN_PROVIDER_ERROR_{index}",
            error_message=f"error-{index}",
            stage="ocr_provider_primary",
            attempt_number=index + 1,
            normalized_mime="image/png",
            page_count=1,
            bytes_sent=32,
        )

    async def _snapshot(refresh_checks=True):
        return await ocr_diag.collect_ocr_health_snapshot(refresh_checks=False)

    client = _build_health_client(monkeypatch, _snapshot)
    response = client.get("/api/ocr/health", headers={"X-OCR-Health": "test-token"})

    assert response.status_code == 200
    recent_errors = response.json()["recent_errors"]
    assert len(recent_errors) == 2
    assert recent_errors[0]["error_code"] == "OCR_UNKNOWN_PROVIDER_ERROR_2"
    assert recent_errors[1]["error_code"] == "OCR_UNKNOWN_PROVIDER_ERROR_1"


def test_patch_m_auth_error_maps_to_ocr_auth_failure():
    namespace = _load_validate_namespace()
    assert namespace["_map_ocr_provider_error_code"]("invalid api key supplied") == "OCR_AUTH_FAILURE"


def test_patch_m_permission_error_maps_to_ocr_permission_denied():
    namespace = _load_validate_namespace()
    assert namespace["_map_ocr_provider_error_code"]("permission denied for processDocument") == "OCR_PERMISSION_DENIED"


def test_patch_m_processor_not_found_maps_correctly():
    namespace = _load_validate_namespace()
    assert namespace["_map_ocr_provider_error_code"]("Document AI processor not found: projects/x/processors/y not found") == "OCR_PROCESSOR_NOT_FOUND"


def test_patch_m_network_error_maps_correctly():
    namespace = _load_validate_namespace()
    assert namespace["_map_ocr_provider_error_code"]("connection error: temporary failure in name resolution") == "OCR_NETWORK_ERROR"


def test_patch_m_timeout_error_maps_correctly():
    namespace = _load_validate_namespace()
    assert namespace["_map_ocr_provider_error_code"]("deadline exceeded waiting for provider") == "OCR_TIMEOUT"


def test_patch_m_unsupported_format_maps_correctly():
    namespace = _load_validate_namespace()
    assert namespace["_map_ocr_provider_error_code"]("UnsupportedDocumentException: bad format") == "OCR_UNSUPPORTED_FORMAT"


def test_patch_m_empty_result_maps_correctly():
    namespace = _load_validate_namespace()
    assert namespace["_map_ocr_provider_error_code"]("no text extracted from document") == "OCR_EMPTY_RESULT"


def test_patch_m_unknown_error_maps_correctly():
    namespace = _load_validate_namespace()
    assert namespace["_map_ocr_provider_error_code"]("unexpected provider meltdown") == "OCR_UNKNOWN_PROVIDER_ERROR"


def test_patch_m_runtime_diagnostics_include_provider_and_classified_code(monkeypatch):
    capture_logger = _CaptureLogger()
    namespace = _load_validate_namespace(capture_logger)
    image_bytes = b"fake-image-bytes"
    namespace["_build_provider_runtime_payload_plan"] = lambda _provider_name, file_bytes, _filename, content_type: {
        "groups": [[{
            "content": file_bytes,
            "filename": "doc.png",
            "input_mime": content_type,
            "normalized_mime": content_type,
            "page_count": 1,
            "dpi": None,
            "bytes_sent": len(file_bytes),
            "payload_source": "original",
            "retry_used": False,
            "page_index": 1,
        }]],
        "aggregate_pages": False,
        "error_code": None,
        "error": None,
    }

    class _GoogleAdapter:
        provider_name = "google_documentai"

        async def health_check(self):
            return True

        async def process_file_bytes(self, _file_bytes, _filename, _content_type, _document_id):
            return SimpleNamespace(full_text="", overall_confidence=0.0, metadata={}, elements=[], error="permission denied by provider")

    _install_fake_factory(monkeypatch, [_GoogleAdapter()])
    result = asyncio.run(namespace["_try_ocr_providers"](image_bytes, "doc.png", "image/png"))

    attempt = result["artifacts"]["provider_attempts"][0]
    assert attempt["provider"] == "google_documentai"
    assert attempt["error_code"] == "OCR_PERMISSION_DENIED"
    assert any("provider=google_documentai" in entry for entry in capture_logger.warning_messages)
    assert any("error_code=OCR_PERMISSION_DENIED" in entry for entry in capture_logger.warning_messages)


def test_patch_m_startup_summary_hook_logs_provider_summary(monkeypatch, caplog):
    async def _snapshot(*, refresh_checks=True):
        return {
            "timestamp": "2026-03-07T00:00:00+00:00",
            "effective_provider_order": ["google_documentai"],
            "feature_flags": {"OCR_ENABLED": True},
            "providers": [
                {
                    "provider_name": "google_documentai",
                    "configured": True,
                    "initialized": True,
                    "healthy": True,
                    "last_check_at": "2026-03-07T00:00:00+00:00",
                    "last_error_code": None,
                    "last_error_message_sanitized": None,
                    "capabilities": {"pdf": True, "image": True},
                }
            ],
            "recent_errors": [],
        }

    monkeypatch.setattr(ocr_diag, "collect_ocr_health_snapshot", _snapshot)
    with caplog.at_level(logging.INFO):
        snapshot = asyncio.run(ocr_diag.emit_ocr_startup_summary())

    assert snapshot["effective_provider_order"] == ["google_documentai"]
    assert "OCR startup summary" in caplog.text
