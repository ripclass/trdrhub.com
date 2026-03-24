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
    assert projected["goods_description"] == "100% cotton knit tops"


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
