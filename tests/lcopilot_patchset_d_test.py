from __future__ import annotations

import ast
import asyncio
import os
import sys
import types
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]


class _DummyLogger:
    def log(self, *args, **kwargs):
        return None

    def info(self, *args, **kwargs):
        return None

    def warning(self, *args, **kwargs):
        return None

    def error(self, *args, **kwargs):
        return None

    def debug(self, *args, **kwargs):
        return None


class _FakeUploadFile:
    def __init__(self, data: bytes, filename: str = "doc.pdf", content_type: str = "application/pdf"):
        self._data = data
        self.filename = filename
        self.content_type = content_type

    async def read(self) -> bytes:
        return self._data

    async def seek(self, _offset: int) -> None:
        return None


def _load_validate_namespace() -> dict[str, object]:
    path = ROOT / "apps" / "api" / "app" / "routers" / "validate.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    wanted = {
        "_empty_extraction_artifacts_v1",
        "_extraction_fallback_hotfix_enabled",
        "_ocr_compatibility_v1_enabled",
        "_record_extraction_reason_code",
        "_record_extraction_stage",
        "_merge_extraction_artifacts",
        "_finalize_text_extraction_result",
        "_merge_text_sources",
        "_scrape_binary_text_metadata",
        "_detect_input_mime_type",
        "_normalize_ocr_input",
        "_prepare_provider_ocr_payload",
        "_map_ocr_provider_error_code",
        "_extract_text_from_upload",
        "_try_secondary_ocr_adapter",
        "_finalize_text_backed_extraction_status",
    }
    selected = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in wanted
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
        "logger": _DummyLogger(),
        "settings": SimpleNamespace(
            OCR_MIN_TEXT_CHARS_FOR_SKIP=20,
            OCR_ENABLED=True,
            OCR_MAX_PAGES=10,
            OCR_MAX_BYTES=1024 * 1024,
            OCR_TIMEOUT_SEC=5,
            OCR_PROVIDER_ORDER=["gdocai", "textract"],
        ),
        "TRACE_LOG_LEVEL": 15,
    }
    exec(compile(module, str(path), "exec"), namespace)
    return namespace


def _load_function(path: Path, function_name: str):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    selected = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == function_name
    ]
    module = ast.Module(
        body=ast.parse("from typing import Any, Dict, Optional\n").body + selected,
        type_ignores=[],
    )
    namespace: dict[str, object] = {}
    exec(compile(module, str(path), "exec"), namespace)
    return namespace[function_name]


NORMALIZE_DOC_STATUS = _load_function(
    ROOT / "apps" / "api" / "app" / "routers" / "validation" / "response_shaping.py",
    "_normalize_doc_status",
)
NORMALIZE_DOCUMENT_STATUS = _load_function(
    ROOT / "apps" / "api" / "app" / "services" / "validation" / "response_schema.py",
    "_normalize_document_status",
)


def _install_pdf_stubs(monkeypatch, *, pdfminer_text: str = "", pypdf_text: str = "", pages: int = 1) -> None:
    pdfminer_pkg = types.ModuleType("pdfminer")
    pdfminer_high_level = types.ModuleType("pdfminer.high_level")

    def extract_text(_stream: BytesIO) -> str:
        return pdfminer_text

    pdfminer_high_level.extract_text = extract_text
    pdfminer_pkg.high_level = pdfminer_high_level
    monkeypatch.setitem(sys.modules, "pdfminer", pdfminer_pkg)
    monkeypatch.setitem(sys.modules, "pdfminer.high_level", pdfminer_high_level)

    pypdf2_module = types.ModuleType("PyPDF2")

    class _Page:
        def __init__(self, text: str):
            self._text = text

        def extract_text(self) -> str:
            return self._text

    class PdfReader:
        def __init__(self, _stream: BytesIO):
            self.pages = [_Page(pypdf_text) for _ in range(pages)]

    pypdf2_module.PdfReader = PdfReader
    monkeypatch.setitem(sys.modules, "PyPDF2", pypdf2_module)


def _run_extract(
    namespace: dict[str, object],
    upload_file: _FakeUploadFile,
) -> dict[str, object]:
    return asyncio.run(namespace["_extract_text_from_upload"](upload_file))


def test_empty_artifacts_include_hotfix_metadata_fields():
    namespace = _load_validate_namespace()
    artifacts = namespace["_empty_extraction_artifacts_v1"]("abc", 0.91)
    assert artifacts["attempted_stages"] == []
    assert artifacts["provider_attempts"] == []
    assert artifacts["reason_codes"] == []
    assert artifacts["final_text_length"] == 3


def test_binary_metadata_scrape_recovers_printable_pdf_strings():
    namespace = _load_validate_namespace()
    recovered = namespace["_scrape_binary_text_metadata"](
        b"%PDF-1.4 (LC NUMBER 12345) (BENEFICIARY ACME EXPORTS)"
    )
    assert "LC NUMBER 12345" in recovered
    assert "BENEFICIARY ACME EXPORTS" in recovered


def test_primary_empty_secondary_ocr_recovers_text(monkeypatch):
    namespace = _load_validate_namespace()
    monkeypatch.delenv("LCCOPILOT_EXTRACTION_FALLBACK_HOTFIX", raising=False)
    _install_pdf_stubs(monkeypatch, pdfminer_text="", pypdf_text="", pages=1)

    async def fake_primary(*_args, **_kwargs):
        return {
            "text": "",
            "artifacts": {
                "error_code": "OCR_PROVIDER_UNAVAILABLE",
                "error": "provider_down",
                "provider_attempts": [{"provider": "google_documentai", "status": "error"}],
            },
        }

    async def fake_secondary(*_args, **_kwargs):
        return {
            "text": "LC NUMBER 12345\nAPPLICANT ACME",
            "artifacts": {"provider_attempts": [{"provider": "ocr_service", "status": "success"}]},
        }

    namespace["_try_ocr_providers"] = fake_primary
    namespace["_try_secondary_ocr_adapter"] = fake_secondary
    result = _run_extract(namespace, _FakeUploadFile(b"%PDF demo"))

    artifacts = result["artifacts"]
    assert "LC NUMBER 12345" in result["text"]
    assert artifacts["final_stage"] == "ocr_secondary"
    assert artifacts["fallback_activated"] is True
    assert "PARSER_EMPTY_OUTPUT" in artifacts["reason_codes"]
    assert "FALLBACK_TEXT_RECOVERED" in artifacts["reason_codes"]
    assert "ocr_secondary" in artifacts["attempted_stages"]


def test_primary_empty_binary_scrape_recovers_text(monkeypatch):
    namespace = _load_validate_namespace()
    monkeypatch.delenv("LCCOPILOT_EXTRACTION_FALLBACK_HOTFIX", raising=False)
    _install_pdf_stubs(monkeypatch, pdfminer_text="", pypdf_text="", pages=1)

    async def fake_empty(*_args, **_kwargs):
        return {
            "text": "",
            "artifacts": {"error_code": "OCR_PROVIDER_UNAVAILABLE", "error": "down"},
        }

    namespace["_try_ocr_providers"] = fake_empty
    namespace["_try_secondary_ocr_adapter"] = fake_empty
    namespace["_scrape_binary_text_metadata"] = lambda _file_bytes: "Invoice Number INV-1"

    result = _run_extract(namespace, _FakeUploadFile(b"%PDF demo"))
    artifacts = result["artifacts"]

    assert result["text"] == "Invoice Number INV-1"
    assert artifacts["final_stage"] == "binary_metadata_scrape"
    assert "FALLBACK_TEXT_RECOVERED" in artifacts["reason_codes"]
    assert "binary_metadata_scrape" in artifacts["attempted_stages"]


def test_all_stages_empty_records_explicit_reason_codes(monkeypatch):
    namespace = _load_validate_namespace()
    monkeypatch.delenv("LCCOPILOT_EXTRACTION_FALLBACK_HOTFIX", raising=False)
    _install_pdf_stubs(monkeypatch, pdfminer_text="", pypdf_text="", pages=1)

    async def fake_empty(*_args, **_kwargs):
        return {
            "text": "",
            "artifacts": {"error_code": "OCR_PROVIDER_UNAVAILABLE", "error": "down"},
        }

    namespace["_try_ocr_providers"] = fake_empty
    namespace["_try_secondary_ocr_adapter"] = fake_empty
    namespace["_scrape_binary_text_metadata"] = lambda _file_bytes: ""

    result = _run_extract(namespace, _FakeUploadFile(b"%PDF demo"))
    artifacts = result["artifacts"]

    assert result["text"] == ""
    assert artifacts["final_text_length"] == 0
    assert "PARSER_EMPTY_OUTPUT" in artifacts["reason_codes"]
    assert "OCR_PROVIDER_UNAVAILABLE" in artifacts["reason_codes"]
    assert "EXTRACTION_EMPTY_ALL_STAGES" in artifacts["reason_codes"]


def test_hotfix_toggle_disables_secondary_and_binary_fallback(monkeypatch):
    namespace = _load_validate_namespace()
    monkeypatch.setenv("LCCOPILOT_EXTRACTION_FALLBACK_HOTFIX", "0")
    _install_pdf_stubs(monkeypatch, pdfminer_text="", pypdf_text="", pages=1)

    async def fake_primary(*_args, **_kwargs):
        return {
            "text": "",
            "artifacts": {"error_code": "OCR_PROVIDER_UNAVAILABLE", "error": "down"},
        }

    secondary_calls: list[str] = []

    async def fake_secondary(*_args, **_kwargs):
        secondary_calls.append("called")
        return {"text": "should-not-run", "artifacts": {}}

    namespace["_try_ocr_providers"] = fake_primary
    namespace["_try_secondary_ocr_adapter"] = fake_secondary
    namespace["_scrape_binary_text_metadata"] = lambda _file_bytes: "should-not-run"

    result = _run_extract(namespace, _FakeUploadFile(b"%PDF demo"))

    assert result["text"] == ""
    assert secondary_calls == []
    assert "EXTRACTION_EMPTY_ALL_STAGES" in result["artifacts"]["reason_codes"]


def test_no_silent_empty_when_native_text_exists(monkeypatch):
    namespace = _load_validate_namespace()
    monkeypatch.delenv("LCCOPILOT_EXTRACTION_FALLBACK_HOTFIX", raising=False)
    _install_pdf_stubs(monkeypatch, pdfminer_text="LC 12345", pypdf_text="", pages=1)

    async def fake_empty(*_args, **_kwargs):
        return {
            "text": "",
            "artifacts": {"error_code": "OCR_PROVIDER_UNAVAILABLE", "error": "down"},
        }

    namespace["_try_ocr_providers"] = fake_empty
    namespace["_try_secondary_ocr_adapter"] = fake_empty
    namespace["_scrape_binary_text_metadata"] = lambda _file_bytes: ""

    result = _run_extract(namespace, _FakeUploadFile(b"%PDF demo"))

    assert result["text"] == "LC 12345"
    assert result["artifacts"]["final_stage"] == "native_pdf_text"


def test_recovered_text_maps_to_parse_failed_with_reason_code(monkeypatch):
    namespace = _load_validate_namespace()
    monkeypatch.delenv("LCCOPILOT_EXTRACTION_FALLBACK_HOTFIX", raising=False)
    _install_pdf_stubs(monkeypatch, pdfminer_text="", pypdf_text="", pages=1)

    async def fake_empty(*_args, **_kwargs):
        return {
            "text": "",
            "artifacts": {"error_code": "OCR_PROVIDER_UNAVAILABLE", "error": "down"},
        }

    namespace["_try_ocr_providers"] = fake_empty
    namespace["_try_secondary_ocr_adapter"] = fake_empty
    namespace["_scrape_binary_text_metadata"] = lambda _file_bytes: "Invoice Number INV-1"

    result = _run_extract(namespace, _FakeUploadFile(b"%PDF demo"))
    doc_info = {"extraction_status": "empty", "extracted_fields": {}}
    namespace["_finalize_text_backed_extraction_status"](
        doc_info,
        "commercial_invoice",
        result["text"],
    )

    assert doc_info["extraction_status"] == "parse_failed"
    assert "FALLBACK_TEXT_RECOVERED" in result["artifacts"]["reason_codes"]


def test_finalize_text_backed_status_preserves_supporting_document_text_only(monkeypatch):
    namespace = _load_validate_namespace()
    monkeypatch.delenv("LCCOPILOT_EXTRACTION_FALLBACK_HOTFIX", raising=False)

    doc_info = {"extraction_status": "empty", "extracted_fields": {}}
    namespace["_finalize_text_backed_extraction_status"](doc_info, "supporting_document", "memo text")

    assert doc_info["extraction_status"] == "text_only"


def test_finalize_text_backed_status_does_not_change_successful_extraction(monkeypatch):
    namespace = _load_validate_namespace()
    monkeypatch.delenv("LCCOPILOT_EXTRACTION_FALLBACK_HOTFIX", raising=False)

    doc_info = {"extraction_status": "success", "extracted_fields": {"invoice_number": "INV-1"}}
    namespace["_finalize_text_backed_extraction_status"](doc_info, "commercial_invoice", "Invoice Number INV-1")

    assert doc_info["extraction_status"] == "success"


def test_response_shaping_normalizes_parse_failed_to_warning():
    assert NORMALIZE_DOC_STATUS(None, "parse_failed", None) == "warning"


def test_response_schema_normalizes_parse_failed_to_warning():
    assert NORMALIZE_DOCUMENT_STATUS({"extraction_status": "parse_failed"}) == "warning"


def test_validate_source_contains_hotfix_toggle_and_secondary_stage():
    source = (ROOT / "apps" / "api" / "app" / "routers" / "validate.py").read_text(encoding="utf-8")
    assert "LCCOPILOT_EXTRACTION_FALLBACK_HOTFIX" in source
    assert 'stage="ocr_secondary"' in source
    assert "EXTRACTION_EMPTY_ALL_STAGES" in source
