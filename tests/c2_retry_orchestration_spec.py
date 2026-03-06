from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


ROOT = Path(__file__).resolve().parents[1]
LC_EXTRACTOR_PATH = ROOT / "apps" / "api" / "app" / "services" / "extraction" / "lc_extractor.py"


def _load_functions(function_names: List[str]) -> Dict[str, Any]:
    source = LC_EXTRACTOR_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)

    selected = []
    for node in parsed.body:
        if isinstance(node, ast.FunctionDef) and node.name in function_names:
            selected.append(node)

    namespace: Dict[str, Any] = {
        "Any": Any,
        "Dict": Dict,
        "List": List,
        "Optional": Optional,
        "Tuple": Tuple,
    }
    module_ast = ast.Module(body=selected, type_ignores=[])
    ast.fix_missing_locations(module_ast)
    exec(compile(module_ast, str(LC_EXTRACTOR_PATH), "exec"), namespace)
    return {name: namespace[name] for name in function_names}


FUNCS = _load_functions([
    "_diagnose_candidates",
    "_candidate_value",
    "_candidate_method",
    "_has_evidence_in_text",
    "_arbitrate_field",
    "_is_unresolved_critical",
    "_upgrade_reason",
    "_filter_candidates_by_methods",
    "_retry_unresolved_critical_fields",
])


def _base_specs() -> Dict[str, Dict[str, Any]]:
    return {
        "lc_number": {
            "critical": True,
            "validator": lambda x: isinstance(x, str) and x.startswith("LC-"),
            "normalizer": lambda x: str(x).upper(),
            "fallback_method": "regex",
        }
    }


def test_retry_recovers_via_table_kv_reparse():
    decisions, diagnostics, recovered = FUNCS["_retry_unresolved_critical_fields"](
        field_decisions={"lc_number": {"field": "lc_number", "status": "retry", "reason_code": "extraction_failed"}},
        field_diagnostics={},
        field_candidates={
            "lc_number": [
                {"value": "LC-777", "method": "table"},
                {"value": "LC-999", "method": "regex"},
            ]
        },
        field_specs=_base_specs(),
        raw_text="TABLE VALUE LC-777",
        llm_field_repair=None,
    )

    assert recovered["lc_number"] == "LC-777"
    assert decisions["lc_number"]["status"] == "accepted"
    assert decisions["lc_number"]["retry_trace"] == {
        "attempted_passes": ["table_kv_reparse"],
        "final_pass_used": "table_kv_reparse",
        "recovered": True,
    }
    assert diagnostics["lc_number"]["decision"]["method"] == "table"


def test_retry_recovers_via_regex_fallback():
    decisions, _diagnostics, recovered = FUNCS["_retry_unresolved_critical_fields"](
        field_decisions={"lc_number": {"field": "lc_number", "status": "retry", "reason_code": "extraction_failed"}},
        field_diagnostics={},
        field_candidates={
            "lc_number": [
                {"value": "BAD", "method": "kv"},
                {"value": "LC-456", "method": "regex"},
            ]
        },
        field_specs=_base_specs(),
        raw_text="Regex found LC-456",
        llm_field_repair=None,
    )

    assert recovered["lc_number"] == "LC-456"
    assert decisions["lc_number"]["status"] == "accepted"
    assert decisions["lc_number"]["retry_trace"]["attempted_passes"] == [
        "table_kv_reparse",
        "regex_fallback",
    ]
    assert decisions["lc_number"]["retry_trace"]["final_pass_used"] == "regex_fallback"


def test_retry_recovers_via_constrained_llm_field_repair():
    llm_calls: List[str] = []

    def llm_field_repair(*, field: str, raw_text: str):
        llm_calls.append(f"{field}:{raw_text}")
        return "LC-888"

    decisions, _diagnostics, recovered = FUNCS["_retry_unresolved_critical_fields"](
        field_decisions={"lc_number": {"field": "lc_number", "status": "rejected", "reason_code": "missing_in_source"}},
        field_diagnostics={},
        field_candidates={"lc_number": []},
        field_specs=_base_specs(),
        raw_text="No obvious LC number in first passes but contains LC-888 context",
        llm_field_repair=llm_field_repair,
    )

    assert len(llm_calls) == 1
    assert recovered["lc_number"] == "LC-888"
    assert decisions["lc_number"]["status"] == "accepted"
    assert decisions["lc_number"]["retry_trace"] == {
        "attempted_passes": ["table_kv_reparse", "regex_fallback", "llm_field_repair"],
        "final_pass_used": "llm_field_repair",
        "recovered": True,
    }


def test_unresolved_after_all_passes_keeps_non_accepted_with_deterministic_reason_upgrade():
    def llm_field_repair(*, field: str, raw_text: str):
        return "BAD"

    decisions, diagnostics, recovered = FUNCS["_retry_unresolved_critical_fields"](
        field_decisions={"lc_number": {"field": "lc_number", "status": "retry", "reason_code": "missing_in_source"}},
        field_diagnostics={},
        field_candidates={
            "lc_number": [
                {"value": "LC-1", "method": "kv"},
                {"value": "LC-2", "method": "kv"},
                {"value": "BAD", "method": "regex"},
            ]
        },
        field_specs=_base_specs(),
        raw_text="LC-1 LC-2 BAD",
        llm_field_repair=llm_field_repair,
    )

    assert recovered == {}
    assert decisions["lc_number"]["status"] in {"retry", "rejected"}
    assert decisions["lc_number"]["reason_code"] == "conflict_detected"
    assert decisions["lc_number"]["retry_trace"]["recovered"] is False
    assert diagnostics["lc_number"]["decision"]["reason_code"] == "conflict_detected"


def test_bounded_attempts_and_no_full_document_loop_behavior():
    llm_calls: List[str] = []

    def llm_field_repair(*, field: str, raw_text: str):
        llm_calls.append(field)
        return None

    decisions, _diagnostics, recovered = FUNCS["_retry_unresolved_critical_fields"](
        field_decisions={"lc_number": {"field": "lc_number", "status": "retry", "reason_code": "extraction_failed"}},
        field_diagnostics={},
        field_candidates={"lc_number": []},
        field_specs=_base_specs(),
        raw_text="No extractable value",
        llm_field_repair=llm_field_repair,
    )

    assert recovered == {}
    assert len(llm_calls) == 1
    assert decisions["lc_number"]["retry_trace"]["attempted_passes"] == [
        "table_kv_reparse",
        "regex_fallback",
        "llm_field_repair",
    ]
    assert decisions["lc_number"]["retry_trace"]["final_pass_used"] is None
    assert decisions["lc_number"]["retry_trace"]["recovered"] is False
