from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

from app.services.facts.insurance_facts import build_insurance_fact_set  # noqa: E402


def _fact_by_name(payload: dict, field_name: str) -> dict:
    facts = payload.get("facts") or []
    for fact in facts:
        if fact.get("field_name") == field_name:
            return fact
    raise AssertionError(f"Missing fact {field_name}")


def test_build_insurance_fact_set_normalizes_amount_currency_and_date() -> None:
    payload = build_insurance_fact_set(
        {
            "document_type": "insurance_certificate",
            "insurance_subtype": "insurance_certificate",
            "extraction_lane": "document_ai",
            "extracted_fields": {
                "policy_number": "POL-2026-001",
                "insured_amount": "USD 125,000.50",
                "currency": "usd",
                "issue_date": "20 Apr 2026",
            },
            "field_details": {
                "insured_amount": {
                    "value": "USD 125,000.50",
                    "confidence": 0.93,
                    "verification": "confirmed",
                    "source": "multimodal:pdf_pages",
                    "evidence": {
                        "snippet": "Sum Insured: USD 125,000.50",
                        "source": "visual+native_text",
                        "page": 1,
                    },
                }
            },
        }
    )

    amount_fact = _fact_by_name(payload, "insured_amount")
    currency_fact = _fact_by_name(payload, "currency")
    date_fact = _fact_by_name(payload, "issue_date")
    assert amount_fact["normalized_value"] == "125000.50"
    assert currency_fact["normalized_value"] == "USD"
    assert date_fact["normalized_value"] == "2026-04-20"


def test_build_insurance_fact_set_maps_candidate_beneficiary_alias_to_issuer() -> None:
    payload = build_insurance_fact_set(
        {
            "document_type": "beneficiary_certificate",
            "insurance_subtype": "beneficiary_certificate",
            "extracted_fields": {"beneficiary": "Shanta Apparels Ltd."},
            "field_details": {
                "beneficiary": {
                    "value": "Shanta Apparels Ltd.",
                    "verification": "model_suggested",
                    "confidence": 0.58,
                }
            },
        }
    )

    fact = _fact_by_name(payload, "issuer_name")
    assert fact["value"] == "Shanta Apparels Ltd."
    assert fact["verification_state"] == "candidate"
    assert fact["source_field_name"] == "beneficiary"


def test_build_insurance_fact_set_marks_absent_coverage_when_source_absent() -> None:
    payload = build_insurance_fact_set(
        {
            "document_type": "insurance_certificate",
            "field_details": {
                "coverage_type": {
                    "verification": "not_found",
                    "reason_code": "source_absent",
                }
            },
        }
    )

    fact = _fact_by_name(payload, "coverage_type")
    assert fact["value"] is None
    assert fact["verification_state"] == "absent_in_source"


def test_build_insurance_fact_set_preserves_operator_confirmed_lc_reference() -> None:
    payload = build_insurance_fact_set(
        {
            "document_type": "beneficiary_certificate",
            "field_details": {
                "lc_reference": {
                    "value": "EXP2026BD001",
                    "verification": "operator_confirmed",
                    "source": "operator_override",
                    "confidence": 1.0,
                }
            },
        }
    )

    fact = _fact_by_name(payload, "lc_reference")
    assert fact["verification_state"] == "operator_confirmed"
    assert fact["origin"] == "operator_override"
    assert fact["normalized_value"] == "EXP2026BD001"


def test_build_insurance_fact_set_recovers_originals_presented_from_raw_text() -> None:
    payload = build_insurance_fact_set(
        {
            "document_type": "insurance_certificate",
            "extraction_artifacts_v1": {
                "raw_text": (
                    "INSURANCE CERTIFICATE\n"
                    "Certificate No: INS-2026-001\n"
                    "Number of Originals: 1\n"
                )
            },
            "field_details": {
                "originals_presented": {
                    "verification": "not_found",
                    "reason_code": "source_absent",
                }
            },
        }
    )

    fact = _fact_by_name(payload, "originals_presented")
    assert fact["value"] == 1
    assert fact["normalized_value"] == 1
    assert fact["verification_state"] == "confirmed"
    assert fact["origin"] == "artifact_raw_text"
