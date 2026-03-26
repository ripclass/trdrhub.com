from __future__ import annotations

import ast
import re
from pathlib import Path
from types import MethodType, SimpleNamespace
from typing import Any, Dict, Optional, Set


ROOT = Path(__file__).resolve().parents[1]
CROSSDOC_VALIDATOR_PATH = ROOT / "app" / "services" / "validation" / "crossdoc_validator.py"


def _load_crossdoc_goods_symbols() -> Dict[str, Any]:
    source = CROSSDOC_VALIDATOR_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)
    selected_nodes: list[ast.AST] = []

    for node in parsed.body:
        if isinstance(node, ast.ClassDef) and node.name == "CrossDocValidator":
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name in {
                    "_extract_hs_codes",
                    "_check_invoice_goods",
                }:
                    selected_nodes.append(item)

    module_ast = ast.Module(body=selected_nodes, type_ignores=[])
    ast.fix_missing_locations(module_ast)
    namespace: Dict[str, Any] = {
        "Any": Any,
        "Dict": Dict,
        "Optional": Optional,
        "Set": Set,
        "re": re,
        "CrossDocIssue": lambda **kwargs: kwargs,
        "IssueSeverity": SimpleNamespace(MAJOR="major"),
        "DocumentType": SimpleNamespace(INVOICE="commercial_invoice", LC="letter_of_credit"),
        "VALIDATION": SimpleNamespace(),
        "SIMILARITY": SimpleNamespace(GOODS=0.35),
        "logger": SimpleNamespace(info=lambda *args, **kwargs: None),
    }
    exec(compile(module_ast, str(CROSSDOC_VALIDATOR_PATH), "exec"), namespace)
    return namespace


def test_invoice_goods_check_flags_conflicting_hs_codes_even_when_product_terms_overlap() -> None:
    ns = _load_crossdoc_goods_symbols()

    class _Shim:
        @staticmethod
        def _normalize_text(value: Any) -> str:
            return str(value or "").strip()

        @staticmethod
        def _check_key_product_terms(_text1: str, _text2: str) -> bool:
            return True

        @staticmethod
        def _text_similarity(_text1: str, _text2: str) -> float:
            return 1.0

    shim = _Shim()
    shim._extract_hs_codes = MethodType(ns["_extract_hs_codes"], shim)
    shim._check_invoice_goods = MethodType(ns["_check_invoice_goods"], shim)

    issue = shim._check_invoice_goods(
        {"goods_description": "Polyester Blend T-Shirts, HS Code 6109.90"},
        {"goods_description": "100% Cotton T-Shirts, HS Code 6109.10"},
    )

    assert issue is not None
    assert issue["rule_id"] == "CROSSDOC-INV-003"
    assert issue["title"] == "Invoice Goods Description Mismatch"
    assert "conflicting HS codes" in issue["message"]
