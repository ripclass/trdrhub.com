from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Dict


VALIDATION_EXECUTION_PATH = Path(
    "apps/api/app/routers/validation/validation_execution.py"
)


def _load_insurance_rule_context_symbols() -> Dict[str, Any]:
    source = VALIDATION_EXECUTION_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)
    selected_nodes = []

    for node in parsed.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (
                    isinstance(target, ast.Name)
                    and target.id == "_INSURANCE_RULE_DOCUMENT_TYPES"
                ):
                    selected_nodes.append(node)
                    break
        elif isinstance(node, ast.FunctionDef) and node.name in {
            "_insurance_document_type",
            "_resolve_insurance_rule_context",
        }:
            selected_nodes.append(node)

    module_ast = ast.Module(body=selected_nodes, type_ignores=[])
    ast.fix_missing_locations(module_ast)

    namespace: Dict[str, Any] = {
        "Any": Any,
        "Dict": Dict,
        "materialize_document_fact_graph_v1": lambda document: {
            "version": "fact_graph_v1",
            "facts": [
                {
                    "field_name": "originals_presented",
                    "normalized_value": 1,
                    "verification_state": "confirmed",
                }
            ],
        },
        "project_insurance_validation_context": (
            lambda base_context, *, document=None, fact_graph=None: {
                "originals_presented": 1,
                "fact_graph_v1": fact_graph,
                "document_name": (document or {}).get("filename"),
            }
        ),
    }
    exec(compile(module_ast, str(VALIDATION_EXECUTION_PATH), "exec"), namespace)
    return namespace


def test_resolve_insurance_rule_context_rebuilds_alias_from_document_list() -> None:
    namespace = _load_insurance_rule_context_symbols()
    resolve_insurance_rule_context = namespace["_resolve_insurance_rule_context"]

    insurance_document = {
        "documentType": "insurance_certificate",
        "filename": "Insurance_Certificate.pdf",
        "extracted_fields": {"insured_amount": "111100"},
        "extraction_artifacts_v1": {"raw_text": "Presented Originals: 1"},
    }
    payload = {"documents": [insurance_document]}
    extracted_context = {"documents": [dict(insurance_document)]}

    resolved = resolve_insurance_rule_context(payload, extracted_context)

    assert resolved["originals_presented"] == 1
    assert payload["insurance"]["originals_presented"] == 1
    assert payload["insurance_certificate"]["originals_presented"] == 1
    assert extracted_context["insurance"]["originals_presented"] == 1
    assert extracted_context["insurance_certificate"]["originals_presented"] == 1
