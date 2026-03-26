from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

from app.services.requirements import build_lc_requirements_graph_v1  # noqa: E402


def test_build_lc_requirements_graph_v1_compiles_required_docs_and_core_terms() -> None:
    graph = build_lc_requirements_graph_v1(
        {
            "document_id": "doc-lc",
            "document_type": "letter_of_credit",
            "extraction_lane": "document_ai",
            "lc_classification": {
                "workflow_orientation": "export",
                "applicable_rules": "UCP LATEST VERSION",
                "required_documents": [
                    {"code": "commercial_invoice", "display_name": "Commercial Invoice"},
                    {
                        "code": "bill_of_lading",
                        "display_name": "Bill Of Lading",
                        "originals": 3,
                        "copies": 3,
                        "exact_wording": "FULL SET CLEAN ON BOARD OCEAN BILLS OF LADING",
                    },
                ],
                "requirement_conditions": [
                    "Invoice must mention LC number",
                    "BUYER PURCHASE ORDER NO. GBE-44592 MUST APPEAR ON ALL DOCUMENTS",
                    "Bill of lading must show voyage number and gross weight.",
                ],
                "unmapped_requirements": ["Third-party docs clause needs interpretation"],
            },
            "fact_graph_v1": {
                "version": "fact_graph_v1",
                "document_type": "letter_of_credit",
                "facts": [
                    {
                        "field_name": "lc_number",
                        "value": "EXP2026BD001",
                        "normalized_value": "EXP2026BD001",
                    },
                    {
                        "field_name": "amount",
                        "value": "455750",
                        "normalized_value": "455750",
                    },
                    {
                        "field_name": "currency",
                        "value": "USD",
                        "normalized_value": "USD",
                    },
                    {
                        "field_name": "port_of_loading",
                        "value": "Chittagong",
                        "normalized_value": "Chittagong",
                    },
                ],
            },
        }
    )

    assert graph is not None
    assert graph["version"] == "requirements_graph_v1"
    assert graph["required_document_types"] == ["commercial_invoice", "bill_of_lading"]
    assert graph["core_terms"]["lc_number"] == "EXP2026BD001"
    assert "port_of_loading" in graph["required_fact_fields"]
    assert graph["documentary_conditions"] == [
        "Invoice must mention LC number",
        "BUYER PURCHASE ORDER NO. GBE-44592 MUST APPEAR ON ALL DOCUMENTS",
        "Bill of lading must show voyage number and gross weight.",
    ]
    assert graph["ambiguous_conditions"] == ["Third-party docs clause needs interpretation"]
    assert graph["condition_requirements"] == [
        {
            "requirement_type": "identifier_presence",
            "identifier_type": "po_number",
            "value": "GBE-44592",
            "applies_to": "all_documents",
            "source_text": "BUYER PURCHASE ORDER NO. GBE-44592 MUST APPEAR ON ALL DOCUMENTS",
            "source_bucket": "documentary_conditions",
        },
        {
            "requirement_type": "document_field_presence",
            "document_type": "bill_of_lading",
            "field_name": "voyage_number",
            "applies_to": "bill_of_lading",
            "source_text": "Bill of lading must show voyage number and gross weight.",
            "source_bucket": "documentary_conditions",
        },
        {
            "requirement_type": "document_field_presence",
            "document_type": "bill_of_lading",
            "field_name": "gross_weight",
            "applies_to": "bill_of_lading",
            "source_text": "Bill of lading must show voyage number and gross weight.",
            "source_bucket": "documentary_conditions",
        },
        {
            "requirement_type": "document_quantity",
            "document_type": "bill_of_lading",
            "originals_required": 3,
            "copies_required": 3,
            "applies_to": "bill_of_lading",
            "source_text": "Bill Of Lading",
            "source_bucket": "required_documents",
        },
        {
            "requirement_type": "document_exact_wording",
            "document_type": "bill_of_lading",
            "exact_wording": "FULL SET CLEAN ON BOARD OCEAN BILLS OF LADING",
            "applies_to": "bill_of_lading",
            "source_text": "Bill Of Lading",
            "source_bucket": "required_documents",
        },
    ]


def test_build_lc_requirements_graph_v1_falls_back_to_raw_46a_and_47a_text() -> None:
    graph = build_lc_requirements_graph_v1(
        {
            "document_id": "doc-lc-raw",
            "document_type": "letter_of_credit",
            "extraction_lane": "document_ai",
            "raw_text": (
                ":27:1/1\n"
                ":40A:IRREVOCABLE\n"
                ":20:EXP2026BD001\n"
                ":31C:251126\n"
                ":46A:\n"
                "COMMERCIAL INVOICE IN TRIPLICATE\n"
                "FULL SET OF CLEAN ON BOARD BILL OF LADING\n"
                "PACKING LIST\n"
                "CERTIFICATE OF ORIGIN\n"
                "BENEFICIARY CERTIFICATE STATING EXACTLY WE HEREBY CERTIFY GOODS ARE BRAND NEW\n"
                ":47A:\n"
                "ALL DOCUMENTS MUST SHOW LC NUMBER EXP2026BD001\n"
                "DOCUMENTS MUST BE PRESENTED WITHIN 21 DAYS AFTER SHIPMENT\n"
            ),
            "fact_graph_v1": {
                "version": "fact_graph_v1",
                "document_type": "letter_of_credit",
                "facts": [
                    {
                        "field_name": "lc_number",
                        "value": "EXP2026BD001",
                        "normalized_value": "EXP2026BD001",
                    },
                    {
                        "field_name": "issue_date",
                        "value": "2025-11-26",
                        "normalized_value": "2025-11-26",
                    },
                    {
                        "field_name": "applicant",
                        "value": "Global Trade Corp",
                        "normalized_value": "Global Trade Corp",
                    },
                    {
                        "field_name": "beneficiary",
                        "value": "Bangladesh Export Ltd",
                        "normalized_value": "Bangladesh Export Ltd",
                    },
                    {
                        "field_name": "amount",
                        "value": "125000.00",
                        "normalized_value": "125000.00",
                    },
                    {
                        "field_name": "currency",
                        "value": "USD",
                        "normalized_value": "USD",
                    },
                ],
            },
        }
    )

    assert graph is not None
    assert graph["required_document_types"] == [
        "commercial_invoice",
        "ocean_bill_of_lading",
        "packing_list",
        "certificate_of_origin",
        "beneficiary_certificate",
    ]
    assert graph["documentary_conditions"] == [
        "ALL DOCUMENTS MUST SHOW LC NUMBER EXP2026BD001",
        "DOCUMENTS MUST BE PRESENTED WITHIN 21 DAYS AFTER SHIPMENT",
    ]
    assert {
        "requirement_type": "identifier_presence",
        "identifier_type": "lc_number",
        "value": "EXP2026BD001",
        "applies_to": "all_documents",
        "source_text": "ALL DOCUMENTS MUST SHOW LC NUMBER EXP2026BD001",
        "source_bucket": "documentary_conditions",
    } in graph["condition_requirements"]
    assert {
        "requirement_type": "document_exact_wording",
        "document_type": "beneficiary_certificate",
        "exact_wording": "WE HEREBY CERTIFY GOODS ARE BRAND NEW",
        "applies_to": "beneficiary_certificate",
        "source_text": "BENEFICIARY CERTIFICATE STATING EXACTLY WE HEREBY CERTIFY GOODS ARE BRAND NEW",
        "source_bucket": "required_documents",
    } in graph["condition_requirements"]
