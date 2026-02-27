from pathlib import Path
import sys

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.services.extraction.structured_lc_builder import build_unified_structured_result


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


def test_processing_summary_and_documents_share_identical_status_source():
    structured = _build_payload(
        [
            {"id": "d1", "name": "LC.pdf", "documentType": "letter_of_credit", "extractionStatus": "success", "discrepancyCount": 0},
            {"id": "d2", "name": "Invoice.pdf", "documentType": "commercial_invoice", "extractionStatus": "success", "discrepancyCount": 0},
            {"id": "d3", "name": "Packing.pdf", "documentType": "packing_list", "extractionStatus": "success", "discrepancyCount": 1},
            {"id": "d4", "name": "Insurance.pdf", "documentType": "insurance_certificate", "extractionStatus": "partial", "discrepancyCount": 0},
            {"id": "d5", "name": "BL.pdf", "documentType": "bill_of_lading", "extractionStatus": "success", "discrepancyCount": 3},
            {"id": "d6", "name": "COO.pdf", "documentType": "certificate_of_origin", "extractionStatus": "error", "discrepancyCount": 0},
        ]
    )

    docs = structured["documents_structured"]
    dist_from_docs = {"success": 0, "warning": 0, "error": 0}
    for doc in docs:
        dist_from_docs[doc["status"]] += 1

    assert dist_from_docs == {"success": 2, "warning": 2, "error": 2}

    summary = structured["processing_summary"]
    analytics = structured["analytics"]

    assert structured["validation_contract_version"] == "2026-02-27.p0"
    assert summary["status_counts"] == dist_from_docs
    assert summary["document_status"] == dist_from_docs
    assert analytics["document_status_distribution"] == dist_from_docs
    assert summary["verified"] == dist_from_docs["success"]
    assert summary["warnings"] == dist_from_docs["warning"]
    assert summary["errors"] == dist_from_docs["error"]
