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


def test_document_extraction_v1_preserves_supporting_fact_graph() -> None:
    response_shaping = _load_response_shaping_symbols()
    payload = response_shaping["build_document_extraction_v1"](
        [
            {
                "id": "doc-supporting-1",
                "documentType": "shipment_advice",
                "name": "Shipment_Advice.pdf",
                "status": "warning",
                "extractionStatus": "partial",
                "fact_graph_v1": {
                    "version": "fact_graph_v1",
                    "document_type": "shipment_advice",
                    "document_subtype": "shipment_advice",
                    "facts": [{"field_name": "document_reference", "verification_state": "confirmed"}],
                },
            }
        ]
    )

    assert payload["documents"][0]["fact_graph_v1"]["facts"][0]["field_name"] == "document_reference"


def test_launch_pipeline_supporting_path_wires_build_supporting_fact_set() -> None:
    source = LAUNCH_PIPELINE_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)

    process_supporting = None
    for node in parsed.body:
        if isinstance(node, ast.ClassDef) and node.name == "LaunchExtractionPipeline":
            for child in node.body:
                if isinstance(child, ast.AsyncFunctionDef) and child.name == "_process_supporting_document":
                    process_supporting = child
                    break
    assert process_supporting is not None

    build_calls = [
        node
        for node in ast.walk(process_supporting)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "build_supporting_fact_set"
    ]
    assert len(build_calls) == 1

    supporting_constants = {
        node.value
        for node in ast.walk(process_supporting)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    assert "fact_graph_v1" in supporting_constants


def _load_launch_pipeline_symbols() -> Dict[str, Any]:
    source = LAUNCH_PIPELINE_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)
    target_assignments = {
        "TRANSPORT_DOC_ALIASES",
        "REGULATORY_DOC_ALIASES",
        "INSURANCE_DOC_ALIASES",
        "INSPECTION_DOC_ALIASES",
    }
    selected_nodes = []
    for node in parsed.body:
        if isinstance(node, ast.Assign):
            target_names = {
                target.id
                for target in node.targets
                if isinstance(target, ast.Name)
            }
            if target_names & target_assignments:
                selected_nodes.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name == "_canonicalize_launch_doc_type":
            selected_nodes.append(node)

    module_ast = ast.Module(body=selected_nodes, type_ignores=[])
    ast.fix_missing_locations(module_ast)
    namespace: Dict[str, Any] = {}
    exec(compile(module_ast, str(LAUNCH_PIPELINE_PATH), "exec"), namespace)
    return namespace


def test_launch_pipeline_canonicalize_preserves_transport_subtypes() -> None:
    namespace = _load_launch_pipeline_symbols()
    canonicalize = namespace["_canonicalize_launch_doc_type"]

    assert canonicalize("air_waybill") == "air_waybill"
    assert canonicalize("sea_waybill") == "sea_waybill"
    assert canonicalize("road_transport_document") == "road_transport_document"


def test_launch_pipeline_canonicalize_preserves_non_transport_supporting_subtypes() -> None:
    namespace = _load_launch_pipeline_symbols()
    canonicalize = namespace["_canonicalize_launch_doc_type"]

    assert canonicalize("veterinary_certificate") == "veterinary_certificate"
    assert canonicalize("lab_test_report") == "lab_test_report"
    assert canonicalize("conformity_certificate") == "conformity_certificate"
