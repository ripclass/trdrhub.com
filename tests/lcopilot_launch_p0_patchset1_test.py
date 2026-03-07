from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
VALIDATE_PATH = ROOT / "apps" / "api" / "app" / "routers" / "validate.py"
STRUCTURED_BUILDER_PATH = (
    ROOT / "apps" / "api" / "app" / "services" / "extraction" / "structured_lc_builder.py"
)


def _load_module_from_path(module_name: str, module_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec and spec.loader, f"Unable to load module from {module_path}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_validate_function(function_name: str):
    source = VALIDATE_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)

    selected = [
        node
        for node in parsed.body
        if isinstance(node, ast.FunctionDef) and node.name == function_name
    ]
    assert selected, f"Missing function {function_name}"

    module_ast = ast.Module(body=selected, type_ignores=[])
    ast.fix_missing_locations(module_ast)

    namespace = {
        "Any": Any,
        "Dict": Dict,
        "List": List,
    }
    exec(compile(module_ast, str(VALIDATE_PATH), "exec"), namespace)
    return namespace[function_name]


def test_structured_builder_handles_list_timeline_and_keeps_top_level_aliases():
    builder = _load_module_from_path("structured_builder_patchset1", STRUCTURED_BUILDER_PATH)

    result = builder.build_unified_structured_result(
        session_documents=[
            {
                "id": "doc-1",
                "document_type": "commercial_invoice",
                "filename": "Invoice.pdf",
                "extraction_status": "success",
                "extracted_fields": {"amount": "1000"},
            }
        ],
        extractor_outputs={
            "timeline": [],
            "issues": [],
        },
        legacy_payload=None,
    )["structured_result"]

    assert result["documents"] == result["documents_structured"]
    assert result["timeline"]
    assert result["timeline"][0]["title"] == "Documents Uploaded"


def test_sync_structured_result_collections_backfills_documents_and_timeline():
    sync_collections = _load_validate_function("_sync_structured_result_collections")

    structured_result = {
        "lc_structured": {
            "documents_structured": [
                {
                    "document_id": "doc-1",
                    "document_type": "bill_of_lading",
                    "filename": "BL.pdf",
                }
            ],
            "timeline": [{"title": "OCR Complete", "status": "success"}],
        }
    }

    sync_collections(structured_result)

    assert structured_result["documents"] == structured_result["documents_structured"]
    assert structured_result["documents"][0]["document_type"] == "bill_of_lading"
    assert structured_result["timeline"][0]["title"] == "OCR Complete"


def test_validate_route_applies_bank_policy_to_real_deduplicated_results():
    source = VALIDATE_PATH.read_text(encoding="utf-8")

    assert "validation_results=deduplicated_results" in source
    assert "validation_results=results" not in source
