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
