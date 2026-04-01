from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

from app.services.facts.bl_facts import build_bl_fact_set  # noqa: E402


def _fact_by_name(payload: dict, field_name: str) -> dict:
    facts = payload.get("facts") or []
    for fact in facts:
        if fact.get("field_name") == field_name:
            return fact
    raise AssertionError(f"Missing fact {field_name}")


def test_build_bl_fact_set_confirms_on_board_date_with_evidence() -> None:
    payload = build_bl_fact_set(
        {
            "document_type": "bill_of_lading",
            "transport_subtype": "ocean_bill_of_lading",
            "extraction_lane": "document_ai",
            "extracted_fields": {"shipped_on_board_date": "21 Apr 2026"},
            "field_details": {
                "shipped_on_board_date": {
                    "value": "21 Apr 2026",
                    "confidence": 0.91,
                    "verification": "confirmed",
                    "source": "multimodal:pdf_pages",
                    "evidence": {
                        "snippet": "Shipped on Board 21 Apr 2026",
                        "source": "visual+native_text",
                        "page": 1,
                    },
                }
            },
        }
    )

    fact = _fact_by_name(payload, "on_board_date")
    assert fact["normalized_value"] == "2026-04-21"
    assert fact["verification_state"] == "confirmed"
    assert fact["origin"] == "multimodal:pdf_pages"
    assert fact["evidence_source"] == "visual+native_text"
    assert fact["page"] == 1


def test_build_bl_fact_set_maps_candidate_shipper_alias() -> None:
    payload = build_bl_fact_set(
        {
            "document_type": "bill_of_lading",
            "transport_subtype": "bill_of_lading",
            "extracted_fields": {"shipper_name": "Dhaka Knitwear & Exports Ltd."},
            "field_details": {
                "shipper_name": {
                    "value": "Dhaka Knitwear & Exports Ltd.",
                    "confidence": 0.63,
                    "verification": "model_suggested",
                }
            },
        }
    )

    fact = _fact_by_name(payload, "shipper")
    assert fact["value"] == "Dhaka Knitwear & Exports Ltd."
    assert fact["verification_state"] == "candidate"
    assert fact["source_field_name"] == "shipper_name"


def test_build_bl_fact_set_marks_absent_consignee_when_source_absent() -> None:
    payload = build_bl_fact_set(
        {
            "document_type": "bill_of_lading",
            "transport_subtype": "bill_of_lading",
            "field_details": {
                "consignee_name": {
                    "verification": "not_found",
                    "reason_code": "source_absent",
                }
            },
        }
    )

    fact = _fact_by_name(payload, "consignee")
    assert fact["value"] is None
    assert fact["verification_state"] == "absent_in_source"
    assert fact["source_field_name"] == "consignee_name"


def test_build_bl_fact_set_normalizes_transport_reference_and_ports() -> None:
    payload = build_bl_fact_set(
        {
            "document_type": "bill_of_lading",
            "transport_subtype": "bill_of_lading",
            "extracted_fields": {
                "transport_document_reference": " HLCU/EXP/2026/114 ",
                "pol": " Chittagong Sea Port, Bangladesh ",
                "pod": " New York, USA ",
            },
        }
    )

    bl_number_fact = _fact_by_name(payload, "bl_number")
    pol_fact = _fact_by_name(payload, "port_of_loading")
    pod_fact = _fact_by_name(payload, "port_of_discharge")
    assert bl_number_fact["normalized_value"] == "HLCU/EXP/2026/114"
    assert pol_fact["normalized_value"] == "Chittagong Sea Port, Bangladesh"
    assert pod_fact["normalized_value"] == "New York, USA"


def test_build_bl_fact_set_confirms_raw_text_supported_ports() -> None:
    payload = build_bl_fact_set(
        {
            "document_type": "bill_of_lading",
            "transport_subtype": "ocean_bill_of_lading",
            "extracted_fields": {
                "port_of_loading": "Chattogram, Bangladesh",
                "port_of_discharge": "New York, United States",
            },
            "field_details": {
                "port_of_loading": {
                    "value": "Chattogram, Bangladesh",
                    "confidence": 0.75,
                    "verification": "model_suggested",
                    "source": "ai",
                    "evidence": None,
                },
                "port_of_discharge": {
                    "value": "New York, United States",
                    "confidence": 0.75,
                    "verification": "model_suggested",
                    "source": "ai",
                    "evidence": None,
                },
            },
            "extraction_artifacts_v1": {
                "raw_text": "Bill of Lading\nPort of Loading: Chattogram\nPort of Discharge: New York\n",
            },
        }
    )

    pol_fact = _fact_by_name(payload, "port_of_loading")
    pod_fact = _fact_by_name(payload, "port_of_discharge")

    assert pol_fact["verification_state"] == "confirmed"
    assert pol_fact["origin"] == "artifact_raw_text"
    assert pol_fact["evidence_source"] == "artifact_raw_text"
    assert pol_fact["evidence_snippet"] == "Port of Loading: Chattogram"
    assert pol_fact["normalized_value"] == "Chittagong"
    assert pod_fact["verification_state"] == "confirmed"
    assert pod_fact["origin"] == "artifact_raw_text"
    assert pod_fact["evidence_source"] == "artifact_raw_text"
    assert pod_fact["evidence_snippet"] == "Port of Discharge: New York"


def test_build_bl_fact_set_normalizes_chattogram_alias_to_chittagong() -> None:
    payload = build_bl_fact_set(
        {
            "document_type": "bill_of_lading",
            "transport_subtype": "bill_of_lading",
            "extracted_fields": {
                "port_of_loading": "Chattogram, Bangladesh",
            },
        }
    )

    pol_fact = _fact_by_name(payload, "port_of_loading")

    assert pol_fact["normalized_value"] == "Chittagong, Bangladesh"


def test_build_bl_fact_set_preserves_operator_confirmed_values() -> None:
    payload = build_bl_fact_set(
        {
            "document_type": "bill_of_lading",
            "transport_subtype": "bill_of_lading",
            "extracted_fields": {"bl_number": "BOL-2026-001"},
            "field_details": {
                "bl_number": {
                    "value": "BOL-2026-001",
                    "verification": "operator_confirmed",
                    "source": "operator_override",
                    "confidence": 1.0,
                }
            },
        }
    )

    fact = _fact_by_name(payload, "bl_number")
    assert fact["verification_state"] == "operator_confirmed"
    assert fact["origin"] == "operator_override"
    assert fact["normalized_value"] == "BOL-2026-001"


def test_build_bl_fact_set_supports_courier_receipt_aliases_and_document_type() -> None:
    payload = build_bl_fact_set(
        {
            "document_type": "courier_or_post_receipt_or_certificate_of_posting",
            "transport_subtype": "courier_or_post_receipt_or_certificate_of_posting",
            "extraction_lane": "document_ai",
            "extracted_fields": {
                "receipt_number": "CR-2026-22",
                "consignee_name": "ABC Imports LLC",
            },
            "field_details": {
                "receipt_number": {
                    "value": "CR-2026-22",
                    "verification": "confirmed",
                    "source": "multimodal:pdf_pages",
                }
            },
        }
    )

    consignment_fact = _fact_by_name(payload, "consignment_reference")
    consignee_fact = _fact_by_name(payload, "consignee")

    assert payload["document_type"] == "courier_or_post_receipt_or_certificate_of_posting"
    assert payload["document_subtype"] == "courier_or_post_receipt_or_certificate_of_posting"
    assert consignment_fact["normalized_value"] == "CR-2026-22"
    assert consignee_fact["normalized_value"] == "ABC Imports LLC"
