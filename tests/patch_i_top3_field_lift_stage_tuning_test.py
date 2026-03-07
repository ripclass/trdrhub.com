from __future__ import annotations

import ast
import copy
import sys
import types
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
SERVICES_DIR = ROOT / "apps" / "api" / "app" / "services"

if str(SERVICES_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICES_DIR))

from extraction_core.profiles import load_profile  # noqa: E402
from extraction_core.review_metadata import (  # noqa: E402
    _preparse_document_fields,
    annotate_documents_with_review_metadata,
    build_document_extraction,
)


class _DummyLogger:
    def log(self, *args, **kwargs):
        return None

    def info(self, *args, **kwargs):
        return None

    def warning(self, *args, **kwargs):
        return None

    def error(self, *args, **kwargs):
        return None

    def debug(self, *args, **kwargs):
        return None


def _load_validate_namespace() -> dict[str, object]:
    path = ROOT / "apps" / "api" / "app" / "routers" / "validate.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    wanted_funcs = {
        "_empty_extraction_artifacts_v1",
        "_stage_promotion_v1_enabled",
        "_stage_threshold_tuning_v1_enabled",
        "_score_stage_candidate",
        "_select_best_extraction_stage",
    }
    wanted_assigns = {
        "_STAGE_FIELD_PATTERNS",
        "_STAGE_CRITICAL_FIELD_TO_ANCHOR_FIELD",
    }
    selected = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in wanted_funcs:
            selected.append(node)
        elif isinstance(node, ast.Assign):
            target_names = {target.id for target in node.targets if isinstance(target, ast.Name)}
            if target_names & wanted_assigns:
                selected.append(node)

    module = ast.Module(
        body=ast.parse(
            "import os\n"
            "import re\n"
            "from typing import Any, Dict, List, Optional, Tuple\n"
        ).body
        + selected,
        type_ignores=[],
    )
    namespace: dict[str, object] = {
        "logger": _DummyLogger(),
        "settings": SimpleNamespace(
            OCR_STAGE_SCORER_ENABLED=True,
            OCR_STAGE_WEIGHT_TEXT_LEN=0.30,
            OCR_STAGE_WEIGHT_ALNUM_RATIO=0.20,
            OCR_STAGE_WEIGHT_ANCHOR_HIT=0.25,
            OCR_STAGE_WEIGHT_FIELD_PATTERN=0.25,
            OCR_STAGE_SELECTION_PRIORITY=[
                "ocr_provider_primary",
                "ocr_secondary",
                "native_pdf_text",
                "binary_metadata_scrape",
            ],
            OCR_MIN_TEXT_CHARS_FOR_SKIP=1200,
        ),
    }
    exec(compile(module, str(path), "exec"), namespace)
    return namespace


def _install_stage_stubs(monkeypatch) -> None:
    app_module = sys.modules.setdefault("app", types.ModuleType("app"))
    services_module = sys.modules.setdefault("app.services", types.ModuleType("app.services"))
    extraction_core_module = sys.modules.setdefault(
        "app.services.extraction_core",
        types.ModuleType("app.services.extraction_core"),
    )
    validation_module = sys.modules.setdefault(
        "app.services.validation",
        types.ModuleType("app.services.validation"),
    )

    profiles_module = types.ModuleType("app.services.extraction_core.profiles")
    profiles_module.load_profile = load_profile
    monkeypatch.setitem(sys.modules, "app.services.extraction_core.profiles", profiles_module)

    review_metadata_module = types.ModuleType("app.services.extraction_core.review_metadata")
    review_metadata_module._preparse_document_fields = _preparse_document_fields
    monkeypatch.setitem(sys.modules, "app.services.extraction_core.review_metadata", review_metadata_module)

    retrieval_module = types.ModuleType("app.services.validation.day1_retrieval_guard")

    def evaluate_anchor_evidence(text: str, min_score: float = 0.0):
        lowered = (text or "").lower()
        return {
            "bin": SimpleNamespace(score=1.0 if any(token in lowered for token in ("bin", "tin", "vat reg", "seller bin")) else 0.0),
            "gross_weight": SimpleNamespace(score=1.0 if "gross" in lowered else 0.0),
            "net_weight": SimpleNamespace(score=1.0 if "net" in lowered else 0.0),
            "doc_date": SimpleNamespace(score=1.0 if any(token in lowered for token in ("issue date", "invoice date", "2026-")) else 0.0),
            "issuer": SimpleNamespace(score=1.0 if any(token in lowered for token in ("issuer", "seller", "shipper", "carrier")) else 0.0),
            "voyage": SimpleNamespace(score=1.0 if "voyage" in lowered else 0.0),
        }

    retrieval_module.evaluate_anchor_evidence = evaluate_anchor_evidence
    monkeypatch.setitem(sys.modules, "app.services.validation.day1_retrieval_guard", retrieval_module)

    app_module.services = services_module
    services_module.extraction_core = extraction_core_module
    services_module.validation = validation_module


def _field_map(doc):
    return {field.name: field for field in doc.fields}


def _invoice_doc() -> dict[str, object]:
    raw_text = (
        "Seller Acme Exports Limited\n"
        "Invoice Date 14 Feb 2026\n"
        "BIN 1234567890123\n"
        "Gross Weight 100 KG\n"
        "Net Weight 90 KG\n"
    )
    return {
        "id": "doc-ci-1",
        "document_type": "commercial_invoice",
        "extraction_confidence": 0.96,
        "raw_text": raw_text,
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
            "raw_text": raw_text,
            "reason_codes": [],
            "stage_errors": {},
            "provider_attempts": [],
            "final_text_length": len(raw_text),
            "selected_stage": "ocr_provider_primary",
            "final_stage": "ocr_provider_primary",
        },
    }


def test_patch_i_bin_tin_ocr_confusion_chars():
    parsed = _preparse_document_fields(
        "Seller BIN/TIN No: 12S45O789O123\n",
        "commercial_invoice",
    )

    assert parsed["bin_tin"].state == "found"
    assert parsed["bin_tin"].value_normalized == "1254507890123"


def test_patch_i_bin_tin_invalid_length_rejection():
    parsed = _preparse_document_fields(
        "Seller BIN/TIN No: 1234567\n",
        "commercial_invoice",
    )

    assert parsed["bin_tin"].state == "parse_failed"
    assert "FORMAT_INVALID" in parsed["bin_tin"].reason_codes


def test_patch_i_gross_weight_parses_comma_unit_variant():
    parsed = _preparse_document_fields(
        "Gross Weight 1,250 KGS\n",
        "packing_list",
    )

    assert parsed["gross_weight"].state == "found"
    assert parsed["gross_weight"].value_normalized == "1250 KG"


def test_patch_i_net_weight_converts_lb_to_kg():
    parsed = _preparse_document_fields(
        "Net Weight 2204.62 LB\n",
        "packing_list",
    )

    assert parsed["net_weight"].state == "found"
    assert parsed["net_weight"].value_normalized == "1000 KG"


def test_patch_i_weight_table_disambiguation():
    parsed = _preparse_document_fields(
        "Gross Weight | Net Weight\n1,250 KG | 1,100 KG\n",
        "packing_list",
    )

    assert parsed["gross_weight"].value_normalized == "1250 KG"
    assert parsed["net_weight"].value_normalized == "1100 KG"


def test_patch_i_net_greater_than_gross_conflict():
    payload = _invoice_doc()
    payload["raw_text"] = (
        "Seller Acme Exports Limited\n"
        "Invoice Date 14 Feb 2026\n"
        "BIN 1234567890123\n"
        "Gross Weight 80 KG\n"
        "Net Weight 90 KG\n"
    )
    payload["extraction_artifacts_v1"]["raw_text"] = payload["raw_text"]
    payload["extracted_fields"]["gross_weight"] = "80 KG"
    payload["field_details"]["gross_weight"]["evidence_snippet"] = "Gross Weight 80 KG"

    doc = build_document_extraction(payload)

    assert doc.review_required is True
    assert "CROSS_FIELD_CONFLICT" in doc.review_reasons


def test_patch_i_stage_promotion_when_ocr_has_valid_top3_anchors(monkeypatch):
    namespace = _load_validate_namespace()
    _install_stage_stubs(monkeypatch)
    artifacts = namespace["_empty_extraction_artifacts_v1"]()

    selected = namespace["_select_best_extraction_stage"](
        {
            "binary_metadata_scrape": "A" * 2600,
            "ocr_provider_primary": "Seller BIN/TIN 12S45O789O123\nGross Weight 1,250 KG\nNet Weight 1,100 KG\n",
        },
        artifacts,
        "commercial_invoice",
    )

    assert selected["stage"] == "ocr_provider_primary"
    assert artifacts["stage_selection_rationale"]["reason"] == "binary_scrape_rejected_low_top3_quality"


def test_patch_i_binary_scrape_rejected_when_low_quality_for_top3(monkeypatch):
    namespace = _load_validate_namespace()
    _install_stage_stubs(monkeypatch)
    artifacts = namespace["_empty_extraction_artifacts_v1"]()

    namespace["_select_best_extraction_stage"](
        {
            "binary_metadata_scrape": "A" * 2600,
            "native_pdf_text": "Gross Weight 100 KG\nNet Weight 90 KG\n",
        },
        artifacts,
        "packing_list",
    )

    assert artifacts["stage_scores"]["binary_metadata_scrape"]["binary_scrape_penalty"] >= 0.38
    assert artifacts["stage_selection_rationale"]["binary_rejected_for_top3"] is True


def test_patch_i_binary_scrape_only_available_when_no_other_signal(monkeypatch):
    namespace = _load_validate_namespace()
    _install_stage_stubs(monkeypatch)
    artifacts = namespace["_empty_extraction_artifacts_v1"]()

    selected = namespace["_select_best_extraction_stage"](
        {
            "binary_metadata_scrape": "Gross Weight ??? Net Weight ???",
            "native_pdf_text": "plain note",
        },
        artifacts,
        "packing_list",
    )

    assert selected["stage"] == "binary_metadata_scrape"
    assert artifacts["stage_selection_rationale"]["reason"] == "binary_scrape_only_available"


def test_patch_i_confidence_threshold_downgrade_path_marks_field_reason():
    payload = _invoice_doc()
    payload["extraction_confidence"] = 0.78
    for key in ("exporter_bin", "gross_weight", "net_weight"):
        payload["field_details"][key]["confidence"] = 0.78

    doc = build_document_extraction(payload)
    fields = _field_map(doc)

    assert doc.review_required is True
    assert "LOW_CONFIDENCE_CRITICAL" in doc.review_reasons
    assert "LOW_CONFIDENCE_CRITICAL" in fields["bin_tin"].reason_codes


def test_patch_i_reason_codes_emit_field_not_found_and_format_invalid():
    missing = _preparse_document_fields("Seller Acme Exports Limited\n", "commercial_invoice")
    invalid = _preparse_document_fields("Gross Weight ABC KG\n", "packing_list")

    assert "FIELD_NOT_FOUND" in missing["bin_tin"].reason_codes
    assert "FORMAT_INVALID" in invalid["gross_weight"].reason_codes


def test_patch_i_stage_rationale_persists_threshold_details(monkeypatch):
    namespace = _load_validate_namespace()
    _install_stage_stubs(monkeypatch)
    artifacts = namespace["_empty_extraction_artifacts_v1"]()

    namespace["_select_best_extraction_stage"](
        {
            "binary_metadata_scrape": "A" * 2600,
            "ocr_provider_primary": "Seller BIN/TIN 1234567890123\nGross Weight 100 KG\nNet Weight 90 KG\n",
        },
        artifacts,
        "commercial_invoice",
    )

    rationale = artifacts["stage_selection_rationale"]
    assert rationale["binary_min_quality"] == 0.58
    assert rationale["selected_stage_quality_score"] >= 0.6


def test_patch_i_contract_regression_is_additive():
    payload = copy.deepcopy(_invoice_doc())
    payload["custom_key"] = "keep-me"
    documents = [payload]

    bundle = annotate_documents_with_review_metadata(documents)

    assert bundle is not None
    assert documents[0]["custom_key"] == "keep-me"
    assert "review_required" in documents[0]
    assert "critical_field_states" in documents[0]
