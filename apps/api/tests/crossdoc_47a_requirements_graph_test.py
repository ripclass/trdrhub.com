from __future__ import annotations

import ast
import re
from pathlib import Path
from types import MethodType, SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple


ROOT = Path(__file__).resolve().parents[1]
CROSSDOC_VALIDATOR_PATH = ROOT / "app" / "services" / "validation" / "crossdoc_validator.py"


class _LoggerStub:
    def info(self, *args: Any, **kwargs: Any) -> None:
        return None

    def warning(self, *args: Any, **kwargs: Any) -> None:
        return None


def _load_crossdoc_47a_symbols() -> Dict[str, Any]:
    source = CROSSDOC_VALIDATOR_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)
    selected_nodes: List[ast.AST] = []

    for node in parsed.body:
        if isinstance(node, ast.FunctionDef) and node.name == "_condition_texts_from_graph":
            selected_nodes.append(node)
        if isinstance(node, ast.FunctionDef) and node.name == "_identifier_requirements_from_graph":
            selected_nodes.append(node)
        if isinstance(node, ast.ClassDef) and node.name == "CrossDocValidator":
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name in {
                    "_normalize_identifier_token",
                    "_token_present_in_text",
                    "_check_value_in_document",
                    "_doc_has_parser_failure_for_fields",
                    "_presence_state_for_document",
                    "_format_presence_matrix",
                    "_parse_47a_requirements",
                    "_validate_po_number_all_docs",
                    "_validate_bin_all_docs",
                    "_validate_tin_all_docs",
                }:
                    selected_nodes.append(item)

    module_ast = ast.Module(body=selected_nodes, type_ignores=[])
    ast.fix_missing_locations(module_ast)
    namespace: Dict[str, Any] = {
        "Any": Any,
        "Dict": Dict,
        "List": List,
        "Optional": Optional,
        "Tuple": Tuple,
        "re": re,
        "logger": _LoggerStub(),
        "BIN_REGEX_PATTERNS": [r"EXPORTER\s+BIN[:\s]*([A-Z0-9\\-]+)"],
        "TIN_REGEX_PATTERNS": [r"EXPORTER\s+TIN[:\s]*([A-Z0-9\\-]+)"],
        "canonicalize_fields": lambda value: value if isinstance(value, dict) else {},
        "CrossDocIssue": lambda **kwargs: kwargs,
        "IssueSeverity": SimpleNamespace(CRITICAL="critical"),
        "DocumentType": SimpleNamespace(
            LC="letter_of_credit",
            INVOICE="commercial_invoice",
            BILL_OF_LADING="bill_of_lading",
            INSURANCE="insurance_certificate",
            CERTIFICATE_OF_ORIGIN="certificate_of_origin",
            PACKING_LIST="packing_list",
            INSPECTION_CERT="inspection_certificate",
            BENEFICIARY_CERT="beneficiary_certificate",
        ),
    }
    exec(compile(module_ast, str(CROSSDOC_VALIDATOR_PATH), "exec"), namespace)
    return namespace


def _build_validator_shim(ns: Dict[str, Any]) -> Any:
    class _Shim:
        pass

    shim = _Shim()
    for name in (
        "_normalize_identifier_token",
        "_token_present_in_text",
        "_check_value_in_document",
        "_doc_has_parser_failure_for_fields",
        "_presence_state_for_document",
        "_format_presence_matrix",
        "_validate_po_number_all_docs",
        "_validate_bin_all_docs",
        "_validate_tin_all_docs",
    ):
        setattr(shim, name, MethodType(ns[name], shim))
    return shim


def test_parse_47a_requirements_prefers_requirements_graph_conditions() -> None:
    ns = _load_crossdoc_47a_symbols()
    parse_requirements = ns["_parse_47a_requirements"]

    requirements = parse_requirements(
        object(),
        {
            "additional_conditions": ["UNRELATED CONDITION TEXT"],
            "requirements_graph_v1": {
                "documentary_conditions": [
                    "BUYER PURCHASE ORDER NO. GBE-44592 MUST APPEAR ON ALL DOCUMENTS",
                ],
            },
        },
    )

    assert requirements["po_number"] == "GBE-44592"
    assert requirements["all_docs_require_po"] is True
    assert requirements["raw_conditions"] == [
        "BUYER PURCHASE ORDER NO. GBE-44592 MUST APPEAR ON ALL DOCUMENTS",
    ]


def test_parse_47a_requirements_prefers_structured_condition_requirements() -> None:
    ns = _load_crossdoc_47a_symbols()
    parse_requirements = ns["_parse_47a_requirements"]

    requirements = parse_requirements(
        object(),
        {
            "additional_conditions": [
                "BUYER PURCHASE ORDER NO. WRONG-0001 MUST APPEAR ON ALL DOCUMENTS",
            ],
            "requirements_graph_v1": {
                "condition_requirements": [
                    {
                        "requirement_type": "identifier_presence",
                        "identifier_type": "po_number",
                        "value": "GBE-44592",
                        "applies_to": "all_documents",
                        "source_text": "BUYER PURCHASE ORDER NO. GBE-44592 MUST APPEAR ON ALL DOCUMENTS",
                    }
                ],
            },
        },
    )

    assert requirements["po_number"] == "GBE-44592"
    assert requirements["all_docs_require_po"] is True
    assert requirements["raw_conditions"] == [
        "BUYER PURCHASE ORDER NO. GBE-44592 MUST APPEAR ON ALL DOCUMENTS",
    ]


def test_parse_47a_requirements_falls_back_to_ambiguous_graph_conditions() -> None:
    ns = _load_crossdoc_47a_symbols()
    parse_requirements = ns["_parse_47a_requirements"]

    requirements = parse_requirements(
        object(),
        {
            "requirements_graph_v1": {
                "documentary_conditions": [],
                "ambiguous_conditions": [
                    "EXPORTER BIN: 000334455-0103 MUST APPEAR ON ALL DOCUMENTS",
                    "EXPORTER TIN: 545342112233 MUST APPEAR ON ALL DOCUMENTS",
                ],
            },
        },
    )

    assert requirements["bin_number"] == "000334455-0103"
    assert requirements["all_docs_require_bin"] is True
    assert requirements["tin_number"] == "545342112233"
    assert requirements["all_docs_require_tin"] is True


def test_identifier_presence_issues_are_requirement_backed_documentary_findings() -> None:
    ns = _load_crossdoc_47a_symbols()
    validator = _build_validator_shim(ns)

    docs = {
        "invoice": {"raw_text": "COMMERCIAL INVOICE\nInvoice Number: INV-2026-015"},
        "bill_of_lading": {"raw_text": "BILL OF LADING\nShipped on board"},
    }

    po_issues, _, _ = validator._validate_po_number_all_docs("GBE-44592", docs, {})
    bin_issues, _, _ = validator._validate_bin_all_docs("000334455-0103", docs, {})
    tin_issues, _, _ = validator._validate_tin_all_docs("545342112233", docs, {})

    for issue, expected_text in (
        (po_issues[0], "GBE-44592"),
        (bin_issues[0], "000334455-0103"),
        (tin_issues[0], "545342112233"),
    ):
        assert issue["requirement_source"] == "requirements_graph_v1"
        assert issue["requirement_kind"] == "identifier_presence"
        assert issue["requirement_text"] == expected_text
