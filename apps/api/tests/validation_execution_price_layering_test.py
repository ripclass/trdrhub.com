from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict


ROOT = Path(__file__).resolve().parents[1]
VALIDATION_EXECUTION_PATH = ROOT / "app" / "routers" / "validation" / "validation_execution.py"


def _load_symbols() -> Dict[str, Any]:
    source = VALIDATION_EXECUTION_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)
    selected_nodes: list[ast.AST] = []

    for node in parsed.body:
        if isinstance(node, ast.FunctionDef) and node.name == "_filter_price_issues_for_documentary_context":
            selected_nodes.append(node)

    module_ast = ast.Module(body=selected_nodes, type_ignores=[])
    ast.fix_missing_locations(module_ast)
    namespace: Dict[str, Any] = {
        "Any": Any,
    }
    exec(compile(module_ast, str(VALIDATION_EXECUTION_PATH), "exec"), namespace)
    return namespace


def test_validation_execution_drops_price_findings_when_goods_mismatch_already_exists() -> None:
    fn = _load_symbols()["_filter_price_issues_for_documentary_context"]

    filtered = fn(
        existing_issues=[
            {"rule_id": "CROSSDOC-INV-003", "title": "Invoice Goods Description Mismatch"},
        ],
        price_issues=[
            {"rule": "PRICE-VERIFY-2", "title": "Significant Price Discrepancy"},
        ],
    )

    assert filtered == []


def test_validation_execution_drops_price_findings_when_goods_mismatch_exists_as_object() -> None:
    fn = _load_symbols()["_filter_price_issues_for_documentary_context"]

    filtered = fn(
        existing_issues=[
            SimpleNamespace(rule_id="CROSSDOC-INV-003", title="Invoice Goods Description Mismatch"),
        ],
        price_issues=[
            {"rule": "PRICE-VERIFY-2", "title": "Significant Price Discrepancy"},
        ],
    )

    assert filtered == []


def test_validation_execution_keeps_price_findings_without_documentary_goods_mismatch() -> None:
    fn = _load_symbols()["_filter_price_issues_for_documentary_context"]

    price_issues = [
        {"rule": "PRICE-VERIFY-2", "title": "Significant Price Discrepancy"},
    ]
    filtered = fn(
        existing_issues=[
            {"rule_id": "CROSSDOC-AMOUNT-1", "title": "Invoice Amount Exceeds LC Amount"},
        ],
        price_issues=price_issues,
    )

    assert filtered == price_issues
