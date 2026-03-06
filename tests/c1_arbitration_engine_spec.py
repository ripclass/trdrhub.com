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
])


def test_decision_object_shape_present():
    selected, diag, decision = FUNCS["_arbitrate_field"](
        field="lc_number",
        candidates=[{"value": "LC-123", "method": "regex"}],
        raw_text="LC-123 appears in body",
        validator=lambda x: True,
        normalizer=lambda x: str(x),
        fallback_method="regex",
    )

    assert selected == "LC-123"
    assert isinstance(diag, dict)
    assert set(decision.keys()) == {
        "field",
        "value",
        "status",
        "reason_code",
        "evidence_present",
        "method",
    }


def test_rule_order_conflict_first():
    selected, _diag, decision = FUNCS["_arbitrate_field"](
        field="lc_number",
        candidates=[
            {"value": "LC-111", "method": "kv"},
            {"value": "LC-222", "method": "regex"},
        ],
        raw_text="LC-111 LC-222",
        validator=lambda x: True,
        normalizer=lambda x: x,
        fallback_method="regex",
    )
    assert selected is None
    assert decision["status"] == "rejected"
    assert decision["reason_code"] == "conflict_detected"


def test_rule_order_missing_second():
    selected, _diag, decision = FUNCS["_arbitrate_field"](
        field="currency",
        candidates=[],
        raw_text="",
        validator=None,
        normalizer=lambda x: x,
        fallback_method="regex",
    )
    assert selected is None
    assert decision["status"] == "rejected"
    assert decision["reason_code"] == "missing_in_source"


def test_rule_order_retry_third_when_invalid():
    selected, _diag, decision = FUNCS["_arbitrate_field"](
        field="amount",
        candidates=[{"value": "ABC", "method": "kv"}],
        raw_text="amount token present",
        validator=None,
        normalizer=lambda _x: None,
        fallback_method="regex",
    )
    assert selected is None
    assert decision["status"] == "retry"
    assert decision["reason_code"] == "extraction_failed"


def test_rule_order_accept_fourth_when_valid_with_evidence():
    selected, _diag, decision = FUNCS["_arbitrate_field"](
        field="applicant",
        candidates=[{"value": "ABC TRADING LTD", "method": "kv"}],
        raw_text="Applicant: ABC TRADING LTD",
        validator=lambda x: bool(x),
        normalizer=lambda x: str(x).upper(),
        fallback_method="regex",
    )
    assert selected == "ABC TRADING LTD"
    assert decision["status"] == "accepted"
    assert decision["evidence_present"] is True
