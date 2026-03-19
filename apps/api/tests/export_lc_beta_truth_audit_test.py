from __future__ import annotations

import ast
import asyncio
import importlib.util
import logging
import re
import sys
import types
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


ROOT = Path(__file__).resolve().parents[1]
VALIDATE_PATH = ROOT / "app" / "routers" / "validate.py"
LAUNCH_PIPELINE_PATH = ROOT / "app" / "services" / "extraction" / "launch_pipeline.py"
CROSSDOC_PATH = ROOT / "app" / "services" / "crossdoc.py"
VESSEL_SANCTIONS_PATH = ROOT / "app" / "services" / "vessel_sanctions.py"


def _load_symbols(path: Path, target_names: set[str], *, extra_namespace: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    source = path.read_text(encoding="utf-8")
    parsed = ast.parse(source)
    selected: List[ast.AST] = []
    for node in parsed.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in target_names:
                    selected.append(node)
                    break
        if isinstance(node, ast.FunctionDef) and node.name in target_names:
            selected.append(node)
        if isinstance(node, ast.AsyncFunctionDef) and node.name in target_names:
            selected.append(node)
    module_ast = ast.Module(body=selected, type_ignores=[])
    ast.fix_missing_locations(module_ast)
    namespace: Dict[str, Any] = {
        "Any": Any,
        "Dict": Dict,
        "List": List,
        "Optional": Optional,
        "Tuple": Tuple,
        "Decimal": Decimal,
        "InvalidOperation": InvalidOperation,
        "logging": logging,
        "logger": logging.getLogger("export_lc_beta_truth_audit_test"),
    }
    if extra_namespace:
        namespace.update(extra_namespace)
    exec(compile(module_ast, str(path), "exec"), namespace)
    return namespace


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_day1_invoice_policy_does_not_require_invoice_weights() -> None:
    symbols = _load_symbols(VALIDATE_PATH, {"_day1_policy_for_doc"})
    policy = symbols["_day1_policy_for_doc"]("commercial_invoice")

    assert "gross_weight" not in policy["fields"]
    assert "net_weight" not in policy["fields"]
    assert set(policy["fields"]) == {"issuer", "doc_date", "bin", "tin"}


def test_beneficiary_certificate_completeness_does_not_require_certificate_number() -> None:
    symbols = _load_symbols(
        LAUNCH_PIPELINE_PATH,
        {"_is_populated_field_value", "_assess_required_field_completeness", "_assess_insurance_completeness"},
    )
    assess = symbols["_assess_insurance_completeness"]

    result = assess(
        {
            "issue_date": "2026-04-20",
            "lc_reference": "EXP2026BD001",
            "issuer_name": "BENEFICIARY CERTIFICATE",
        },
        insurance_subtype="beneficiary_certificate",
    )

    assert result["parse_complete"] is True
    assert result["required_found"] >= 1
    assert result["missing_required_fields"] == []
    assert "missing:certificate_number" not in result["review_reasons"]


def test_beneficiary_certificate_shaping_recovers_lc_reference_from_raw_text() -> None:
    symbols = _load_symbols(
        LAUNCH_PIPELINE_PATH,
        {
            "_extract_label_value",
            "_extract_amount_value",
            "_shape_insurance_payload",
        },
        extra_namespace={"re": re, "_apply_canonical_normalization": lambda payload: payload},
    )
    shape = symbols["_shape_insurance_payload"]

    shaped = shape(
        {
            "issuer_name": "BENEFICIARY CERTIFICATE",
            "issue_date": "2026-04-20",
        },
        insurance_subtype="beneficiary_certificate",
        raw_text="BENEFICIARY CERTIFICATE\nLC No: EXP2026BD001\nBUYER PO NO. GBE-44592\n",
    )

    assert shaped["lc_reference"] == "EXP2026BD001"
    assert shaped["lc_number"] == "EXP2026BD001"


def test_coo_completeness_accepts_useful_origin_fields_without_certificate_number() -> None:
    symbols = _load_symbols(
        LAUNCH_PIPELINE_PATH,
        {"_is_populated_field_value", "_assess_required_field_completeness", "_assess_coo_parse_completeness"},
    )
    assess = symbols["_assess_coo_parse_completeness"]

    result = assess(
        {
            "country_of_origin": "Bangladesh",
            "exporter_name": "Dhaka Knitwear & Exports Ltd.",
            "importer_name": "Global Importers Inc.",
            "goods_description": "Knitwear & Woven Garments",
        }
    )

    assert result["parse_complete"] is True
    assert result["has_certificate_number"] is False


def test_regulatory_coo_completeness_does_not_require_certificate_number() -> None:
    symbols = _load_symbols(
        LAUNCH_PIPELINE_PATH,
        {
            "_is_populated_field_value",
            "_assess_required_field_completeness",
            "_assess_coo_parse_completeness",
            "_assess_regulatory_completeness",
        },
    )
    assess = symbols["_assess_regulatory_completeness"]

    result = assess(
        {
            "country_of_origin": "Bangladesh",
            "exporter_name": "Dhaka Knitwear & Exports Ltd.",
            "importer_name": "Global Importers Inc.",
            "goods_description": "Knitwear & Woven Garments",
        },
        regulatory_subtype="certificate_of_origin",
    )

    assert result["parse_complete"] is True
    assert result["missing_required_fields"] == []
    assert "missing:certificate_number" not in result["review_reasons"]


def test_price_verification_skips_when_only_total_invoice_amount_exists() -> None:
    fake_price_module = types.ModuleType("app.services.price_verification")
    service_calls = {"verify_price": 0}

    class _FakeService:
        async def resolve_commodity(self, goods_description: str, hs_code: Optional[str] = None) -> Dict[str, Any]:
            return {
                "code": "HS-TEST",
                "name": goods_description,
                "unit": "kg",
                "category": "general",
                "_resolution": {"confidence": 0.9, "source": "test"},
            }

        async def verify_price(self, **kwargs: Any) -> Dict[str, Any]:
            service_calls["verify_price"] += 1
            return {
                "success": True,
                "verdict": "fail",
                "variance": {"percent": 100.0},
                "risk": {"risk_level": "high", "risk_flags": ["tbml_risk"]},
                "market_price": {"price": 11.0, "unit": "kg"},
            }

    fake_price_module.get_price_verification_service = lambda: _FakeService()
    sys.modules["app"] = sys.modules.get("app") or types.ModuleType("app")
    sys.modules["app.services"] = sys.modules.get("app.services") or types.ModuleType("app.services")
    sys.modules["app.services.price_verification"] = fake_price_module

    symbols = _load_symbols(
        CROSSDOC_PATH,
        {
            "DEFAULT_LABELS",
            "_coerce_decimal",
            "_coerce_single_numeric_scalar",
            "_build_document_lookup",
            "_resolve_doc_references",
            "run_price_verification_checks",
        },
        extra_namespace={"re": re},
    )
    run_price_verification_checks = symbols["run_price_verification_checks"]

    issues = asyncio.run(
        run_price_verification_checks(
            {
                "invoice": {
                    "goods_description": "100% Cotton Knit T-Shirts, Men's Woven Denim Trousers, Girls Cotton Dresses",
                    "amount": 458750.0,
                    "currency": "USD",
                },
                "documents": [{"document_type": "commercial_invoice", "filename": "Invoice.pdf"}],
            }
        )
    )

    assert issues == []
    assert service_calls["verify_price"] == 0


def test_missing_flag_state_does_not_create_high_risk_vessel_flag_result() -> None:
    module = _load_module(VESSEL_SANCTIONS_PATH, "vessel_sanctions_beta_truth_test")
    service = module.VesselSanctionsService()

    assessment = service.assess_flag_risk(flag_state=None, flag_code=None)

    assert assessment.risk_level == "LOW"
    assert assessment.paris_mou_status == "unknown"
    assert "no flag-risk escalation" in assessment.notes.lower()
