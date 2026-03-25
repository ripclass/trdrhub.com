from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
AI_VALIDATOR_PATH = ROOT / "app" / "services" / "validation" / "ai_validator.py"


def _load_ai_validator_symbols() -> Dict[str, Any]:
    source = AI_VALIDATOR_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)
    selected_nodes: List[ast.AST] = []

    for node in parsed.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "_GRAPH_CRITICAL_DOC_TYPES":
                    selected_nodes.append(node)
                    break
        if isinstance(node, ast.FunctionDef) and node.name == "_parse_lc_requirements_from_graph":
            selected_nodes.append(node)

    module_ast = ast.Module(body=selected_nodes, type_ignores=[])
    ast.fix_missing_locations(module_ast)
    namespace: Dict[str, Any] = {
        "Any": Any,
        "Dict": Dict,
        "List": List,
    }
    exec(compile(module_ast, str(AI_VALIDATOR_PATH), "exec"), namespace)
    return namespace


def test_parse_lc_requirements_from_graph_extracts_critical_docs_and_bl_fields() -> None:
    ns = _load_ai_validator_symbols()
    parse_from_graph = ns["_parse_lc_requirements_from_graph"]
    requirements = parse_from_graph(
        {
            "required_document_types": ["inspection_certificate", "beneficiary_certificate"],
            "documentary_conditions": [
                "Bill of lading must show voyage number and gross weight.",
                "Net weight must be shown on transport document.",
            ],
        }
    )

    assert [doc["document_type"] for doc in requirements["required_documents"]] == [
        "inspection_certificate",
        "beneficiary_certificate",
    ]
    assert requirements["bl_must_show"] == ["voyage_number", "gross_weight", "net_weight"]


def test_parse_lc_requirements_from_graph_prefers_structured_bl_field_requirements() -> None:
    ns = _load_ai_validator_symbols()
    parse_from_graph = ns["_parse_lc_requirements_from_graph"]
    requirements = parse_from_graph(
        {
            "required_document_types": ["inspection_certificate"],
            "documentary_conditions": [
                "This condition text should not be needed when structured requirements exist."
            ],
            "condition_requirements": [
                {
                    "requirement_type": "document_field_presence",
                    "document_type": "bill_of_lading",
                    "field_name": "gross_weight",
                },
                {
                    "requirement_type": "document_field_presence",
                    "document_type": "bill_of_lading",
                    "field_name": "voyage_number",
                },
            ],
        }
    )

    assert [doc["document_type"] for doc in requirements["required_documents"]] == [
        "inspection_certificate",
    ]
    assert requirements["bl_must_show"] == ["gross_weight", "voyage_number"]


def test_parse_lc_requirements_from_graph_returns_empty_for_noncritical_graph() -> None:
    ns = _load_ai_validator_symbols()
    parse_from_graph = ns["_parse_lc_requirements_from_graph"]
    requirements = parse_from_graph(
        {
            "required_document_types": ["commercial_invoice", "packing_list"],
            "documentary_conditions": ["Invoice must mention LC number."],
        }
    )

    assert requirements["required_documents"] == []
    assert requirements["bl_must_show"] == []
