from __future__ import annotations

import ast
from datetime import date, datetime
from pathlib import Path
from types import MethodType, SimpleNamespace
from typing import Any, Dict


ROOT = Path(__file__).resolve().parents[1]
CROSSDOC_VALIDATOR_PATH = ROOT / "app" / "services" / "validation" / "crossdoc_validator.py"


def _load_crossdoc_reference_symbols() -> Dict[str, Any]:
    source = CROSSDOC_VALIDATOR_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)
    selected_nodes: list[ast.AST] = []

    for node in parsed.body:
        if isinstance(node, ast.ClassDef) and node.name == "CrossDocValidator":
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name in {
                    "_parse_date",
                    "_resolve_validation_reference_date",
                    "_check_lc_expiry",
                    "_check_article_16_timing",
                }:
                    selected_nodes.append(item)

    module_ast = ast.Module(body=selected_nodes, type_ignores=[])
    ast.fix_missing_locations(module_ast)

    namespace: Dict[str, Any] = {
        "Any": Any,
        "Dict": Dict,
        "List": list,
        "Optional": Any,
        "date": date,
        "datetime": datetime,
        "timedelta": __import__("datetime").timedelta,
        "CrossDocIssue": lambda **kwargs: kwargs,
        "IssueSeverity": SimpleNamespace(CRITICAL="critical", MAJOR="major"),
        "DocumentType": SimpleNamespace(LC="letter_of_credit", BILL_OF_LADING="bill_of_lading"),
        "logger": SimpleNamespace(warning=lambda *args, **kwargs: None),
    }
    exec(compile(module_ast, str(CROSSDOC_VALIDATOR_PATH), "exec"), namespace)
    return namespace


def _build_validator_shim(ns: Dict[str, Any]) -> Any:
    class _Shim:
        pass

    shim = _Shim()
    for name in (
        "_parse_date",
        "_resolve_validation_reference_date",
        "_check_lc_expiry",
        "_check_article_16_timing",
    ):
        setattr(shim, name, MethodType(ns[name], shim))
    return shim


def test_lc_expiry_skips_without_explicit_reference_date() -> None:
    ns = _load_crossdoc_reference_symbols()
    validator = _build_validator_shim(ns)

    issue = validator._check_lc_expiry({"expiry_date": "2026-03-31"})

    assert issue is None


def test_lc_expiry_warns_when_bank_reference_date_is_close() -> None:
    ns = _load_crossdoc_reference_symbols()
    validator = _build_validator_shim(ns)

    issue = validator._check_lc_expiry(
        {
            "expiry_date": "2026-03-31",
            "date_received": "2026-03-26",
        }
    )

    assert issue is not None
    assert issue["rule_id"] == "CROSSDOC-LC-002"


def test_article_16_timing_skips_without_explicit_reference_date() -> None:
    ns = _load_crossdoc_reference_symbols()
    validator = _build_validator_shim(ns)

    issue = validator._check_article_16_timing(
        {"on_board_date": "2026-03-01"},
        {"presentation_period": 21, "expiry_date": "2026-03-31"},
    )

    assert issue is None


def test_article_16_timing_uses_bank_date_received_as_reference_date() -> None:
    ns = _load_crossdoc_reference_symbols()
    validator = _build_validator_shim(ns)

    issue = validator._check_article_16_timing(
        {"on_board_date": "2026-03-01"},
        {
            "presentation_period": 21,
            "expiry_date": "2026-03-31",
            "bank_metadata": {"date_received": "2026-03-26"},
        },
    )

    assert issue is not None
    assert issue["rule_id"] == "CROSSDOC-TIMING-001"
