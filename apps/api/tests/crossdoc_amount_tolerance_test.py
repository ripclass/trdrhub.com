from __future__ import annotations

import ast
from pathlib import Path
from types import MethodType
from typing import Any, Dict, List, Optional


ROOT = Path(__file__).resolve().parents[1]
CROSSDOC_VALIDATOR_PATH = ROOT / "app" / "services" / "validation" / "crossdoc_validator.py"


def _load_crossdoc_amount_symbols() -> Dict[str, Any]:
    source = CROSSDOC_VALIDATOR_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)
    selected_nodes: List[ast.AST] = []

    for node in parsed.body:
        if isinstance(node, ast.ClassDef) and node.name == "CrossDocValidator":
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name in {
                    "_coerce_tolerance_fraction",
                    "_resolve_amount_tolerance",
                    "_parse_amount",
                    "_check_invoice_amount",
                }:
                    selected_nodes.append(item)

    module_ast = ast.Module(body=selected_nodes, type_ignores=[])
    ast.fix_missing_locations(module_ast)
    namespace: Dict[str, Any] = {
        "Any": Any,
        "Dict": Dict,
        "List": List,
        "Optional": Optional,
        "CrossDocIssue": lambda **kwargs: kwargs,
        "IssueSeverity": type("IssueSeverity", (), {"CRITICAL": "critical"}),
        "DocumentType": type(
            "DocumentType",
            (),
            {"INVOICE": type("Invoice", (), {"value": "commercial_invoice"})(), "LC": type("LC", (), {"value": "letter_of_credit"})()},
        ),
        "re": __import__("re"),
    }
    exec(compile(module_ast, str(CROSSDOC_VALIDATOR_PATH), "exec"), namespace)
    return namespace


def _build_validator_shim(ns: Dict[str, Any], amount_tolerance: float = 0.0) -> Any:
    class _Shim:
        pass

    shim = _Shim()
    shim.amount_tolerance = amount_tolerance
    for name in (
        "_coerce_tolerance_fraction",
        "_resolve_amount_tolerance",
        "_parse_amount",
        "_check_invoice_amount",
    ):
        setattr(shim, name, MethodType(ns[name], shim))
    return shim


def test_check_invoice_amount_defaults_to_zero_tolerance_when_lc_has_none() -> None:
    ns = _load_crossdoc_amount_symbols()
    validator = _build_validator_shim(ns)

    issue = validator._check_invoice_amount(
        {"amount": 105000.0},
        {"amount": 100000.0},
    )

    assert issue is not None
    assert issue["rule_id"] == "CROSSDOC-AMOUNT-1"
    assert issue["tolerance_applied"] == 0.0


def test_check_invoice_amount_respects_requirements_graph_tolerance() -> None:
    ns = _load_crossdoc_amount_symbols()
    validator = _build_validator_shim(ns)

    issue = validator._check_invoice_amount(
        {"amount": 105000.0},
        {
            "amount": 100000.0,
            "requirements_graph_v1": {
                "tolerances": {
                    "amount": {
                        "tolerance_percent": 10,
                    }
                }
            },
        },
    )

    assert issue is None
