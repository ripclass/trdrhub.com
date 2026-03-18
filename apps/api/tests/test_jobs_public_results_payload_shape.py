import ast
from pathlib import Path
from typing import Any, Dict, Optional


JOBS_PUBLIC_PATH = Path(__file__).resolve().parents[1] / "app" / "routers" / "jobs_public.py"


def _load_helpers():
    source = JOBS_PUBLIC_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    targets = []
    wanted = {
        "_looks_like_structured_result",
        "_normalize_structured_result_shape",
        "_extract_option_e_payload",
    }
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in wanted:
            targets.append(node)
    module = ast.Module(body=targets, type_ignores=[])
    namespace = {
        "Any": Any,
        "Dict": Dict,
        "Optional": Optional,
    }
    exec(compile(module, filename=str(JOBS_PUBLIC_PATH), mode="exec"), namespace)
    return namespace


def test_extract_option_e_payload_accepts_nested_unversioned_structured_result():
    helpers = _load_helpers()
    extract_option_e_payload = helpers["_extract_option_e_payload"]

    payload = {
        "structured_result": {
            "documents": [{"document_type": "letter_of_credit"}],
            "issues": [],
            "processing_summary": {"documents_processed": 1},
            "validation_status": "pass",
        }
    }

    structured = extract_option_e_payload(payload)

    assert structured is not None
    assert structured["version"] == "structured_result_v1"
    assert structured["documents"] == [{"document_type": "letter_of_credit"}]
    assert structured["documents_structured"] == [{"document_type": "letter_of_credit"}]


def test_extract_option_e_payload_accepts_flat_unversioned_structured_result():
    helpers = _load_helpers()
    extract_option_e_payload = helpers["_extract_option_e_payload"]

    payload = {
        "documents_structured": [{"document_type": "commercial_invoice"}],
        "analytics": {"compliance_score": 91},
        "submission_eligibility": {"can_submit": True},
    }

    structured = extract_option_e_payload(payload)

    assert structured is not None
    assert structured["version"] == "structured_result_v1"
    assert structured["documents"] == [{"document_type": "commercial_invoice"}]
    assert structured["documents_structured"] == [{"document_type": "commercial_invoice"}]
