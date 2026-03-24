from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


ROOT = Path(__file__).resolve().parents[1]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

LAUNCH_PIPELINE_PATH = ROOT / "app" / "services" / "extraction" / "launch_pipeline.py"
STRUCTURED_BUILDER_PATH = ROOT / "app" / "services" / "extraction" / "structured_lc_builder.py"
RESPONSE_SHAPING_PATH = ROOT / "app" / "routers" / "validation" / "response_shaping.py"


def _load_module(path: Path, name: str):
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
    namespace: Dict[str, Any] = {"Any": Any, "Dict": Dict, "List": List, "Optional": Optional}
    exec(compile(module_ast, str(RESPONSE_SHAPING_PATH), "exec"), namespace)
    return namespace


def test_document_extraction_v1_preserves_fact_graph() -> None:
    response_shaping = _load_response_shaping_symbols()
    payload = response_shaping["build_document_extraction_v1"](
        [
            {
                "id": "doc-invoice-1",
                "documentType": "commercial_invoice",
                "name": "Invoice.pdf",
                "status": "warning",
                "extractionStatus": "partial",
                "fact_graph_v1": {
                    "version": "fact_graph_v1",
                    "document_type": "commercial_invoice",
                    "document_subtype": "commercial_invoice",
                    "facts": [{"field_name": "invoice_number", "verification_state": "confirmed"}],
                },
            }
        ]
    )

    assert payload["documents"][0]["fact_graph_v1"]["facts"][0]["field_name"] == "invoice_number"


def test_structured_documents_normalization_preserves_fact_graph() -> None:
    structured_builder = _load_module(STRUCTURED_BUILDER_PATH, "fact_graph_structured_builder")
    docs = structured_builder._normalize_documents_structured(
        [
            {
                "document_id": "doc-invoice-1",
                "document_type": "commercial_invoice",
                "filename": "Invoice.pdf",
                "extraction_status": "success",
                "fact_graph_v1": {
                    "version": "fact_graph_v1",
                    "document_type": "commercial_invoice",
                    "document_subtype": "commercial_invoice",
                    "facts": [{"field_name": "invoice_date", "verification_state": "confirmed"}],
                },
            }
        ]
    )

    assert docs[0]["fact_graph_v1"]["facts"][0]["field_name"] == "invoice_date"
    assert docs[0]["factGraphV1"]["facts"][0]["field_name"] == "invoice_date"


def test_launch_pipeline_invoice_path_wires_build_invoice_fact_set() -> None:
    source = LAUNCH_PIPELINE_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)

    process_invoice = None
    for node in parsed.body:
        if isinstance(node, ast.ClassDef) and node.name == "LaunchExtractionPipeline":
            for child in node.body:
                if isinstance(child, ast.AsyncFunctionDef) and child.name == "_process_invoice":
                    process_invoice = child
                    break
    assert process_invoice is not None

    build_calls = [
        node
        for node in ast.walk(process_invoice)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "build_invoice_fact_set"
    ]
    assert len(build_calls) == 3

    fact_graph_constants = {
        node.value
        for node in ast.walk(process_invoice)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    assert "fact_graph_v1" in fact_graph_constants
