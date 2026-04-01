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
        if isinstance(node, ast.FunctionDef) and node.name in {
            "_suppress_advisory_findings_for_documentary_context",
            "_retire_legacy_sanctions_block_surface",
            "_resolve_result_user_type",
        }:
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


def test_result_finalization_suppresses_price_findings_when_documentary_goods_overlap_exists() -> None:
    fn = _load_symbols()["_suppress_advisory_findings_for_documentary_context"]

    filtered = fn(
        [
            {
                "rule": "UCP600-18D",
                "title": "Commercial Invoice: Goods Description Must Correspond to LC",
                "overlap_keys": ["invoice.goods_description|lc.goods_description"],
            },
            {"rule": "PRICE-VERIFY-2", "title": "Significant Price Discrepancy"},
        ]
    )

    assert [issue["rule"] for issue in filtered] == ["UCP600-18D"]


def test_result_finalization_keeps_price_findings_without_goods_mismatch() -> None:
    fn = _load_symbols()["_suppress_advisory_findings_for_documentary_context"]

    issues = [
        {"rule": "CROSSDOC-AMOUNT-1", "title": "Invoice Amount Exceeds LC Amount"},
        {"rule": "PRICE-VERIFY-2", "title": "Significant Price Discrepancy"},
    ]

    assert fn(issues) == issues


def test_result_finalization_retires_legacy_sanctions_block_surface() -> None:
    fn = _load_symbols()["_retire_legacy_sanctions_block_surface"]

    structured = {
        "sanctions_screening": {
            "screened": True,
            "matches": 1,
        },
        "sanctions_blocked": True,
        "sanctions_block_reason": "legacy blocker",
    }

    retired = fn(structured)

    assert retired["sanctions_blocked"] is False
    assert retired["sanctions_block_reason"] is None
    assert retired["sanctions_screening"]["legacy_block_surface_retired"] is True


def test_result_finalization_resolves_user_type_from_explicit_request_value() -> None:
    fn = _load_symbols()["_resolve_result_user_type"]

    assert fn("exporter", object()) == "exporter"


def test_result_finalization_resolves_user_type_from_string_role_without_value_attr() -> None:
    fn = _load_symbols()["_resolve_result_user_type"]

    class _User:
        role = "exporter"

    assert fn("", _User()) == "exporter"


def test_result_finalization_resolves_user_type_from_enum_like_role() -> None:
    fn = _load_symbols()["_resolve_result_user_type"]

    class _Role:
        value = "importer"

    class _User:
        role = _Role()

    assert fn(None, _User()) == "importer"
