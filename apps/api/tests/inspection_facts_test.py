from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

from app.services.facts.inspection_facts import build_inspection_fact_set  # noqa: E402


def _fact_by_name(payload: dict, field_name: str) -> dict:
    facts = payload.get("facts") or []
    for fact in facts:
        if fact.get("field_name") == field_name:
            return fact
    raise AssertionError(f"Missing fact {field_name}")


def test_build_inspection_fact_set_confirms_inspection_date_with_evidence() -> None:
    payload = build_inspection_fact_set(
        {
            "document_type": "inspection_certificate",
            "inspection_subtype": "inspection_certificate",
            "extraction_lane": "document_ai",
            "extracted_fields": {"inspection_date": "20 Apr 2026"},
            "field_details": {
                "inspection_date": {
                    "value": "20 Apr 2026",
                    "confidence": 0.92,
                    "verification": "confirmed",
                    "source": "multimodal:pdf_pages",
                    "evidence": {
                        "snippet": "Inspection Date: 20 Apr 2026",
                        "source": "visual+native_text",
                        "page": 1,
                    },
                }
            },
        }
    )

    fact = _fact_by_name(payload, "inspection_date")
    assert fact["normalized_value"] == "2026-04-20"
    assert fact["verification_state"] == "confirmed"
    assert fact["origin"] == "multimodal:pdf_pages"
    assert fact["evidence_source"] == "visual+native_text"


def test_build_inspection_fact_set_maps_candidate_weight_alias() -> None:
    payload = build_inspection_fact_set(
        {
            "document_type": "weight_list",
            "inspection_subtype": "weight_certificate",
            "extracted_fields": {"gross_wt": "20,400 KGS"},
            "field_details": {
                "gross_wt": {
                    "value": "20,400 KGS",
                    "verification": "model_suggested",
                    "confidence": 0.61,
                }
            },
        }
    )

    fact = _fact_by_name(payload, "gross_weight")
    assert fact["value"] == "20,400 KGS"
    assert fact["verification_state"] == "candidate"
    assert fact["source_field_name"] == "gross_wt"


def test_build_inspection_fact_set_marks_absent_analysis_when_source_absent() -> None:
    payload = build_inspection_fact_set(
        {
            "document_type": "analysis_certificate",
            "field_details": {
                "analysis_result": {
                    "verification": "not_found",
                    "reason_code": "source_absent",
                }
            },
        }
    )

    fact = _fact_by_name(payload, "analysis_result")
    assert fact["value"] is None
    assert fact["verification_state"] == "absent_in_source"


def test_build_inspection_fact_set_preserves_operator_confirmed_agency() -> None:
    payload = build_inspection_fact_set(
        {
            "document_type": "sgs_certificate",
            "field_details": {
                "inspection_agency": {
                    "value": "SGS Bangladesh Ltd.",
                    "verification": "operator_confirmed",
                    "source": "operator_override",
                    "confidence": 1.0,
                }
            },
        }
    )

    fact = _fact_by_name(payload, "inspection_agency")
    assert fact["verification_state"] == "operator_confirmed"
    assert fact["origin"] == "operator_override"
    assert fact["normalized_value"] == "SGS Bangladesh Ltd."
