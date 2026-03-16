from __future__ import annotations

import ast
import re
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional


ROOT = Path(__file__).resolve().parents[1]
LC_CLASSIFIER_PATH = ROOT / "app" / "services" / "lc_classifier.py"
VALIDATE_PATH = ROOT / "app" / "routers" / "validate.py"


class LCType(str, Enum):
    IMPORT = "import"
    EXPORT = "export"
    UNKNOWN = "unknown"


def normalize_lc_type(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    candidate = value.strip().lower()
    if candidate in {member.value for member in LCType}:
        return candidate
    return None


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


def _load_extract_workflow_lc_type():
    namespace: Dict[str, Any] = {
        "Dict": Dict,
        "Optional": Optional,
        "normalize_lc_type": normalize_lc_type,
    }
    loaded = _load_symbols(VALIDATE_PATH, {"_extract_workflow_lc_type"}, namespace)
    return loaded["_extract_workflow_lc_type"]


def test_extract_workflow_lc_type_ignores_documentary_form_values() -> None:
    extract_workflow_lc_type = _load_extract_workflow_lc_type()

    assert extract_workflow_lc_type({"lc_type": "documentary"}) is None
    assert extract_workflow_lc_type({"lc_type": "standby"}) is None
    assert extract_workflow_lc_type({"lc_type": "export"}) == "export"
    assert extract_workflow_lc_type({"form_of_doc_credit": "import"}) == "import"


def test_detect_lc_type_uses_exporter_company_country_when_iso_sample_has_loading_flow() -> None:
    detect_lc_type = _load_detect_lc_type()

    guess = detect_lc_type(
        {
            "format": "iso20022",
            "beneficiary": "Beneficiary Co.",
            "applicant": "Applicant Co.",
            "port_of_loading_country_name": "Bangladesh",
            "port_of_discharge_country_name": "United Arab Emirates",
            "ports": {
                "loading": "Chattogram Port",
                "discharge": "Jebel Ali Port",
            },
        },
        None,
        {
            "user_type": "exporter",
            "workflow_type": "export-lc-upload",
            "company_country": "BD",
        },
    )

    assert guess["lc_type"] == "export"
    assert guess["confidence"] >= 0.62


def test_detect_lc_type_uses_importer_company_country_when_iso_sample_has_discharge_flow() -> None:
    detect_lc_type = _load_detect_lc_type()

    guess = detect_lc_type(
        {
            "format": "iso20022",
            "beneficiary": "Seller Co.",
            "applicant": "Buyer Co.",
            "port_of_loading_country_name": "China",
            "port_of_discharge_country_name": "Bangladesh",
            "ports": {
                "loading": "Shanghai Port",
                "discharge": "Chattogram Port",
            },
        },
        None,
        {
            "user_type": "importer",
            "workflow_type": "supplier-document-check",
            "company_country": "BD",
        },
    )

    assert guess["lc_type"] == "import"
    assert guess["confidence"] >= 0.62


def test_detect_lc_type_keeps_ambiguous_iso_unknown_without_request_country_hint() -> None:
    detect_lc_type = _load_detect_lc_type()

    guess = detect_lc_type(
        {
            "format": "iso20022",
            "beneficiary": "Beneficiary Co.",
            "applicant": "Applicant Co.",
            "ports": {
                "loading": "Chattogram Port",
                "discharge": "Jebel Ali Port",
            },
        },
        None,
        {
            "user_type": "exporter",
            "workflow_type": "export-lc-upload",
        },
    )

    assert guess["lc_type"] == "unknown"


def test_detect_lc_type_uses_exporter_lane_as_last_resort_when_ports_exist() -> None:
    detect_lc_type = _load_detect_lc_type()

    guess = detect_lc_type(
        {
            "format": "iso20022",
            "beneficiary": "Beneficiary Co.",
            "applicant": "Applicant Co.",
            "port_of_loading_country_name": "Bangladesh",
            "port_of_discharge_country_name": "United Arab Emirates",
            "ports": {
                "loading": "Chattogram Port",
                "discharge": "Jebel Ali Port",
            },
        },
        None,
        {
            "user_type": "exporter",
            "workflow_type": "export-lc-upload",
        },
    )

    assert guess["lc_type"] == "export"
    assert guess["confidence"] == 0.52


def test_detect_lc_type_uses_importer_lane_as_last_resort_when_ports_exist() -> None:
    detect_lc_type = _load_detect_lc_type()

    guess = detect_lc_type(
        {
            "format": "iso20022",
            "beneficiary": "Seller Co.",
            "applicant": "Buyer Co.",
            "port_of_loading_country_name": "China",
            "port_of_discharge_country_name": "Bangladesh",
            "ports": {
                "loading": "Shanghai Port",
                "discharge": "Chattogram Port",
            },
        },
        None,
        {
            "user_type": "importer",
            "workflow_type": "supplier-document-check",
        },
    )

    assert guess["lc_type"] == "import"
    assert guess["confidence"] == 0.52
