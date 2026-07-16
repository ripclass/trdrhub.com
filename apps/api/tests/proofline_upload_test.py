from types import SimpleNamespace

import pytest

from app.services.proofline.uploads import (
    ProoflineUploadError,
    choose_case_document_type,
    validate_case_upload,
)


PDF = b"%PDF-1.7\nproofline evidence"


def test_upload_validation_uses_existing_magic_byte_rules_and_size_limit():
    validate_case_upload(PDF, filename="invoice.pdf", content_type="application/pdf", max_bytes=1024)

    with pytest.raises(ProoflineUploadError, match="does not match"):
        validate_case_upload(b"not a pdf", filename="invoice.pdf", content_type="application/pdf", max_bytes=1024)
    with pytest.raises(ProoflineUploadError, match="maximum"):
        validate_case_upload(PDF, filename="invoice.pdf", content_type="application/pdf", max_bytes=8)


def test_reliable_content_classification_can_refine_known_document_type():
    classifier = SimpleNamespace(classify=lambda **_kwargs: SimpleNamespace(
        document_type=SimpleNamespace(value="commercial_invoice"),
        confidence=0.96,
        confidence_level=SimpleNamespace(value="high"),
        is_reliable=True,
        reasoning="Invoice heading and totals detected",
        matched_patterns=["commercial invoice"],
    ))

    document_type, metadata = choose_case_document_type(
        ocr_text="COMMERCIAL INVOICE",
        filename="scan.pdf",
        declared_type=None,
        classifier=classifier,
    )

    assert document_type == "commercial_invoice"
    assert metadata["confidence"] == 0.96
    assert metadata["is_reliable"] is True


def test_proofline_specific_declared_type_is_preserved_when_legacy_classifier_is_generic():
    classifier = SimpleNamespace(classify=lambda **_kwargs: SimpleNamespace(
        document_type=SimpleNamespace(value="supporting_document"),
        confidence=0.35,
        confidence_level=SimpleNamespace(value="low"),
        is_reliable=False,
        reasoning="No legacy LC document pattern",
        matched_patterns=[],
    ))

    document_type, metadata = choose_case_document_type(
        ocr_text="PURCHASE ORDER",
        filename="po-1007.pdf",
        declared_type="purchase_order",
        classifier=classifier,
    )

    assert document_type == "purchase_order"
    assert metadata["suggested_type"] == "supporting_document"
