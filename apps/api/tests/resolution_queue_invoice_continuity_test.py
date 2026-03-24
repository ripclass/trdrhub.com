from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

from app.services.facts import materialize_document_fact_graphs_v1  # noqa: E402
from app.services.resolution import build_resolution_queue_v1  # noqa: E402


def test_materialize_document_fact_graphs_v1_rebuilds_invoice_fact_graph() -> None:
    documents = [
        {
            "document_id": "doc-invoice",
            "document_type": "commercial_invoice",
            "filename": "Invoice.pdf",
            "extracted_fields": {"invoice_date": "20 Apr 2026"},
            "field_details": {
                "invoice_date": {
                    "value": "20 Apr 2026",
                    "verification": "confirmed",
                    "source": "multimodal:pdf_pages",
                    "confidence": 0.94,
                }
            },
        }
    ]

    materialize_document_fact_graphs_v1(documents)

    fact_graph = documents[0]["fact_graph_v1"]
    invoice_date = next(fact for fact in fact_graph["facts"] if fact["field_name"] == "invoice_date")
    assert invoice_date["normalized_value"] == "2026-04-20"
    assert documents[0]["factGraphV1"]["version"] == "fact_graph_v1"


def test_build_resolution_queue_v1_collects_only_unresolved_invoice_facts() -> None:
    documents = [
        {
            "document_id": "doc-invoice",
            "document_type": "commercial_invoice",
            "filename": "Invoice.pdf",
            "fact_graph_v1": {
                "version": "fact_graph_v1",
                "document_type": "commercial_invoice",
                "document_subtype": "commercial_invoice",
                "facts": [
                    {
                        "field_name": "invoice_number",
                        "value": "INV-2026-001",
                        "normalized_value": "INV-2026-001",
                        "verification_state": "candidate",
                        "origin": "document_ai",
                        "evidence_snippet": "Invoice No: INV-2026-001",
                        "evidence_source": "visual+native_text",
                        "page": 1,
                    },
                    {
                        "field_name": "invoice_date",
                        "value": None,
                        "normalized_value": None,
                        "verification_state": "unconfirmed",
                        "origin": "document_ai",
                    },
                    {
                        "field_name": "amount",
                        "value": "125000.50",
                        "normalized_value": "125000.50",
                        "verification_state": "confirmed",
                        "origin": "document_ai",
                    },
                ],
            },
        },
        {
            "document_id": "doc-packing",
            "document_type": "packing_list",
            "filename": "Packing.pdf",
            "fact_graph_v1": {
                "version": "fact_graph_v1",
                "document_type": "packing_list",
                "facts": [
                    {
                        "field_name": "packing_list_number",
                        "verification_state": "candidate",
                    }
                ],
            },
        },
    ]

    queue = build_resolution_queue_v1(documents)

    assert queue["version"] == "resolution_queue_v1"
    assert queue["summary"]["total_items"] == 2
    assert queue["summary"]["user_resolvable_items"] == 2
    assert queue["summary"]["unresolved_documents"] == 1
    assert queue["summary"]["document_counts"]["commercial_invoice"] == 2
    assert [item["field_name"] for item in queue["items"]] == ["invoice_number", "invoice_date"]
    assert queue["items"][0]["reason"] == "system_could_not_confirm"


def test_build_resolution_queue_v1_keeps_rejected_candidate_visible() -> None:
    documents = [
        {
            "document_id": "doc-invoice",
            "document_type": "commercial_invoice",
            "filename": "Invoice.pdf",
            "extracted_fields": {},
            "field_details": {
                "invoice_date": {
                    "verification": "operator_rejected",
                    "rejected_value": "2026-04-20",
                    "source": "operator_override",
                }
            },
        }
    ]

    materialize_document_fact_graphs_v1(documents)
    queue = build_resolution_queue_v1(documents)

    invoice_date_item = next(item for item in queue["items"] if item["field_name"] == "invoice_date")
    assert queue["summary"]["total_items"] >= 1
    assert invoice_date_item["candidate_value"] == "2026-04-20"
    assert invoice_date_item["reason"] == "operator_rejected_candidate"
