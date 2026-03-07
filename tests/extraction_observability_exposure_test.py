from __future__ import annotations

import ast
import copy
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_response_shaping_namespace() -> dict[str, object]:
    path = ROOT / "apps" / "api" / "app" / "routers" / "validation" / "response_shaping.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    wanted_assigns = {
        "EXPOSURE_DIAGNOSTICS_V1_ENV",
        "_MAX_STAGE_ATTEMPTS",
        "_MAX_REASON_CODES",
        "_MAX_STAGE_SCORE_STAGES",
        "_MAX_STAGE_SCORE_KEYS",
        "_SAFE_REASON_CODE_RE",
    }
    wanted_funcs = {
        "summarize_document_statuses",
        "_normalize_doc_status",
        "build_document_extraction_v1",
        "exposure_diagnostics_v1_enabled",
        "_sanitize_reason_codes",
        "_normalize_stage_scores",
        "_extract_stage_error_code",
        "build_extraction_debug",
        "attach_extraction_observability",
        "build_extraction_diagnostics",
    }
    selected = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            target_names = {target.id for target in node.targets if isinstance(target, ast.Name)}
            if target_names & wanted_assigns:
                selected.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in wanted_funcs:
            selected.append(node)

    module = ast.Module(
        body=ast.parse("import os\nimport re\nfrom typing import Any, Dict, List, Optional\n").body + selected,
        type_ignores=[],
    )
    namespace: dict[str, object] = {}
    exec(compile(module, str(path), "exec"), namespace)
    return namespace


RESPONSE_SHAPING = _load_response_shaping_namespace()


def _sample_doc(**overrides) -> dict[str, object]:
    payload = {
        "id": "doc-1",
        "name": "invoice.pdf",
        "documentType": "commercial_invoice",
        "status": "warning",
        "extractionStatus": "partial",
        "review_required": True,
        "review_reasons": ["FIELD_NOT_FOUND", "LOW_CONFIDENCE_CRITICAL", "critical_issuer_missing"],
        "critical_field_states": {
            "issue_date": "found",
            "issuer": "missing",
            "gross_weight": "parse_failed",
        },
        "extraction_artifacts_v1": {
            "raw_text": "Invoice Date 2026-01-01\nIssuer ???\nGross Weight BAD\n",
            "attempted_stages": ["native_pdf_text", "ocr_provider_primary", "ocr_secondary"],
            "text_length_by_stage": {
                "native_pdf_text": 42,
                "ocr_provider_primary": 78,
                "ocr_secondary": 64,
            },
            "stage_errors": {
                "ocr_provider_primary": ["OCR_TIMEOUT", "timed out waiting for provider"],
                "ocr_secondary": ["OCR_AUTH_ERROR"],
            },
            "reason_codes": ["OCR_TIMEOUT", "FIELD_NOT_FOUND"],
            "canonical_reason_codes": ["OCR_TIMEOUT", "FIELD_NOT_FOUND"],
            "stage_scores": {
                "native_pdf_text": {
                    "overall_score": 0.12,
                    "text_len_score": 0.10,
                    "alnum_ratio_score": 0.60,
                },
                "ocr_provider_primary": {
                    "overall_score": 0.91,
                    "text_len_score": 0.75,
                    "alnum_ratio_score": 0.95,
                    "anchor_hit_score": 1.0,
                },
            },
            "selected_stage": "ocr_provider_primary",
            "final_stage": "ocr_provider_primary",
            "final_text_length": 78,
        },
    }
    payload.update(overrides)
    return payload


def test_selected_stage_present_when_extraction_ran(monkeypatch):
    monkeypatch.delenv("LCCOPILOT_EXPOSURE_DIAGNOSTICS_V1_ENABLED", raising=False)
    debug = RESPONSE_SHAPING["build_extraction_debug"](_sample_doc())
    assert debug is not None
    assert debug["selected_stage"] == "ocr_provider_primary"


def test_stage_score_map_present_and_deterministic(monkeypatch):
    monkeypatch.delenv("LCCOPILOT_EXPOSURE_DIAGNOSTICS_V1_ENABLED", raising=False)
    debug = RESPONSE_SHAPING["build_extraction_debug"](_sample_doc())
    assert debug["stage_scores"] == {
        "native_pdf_text": {
            "overall_score": 0.12,
            "text_len_score": 0.1,
            "alnum_ratio_score": 0.6,
        },
        "ocr_provider_primary": {
            "overall_score": 0.91,
            "text_len_score": 0.75,
            "alnum_ratio_score": 0.95,
            "anchor_hit_score": 1.0,
        },
    }


def test_stage_attempts_include_error_code_when_provider_fails(monkeypatch):
    monkeypatch.delenv("LCCOPILOT_EXPOSURE_DIAGNOSTICS_V1_ENABLED", raising=False)
    debug = RESPONSE_SHAPING["build_extraction_debug"](_sample_doc())
    attempts = {entry["stage"]: entry for entry in debug["stage_attempts"]}
    assert attempts["ocr_provider_primary"]["error_code"] == "OCR_TIMEOUT"
    assert attempts["ocr_secondary"]["error_code"] == "OCR_AUTH_ERROR"


def test_critical_field_states_map_populated(monkeypatch):
    monkeypatch.delenv("LCCOPILOT_EXPOSURE_DIAGNOSTICS_V1_ENABLED", raising=False)
    debug = RESPONSE_SHAPING["build_extraction_debug"](_sample_doc())
    assert debug["critical_field_states"] == {
        "issue_date": "found",
        "issuer": "missing",
        "gross_weight": "parse_failed",
    }


def test_unresolved_critical_fields_top_level_aggregation(monkeypatch):
    monkeypatch.delenv("LCCOPILOT_EXPOSURE_DIAGNOSTICS_V1_ENABLED", raising=False)
    documents = [_sample_doc(), _sample_doc(id="doc-2")]
    RESPONSE_SHAPING["attach_extraction_observability"](documents)
    diagnostics = RESPONSE_SHAPING["build_extraction_diagnostics"](documents)
    assert diagnostics["unresolved_critical_fields"] == ["gross_weight", "issuer"]


def test_failure_reasons_top_level_aggregation(monkeypatch):
    monkeypatch.delenv("LCCOPILOT_EXPOSURE_DIAGNOSTICS_V1_ENABLED", raising=False)
    documents = [_sample_doc(), _sample_doc(id="doc-2", review_reasons=["OCR_AUTH_ERROR", "FIELD_NOT_FOUND"])]
    RESPONSE_SHAPING["attach_extraction_observability"](documents)
    diagnostics = RESPONSE_SHAPING["build_extraction_diagnostics"](documents)
    assert diagnostics["failure_reasons"] == ["OCR_TIMEOUT", "FIELD_NOT_FOUND", "LOW_CONFIDENCE_CRITICAL", "OCR_AUTH_ERROR"]


def test_no_raw_text_leak_in_diagnostics(monkeypatch):
    monkeypatch.delenv("LCCOPILOT_EXPOSURE_DIAGNOSTICS_V1_ENABLED", raising=False)
    debug = RESPONSE_SHAPING["build_extraction_debug"](_sample_doc())
    serialized = json.dumps(debug, sort_keys=True)
    assert "raw_text" not in debug
    assert "Issuer ???" not in serialized


def test_backward_compatibility_existing_fields_unchanged(monkeypatch):
    monkeypatch.delenv("LCCOPILOT_EXPOSURE_DIAGNOSTICS_V1_ENABLED", raising=False)
    documents = [copy.deepcopy(_sample_doc())]
    RESPONSE_SHAPING["attach_extraction_observability"](documents)
    payload = RESPONSE_SHAPING["build_document_extraction_v1"](documents)
    document = payload["documents"][0]
    assert document["document_id"] == "doc-1"
    assert document["document_type"] == "commercial_invoice"
    assert document["status"] == "warning"
    assert document["review_required"] is True
    assert document["extraction_debug"]["selected_stage"] == "ocr_provider_primary"


def test_diagnostics_included_for_partial_docs(monkeypatch):
    monkeypatch.delenv("LCCOPILOT_EXPOSURE_DIAGNOSTICS_V1_ENABLED", raising=False)
    documents = [_sample_doc(extractionStatus="partial")]
    RESPONSE_SHAPING["attach_extraction_observability"](documents)
    diagnostics = RESPONSE_SHAPING["build_extraction_diagnostics"](documents)
    assert diagnostics["review_gate_inputs"]["documents_evaluated"] == 1
    assert diagnostics["review_gate_inputs"]["critical_fields_unresolved"] == 2


def test_diagnostics_omitted_when_flag_off(monkeypatch):
    monkeypatch.setenv("LCCOPILOT_EXPOSURE_DIAGNOSTICS_V1_ENABLED", "0")
    documents = [_sample_doc()]
    RESPONSE_SHAPING["attach_extraction_observability"](documents)
    diagnostics = RESPONSE_SHAPING["build_extraction_diagnostics"](documents)
    assert "extraction_debug" not in documents[0]
    assert diagnostics is None


def test_validate_source_wires_document_and_top_level_diagnostics():
    source = (ROOT / "apps" / "api" / "app" / "routers" / "validate.py").read_text(encoding="utf-8")
    assert "_response_shaping.attach_extraction_observability(document_summaries)" in source
    assert '_response_shaping.build_extraction_diagnostics(' in source
    assert 'structured_result["_extraction_diagnostics"] = extraction_diagnostics' in source
    assert 'result["_extraction_diagnostics"] = extraction_diagnostics' in source


def test_shared_type_sources_expose_diagnostics_fields():
    ts_source = (ROOT / "packages" / "shared-types" / "src" / "api.ts").read_text(encoding="utf-8")
    py_source = (ROOT / "packages" / "shared-types" / "python" / "schemas.py").read_text(encoding="utf-8")
    assert "extraction_debug" in ts_source
    assert "_extraction_diagnostics" in ts_source
    assert "extraction_debug" in py_source
    assert "_extraction_diagnostics" in py_source
