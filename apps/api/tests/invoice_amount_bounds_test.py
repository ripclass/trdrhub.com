from __future__ import annotations

import ast
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


ROOT = Path(__file__).resolve().parents[1]
VALIDATE_PATH = ROOT / "app" / "routers" / "validate.py"


def _load_amount_bound_symbols() -> Dict[str, Any]:
    source = VALIDATE_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)
    selected_nodes: List[ast.AST] = []

    for node in parsed.body:
        if isinstance(node, ast.FunctionDef) and node.name in {
            "_coerce_decimal",
            "_resolve_invoice_amount_tolerance_percent",
            "_compute_invoice_amount_bounds",
        }:
            selected_nodes.append(node)

    module_ast = ast.Module(body=selected_nodes, type_ignores=[])
    ast.fix_missing_locations(module_ast)
    namespace: Dict[str, Any] = {
        "Any": Any,
        "Dict": Dict,
        "List": List,
        "Optional": Optional,
        "Tuple": Tuple,
        "Decimal": Decimal,
    }
    exec(compile(module_ast, str(VALIDATE_PATH), "exec"), namespace)
    return namespace


def test_compute_invoice_amount_bounds_defaults_to_zero_without_explicit_tolerance() -> None:
    ns = _load_amount_bound_symbols()
    compute_invoice_amount_bounds = ns["_compute_invoice_amount_bounds"]

    tolerance_value, amount_limit = compute_invoice_amount_bounds(
        {
            "lc": {
                "amount": 100000,
            }
        }
    )

    assert tolerance_value == 0.0
    assert amount_limit == 100000.0


def test_compute_invoice_amount_bounds_prefers_requirements_graph_tolerance() -> None:
    ns = _load_amount_bound_symbols()
    compute_invoice_amount_bounds = ns["_compute_invoice_amount_bounds"]

    tolerance_value, amount_limit = compute_invoice_amount_bounds(
        {
            "lc": {
                "amount": 100000,
                "requirements_graph_v1": {
                    "tolerances": {
                        "amount": {
                            "tolerance_percent": 10,
                        }
                    }
                },
            }
        }
    )

    assert tolerance_value == 10000.0
    assert amount_limit == 110000.0
