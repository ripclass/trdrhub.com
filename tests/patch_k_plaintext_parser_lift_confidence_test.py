from __future__ import annotations

import copy
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVICES_DIR = ROOT / "apps" / "api" / "app" / "services"

if str(SERVICES_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICES_DIR))

from extraction_core import review_metadata  # noqa: E402
from extraction_core.review_metadata import (  # noqa: E402
    _preparse_document_fields,
    annotate_documents_with_review_metadata,
    build_document_extraction,
)


def _field_map(doc):
    return {field.name: field for field in doc.fields}


def _plaintext_doc(doc_type: str, raw_text: str, *, doc_id: str = "doc-plain-1") -> dict[str, object]:
    return {
        "id": doc_id,
        "document_type": doc_type,
        "extraction_confidence": 0.0,
        "extracted_fields": {},
        "field_details": {},
        "extraction_artifacts_v1": {
            "raw_text": raw_text,
            "selected_stage": "plaintext_native",
            "final_stage": "plaintext_native",
            "reason_codes": [],
            "stage_errors": {},
            "provider_attempts": [],
            "final_text_length": len(raw_text),
        },
    }


def _plaintext_invoice_doc() -> dict[str, object]:
    raw_text = (
        "COMMERCIAL INVOICE\n"
        "Seller: Acme Exports Limited\n"
        "Invoice Date: 14-Feb-2026\n"
        "Exporter BIN/TIN No:\n"
        "12S45O789O123\n"
        "Gross Weight: 1,250 KGS\n"
        "Net Weight: 1,100 KG\n"
    )
    return _plaintext_doc("commercial_invoice", raw_text, doc_id="doc-plain-invoice")


def test_patch_k_bin_tin_extraction_from_plaintext_anchor():
    parsed = _preparse_document_fields(
        "Seller BIN/TIN No:\n12S45O789O123\n",
        "commercial_invoice",
        "plaintext_native",
    )

    assert parsed["bin_tin"].state == "found"
    assert parsed["bin_tin"].value_normalized == "1254507890123"
    assert parsed["bin_tin"].confidence >= 0.8


def test_patch_k_bin_tin_invalid_format_rejection():
    parsed = _preparse_document_fields(
        "Business Identification No: 1234 567\n",
        "commercial_invoice",
        "plaintext_native",
    )

    assert parsed["bin_tin"].state == "parse_failed"
    assert "FORMAT_INVALID" in parsed["bin_tin"].reason_codes


def test_patch_k_gross_weight_parse_with_comma_unit_variants():
    parsed = _preparse_document_fields(
        "Total Gross Weight:\n1,250.50 KGS\n",
        "packing_list",
        "plaintext_native",
    )

    assert parsed["gross_weight"].state == "found"
    assert parsed["gross_weight"].value_normalized == "1250.5 KG"


def test_patch_k_net_weight_parse_with_unit_normalization():
    parsed = _preparse_document_fields(
        "Net Weight: 2,204.62 LB\n",
        "packing_list",
        "plaintext_native",
    )

    assert parsed["net_weight"].state == "found"
    assert parsed["net_weight"].value_normalized == "1000 KG"


def test_patch_k_gross_net_disambiguation_with_adjacent_labels():
    parsed = _preparse_document_fields(
        "Gross Weight 1,250 KG Net Weight 1,100 KG\n",
        "packing_list",
        "plaintext_native",
    )

    assert parsed["gross_weight"].value_normalized == "1250 KG"
    assert parsed["net_weight"].value_normalized == "1100 KG"


def test_patch_k_voyage_extraction_in_plaintext():
    parsed = _preparse_document_fields(
        "Vessel / Voyage: MAERSK SINGAPORE / V.2026E\n",
        "bill_of_lading",
        "plaintext_native",
    )

    assert parsed["voyage"].state == "found"
    assert parsed["voyage"].value_normalized == "V.2026E"


def test_patch_k_issue_date_extraction_variants():
    parsed_a = _preparse_document_fields("Invoice Date: 14-Feb-2026\n", "commercial_invoice", "plaintext_native")
    parsed_b = _preparse_document_fields("Issued On 15 Feb 2026\n", "letter_of_credit", "plaintext_native")

    assert parsed_a["issue_date"].value_normalized == "2026-02-14"
    assert parsed_b["issue_date"].value_normalized == "2026-02-15"


def test_patch_k_evidence_span_extraction_success():
    doc = build_document_extraction(_plaintext_invoice_doc())
    fields = _field_map(doc)

    assert fields["bin_tin"].evidence and "BIN/TIN" in fields["bin_tin"].evidence[0].text_span
    assert fields["gross_weight"].evidence and "Gross Weight" in fields["gross_weight"].evidence[0].text_span
    assert fields["net_weight"].evidence and "Net Weight" in fields["net_weight"].evidence[0].text_span
    assert fields["issue_date"].evidence and "Invoice Date" in fields["issue_date"].evidence[0].text_span


def test_patch_k_evidence_missing_downgrade(monkeypatch):
    payload = _plaintext_invoice_doc()
    baseline = build_document_extraction(copy.deepcopy(payload))
    baseline_confidence = _field_map(baseline)["bin_tin"].confidence

    monkeypatch.setattr(review_metadata, "_derive_plaintext_evidence_snippet", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(review_metadata, "_build_parser_evidence", lambda *_args, **_kwargs: [])

    doc = build_document_extraction(payload)
    field = _field_map(doc)["bin_tin"]

    assert doc.review_required is True
    assert "EVIDENCE_MISSING" in field.reason_codes
    assert field.confidence < baseline_confidence


def test_patch_k_plaintext_confidence_threshold_downgrade(monkeypatch):
    payload = _plaintext_invoice_doc()
    original_load_profile = review_metadata.load_profile

    def _patched_load_profile(doc_type: str):
        profile = copy.deepcopy(original_load_profile(doc_type))
        profile["pass_gate"]["plaintext_min_confidence"] = 1.01
        return profile

    monkeypatch.setattr(review_metadata, "load_profile", _patched_load_profile)
    doc = build_document_extraction(payload)
    field = _field_map(doc)["bin_tin"]

    assert field.state == "parse_failed"
    assert "LOW_CONFIDENCE_CRITICAL" in field.reason_codes


def test_patch_k_plaintext_strong_invoice_can_pass():
    doc = build_document_extraction(_plaintext_invoice_doc())

    assert doc.review_required is False
    assert doc.review_reasons == []


def test_patch_k_contract_regression_is_additive():
    payload = _plaintext_invoice_doc()
    payload["custom_key"] = "keep-me"
    documents = [payload]

    bundle = annotate_documents_with_review_metadata(documents)

    assert bundle is not None
    assert documents[0]["custom_key"] == "keep-me"
    assert documents[0]["critical_field_states"]["bin_tin"] == "found"
    assert documents[0]["review_required"] is False


def test_patch_k_plaintext_bill_of_lading_review_path_keeps_reason_codes():
    payload = _plaintext_doc(
        "bill_of_lading",
        (
            "BILL OF LADING\n"
            "Carrier: Oceanic Shipping Line\n"
            "Dated: 16 Feb 2026\n"
            "Voyage No: 88E\n"
            "Gross Weight: 900 KG\n"
            "Net Weight: 1000 KG\n"
        ),
        doc_id="doc-plain-bl",
    )

    doc = build_document_extraction(payload)

    assert doc.review_required is True
    assert "CROSS_FIELD_CONFLICT" in doc.review_reasons
