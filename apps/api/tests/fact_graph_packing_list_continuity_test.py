from __future__ import annotations

import ast
from typing import Any, Dict, List, Optional
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

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


def test_build_document_extraction_v1_preserves_packing_list_fact_graph_v1() -> None:
    response_shaping = _load_response_shaping_symbols()
    documents = [
        {
            "id": "doc-packing",
            "documentType": "packing_list",
            "name": "Packing_List.pdf",
            "status": "warning",
            "extractionStatus": "partial",
            "fact_graph_v1": {
                "version": "fact_graph_v1",
                "document_type": "packing_list",
                "facts": [
                    {
                        "field_name": "gross_weight",
                        "value": "20,400 KGS",
                        "normalized_value": "20,400 KGS",
                        "verification_state": "confirmed",
                    }
                ],
            },
        }
    ]

    payload = response_shaping["build_document_extraction_v1"](documents)
    extracted_doc = payload["documents"][0]

    assert extracted_doc["document_id"] == "doc-packing"
    assert extracted_doc["document_type"] == "packing_list"
    assert extracted_doc["fact_graph_v1"]["document_type"] == "packing_list"
    assert extracted_doc["fact_graph_v1"]["facts"][0]["field_name"] == "gross_weight"


def test_launch_pipeline_packing_list_path_wires_build_packing_list_fact_set() -> None:
    source = Path(ROOT / "app/services/extraction/launch_pipeline.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    packing_process = next(
        node for node in ast.walk(tree)
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "_process_packing_list"
    )

    build_calls = [
        node for node in ast.walk(packing_process)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "build_packing_list_fact_set"
    ]

    assert len(build_calls) == 3
    assert '"fact_graph_v1"' in ast.get_source_segment(source, packing_process)
