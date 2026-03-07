from __future__ import annotations

import ast
import os
import sys
import types
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]


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
        "_finalize_text_extraction_result",
        "_extraction_fallback_hotfix_enabled",
        "_ocr_compatibility_v1_enabled",
        "_stage_promotion_v1_enabled",
        "_stage_threshold_tuning_v1_enabled",
        "_finalize_text_backed_extraction_status",
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


def _install_profile_stubs(monkeypatch, *, critical_fields=None):
    critical_fields = critical_fields or ["bin_tin", "gross_weight", "net_weight", "issue_date", "issuer"]

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
    profiles_module.load_profile = lambda _doc_type: {"critical_fields": list(critical_fields)}
    monkeypatch.setitem(sys.modules, "app.services.extraction_core.profiles", profiles_module)

    retrieval_module = types.ModuleType("app.services.validation.day1_retrieval_guard")

    def evaluate_anchor_evidence(text: str, min_score: float = 0.0):
        lowered = (text or "").lower()
        return {
            "bin": SimpleNamespace(score=1.0 if "bin" in lowered else 0.0),
            "gross_weight": SimpleNamespace(score=1.0 if "gross weight" in lowered else 0.0),
            "net_weight": SimpleNamespace(score=1.0 if "net weight" in lowered else 0.0),
            "doc_date": SimpleNamespace(score=1.0 if "2026-" in lowered or "issue date" in lowered else 0.0),
            "issuer": SimpleNamespace(score=1.0 if any(token in lowered for token in ("issuer", "seller", "exporter", "carrier")) else 0.0),
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


def _png_bytes(mode: str = "RGBA") -> bytes:
    image = Image.new(mode, (16, 16), color=(255, 0, 0, 128) if "A" in mode else "white")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_pdf_normalization_produces_provider_friendly_image_bytes(monkeypatch):
    namespace = _load_validate_namespace()
    _install_pdf_render_stubs(monkeypatch, page_count=2)

    normalized = namespace["_normalize_ocr_input"](b"%PDF-1.4 demo", "doc.pdf", "application/pdf")

    assert normalized["content_type"] == "image/tiff"
    assert normalized["page_count"] == 2
    assert normalized["dpi"] == 300
    assert normalized["content"][:4] in (b"II*\x00", b"MM\x00*")


def test_image_normalization_produces_png_bytes():
    namespace = _load_validate_namespace()

    normalized = namespace["_normalize_ocr_input"](_png_bytes(), "scan.png", "image/png")

    assert normalized["content_type"] == "image/png"
    assert normalized["page_count"] == 1
    assert normalized["content"][:8] == b"\x89PNG\r\n\x1a\n"


def test_unsupported_format_maps_to_ocr_unsupported_format():
    namespace = _load_validate_namespace()

    normalized = namespace["_normalize_ocr_input"](b"plain text", "note.txt", "text/plain")

    assert normalized["error_code"] == "OCR_UNSUPPORTED_FORMAT"
    assert namespace["_map_ocr_provider_error_code"]("unsupported file format") == "OCR_UNSUPPORTED_FORMAT"


def test_scoring_prefers_higher_quality_stage_over_first_non_empty(monkeypatch):
    namespace = _load_validate_namespace()
    _install_profile_stubs(monkeypatch)
    artifacts = namespace["_empty_extraction_artifacts_v1"]()

    selected = namespace["_select_best_extraction_stage"](
        {
            "native_pdf_text": "short text",
            "ocr_provider_primary": "Invoice Date 2026-01-01\nBIN 1234567890\nGross Weight 10 KG\nNet Weight 9 KG\nSeller Acme Exports",
        },
        artifacts,
        "commercial_invoice",
    )

    assert selected["stage"] == "ocr_provider_primary"
    assert artifacts["selected_stage"] == "ocr_provider_primary"


def test_tie_break_behavior_is_deterministic(monkeypatch):
    namespace = _load_validate_namespace()
    _install_profile_stubs(monkeypatch, critical_fields=[])
    artifacts = namespace["_empty_extraction_artifacts_v1"]()

    selected = namespace["_select_best_extraction_stage"](
        {
            "native_pdf_text": "Same text 123",
            "ocr_secondary": "Same text 123",
        },
        artifacts,
        "supporting_document",
    )

    assert selected["stage"] == "ocr_secondary"
    assert artifacts["rejected_stages"]["native_pdf_text"]["reason"] == "tie_break_priority"


def test_anchor_hit_stage_wins_when_text_length_is_similar(monkeypatch):
    namespace = _load_validate_namespace()
    _install_profile_stubs(monkeypatch, critical_fields=["gross_weight", "net_weight"])
    artifacts = namespace["_empty_extraction_artifacts_v1"]()

    selected = namespace["_select_best_extraction_stage"](
        {
            "native_pdf_text": "AAAAAAAAAAAAAAAAAA 1234567890",
            "ocr_secondary": "Gross Weight 10 KG\nNet Weight 9 KG",
        },
        artifacts,
        "packing_list",
    )

    assert selected["stage"] == "ocr_secondary"
    assert artifacts["stage_scores"]["ocr_secondary"]["anchor_hit_score"] > artifacts["stage_scores"]["native_pdf_text"]["anchor_hit_score"]


def test_alnum_garbage_text_loses_against_structured_text(monkeypatch):
    namespace = _load_validate_namespace()
    _install_profile_stubs(monkeypatch)
    artifacts = namespace["_empty_extraction_artifacts_v1"]()

    selected = namespace["_select_best_extraction_stage"](
        {
            "native_pdf_text": "@@@ ### $$$ --- !!!",
            "ocr_provider_primary": "Invoice Date 2026-01-01 BIN 1234567890 Gross Weight 10 KG Net Weight 9 KG Seller Acme",
        },
        artifacts,
        "commercial_invoice",
    )

    assert selected["stage"] == "ocr_provider_primary"
    assert artifacts["stage_scores"]["native_pdf_text"]["alnum_ratio_score"] < artifacts["stage_scores"]["ocr_provider_primary"]["alnum_ratio_score"]


def test_selected_stage_and_score_breakdown_are_persisted(monkeypatch):
    namespace = _load_validate_namespace()
    _install_profile_stubs(monkeypatch)
    artifacts = namespace["_empty_extraction_artifacts_v1"]()

    namespace["_select_best_extraction_stage"](
        {
            "native_pdf_text": "Invoice 123",
            "ocr_provider_primary": "Invoice Date 2026-01-01 BIN 1234567890 Gross Weight 10 KG Net Weight 9 KG Seller Acme",
        },
        artifacts,
        "commercial_invoice",
    )

    assert "native_pdf_text" in artifacts["stage_scores"]
    assert "ocr_provider_primary" in artifacts["stage_scores"]
    assert artifacts["selected_stage"] == "ocr_provider_primary"
    assert "native_pdf_text" in artifacts["rejected_stages"]


def test_parse_failed_semantics_do_not_regress(monkeypatch):
    namespace = _load_validate_namespace()
    monkeypatch.delenv("LCCOPILOT_EXTRACTION_FALLBACK_HOTFIX", raising=False)

    doc_info = {"extraction_status": "empty", "extracted_fields": {}}
    namespace["_finalize_text_backed_extraction_status"](doc_info, "commercial_invoice", "Recovered OCR text")

    assert doc_info["extraction_status"] == "parse_failed"


def test_backward_compatible_artifact_fields_are_preserved():
    namespace = _load_validate_namespace()

    artifacts = namespace["_empty_extraction_artifacts_v1"]("raw", 0.9)

    for key in ("raw_text", "tables", "key_value_candidates", "spans", "bbox", "ocr_confidence"):
        assert key in artifacts
    for key in ("stage_scores", "selected_stage", "rejected_stages"):
        assert key in artifacts


def test_finalizer_keeps_selected_stage_alias():
    namespace = _load_validate_namespace()
    artifacts = namespace["_empty_extraction_artifacts_v1"]()
    artifacts["selected_stage"] = "ocr_provider_primary"

    result = namespace["_finalize_text_extraction_result"](
        artifacts,
        stage="ocr_provider_primary",
        text="Invoice Date 2026-01-01",
    )

    assert result["artifacts"]["selected_stage"] == "ocr_provider_primary"
    assert result["artifacts"]["final_stage"] == "ocr_provider_primary"


def test_config_source_exposes_shim_and_scorer_toggles():
    source = (ROOT / "apps" / "api" / "app" / "config.py").read_text(encoding="utf-8")
    assert "OCR_NORMALIZATION_SHIM_ENABLED" in source
    assert "OCR_STAGE_SCORER_ENABLED" in source
