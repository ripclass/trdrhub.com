from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


ROOT = Path(__file__).resolve().parents[1]
VALIDATE_PATH = ROOT / "apps" / "api" / "app" / "routers" / "validate.py"
RESPONSE_SHAPING_PATH = ROOT / "apps" / "api" / "app" / "routers" / "validation" / "response_shaping.py"


def _load_functions(path: Path, function_names: List[str], extra_globals: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    source = path.read_text(encoding="utf-8")
    parsed = ast.parse(source)

    selected: List[ast.FunctionDef] = []
    found = set()
    for node in parsed.body:
        if isinstance(node, ast.FunctionDef) and node.name in function_names:
            selected.append(node)
            found.add(node.name)

    missing = sorted(set(function_names) - found)
    assert not missing, f"Missing function(s) in {path.name}: {missing}"

    module_ast = ast.Module(body=selected, type_ignores=[])
    ast.fix_missing_locations(module_ast)

    namespace: Dict[str, Any] = {
        "Any": Any,
        "Dict": Dict,
        "List": List,
        "Optional": Optional,
        "Tuple": Tuple,
    }
    if extra_globals:
        namespace.update(extra_globals)

    exec(compile(module_ast, str(path), "exec"), namespace)
    return {name: namespace[name] for name in function_names}


def test_issue_payload_carries_decision_status_and_reason_code():
    funcs = _load_functions(VALIDATE_PATH, ["_augment_issues_with_field_decisions"])
    augment = funcs["_augment_issues_with_field_decisions"]

    issues = [{"id": "I-1", "field_name": "amount", "severity": "critical"}]
    decisions = {"amount": {"status": "retry", "reason_code": "extraction_failed"}}

    augment(issues, decisions)

    assert issues[0]["decision_status"] == "retry"
    assert issues[0]["reason_code"] == "extraction_failed"

    provenance_fn = _load_functions(RESPONSE_SHAPING_PATH, ["build_issue_provenance_v1"])[
        "build_issue_provenance_v1"
    ]
    provenance = provenance_fn(issues)
    assert provenance["issues"][0]["decision_status"] == "retry"
    assert provenance["issues"][0]["reason_code"] == "extraction_failed"


def test_docs_field_details_expose_decision_reason_and_retry_trace():
    funcs = _load_functions(VALIDATE_PATH, ["_augment_doc_field_details_with_decisions"])
    augment = funcs["_augment_doc_field_details_with_decisions"]

    docs = [
        {
            "filename": "lc.pdf",
            "field_details": {"amount": {"confidence": 0.51}},
            "extracted_fields": {
                "_field_decisions": {
                    "amount": {
                        "status": "retry",
                        "reason_code": "extraction_failed",
                        "retry_trace": {"attempted_passes": ["regex_fallback"], "recovered": False},
                    }
                }
            },
        }
    ]

    augment(docs)

    amount = docs[0]["field_details"]["amount"]
    assert amount["decision_status"] == "retry"
    assert amount["reason_code"] == "extraction_failed"
    assert amount["retry_trace"]["recovered"] is False


def test_submission_eligibility_includes_reason_aggregates_and_unresolved_statuses():
    funcs = _load_functions(
        VALIDATE_PATH,
        ["_build_unresolved_critical_context", "_build_submission_eligibility_context"],
    )
    build_context = funcs["_build_submission_eligibility_context"]

    eligibility = build_context(
        {"missing_reason_codes": ["missing_in_source"]},
        {
            "amount": {"status": "retry", "reason_code": "extraction_failed"},
            "beneficiary": {"status": "rejected", "reason_code": "conflict_detected"},
        },
    )

    assert set(eligibility["missing_reason_codes"]) == {
        "missing_in_source",
        "extraction_failed",
        "conflict_detected",
    }
    assert set(eligibility["unresolved_critical_statuses"]) == {"retry", "rejected"}


def test_unresolved_criticals_never_surface_without_status_and_reason_code():
    funcs = _load_functions(VALIDATE_PATH, ["_build_unresolved_critical_context"])
    unresolved = funcs["_build_unresolved_critical_context"](
        {
            "amount": {"status": "retry", "reason_code": "extraction_failed"},
            "lc_number": {"status": "rejected"},
        }
    )

    for item in unresolved:
        assert item.get("status")
        assert item.get("reason_code")
