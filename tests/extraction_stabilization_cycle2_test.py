from __future__ import annotations

import copy
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVICES_DIR = ROOT / "apps" / "api" / "app" / "services"

if str(SERVICES_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICES_DIR))

from extraction_core.review_metadata import (  # noqa: E402
    _canonicalize_reason_codes,
    _evaluate_cross_field_reasons,
    _preparse_document_fields,
    annotate_documents_with_review_metadata,
    build_document_extraction,
)


def _field_map(doc):
    return {field.name: field for field in doc.fields}


def _invoice_doc() -> dict[str, object]:
    return {
        "id": "doc-ci-1",
        "document_type": "commercial_invoice",
        "extraction_confidence": 0.96,
        "raw_text": (
            "Seller Acme Exports Limited\n"
            "Invoice Date 14 Feb 2026\n"
            "BIN 1234567890123\n"
            "Gross Weight 100 KG\n"
            "Net Weight 90 KG\n"
        ),
        "extracted_fields": {
            "exporter_bin": "1234567890123",
            "gross_weight": "100 KG",
            "net_weight": "90 KG",
            "invoice_date": "14 Feb 2026",
            "seller_name": "Acme Exports Limited",
        },
        "field_details": {
            "exporter_bin": {"confidence": 0.96, "evidence_snippet": "BIN 1234567890123"},
            "gross_weight": {"confidence": 0.96, "evidence_snippet": "Gross Weight 100 KG"},
            "net_weight": {"confidence": 0.96, "evidence_snippet": "Net Weight 90 KG"},
            "invoice_date": {"confidence": 0.96, "evidence_snippet": "Invoice Date 14 Feb 2026"},
            "seller_name": {"confidence": 0.96, "evidence_snippet": "Seller Acme Exports Limited"},
        },
        "extraction_artifacts_v1": {
            "raw_text": (
                "Seller Acme Exports Limited\n"
                "Invoice Date 14 Feb 2026\n"
                "BIN 1234567890123\n"
                "Gross Weight 100 KG\n"
                "Net Weight 90 KG\n"
            ),
            "reason_codes": [],
            "stage_errors": {},
            "provider_attempts": [],
            "final_text_length": 112,
        },
    }


def _lc_doc() -> dict[str, object]:
    return {
        "id": "doc-lc-1",
        "document_type": "letter_of_credit",
        "extraction_confidence": 0.94,
        "raw_text": (
            ":20:LC-12345/26\n"
            ":31C:260214\n"
            ":32B:USD12345,67\n"
            "Issuing Bank: Global Trade Bank Limited\n"
        ),
        "extracted_fields": {
            "issuing_bank": "Global Trade Bank Limited",
            "issue_date": "260214",
        },
        "field_details": {
            "issuing_bank": {"confidence": 0.94, "evidence_snippet": "Issuing Bank: Global Trade Bank Limited"},
            "issue_date": {"confidence": 0.94, "evidence_snippet": ":31C:260214"},
        },
        "extraction_artifacts_v1": {
            "raw_text": (
                ":20:LC-12345/26\n"
                ":31C:260214\n"
                ":32B:USD12345,67\n"
                "Issuing Bank: Global Trade Bank Limited\n"
            ),
            "reason_codes": [],
            "stage_errors": {},
            "provider_attempts": [],
            "final_text_length": 90,
        },
    }


def test_cycle2_lc_number_positive_extraction():
    parsed = _preparse_document_fields(_lc_doc()["raw_text"], "letter_of_credit")
    assert parsed["lc_number"].state == "found"
    assert parsed["lc_number"].value_normalized == "LC-12345/26"


def test_cycle2_lc_number_negative_extraction():
    parsed = _preparse_document_fields("LC Number: ###\nIssuing Bank: Example Bank\n", "letter_of_credit")
    assert parsed["lc_number"].state == "parse_failed"
    assert "FORMAT_INVALID" in parsed["lc_number"].reason_codes


def test_cycle2_issue_date_normalization_variants():
    parsed_a = _preparse_document_fields("Invoice Date 14/02/2026\n", "commercial_invoice")
    parsed_b = _preparse_document_fields("Date of Issue 14 Feb 2026\n", "letter_of_credit")
    parsed_c = _preparse_document_fields(":31C:260214\n", "letter_of_credit")
    assert parsed_a["issue_date"].value_normalized == "2026-02-14"
    assert parsed_b["issue_date"].value_normalized == "2026-02-14"
    assert parsed_c["issue_date"].value_normalized == "2026-02-14"


def test_cycle2_amount_currency_pair_extraction():
    parsed = _preparse_document_fields(_lc_doc()["raw_text"], "letter_of_credit")
    assert parsed["amount"].state == "found"
    assert parsed["amount"].value_normalized == "12345.67"
    assert parsed["currency"].value_normalized == "USD"


def test_cycle2_bin_tin_normalization_edge_case():
    parsed = _preparse_document_fields("Exporter BIN 12S45O789O123\n", "commercial_invoice")
    assert parsed["bin_tin"].state == "found"
    assert parsed["bin_tin"].value_normalized == "1254507890123"


def test_cycle2_voyage_extraction_edge_cases():
    parsed = _preparse_document_fields("VVD No. 88E\nCarrier Oceanic Line\n", "bill_of_lading")
    assert parsed["voyage"].state == "found"
    assert parsed["voyage"].value_normalized == "88E"


def test_cycle2_gross_net_normalization_and_conflict():
    payload = _invoice_doc()
    payload["raw_text"] = "Gross/Net Weight: 90/100 KGS\nSeller Acme Exports Limited\nInvoice Date 14 Feb 2026\nBIN 1234567890123\n"
    payload["extraction_artifacts_v1"]["raw_text"] = payload["raw_text"]
    payload["extracted_fields"]["gross_weight"] = "90 KG"
    payload["extracted_fields"]["net_weight"] = "100 KG"
    payload["field_details"]["gross_weight"]["evidence_snippet"] = "Gross/Net Weight: 90/100 KGS"
    payload["field_details"]["net_weight"]["evidence_snippet"] = "Gross/Net Weight: 90/100 KGS"
    doc = build_document_extraction(payload)
    assert _field_map(doc)["gross_weight"].value_normalized == "90 KG"
    assert _field_map(doc)["net_weight"].value_normalized == "100 KG"
    reasons = _evaluate_cross_field_reasons(
        fields=doc.fields,
        auxiliary_fields=_preparse_document_fields(payload["raw_text"], "commercial_invoice"),
        cross_checks=["weight_consistency"],
    )
    assert "CROSS_FIELD_CONFLICT" in reasons


def test_cycle2_issuer_anchor_extraction():
    parsed = _preparse_document_fields("Issuing Bank: Global Trade Bank Limited\n", "letter_of_credit")
    assert parsed["issuer"].state == "found"
    assert parsed["issuer"].value_normalized == "GLOBAL TRADE BANK LTD"


def test_cycle2_confidence_threshold_downgrade():
    payload = _invoice_doc()
    payload["extraction_confidence"] = 0.75
    for key in ("exporter_bin", "gross_weight", "net_weight", "invoice_date", "seller_name"):
        payload["field_details"][key]["confidence"] = 0.75
    doc = build_document_extraction(payload)
    assert doc.review_required is True
    assert "LOW_CONFIDENCE_CRITICAL" in doc.review_reasons


def test_cycle2_evidence_required_downgrade():
    payload = _invoice_doc()
    payload["raw_text"] = ""
    payload["extraction_artifacts_v1"]["raw_text"] = ""
    payload["field_details"] = {
        "exporter_bin": {"confidence": 0.96},
        "gross_weight": {"confidence": 0.96},
        "net_weight": {"confidence": 0.96},
        "invoice_date": {"confidence": 0.96},
        "seller_name": {"confidence": 0.96},
    }
    doc = build_document_extraction(payload)
    assert doc.review_required is True
    assert "EVIDENCE_MISSING" in doc.review_reasons


def test_cycle2_reason_code_mapping_for_ocr_timeout():
    payload = _invoice_doc()
    payload["raw_text"] = ""
    payload["extraction_status"] = "empty"
    payload["extraction_artifacts_v1"]["raw_text"] = ""
    payload["extraction_artifacts_v1"]["stage_errors"] = {"ocr_provider_primary": "timed out waiting for provider"}
    doc = build_document_extraction(payload)
    assert "OCR_TIMEOUT" in doc.review_reasons
    assert "OCR_TIMEOUT" in payload["extraction_artifacts_v1"]["canonical_reason_codes"]


def test_cycle2_reason_code_mapping_for_ocr_auth_error():
    payload = _invoice_doc()
    payload["raw_text"] = ""
    payload["extraction_status"] = "empty"
    payload["extraction_artifacts_v1"]["raw_text"] = ""
    payload["extraction_artifacts_v1"]["provider_attempts"] = [{"provider": "ocr_service", "error": "permission denied", "healthy": False}]
    doc = build_document_extraction(payload)
    assert "OCR_AUTH_ERROR" in doc.review_reasons
    assert "OCR_AUTH_ERROR" in payload["extraction_artifacts_v1"]["canonical_reason_codes"]


def test_cycle2_reason_code_mapping_for_parse_failure():
    payload = _invoice_doc()
    payload["extracted_fields"]["invoice_date"] = "31/31/2026"
    payload["raw_text"] = payload["raw_text"].replace("14 Feb 2026", "31/31/2026")
    payload["extraction_artifacts_v1"]["raw_text"] = payload["raw_text"]
    payload["field_details"]["invoice_date"] = {"confidence": 0.96, "evidence_snippet": "Invoice Date 31/31/2026"}
    doc = build_document_extraction(payload)
    issue_date = _field_map(doc)["issue_date"]
    assert issue_date.state == "parse_failed"
    assert "FORMAT_INVALID" in issue_date.reason_codes


def test_cycle2_pass_true_synthetic():
    doc = build_document_extraction(_invoice_doc())
    assert doc.review_required is False
    assert doc.review_reasons == []


def test_cycle2_review_true_synthetic():
    payload = _invoice_doc()
    payload["extracted_fields"]["gross_weight"] = "80 KG"
    payload["extracted_fields"]["net_weight"] = "90 KG"
    payload["field_details"]["gross_weight"]["evidence_snippet"] = "Gross Weight 80 KG"
    payload["field_details"]["net_weight"]["evidence_snippet"] = "Net Weight 90 KG"
    payload["raw_text"] = (
        "Seller Acme Exports Limited\n"
        "Invoice Date 14 Feb 2026\n"
        "BIN 1234567890123\n"
        "Gross Weight 80 KG\n"
        "Net Weight 90 KG\n"
    )
    payload["extraction_artifacts_v1"]["raw_text"] = payload["raw_text"]
    doc = build_document_extraction(payload)
    assert doc.review_required is True
    assert "CROSS_FIELD_CONFLICT" in doc.review_reasons


def test_cycle2_contract_backward_compatibility():
    payload = copy.deepcopy(_invoice_doc())
    payload["custom_key"] = "keep-me"
    documents = [payload]
    bundle = annotate_documents_with_review_metadata(documents)
    assert bundle is not None
    assert documents[0]["custom_key"] == "keep-me"
    assert "review_required" in documents[0]
    assert documents[0]["extraction_artifacts_v1"]["field_diagnostics"]["issuer"]["state"] == "found"


def test_cycle2_unsupported_format_reason_mapping():
    assert _canonicalize_reason_codes(["unsupported mime type"]) == ["OCR_UNSUPPORTED_FORMAT"]
