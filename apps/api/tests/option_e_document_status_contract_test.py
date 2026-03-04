from importlib import util
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = API_ROOT / "app" / "services" / "extraction" / "structured_lc_builder.py"
_spec = util.spec_from_file_location("structured_lc_builder_test_module", MODULE_PATH)
_module = util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(_module)
build_unified_structured_result = _module.build_unified_structured_result


def _build_payload(session_documents):
    return build_unified_structured_result(
        session_documents=session_documents,
        extractor_outputs={"lc_type": "export", "issues": []},
    )["structured_result"]


def test_documents_structured_keeps_issue_count_fields_for_mapper():
    structured = _build_payload(
        [
            {
                "id": "d1",
                "name": "LC.pdf",
                "documentType": "letter_of_credit",
                "extractionStatus": "success",
                "discrepancyCount": 2,
            }
        ]
    )

    doc = structured["documents_structured"][0]
    assert doc["extraction_status"] == "success"
    assert doc["issues_count"] == 2
    assert doc["discrepancyCount"] == 2
    assert doc["status"] == "warning"


def test_processing_summary_uses_canonical_extraction_status():
    structured = _build_payload(
        [
            {"id": "d1", "name": "LC.pdf", "documentType": "letter_of_credit", "extractionStatus": "success", "discrepancyCount": 0},
            {"id": "d2", "name": "Invoice.pdf", "documentType": "commercial_invoice", "extractionStatus": "success", "discrepancyCount": 0},
            {"id": "d3", "name": "Packing.pdf", "documentType": "packing_list", "extractionStatus": "success", "discrepancyCount": 1},
            {"id": "d4", "name": "Insurance.pdf", "documentType": "insurance_certificate", "extractionStatus": "partial", "discrepancyCount": 0},
            {"id": "d5", "name": "BL.pdf", "documentType": "bill_of_lading", "extractionStatus": "success", "discrepancyCount": 3},
            {"id": "d6", "name": "COO.pdf", "documentType": "certificate_of_origin", "extractionStatus": "error", "discrepancyCount": 0, "failed_reason": "OCR timeout"},
        ]
    )

    docs = structured["documents_structured"]
    extraction_dist = {"success": 0, "warning": 0, "error": 0}
    for doc in docs:
        ex_status = doc["extraction_status"]
        if ex_status == "success":
            extraction_dist["success"] += 1
        elif ex_status == "failed":
            extraction_dist["error"] += 1
        else:
            extraction_dist["warning"] += 1

    assert extraction_dist == {"success": 4, "warning": 1, "error": 1}

    summary = structured["processing_summary"]
    analytics = structured["analytics"]

    assert structured["validation_contract_version"] == "2026-02-27.p0"
    assert summary["status_counts"] == extraction_dist
    assert summary["document_status"] == extraction_dist
    assert analytics["document_status_distribution"] == extraction_dist
    assert summary["verified"] == extraction_dist["success"]
    assert summary["warnings"] == extraction_dist["warning"]
    assert summary["errors"] == extraction_dist["error"]


def test_failed_without_reason_is_downgraded_and_confident_fields_not_failed():
    structured = _build_payload(
        [
            {
                "id": "d1",
                "name": "Invoice.pdf",
                "documentType": "commercial_invoice",
                "extractionStatus": "failed",
                "extractedFields": {"invoice_number": "INV-1"},
                "extraction_confidence": 0.92,
            },
            {
                "id": "d2",
                "name": "BL.pdf",
                "documentType": "bill_of_lading",
                "extractionStatus": "failed",
                "extractedFields": {},
            },
            {
                "id": "d3",
                "name": "COO.pdf",
                "documentType": "certificate_of_origin",
                "extractionStatus": "failed",
                "failed_reason": "OCR timeout",
                "extractedFields": {},
            },
        ]
    )

    docs = structured["documents_structured"]
    assert docs[0]["extraction_status"] == "success"
    assert docs[1]["extraction_status"] == "partial"  # failed without explicit reason cannot remain hard failed
    assert docs[2]["extraction_status"] == "failed"
    assert docs[2]["failed_reason"] == "OCR timeout"
    assert structured["processing_summary"]["failed_extractions"] == 1


def test_documents_structured_preserves_ocr_confidence_and_provider():
    structured = _build_payload(
        [
            {
                "id": "d1",
                "name": "LC.pdf",
                "documentType": "letter_of_credit",
                "extractionStatus": "partial",
                "discrepancyCount": 0,
                "ocr_confidence": 0.0,
                "ocr_provider": "google_documentai",
                "ocr_source": "ocr",
            }
        ]
    )

    doc = structured["documents_structured"][0]
    assert doc["ocr_confidence"] == 0.0
    assert doc["ocr_provider"] == "google_documentai"
    assert doc["ocr_source"] == "ocr"
