from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
from typing import Any, Dict, List
import json
import sys


ROOT = Path(__file__).resolve().parents[1]
VALIDATE_PATH = ROOT / "apps" / "api" / "app" / "routers" / "validate.py"
RESULTS_MAPPER_PATH = ROOT / "apps" / "web" / "src" / "lib" / "exporter" / "resultsMapper.ts"
USE_LCOPILOT_PATH = ROOT / "apps" / "web" / "src" / "hooks" / "use-lcopilot.ts"
CONTRACT_VALIDATOR_PATH = (
    ROOT / "apps" / "api" / "app" / "services" / "validation" / "response_contract_validator.py"
)


def _load_module_from_path(module_name: str, module_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec and spec.loader, f"Unable to load module from {module_path}"
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _load_validate_function(function_name: str):
    source = VALIDATE_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)

    selected = [
        node
        for node in parsed.body
        if isinstance(node, ast.FunctionDef) and node.name == function_name
    ]
    assert selected, f"Missing function {function_name}"

    module_ast = ast.Module(body=selected, type_ignores=[])
    ast.fix_missing_locations(module_ast)

    namespace = {
        "Any": Any,
        "Dict": Dict,
        "List": List,
        "json": json,
    }
    exec(compile(module_ast, str(VALIDATE_PATH), "exec"), namespace)
    return namespace[function_name]


def test_contract_validator_reads_lc_structured_without_false_required_field_errors():
    validator = _load_module_from_path(
        "contract_validator_patchset2",
        CONTRACT_VALIDATOR_PATH,
    )

    result = validator.validate_response_contract(
        {
            "lc_structured": {
                "number": "LC-001",
                "amount": {"value": "1000", "currency": "USD"},
                "currency": "USD",
                "applicant": {"name": "Applicant Co"},
                "beneficiary": {"name": "Beneficiary Co"},
                "goods_description": "Cotton shirts",
                "additional_conditions": "47A clauses",
            },
            "processing_summary": {"documents": 1},
            "analytics": {"compliance_score": 85},
            "issues": [],
        }
    )

    error_fields = {
        warning.field for warning in result.warnings if warning.severity.value == "error"
    }
    assert result.error_count == 0
    assert {"number", "amount", "currency"}.isdisjoint(error_fields)


def test_issue_dedup_key_preserves_same_rule_on_different_documents():
    build_dedup_key = _load_validate_function("_build_issue_dedup_key")

    exact_a = {
        "rule": "DOC-MISSING-1",
        "documents": ["Invoice.pdf"],
        "document_ids": ["doc-invoice"],
        "expected": "Present",
        "found": "Missing",
    }
    exact_b = dict(exact_a)
    other_doc = {
        "rule": "DOC-MISSING-1",
        "documents": ["Packing.pdf"],
        "document_ids": ["doc-packing"],
        "expected": "Present",
        "found": "Missing",
    }

    assert build_dedup_key(exact_a) == build_dedup_key(exact_b)
    assert build_dedup_key(exact_a) != build_dedup_key(other_doc)


def test_frontend_regressions_remove_docs_debug_log_and_allow_parsing_error_type():
    results_mapper_source = RESULTS_MAPPER_PATH.read_text(encoding="utf-8")
    use_lcopilot_source = USE_LCOPILOT_PATH.read_text(encoding="utf-8")
    validate_source = VALIDATE_PATH.read_text(encoding="utf-8")

    assert "DOCS_MAPPER_DEBUG" not in results_mapper_source
    assert "'quota' | 'parsing'" in use_lcopilot_source
    assert "_build_issue_dedup_key(issue)" in validate_source
