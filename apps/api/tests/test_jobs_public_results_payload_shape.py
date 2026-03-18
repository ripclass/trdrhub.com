import ast
from pathlib import Path
from typing import Any, Dict, List, Optional


JOBS_PUBLIC_PATH = Path(__file__).resolve().parents[1] / "app" / "routers" / "jobs_public.py"


def _load_helpers():
    source = JOBS_PUBLIC_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    targets = []
    wanted = {
        "_looks_like_structured_result",
        "_normalize_structured_result_shape",
        "_extract_option_e_payload",
        "_extract_lc_number",
        "_build_fallback_structured_result",
    }
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in wanted:
            targets.append(node)
    module = ast.Module(body=targets, type_ignores=[])
    namespace = {
        "Any": Any,
        "Dict": Dict,
        "List": List,
        "Optional": Optional,
        "ValidationSession": object,
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


def test_build_fallback_structured_result_reconstructs_completed_session_payload():
    helpers = _load_helpers()
    build_fallback_structured_result = helpers["_build_fallback_structured_result"]

    class DummyDocument:
        document_type = "commercial_invoice"
        original_filename = "Invoice.pdf"
        extracted_fields = {"invoice_number": "INV-001"}
        ocr_confidence = 0.94

    class DummySession:
        extracted_data = {"lc_number": "EXP2026BD001", "invoice": {"amount": "1000"}}
        documents = [DummyDocument()]
        discrepancies = []
        validation_results = None

    structured = build_fallback_structured_result(DummySession())

    assert structured is not None
    assert structured["version"] == "structured_result_v1"
    assert structured["lc_number"] == "EXP2026BD001"
    assert structured["documents_structured"][0]["filename"] == "Invoice.pdf"
    assert structured["submission_eligibility"]["can_submit"] is True
    assert structured["processing_summary"]["total_documents"] == 1
