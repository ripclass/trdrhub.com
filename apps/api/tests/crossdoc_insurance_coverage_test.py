from __future__ import annotations

import ast
from pathlib import Path
from types import MethodType, SimpleNamespace
from typing import Any, Dict


ROOT = Path(__file__).resolve().parents[1]
CROSSDOC_VALIDATOR_PATH = ROOT / "app" / "services" / "validation" / "crossdoc_validator.py"


def _load_crossdoc_insurance_symbols() -> Dict[str, Any]:
    source = CROSSDOC_VALIDATOR_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)
    selected_nodes: list[ast.AST] = []

    for node in parsed.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "_NUMERIC_EPSILON":
                    selected_nodes.append(node)
                    break
        if isinstance(node, ast.ClassDef) and node.name == "CrossDocValidator":
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name in {
                    "_parse_amount",
                    "_resolve_insurance_coverage_ratio",
                    "_check_insurance_amount",
                }:
                    selected_nodes.append(item)

    module_ast = ast.Module(body=selected_nodes, type_ignores=[])
    ast.fix_missing_locations(module_ast)

    namespace: Dict[str, Any] = {
        "Any": Any,
        "Dict": Dict,
        "List": list,
        "Optional": Any,
        "CrossDocIssue": lambda **kwargs: kwargs,
        "IssueSeverity": SimpleNamespace(MAJOR="major"),
        "DocumentType": SimpleNamespace(INSURANCE="insurance_certificate", LC="letter_of_credit"),
        "_INSURANCE_REQUIREMENT_TYPES": {"insurance_certificate", "insurance_policy"},
        "re": __import__("re"),
    }
    exec(compile(module_ast, str(CROSSDOC_VALIDATOR_PATH), "exec"), namespace)
    return namespace


def _build_validator_shim(ns: Dict[str, Any]) -> Any:
    class _Shim:
        pass

    shim = _Shim()
    for name in (
        "_parse_amount",
        "_resolve_insurance_coverage_ratio",
        "_check_insurance_amount",
    ):
        setattr(shim, name, MethodType(ns[name], shim))
    return shim


def test_check_insurance_amount_uses_insured_amount_and_graph_requirement() -> None:
    ns = _load_crossdoc_insurance_symbols()
    validator = _build_validator_shim(ns)

    issue = validator._check_insurance_amount(
        {
            "insured_amount": "150000",
            "currency": "USD",
        },
        {
            "amount": "150000",
            "currency": "USD",
            "requirements_graph_v1": {
                "version": "requirements_graph_v1",
                "required_documents": [
                    {
                        "code": "insurance_certificate",
                        "raw_text": "Insurance Certificate for 110% of invoice value",
                    }
                ],
            },
        },
    )

    assert issue is not None
    assert issue["rule_id"] == "CROSSDOC-INSURANCE-1"
    assert issue["severity"] == "major"
    assert issue["expected"] == ">= 165,000.00 (110% of LC amount)"
    assert issue["found"] == "150,000.00"


def test_check_insurance_amount_passes_when_required_coverage_is_met() -> None:
    ns = _load_crossdoc_insurance_symbols()
    validator = _build_validator_shim(ns)

    issue = validator._check_insurance_amount(
        {
            "insured_amount": "165000",
            "currency": "USD",
        },
        {
            "amount": "150000",
            "currency": "USD",
            "requirements_graph_v1": {
                "version": "requirements_graph_v1",
                "required_documents": [
                    {
                        "code": "insurance_certificate",
                        "raw_text": "Insurance Certificate for 110% of invoice value",
                    }
                ],
            },
        },
    )

    assert issue is None
