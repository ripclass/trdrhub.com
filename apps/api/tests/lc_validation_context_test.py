from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

from app.services.facts import (  # noqa: E402
    apply_lc_fact_graph_to_validation_inputs,
    project_lc_validation_context,
)


def test_project_lc_validation_context_uses_only_resolved_rendered_lc_facts() -> None:
    projected = project_lc_validation_context(
        {
            "number": "STALE-LC",
            "issue_date": "01 Jan 2026",
            "expiry_date": "30 Jun 2026",
            "latest_shipment": "15 Jun 2026",
            "applicant": "Old Applicant",
            "beneficiary": "Old Beneficiary",
            "amount": {"value": 0, "currency": "USD"},
            "currency": "USD",
            "port_of_loading": "Old Port",
            "goods_description": "Cotton knitwear",
            "documents_required": ["Invoice", "Packing List"],
            "incoterm": "FOB",
            "ucp_reference": "UCP LATEST VERSION",
            "raw_text": "original lc text",
            "format": "pdf_text",
        },
        document={
            "document_type": "letter_of_credit",
            "extraction_lane": "document_ai",
            "requirements_graph_v1": {
                "version": "requirements_graph_v1",
                "required_document_types": ["commercial_invoice", "packing_list"],
            },
        },
        fact_graph={
            "version": "fact_graph_v1",
            "document_type": "letter_of_credit",
            "facts": [
                {
                    "field_name": "lc_number",
                    "value": "EXP2026BD001",
                    "normalized_value": "EXP2026BD001",
                    "verification_state": "confirmed",
                },
                {
                    "field_name": "issue_date",
                    "value": "15 Apr 2026",
                    "normalized_value": "2026-04-15",
                    "verification_state": "confirmed",
                },
                {
                    "field_name": "expiry_date",
                    "value": "15 Oct 2026",
                    "normalized_value": "2026-10-15",
                    "verification_state": "operator_confirmed",
                },
                {
                    "field_name": "latest_shipment_date",
                    "value": "30 Sep 2026",
                    "normalized_value": "2026-09-30",
                    "verification_state": "confirmed",
                },
                {
                    "field_name": "applicant",
                    "value": "ABC Imports Ltd.",
                    "normalized_value": "ABC Imports Ltd.",
                    "verification_state": "confirmed",
                },
                {
                    "field_name": "beneficiary",
                    "value": "Rejected Beneficiary",
                    "normalized_value": "Rejected Beneficiary",
                    "verification_state": "operator_rejected",
                },
                {
                    "field_name": "amount",
                    "value": "USD 125,000.50",
                    "normalized_value": "125000.50",
                    "verification_state": "confirmed",
                },
                {
                    "field_name": "currency",
                    "value": "usd",
                    "normalized_value": "USD",
                    "verification_state": "confirmed",
                },
                {
                    "field_name": "port_of_loading",
                    "value": "Chittagong",
                    "normalized_value": "Chittagong",
                    "verification_state": "confirmed",
                },
                {
                    "field_name": "goods_description",
                    "value": "100% Cotton T-Shirts",
                    "normalized_value": "100% Cotton T-Shirts",
                    "verification_state": "confirmed",
                },
                {
                    "field_name": "documents_required",
                    "value": ["Commercial Invoice", "Packing List"],
                    "normalized_value": ["Commercial Invoice", "Packing List"],
                    "verification_state": "confirmed",
                },
            ],
        },
    )

    assert projected["lc_number"] == "EXP2026BD001"
    assert projected["number"] == "EXP2026BD001"
    assert projected["reference"] == "EXP2026BD001"
    assert projected["issue_date"] == "2026-04-15"
    assert projected["dates"]["issue"] == "2026-04-15"
    assert projected["expiry_date"] == "2026-10-15"
    assert projected["latest_shipment"] == "2026-09-30"
    assert projected["applicant"] == "ABC Imports Ltd."
    assert "beneficiary" not in projected
    assert projected["amount"]["value"] == "125000.50"
    assert projected["amount"]["currency"] == "USD"
    assert projected["currency"] == "USD"
    assert projected["port_of_loading"] == "Chittagong"
    assert projected["goods_description"] == "100% Cotton T-Shirts"
    assert projected["documents_required"] == ["Commercial Invoice", "Packing List"]
    assert projected["incoterm"] == "FOB"
    assert projected["raw_text"] == "original lc text"
    assert projected["requirements_graph_v1"]["required_document_types"] == [
        "commercial_invoice",
        "packing_list",
    ]


def test_project_lc_validation_context_leaves_structured_lc_context_intact() -> None:
    base_context = {
        "number": "EXP2026BD001",
        "issue_date": "2026-04-15",
        "mt700": {"blocks": {"20": "EXP2026BD001"}},
        "format": "mt700",
    }

    projected = project_lc_validation_context(
        base_context,
        document={
            "document_type": "letter_of_credit",
            "extraction_lane": "structured_mt",
        },
    )

    assert projected["number"] == "EXP2026BD001"
    assert projected["mt700"]["blocks"]["20"] == "EXP2026BD001"
    assert projected["format"] == "mt700"


def test_apply_lc_fact_graph_to_validation_inputs_mutates_payload_and_context_for_rendered_lc() -> None:
    lc_document = {
        "document_id": "doc-lc",
        "document_type": "letter_of_credit",
        "filename": "LC.pdf",
        "extraction_lane": "document_ai",
        "fact_graph_v1": {
            "version": "fact_graph_v1",
            "document_type": "letter_of_credit",
            "facts": [
                {
                    "field_name": "lc_number",
                    "value": "EXP2026BD001",
                    "normalized_value": "EXP2026BD001",
                    "verification_state": "confirmed",
                },
                {
                    "field_name": "issue_date",
                    "value": "15 Apr 2026",
                    "normalized_value": "2026-04-15",
                    "verification_state": "confirmed",
                },
                {
                    "field_name": "beneficiary",
                    "value": "Old Beneficiary",
                    "normalized_value": "Old Beneficiary",
                    "verification_state": "operator_rejected",
                },
            ],
        },
    }
    payload = {
        "lc": {"number": "STALE-LC", "beneficiary": "STALE BENEFICIARY"},
        "documents": [lc_document],
    }
    extracted_context = {
        "lc": {"number": "STALE-LC", "beneficiary": "STALE BENEFICIARY"},
        "documents": [lc_document],
    }

    projected = apply_lc_fact_graph_to_validation_inputs(payload, extracted_context)

    assert projected["number"] == "EXP2026BD001"
    assert projected["lc_number"] == "EXP2026BD001"
    assert projected["issue_date"] == "2026-04-15"
    assert "beneficiary" not in projected
    assert payload["lc"]["number"] == "EXP2026BD001"
    assert "beneficiary" not in payload["lc"]
    assert extracted_context["lc"]["number"] == "EXP2026BD001"
    assert "beneficiary" not in extracted_context["lc"]
