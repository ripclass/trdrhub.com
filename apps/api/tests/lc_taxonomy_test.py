from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LC_TAXONOMY_PATH = ROOT / "app" / "services" / "extraction" / "lc_taxonomy.py"


def _load_taxonomy_module():
    spec = importlib.util.spec_from_file_location("lc_taxonomy_test", LC_TAXONOMY_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load lc_taxonomy module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_mt760_and_mt798_variants_stay_classified_under_swift_contract() -> None:
    taxonomy = _load_taxonomy_module()

    mt760 = taxonomy.build_lc_classification(
        {
            "schema": "mt760",
            "raw_text": "IRREVOCABLE BANK GUARANTEE issued under URDG758 with GREEN CLAUSE and 60 DAYS usance.",
        },
        {"lc_type": "export"},
    )
    assert mt760["format_variant"] == "mt760"
    assert mt760["format_family"] == "swift_mt_fin"
    assert mt760["instrument_type"] == "demand_guarantee"
    assert mt760["workflow_orientation"] == "export"
    assert mt760["attributes"]["green_clause"] == "present"
    assert mt760["attributes"]["availability"] == "usance"

    mt798 = taxonomy.build_lc_classification(
        {
            "schema": "mt798",
            "raw_text": "MT798 wrapper carrying MT700 documentary credit issuance terms.",
        }
    )
    assert mt798["format_variant"] == "mt798"
    assert mt798["format_family"] == "swift_mt_fin"
    assert mt798["embedded_variant"] == "mt700"
    assert mt798["instrument_type"] == "documentary_credit"


def test_iso_variant_recognition_and_instrument_continuity_for_tsrv_and_tsmt() -> None:
    taxonomy = _load_taxonomy_module()

    undertaking = taxonomy.build_lc_classification({"schema": "tsrv.005"})
    assert undertaking["format_variant"] == "tsrv.005"
    assert undertaking["format_family"] == "iso20022_xml_trade_services"
    assert undertaking["instrument_type"] == "standby_letter_of_credit"

    documentary = taxonomy.build_lc_classification(
        {"schema": "tsmt.015", "raw_text": "Documentary credit amendment under tsmt workflow."}
    )
    assert documentary["format_variant"] == "tsmt.015"
    assert documentary["format_family"] == "iso20022_xml_trade_services"
    assert documentary["instrument_type"] == "documentary_credit"


def test_attribute_normalization_includes_green_clause_and_shipment_permissions() -> None:
    taxonomy = _load_taxonomy_module()

    classification = taxonomy.build_lc_classification(
        {
            "raw_text": (
                "IRREVOCABLE CREDIT AVAILABLE AT SIGHT. GREEN CLAUSE APPLIES. "
                "AUTOMATIC REINSTATEMENT. MAY ADD confirmation."
            ),
            "partial_shipments": "NOT ALLOWED",
            "transshipment": "ALLOWED",
            "available_with": "ANY BANK IN BENEFICIARY COUNTRY",
            "tenor_days": "90 days",
            "shipment": {},
        }
    )
    attributes = classification["attributes"]
    assert attributes["revocability"] == "irrevocable"
    assert attributes["availability"] == "sight"
    assert attributes["available_with_scope"] == "any_bank"
    assert attributes["confirmation"] == "may_add"
    assert attributes["green_clause"] == "present"
    assert attributes["partial_shipments"] == "prohibited"
    assert attributes["transshipment"] == "allowed"
    assert attributes["revolving_mode"] == "automatic"
    assert attributes["tenor_days"] == 90


def test_required_document_normalization_covers_new_canonical_aliases() -> None:
    taxonomy = _load_taxonomy_module()

    classification = taxonomy.build_lc_classification(
        {
            "documents_required": [
                "Full set charter party bill of lading made out to order and blank endorsed.",
                "Courier receipt evidencing dispatch within three days after shipment.",
                "Beneficiary statement certifying one copy sent directly to applicant.",
                "Analysis certificate issued by independent laboratory.",
            ]
        }
    )
    codes = {item["code"] for item in classification["required_documents"]}
    assert "charter_party_bill_of_lading" in codes
    assert "courier_or_post_receipt_or_certificate_of_posting" in codes
    assert "beneficiary_certificate" in codes
    assert "analysis_certificate" in codes


def test_mt700_compact_required_document_shorthand_maps_to_canonical_codes() -> None:
    taxonomy = _load_taxonomy_module()

    classification = taxonomy.build_lc_classification(
        {"documents_required": ["INVOICE/BL/PL/COO/INSURANCE"]}
    )
    codes = {item["code"] for item in classification["required_documents"]}

    assert "commercial_invoice" in codes
    assert "ocean_bill_of_lading" in codes or "bill_of_lading" in codes
    assert "packing_list" in codes
    assert "certificate_of_origin" in codes
    assert "insurance_certificate" in codes
    assert "other_specified_document" not in codes


def test_requirement_contract_separates_document_requirements_from_conditions() -> None:
    taxonomy = _load_taxonomy_module()

    classification = taxonomy.build_lc_classification(
        {
            "documents_required": [
                "BENEFICIARY CERTIFICATE CONFIRMING GOODS ARE BRAND NEW AND MANUFACTURED IN 2026.",
                "NON-NEGOTIABLE DOCUMENTS TO BE SENT TO APPLICANT WITHIN 5 DAYS OF SHIPMENT.",
                "ALL DOCUMENTS MUST SHOW LC NO. EXP2026BD001 AND BUYER PURCHASE ORDER NO. GBE-44592.",
            ]
        }
    )

    required_docs = classification["required_documents"]
    codes = {item["code"] for item in required_docs}
    assert "beneficiary_certificate" in codes
    assert "other_specified_document" not in codes
    assert classification["requirement_conditions"] == [
        "NON-NEGOTIABLE DOCUMENTS TO BE SENT TO APPLICANT WITHIN 5 DAYS OF SHIPMENT.",
        "ALL DOCUMENTS MUST SHOW LC NO. EXP2026BD001 AND BUYER PURCHASE ORDER NO. GBE-44592.",
    ]
    assert classification["unmapped_requirements"] == []


def test_raw_field_46a_and_47a_text_populates_required_docs_conditions_and_exact_wording() -> None:
    taxonomy = _load_taxonomy_module()

    classification = taxonomy.build_lc_classification(
        {
            "raw_text": (
                "IRREVOCABLE DOCUMENTARY CREDIT\n"
                "Field 46A: Documents Required:\n"
                "- Commercial Invoice in triplicate\n"
                "- Full set of clean on board Bills of Lading\n"
                "- Packing List\n"
                "- Certificate of Origin\n"
                "- Beneficiary Certificate stating exactly WE HEREBY CERTIFY GOODS ARE BRAND NEW\n"
                "Field 47A: Additional Conditions:\n"
                "- All documents must show LC number EXP2026BD001\n"
                "- Documents must be presented within 21 days after shipment\n"
            )
        }
    )

    codes = {item["code"] for item in classification["required_documents"]}
    assert "commercial_invoice" in codes
    assert "ocean_bill_of_lading" in codes
    assert "bill_of_lading" not in codes
    assert "packing_list" in codes
    assert "certificate_of_origin" in codes
    assert "beneficiary_certificate" in codes

    beneficiary_certificate = next(
        item for item in classification["required_documents"] if item["code"] == "beneficiary_certificate"
    )
    assert beneficiary_certificate["exact_wording"] == "WE HEREBY CERTIFY GOODS ARE BRAND NEW"
    assert beneficiary_certificate["detection_source"] == "documents_required_raw_text"

    assert classification["requirement_conditions"] == [
        "All documents must show LC number EXP2026BD001",
        "Documents must be presented within 21 days after shipment",
    ]


def test_raw_mt700_blocks_populate_required_docs_conditions_and_exact_wording() -> None:
    taxonomy = _load_taxonomy_module()

    classification = taxonomy.build_lc_classification(
        {
            "raw_text": (
                ":27:1/1\n"
                ":40A:IRREVOCABLE\n"
                ":20:EXP2026BD001\n"
                ":46A:\n"
                "COMMERCIAL INVOICE IN TRIPLICATE\n"
                "FULL SET OF CLEAN ON BOARD BILL OF LADING\n"
                "PACKING LIST\n"
                "CERTIFICATE OF ORIGIN\n"
                "BENEFICIARY CERTIFICATE STATING EXACTLY WE HEREBY CERTIFY GOODS ARE BRAND NEW\n"
                ":47A:\n"
                "ALL DOCUMENTS MUST SHOW LC NUMBER EXP2026BD001\n"
                "DOCUMENTS MUST BE PRESENTED WITHIN 21 DAYS AFTER SHIPMENT\n"
            )
        }
    )

    codes = {item["code"] for item in classification["required_documents"]}
    assert "commercial_invoice" in codes
    assert "ocean_bill_of_lading" in codes
    assert "bill_of_lading" not in codes
    assert "packing_list" in codes
    assert "certificate_of_origin" in codes
    assert "beneficiary_certificate" in codes

    beneficiary_certificate = next(
        item for item in classification["required_documents"] if item["code"] == "beneficiary_certificate"
    )
    assert beneficiary_certificate["exact_wording"] == "WE HEREBY CERTIFY GOODS ARE BRAND NEW"
    assert classification["requirement_conditions"] == [
        "ALL DOCUMENTS MUST SHOW LC NUMBER EXP2026BD001",
        "DOCUMENTS MUST BE PRESENTED WITHIN 21 DAYS AFTER SHIPMENT",
    ]


def test_existing_unknown_workflow_does_not_block_recomputed_export_orientation() -> None:
    taxonomy = _load_taxonomy_module()

    classification = taxonomy.build_lc_classification(
        {
            "schema": "mt700",
            "raw_text": "IRREVOCABLE DOCUMENTARY CREDIT SUBJECT TO UCP 600.",
            "applicant": "GLOBAL IMPORTERS INC.\n1250 HUDSON STREET, NEW YORK, USA",
            "beneficiary": "DHAKA KNITWEAR & EXPORTS LTD.\nPLOT 22, DEPZ, SAVAR, DHAKA, BANGLADESH",
            "port_of_loading": "CHITTAGONG SEA PORT, BANGLADESH",
            "port_of_discharge": "NEW YORK, USA",
            "lc_classification": {"workflow_orientation": "unknown"},
        }
    )

    assert classification["workflow_orientation"] == "export"


def test_existing_non_unknown_workflow_orientation_remains_authoritative() -> None:
    taxonomy = _load_taxonomy_module()

    classification = taxonomy.build_lc_classification(
        {
            "schema": "mt700",
            "raw_text": "IRREVOCABLE DOCUMENTARY CREDIT SUBJECT TO UCP 600.",
            "applicant": "GLOBAL IMPORTERS INC.\n1250 HUDSON STREET, NEW YORK, USA",
            "beneficiary": "DHAKA KNITWEAR & EXPORTS LTD.\nPLOT 22, DEPZ, SAVAR, DHAKA, BANGLADESH",
            "port_of_loading": "CHITTAGONG SEA PORT, BANGLADESH",
            "port_of_discharge": "NEW YORK, USA",
            "lc_classification": {"workflow_orientation": "import"},
        },
        {"lc_type": "export"},
    )

    assert classification["workflow_orientation"] == "import"
