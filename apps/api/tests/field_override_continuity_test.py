from __future__ import annotations

import ast
import copy
from pathlib import Path
from typing import Any, Dict, List, Optional


ROOT = Path(__file__).resolve().parents[1]
JOBS_PUBLIC_PATH = ROOT / "app" / "routers" / "jobs_public.py"


def _load_symbols(target_names: set[str]) -> Dict[str, Any]:
    source = JOBS_PUBLIC_PATH.read_text(encoding="utf-8")
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
        "copy": copy,
    }
    exec(compile(module_ast, str(JOBS_PUBLIC_PATH), "exec"), namespace)
    return namespace


def test_apply_field_override_updates_document_review_state_and_field_metadata() -> None:
    symbols = _load_symbols(
        {
            "_normalize_override_field_name",
            "_is_unresolved_field_state",
            "_remove_override_resolved_review_reasons",
            "_apply_field_override_to_document",
        }
    )
    apply_field_override_to_document = symbols["_apply_field_override_to_document"]

    document = {
        "document_id": "doc-invoice",
        "extracted_fields": {"invoice_number": "DKEL/EXP/2026/114"},
        "field_details": {
            "invoice_date": {
                "verification": "not_found",
                "status": "missing",
            }
        },
        "missing_required_fields": ["invoice_date"],
        "review_reasons": ["FIELD_NOT_FOUND", "critical_invoice_date_missing"],
        "critical_field_states": {"invoice_date": "missing"},
        "review_required": True,
        "extraction_artifacts_v1": {
            "field_diagnostics": {
                "invoice_date": {"state": "missing", "reason_codes": ["FIELD_NOT_FOUND"]}
            }
        },
    }

    updated = apply_field_override_to_document(
        document,
        field_name="invoice_date",
        override_value="2026-04-20",
        note="Confirmed from invoice header",
        actor_email="imran@iec.com",
        applied_at_iso="2026-03-23T12:00:00+00:00",
    )

    assert updated["extracted_fields"]["invoice_date"] == "2026-04-20"
    assert updated["field_details"]["invoice_date"]["verification"] == "operator_confirmed"
    assert updated["field_details"]["invoice_date"]["source"] == "operator_override"
    assert updated["missing_required_fields"] == []
    assert updated["critical_field_states"]["invoice_date"] == "found"
    assert updated["review_reasons"] == []
    assert updated["review_required"] is False
    assert (
        updated["extraction_artifacts_v1"]["field_diagnostics"]["invoice_date"]["state"]
        == "operator_confirmed"
    )


def test_apply_field_override_updates_top_level_and_lc_structured_document_collections() -> None:
    symbols = _load_symbols(
        {
            "_normalize_override_field_name",
            "_is_unresolved_field_state",
            "_remove_override_resolved_review_reasons",
            "_apply_field_override_to_document",
            "_apply_field_override_to_structured_result",
        }
    )
    apply_field_override_to_structured_result = symbols["_apply_field_override_to_structured_result"]

    structured_result = {
        "documents": [
            {
                "document_id": "doc-pack",
                "extracted_fields": {},
                "field_details": {"issue_date": {"verification": "not_found"}},
                "missing_required_fields": ["issue_date"],
                "review_reasons": ["FIELD_NOT_FOUND", "critical_issue_date_missing"],
                "critical_field_states": {"issue_date": "missing"},
            }
        ],
        "documents_structured": [
            {
                "document_id": "doc-pack",
                "extracted_fields": {},
                "field_details": {"issue_date": {"verification": "not_found"}},
                "missing_required_fields": ["issue_date"],
                "review_reasons": ["FIELD_NOT_FOUND", "critical_issue_date_missing"],
                "critical_field_states": {"issue_date": "missing"},
            }
        ],
        "document_extraction_v1": {
            "documents": [
                {
                    "document_id": "doc-pack",
                    "extracted_fields": {},
                    "field_details": {"issue_date": {"verification": "not_found"}},
                    "missing_required_fields": ["issue_date"],
                    "review_reasons": ["FIELD_NOT_FOUND", "critical_issue_date_missing"],
                    "critical_field_states": {"issue_date": "missing"},
                }
            ]
        },
        "processing_summary": {
            "documents": [
                {
                    "document_id": "doc-pack",
                    "extracted_fields": {},
                    "field_details": {"issue_date": {"verification": "not_found"}},
                    "missing_required_fields": ["issue_date"],
                    "review_reasons": ["FIELD_NOT_FOUND", "critical_issue_date_missing"],
                    "critical_field_states": {"issue_date": "missing"},
                }
            ]
        },
        "processing_summary_v2": {
            "documents": [
                {
                    "document_id": "doc-pack",
                    "extracted_fields": {},
                    "field_details": {"issue_date": {"verification": "not_found"}},
                    "missing_required_fields": ["issue_date"],
                    "review_reasons": ["FIELD_NOT_FOUND", "critical_issue_date_missing"],
                    "critical_field_states": {"issue_date": "missing"},
                }
            ]
        },
        "lc_structured": {
            "documents_structured": [
                {
                    "document_id": "doc-pack",
                    "extracted_fields": {},
                    "field_details": {"issue_date": {"verification": "not_found"}},
                    "missing_required_fields": ["issue_date"],
                    "review_reasons": ["FIELD_NOT_FOUND", "critical_issue_date_missing"],
                    "critical_field_states": {"issue_date": "missing"},
                }
            ]
        },
    }

    updated_document = apply_field_override_to_structured_result(
        structured_result,
        document_id="doc-pack",
        field_name="issue_date",
        override_value="2026-04-20",
        note="Confirmed from packing list header",
        actor_email="imran@iec.com",
        applied_at_iso="2026-03-23T12:00:00+00:00",
    )

    assert updated_document is not None
    assert structured_result["documents"][0]["extracted_fields"]["issue_date"] == "2026-04-20"
    assert structured_result["documents_structured"][0]["field_details"]["issue_date"]["verification"] == "operator_confirmed"
    assert structured_result["document_extraction_v1"]["documents"][0]["field_details"]["issue_date"]["verification"] == "operator_confirmed"
    assert structured_result["processing_summary"]["documents"][0]["critical_field_states"]["issue_date"] == "found"
    assert structured_result["processing_summary_v2"]["documents"][0]["critical_field_states"]["issue_date"] == "found"
    assert structured_result["lc_structured"]["documents_structured"][0]["critical_field_states"]["issue_date"] == "found"


def test_record_operator_field_override_persists_session_override_metadata() -> None:
    symbols = _load_symbols({"_normalize_override_field_name", "_record_operator_field_override"})
    record_operator_field_override = symbols["_record_operator_field_override"]

    updated = record_operator_field_override(
        {"lc_number": "EXP2026BD001"},
        document_id="doc-coo",
        field_name="exporter_name",
        override_value="Dhaka Knitwear & Exports Ltd.",
        note="Confirmed from certificate body",
        actor_id="user-1",
        actor_email="imran@iec.com",
        applied_at_iso="2026-03-23T12:00:00+00:00",
    )

    override = updated["operator_field_overrides"]["doc-coo"]["exporter_name"]
    assert override["value"] == "Dhaka Knitwear & Exports Ltd."
    assert override["verification"] == "operator_confirmed"
    assert override["confirmed_by"] == "imran@iec.com"
