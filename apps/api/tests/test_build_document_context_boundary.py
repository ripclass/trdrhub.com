from __future__ import annotations

import ast
import asyncio
import os
import sys
import time
import types
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
VALIDATE_PATH = ROOT / "app" / "routers" / "validate.py"


def _load_symbols(path: Path, names: set[str], namespace: Dict[str, Any]) -> Dict[str, Any]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    selected: list[ast.stmt] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names:
            selected.append(node)
    module = ast.Module(body=selected, type_ignores=[])
    exec(compile(module, filename=str(path), mode="exec"), namespace)
    return namespace


def _install_stub_modules() -> None:
    app_pkg = types.ModuleType("app")
    app_pkg.__path__ = []  # type: ignore[attr-defined]
    sys.modules.setdefault("app", app_pkg)

    rules_pkg = types.ModuleType("app.rules")
    rules_pkg.__path__ = []  # type: ignore[attr-defined]
    sys.modules["app.rules"] = rules_pkg

    extractors_mod = types.ModuleType("app.rules.extractors")

    class DocumentFieldExtractor:
        def extract_fields(self, *args: Any, **kwargs: Any) -> list[Any]:
            return []

    class ISO20022ParseError(Exception):
        pass

    def extract_iso20022_lc(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return {}

    extractors_mod.DocumentFieldExtractor = DocumentFieldExtractor
    extractors_mod.ISO20022ParseError = ISO20022ParseError
    extractors_mod.extract_iso20022_lc = extract_iso20022_lc
    sys.modules["app.rules.extractors"] = extractors_mod

    models_mod = types.ModuleType("app.rules.models")

    class DocumentType:
        LETTER_OF_CREDIT = "letter_of_credit"
        SUPPORTING_DOCUMENT = "supporting_document"

    models_mod.DocumentType = DocumentType
    sys.modules["app.rules.models"] = models_mod

    services_pkg = types.ModuleType("app.services")
    services_pkg.__path__ = []  # type: ignore[attr-defined]
    sys.modules["app.services"] = services_pkg

    extraction_pkg = types.ModuleType("app.services.extraction")
    extraction_pkg.__path__ = []  # type: ignore[attr-defined]
    sys.modules["app.services.extraction"] = extraction_pkg

    lc_extractor_mod = types.ModuleType("app.services.extraction.lc_extractor")
    lc_extractor_mod.extract_lc_structured = lambda *args, **kwargs: {}
    sys.modules["app.services.extraction.lc_extractor"] = lc_extractor_mod


class _LoggerStub:
    def debug(self, *args: Any, **kwargs: Any) -> None:
        return None

    def info(self, *args: Any, **kwargs: Any) -> None:
        return None

    def warning(self, *args: Any, **kwargs: Any) -> None:
        return None

    def error(self, *args: Any, **kwargs: Any) -> None:
        return None


class _SettingsStub:
    OCR_MAX_CONCURRENCY = 2
    EXTRACTION_LLM_CONCURRENCY = 4


class DummyUploadFile:
    def __init__(self, filename: str, content_type: str, data: bytes) -> None:
        self.filename = filename
        self.content_type = content_type
        self._data = data

    async def read(self) -> bytes:
        return self._data

    async def seek(self, offset: int) -> None:
        return None


async def _fake_extract_text_from_upload(upload_file: DummyUploadFile, document_type: Optional[str] = None) -> dict[str, Any]:
    text = {
        "LC_001.pdf": ":20:LC12345\n:46A:INVOICE/WEIGHT LIST\n:47A:SHIPMENT DOCS AS PER LC",
        "Invoice_001.pdf": "COMMERCIAL INVOICE\nINVOICE NO: INV-001\nAMOUNT: USD 1000",
        "Weight_List_001.pdf": "WEIGHT LIST\nREF: WL-001\nNET: 850 KG\nGROSS: 900 KG",
        "Unknown_Support.pdf": "MISC SUPPORTING DOC\nREFERENCE: SUP-001",
    }[upload_file.filename]
    return {
        "text": text,
        "artifacts": {
            "version": "extraction_artifacts_v1",
            "raw_text": text,
            "tables": [],
            "key_value_candidates": [],
            "spans": [],
            "bbox": [],
            "ocr_confidence": 0.95,
            "attempted_stages": [],
            "text_length_by_stage": {},
            "stage_errors": {},
            "reason_codes": [],
            "provider_attempts": [],
            "fallback_activated": False,
            "final_stage": None,
            "final_text_length": len(text),
            "stage_scores": {},
            "selected_stage": None,
            "rejected_stages": {},
            "total_time_ms": 3.0,
        },
    }


class DummyLaunchPipeline:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def process_document(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(
            {
                "filename": kwargs.get("filename"),
                "document_type": kwargs.get("document_type"),
                "content_type": kwargs.get("content_type"),
                "has_file_bytes": bool(kwargs.get("file_bytes")),
            }
        )
        filename = kwargs.get("filename")
        if filename == "LC_001.pdf":
            return {
                "handled": True,
                "context_key": "lc",
                "context_payload": {
                    "raw_text": kwargs.get("extracted_text"),
                    "lc_number": "LC12345",
                    "documents_required": ["INVOICE", "WEIGHT LIST"],
                },
                "doc_info_patch": {
                    "extracted_fields": {
                        "lc_number": "LC12345",
                        "documents_required": ["INVOICE", "WEIGHT LIST"],
                    },
                    "extraction_status": "success",
                    "extraction_method": "mock_launch_pipeline",
                },
                "has_structured_data": True,
                "lc_number": "LC12345",
                "validation_doc_type": None,
                "post_validation_target": "lc",
            }
        if filename == "Invoice_001.pdf":
            return {
                "handled": True,
                "context_key": "invoice",
                "context_payload": {
                    "raw_text": kwargs.get("extracted_text"),
                    "invoice_number": "INV-001",
                    "amount": "USD 1000",
                },
                "doc_info_patch": {
                    "extracted_fields": {"invoice_number": "INV-001", "amount": "USD 1000"},
                    "extraction_status": "success",
                    "extraction_method": "mock_launch_pipeline",
                },
                "has_structured_data": True,
                "validation_doc_type": None,
                "post_validation_target": "invoice",
            }
        if filename == "Weight_List_001.pdf":
            return {
                "handled": True,
                "context_key": "weight_list",
                "context_payload": {
                    "raw_text": kwargs.get("extracted_text"),
                    "gross_weight": "900 KG",
                    "net_weight": "850 KG",
                },
                "doc_info_patch": {
                    "inspection_subtype": "weight_certificate",
                    "extracted_fields": {"gross_weight": "900 KG", "net_weight": "850 KG"},
                    "extraction_status": "success",
                    "extraction_method": "mock_launch_pipeline",
                },
                "has_structured_data": True,
                "validation_doc_type": None,
                "post_validation_target": "weight_list",
            }
        return {"handled": False}


def test_build_document_context_lc_first_mixed_batch_uses_launch_pipeline_as_single_boundary() -> None:
    _install_stub_modules()
    pipeline = DummyLaunchPipeline()

    namespace: Dict[str, Any] = {
        "asyncio": asyncio,
        "os": os,
        "time": time,
        "uuid4": uuid4,
        "Any": Any,
        "Dict": Dict,
        "List": List,
        "Optional": Optional,
        "settings": _SettingsStub(),
        "logger": _LoggerStub(),
        "_canonical_document_tag": lambda value: str(value).strip().lower(),
        "_resolve_document_type": lambda filename, idx, normalized_tags: normalized_tags.get(str(filename).lower(), "supporting_document"),
        "_extract_text_from_upload": _fake_extract_text_from_upload,
        "_empty_extraction_artifacts_v1": lambda raw_text="", ocr_confidence=None: {
            "version": "extraction_artifacts_v1",
            "raw_text": raw_text or "",
            "tables": [],
            "key_value_candidates": [],
            "spans": [],
            "bbox": [],
            "ocr_confidence": ocr_confidence,
            "attempted_stages": [],
            "text_length_by_stage": {},
            "stage_errors": {},
            "reason_codes": [],
            "provider_attempts": [],
            "fallback_activated": False,
            "final_stage": None,
            "final_text_length": len((raw_text or "").strip()),
            "stage_scores": {},
            "selected_stage": None,
            "rejected_stages": {},
        },
        "_infer_required_document_types_from_lc": lambda lc: [
            "commercial_invoice",
            "weight_certificate",
        ] if lc and lc.get("documents_required") else [],
        "_maybe_promote_document_type_from_content": lambda **kwargs: {
            "document_type": kwargs.get("current_type"),
            "promoted": False,
            "content_classification": None,
        },
        "get_launch_extraction_pipeline": lambda: pipeline,
        "LaunchExtractionPipeline": type(pipeline),
        "_apply_two_stage_validation": lambda payload, *args, **kwargs: (payload, {}),
        "_context_payload_for_doc_type": lambda context, document_type: context.get(document_type) or context.get({
            "letter_of_credit": "lc",
            "commercial_invoice": "invoice",
            "weight_list": "weight_list",
            "supporting_document": "supporting_document",
        }.get(document_type, document_type), {}),
        "_apply_direct_token_recovery": lambda *args, **kwargs: None,
        "_enforce_day1_runtime_policy": lambda *args, **kwargs: None,
        "_apply_extraction_guard": lambda *args, **kwargs: None,
        "_finalize_text_backed_extraction_status": lambda *args, **kwargs: None,
        "_stabilize_document_review_semantics": lambda *args, **kwargs: None,
        "_resolve_doc_llm_trace": lambda *args, **kwargs: {},
        "_count_populated_canonical_fields": lambda fields: len(fields or {}),
        "_build_document_extraction_payload": lambda **kwargs: kwargs,
        "_log_document_extraction_telemetry": lambda **kwargs: None,
        "_augment_doc_field_details_with_decisions": lambda docs: None,
        "_annotate_documents_with_review_metadata": lambda docs: {"documents": len(docs or [])},
        "_normalize_lc_payload_structures": lambda payload: payload,
        "build_lc_classification": lambda lc, context=None: {"required_documents": [{"code": "commercial_invoice"}, {"code": "weight_certificate"}]},
        "_build_minimal_lc_structured_output": lambda lc_data, context: {"lc_number": (lc_data or {}).get("lc_number")},
        "_extraction_fallback_hotfix_enabled": lambda: False,
        "_backfill_lc_mt700_sources": lambda lc_data, *args, **kwargs: lc_data,
        "_repair_lc_mt700_dates": lambda payload: payload,
        "build_lc_requirements_graph_v1": lambda lc_data: {},
        "_extract_extraction_resolution_from_context_payload": lambda payload: None,
    }

    loaded = _load_symbols(VALIDATE_PATH, {"_build_document_context"}, namespace)
    build_document_context = loaded["_build_document_context"]

    files = [
        DummyUploadFile("LC_001.pdf", "application/pdf", b"lc-bytes"),
        DummyUploadFile("Invoice_001.pdf", "application/pdf", b"invoice-bytes"),
        DummyUploadFile("Weight_List_001.pdf", "application/pdf", b"weight-bytes"),
        DummyUploadFile("Unknown_Support.pdf", "application/pdf", b"support-bytes"),
    ]

    context = asyncio.run(
        build_document_context(
            files,
            document_tags={
                "LC_001.pdf": "letter_of_credit",
                "Invoice_001.pdf": "commercial_invoice",
                "Weight_List_001.pdf": "weight_list",
                "Unknown_Support.pdf": "supporting_document",
            },
        )
    )

    # LC goes through singleton pipeline; supporting docs run in parallel
    # via fresh LaunchExtractionPipeline instances (to avoid shared state).
    # The singleton only sees the LC call.
    lc_calls = [c for c in pipeline.calls if c["filename"] == "LC_001.pdf"]
    assert len(lc_calls) == 1
    assert lc_calls[0]["has_file_bytes"]
    assert context["lc_number"] == "LC12345"
    assert context["lc"]["documents_required"] == ["INVOICE", "WEIGHT LIST"]
    assert context["invoice"]["invoice_number"] == "INV-001"
    assert context["weight_list"]["gross_weight"] == "900 KG"
    assert context["weight_list"]["net_weight"] == "850 KG"
    assert context["supporting_document"]["raw_text"] == "MISC SUPPORTING DOC\nREFERENCE: SUP-001"
    assert context["documents_presence"]["letter_of_credit"]["present"] is True
    assert context["documents_presence"]["commercial_invoice"]["present"] is True
    assert context["documents_presence"]["weight_list"]["present"] is True
    assert context["extraction_status"] == "success"
    docs = context["documents"]
    assert len(docs) == 4
    assert docs[0]["document_type"] == "letter_of_credit"
    assert docs[0]["extraction_method"] == "mock_launch_pipeline"
    assert docs[1]["document_type"] == "commercial_invoice"
    assert docs[2]["document_type"] == "weight_list"
    assert docs[3]["document_type"] == "supporting_document"
    assert docs[3]["extraction_status"] == "text_only"


def test_build_document_context_allows_lc_launch_pipeline_when_route_text_is_empty() -> None:
    _install_stub_modules()

    class LCOnlyPipeline:
        def __init__(self) -> None:
            self.calls: list[dict[str, Any]] = []

        async def process_document(self, **kwargs: Any) -> dict[str, Any]:
            self.calls.append(
                {
                    "filename": kwargs.get("filename"),
                    "document_type": kwargs.get("document_type"),
                    "extracted_text": kwargs.get("extracted_text"),
                    "has_file_bytes": bool(kwargs.get("file_bytes")),
                }
            )
            if kwargs.get("document_type") == "letter_of_credit":
                return {
                    "handled": True,
                    "context_key": "lc",
                    "context_payload": {
                        "raw_text": "",
                        "lc_number": "LC-MM-001",
                        "documents_required": ["COMMERCIAL INVOICE", "PACKING LIST"],
                    },
                    "doc_info_patch": {
                        "extracted_fields": {
                            "lc_number": "LC-MM-001",
                            "documents_required": ["COMMERCIAL INVOICE", "PACKING LIST"],
                        },
                        "extraction_status": "success",
                        "extraction_method": "multimodal_ai_first",
                    },
                    "has_structured_data": True,
                    "lc_number": "LC-MM-001",
                    "validation_doc_type": None,
                    "post_validation_target": "lc",
                }
            return {"handled": False}

    pipeline = LCOnlyPipeline()

    async def _fake_extract_text_empty_for_lc(upload_file: DummyUploadFile, document_type: Optional[str] = None) -> dict[str, Any]:
        if upload_file.filename == "LC_Image_001.pdf":
            return {
                "text": "",
                "artifacts": {
                    "version": "extraction_artifacts_v1",
                    "raw_text": "",
                    "tables": [],
                    "key_value_candidates": [],
                    "spans": [],
                    "bbox": [],
                    "ocr_confidence": None,
                    "attempted_stages": [],
                    "text_length_by_stage": {},
                    "stage_errors": {},
                    "reason_codes": ["OCR_SKIPPED_NO_VIABLE_PROVIDER"],
                    "provider_attempts": [],
                    "fallback_activated": False,
                    "final_stage": None,
                    "final_text_length": 0,
                    "stage_scores": {},
                    "selected_stage": None,
                    "rejected_stages": {},
                },
            }
        return await _fake_extract_text_from_upload(upload_file, document_type=document_type)

    namespace: Dict[str, Any] = {
        "asyncio": asyncio,
        "os": os,
        "time": time,
        "uuid4": uuid4,
        "Any": Any,
        "Dict": Dict,
        "List": List,
        "Optional": Optional,
        "settings": _SettingsStub(),
        "logger": _LoggerStub(),
        "_canonical_document_tag": lambda value: str(value).strip().lower(),
        "_resolve_document_type": lambda filename, idx, normalized_tags: normalized_tags.get(str(filename).lower(), "supporting_document"),
        "_extract_text_from_upload": _fake_extract_text_empty_for_lc,
        "_empty_extraction_artifacts_v1": lambda raw_text="", ocr_confidence=None: {
            "version": "extraction_artifacts_v1",
            "raw_text": raw_text or "",
            "tables": [],
            "key_value_candidates": [],
            "spans": [],
            "bbox": [],
            "ocr_confidence": ocr_confidence,
            "attempted_stages": [],
            "text_length_by_stage": {},
            "stage_errors": {},
            "reason_codes": [],
            "provider_attempts": [],
            "fallback_activated": False,
            "final_stage": None,
            "final_text_length": len((raw_text or "").strip()),
            "stage_scores": {},
            "selected_stage": None,
            "rejected_stages": {},
        },
        "_infer_required_document_types_from_lc": lambda lc: ["commercial_invoice", "packing_list"] if lc and lc.get("documents_required") else [],
        "_maybe_promote_document_type_from_content": lambda **kwargs: {
            "document_type": kwargs.get("current_type"),
            "promoted": False,
            "content_classification": None,
        },
        "get_launch_extraction_pipeline": lambda: pipeline,
        "LaunchExtractionPipeline": type(pipeline),
        "_apply_two_stage_validation": lambda payload, *args, **kwargs: (payload, {}),
        "_context_payload_for_doc_type": lambda context, document_type: context.get(document_type) or context.get({
            "letter_of_credit": "lc",
            "commercial_invoice": "invoice",
            "supporting_document": "supporting_document",
        }.get(document_type, document_type), {}),
        "_apply_direct_token_recovery": lambda *args, **kwargs: None,
        "_enforce_day1_runtime_policy": lambda *args, **kwargs: None,
        "_apply_extraction_guard": lambda *args, **kwargs: None,
        "_finalize_text_backed_extraction_status": lambda *args, **kwargs: None,
        "_stabilize_document_review_semantics": lambda *args, **kwargs: None,
        "_resolve_doc_llm_trace": lambda *args, **kwargs: {},
        "_count_populated_canonical_fields": lambda fields: len(fields or {}),
        "_build_document_extraction_payload": lambda **kwargs: kwargs,
        "_log_document_extraction_telemetry": lambda **kwargs: None,
        "_augment_doc_field_details_with_decisions": lambda docs: None,
        "_annotate_documents_with_review_metadata": lambda docs: {"documents": len(docs or [])},
        "_normalize_lc_payload_structures": lambda payload: payload,
        "build_lc_classification": lambda lc, context=None: {"required_documents": [{"code": "commercial_invoice"}, {"code": "packing_list"}]},
        "_build_minimal_lc_structured_output": lambda lc_data, context: {"lc_number": (lc_data or {}).get("lc_number")},
        "_extraction_fallback_hotfix_enabled": lambda: False,
        "_backfill_lc_mt700_sources": lambda lc_data, *args, **kwargs: lc_data,
        "_repair_lc_mt700_dates": lambda payload: payload,
        "build_lc_requirements_graph_v1": lambda lc_data: {},
        "_extract_extraction_resolution_from_context_payload": lambda payload: None,
    }

    loaded = _load_symbols(VALIDATE_PATH, {"_build_document_context"}, namespace)
    build_document_context = loaded["_build_document_context"]

    files = [DummyUploadFile("LC_Image_001.pdf", "application/pdf", b"lc-image-bytes")]

    context = asyncio.run(
        build_document_context(
            files,
            document_tags={
                "LC_Image_001.pdf": "letter_of_credit",
            },
        )
    )

    assert len(pipeline.calls) == 1
    assert pipeline.calls[0]["filename"] == "LC_Image_001.pdf"
    assert pipeline.calls[0]["document_type"] == "letter_of_credit"
    assert pipeline.calls[0]["extracted_text"] == ""
    assert pipeline.calls[0]["has_file_bytes"] is True
    assert context["lc_number"] == "LC-MM-001"
    assert context["lc"]["documents_required"] == ["COMMERCIAL INVOICE", "PACKING LIST"]
    assert context["documents"][0]["extraction_method"] == "multimodal_ai_first"
    assert context["documents"][0]["extraction_status"] == "success"
