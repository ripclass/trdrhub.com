from __future__ import annotations

import ast
import asyncio
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
        "_record_extraction_reason_code",
        "_record_extraction_stage",
        "_finalize_text_extraction_result",
        "_merge_text_sources",
        "_scrape_binary_text_metadata",
        "_detect_input_mime_type",
        "_looks_like_plaintext_bytes",
        "_extract_plaintext_bytes",
        "_extract_text_from_upload",
    }
    selected = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in wanted
    ]
    module = ast.Module(
        body=ast.parse(
            "import os\n"
            "from io import BytesIO\n"
            "from typing import Any, Dict, List, Optional\n"
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
        ),
        "TRACE_LOG_LEVEL": 15,
    }
    exec(compile(module, str(path), "exec"), namespace)
    return namespace


def test_detect_input_mime_type_marks_textlike_pdf_as_text_plain():
    namespace = _load_validate_namespace()
    pseudo_pdf = b"COMMERCIAL INVOICE\r\nInvoice Number: INV-2026-001\r\nTOTAL: USD 125,000.00\r\n"

    detected = namespace["_detect_input_mime_type"](pseudo_pdf, "Invoice.pdf", "application/pdf")

    assert detected == "text/plain"


def test_detect_input_mime_type_keeps_real_pdf_magic():
    namespace = _load_validate_namespace()

    detected = namespace["_detect_input_mime_type"](b"%PDF-1.4 test", "doc.pdf", "application/pdf")

    assert detected == "application/pdf"


def test_looks_like_plaintext_bytes_rejects_binary_pdf_signature():
    namespace = _load_validate_namespace()

    assert namespace["_looks_like_plaintext_bytes"](b"%PDF-1.4 binary") is False


def test_extract_plaintext_bytes_decodes_text_payload():
    namespace = _load_validate_namespace()
    text = namespace["_extract_plaintext_bytes"](b"LC NUMBER: EXP2026BD001\r\nAMOUNT: USD 125,000.00\r\n")

    assert "EXP2026BD001" in text


def test_extract_text_from_upload_uses_plaintext_native_and_skips_ocr():
    namespace = _load_validate_namespace()
    pseudo_pdf = (
        b"COMMERCIAL INVOICE\r\n"
        b"Invoice Number: INV-2026-001\r\n"
        b"Invoice Date: 2026-02-15\r\n"
        b"TOTAL AMOUNT: USD 125,000.00\r\n"
    )

    async def fail_ocr(*_args, **_kwargs):
        raise AssertionError("OCR should not be called for text/plain pseudo-pdf bytes")

    namespace["_try_ocr_providers"] = fail_ocr
    namespace["_try_secondary_ocr_adapter"] = fail_ocr

    result = asyncio.run(namespace["_extract_text_from_upload"](_FakeUploadFile(pseudo_pdf, "Invoice.pdf", "application/pdf")))

    assert result["artifacts"]["final_stage"] == "plaintext_native"
    assert "TOTAL AMOUNT" in result["text"]
    assert "ocr_provider_primary" not in result["artifacts"]["attempted_stages"]


def test_extract_text_from_upload_plaintext_empty_still_falls_back_to_binary():
    namespace = _load_validate_namespace()
    namespace["settings"].OCR_MIN_TEXT_CHARS_FOR_SKIP = 5
    namespace["_extract_plaintext_bytes"] = lambda _file_bytes: ""
    namespace["_scrape_binary_text_metadata"] = lambda _file_bytes: "Recovered binary text"
    pseudo_pdf = b"HEADER TEXT\r\nREFERENCE\r\n"

    result = asyncio.run(namespace["_extract_text_from_upload"](_FakeUploadFile(pseudo_pdf, "empty.pdf", "application/pdf")))

    assert result["artifacts"]["final_stage"] == "binary_metadata_scrape"
    assert result["text"] == "Recovered binary text"
