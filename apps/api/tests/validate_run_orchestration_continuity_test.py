from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest
from fastapi import HTTPException
from starlette import status


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

VALIDATE_RUN_PATH = ROOT / "app" / "routers" / "validate_run.py"
REQUEST_PARSING_PATH = ROOT / "app" / "routers" / "validation" / "request_parsing.py"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _JsonOnlyRequest:
    def __init__(self, payload: dict):
        self.headers = {"content-type": "application/json"}
        self._payload = payload

    async def json(self):
        return self._payload


@pytest.mark.asyncio
async def test_request_parsing_module_parses_json_payload_and_derives_runtime_fields() -> None:
    request_parsing = _load_module(REQUEST_PARSING_PATH, "validate_request_parsing_test")
    request_parsing.bind_shared(
        {
            "HTTPException": HTTPException,
            "Request": object,
            "_extract_intake_only": lambda payload: bool(payload.get("intake_only")),
            "json": json,
            "status": status,
            "validate_upload_file": lambda *args, **kwargs: (True, ""),
        }
    )

    request = _JsonOnlyRequest(
        {
            "documentType": "commercial_invoice",
            "document_tags": "{\"invoice\":\"commercial_invoice\"}",
            "metadata": "{\"lcNumber\":\"LC-001\"}",
            "intake_only": True,
        }
    )

    parsed = await request_parsing.parse_validate_request(request)

    assert parsed.doc_type == "commercial_invoice"
    assert parsed.intake_only is True
    assert parsed.payload["document_type"] == "commercial_invoice"
    assert parsed.payload["document_tags"] == {"invoice": "commercial_invoice"}
    assert parsed.payload["metadata"] == {"lcNumber": "LC-001"}
    assert parsed.files_list == []


def test_validate_run_route_delegates_to_extracted_request_and_pipeline_modules() -> None:
    source = VALIDATE_RUN_PATH.read_text(encoding="utf-8")

    assert "await parse_validate_request(request)" in source
    assert "await run_validate_pipeline(" in source
    assert "await request.form()" not in source
    assert "payload = await request.json()" not in source
