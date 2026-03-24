from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

from app.services.facts.coo_facts import build_coo_fact_set  # noqa: E402


def _fact_by_name(payload: dict, field_name: str) -> dict:
    facts = payload.get("facts") or []
    for fact in facts:
        if fact.get("field_name") == field_name:
            return fact
    raise AssertionError(f"Missing fact {field_name}")


def test_build_coo_fact_set_confirms_issue_date_with_evidence() -> None:
    payload = build_coo_fact_set(
        {
            "document_type": "certificate_of_origin",
            "regulatory_subtype": "certificate_of_origin",
            "extraction_lane": "document_ai",
            "extracted_fields": {"issue_date": "20 Apr 2026"},
            "field_details": {
                "issue_date": {
                    "value": "20 Apr 2026",
                    "confidence": 0.93,
                    "verification": "confirmed",
                    "source": "multimodal:pdf_pages",
                    "evidence": {
                        "snippet": "Date of Issue: 20 Apr 2026",
                        "source": "visual+native_text",
                        "page": 1,
                    },
                }
            },
        }
    )

    fact = _fact_by_name(payload, "issue_date")
    assert fact["normalized_value"] == "2026-04-20"
    assert fact["verification_state"] == "confirmed"
    assert fact["origin"] == "multimodal:pdf_pages"
    assert fact["evidence_source"] == "visual+native_text"
    assert fact["page"] == 1


def test_build_coo_fact_set_maps_candidate_exporter_alias() -> None:
    payload = build_coo_fact_set(
        {
            "document_type": "certificate_of_origin",
            "extracted_fields": {"exporter": "Dhaka Knitwear & Exports Ltd."},
            "field_details": {
                "exporter": {
                    "value": "Dhaka Knitwear & Exports Ltd.",
                    "confidence": 0.64,
                    "verification": "model_suggested",
                }
            },
        }
    )

    fact = _fact_by_name(payload, "exporter_name")
    assert fact["value"] == "Dhaka Knitwear & Exports Ltd."
    assert fact["verification_state"] == "candidate"
    assert fact["source_field_name"] == "exporter"


def test_build_coo_fact_set_marks_absent_goods_description_when_source_absent() -> None:
    payload = build_coo_fact_set(
        {
            "document_type": "certificate_of_origin",
            "field_details": {
                "goods_description": {
                    "verification": "not_found",
                    "reason_code": "source_absent",
                }
            },
        }
    )

    fact = _fact_by_name(payload, "goods_description")
    assert fact["value"] is None
    assert fact["verification_state"] == "absent_in_source"
    assert fact["source_field_name"] == "goods_description"


def test_build_coo_fact_set_normalizes_core_reference_fields() -> None:
    payload = build_coo_fact_set(
        {
            "document_type": "certificate_of_origin",
            "extracted_fields": {
                "certificate_number": " COO-2026-09 ",
                "country_of_origin": " Bangladesh ",
                "certifying_authority": " Dhaka Chamber of Commerce & Industry ",
            },
        }
    )

    certificate_fact = _fact_by_name(payload, "certificate_number")
    country_fact = _fact_by_name(payload, "country_of_origin")
    authority_fact = _fact_by_name(payload, "certifying_authority")
    assert certificate_fact["normalized_value"] == "COO-2026-09"
    assert country_fact["normalized_value"] == "Bangladesh"
    assert authority_fact["normalized_value"] == "Dhaka Chamber of Commerce & Industry"


def test_build_coo_fact_set_preserves_operator_confirmed_values() -> None:
    payload = build_coo_fact_set(
        {
            "document_type": "certificate_of_origin",
            "extracted_fields": {"country_of_origin": "Bangladesh"},
            "field_details": {
                "country_of_origin": {
                    "value": "Bangladesh",
                    "verification": "operator_confirmed",
                    "source": "operator_override",
                    "confidence": 1.0,
                }
            },
        }
    )

    fact = _fact_by_name(payload, "country_of_origin")
    assert fact["verification_state"] == "operator_confirmed"
    assert fact["origin"] == "operator_override"
    assert fact["normalized_value"] == "Bangladesh"


def test_build_coo_fact_set_supports_regulatory_subtypes_and_license_fields() -> None:
    payload = build_coo_fact_set(
        {
            "document_type": "export_license",
            "regulatory_subtype": "export_license",
            "extracted_fields": {
                "license_number": "EXP-LIC-009",
                "issuing_authority": "Chief Controller of Imports and Exports",
            },
            "field_details": {
                "issuing_authority": {
                    "value": "Chief Controller of Imports and Exports",
                    "verification": "confirmed",
                    "source": "multimodal:pdf_pages",
                }
            },
        }
    )

    authority_fact = _fact_by_name(payload, "certifying_authority")
    license_fact = _fact_by_name(payload, "license_number")
    assert payload["document_type"] == "export_license"
    assert authority_fact["normalized_value"] == "Chief Controller of Imports and Exports"
    assert license_fact["normalized_value"] == "EXP-LIC-009"
