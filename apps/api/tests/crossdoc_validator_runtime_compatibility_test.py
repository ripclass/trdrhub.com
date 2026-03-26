from __future__ import annotations

import ast
from pathlib import Path
from types import MethodType, SimpleNamespace
from typing import Any, Dict


ROOT = Path(__file__).resolve().parents[1]
CROSSDOC_VALIDATOR_PATH = ROOT / "app" / "services" / "validation" / "crossdoc_validator.py"


def _load_crossdoc_runtime_symbols() -> Dict[str, Any]:
    source = CROSSDOC_VALIDATOR_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)
    selected_nodes: list[ast.AST] = []

    for node in parsed.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "_NUMERIC_EPSILON":
                    selected_nodes.append(node)
                    break
        if isinstance(node, ast.ClassDef) and node.name == "CrossDocValidator":
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name in {
                    "_check_insurance_amount",
                    "_resolve_insurance_coverage_ratio",
                }:
                    selected_nodes.append(item)

    module_ast = ast.Module(body=selected_nodes, type_ignores=[])
    ast.fix_missing_locations(module_ast)

    namespace: Dict[str, Any] = {
        "Any": Any,
        "Optional": Any,
        "Dict": Dict,
        "List": list,
        "CrossDocIssue": lambda **kwargs: kwargs,
        "IssueSeverity": SimpleNamespace(CRITICAL="critical", MAJOR="major"),
        "DocumentType": SimpleNamespace(INSURANCE="insurance_certificate", LC="letter_of_credit"),
        "_INSURANCE_REQUIREMENT_TYPES": {"insurance_certificate", "insurance_policy"},
        "re": __import__("re"),
    }
    exec(compile(module_ast, str(CROSSDOC_VALIDATOR_PATH), "exec"), namespace)
    return namespace


def test_crossdoc_validator_runtime_uses_supported_threshold_aliases() -> None:
    source = CROSSDOC_VALIDATOR_PATH.read_text(encoding="utf-8")

    assert "from app.constants.thresholds import VALIDATION, CONFIDENCE, SIMILARITY" in source
    assert "_NUMERIC_EPSILON = 1e-6" in source
    assert "SIMILARITY.GOODS" in source
    assert "SIMILARITY.JACCARD" in source
    assert "VALIDATION.NUMERIC_EPSILON" not in source
    assert "VALIDATION.GOODS_DESCRIPTION_MIN_SIMILARITY" not in source
    assert "VALIDATION.JACCARD_SIMILARITY_THRESHOLD" not in source


def test_check_insurance_amount_returns_issue_without_missing_constant_crash() -> None:
    ns = _load_crossdoc_runtime_symbols()
    check_insurance_amount = ns["_check_insurance_amount"]
    resolve_ratio = ns["_resolve_insurance_coverage_ratio"]

    class _Shim:
        @staticmethod
        def _parse_amount(value: Any) -> float | None:
            if value is None:
                return None
            return float(value)

    _Shim._resolve_insurance_coverage_ratio = resolve_ratio

    issue = check_insurance_amount(
        _Shim(),
        {"insured_amount": "100"},
        {"amount": "100"},
    )

    assert issue is not None
    assert issue["rule_id"] == "CROSSDOC-INSURANCE-1"
    assert issue["title"] == "Insurance Coverage Below LC Requirement"


def test_check_insurance_amount_reads_lc_required_percentage_from_requirements_graph() -> None:
    ns = _load_crossdoc_runtime_symbols()
    check_insurance_amount = ns["_check_insurance_amount"]
    resolve_ratio = ns["_resolve_insurance_coverage_ratio"]

    class _Shim:
        @staticmethod
        def _parse_amount(value: Any) -> float | None:
            if value is None:
                return None
            return float(value)

    _Shim._resolve_insurance_coverage_ratio = resolve_ratio

    issue = check_insurance_amount(
        _Shim(),
        {"insured_amount": "150000"},
        {
            "amount": "150000",
            "requirements_graph_v1": {
                "required_documents": [
                    {
                        "code": "insurance_certificate",
                        "raw_text": "Insurance Certificate for 110% of invoice value",
                    }
                ]
            },
        },
    )

    assert issue is not None
    assert issue["expected"] == ">= 165,000.00 (110% of LC amount)"
