import ast
from pathlib import Path
from typing import Any, Dict, List, Optional


ROOT = Path(__file__).resolve().parents[1]
RESPONSE_SHAPING_PATH = ROOT / "app" / "routers" / "validation" / "response_shaping.py"


def _load_response_shaping_symbols(target_names: set[str]) -> Dict[str, Any]:
    source = RESPONSE_SHAPING_PATH.read_text(encoding="utf-8")
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
    }
    exec(compile(module_ast, str(RESPONSE_SHAPING_PATH), "exec"), namespace)
    return namespace


def test_build_public_validation_envelope_mirrors_contract_surfaces() -> None:
    symbols = _load_response_shaping_symbols({"build_public_validation_envelope"})
    build_public_validation_envelope = symbols["build_public_validation_envelope"]

    structured_result = {
        "version": "structured_result_v1",
        "validation_contract_v1": {
            "final_verdict": "review",
            "ruleset_verdict": "review",
        },
        "submission_eligibility": {
            "can_submit": False,
            "reasons": ["validation_contract_review"],
        },
        "raw_submission_eligibility": {
            "can_submit": True,
            "reasons": [],
        },
        "bank_verdict": {
            "verdict": "CAUTION",
            "can_submit": False,
        },
    }

    payload = build_public_validation_envelope(
        job_id="job-123",
        structured_result=structured_result,
        telemetry={"UnifiedStructuredResultServed": True},
    )

    assert payload["job_id"] == "job-123"
    assert payload["jobId"] == "job-123"
    assert payload["structured_result"] is structured_result
    assert payload["validation_contract_v1"]["final_verdict"] == "review"
    assert payload["final_verdict"] == "review"
    assert payload["ruleset_verdict"] == "review"
    assert payload["submission_can_submit"] is False
    assert payload["submission_reasons"] == ["validation_contract_review"]
    assert payload["submission_eligibility"]["can_submit"] is False
    assert payload["effective_submission_eligibility"]["can_submit"] is False
    assert payload["raw_submission_eligibility"]["can_submit"] is True
    assert payload["bank_verdict"]["verdict"] == "CAUTION"
