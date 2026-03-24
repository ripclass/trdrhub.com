from __future__ import annotations

import ast
import copy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from decimal import Decimal
from fastapi.encoders import jsonable_encoder


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
        "datetime": datetime,
        "timezone": timezone,
        "uuid4": uuid4,
        "Decimal": Decimal,
        "jsonable_encoder": jsonable_encoder,
    }
    exec(compile(module_ast, str(JOBS_PUBLIC_PATH), "exec"), namespace)
    return namespace


def test_apply_field_override_updates_document_review_state_and_field_metadata() -> None:
    symbols = _load_symbols(
        {
            "_document_matches_override_target",
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
        "extraction_resolution": {
            "required": True,
            "unresolved_count": 1,
            "summary": "1 field still needs confirmation from source evidence.",
            "fields": [{"field_name": "invoice_date", "label": "Invoice Date"}],
        },
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
        verification="operator_confirmed",
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
    assert updated["extraction_resolution"]["required"] is False
    assert updated["extraction_resolution"]["unresolved_count"] == 0
    assert (
        updated["extraction_artifacts_v1"]["field_diagnostics"]["invoice_date"]["state"]
        == "operator_confirmed"
    )


def test_apply_field_override_updates_top_level_and_lc_structured_document_collections() -> None:
    symbols = _load_symbols(
        {
            "_document_matches_override_target",
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
        verification="operator_confirmed",
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


def test_apply_field_override_matches_filename_alias_when_uuid_is_not_sent() -> None:
    symbols = _load_symbols(
        {
            "_document_matches_override_target",
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
                "document_id": "doc-bl-uuid",
                "filename": "Bill_of_Lading.pdf",
                "extracted_fields": {"issue_date": "2026-03-24"},
                "field_details": {"issue_date": {"verification": "model_suggested"}},
                "missing_required_fields": [],
                "review_reasons": ["FIELD_NOT_FOUND"],
                "critical_field_states": {"issue_date": "missing"},
            }
        ]
    }

    updated_document = apply_field_override_to_structured_result(
        structured_result,
        document_id="Bill_of_Lading.pdf",
        field_name="issue_date",
        override_value="2026-03-24",
        verification="operator_rejected",
        note="Rejected from browser alias payload",
        actor_email="imran@iec.com",
        applied_at_iso="2026-03-23T12:00:00+00:00",
    )

    assert updated_document is not None
    assert updated_document["document_id"] == "doc-bl-uuid"
    assert updated_document["field_details"]["issue_date"]["verification"] == "operator_rejected"


def test_record_operator_field_override_persists_session_override_metadata() -> None:
    symbols = _load_symbols({"_normalize_override_field_name", "_record_operator_field_override"})
    record_operator_field_override = symbols["_record_operator_field_override"]

    updated = record_operator_field_override(
        {"lc_number": "EXP2026BD001"},
        document_id="doc-coo",
        field_name="exporter_name",
        override_value="Dhaka Knitwear & Exports Ltd.",
        verification="operator_confirmed",
        note="Confirmed from certificate body",
        actor_id="user-1",
        actor_email="imran@iec.com",
        applied_at_iso="2026-03-23T12:00:00+00:00",
    )

    override = updated["operator_field_overrides"]["doc-coo"]["exporter_name"]
    assert override["value"] == "Dhaka Knitwear & Exports Ltd."
    assert override["verification"] == "operator_confirmed"
    assert override["confirmed_by"] == "imran@iec.com"


def test_build_field_override_response_coerces_nested_non_json_types() -> None:
    symbols = _load_symbols({"_build_field_override_response"})
    build_field_override_response = symbols["_build_field_override_response"]

    updated_document = {
        "document_id": uuid4(),
        "field_details": {
            "issue_date": {
                "operator_confirmed_at": datetime(2026, 3, 23, 15, 0, tzinfo=timezone.utc),
                "confidence": Decimal("1.0"),
            }
        },
    }

    response = build_field_override_response(
        session_id=str(uuid4()),
        document_id=str(uuid4()),
        field_name="issue_date",
        override_value="2026-04-20",
        verification="operator_confirmed",
        applied_at_iso="2026-03-23T15:00:00+00:00",
        updated_document=updated_document,
    )

    assert isinstance(response["updated_document"]["document_id"], str)
    assert (
        response["updated_document"]["field_details"]["issue_date"]["operator_confirmed_at"]
        == "2026-03-23T15:00:00+00:00"
    )
    assert (
        response["updated_document"]["field_details"]["issue_date"]["confidence"] == 1.0
    )


def test_apply_field_override_rejection_keeps_field_unresolved() -> None:
    symbols = _load_symbols(
        {
            "_document_matches_override_target",
            "_normalize_override_field_name",
            "_is_unresolved_field_state",
            "_remove_override_resolved_review_reasons",
            "_apply_field_override_to_document",
        }
    )
    apply_field_override_to_document = symbols["_apply_field_override_to_document"]

    document = {
        "document_id": "doc-invoice",
        "extracted_fields": {"invoice_date": "2026-04-20"},
        "field_details": {
            "invoice_date": {
                "verification": "model_suggested",
                "status": "missing",
                "value": "2026-04-20",
            }
        },
        "missing_required_fields": [],
        "review_reasons": ["FIELD_NOT_FOUND"],
        "critical_field_states": {"invoice_date": "missing"},
        "review_required": True,
        "extraction_resolution": {
            "required": True,
            "unresolved_count": 1,
            "summary": "1 field still needs confirmation from source evidence.",
            "fields": [{"field_name": "invoice_date", "label": "Invoice Date"}],
        },
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
        verification="operator_rejected",
        note="This date does not match the invoice header.",
        actor_email="imran@iec.com",
        applied_at_iso="2026-03-23T12:00:00+00:00",
    )

    assert "invoice_date" not in updated["extracted_fields"]
    assert updated["field_details"]["invoice_date"]["verification"] == "operator_rejected"
    assert updated["field_details"]["invoice_date"]["rejected_value"] == "2026-04-20"
    assert updated["missing_required_fields"] == ["invoice_date"]
    assert updated["critical_field_states"]["invoice_date"] == "unconfirmed"
    assert updated["review_required"] is True
    assert updated["extraction_resolution"]["required"] is True
    assert updated["extraction_resolution"]["unresolved_count"] == 1
    assert updated["extraction_resolution"]["fields"][0]["verification"] == "operator_rejected"
    assert (
        updated["extraction_artifacts_v1"]["field_diagnostics"]["invoice_date"]["state"]
        == "operator_rejected"
    )


def test_record_operator_field_override_persists_rejection_metadata() -> None:
    symbols = _load_symbols({"_normalize_override_field_name", "_record_operator_field_override"})
    record_operator_field_override = symbols["_record_operator_field_override"]

    updated = record_operator_field_override(
        {"lc_number": "EXP2026BD001"},
        document_id="doc-invoice",
        field_name="invoice_date",
        override_value="2026-04-20",
        verification="operator_rejected",
        note="Rejected after checking the invoice header.",
        actor_id="user-1",
        actor_email="imran@iec.com",
        applied_at_iso="2026-03-23T12:00:00+00:00",
    )

    override = updated["operator_field_overrides"]["doc-invoice"]["invoice_date"]
    assert override["value"] is None
    assert override["rejected_value"] == "2026-04-20"
    assert override["verification"] == "operator_rejected"
    assert override["rejected_by"] == "imran@iec.com"
