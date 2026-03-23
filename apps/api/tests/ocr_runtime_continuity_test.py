from __future__ import annotations

import ast
import os
import re
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

import pytest


ROOT = Path(__file__).resolve().parents[1]
OCR_RUNTIME_PATH = ROOT / "app" / "routers" / "validation" / "ocr_runtime.py"


class _DummyLogger:
    def log(self, *args, **kwargs) -> None:
        return None

    def info(self, *args, **kwargs) -> None:
        return None

    def warning(self, *args, **kwargs) -> None:
        return None

    def error(self, *args, **kwargs) -> None:
        return None


def _load_symbols(target_names: set[str]) -> Dict[str, Any]:
    source = OCR_RUNTIME_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)
    selected = [
        node
        for node in parsed.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in target_names
    ]
    module_ast = ast.Module(body=selected, type_ignores=[])
    ast.fix_missing_locations(module_ast)
    namespace: Dict[str, Any] = {
        "Any": Any,
        "Dict": Dict,
        "List": List,
        "Optional": Optional,
        "BytesIO": BytesIO,
        "SimpleNamespace": SimpleNamespace,
        "TRACE_LOG_LEVEL": 5,
        "logger": _DummyLogger(),
        "settings": SimpleNamespace(
            OCR_MIN_TEXT_CHARS_FOR_SKIP=8,
            OCR_NATIVE_TEXT_SOFT_SKIP_CHARS=4,
            OCR_ENABLED=True,
            OCR_MAX_PAGES=10,
            OCR_MAX_BYTES=10_000_000,
        ),
        "os": os,
        "re": re,
    }
    exec(compile(module_ast, str(OCR_RUNTIME_PATH), "exec"), namespace)
    return namespace


class _FakeUpload:
    def __init__(self, payload: bytes, filename: str = "sample.txt", content_type: str = "text/plain") -> None:
        self._payload = payload
        self.filename = filename
        self.content_type = content_type
        self._cursor = 0

    async def read(self) -> bytes:
        self._cursor = len(self._payload)
        return self._payload

    async def seek(self, pos: int) -> None:
        self._cursor = pos


@pytest.mark.asyncio
async def test_extract_text_from_upload_preserves_plaintext_native_path_after_extraction() -> None:
    symbols = _load_symbols(
        {
            "_empty_extraction_artifacts_v1",
            "_extraction_fallback_hotfix_enabled",
            "_record_extraction_reason_code",
            "_record_extraction_stage",
            "_finalize_text_extraction_result",
            "_looks_like_plaintext_bytes",
            "_detect_input_mime_type",
            "_extract_plaintext_bytes",
            "_extract_text_from_upload",
        }
    )
    extract_text_from_upload = symbols["_extract_text_from_upload"]

    upload = _FakeUpload(b"Invoice Number: INV-123\nAmount: 450.00\n")

    result = await extract_text_from_upload(upload, document_type="commercial_invoice")

    assert result["text"] == "Invoice Number: INV-123\nAmount: 450.00"
    assert result["artifacts"]["final_stage"] == "plaintext_native"
    assert result["artifacts"]["selected_stage"] == "plaintext_native"
    assert "plaintext_native" in result["artifacts"]["attempted_stages"]
    assert result["artifacts"]["final_text_length"] == len("Invoice Number: INV-123\nAmount: 450.00")


def test_merge_text_sources_deduplicates_lines_while_preserving_order() -> None:
    symbols = _load_symbols({"_merge_text_sources"})
    merge_text_sources = symbols["_merge_text_sources"]

    merged = merge_text_sources(
        "Invoice Number: INV-123\nAmount: 450.00",
        "Amount: 450.00\nGross Weight: 20 KG",
        "gross   weight: 20 kg\nFinal Note",
    )

    assert merged.splitlines() == [
        "Invoice Number: INV-123",
        "Amount: 450.00",
        "Gross Weight: 20 KG",
        "Final Note",
    ]
