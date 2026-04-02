from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

from app.services.facts import (  # noqa: E402
    apply_invoice_fact_graph_to_validation_inputs,
    project_invoice_validation_context,
)


def test_project_invoice_validation_context_uses_only_resolved_invoice_facts() -> None:
    projected = project_invoice_validation_context(
        {
            "invoice_date": "20 Apr 2026",
            "seller": "Stale Seller",
            "lc_reference": "EXP2026BD001",
            "goods_description": "100% cotton knit tops",
        },
        fact_graph={
            "version": "fact_graph_v1",
            "document_type": "commercial_invoice",
            "facts": [
                {
                    "field_name": "invoice_date",
                    "value": "20 Apr 2026",
                    "normalized_value": "2026-04-20",
                    "verification_state": "confirmed",
                },
                {
                    "field_name": "amount",
                    "value": "USD 458,750.00",
                    "normalized_value": "458750.00",
                    "verification_state": "operator_confirmed",
                },
                {
                    "field_name": "currency",
                    "value": "usd",
                    "normalized_value": "USD",
                    "verification_state": "confirmed",
                },
                {
                    "field_name": "seller",
                    "value": "Dhaka Knitwear & Exports Ltd.",
                    "normalized_value": "Dhaka Knitwear & Exports Ltd.",
                    "verification_state": "operator_rejected",
                },
                {
                    "field_name": "goods_description",
                    "value": "Polyester Blend T-Shirts, HS Code 6109.90",
                    "normalized_value": "Polyester Blend T-Shirts, HS Code 6109.90",
                    "verification_state": "confirmed",
                },
            ],
        },
    )

    assert projected["invoice_date"] == "2026-04-20"
    assert projected["date"] == "2026-04-20"
    assert projected["issue_date"] == "2026-04-20"
    assert projected["amount"] == "458750.00"
    assert projected["total_amount"] == "458750.00"
    assert projected["currency"] == "USD"
    assert projected["currency_code"] == "USD"
    assert "seller" not in projected
    assert "seller_name" not in projected
    assert projected["lc_reference"] == "EXP2026BD001"
    assert projected["goods_description"] == "Polyester Blend T-Shirts, HS Code 6109.90"
    assert projected["description"] == "Polyester Blend T-Shirts, HS Code 6109.90"
    assert projected["product_description"] == "Polyester Blend T-Shirts, HS Code 6109.90"


def test_apply_invoice_fact_graph_to_validation_inputs_mutates_payload_and_context() -> None:
    invoice_document = {
        "document_id": "doc-invoice",
        "document_type": "commercial_invoice",
        "filename": "Invoice.pdf",
        "fact_graph_v1": {
            "version": "fact_graph_v1",
            "document_type": "commercial_invoice",
            "facts": [
                {
                    "field_name": "invoice_number",
                    "value": "INV-2026-114",
                    "normalized_value": "INV-2026-114",
                    "verification_state": "confirmed",
                },
                {
                    "field_name": "buyer",
                    "value": "Rejected Buyer",
                    "normalized_value": "Rejected Buyer",
                    "verification_state": "operator_rejected",
                },
            ],
        },
    }
    payload = {
        "invoice": {
            "invoice_number": "STALE-INV",
            "buyer": "Old Buyer",
            "lc_reference": "EXP2026BD001",
        },
        "documents": [invoice_document],
    }
    extracted_context = {
        "invoice": {
            "invoice_number": "STALE-INV",
            "buyer": "Old Buyer",
        },
        "documents": [invoice_document],
    }

    projected = apply_invoice_fact_graph_to_validation_inputs(payload, extracted_context)

    assert projected["invoice_number"] == "INV-2026-114"
    assert projected["invoice_no"] == "INV-2026-114"
    assert "buyer" not in projected
    assert payload["invoice"]["invoice_number"] == "INV-2026-114"
    assert "buyer" not in payload["invoice"]
    assert extracted_context["invoice"]["invoice_number"] == "INV-2026-114"
    assert "buyer" not in extracted_context["invoice"]


def test_apply_invoice_fact_graph_to_validation_inputs_supports_payment_receipt_documents() -> None:
    payment_document = {
        "document_id": "doc-receipt",
        "document_type": "payment_receipt",
        "filename": "Payment_Receipt.pdf",
        "fact_graph_v1": {
            "version": "fact_graph_v1",
            "document_type": "payment_receipt",
            "facts": [
                {
                    "field_name": "receipt_number",
                    "value": "RCPT-26-009",
                    "normalized_value": "RCPT-26-009",
                    "verification_state": "confirmed",
                },
                {
                    "field_name": "amount",
                    "value": "USD 12,500.00",
                    "normalized_value": "12500.00",
                    "verification_state": "confirmed",
                },
            ],
        },
    }
    payload = {"invoice": {"receipt_number": "STALE", "amount": "0"}, "documents": [payment_document]}
    extracted_context = {"invoice": {"receipt_number": "STALE", "amount": "0"}, "documents": [payment_document]}

    projected = apply_invoice_fact_graph_to_validation_inputs(payload, extracted_context)

    assert projected["receipt_number"] == "RCPT-26-009"
    assert projected["amount"] == "12500.00"
    assert payload["invoice"]["receipt_number"] == "RCPT-26-009"
    assert extracted_context["invoice"]["receipt_number"] == "RCPT-26-009"


def test_project_invoice_validation_context_projects_runtime_issuer_and_applicant_aliases() -> None:
    projected = project_invoice_validation_context(
        {},
        fact_graph={
            "version": "fact_graph_v1",
            "document_type": "commercial_invoice",
            "facts": [
                {
                    "field_name": "seller",
                    "value": "Bangladesh Export Ltd",
                    "normalized_value": "Bangladesh Export Ltd",
                    "verification_state": "confirmed",
                },
                {
                    "field_name": "buyer",
                    "value": "Global Trade Corp",
                    "normalized_value": "Global Trade Corp",
                    "verification_state": "confirmed",
                },
            ],
        },
    )

    assert projected["seller"] == "Bangladesh Export Ltd"
    assert projected["seller_name"] == "Bangladesh Export Ltd"
    assert projected["issuer"] == "Bangladesh Export Ltd"
    assert projected["issuer_name"] == "Bangladesh Export Ltd"
    assert projected["buyer"] == "Global Trade Corp"
    assert projected["buyer_name"] == "Global Trade Corp"
    assert projected["applicant"] == "Global Trade Corp"
    assert projected["applicant_name"] == "Global Trade Corp"


def test_project_invoice_validation_context_projects_valuation_aliases_from_amount() -> None:
    projected = project_invoice_validation_context(
        {},
        fact_graph={
            "version": "fact_graph_v1",
            "document_type": "commercial_invoice",
            "facts": [
                {
                    "field_name": "amount",
                    "value": "USD 150,000.00",
                    "normalized_value": "150000.00",
                    "verification_state": "confirmed",
                },
            ],
        },
    )

    assert projected["amount"] == "150000.00"
    assert projected["invoice_amount"] == "150000.00"
    assert projected["total_amount"] == "150000.00"
    assert projected["cif_amount"] == "150000.00"
    assert projected["invoice_value"] == "150000.00"
