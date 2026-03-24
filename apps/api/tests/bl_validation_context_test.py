from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

from app.services.facts import (  # noqa: E402
    apply_bl_fact_graph_to_validation_inputs,
    project_bl_validation_context,
)


def test_project_bl_validation_context_uses_only_resolved_bl_facts() -> None:
    projected = project_bl_validation_context(
        {
            "shipper": "Stale Shipper",
            "goods_description": "100% cotton knit tops",
            "transport_mode": "sea",
        },
        fact_graph={
            "version": "fact_graph_v1",
            "document_type": "bill_of_lading",
            "facts": [
                {
                    "field_name": "bl_number",
                    "value": "BOL-2026-114",
                    "normalized_value": "BOL-2026-114",
                    "verification_state": "confirmed",
                },
                {
                    "field_name": "on_board_date",
                    "value": "21 Apr 2026",
                    "normalized_value": "2026-04-21",
                    "verification_state": "operator_confirmed",
                },
                {
                    "field_name": "port_of_loading",
                    "value": "Chittagong Sea Port, Bangladesh",
                    "normalized_value": "Chittagong Sea Port, Bangladesh",
                    "verification_state": "confirmed",
                },
                {
                    "field_name": "shipper",
                    "value": "Dhaka Knitwear & Exports Ltd.",
                    "normalized_value": "Dhaka Knitwear & Exports Ltd.",
                    "verification_state": "operator_rejected",
                },
            ],
        },
    )

    assert projected["bl_number"] == "BOL-2026-114"
    assert projected["bill_of_lading_number"] == "BOL-2026-114"
    assert projected["on_board_date"] == "2026-04-21"
    assert projected["shipped_on_board_date"] == "2026-04-21"
    assert projected["shipment_date"] == "2026-04-21"
    assert projected["port_of_loading"] == "Chittagong Sea Port, Bangladesh"
    assert projected["pol"] == "Chittagong Sea Port, Bangladesh"
    assert "shipper" not in projected
    assert "shipper_name" not in projected
    assert projected["goods_description"] == "100% cotton knit tops"
    assert projected["transport_mode"] == "sea"


def test_apply_bl_fact_graph_to_validation_inputs_mutates_payload_and_context() -> None:
    bl_document = {
        "document_id": "doc-bl",
        "document_type": "bill_of_lading",
        "filename": "Bill_of_Lading.pdf",
        "fact_graph_v1": {
            "version": "fact_graph_v1",
            "document_type": "bill_of_lading",
            "facts": [
                {
                    "field_name": "consignee",
                    "value": "TO ORDER OF ISSUING BANK",
                    "normalized_value": "TO ORDER OF ISSUING BANK",
                    "verification_state": "confirmed",
                },
                {
                    "field_name": "port_of_discharge",
                    "value": "Old Port",
                    "normalized_value": "Old Port",
                    "verification_state": "operator_rejected",
                },
            ],
        },
    }
    payload = {
        "bill_of_lading": {
            "consignee": "STALE CONSIGNEE",
            "port_of_discharge": "STALE PORT",
            "transport_mode": "sea",
        },
        "documents": [bl_document],
    }
    extracted_context = {
        "bill_of_lading": {
            "consignee": "STALE CONSIGNEE",
            "port_of_discharge": "STALE PORT",
        },
        "documents": [bl_document],
    }

    projected = apply_bl_fact_graph_to_validation_inputs(payload, extracted_context)

    assert projected["consignee"] == "TO ORDER OF ISSUING BANK"
    assert projected["consignee_name"] == "TO ORDER OF ISSUING BANK"
    assert "port_of_discharge" not in projected
    assert "pod" not in projected
    assert payload["bill_of_lading"]["consignee"] == "TO ORDER OF ISSUING BANK"
    assert "port_of_discharge" not in payload["bill_of_lading"]
    assert extracted_context["bill_of_lading"]["consignee"] == "TO ORDER OF ISSUING BANK"
    assert "port_of_discharge" not in extracted_context["bill_of_lading"]
