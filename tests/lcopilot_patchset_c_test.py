from __future__ import annotations

import ast
import copy
import importlib.util
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVICES_DIR = ROOT / "apps" / "api" / "app" / "services"

if str(SERVICES_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICES_DIR))

from extraction_core.profiles import list_profiles, load_profile  # noqa: E402
from extraction_core.review_metadata import (  # noqa: E402
    annotate_documents_with_review_metadata,
    build_document_extraction,
)


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _load_response_shaping_builder():
    path = ROOT / "apps" / "api" / "app" / "routers" / "validation" / "response_shaping.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    wanted = {"summarize_document_statuses", "_normalize_doc_status", "build_document_extraction_v1"}
    selected = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in wanted
    ]
    module = ast.Module(
        body=ast.parse("from typing import Any, Dict, List, Optional\n").body + selected,
        type_ignores=[],
    )
    namespace: dict[str, object] = {}
    exec(compile(module, str(path), "exec"), namespace)
    return namespace["build_document_extraction_v1"]


STRUCTURED_LC_BUILDER = _load_module(
    "lcopilot_patchset_c_structured_lc_builder",
    ROOT / "apps" / "api" / "app" / "services" / "extraction" / "structured_lc_builder.py",
)
BUILD_DOCUMENT_EXTRACTION_V1 = _load_response_shaping_builder()


def _commercial_invoice_doc() -> dict[str, object]:
    return {
        "id": "doc-ci-1",
        "document_type": "commercial_invoice",
        "extraction_confidence": 0.96,
        "raw_text": (
            "Seller Acme Exports\n"
            "Invoice Date 2026-01-01\n"
            "BIN 1234567890\n"
            "Gross Weight 100 KG\n"
            "Net Weight 90 KG\n"
        ),
        "extracted_fields": {
            "exporter_bin": "1234567890",
            "gross_weight": "100 KG",
            "net_weight": "90 KG",
            "invoice_date": "2026-01-01",
            "seller_name": "Acme Exports",
        },
        "field_details": {
            "exporter_bin": {"confidence": 0.96, "evidence_snippet": "BIN 1234567890"},
            "gross_weight": {"confidence": 0.96, "evidence_snippet": "Gross Weight 100 KG"},
            "net_weight": {"confidence": 0.96, "evidence_snippet": "Net Weight 90 KG"},
            "invoice_date": {"confidence": 0.96, "evidence_snippet": "Invoice Date 2026-01-01"},
            "seller_name": {"confidence": 0.96, "evidence_snippet": "Seller Acme Exports"},
        },
    }


def _letter_of_credit_doc() -> dict[str, object]:
    return {
        "id": "doc-lc-1",
        "document_type": "letter_of_credit",
        "extraction_confidence": 0.94,
        "raw_text": "Issuing Bank: Global Trade Bank\nDate of Issue 2026-02-14\n",
        "extracted_fields": {
            "issuing_bank": "Global Trade Bank",
            "issue_date": "2026-02-14",
        },
        "field_details": {
            "issuing_bank": {"confidence": 0.94, "evidence_snippet": "Issuing Bank: Global Trade Bank"},
            "issue_date": {"confidence": 0.94, "evidence_snippet": "Date of Issue 2026-02-14"},
        },
    }


def _bill_of_lading_doc() -> dict[str, object]:
    return {
        "id": "doc-bl-1",
        "document_type": "bill_of_lading",
        "extraction_confidence": 0.93,
        "raw_text": (
            "Carrier Oceanic Line\n"
            "Issue Date 2026-02-10\n"
            "Voyage 88E\n"
            "Gross Weight 100 KG\n"
            "Net Weight 90 KG\n"
            "BIN 1234567890\n"
        ),
        "extracted_fields": {
            "carrier": "Oceanic Line",
            "issue_date": "2026-02-10",
            "voyage_number": "88E",
            "gross_weight": "100 KG",
            "net_weight": "90 KG",
            "exporter_bin": "1234567890",
        },
        "field_details": {
            "carrier": {"confidence": 0.93, "evidence_snippet": "Carrier Oceanic Line"},
            "issue_date": {"confidence": 0.93, "evidence_snippet": "Issue Date 2026-02-10"},
            "voyage_number": {"confidence": 0.93, "evidence_snippet": "Voyage 88E"},
            "gross_weight": {"confidence": 0.93, "evidence_snippet": "Gross Weight 100 KG"},
            "net_weight": {"confidence": 0.93, "evidence_snippet": "Net Weight 90 KG"},
            "exporter_bin": {"confidence": 0.93, "evidence_snippet": "BIN 1234567890"},
        },
    }


def _states(doc_extraction) -> dict[str, str]:
    return {field.name: field.state for field in doc_extraction.fields}


def test_profiles_loader_finds_launch_profiles():
    profiles = set(list_profiles())
    assert {
        "letter_of_credit",
        "commercial_invoice",
        "bill_of_lading",
        "packing_list",
        "supporting_document",
    }.issubset(profiles)
    assert load_profile("commercial_invoice").get("critical_fields") == [
        "bin_tin",
        "gross_weight",
        "net_weight",
        "issue_date",
        "issuer",
    ]


def test_found_state_inference_for_complete_launch_profile_doc():
    doc = build_document_extraction(_commercial_invoice_doc())
    assert _states(doc) == {
        "bin_tin": "found",
        "gross_weight": "found",
        "net_weight": "found",
        "issue_date": "found",
        "issuer": "found",
    }
    assert doc.review_required is False
    assert doc.review_reasons == []


def test_missing_critical_field_sets_review_required():
    payload = _commercial_invoice_doc()
    payload["extracted_fields"].pop("seller_name")
    payload["field_details"].pop("seller_name")
    doc = build_document_extraction(payload)
    assert _states(doc)["issuer"] == "missing"
    assert doc.review_required is True
    assert "critical_issuer_missing" in doc.review_reasons


def test_parse_failed_state_comes_from_parse_error_marker():
    payload = _commercial_invoice_doc()
    payload["extracted_fields"].pop("invoice_date")
    payload["field_details"]["invoice_date"] = {
        "parse_error": True,
        "reason": "invalid_date_format",
        "confidence": 0.96,
    }
    doc = build_document_extraction(payload)
    assert _states(doc)["issue_date"] == "parse_failed"
    assert "critical_issue_date_parse_failed" in doc.review_reasons


def test_evidence_gate_requires_review_when_found_field_has_no_evidence():
    payload = _letter_of_credit_doc()
    payload["raw_text"] = ""
    payload["field_details"]["issue_date"] = {"confidence": 0.94, "evidence_snippet": "Date of Issue 2026-02-14"}
    payload["field_details"].pop("issuing_bank")
    doc = build_document_extraction(payload)
    assert _states(doc)["issuer"] == "found"
    assert "critical_issuer_evidence_missing" in doc.review_reasons
    assert doc.review_required is True


def test_raw_text_search_satisfies_evidence_gate_when_details_are_absent():
    payload = _letter_of_credit_doc()
    payload["field_details"] = {}
    payload["extraction_confidence"] = 0.92
    doc = build_document_extraction(payload)
    assert _states(doc) == {"issue_date": "found", "issuer": "found"}
    assert doc.review_required is False


def test_low_confidence_gate_requires_review():
    payload = _letter_of_credit_doc()
    payload["field_details"]["issuing_bank"]["confidence"] = 0.40
    payload["field_details"]["issue_date"]["confidence"] = 0.40
    doc = build_document_extraction(payload)
    assert doc.review_required is True
    assert "critical_issue_date_low_confidence" in doc.review_reasons
    assert "critical_issuer_low_confidence" in doc.review_reasons


def test_bin_tin_alias_resolves_from_exporter_bin():
    doc = build_document_extraction(_commercial_invoice_doc())
    assert _states(doc)["bin_tin"] == "found"


def test_voyage_alias_resolves_from_voyage_number():
    doc = build_document_extraction(_bill_of_lading_doc())
    assert _states(doc)["voyage"] == "found"
    assert doc.review_required is False


def test_supporting_document_profile_has_no_review_gate():
    doc = build_document_extraction(
        {
            "id": "doc-support-1",
            "document_type": "supporting_document",
            "extracted_fields": {},
            "field_details": {},
        }
    )
    assert doc.fields == []
    assert doc.review_required is False
    assert doc.review_reasons == []


def test_annotation_is_additive_and_preserves_existing_keys():
    payload = _commercial_invoice_doc()
    payload["custom_key"] = "keep-me"
    documents = [copy.deepcopy(payload)]
    bundle = annotate_documents_with_review_metadata(documents)
    assert bundle is not None
    assert documents[0]["custom_key"] == "keep-me"
    assert documents[0]["review_required"] is False
    assert documents[0]["reviewReasons"] == []
    assert documents[0]["critical_field_states"]["issuer"] == "found"
    assert bundle["meta"]["documents_evaluated"] == 1


def test_feature_flag_disables_annotations(monkeypatch):
    monkeypatch.setenv("LCCOPILOT_EXTRACTION_CORE_V1_ENABLED", "0")
    documents = [copy.deepcopy(_commercial_invoice_doc())]
    bundle = annotate_documents_with_review_metadata(documents)
    assert bundle is None
    assert "review_required" not in documents[0]


def test_structured_result_builder_preserves_review_metadata():
    result = STRUCTURED_LC_BUILDER.build_unified_structured_result(
        session_documents=[
            {
                "id": "doc-1",
                "name": "invoice.pdf",
                "documentType": "commercial_invoice",
                "extractionStatus": "success",
                "extractedFields": {"invoice_number": "INV-1"},
                "review_required": True,
                "review_reasons": ["critical_issuer_missing"],
                "critical_field_states": {"issuer": "missing"},
            }
        ],
        extractor_outputs={"timeline": []},
    )
    structured = result["structured_result"]
    document = structured["documents"][0]
    assert document["review_required"] is True
    assert document["review_reasons"] == ["critical_issuer_missing"]
    assert document["critical_field_states"] == {"issuer": "missing"}


def test_document_extraction_v1_builder_preserves_review_fields():
    output = BUILD_DOCUMENT_EXTRACTION_V1(
        [
            {
                "id": "doc-1",
                "documentType": "commercial_invoice",
                "name": "invoice.pdf",
                "status": "warning",
                "extractionStatus": "success",
                "review_required": True,
                "review_reasons": ["critical_issuer_missing"],
                "critical_field_states": {"issuer": "missing"},
            }
        ]
    )
    document = output["documents"][0]
    assert document["review_required"] is True
    assert document["review_reasons"] == ["critical_issuer_missing"]
    assert document["critical_field_states"] == {"issuer": "missing"}


def test_validate_source_wires_extraction_core_bundle_into_success_and_blocked_paths():
    source = (ROOT / "apps" / "api" / "app" / "routers" / "validate.py").read_text(encoding="utf-8")
    assert "_annotate_documents_with_review_metadata(document_details)" in source
    assert 'structured_result["_extraction_core_v1"] = extraction_core_bundle' in source
    assert 'result["_extraction_core_v1"] = extraction_core_bundle' in source


def test_shared_type_sources_expose_additive_review_fields():
    ts_source = (ROOT / "packages" / "shared-types" / "src" / "api.ts").read_text(encoding="utf-8")
    py_source = (ROOT / "packages" / "shared-types" / "python" / "schemas.py").read_text(encoding="utf-8")
    assert "review_required" in ts_source
    assert "_extraction_core_v1" in ts_source
    assert "critical_field_states" in py_source
    assert "_extraction_core_v1" in py_source
