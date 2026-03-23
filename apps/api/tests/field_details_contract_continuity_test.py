from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
AI_FIRST_PATH = ROOT / "app" / "services" / "extraction" / "ai_first_extractor.py"
STRUCTURED_BUILDER_PATH = ROOT / "app" / "services" / "extraction" / "structured_lc_builder.py"
RESPONSE_SHAPING_PATH = ROOT / "app" / "routers" / "validation" / "response_shaping.py"


def _load_module(path: Path, name: str):
    root_str = str(ROOT)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _load_response_shaping_symbols() -> Dict[str, Any]:
    source = RESPONSE_SHAPING_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)
    target_functions = {"_normalize_doc_status", "summarize_document_statuses", "build_document_extraction_v1"}
    selected_nodes = [
        node
        for node in parsed.body
        if isinstance(node, ast.FunctionDef) and node.name in target_functions
    ]
    module_ast = ast.Module(body=selected_nodes, type_ignores=[])
    ast.fix_missing_locations(module_ast)
    namespace: Dict[str, Any] = {"Dict": Dict, "Any": Any, "List": List}
    exec(compile(module_ast, str(RESPONSE_SHAPING_PATH), "exec"), namespace)
    return namespace


def test_default_field_details_confirm_text_supported_values() -> None:
    ai_first = _load_module(AI_FIRST_PATH, "field_details_ai_first")

    wrapped = {
        "invoice_number": {"value": "INV-2026-001", "confidence": 0.91},
        "currency": {"value": "USD", "confidence": 0.82},
    }

    details = ai_first._build_default_field_details_from_wrapped_result(
        wrapped,
        source="multimodal:pdf_pages",
        raw_text="Commercial Invoice\nInvoice Number: INV-2026-001\nCurrency: USD\n",
    )

    assert details["invoice_number"]["verification"] == "confirmed"
    assert details["invoice_number"]["status"] == "trusted"
    assert details["invoice_number"]["evidence"]["snippet"].startswith("Commercial Invoice")
    assert details["currency"]["verification"] == "confirmed"


def test_document_extraction_v1_preserves_field_details() -> None:
    response_shaping = _load_response_shaping_symbols()
    payload = response_shaping["build_document_extraction_v1"](
        [
            {
                "id": "doc-1",
                "documentType": "commercial_invoice",
                "name": "Invoice.pdf",
                "status": "warning",
                "extractionStatus": "partial",
                "extractedFields": {"invoice_number": "INV-2026-001"},
                "fieldDetails": {
                    "invoice_number": {
                        "value": "INV-2026-001",
                        "confidence": 0.91,
                        "verification": "confirmed",
                    }
                },
            }
        ]
    )

    assert payload["documents"][0]["field_details"]["invoice_number"]["verification"] == "confirmed"


def test_structured_documents_normalization_preserves_field_details() -> None:
    structured_builder = _load_module(STRUCTURED_BUILDER_PATH, "field_details_structured_builder")
    docs = structured_builder._normalize_documents_structured(
        [
            {
                "document_id": "doc-1",
                "document_type": "commercial_invoice",
                "filename": "Invoice.pdf",
                "extraction_status": "success",
                "extracted_fields": {"invoice_number": "INV-2026-001"},
                "field_details": {
                    "invoice_number": {
                        "value": "INV-2026-001",
                        "confidence": 0.91,
                        "verification": "confirmed",
                    }
                },
            }
        ]
    )

    assert docs[0]["field_details"]["invoice_number"]["verification"] == "confirmed"
    assert docs[0]["fieldDetails"]["invoice_number"]["verification"] == "confirmed"
