from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Dict, List, Optional
import sys


ROOT = Path(__file__).resolve().parents[1]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

LAUNCH_PIPELINE_PATH = ROOT / "app" / "services" / "extraction" / "launch_pipeline.py"
RESPONSE_SHAPING_PATH = ROOT / "app" / "routers" / "validation" / "response_shaping.py"


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


def test_document_extraction_v1_preserves_inspection_fact_graph() -> None:
    response_shaping = _load_response_shaping_symbols()
    payload = response_shaping["build_document_extraction_v1"](
        [
            {
                "id": "doc-inspection-1",
                "documentType": "inspection_certificate",
                "name": "Inspection_Certificate.pdf",
                "status": "warning",
                "extractionStatus": "partial",
                "fact_graph_v1": {
                    "version": "fact_graph_v1",
                    "document_type": "inspection_certificate",
                    "document_subtype": "inspection_certificate",
                    "facts": [{"field_name": "inspection_result", "verification_state": "confirmed"}],
                },
            }
        ]
    )

    assert payload["documents"][0]["fact_graph_v1"]["facts"][0]["field_name"] == "inspection_result"


def test_launch_pipeline_inspection_path_wires_build_inspection_fact_set() -> None:
    source = LAUNCH_PIPELINE_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)

    process_inspection = None
    for node in parsed.body:
        if isinstance(node, ast.ClassDef) and node.name == "LaunchExtractionPipeline":
            for child in node.body:
                if isinstance(child, ast.AsyncFunctionDef) and child.name == "_process_inspection_certificate":
                    process_inspection = child
                    break
    assert process_inspection is not None

    build_calls = [
        node
        for node in ast.walk(process_inspection)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "build_inspection_fact_set"
    ]
    assert len(build_calls) == 4

    fact_graph_constants = {
        node.value
        for node in ast.walk(process_inspection)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    assert "fact_graph_v1" in fact_graph_constants
