from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


ROOT = Path(__file__).resolve().parents[1]
VALIDATION_EXECUTION_PATH = ROOT / "app" / "routers" / "validation" / "validation_execution.py"
ISSUES_PIPELINE_PATH = ROOT / "app" / "routers" / "validation" / "issues_pipeline.py"
PRESENTATION_CONTRACT_PATH = ROOT / "app" / "routers" / "validation" / "presentation_contract.py"


class _DummyLogger:
    def warning(self, *args, **kwargs) -> None:
        return None


def _load_validation_execution_symbols(target_names: set[str]) -> Dict[str, Any]:
    source = VALIDATION_EXECUTION_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)
    selected = [
        node
        for node in parsed.body
        if isinstance(node, ast.FunctionDef) and node.name in target_names
    ]
    module_ast = ast.Module(body=selected, type_ignores=[])
    ast.fix_missing_locations(module_ast)
    namespace: Dict[str, Any] = {
        "Any": Any,
        "Dict": Dict,
    }
    exec(compile(module_ast, str(VALIDATION_EXECUTION_PATH), "exec"), namespace)
    return namespace


def _load_issue_symbols(target_names: set[str]) -> Dict[str, Any]:
    source = ISSUES_PIPELINE_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)
    selected = [
        node
        for node in parsed.body
        if isinstance(node, ast.FunctionDef) and node.name in target_names
    ]
    module_ast = ast.Module(body=selected, type_ignores=[])
    ast.fix_missing_locations(module_ast)
    namespace: Dict[str, Any] = {
        "Any": Any,
        "Dict": Dict,
        "List": List,
        "Optional": Optional,
        "Set": Set,
    }
    exec(compile(module_ast, str(ISSUES_PIPELINE_PATH), "exec"), namespace)
    return namespace


def _load_contract_symbols(issue_symbols: Dict[str, Any], target_names: set[str]) -> Dict[str, Any]:
    source = PRESENTATION_CONTRACT_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)
    selected = [
        node
        for node in parsed.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in target_names
    ]
    module_ast = ast.Module(body=selected, type_ignores=[])
    ast.fix_missing_locations(module_ast)
    namespace: Dict[str, Any] = {
        "Any": Any,
        "Dict": Dict,
        "List": List,
        "Optional": Optional,
        "Tuple": Tuple,
        "json": json,
        "logger": _DummyLogger(),
        "_build_document_field_hint_index": issue_symbols["_build_document_field_hint_index"],
        "_build_unresolved_critical_context": issue_symbols["_build_unresolved_critical_context"],
    }
    exec(compile(module_ast, str(PRESENTATION_CONTRACT_PATH), "exec"), namespace)
    return namespace


def test_build_ai_validation_layers_projects_current_runtime_checks_into_l1_l2_l3() -> None:
    symbols = _load_validation_execution_symbols(
        {"_derive_ai_layer_verdict", "_build_ai_validation_layers"}
    )
    build_ai_validation_layers = symbols["_build_ai_validation_layers"]

    layers = build_ai_validation_layers(
        {
            "checks_performed": [
                "lc_requirement_parsing",
                "document_completeness",
                "bl_field_validation",
            ],
            "required_critical_docs": ["inspection_certificate"],
            "missing_critical_docs": 1,
            "bl_must_show": ["voyage_number"],
            "bl_missing_fields": 2,
            "packing_list_issues": 0,
        }
    )

    assert layers["l1"]["executed"] is True
    assert layers["l1"]["verdict"] == "reject"
    assert layers["l1"]["critical_issues"] == 1
    assert layers["l1"]["checks_performed"] == [
        "lc_requirement_parsing",
        "document_completeness",
    ]

    assert layers["l2"]["executed"] is True
    assert layers["l2"]["verdict"] == "warn"
    assert layers["l2"]["major_issues"] == 2
    assert layers["l2"]["evidence"]["bl_must_show"] == ["voyage_number"]

    assert layers["l3"]["executed"] is False
    assert layers["l3"]["verdict"] == "not_run"
    assert layers["l3"]["reason"] == "advanced_anomaly_reasoning_not_wired"


def test_validation_contract_uses_projected_ai_layers_as_first_class_contract_evidence() -> None:
    issue_symbols = _load_issue_symbols(
        {
            "_build_document_field_hint_index",
            "_build_unresolved_critical_context",
        }
    )
    contract_symbols = _load_contract_symbols(
        issue_symbols,
        {
            "_classify_reason_semantics",
            "_build_issue_lane_summary",
            "_extract_requirement_readiness_items",
            "_extract_rule_evidence_items",
            "_classify_rules_signal_classes",
            "_build_validation_contract",
        },
    )
    build_validation_contract = contract_symbols["_build_validation_contract"]

    contract = build_validation_contract(
        {
            "critical_issues": 0,
            "major_issues": 0,
            "minor_issues": 0,
            "execution_position": "post_deterministic_runtime",
            "layer_contract_version": "ai_layers_v1",
            "layers": {
                "l1": {
                    "layer": "L1",
                    "label": "Document Completeness",
                    "executed": True,
                    "verdict": "reject",
                    "issue_count": 1,
                    "critical_issues": 1,
                    "major_issues": 0,
                    "minor_issues": 0,
                    "checks_performed": ["document_completeness"],
                    "evidence": {"missing_critical_docs": 1},
                },
                "l2": {
                    "layer": "L2",
                    "label": "Requirement-To-Document Checks",
                    "executed": False,
                    "verdict": "not_run",
                    "issue_count": 0,
                    "critical_issues": 0,
                    "major_issues": 0,
                    "minor_issues": 0,
                    "checks_performed": [],
                    "reason": "not_triggered",
                    "evidence": {},
                },
                "l3": {
                    "layer": "L3",
                    "label": "Advanced Anomaly Review",
                    "executed": False,
                    "verdict": "not_run",
                    "issue_count": 0,
                    "critical_issues": 0,
                    "major_issues": 0,
                    "minor_issues": 0,
                    "checks_performed": [],
                    "reason": "advanced_anomaly_reasoning_not_wired",
                    "evidence": {},
                },
            },
        },
        {"verdict": "SUBMIT", "reasons": [], "risk_flags": []},
        {"missing_critical": []},
        {"can_submit": True, "reasons": [], "missing_reason_codes": [], "unresolved_critical_fields": []},
        issues=[],
    )

    assert contract["ai_verdict"] == "reject"
    assert contract["ai_layer_contract_version"] == "ai_layers_v1"
    assert contract["ai_execution_position"] == "post_deterministic_runtime"
    assert contract["ai_layers"]["l1"]["verdict"] == "reject"
    assert contract["evidence_summary"]["ai_layer_verdicts"]["l1"] == "reject"
    assert contract["evidence_summary"]["ai_layers_executed"] == ["l1"]
