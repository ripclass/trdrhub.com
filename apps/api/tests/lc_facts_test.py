from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

from app.services.facts.lc_facts import build_lc_fact_set  # noqa: E402


def _fact_by_name(payload: dict, field_name: str) -> dict:
    facts = payload.get("facts") or []
    for fact in facts:
        if fact.get("field_name") == field_name:
            return fact
    raise AssertionError(f"Missing fact {field_name}")


def test_build_lc_fact_set_confirms_core_rendered_lc_fields() -> None:
    payload = build_lc_fact_set(
        {
            "document_type": "letter_of_credit",
            "lc_subtype": "letter_of_credit",
            "extraction_lane": "document_ai",
            "extracted_fields": {
                "lc_number": "EXP2026BD001",
                "issue_date": "15 Apr 2026",
                "expiry_date": "15 Oct 2026",
                "latest_shipment_date": "30 Sep 2026",
                "amount": "USD 125,000.50",
                "currency": "usd",
                "applicant": "ABC Imports Ltd.",
                "beneficiary": "Dhaka Knitwear & Exports Ltd.",
            },
            "field_details": {
                "lc_number": {
                    "value": "EXP2026BD001",
                    "confidence": 0.97,
                    "verification": "confirmed",
                    "source": "multimodal:pdf_pages",
                    "evidence": {
                        "snippet": "20: EXP2026BD001",
                        "source": "visual+native_text",
                        "page": 1,
                    },
                },
                "issue_date": {
                    "value": "15 Apr 2026",
                    "verification": "confirmed",
                    "source": "multimodal:pdf_pages",
                },
                "amount": {
                    "value": "USD 125,000.50",
                    "verification": "model_suggested",
                },
            },
        }
    )

    lc_number = _fact_by_name(payload, "lc_number")
    issue_date = _fact_by_name(payload, "issue_date")
    expiry_date = _fact_by_name(payload, "expiry_date")
    latest_shipment_date = _fact_by_name(payload, "latest_shipment_date")
    amount = _fact_by_name(payload, "amount")
    currency = _fact_by_name(payload, "currency")

    assert lc_number["verification_state"] == "confirmed"
    assert lc_number["origin"] == "multimodal:pdf_pages"
    assert lc_number["evidence_source"] == "visual+native_text"
    assert issue_date["normalized_value"] == "2026-04-15"
    assert expiry_date["normalized_value"] == "2026-10-15"
    assert latest_shipment_date["normalized_value"] == "2026-09-30"
    assert amount["normalized_value"] == "125000.50"
    assert amount["verification_state"] == "candidate"
    assert currency["normalized_value"] == "USD"


def test_build_lc_fact_set_uses_shaped_payload_fallbacks() -> None:
    payload = build_lc_fact_set(
        {
            "document_type": "letter_of_credit",
            "lc_subtype": "letter_of_credit",
            "extraction_lane": "document_ai",
            "number": "EXP2026BD014",
            "dates": {
                "issue": "2026-04-15",
                "expiry": "2026-10-15",
                "latest_shipment": "2026-09-30",
            },
            "amount": {"value": "USD 88,500.00", "currency": "USD"},
            "ports": {"loading": "Chittagong", "discharge": "Hamburg"},
            "applicant": {"name": "ABC Imports Ltd."},
            "beneficiary": {"name": "Dhaka Knitwear & Exports Ltd."},
        }
    )

    assert _fact_by_name(payload, "lc_number")["normalized_value"] == "EXP2026BD014"
    assert _fact_by_name(payload, "amount")["normalized_value"] == "88500.00"
    assert _fact_by_name(payload, "port_of_loading")["normalized_value"] == "Chittagong"
    assert _fact_by_name(payload, "beneficiary")["normalized_value"] == "Dhaka Knitwear & Exports Ltd."


def test_build_lc_fact_set_preserves_operator_confirmed_bank() -> None:
    payload = build_lc_fact_set(
        {
            "document_type": "letter_of_credit",
            "lc_subtype": "letter_of_credit",
            "extraction_lane": "document_ai",
            "field_details": {
                "issuing_bank": {
                    "value": "Eastern Bank PLC",
                    "verification": "operator_confirmed",
                    "source": "operator_override",
                    "confidence": 1.0,
                }
            },
        }
    )

    issuing_bank = _fact_by_name(payload, "issuing_bank")
    assert issuing_bank["verification_state"] == "operator_confirmed"
    assert issuing_bank["origin"] == "operator_override"
    assert issuing_bank["normalized_value"] == "Eastern Bank PLC"


def test_build_lc_fact_set_recovers_core_fields_from_artifact_raw_text() -> None:
    payload = build_lc_fact_set(
        {
            "document_type": "letter_of_credit",
            "lc_subtype": "letter_of_credit",
            "extraction_lane": "document_ai",
            "extracted_fields": {
                "issue_date": "2025-11-26",
                "issuer": "Some OCR Side Output",
            },
            "extraction_artifacts_v1": {
                "raw_text": (
                    "IRREVOCABLE DOCUMENTARY CREDIT\n"
                    "MT700 FORMAT\n\n"
                    "Field 20: Documentary Credit Number: EXP2026BD001\n"
                    "Field 31C: Date of Issue: 2025-11-26\n"
                    "Field 31D: Date and Place of Expiry: 2026-03-31 New York, USA\n"
                    "Field 50: Applicant: Global Trade Corp\n"
                    "         123 Commerce Street, New York, NY 10001, USA\n"
                    "Field 59: Beneficiary: Bangladesh Export Ltd\n"
                    "          45 Export Zone, Chittagong, Bangladesh\n"
                    "Field 32B: Currency Code, Amount: USD 458,750.00\n"
                    "Field 44C: Latest Date of Shipment: 2026-03-15\n"
                    "Field 44E: Port of Loading: Chittagong, Bangladesh\n"
                    "Field 44F: Port of Discharge: New York, USA\n"
                    "Field 40E: Applicable Rules: UCP LATEST VERSION\n"
                )
            },
        }
    )

    assert _fact_by_name(payload, "lc_number")["normalized_value"] == "EXP2026BD001"
    assert _fact_by_name(payload, "lc_number")["verification_state"] == "confirmed"
    assert _fact_by_name(payload, "lc_number")["origin"] == "artifact_raw_text"
    assert _fact_by_name(payload, "expiry_date")["normalized_value"] == "2026-03-31"
    assert _fact_by_name(payload, "latest_shipment_date")["normalized_value"] == "2026-03-15"
    assert _fact_by_name(payload, "applicant")["normalized_value"] == "Global Trade Corp"
    assert _fact_by_name(payload, "beneficiary")["normalized_value"] == "Bangladesh Export Ltd"
    assert _fact_by_name(payload, "amount")["normalized_value"] == "458750.00"
    assert _fact_by_name(payload, "currency")["normalized_value"] == "USD"
    assert _fact_by_name(payload, "port_of_loading")["normalized_value"] == "Chittagong, Bangladesh"
    assert _fact_by_name(payload, "port_of_discharge")["normalized_value"] == "New York, USA"
    assert _fact_by_name(payload, "ucp_reference")["normalized_value"] == "UCP LATEST VERSION"
