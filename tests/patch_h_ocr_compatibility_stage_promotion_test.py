from __future__ import annotations

import ast
import copy
import sys
import types
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

from PIL import Image


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
        "_ocr_compatibility_v1_enabled",
        "_stage_promotion_v1_enabled",
        "_stage_threshold_tuning_v1_enabled",
        "_detect_input_mime_type",
        "_normalize_ocr_input",
        "_prepare_provider_ocr_payload",
        "_map_ocr_provider_error_code",
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
            "from io import BytesIO\n"
            "from typing import Any, Dict, List, Optional, Tuple\n"
        ).body
        + selected,
        type_ignores=[],
    )
    namespace: dict[str, object] = {
        "logger": _DummyLogger(),
        "settings": SimpleNamespace(
            OCR_NORMALIZATION_SHIM_ENABLED=True,
            OCR_NORMALIZATION_DPI=300,
            OCR_MAX_PAGES=5,
            OCR_MAX_BYTES=5 * 1024 * 1024,
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


def _load_response_shaping_namespace() -> dict[str, object]:
    path = ROOT / "apps" / "api" / "app" / "routers" / "validation" / "response_shaping.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    wanted_assigns = {
        "EXPOSURE_DIAGNOSTICS_V1_ENV",
        "_MAX_STAGE_ATTEMPTS",
        "_MAX_REASON_CODES",
        "_MAX_STAGE_SCORE_STAGES",
        "_MAX_STAGE_SCORE_KEYS",
        "_SAFE_REASON_CODE_RE",
    }
    wanted_funcs = {
        "exposure_diagnostics_v1_enabled",
        "_sanitize_reason_codes",
        "_normalize_stage_scores",
        "_extract_stage_error_code",
        "build_extraction_debug",
    }
    selected = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            target_names = {target.id for target in node.targets if isinstance(target, ast.Name)}
            if target_names & wanted_assigns:
                selected.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in wanted_funcs:
            selected.append(node)

    module = ast.Module(
        body=ast.parse("import os\nimport re\nfrom typing import Any, Dict, List, Optional\n").body + selected,
        type_ignores=[],
    )
    namespace: dict[str, object] = {}
    exec(compile(module, str(path), "exec"), namespace)
    return namespace


def _install_profile_stubs(monkeypatch) -> None:
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
            "bin": SimpleNamespace(score=1.0 if any(token in lowered for token in ("bin", "tin", "vat reg")) else 0.0),
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


def _install_pdf_render_stubs(monkeypatch, *, page_count: int = 2):
    pdf2image_module = types.ModuleType("pdf2image")
    pdf2image_module.convert_from_bytes = lambda *_args, **_kwargs: [
        Image.new("RGB", (24, 24), color="white") for _ in range(page_count)
    ]
    monkeypatch.setitem(sys.modules, "pdf2image", pdf2image_module)

    pypdf2_module = types.ModuleType("PyPDF2")

    class PdfReader:
        def __init__(self, _stream):
            self.pages = [object() for _ in range(page_count)]

    pypdf2_module.PdfReader = PdfReader
    monkeypatch.setitem(sys.modules, "PyPDF2", pypdf2_module)


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
            "stage_selection_rationale": {
                "selected_stage": "ocr_provider_primary",
                "reason": "anchor_promoted_over_binary_scrape",
                "binary_scrape_penalty_applied": True,
            },
        },
    }


def test_patch_h_pdf_payload_normalizes_for_google_provider(monkeypatch):
    namespace = _load_validate_namespace()
    _install_pdf_render_stubs(monkeypatch, page_count=2)

    payload = namespace["_prepare_provider_ocr_payload"](
        "google_documentai",
        b"%PDF-1.4 demo",
        "lc.pdf",
        "application/pdf",
    )

    assert payload["content_type"] == "image/tiff"
    assert payload["payload_source"] == "normalized"
    assert payload["page_count"] == 2
    assert payload["bytes_sent"] > 0


def test_patch_h_pdf_payload_normalizes_for_textract_provider(monkeypatch):
    namespace = _load_validate_namespace()
    _install_pdf_render_stubs(monkeypatch, page_count=2)

    payload = namespace["_prepare_provider_ocr_payload"](
        "aws_textract",
        b"%PDF-1.4 demo",
        "bl.pdf",
        "application/pdf",
    )

    assert payload["content_type"] == "image/tiff"
    assert payload["payload_source"] == "normalized"
    assert payload["original_content_type"] == "application/pdf"
    assert payload["bytes_sent"] > 0


def test_patch_h_unsupported_format_maps_cleanly():
    namespace = _load_validate_namespace()

    payload = namespace["_prepare_provider_ocr_payload"](
        "google_documentai",
        b"plain text",
        "note.txt",
        "text/plain",
    )

    assert payload["error_code"] == "OCR_UNSUPPORTED_FORMAT"
    assert namespace["_map_ocr_provider_error_code"]("unsupported file format") == "OCR_UNSUPPORTED_FORMAT"


def test_patch_h_stage_promotion_prefers_anchor_stage_over_binary_scrape(monkeypatch):
    namespace = _load_validate_namespace()
    _install_profile_stubs(monkeypatch)
    artifacts = namespace["_empty_extraction_artifacts_v1"]()

    selected = namespace["_select_best_extraction_stage"](
        {
            "binary_metadata_scrape": "A" * 2600,
            "ocr_provider_primary": "Invoice Date 2026-02-14\nBIN 12S45O789O123\nGross Weight 1OO KG\nNet Weight 9O KG\n",
        },
        artifacts,
        "commercial_invoice",
    )

    assert selected["stage"] == "ocr_provider_primary"
    assert artifacts["stage_selection_rationale"]["reason"] in {
        "anchor_promoted_over_binary_scrape",
        "binary_scrape_rejected_low_top3_quality",
    }
    assert artifacts["stage_scores"]["binary_metadata_scrape"]["binary_scrape_penalty"] > 0


def test_patch_h_binary_scrape_remains_fallback_when_others_have_no_signal(monkeypatch):
    namespace = _load_validate_namespace()
    _install_profile_stubs(monkeypatch)
    artifacts = namespace["_empty_extraction_artifacts_v1"]()

    selected = namespace["_select_best_extraction_stage"](
        {
            "binary_metadata_scrape": "Structured text 1234567890 " * 20,
            "native_pdf_text": "plain note",
        },
        artifacts,
        "supporting_document",
    )

    assert selected["stage"] == "binary_metadata_scrape"
    assert artifacts["stage_selection_rationale"]["reason"] == "highest_selection_score"


def test_patch_h_bin_tin_extracts_ocr_confused_value():
    parsed = _preparse_document_fields(
        "Exporter BIN/TIN No: 12S45O789O123\n",
        "commercial_invoice",
    )

    assert parsed["bin_tin"].state == "found"
    assert parsed["bin_tin"].value_normalized == "1254507890123"


def test_patch_h_gross_net_extract_mixed_units():
    parsed = _preparse_document_fields(
        "Gross Weight 1.2 MT\nNet Weight 950 KG\n",
        "packing_list",
    )

    assert parsed["gross_weight"].state == "found"
    assert parsed["gross_weight"].value_normalized == "1200 KG"
    assert parsed["net_weight"].value_normalized == "950 KG"


def test_patch_h_gross_net_label_disambiguation():
    parsed = _preparse_document_fields(
        "Gross/Net Weight: 100/90 KGS\n",
        "packing_list",
    )

    assert parsed["gross_weight"].value_normalized == "100 KG"
    assert parsed["net_weight"].value_normalized == "90 KG"


def test_patch_h_missing_vs_parse_failed_remains_correct():
    parsed = _preparse_document_fields(
        "BIN:\nGross Weight: ???\n",
        "commercial_invoice",
    )

    assert parsed["bin_tin"].state == "parse_failed"
    assert parsed["gross_weight"].state == "parse_failed"
    assert parsed["net_weight"].state == "missing"


def test_patch_h_evidence_required_downgrade_still_enforced():
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


def test_patch_h_extraction_debug_exposes_stage_rationale(monkeypatch):
    monkeypatch.delenv("LCCOPILOT_EXPOSURE_DIAGNOSTICS_V1_ENABLED", raising=False)
    response_shaping = _load_response_shaping_namespace()
    document = _invoice_doc()
    document["critical_field_states"] = {
        "bin_tin": "found",
        "gross_weight": "found",
        "net_weight": "found",
    }

    debug = response_shaping["build_extraction_debug"](document)

    assert debug["selected_stage_rationale"]["reason"] == "anchor_promoted_over_binary_scrape"
    assert "raw_text" not in debug


def test_patch_h_contract_fields_remain_additive():
    payload = copy.deepcopy(_invoice_doc())
    payload["custom_key"] = "keep-me"
    documents = [payload]

    bundle = annotate_documents_with_review_metadata(documents)

    assert bundle is not None
    assert documents[0]["custom_key"] == "keep-me"
    assert "review_required" in documents[0]
    assert "critical_field_states" in documents[0]


def test_patch_h_reason_code_mapping_is_canonical():
    payload = _invoice_doc()
    payload["raw_text"] = ""
    payload["extraction_status"] = "empty"
    payload["extraction_artifacts_v1"]["raw_text"] = ""
    payload["extraction_artifacts_v1"]["stage_errors"] = {
        "ocr_provider_primary": "unsupported content type",
    }

    doc = build_document_extraction(payload)

    assert "OCR_UNSUPPORTED_FORMAT" in doc.review_reasons


def test_patch_h_stage_scores_capture_target_hits_and_penalty(monkeypatch):
    namespace = _load_validate_namespace()
    _install_profile_stubs(monkeypatch)
    artifacts = namespace["_empty_extraction_artifacts_v1"]()

    namespace["_select_best_extraction_stage"](
        {
            "binary_metadata_scrape": "A" * 2600,
            "native_pdf_text": "Gross Weight 100 KG\nNet Weight 90 KG\n",
        },
        artifacts,
        "packing_list",
    )

    assert artifacts["stage_scores"]["native_pdf_text"]["target_field_hits"] >= 2
    assert "selection_score" in artifacts["stage_scores"]["native_pdf_text"]
    assert artifacts["stage_scores"]["binary_metadata_scrape"]["binary_scrape_penalty"] > 0
