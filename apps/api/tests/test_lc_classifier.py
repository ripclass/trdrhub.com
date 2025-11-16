import sys
from types import ModuleType

import pytest

# Provide a lightweight stub for weasyprint so importing app.services.* doesn't fail in CI
if "weasyprint" not in sys.modules:
    class _WeasyStub:  # pragma: no cover - import shim only
        def __init__(self, *args, **kwargs):
            pass

        def write_pdf(self, *args, **kwargs):
            return b""

    weasy_module = ModuleType("weasyprint")
    weasy_module.HTML = _WeasyStub
    weasy_module.CSS = _WeasyStub
    sys.modules["weasyprint"] = weasy_module

    text_module = ModuleType("weasyprint.text")
    fonts_module = ModuleType("weasyprint.text.fonts")
    fonts_module.FontConfiguration = _WeasyStub
    text_module.fonts = fonts_module
    sys.modules["weasyprint.text"] = text_module
    sys.modules["weasyprint.text.fonts"] = fonts_module

from app.core.lc_types import LCType
from app.services.lc_classifier import detect_lc_type
from app.services.rule_evaluator import RuleEvaluator


def test_detect_lc_type_import():
    lc = {
        "applicant": {"address": {"country": "Bangladesh"}},
        "beneficiary": {"address": {"country": "China"}},
        "issuing_bank": {"address": {"country": "Bangladesh"}},
    }
    shipment = {
        "port_of_discharge": "Chattogram, Bangladesh",
        "port_of_loading": "Qingdao, China",
    }

    guess = detect_lc_type(lc, shipment)

    assert guess["lc_type"] == LCType.IMPORT.value
    assert guess["confidence"] >= 0.8
    assert "import" in guess["reason"].lower()


def test_detect_lc_type_export():
    lc = {
        "applicant": {"address": {"country": "United States"}},
        "beneficiary": {"address": {"country": "Bangladesh"}},
        "issuing_bank": {"address": {"country": "Bangladesh"}},
    }
    shipment = {
        "port_of_loading": "Chattogram, Bangladesh",
        "port_of_discharge": "Los Angeles, United States",
    }

    guess = detect_lc_type(lc, shipment)

    assert guess["lc_type"] == LCType.EXPORT.value
    assert guess["confidence"] >= 0.8
    assert "export" in guess["reason"].lower()


def test_detect_lc_type_unknown_when_conflicting():
    lc = {
        "applicant": {"address": {"country": "Bangladesh"}},
        "beneficiary": {"address": {"country": "Bangladesh"}},
    }
    shipment = {}

    guess = detect_lc_type(lc, shipment)

    assert guess["lc_type"] == LCType.UNKNOWN.value
    assert guess["confidence"] <= 0.2


def test_rule_evaluator_respects_lc_types_metadata():
    evaluator = RuleEvaluator()
    rule = {
        "rule_id": "EXPORT-ONLY",
        "lc_types": ["export"],
        "conditions": [
            {
                "field": "lc.amount.value",
                "operator": "exists",
            }
        ],
    }

    context = {"lc": {"amount": {"value": "100000"}}, "lc_type": "import"}
    skipped = evaluator.evaluate_rule(rule, context)
    assert skipped.get("not_applicable") is True

    context["lc_type"] = "export"
    evaluated = evaluator.evaluate_rule(rule, context)
    assert evaluated.get("not_applicable") is not True