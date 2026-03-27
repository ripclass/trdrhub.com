from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
RESULT_FINALIZATION_PATH = ROOT / "app" / "routers" / "validation" / "result_finalization.py"


def _load_symbols() -> Dict[str, Any]:
    source = RESULT_FINALIZATION_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)
    selected_nodes: List[ast.AST] = []

    for node in parsed.body:
        if isinstance(node, ast.FunctionDef) and node.name == "_suppress_advisory_findings_for_documentary_context":
            selected_nodes.append(node)

    module_ast = ast.Module(body=selected_nodes, type_ignores=[])
    ast.fix_missing_locations(module_ast)
    namespace: Dict[str, Any] = {
        "Any": Any,
        "Dict": Dict,
        "List": List,
    }
    exec(compile(module_ast, str(RESULT_FINALIZATION_PATH), "exec"), namespace)
    return namespace


def test_result_finalization_suppresses_price_findings_when_goods_mismatch_exists() -> None:
    fn = _load_symbols()["_suppress_advisory_findings_for_documentary_context"]

    filtered = fn(
        [
            {"rule": "CROSSDOC-INV-003", "title": "Invoice Goods Description Mismatch"},
            {"rule": "PRICE-VERIFY-2", "title": "Significant Price Discrepancy"},
        ]
    )

    assert [issue["rule"] for issue in filtered] == ["CROSSDOC-INV-003"]


def test_result_finalization_keeps_price_findings_without_goods_mismatch() -> None:
    fn = _load_symbols()["_suppress_advisory_findings_for_documentary_context"]

    issues = [
        {"rule": "CROSSDOC-AMOUNT-1", "title": "Invoice Amount Exceeds LC Amount"},
        {"rule": "PRICE-VERIFY-2", "title": "Significant Price Discrepancy"},
    ]

    assert fn(issues) == issues

