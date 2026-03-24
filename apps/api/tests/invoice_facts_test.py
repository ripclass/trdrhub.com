from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

from app.services.facts.invoice_facts import build_invoice_fact_set  # noqa: E402


def _fact_by_name(payload: dict, field_name: str) -> dict:
    facts = payload.get("facts") or []
    for fact in facts:
        if fact.get("field_name") == field_name:
            return fact
    raise AssertionError(f"Missing fact {field_name}")


def test_build_invoice_fact_set_confirms_invoice_date_with_evidence() -> None:
    payload = build_invoice_fact_set(
        {
            "document_type": "commercial_invoice",
            "invoice_subtype": "commercial_invoice",
            "extraction_lane": "document_ai",
            "extracted_fields": {"invoice_date": "20 Apr 2026"},
            "field_details": {
                "invoice_date": {
                    "value": "20 Apr 2026",
                    "confidence": 0.94,
                    "verification": "confirmed",
                    "source": "multimodal:pdf_pages",
                    "evidence": {
                        "snippet": "Invoice Date: 20 Apr 2026",
                        "source": "visual+native_text",
                        "page": 1,
                    },
                }
            },
        }
    )

    fact = _fact_by_name(payload, "invoice_date")
    assert fact["normalized_value"] == "2026-04-20"
    assert fact["verification_state"] == "confirmed"
    assert fact["origin"] == "multimodal:pdf_pages"
    assert fact["evidence_source"] == "visual+native_text"
    assert fact["page"] == 1


def test_build_invoice_fact_set_maps_candidate_seller_alias() -> None:
    payload = build_invoice_fact_set(
        {
            "document_type": "commercial_invoice",
            "invoice_subtype": "commercial_invoice",
            "extraction_lane": "document_ai",
            "extracted_fields": {"seller_name": "Dhaka Knitwear & Exports Ltd."},
            "field_details": {
                "seller_name": {
                    "value": "Dhaka Knitwear & Exports Ltd.",
                    "confidence": 0.62,
                    "verification": "model_suggested",
                }
            },
        }
    )

    fact = _fact_by_name(payload, "seller")
    assert fact["value"] == "Dhaka Knitwear & Exports Ltd."
    assert fact["verification_state"] == "candidate"
    assert fact["source_field_name"] == "seller_name"


def test_build_invoice_fact_set_marks_absent_buyer_when_source_absent() -> None:
    payload = build_invoice_fact_set(
        {
            "document_type": "commercial_invoice",
            "invoice_subtype": "commercial_invoice",
            "field_details": {
                "buyer_name": {
                    "verification": "not_found",
                    "reason_code": "source_absent",
                }
            },
        }
    )

    fact = _fact_by_name(payload, "buyer")
    assert fact["value"] is None
    assert fact["verification_state"] == "absent_in_source"
    assert fact["source_field_name"] == "buyer_name"


def test_build_invoice_fact_set_normalizes_amount_and_currency() -> None:
    payload = build_invoice_fact_set(
        {
            "document_type": "commercial_invoice",
            "invoice_subtype": "commercial_invoice",
            "extracted_fields": {
                "amount": "USD 125,000.50",
                "currency": "usd",
            },
        }
    )

    amount_fact = _fact_by_name(payload, "amount")
    currency_fact = _fact_by_name(payload, "currency")
    assert amount_fact["normalized_value"] == "125000.50"
    assert currency_fact["normalized_value"] == "USD"


def test_build_invoice_fact_set_preserves_operator_confirmed_values() -> None:
    payload = build_invoice_fact_set(
        {
            "document_type": "commercial_invoice",
            "invoice_subtype": "commercial_invoice",
            "extracted_fields": {"invoice_number": "INV-2026-001"},
            "field_details": {
                "invoice_number": {
                    "value": "INV-2026-001",
                    "verification": "operator_confirmed",
                    "source": "operator_override",
                    "confidence": 1.0,
                }
            },
        }
    )

    fact = _fact_by_name(payload, "invoice_number")
    assert fact["verification_state"] == "operator_confirmed"
    assert fact["origin"] == "operator_override"
    assert fact["normalized_value"] == "INV-2026-001"


def test_build_invoice_fact_set_supports_payment_receipt_fields_and_document_type() -> None:
    payload = build_invoice_fact_set(
        {
            "document_type": "payment_receipt",
            "invoice_subtype": "payment_receipt",
            "extraction_lane": "document_ai",
            "extracted_fields": {
                "receipt_number": "RCPT-2026-014",
                "amount": "USD 12,500.00",
                "currency": "usd",
                "lc_reference": "EXP2026BD014",
            },
            "field_details": {
                "receipt_number": {
                    "value": "RCPT-2026-014",
                    "verification": "confirmed",
                    "source": "multimodal:pdf_pages",
                }
            },
        }
    )

    receipt_fact = _fact_by_name(payload, "receipt_number")
    lc_reference_fact = _fact_by_name(payload, "lc_reference")
    amount_fact = _fact_by_name(payload, "amount")

    assert payload["document_type"] == "payment_receipt"
    assert payload["document_subtype"] == "payment_receipt"
    assert receipt_fact["normalized_value"] == "RCPT-2026-014"
    assert lc_reference_fact["normalized_value"] == "EXP2026BD014"
    assert amount_fact["normalized_value"] == "12500.00"
