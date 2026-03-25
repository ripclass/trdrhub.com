from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


ROOT = Path(__file__).resolve().parents[1]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

from app.services.facts import materialize_document_fact_graph_v1  # noqa: E402

LAUNCH_PIPELINE_PATH = ROOT / "app" / "services" / "extraction" / "launch_pipeline.py"
RESPONSE_SHAPING_PATH = ROOT / "app" / "routers" / "validation" / "response_shaping.py"


def _load_response_shaping_symbols() -> Dict[str, Any]:
    source = RESPONSE_SHAPING_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)
    target_functions = {
        "_normalize_doc_status",
        "_uses_fact_resolution_contract",
        "_is_legacy_extraction_review_reason",
        "sanitize_public_document_contract_v1",
        "summarize_document_statuses",
        "build_document_extraction_v1",
    }
    selected_nodes = [
        node
        for node in parsed.body
        if isinstance(node, ast.FunctionDef) and node.name in target_functions
    ]
    module_ast = ast.Module(body=selected_nodes, type_ignores=[])
    ast.fix_missing_locations(module_ast)
    namespace: Dict[str, Any] = {"Any": Any, "Dict": Dict, "List": List, "Optional": Optional}
    namespace["materialize_document_requirements_graphs_v1"] = lambda documents: documents
    exec(compile(module_ast, str(RESPONSE_SHAPING_PATH), "exec"), namespace)
    return namespace


def test_document_extraction_v1_preserves_lc_fact_graph() -> None:
    response_shaping = _load_response_shaping_symbols()
    payload = response_shaping["build_document_extraction_v1"](
        [
            {
                "id": "doc-lc-1",
                "documentType": "letter_of_credit",
                "name": "LC.pdf",
                "status": "warning",
                "extractionStatus": "partial",
                "fact_graph_v1": {
                    "version": "fact_graph_v1",
                    "document_type": "letter_of_credit",
                    "document_subtype": "letter_of_credit",
                    "facts": [{"field_name": "lc_number", "verification_state": "confirmed"}],
                },
            }
        ]
    )

    assert payload["documents"][0]["fact_graph_v1"]["facts"][0]["field_name"] == "lc_number"


def test_document_extraction_v1_preserves_lc_requirements_graph() -> None:
    response_shaping = _load_response_shaping_symbols()
    payload = response_shaping["build_document_extraction_v1"](
        [
            {
                "id": "doc-lc-1",
                "documentType": "letter_of_credit",
                "name": "LC.pdf",
                "status": "warning",
                "extractionStatus": "partial",
                "requirements_graph_v1": {
                    "version": "requirements_graph_v1",
                    "required_document_types": ["commercial_invoice", "bill_of_lading"],
                    "required_fact_fields": ["lc_number", "amount", "currency"],
                },
            }
        ]
    )

    assert payload["documents"][0]["requirements_graph_v1"]["required_document_types"] == [
        "commercial_invoice",
        "bill_of_lading",
    ]


def test_materialize_document_fact_graph_v1_only_builds_rendered_lc_lane() -> None:
    rendered_document = {
        "document_type": "letter_of_credit",
        "extraction_lane": "document_ai",
        "extracted_fields": {"lc_number": "EXP2026BD001"},
    }
    structured_document = {
        "document_type": "letter_of_credit",
        "extraction_lane": "structured_mt",
        "extracted_fields": {"lc_number": "EXP2026BD001"},
    }

    rendered_fact_graph = materialize_document_fact_graph_v1(rendered_document)
    structured_fact_graph = materialize_document_fact_graph_v1(structured_document)

    assert rendered_fact_graph is not None
    assert rendered_document["fact_graph_v1"]["document_type"] == "letter_of_credit"
    assert structured_fact_graph is None
    assert "fact_graph_v1" not in structured_document


def test_launch_pipeline_lc_path_wires_build_lc_fact_set() -> None:
    source = LAUNCH_PIPELINE_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)

    process_lc = None
    for node in parsed.body:
        if isinstance(node, ast.ClassDef) and node.name == "LaunchExtractionPipeline":
            for child in node.body:
                if isinstance(child, ast.AsyncFunctionDef) and child.name == "_process_lc_like":
                    process_lc = child
                    break
    assert process_lc is not None

    build_calls = [
        node
        for node in ast.walk(process_lc)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "build_lc_fact_set"
    ]
    assert len(build_calls) >= 1

    fact_graph_constants = {
        node.value
        for node in ast.walk(process_lc)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    assert "fact_graph_v1" in fact_graph_constants
    assert "document_ai" in fact_graph_constants
