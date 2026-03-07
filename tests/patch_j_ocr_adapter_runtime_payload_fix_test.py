from __future__ import annotations

import ast
import asyncio
import copy
import sys
import types
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SERVICES_DIR = ROOT / "apps" / "api" / "app" / "services"

if str(SERVICES_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICES_DIR))

from extraction_core.review_metadata import build_document_extraction  # noqa: E402


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
    wanted_funcs = {
        "_empty_extraction_artifacts_v1",
        "_extraction_fallback_hotfix_enabled",
        "_ocr_compatibility_v1_enabled",
        "_ocr_adapter_runtime_payload_fix_v1_enabled",
        "_record_extraction_reason_code",
        "_record_extraction_stage",
        "_merge_extraction_artifacts",
        "_finalize_text_extraction_result",
        "_merge_text_sources",
        "_build_extraction_artifacts_from_ocr",
        "_scrape_binary_text_metadata",
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
        "_extract_text_from_upload",
        "_try_secondary_ocr_adapter",
        "_try_ocr_providers",
        "_finalize_text_backed_extraction_status",
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
        "logger": _DummyLogger(),
        "settings": SimpleNamespace(
            OCR_MIN_TEXT_CHARS_FOR_SKIP=20,
            OCR_ENABLED=True,
            OCR_MAX_PAGES=10,
            OCR_MAX_BYTES=10 * 1024 * 1024,
            OCR_TIMEOUT_SEC=5,
            OCR_PROVIDER_ORDER=["gdocai", "textract"],
            OCR_NORMALIZATION_DPI=300,
            OCR_NORMALIZATION_SHIM_ENABLED=True,
        ),
        "TRACE_LOG_LEVEL": 15,
    }
    exec(compile(module, str(path), "exec"), namespace)
    return namespace


def _load_response_shaping_namespace() -> dict[str, object]:
    path = ROOT / "apps" / "api" / "app" / "routers" / "validation" / "response_shaping.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    wanted_assigns = {
        "EXPOSURE_DIAGNOSTICS_V1_ENV",
        "_MAX_STAGE_ATTEMPTS",
        "_MAX_REASON_CODES",
        "_MAX_STAGE_SCORE_STAGES",
        "_MAX_STAGE_SCORE_KEYS",
        "_SAFE_REASON_CODE_RE",
    }
    wanted_funcs = {
        "exposure_diagnostics_v1_enabled",
        "_sanitize_reason_codes",
        "_normalize_stage_scores",
        "_extract_stage_error_code",
        "build_extraction_debug",
    }
    selected = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            target_names = {target.id for target in node.targets if isinstance(target, ast.Name)}
            if target_names & wanted_assigns:
                selected.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in wanted_funcs:
            selected.append(node)

    module = ast.Module(
        body=ast.parse("import os\nimport re\nfrom typing import Any, Dict, List, Optional\n").body + selected,
        type_ignores=[],
    )
    namespace: dict[str, object] = {}
    exec(compile(module, str(path), "exec"), namespace)
    return namespace


def _install_pdf_text_stubs(monkeypatch, *, pdfminer_text: str = "", pypdf_text: str = "", pages: int = 1) -> None:
    pdfminer_pkg = types.ModuleType("pdfminer")
    pdfminer_high_level = types.ModuleType("pdfminer.high_level")
    pdfminer_high_level.extract_text = lambda _stream: pdfminer_text
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


def _install_pdf_render_stubs(monkeypatch, *, page_count: int = 2) -> None:
    pdf2image_module = types.ModuleType("pdf2image")
    pdf2image_module.convert_from_bytes = lambda *_args, **_kwargs: [
        Image.new("RGB", (24, 24), color="white") for _ in range(page_count)
    ]
    monkeypatch.setitem(sys.modules, "pdf2image", pdf2image_module)

    pypdf2_module = types.ModuleType("PyPDF2")

    class PdfReader:
        def __init__(self, _stream):
            self.pages = [object() for _ in range(page_count)]

    pypdf2_module.PdfReader = PdfReader
    monkeypatch.setitem(sys.modules, "PyPDF2", pypdf2_module)


def _install_fake_factory(monkeypatch, adapters):
    app_module = sys.modules.setdefault("app", types.ModuleType("app"))
    ocr_module = sys.modules.setdefault("app.ocr", types.ModuleType("app.ocr"))
    factory_module = types.ModuleType("app.ocr.factory")

    class _Factory:
        def get_all_adapters(self):
            return list(adapters)

    factory_module.get_ocr_factory = lambda: _Factory()
    monkeypatch.setitem(sys.modules, "app.ocr.factory", factory_module)
    app_module.ocr = ocr_module


def _install_fake_ocr_service(monkeypatch, service):
    app_module = sys.modules.setdefault("app", types.ModuleType("app"))
    services_module = sys.modules.setdefault("app.services", types.ModuleType("app.services"))
    ocr_service_module = types.ModuleType("app.services.ocr_service")
    ocr_service_module.get_ocr_service = lambda: service
    monkeypatch.setitem(sys.modules, "app.services.ocr_service", ocr_service_module)
    app_module.services = services_module


def _response_shaping_debug(document):
    namespace = _load_response_shaping_namespace()
    return namespace["build_extraction_debug"](document)


def _invoice_doc() -> dict[str, object]:
    raw_text = (
        "Seller Acme Exports Limited\n"
        "Invoice Date 14 Feb 2026\n"
        "BIN 1234567890123\n"
        "Gross Weight 100 KG\n"
        "Net Weight 90 KG\n"
    )
    return {
        "id": "doc-ci-1",
        "document_type": "commercial_invoice",
        "extraction_confidence": 0.96,
        "raw_text": raw_text,
        "extracted_fields": {
            "exporter_bin": "1234567890123",
            "gross_weight": "100 KG",
            "net_weight": "90 KG",
            "invoice_date": "14 Feb 2026",
            "seller_name": "Acme Exports Limited",
        },
        "field_details": {
            "exporter_bin": {"confidence": 0.96, "evidence_snippet": "BIN 1234567890123"},
            "gross_weight": {"confidence": 0.96, "evidence_snippet": "Gross Weight 100 KG"},
            "net_weight": {"confidence": 0.96, "evidence_snippet": "Net Weight 90 KG"},
            "invoice_date": {"confidence": 0.96, "evidence_snippet": "Invoice Date 14 Feb 2026"},
            "seller_name": {"confidence": 0.96, "evidence_snippet": "Seller Acme Exports Limited"},
        },
        "extraction_artifacts_v1": {
            "raw_text": raw_text,
            "reason_codes": [],
            "stage_errors": {},
            "provider_attempts": [],
            "final_text_length": len(raw_text),
        },
    }


def test_patch_j_google_payload_builder_for_pdf_input(monkeypatch):
    namespace = _load_validate_namespace()
    _install_pdf_render_stubs(monkeypatch, page_count=2)

    plan = namespace["_build_google_docai_payload_plan"](
        "google_documentai",
        b"%PDF-1.4 demo",
        "lc.pdf",
        "application/pdf",
    )

    assert plan["error_code"] is None
    assert plan["groups"][0][0]["normalized_mime"] == "application/pdf"
    assert plan["groups"][0][0]["retry_used"] is False
    assert plan["groups"][0][1]["retry_used"] is True


def test_patch_j_textract_payload_builder_for_pdf_input(monkeypatch):
    namespace = _load_validate_namespace()
    _install_pdf_render_stubs(monkeypatch, page_count=2)

    plan = namespace["_build_textract_payload_plan"](
        "aws_textract",
        b"%PDF-1.4 demo",
        "bl.pdf",
        "application/pdf",
    )

    assert plan["error_code"] is None
    assert plan["aggregate_pages"] is True
    assert len(plan["groups"]) == 2
    assert plan["groups"][0][0]["normalized_mime"] == "image/png"
    assert plan["groups"][0][1]["normalized_mime"] == "image/jpeg"


def test_patch_j_fallback_conversion_retry_after_unsupported_format(monkeypatch):
    namespace = _load_validate_namespace()
    _install_pdf_render_stubs(monkeypatch, page_count=1)

    class _GoogleAdapter:
        provider_name = "google_documentai"

        async def health_check(self):
            return True

        async def process_file_bytes(self, _file_bytes, _filename, content_type, _document_id):
            if content_type == "application/pdf":
                return SimpleNamespace(full_text="", overall_confidence=0.0, metadata={}, elements=[], error="unsupported document format")
            return SimpleNamespace(full_text="LC NUMBER 12345", overall_confidence=0.91, metadata={}, elements=[], error=None)

    _install_fake_factory(monkeypatch, [_GoogleAdapter()])
    result = asyncio.run(namespace["_try_ocr_providers"](b"%PDF-1.4 demo", "lc.pdf", "application/pdf"))

    attempts = result["artifacts"]["provider_attempts"]
    assert result["text"] == "LC NUMBER 12345"
    assert attempts[0]["error_code"] == "OCR_UNSUPPORTED_FORMAT"
    assert attempts[1]["retry_used"] is True


def test_patch_j_success_path_returns_non_empty_text_len(monkeypatch):
    namespace = _load_validate_namespace()
    _install_pdf_render_stubs(monkeypatch, page_count=1)

    class _GoogleAdapter:
        provider_name = "google_documentai"

        async def health_check(self):
            return True

        async def process_file_bytes(self, _file_bytes, _filename, _content_type, _document_id):
            return SimpleNamespace(full_text="Commercial Invoice", overall_confidence=0.92, metadata={}, elements=[], error=None)

    _install_fake_factory(monkeypatch, [_GoogleAdapter()])
    result = asyncio.run(namespace["_try_ocr_providers"](b"%PDF-1.4 demo", "invoice.pdf", "application/pdf"))

    assert result["artifacts"]["provider_attempts"][0]["text_len"] == len("Commercial Invoice")


def test_patch_j_stage_attempt_telemetry_includes_non_null_text_len(monkeypatch):
    monkeypatch.delenv("LCCOPILOT_EXPOSURE_DIAGNOSTICS_V1_ENABLED", raising=False)
    debug = _response_shaping_debug(
        {
            "review_required": True,
            "critical_field_states": {"bin_tin": "parse_failed"},
            "extraction_artifacts_v1": {
                "provider_attempts": [
                    {
                        "stage": "ocr_provider_primary",
                        "provider": "google_documentai",
                        "text_len": 0,
                        "error_code": "OCR_UNSUPPORTED_FORMAT",
                        "input_mime": "application/pdf",
                        "normalized_mime": "application/pdf",
                        "retry_used": False,
                    },
                    {
                        "stage": "ocr_provider_primary",
                        "provider": "google_documentai",
                        "text_len": 18,
                        "error_code": None,
                        "input_mime": "application/pdf",
                        "normalized_mime": "image/tiff",
                        "retry_used": True,
                    },
                ]
            },
        }
    )

    assert debug["stage_attempts"][0]["text_length"] == 0
    assert debug["stage_attempts"][1]["text_length"] == 18
    assert debug["stage_attempts"][1]["provider"] == "google_documentai"


def test_patch_j_reason_code_mapping_correct_for_format_error():
    namespace = _load_validate_namespace()
    assert namespace["_map_ocr_provider_error_code"]("UnsupportedDocumentException: bad format") == "OCR_UNSUPPORTED_FORMAT"


def test_patch_j_no_regression_in_binary_fallback_behavior(monkeypatch):
    namespace = _load_validate_namespace()
    _install_pdf_text_stubs(monkeypatch, pdfminer_text="", pypdf_text="", pages=1)

    async def fake_primary(*_args, **_kwargs):
        return {"text": "", "artifacts": {"error_code": "OCR_UNSUPPORTED_FORMAT", "error": "unsupported document format"}}

    async def fake_secondary(*_args, **_kwargs):
        return {"text": "", "artifacts": {"error_code": "OCR_UNSUPPORTED_FORMAT", "error": "unsupported document format"}}

    namespace["_try_ocr_providers"] = fake_primary
    namespace["_try_secondary_ocr_adapter"] = fake_secondary
    namespace["_scrape_binary_text_metadata"] = lambda _file_bytes: "Recovered invoice text"

    result = asyncio.run(namespace["_extract_text_from_upload"](_FakeUploadFile(b"%PDF demo")))

    assert result["artifacts"]["final_stage"] == "binary_metadata_scrape"
    assert "FALLBACK_TEXT_RECOVERED" in result["artifacts"]["reason_codes"]


def test_patch_j_no_regression_in_field_states():
    doc = build_document_extraction(_invoice_doc())
    fields = {field.name: field for field in doc.fields}

    assert fields["bin_tin"].state == "found"
    assert fields["gross_weight"].state == "found"
    assert fields["net_weight"].state == "found"


def test_patch_j_no_regression_in_review_gating():
    payload = _invoice_doc()
    payload["extraction_confidence"] = 0.75
    for key in ("exporter_bin", "gross_weight", "net_weight"):
        payload["field_details"][key]["confidence"] = 0.75

    doc = build_document_extraction(payload)

    assert doc.review_required is True
    assert "LOW_CONFIDENCE_CRITICAL" in doc.review_reasons


def test_patch_j_no_contract_shape_regression(monkeypatch):
    monkeypatch.delenv("LCCOPILOT_EXPOSURE_DIAGNOSTICS_V1_ENABLED", raising=False)
    debug = _response_shaping_debug(
        {
            "review_required": True,
            "critical_field_states": {"bin_tin": "found"},
            "extraction_artifacts_v1": {
                "selected_stage": "ocr_provider_primary",
                "provider_attempts": [
                    {
                        "stage": "ocr_provider_primary",
                        "provider": "google_documentai",
                        "text_len": 12,
                        "error_code": None,
                        "input_mime": "application/pdf",
                        "normalized_mime": "application/pdf",
                        "retry_used": False,
                    }
                ],
            },
        }
    )

    assert debug["selected_stage"] == "ocr_provider_primary"
    assert debug["coverage"] == 1.0
    assert debug["stage_attempts"][0]["text_length"] == 12


def test_patch_j_integration_sample_pdf_through_adapter_path(monkeypatch):
    namespace = _load_validate_namespace()
    _install_pdf_text_stubs(monkeypatch, pdfminer_text="", pypdf_text="", pages=1)
    _install_pdf_render_stubs(monkeypatch, page_count=1)

    class _GoogleAdapter:
        provider_name = "google_documentai"

        async def health_check(self):
            return True

        async def process_file_bytes(self, _file_bytes, _filename, content_type, _document_id):
            if content_type == "application/pdf":
                return SimpleNamespace(full_text="Invoice Date 2026-02-14\nBIN 1234567890123", overall_confidence=0.93, metadata={}, elements=[], error=None)
            return SimpleNamespace(full_text="", overall_confidence=0.0, metadata={}, elements=[], error="should not retry")

    _install_fake_factory(monkeypatch, [_GoogleAdapter()])
    result = asyncio.run(namespace["_extract_text_from_upload"](_FakeUploadFile(b"%PDF-1.4 demo")))

    assert "BIN 1234567890123" in result["text"]
    assert result["artifacts"]["final_stage"] == "ocr_provider_primary"


def test_patch_j_textract_pdf_pages_aggregate_text(monkeypatch):
    namespace = _load_validate_namespace()
    _install_pdf_render_stubs(monkeypatch, page_count=2)
    namespace["settings"].OCR_PROVIDER_ORDER = ["textract"]

    class _TextractAdapter:
        provider_name = "aws_textract"

        async def health_check(self):
            return True

        async def process_file_bytes(self, _file_bytes, _filename, content_type, _document_id):
            if content_type != "image/png":
                return SimpleNamespace(full_text="", overall_confidence=0.0, metadata={}, elements=[], error="unsupported content type")
            return SimpleNamespace(full_text="PAGE TEXT", overall_confidence=0.88, metadata={}, elements=[], error=None)

    _install_fake_factory(monkeypatch, [_TextractAdapter()])
    result = asyncio.run(namespace["_try_ocr_providers"](b"%PDF-1.4 demo", "bl.pdf", "application/pdf"))

    assert result["text"] == "PAGE TEXT"
    assert len(result["artifacts"]["provider_attempts"]) == 2
    assert all(isinstance(attempt["text_len"], int) for attempt in result["artifacts"]["provider_attempts"])


def test_patch_j_secondary_service_retry_works(monkeypatch):
    namespace = _load_validate_namespace()
    _install_pdf_render_stubs(monkeypatch, page_count=1)

    class _Service:
        async def health_check(self):
            return True

        async def extract_text(self, _content, filename=None, content_type=None):
            if content_type == "application/pdf":
                return {"text": "", "confidence": 0.0, "provider": "google_documentai", "error": "invalid document format"}
            return {"text": "Secondary OCR text", "confidence": 0.84, "provider": "google_documentai", "error": None}

    _install_fake_ocr_service(monkeypatch, _Service())
    result = asyncio.run(namespace["_try_secondary_ocr_adapter"](b"%PDF-1.4 demo", "doc.pdf", "application/pdf"))

    assert result["text"] == "Secondary OCR text"
    assert result["artifacts"]["provider_attempts"][0]["error_code"] == "OCR_UNSUPPORTED_FORMAT"
    assert result["artifacts"]["provider_attempts"][1]["retry_used"] is True


def test_patch_j_runtime_stage_attempts_include_provider_mimes_after_extract(monkeypatch):
    namespace = _load_validate_namespace()
    _install_pdf_text_stubs(monkeypatch, pdfminer_text="", pypdf_text="", pages=1)
    _install_pdf_render_stubs(monkeypatch, page_count=1)

    class _GoogleAdapter:
        provider_name = "google_documentai"

        async def health_check(self):
            return True

        async def process_file_bytes(self, _file_bytes, _filename, content_type, _document_id):
            if content_type == "application/pdf":
                return SimpleNamespace(full_text="", overall_confidence=0.0, metadata={}, elements=[], error="unsupported file format")
            return SimpleNamespace(full_text="OCR text", overall_confidence=0.9, metadata={}, elements=[], error=None)

    _install_fake_factory(monkeypatch, [_GoogleAdapter()])
    result = asyncio.run(namespace["_extract_text_from_upload"](_FakeUploadFile(b"%PDF-1.4 demo")))
    debug = _response_shaping_debug(
        {
            "review_required": True,
            "critical_field_states": {"bin_tin": "missing"},
            "extraction_artifacts_v1": result["artifacts"],
        }
    )

    assert debug["stage_attempts"][0]["input_mime"] == "application/pdf"
    assert debug["stage_attempts"][1]["normalized_mime"] in {"image/tiff", "image/png"}
