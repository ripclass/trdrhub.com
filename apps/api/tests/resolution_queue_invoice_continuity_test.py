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
    assert queue["summary"]["total_items"] == 1
    assert queue["summary"]["user_resolvable_items"] == 1
    assert queue["summary"]["unresolved_documents"] == 1
    assert queue["summary"]["document_counts"]["commercial_invoice"] == 1
    assert "packing_list" not in queue["summary"]["document_counts"]
    assert [item["field_name"] for item in queue["items"]] == ["invoice_number"]
    assert queue["items"][0]["reason"] == "system_could_not_confirm"


def test_build_resolution_queue_v1_skips_nonrequired_support_doc_when_lc_graph_present() -> None:
    documents = [
        {
            "document_id": "doc-lc",
            "document_type": "letter_of_credit",
            "filename": "LC.pdf",
            "extraction_lane": "document_ai",
            "requirements_graph_v1": {
                "version": "requirements_graph_v1",
                "required_document_types": ["commercial_invoice", "bill_of_lading"],
                "required_fact_fields": ["lc_number", "amount", "currency"],
            },
            "fact_graph_v1": {
                "version": "fact_graph_v1",
                "document_type": "letter_of_credit",
                "facts": [],
            },
        },
        {
            "document_id": "doc-coo",
            "document_type": "certificate_of_origin",
            "filename": "Certificate_of_Origin.pdf",
            "fact_graph_v1": {
                "version": "fact_graph_v1",
                "document_type": "certificate_of_origin",
                "facts": [
                    {
                        "field_name": "certificate_number",
                        "value": "COO-2026-001",
                        "normalized_value": "COO-2026-001",
                        "verification_state": "candidate",
                        "origin": "document_ai",
                    }
                ],
            },
        },
    ]

    queue = build_resolution_queue_v1(documents)

    assert queue["summary"]["total_items"] == 0
    assert queue["items"] == []


def test_build_resolution_queue_v1_uses_required_fact_fields_for_lc_tasks() -> None:
    documents = [
        {
            "document_id": "doc-lc",
            "document_type": "letter_of_credit",
            "filename": "LC.pdf",
            "extraction_lane": "document_ai",
            "requirements_graph_v1": {
                "version": "requirements_graph_v1",
                "required_document_types": ["commercial_invoice"],
                "required_fact_fields": ["lc_number", "amount", "currency"],
            },
            "fact_graph_v1": {
                "version": "fact_graph_v1",
                "document_type": "letter_of_credit",
                "facts": [
                    {
                        "field_name": "lc_number",
                        "value": "EXP2026BD001",
                        "normalized_value": "EXP2026BD001",
                        "verification_state": "candidate",
                        "origin": "document_ai",
                    },
                    {
                        "field_name": "port_of_loading",
                        "value": "Chittagong",
                        "normalized_value": "Chittagong",
                        "verification_state": "candidate",
                        "origin": "document_ai",
                    },
                ],
            },
        }
    ]

    queue = build_resolution_queue_v1(documents)

    assert queue["summary"]["total_items"] == 1
    assert [item["field_name"] for item in queue["items"]] == ["lc_number"]


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


def test_build_resolution_queue_v1_collects_bl_unresolved_facts() -> None:
    documents = [
        {
            "document_id": "doc-bl",
            "document_type": "bill_of_lading",
            "filename": "Bill_of_Lading.pdf",
            "fact_graph_v1": {
                "version": "fact_graph_v1",
                "document_type": "bill_of_lading",
                "document_subtype": "bill_of_lading",
                "facts": [
                    {
                        "field_name": "bl_number",
                        "value": "BOL-2026-001",
                        "normalized_value": "BOL-2026-001",
                        "verification_state": "candidate",
                        "origin": "document_ai",
                        "evidence_snippet": "Bill of Lading No. BOL-2026-001",
                        "evidence_source": "visual+native_text",
                        "page": 1,
                    },
                    {
                        "field_name": "port_of_loading",
                        "value": None,
                        "normalized_value": None,
                        "verification_state": "unconfirmed",
                        "origin": "document_ai",
                    },
                    {
                        "field_name": "shipper",
                        "value": "Dhaka Knitwear & Exports Ltd.",
                        "normalized_value": "Dhaka Knitwear & Exports Ltd.",
                        "verification_state": "confirmed",
                        "origin": "document_ai",
                    },
                ],
            },
        }
    ]

    queue = build_resolution_queue_v1(documents)

    assert queue["summary"]["total_items"] == 1
    assert queue["summary"]["user_resolvable_items"] == 1
    assert queue["summary"]["unresolved_documents"] == 1
    assert queue["summary"]["document_counts"]["bill_of_lading"] == 1
    assert [item["field_name"] for item in queue["items"]] == ["bl_number"]


def test_build_resolution_queue_v1_collects_packing_list_unresolved_facts() -> None:
    documents = [
        {
            "document_id": "doc-packing",
            "document_type": "packing_list",
            "filename": "Packing_List.pdf",
            "fact_graph_v1": {
                "version": "fact_graph_v1",
                "document_type": "packing_list",
                "facts": [
                    {
                        "field_name": "document_date",
                        "value": "20 Apr 2026",
                        "normalized_value": "2026-04-20",
                        "verification_state": "candidate",
                        "evidence_snippet": "Date: 20 Apr 2026",
                        "evidence_source": "native_text",
                        "page": 1,
                        "origin": "document_ai",
                    },
                    {
                        "field_name": "gross_weight",
                        "value": "20,400 KGS",
                        "normalized_value": "20,400 KGS",
                        "verification_state": "operator_rejected",
                        "evidence_snippet": "G.W. 20,400 KGS",
                        "evidence_source": "native_text",
                        "page": 1,
                        "origin": "document_ai",
                    },
                    {
                        "field_name": "packing_list_number",
                        "value": "PL-026",
                        "normalized_value": "PL-026",
                        "verification_state": "confirmed",
                    },
                ],
            },
        }
    ]

    queue = build_resolution_queue_v1(documents)

    assert queue["summary"]["total_items"] == 2
    assert queue["summary"]["document_counts"] == {"packing_list": 2}
    items = sorted(queue["items"], key=lambda item: item["field_name"])
    assert items[0]["field_name"] == "document_date"
    assert items[0]["priority"] == "high"
    assert items[1]["field_name"] == "gross_weight"
    assert items[1]["reason"] == "operator_rejected_candidate"


def test_build_resolution_queue_v1_collects_coo_unresolved_facts() -> None:
    documents = [
        {
            "document_id": "doc-coo",
            "document_type": "certificate_of_origin",
            "filename": "Certificate_of_Origin.pdf",
            "fact_graph_v1": {
                "version": "fact_graph_v1",
                "document_type": "certificate_of_origin",
                "facts": [
                    {
                        "field_name": "country_of_origin",
                        "value": "Bangladesh",
                        "normalized_value": "Bangladesh",
                        "verification_state": "candidate",
                        "evidence_snippet": "Country of Origin: Bangladesh",
                        "evidence_source": "native_text",
                        "page": 1,
                        "origin": "document_ai",
                    },
                    {
                        "field_name": "goods_description",
                        "value": None,
                        "normalized_value": None,
                        "verification_state": "unconfirmed",
                        "origin": "document_ai",
                    },
                    {
                        "field_name": "certificate_number",
                        "value": "COO-26",
                        "normalized_value": "COO-26",
                        "verification_state": "confirmed",
                    },
                ],
            },
        }
    ]

    queue = build_resolution_queue_v1(documents)

    assert queue["summary"]["total_items"] == 1
    assert queue["summary"]["document_counts"] == {"certificate_of_origin": 1}
    items = queue["items"]
    assert items[0]["field_name"] == "country_of_origin"
    assert items[0]["priority"] == "high"


def test_build_resolution_queue_v1_collects_insurance_unresolved_facts() -> None:
    documents = [
        {
            "document_id": "doc-insurance",
            "document_type": "insurance_certificate",
            "filename": "Insurance_Certificate.pdf",
            "fact_graph_v1": {
                "version": "fact_graph_v1",
                "document_type": "insurance_certificate",
                "facts": [
                    {
                        "field_name": "policy_number",
                        "value": "POL-2026-001",
                        "normalized_value": "POL-2026-001",
                        "verification_state": "candidate",
                        "evidence_snippet": "Policy No: POL-2026-001",
                        "evidence_source": "native_text",
                        "page": 1,
                        "origin": "document_ai",
                    },
                    {
                        "field_name": "issuer_name",
                        "value": None,
                        "normalized_value": None,
                        "verification_state": "unconfirmed",
                        "origin": "document_ai",
                    },
                    {
                        "field_name": "insured_amount",
                        "value": "USD 125,000.50",
                        "normalized_value": "125000.50",
                        "verification_state": "confirmed",
                    },
                ],
            },
        }
    ]

    queue = build_resolution_queue_v1(documents)

    assert queue["summary"]["total_items"] == 1
    assert queue["summary"]["document_counts"] == {"insurance_certificate": 1}
    items = queue["items"]
    assert items[0]["field_name"] == "policy_number"


def test_build_resolution_queue_v1_collects_inspection_unresolved_facts() -> None:
    documents = [
        {
            "document_id": "doc-inspection",
            "document_type": "inspection_certificate",
            "filename": "Inspection_Certificate.pdf",
            "fact_graph_v1": {
                "version": "fact_graph_v1",
                "document_type": "inspection_certificate",
                "facts": [
                    {
                        "field_name": "inspection_result",
                        "value": "PASSED",
                        "normalized_value": "PASSED",
                        "verification_state": "candidate",
                        "evidence_snippet": "Inspection Result: PASSED",
                        "evidence_source": "native_text",
                        "page": 1,
                        "origin": "document_ai",
                    },
                    {
                        "field_name": "inspection_agency",
                        "value": None,
                        "normalized_value": None,
                        "verification_state": "unconfirmed",
                        "origin": "document_ai",
                    },
                    {
                        "field_name": "gross_weight",
                        "value": "20,400 KGS",
                        "normalized_value": "20,400 KGS",
                        "verification_state": "confirmed",
                    },
                ],
            },
        }
    ]

    queue = build_resolution_queue_v1(documents)

    assert queue["summary"]["total_items"] == 1
    assert queue["summary"]["document_counts"] == {"inspection_certificate": 1}
    items = queue["items"]
    assert items[0]["field_name"] == "inspection_result"


def test_build_resolution_queue_v1_collects_regulatory_unresolved_facts() -> None:
    documents = [
        {
            "document_id": "doc-phyto",
            "document_type": "phytosanitary_certificate",
            "filename": "Phytosanitary_Certificate.pdf",
            "fact_graph_v1": {
                "version": "fact_graph_v1",
                "document_type": "phytosanitary_certificate",
                "facts": [
                    {
                        "field_name": "certificate_number",
                        "value": "PHY-2026-01",
                        "normalized_value": "PHY-2026-01",
                        "verification_state": "candidate",
                        "evidence_snippet": "Certificate No: PHY-2026-01",
                        "evidence_source": "native_text",
                        "page": 1,
                        "origin": "document_ai",
                    },
                    {
                        "field_name": "certifying_authority",
                        "value": None,
                        "normalized_value": None,
                        "verification_state": "unconfirmed",
                        "origin": "document_ai",
                    },
                ],
            },
        }
    ]

    queue = build_resolution_queue_v1(documents)

    assert queue["summary"]["total_items"] == 1
    assert queue["summary"]["document_counts"] == {"phytosanitary_certificate": 1}
    items = queue["items"]
    assert items[0]["field_name"] == "certificate_number"


def test_build_resolution_queue_v1_collects_payment_receipt_unresolved_facts() -> None:
    documents = [
        {
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
                        "verification_state": "candidate",
                    },
                    {
                        "field_name": "amount",
                        "value": None,
                        "normalized_value": None,
                        "verification_state": "unconfirmed",
                    },
                ],
            },
        }
    ]

    queue = build_resolution_queue_v1(documents)

    assert queue["summary"]["total_items"] == 1
    assert queue["summary"]["document_counts"] == {"payment_receipt": 1}
    assert [item["field_name"] for item in queue["items"]] == ["receipt_number"]


def test_build_resolution_queue_v1_collects_courier_transport_unresolved_facts() -> None:
    documents = [
        {
            "document_id": "doc-courier",
            "document_type": "courier_or_post_receipt_or_certificate_of_posting",
            "filename": "Courier_Receipt.pdf",
            "fact_graph_v1": {
                "version": "fact_graph_v1",
                "document_type": "courier_or_post_receipt_or_certificate_of_posting",
                "facts": [
                    {
                        "field_name": "consignment_reference",
                        "value": "CR-2026-22",
                        "normalized_value": "CR-2026-22",
                        "verification_state": "candidate",
                    },
                    {
                        "field_name": "consignee",
                        "value": None,
                        "normalized_value": None,
                        "verification_state": "unconfirmed",
                    },
                ],
            },
        }
    ]

    queue = build_resolution_queue_v1(documents)

    assert queue["summary"]["total_items"] == 1
    assert queue["summary"]["document_counts"] == {"courier_or_post_receipt_or_certificate_of_posting": 1}
    assert [item["field_name"] for item in queue["items"]] == ["consignment_reference"]


def test_build_resolution_queue_v1_collects_rendered_lc_unresolved_facts_only() -> None:
    documents = [
        {
            "document_id": "doc-lc",
            "document_type": "letter_of_credit",
            "filename": "LC.pdf",
            "extraction_lane": "document_ai",
            "fact_graph_v1": {
                "version": "fact_graph_v1",
                "document_type": "letter_of_credit",
                "document_subtype": "letter_of_credit",
                "facts": [
                    {
                        "field_name": "lc_number",
                        "value": "EXP2026BD001",
                        "normalized_value": "EXP2026BD001",
                        "verification_state": "candidate",
                        "origin": "document_ai",
                        "evidence_snippet": "20: EXP2026BD001",
                        "evidence_source": "native_text",
                        "page": 1,
                    },
                    {
                        "field_name": "issue_date",
                        "value": None,
                        "normalized_value": None,
                        "verification_state": "unconfirmed",
                        "origin": "document_ai",
                    },
                    {
                        "field_name": "goods_description",
                        "value": "100% Cotton T-Shirts",
                        "normalized_value": "100% Cotton T-Shirts",
                        "verification_state": "candidate",
                        "origin": "document_ai",
                    },
                ],
            },
        }
    ]

    queue = build_resolution_queue_v1(documents)

    assert queue["summary"]["total_items"] == 0
    assert queue["summary"]["document_counts"] == {}
    assert queue["items"] == []


def test_build_resolution_queue_v1_hides_rendered_lc_fields_already_resolved_in_requirements_graph() -> None:
    documents = [
        {
            "document_id": "doc-lc",
            "document_type": "letter_of_credit",
            "filename": "LC.pdf",
            "extraction_lane": "document_ai",
            "requirements_graph_v1": {
                "version": "requirements_graph_v1",
                "required_document_types": ["commercial_invoice"],
                "required_fact_fields": ["applicant", "beneficiary", "issue_date"],
                "core_terms": {
                    "applicant": "Global Trade Corp",
                    "beneficiary": "Bangladesh Export Ltd",
                },
            },
            "fact_graph_v1": {
                "version": "fact_graph_v1",
                "document_type": "letter_of_credit",
                "document_subtype": "letter_of_credit",
                "facts": [
                    {
                        "field_name": "applicant",
                        "value": "Global Trade Corp",
                        "normalized_value": "Global Trade Corp",
                        "verification_state": "candidate",
                        "origin": "multimodal:pdf_pages",
                    },
                    {
                        "field_name": "beneficiary",
                        "value": "Bangladesh Export Ltd",
                        "normalized_value": "Bangladesh Export Ltd",
                        "verification_state": "candidate",
                        "origin": "multimodal:pdf_pages",
                    },
                    {
                        "field_name": "issue_date",
                        "value": "2025-11-26",
                        "normalized_value": "2025-11-26",
                        "verification_state": "candidate",
                        "origin": "multimodal:pdf_pages",
                    },
                ],
            },
        }
    ]

    queue = build_resolution_queue_v1(documents)

    assert queue["summary"]["total_items"] == 1
    assert [item["field_name"] for item in queue["items"]] == ["issue_date"]


def test_build_resolution_queue_v1_hides_unbounded_no_candidate_fields_from_user_queue() -> None:
    documents = [
        {
            "document_id": "doc-bl",
            "document_type": "bill_of_lading",
            "filename": "Bill_of_Lading.pdf",
            "fact_graph_v1": {
                "version": "fact_graph_v1",
                "document_type": "bill_of_lading",
                "facts": [
                    {
                        "field_name": "consignee",
                        "value": None,
                        "normalized_value": None,
                        "verification_state": "unconfirmed",
                        "origin": "document_ai",
                    },
                    {
                        "field_name": "carriage_vessel_name",
                        "value": "MV TEST VESSEL",
                        "normalized_value": "MV TEST VESSEL",
                        "verification_state": "candidate",
                        "origin": "document_ai",
                    },
                ],
            },
        }
    ]

    queue = build_resolution_queue_v1(documents)

    assert queue["summary"]["total_items"] == 0
    assert queue["summary"]["document_counts"] == {}


def test_build_resolution_queue_v1_hides_airport_aliases_for_sea_transport_docs() -> None:
    documents = [
        {
            "document_id": "doc-bl-sea",
            "document_type": "bill_of_lading",
            "transport_subtype": "bill_of_lading",
            "filename": "Bill_of_Lading.pdf",
            "fact_graph_v1": {
                "version": "fact_graph_v1",
                "document_type": "bill_of_lading",
                "document_subtype": "bill_of_lading",
                "facts": [
                    {
                        "field_name": "port_of_loading",
                        "value": "Chittagong Sea Port, Bangladesh",
                        "normalized_value": "Chittagong Sea Port, Bangladesh",
                        "verification_state": "candidate",
                    },
                    {
                        "field_name": "port_of_discharge",
                        "value": "New York, USA",
                        "normalized_value": "New York, USA",
                        "verification_state": "candidate",
                    },
                    {
                        "field_name": "airport_of_departure",
                        "value": "Chittagong Sea Port, Bangladesh",
                        "normalized_value": "Chittagong Sea Port, Bangladesh",
                        "verification_state": "candidate",
                    },
                    {
                        "field_name": "airport_of_destination",
                        "value": "New York, USA",
                        "normalized_value": "New York, USA",
                        "verification_state": "candidate",
                    },
                ],
            },
        }
    ]

    queue = build_resolution_queue_v1(documents)

    assert sorted(item["field_name"] for item in queue["items"]) == [
        "port_of_discharge",
        "port_of_loading",
    ]


def test_build_resolution_queue_v1_hides_sea_port_aliases_for_air_transport_docs() -> None:
    documents = [
        {
            "document_id": "doc-awb",
            "document_type": "air_waybill",
            "transport_subtype": "air_waybill",
            "filename": "Air_Waybill.pdf",
            "fact_graph_v1": {
                "version": "fact_graph_v1",
                "document_type": "air_waybill",
                "document_subtype": "air_waybill",
                "facts": [
                    {
                        "field_name": "airway_bill_number",
                        "value": "AWB-2026-001",
                        "normalized_value": "AWB-2026-001",
                        "verification_state": "candidate",
                    },
                    {
                        "field_name": "airport_of_departure",
                        "value": "DAC",
                        "normalized_value": "DAC",
                        "verification_state": "candidate",
                    },
                    {
                        "field_name": "airport_of_destination",
                        "value": "JFK",
                        "normalized_value": "JFK",
                        "verification_state": "candidate",
                    },
                    {
                        "field_name": "port_of_loading",
                        "value": "DAC",
                        "normalized_value": "DAC",
                        "verification_state": "candidate",
                    },
                    {
                        "field_name": "port_of_discharge",
                        "value": "JFK",
                        "normalized_value": "JFK",
                        "verification_state": "candidate",
                    },
                ],
            },
        }
    ]

    queue = build_resolution_queue_v1(documents)

    assert sorted(item["field_name"] for item in queue["items"]) == [
        "airport_of_departure",
        "airport_of_destination",
        "airway_bill_number",
    ]


def test_build_resolution_queue_v1_skips_structured_lc_without_fact_graph() -> None:
    documents = [
        {
            "document_id": "doc-lc",
            "document_type": "letter_of_credit",
            "filename": "LC.txt",
            "extraction_lane": "structured_mt",
        }
    ]

    queue = build_resolution_queue_v1(documents)

    assert queue["summary"]["total_items"] == 0
    assert queue["summary"]["document_counts"] == {}
