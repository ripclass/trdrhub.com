from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

from app.services.facts.packing_list_facts import build_packing_list_fact_set  # noqa: E402


def _fact_by_name(payload: dict, field_name: str) -> dict:
    facts = payload.get("facts") or []
    for fact in facts:
        if fact.get("field_name") == field_name:
            return fact
    raise AssertionError(f"Missing fact {field_name}")


def test_build_packing_list_fact_set_confirms_document_date_with_evidence() -> None:
    payload = build_packing_list_fact_set(
        {
            "document_type": "packing_list",
            "extraction_lane": "document_ai",
            "extracted_fields": {"date": "20 Apr 2026"},
            "field_details": {
                "date": {
                    "value": "20 Apr 2026",
                    "confidence": 0.92,
                    "verification": "confirmed",
                    "source": "multimodal:pdf_pages",
                    "evidence": {
                        "snippet": "Packing List Date: 20 Apr 2026",
                        "source": "visual+native_text",
                        "page": 1,
                    },
                }
            },
        }
    )

    fact = _fact_by_name(payload, "document_date")
    assert fact["normalized_value"] == "2026-04-20"
    assert fact["verification_state"] == "confirmed"
    assert fact["origin"] == "multimodal:pdf_pages"
    assert fact["evidence_source"] == "visual+native_text"
    assert fact["page"] == 1


def test_build_packing_list_fact_set_maps_candidate_package_count_alias() -> None:
    payload = build_packing_list_fact_set(
        {
            "document_type": "packing_list",
            "extracted_fields": {"package_count": "1850"},
            "field_details": {
                "package_count": {
                    "value": "1850",
                    "confidence": 0.61,
                    "verification": "model_suggested",
                }
            },
        }
    )

    fact = _fact_by_name(payload, "total_packages")
    assert fact["value"] == "1850"
    assert fact["verification_state"] == "candidate"
    assert fact["source_field_name"] == "package_count"


def test_build_packing_list_fact_set_confirms_raw_text_supported_weights() -> None:
    payload = build_packing_list_fact_set(
        {
            "document_type": "packing_list",
            "extracted_fields": {
                "gross_weight": "2,500 KG",
                "net_weight": "2,200 KG",
            },
            "field_details": {
                "gross_weight": {
                    "value": 2500,
                    "confidence": 0.86,
                    "verification": "model_suggested",
                    "source": "raw_text",
                    "evidence": {
                        "text_span": "Gross Weight: 2,500 KG",
                        "page": 1,
                        "source": "raw_text",
                    },
                },
                "net_weight": {
                    "value": 2200,
                    "confidence": 0.86,
                    "verification": "model_suggested",
                    "source": "raw_text",
                    "evidence": {
                        "text_span": "Net Weight: 2,200 KG",
                        "page": 1,
                        "source": "raw_text",
                    },
                },
            },
        }
    )

    gross_fact = _fact_by_name(payload, "gross_weight")
    net_fact = _fact_by_name(payload, "net_weight")

    assert gross_fact["verification_state"] == "confirmed"
    assert gross_fact["evidence_source"] == "raw_text"
    assert gross_fact["page"] == 1
    assert net_fact["verification_state"] == "confirmed"
    assert net_fact["evidence_source"] == "raw_text"
    assert net_fact["page"] == 1


def test_build_packing_list_fact_set_marks_absent_marks_when_source_absent() -> None:
    payload = build_packing_list_fact_set(
        {
            "document_type": "packing_list",
            "field_details": {
                "marks_and_numbers": {
                    "verification": "not_found",
                    "reason_code": "source_absent",
                }
            },
        }
    )

    fact = _fact_by_name(payload, "marks_and_numbers")
    assert fact["value"] is None
    assert fact["verification_state"] == "absent_in_source"
    assert fact["source_field_name"] == "marks_and_numbers"


def test_build_packing_list_fact_set_normalizes_reference_fields() -> None:
    payload = build_packing_list_fact_set(
        {
            "document_type": "packing_list",
            "extracted_fields": {
                "packing_list_number": " PL-2026-009 ",
                "gross_weight": " 20,400 KGS ",
                "net_weight": " 18,950 KGS ",
            },
        }
    )

    number_fact = _fact_by_name(payload, "packing_list_number")
    gross_fact = _fact_by_name(payload, "gross_weight")
    net_fact = _fact_by_name(payload, "net_weight")
    assert number_fact["normalized_value"] == "PL-2026-009"
    assert gross_fact["normalized_value"] == "20,400 KGS"
    assert net_fact["normalized_value"] == "18,950 KGS"


def test_build_packing_list_fact_set_preserves_operator_confirmed_values() -> None:
    payload = build_packing_list_fact_set(
        {
            "document_type": "packing_list",
            "extracted_fields": {"packing_size_breakdown": "Carton 1-100: S-10 M-20"},
            "field_details": {
                "packing_size_breakdown": {
                    "value": "Carton 1-100: S-10 M-20",
                    "verification": "operator_confirmed",
                    "source": "operator_override",
                    "confidence": 1.0,
                }
            },
        }
    )

    fact = _fact_by_name(payload, "packing_size_breakdown")
    assert fact["verification_state"] == "operator_confirmed"
    assert fact["origin"] == "operator_override"
    assert fact["normalized_value"] == "Carton 1-100: S-10 M-20"
