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


def _load_crossdoc_exact_wording_symbols() -> Dict[str, Any]:
    source = CROSSDOC_VALIDATOR_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)
    selected_nodes: List[ast.AST] = []

    for node in parsed.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "_EXACT_WORDING_DOC_TYPE_MAP":
                    selected_nodes.append(node)
                    break
        if isinstance(node, ast.FunctionDef) and node.name == "_exact_wording_requirements_from_graph":
            selected_nodes.append(node)
        if isinstance(node, ast.ClassDef) and node.name == "CrossDocValidator":
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name in {
                    "_normalize_identifier_token",
                    "_token_present_in_text",
                    "_check_value_in_document",
                    "_doc_has_parser_failure_for_fields",
                    "_presence_state_for_document",
                    "_validate_exact_wording_requirements",
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
        "_validate_exact_wording_requirements",
    ):
        setattr(shim, name, MethodType(ns[name], shim))
    return shim


def test_exact_wording_requirements_from_graph_collects_required_documents_and_condition_requirements() -> None:
    ns = _load_crossdoc_exact_wording_symbols()
    extract_requirements = ns["_exact_wording_requirements_from_graph"]

    requirements = extract_requirements(
        {
            "required_documents": [
                {
                    "code": "commercial_invoice",
                    "exact_wording": "SIGNED COMMERCIAL INVOICE",
                }
            ],
            "condition_requirements": [
                {
                    "requirement_type": "document_exact_wording",
                    "document_type": "insurance_policy",
                    "exact_wording": "INSURANCE POLICY BLANK ENDORSED",
                }
            ],
        }
    )

    assert requirements == {
        "invoice": ["SIGNED COMMERCIAL INVOICE"],
        "insurance": ["INSURANCE POLICY BLANK ENDORSED"],
    }


def test_validate_exact_wording_requirements_flags_missing_invoice_wording() -> None:
    ns = _load_crossdoc_exact_wording_symbols()
    validator = _build_validator_shim(ns)

    issues, executed, passed = validator._validate_exact_wording_requirements(
        {"invoice": ["WE HEREBY CERTIFY THAT THIS INVOICE IS TRUE AND CORRECT"]},
        {"invoice": {"raw_text": "COMMERCIAL INVOICE\nInvoice Number: INV-2026-001"}},
    )

    assert executed == 1
    assert passed == 0
    assert len(issues) == 1
    assert issues[0]["rule_id"] == "CROSSDOC-EXACT-WORDING"
    assert issues[0]["title"] == "LC-required wording missing from Commercial Invoice"
    assert "WE HEREBY CERTIFY THAT THIS INVOICE IS TRUE AND CORRECT" in issues[0]["expected"]


def test_validate_all_wires_exact_wording_requirements_from_graph() -> None:
    source = CROSSDOC_VALIDATOR_PATH.read_text(encoding="utf-8")

    assert "exact_wording_requirements = _exact_wording_requirements_from_graph(requirements_graph)" in source
    assert "self._validate_exact_wording_requirements(" in source
