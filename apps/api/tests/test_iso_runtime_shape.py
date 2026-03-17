from __future__ import annotations

import ast
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.reference_data import get_country_registry, get_currency_registry, get_port_registry


LC_CLASSIFIER_PATH = ROOT / "app" / "services" / "lc_classifier.py"
LAUNCH_PIPELINE_PATH = ROOT / "app" / "services" / "extraction" / "launch_pipeline.py"


class LCType:
    class _Value:
        def __init__(self, value: str) -> None:
            self.value = value

    IMPORT = _Value("import")
    EXPORT = _Value("export")
    UNKNOWN = _Value("unknown")


def _load_symbols(path: Path, names: set[str], namespace: Dict[str, Any]) -> Dict[str, Any]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    selected: list[ast.stmt] = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets = {
                target.id
                for target in node.targets
                if isinstance(target, ast.Name)
            }
            if targets & names:
                selected.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in names:
            selected.append(node)
    module = ast.Module(body=selected, type_ignores=[])
    exec(compile(module, filename=str(path), mode="exec"), namespace)
    return namespace


def _load_shape_lc_financial_payload():
    namespace: Dict[str, Any] = {
        "re": re,
        "Any": Any,
        "Dict": Dict,
        "List": List,
        "Optional": Optional,
        "get_port_registry": get_port_registry,
        "get_country_registry": get_country_registry,
        "get_currency_registry": get_currency_registry,
    }
    symbols = {
        "CANONICAL_DOCUMENT_ALIASES",
        "MEASUREMENT_LABEL_ALIASES",
        "_normalize_lookup_key",
        "_normalize_country_value",
        "_normalize_port_value",
        "_normalize_currency_value",
        "_normalize_measurement_label",
        "_normalize_document_alias",
        "_apply_canonical_normalization",
        "_extract_label_value",
        "_extract_amount_value",
        "_shape_lc_financial_payload",
    }
    loaded = _load_symbols(LAUNCH_PIPELINE_PATH, symbols, namespace)
    return loaded["_shape_lc_financial_payload"]


def _load_detect_lc_type():
    namespace: Dict[str, Any] = {
        "re": re,
        "Any": Any,
        "Dict": Dict,
        "Optional": Optional,
        "LCType": LCType,
        "LCTypeGuess": Dict[str, Any],
        "detect_lc_family": lambda lc_data: {
            "family": "iso" if (lc_data or {}).get("format") == "iso20022" else "mt",
            "confidence": 0.8,
            "evidence": ["declared-format"],
        },
    }
    symbols = {
        "COUNTRY_SYNONYMS",
        "detect_lc_type",
        "_extract_party_country",
        "_extract_port_country",
        "_normalize_country",
    }
    loaded = _load_symbols(LC_CLASSIFIER_PATH, symbols, namespace)
    return loaded["detect_lc_type"]


def test_live_exporter_sample_shape_populates_port_countries_and_orientation() -> None:
    shape_lc_financial_payload = _load_shape_lc_financial_payload()
    detect_lc_type = _load_detect_lc_type()

    raw_text = "\n".join(
        [
            "LC",
            ":20: DOCUMENTARY CREDIT NUMBER 100924060096",
            ":31C: DATE OF ISSUE 2026-03-08",
            ":31D: EXPIRY 2026-06-28 DHAKA",
            ":50: APPLICANT Applicant Co.",
            ":59: BENEFICIARY Beneficiary Co.",
            ":32B: USD 100000.00",
            ":44E: PORT OF LOADING Chattogram Port",
            ":44F: PORT OF DISCHARGE Jebel Ali Port",
            ":45A: GOODS General merchandise as per proforma invoice",
            ":46A: DOCS REQUIRED: INVOICE/BL/PL/COO/INSURANCE",
            ":47A: ADDITIONAL CONDITIONS APPLY",
        ]
    )

    lc_context = shape_lc_financial_payload(
        {
            "number": "100924060096",
            "currency": "USD",
            "applicant": "Applicant Co.",
            "beneficiary": "Beneficiary Co.",
            "ports": {
                "loading": "Chattogram Port",
                "discharge": "Jebel Ali Port",
            },
        },
        lc_subtype="letter_of_credit",
        raw_text=raw_text,
        source_type="letter_of_credit",
        lc_format="mt700",
    )

    assert lc_context["port_of_loading_country_name"] == "Bangladesh"
    assert lc_context["port_of_discharge_country_name"] == "United Arab Emirates"

    guess = detect_lc_type(
        lc_context,
        None,
        {
            "user_type": "exporter",
            "workflow_type": "export-lc-intake",
        },
    )

    assert guess["lc_type"] == "export"
    assert guess["confidence"] >= 0.52
