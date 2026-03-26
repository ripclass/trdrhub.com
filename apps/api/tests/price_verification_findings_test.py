from __future__ import annotations

import ast
import asyncio
import logging
import sys
import types
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, List, Optional


ROOT = Path(__file__).resolve().parents[1]
CROSSDOC_PATH = ROOT / "app" / "services" / "crossdoc.py"


def _load_price_symbols() -> Dict[str, Any]:
    source = CROSSDOC_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)
    selected_nodes: List[ast.AST] = []

    for node in parsed.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "DEFAULT_LABELS":
                    selected_nodes.append(node)
                    break
        if isinstance(node, ast.FunctionDef) and node.name in {
            "_coerce_decimal",
            "_coerce_single_numeric_scalar",
            "_build_document_lookup",
            "_resolve_doc_references",
        }:
            selected_nodes.append(node)
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "run_price_verification_checks":
            selected_nodes.append(node)

    module_ast = ast.Module(body=selected_nodes, type_ignores=[])
    ast.fix_missing_locations(module_ast)
    namespace: Dict[str, Any] = {
        "Any": Any,
        "Dict": Dict,
        "List": List,
        "Optional": Optional,
        "Tuple": tuple,
        "Decimal": Decimal,
        "InvalidOperation": InvalidOperation,
        "logger": logging.getLogger("price_verification_findings_test"),
        "re": __import__("re"),
    }
    exec(compile(module_ast, str(CROSSDOC_PATH), "exec"), namespace)
    return namespace


def test_warning_level_price_variance_does_not_surface_as_lc_issue() -> None:
    fake_price_module = types.ModuleType("app.services.price_verification")

    class _FakeService:
        async def resolve_commodity(self, goods_description: str, hs_code: str | None = None) -> Dict[str, Any]:
            return {
                "code": "HS-6109",
                "name": goods_description,
                "unit": "kg",
                "_resolution": {"confidence": 0.95, "source": "fixture"},
            }

        async def verify_price(self, **kwargs: Any) -> Dict[str, Any]:
            return {
                "success": True,
                "verdict": "warning",
                "variance": {"percent": 13.6},
                "risk": {"risk_level": "medium", "risk_flags": []},
                "market_price": {"price": 11.0, "unit": "kg"},
            }

    fake_price_module.get_price_verification_service = lambda: _FakeService()
    sys.modules["app"] = sys.modules.get("app") or types.ModuleType("app")
    sys.modules["app.services"] = sys.modules.get("app.services") or types.ModuleType("app.services")
    sys.modules["app.services.price_verification"] = fake_price_module

    symbols = _load_price_symbols()
    run_price_verification_checks = symbols["run_price_verification_checks"]

    issues = asyncio.run(
        run_price_verification_checks(
            {
                "invoice": {
                    "goods_description": "100% Cotton T-Shirts",
                    "amount": 125000.0,
                    "currency": "USD",
                    "unit_price": 12.5,
                    "quantity": 10000,
                    "unit": "kg",
                },
                "documents": [{"document_type": "commercial_invoice", "filename": "Invoice.pdf"}],
            }
        )
    )

    assert issues == []


def test_fail_level_price_variance_still_surfaces_as_lc_issue() -> None:
    fake_price_module = types.ModuleType("app.services.price_verification")

    class _FakeService:
        async def resolve_commodity(self, goods_description: str, hs_code: str | None = None) -> Dict[str, Any]:
            return {
                "code": "HS-6109",
                "name": goods_description,
                "unit": "kg",
                "_resolution": {"confidence": 0.95, "source": "fixture"},
            }

        async def verify_price(self, **kwargs: Any) -> Dict[str, Any]:
            return {
                "success": True,
                "verdict": "fail",
                "variance": {"percent": 55.0},
                "risk": {"risk_level": "critical", "risk_flags": ["tbml_risk"]},
                "market_price": {"price": 11.0, "unit": "kg"},
            }

    fake_price_module.get_price_verification_service = lambda: _FakeService()
    sys.modules["app"] = sys.modules.get("app") or types.ModuleType("app")
    sys.modules["app.services"] = sys.modules.get("app.services") or types.ModuleType("app.services")
    sys.modules["app.services.price_verification"] = fake_price_module

    symbols = _load_price_symbols()
    run_price_verification_checks = symbols["run_price_verification_checks"]

    issues = asyncio.run(
        run_price_verification_checks(
            {
                "invoice": {
                    "goods_description": "100% Cotton T-Shirts",
                    "amount": 125000.0,
                    "currency": "USD",
                    "unit_price": 17.05,
                    "quantity": 10000,
                    "unit": "kg",
                },
                "documents": [{"document_type": "commercial_invoice", "filename": "Invoice.pdf"}],
            }
        )
    )

    assert len(issues) == 1
    assert issues[0]["rule"] == "PRICE-VERIFY-2"

