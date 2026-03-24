from __future__ import annotations

import ast
import asyncio
import json
import re
import sys
import types
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.reference_data import get_country_registry, get_currency_registry, get_port_registry


LC_CLASSIFIER_PATH = ROOT / "app" / "services" / "lc_classifier.py"
LAUNCH_PIPELINE_PATH = ROOT / "app" / "services" / "extraction" / "launch_pipeline.py"


class LCType:
    class _Value:
        def __init__(self, value: str) -> None:
            self.value = value

    IMPORT = _Value("import")
    EXPORT = _Value("export")
    UNKNOWN = _Value("unknown")


def _load_symbols(path: Path, names: set[str], namespace: Dict[str, Any]) -> Dict[str, Any]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    selected: list[ast.stmt] = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets = {
                target.id
                for target in node.targets
                if isinstance(target, ast.Name)
            }
            if targets & names:
                selected.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in names:
            selected.append(node)
        elif isinstance(node, ast.ClassDef) and node.name in names:
            selected.append(node)
    module = ast.Module(body=selected, type_ignores=[])
    exec(compile(module, filename=str(path), mode="exec"), namespace)
    return namespace


def _load_shape_lc_financial_payload():
    namespace: Dict[str, Any] = {
        "re": re,
        "Any": Any,
        "Dict": Dict,
        "List": List,
        "Optional": Optional,
        "get_port_registry": get_port_registry,
        "get_country_registry": get_country_registry,
        "get_currency_registry": get_currency_registry,
        "build_lc_classification": lambda payload: {},
    }
    symbols = {
        "CANONICAL_DOCUMENT_ALIASES",
        "MEASUREMENT_LABEL_ALIASES",
        "_normalize_lookup_key",
        "_normalize_country_value",
        "_normalize_port_value",
        "_normalize_currency_value",
        "_normalize_measurement_label",
        "_normalize_document_alias",
        "_apply_canonical_normalization",
        "_extract_label_value",
        "_extract_amount_value",
        "_coerce_mt700_date_iso",
        "_extract_mt700_timeline_fields",
        "_shape_lc_financial_payload",
    }
    loaded = _load_symbols(LAUNCH_PIPELINE_PATH, symbols, namespace)
    return loaded["_shape_lc_financial_payload"]


def _load_detect_lc_type():
    namespace: Dict[str, Any] = {
        "re": re,
        "Any": Any,
        "Dict": Dict,
        "Optional": Optional,
        "LCType": LCType,
        "LCTypeGuess": Dict[str, Any],
        "detect_lc_family": lambda lc_data: {
            "family": "iso" if (lc_data or {}).get("format") == "iso20022" else "mt",
            "confidence": 0.8,
            "evidence": ["declared-format"],
        },
    }
    symbols = {
        "COUNTRY_SYNONYMS",
        "detect_lc_type",
        "_extract_party_country",
        "_extract_port_country",
        "_normalize_country",
    }
    loaded = _load_symbols(LC_CLASSIFIER_PATH, symbols, namespace)
    return loaded["detect_lc_type"]


class _LoggerStub:
    def warning(self, *args: Any, **kwargs: Any) -> None:
        return None


class _QualityAssessment:
    overall_score = 0.92
    quality_level = types.SimpleNamespace(value="good")
    can_proceed = True
    warnings: list[str] = []
    recommendations: list[str] = []


class _QualityGateStub:
    def assess(self, _text: str, ocr_confidence: Any = None, metadata: Any = None) -> _QualityAssessment:
        return _QualityAssessment()


class _FieldExtractorStub:
    def extract_fields(self, *args: Any, **kwargs: Any) -> list[Any]:
        return []


class _DocumentTypeStub:
    LETTER_OF_CREDIT = "letter_of_credit"
    COMMERCIAL_INVOICE = "commercial_invoice"
    BILL_OF_LADING = "bill_of_lading"
    PACKING_LIST = "packing_list"
    CERTIFICATE_OF_ORIGIN = "certificate_of_origin"
    INSURANCE_CERTIFICATE = "insurance_certificate"
    INSPECTION_CERTIFICATE = "inspection_certificate"


async def _failed_ai(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return {"_status": "failed"}


def _load_launch_supporting_pipeline(overrides: Optional[Dict[str, Any]] = None):
    namespace: Dict[str, Any] = {
        "re": re,
        "json": json,
        "Any": Any,
        "Dict": Dict,
        "List": List,
        "Optional": Optional,
        "logger": _LoggerStub(),
        "OCRQualityGate": _QualityGateStub,
        "DocumentFieldExtractor": _FieldExtractorStub,
        "DocumentType": _DocumentTypeStub,
        "extract_insurance_ai_first": _failed_ai,
        "extract_inspection_ai_first": _failed_ai,
        "extract_lc_ai_first": _failed_ai,
        "extract_iso20022_with_ai_fallback": _failed_ai,
        "extract_invoice_ai_first": _failed_ai,
        "extract_bl_ai_first": _failed_ai,
        "extract_packing_list_ai_first": _failed_ai,
        "extract_coo_ai_first": _failed_ai,
        "extract_document_multimodal_first": _failed_ai,
        "detect_iso20022_schema": lambda _text: (None, 0.0),
        "detect_lc_format": lambda _text: "mt700",
        "_apply_canonical_normalization": lambda payload: dict(payload or {}),
        "_detect_lc_financial_subtype": lambda **kwargs: str(kwargs.get("document_type") or "letter_of_credit"),
        "_shape_lc_financial_payload": lambda payload, **kwargs: dict(payload or {}),
        "_build_lc_user_facing_extracted_fields": lambda payload: dict(payload or {}),
        "_assess_lc_financial_completeness": lambda payload, **kwargs: {
            "parse_complete": False,
            "required_ratio": 0.0,
            "missing_required_fields": [],
            "required_found": 0,
            "required_total": 0,
            "review_reasons": [],
        },
        "_shape_invoice_financial_payload": lambda payload, **kwargs: dict(payload or {}),
        "_assess_invoice_financial_completeness": lambda payload, **kwargs: {
            "parse_complete": False,
            "required_ratio": 0.0,
            "missing_required_fields": [],
            "required_found": 0,
            "required_total": 0,
            "review_reasons": [],
        },
        "_detect_invoice_financial_subtype": lambda **kwargs: "commercial_invoice",
        "_shape_transport_payload": lambda payload, **kwargs: dict(payload or {}),
        "_assess_transport_completeness": lambda payload, **kwargs: {
            "parse_complete": False,
            "required_ratio": 0.0,
            "missing_required_fields": [],
            "required_found": 0,
            "required_total": 0,
            "review_reasons": [],
        },
        "_detect_transport_subtype": lambda **kwargs: "bill_of_lading",
        "_shape_regulatory_payload": lambda payload, **kwargs: dict(payload or {}),
        "_assess_regulatory_completeness": lambda payload, **kwargs: {
            "parse_complete": False,
            "required_ratio": 0.0,
            "missing_required_fields": [],
            "required_found": 0,
            "required_total": 0,
            "review_reasons": [],
        },
        "_detect_regulatory_subtype": lambda **kwargs: "certificate_of_origin",
        "_guess_supporting_document_subtype": lambda **kwargs: {
            "family": "unknown",
            "subtype": "unknown",
            "confidence": 0.1,
            "reasons": [],
        },
        "_summarize_supporting_document": lambda text: {"preview": text[:40]},
        "build_lc_fact_set": lambda payload: {"version": "fact_graph_v1", "document_type": payload.get("document_type", "letter_of_credit"), "facts": []},
        "build_invoice_fact_set": lambda payload: {"version": "fact_graph_v1", "document_type": payload.get("document_type", "commercial_invoice"), "facts": []},
        "build_bl_fact_set": lambda payload: {"version": "fact_graph_v1", "document_type": payload.get("document_type", "bill_of_lading"), "facts": []},
        "build_packing_list_fact_set": lambda payload: {"version": "fact_graph_v1", "document_type": payload.get("document_type", "packing_list"), "facts": []},
        "build_coo_fact_set": lambda payload: {"version": "fact_graph_v1", "document_type": payload.get("document_type", "certificate_of_origin"), "facts": []},
        "build_insurance_fact_set": lambda payload: {"version": "fact_graph_v1", "document_type": payload.get("document_type", "insurance_certificate"), "facts": []},
        "build_inspection_fact_set": lambda payload: {"version": "fact_graph_v1", "document_type": payload.get("document_type", "inspection_certificate"), "facts": []},
        "build_supporting_fact_set": lambda payload: {"version": "fact_graph_v1", "document_type": payload.get("document_type", "supporting_document"), "facts": []},
    }
    symbols = {
        "PAYMENT_FAMILY_DOCUMENT_SUBTYPES",
        "GENERIC_SUPPORTING_DOCUMENT_SUBTYPES",
        "REGULATORY_FAMILY_DOCUMENT_SUBTYPES",
        "INSURANCE_FAMILY_DOCUMENT_SUBTYPES",
        "INSPECTION_FAMILY_DOCUMENT_SUBTYPES",
        "TRANSPORT_DOC_ALIASES",
        "MEASUREMENT_LABEL_ALIASES",
        "LaunchExtractionPipeline",
        "_resolve_extraction_lane",
        "_canonicalize_launch_doc_type",
        "_build_support_only_field_detail",
        "_build_support_only_field_details_from_payload",
        "_build_support_only_extraction_resolution",
        "_build_support_only_result",
        "_fields_to_flat_context",
        "_fields_to_lc_context",
        "_is_populated_field_value",
        "_assess_required_field_completeness",
        "_build_extraction_resolution_metrics",
        "_assess_insurance_completeness",
        "_assess_inspection_completeness",
        "_detect_insurance_subtype",
        "_detect_inspection_subtype",
        "_shape_insurance_payload",
        "_shape_inspection_payload",
        "_extract_label_value",
        "_extract_amount_value",
        "_has_extracted_content",
    }
    if overrides:
        namespace.update(overrides)
    loaded = _load_symbols(LAUNCH_PIPELINE_PATH, symbols, namespace)
    return loaded["LaunchExtractionPipeline"]


def test_live_exporter_sample_shape_populates_port_countries_and_orientation() -> None:
    shape_lc_financial_payload = _load_shape_lc_financial_payload()
    detect_lc_type = _load_detect_lc_type()

    raw_text = "\n".join(
        [
            "LC",
            ":20: DOCUMENTARY CREDIT NUMBER 100924060096",
            ":31C: DATE OF ISSUE 2026-03-08",
            ":31D: EXPIRY 2026-06-28 DHAKA",
            ":50: APPLICANT Applicant Co.",
            ":59: BENEFICIARY Beneficiary Co.",
            ":32B: USD 100000.00",
            ":44E: PORT OF LOADING Chattogram Port",
            ":44F: PORT OF DISCHARGE Jebel Ali Port",
            ":45A: GOODS General merchandise as per proforma invoice",
            ":46A: DOCS REQUIRED: INVOICE/BL/PL/COO/INSURANCE",
            ":47A: ADDITIONAL CONDITIONS APPLY",
        ]
    )

    lc_context = shape_lc_financial_payload(
        {
            "number": "100924060096",
            "currency": "USD",
            "applicant": "Applicant Co.",
            "beneficiary": "Beneficiary Co.",
            "ports": {
                "loading": "Chattogram Port",
                "discharge": "Jebel Ali Port",
            },
        },
        lc_subtype="letter_of_credit",
        raw_text=raw_text,
        source_type="letter_of_credit",
        lc_format="mt700",
    )

    assert lc_context["port_of_loading_country_name"] == "Bangladesh"
    assert lc_context["port_of_discharge_country_name"] == "United Arab Emirates"

    guess = detect_lc_type(
        lc_context,
        None,
        {
            "user_type": "exporter",
            "workflow_type": "export-lc-intake",
        },
    )

    assert guess["lc_type"] == "export"
    assert guess["confidence"] >= 0.52


def test_beneficiary_certificate_dispatch_uses_recoverable_text() -> None:
    pipeline_cls = _load_launch_supporting_pipeline()
    pipeline = pipeline_cls()

    beneficiary_text = """
    BENEFICIARY CERTIFICATE
    BENEFICIARY CERT REF: BC-022
    LC REF: 100924060096
    DOCUMENT SET DISPATCHED TO APPLICANT BY COURIER
    """.strip()

    result = asyncio.run(
        pipeline.process_document(
            extracted_text=beneficiary_text,
            document_type="beneficiary_certificate",
            filename="Beneficiary_Certificate.pdf",
            extraction_artifacts_v1={},
        )
    )

    assert result["handled"] is True
    assert result["support_only"] is True
    assert result["has_structured_data"] is False
    assert result["post_validation_target"] is None
    assert result["doc_info_patch"]["insurance_subtype"] == "beneficiary_certificate"
    assert result["doc_info_patch"]["extraction_status"] == "partial"
    assert result["context_payload"]["certificate_number"] == "BC-022"


def test_weight_list_dispatch_preserves_weight_target_and_extracts_values() -> None:
    pipeline_cls = _load_launch_supporting_pipeline()
    pipeline = pipeline_cls()

    weight_text = """
    WEIGHT LIST
    WEIGHT LIST REF: WL-022
    LC REF: 100924060096
    NET: 1073.15 KG
    GROSS: 1165.65 KG
    """.strip()

    result = asyncio.run(
        pipeline.process_document(
            extracted_text=weight_text,
            document_type="weight_list",
            filename="Weight_List.pdf",
            extraction_artifacts_v1={},
        )
    )

    assert result["handled"] is True
    assert result["support_only"] is True
    assert result["has_structured_data"] is False
    assert result["post_validation_target"] is None
    assert result["doc_info_patch"]["inspection_subtype"] == "weight_certificate"
    assert result["doc_info_patch"]["extraction_status"] == "partial"
    assert result["context_payload"]["gross_weight"] == "1165.65 KG"
    assert result["context_payload"]["net_weight"] == "1073.15 KG"


def test_weight_certificate_dispatch_stays_weight_certificate() -> None:
    pipeline_cls = _load_launch_supporting_pipeline()
    pipeline = pipeline_cls()

    weight_cert_text = """
    WEIGHT CERTIFICATE
    CERT NO: WC-022
    GROSS WEIGHT: 900 KG
    NET WEIGHT: 850 KG
    """.strip()

    result = asyncio.run(
        pipeline.process_document(
            extracted_text=weight_cert_text,
            document_type="weight_certificate",
            filename="Weight_Certificate.pdf",
            extraction_artifacts_v1={},
        )
    )

    assert result["handled"] is True
    assert result["support_only"] is True
    assert result["has_structured_data"] is False
    assert result["post_validation_target"] is None
    assert result["doc_info_patch"]["inspection_subtype"] == "weight_certificate"
    assert result["doc_info_patch"]["extraction_status"] == "partial"


def test_bank_guarantee_dispatch_uses_lc_like_boundary() -> None:
    pipeline_cls = _load_launch_supporting_pipeline()
    pipeline = pipeline_cls()

    guarantee_text = """
    BANK GUARANTEE
    GUARANTEE NUMBER: BG-022
    APPLICANT: XYZ Imports Ltd
    BENEFICIARY: ABC Exports Ltd
    GUARANTEE AMOUNT: USD 25000
    """.strip()

    result = asyncio.run(
        pipeline.process_document(
            extracted_text=guarantee_text,
            document_type="bank_guarantee",
            filename="Bank_Guarantee.pdf",
            extraction_artifacts_v1={},
        )
    )

    assert result["handled"] is True
    assert result["context_key"] == "lc"
    assert result["doc_info_patch"]["lc_subtype"] == "bank_guarantee"


def test_standby_lc_dispatch_uses_lc_like_boundary() -> None:
    pipeline_cls = _load_launch_supporting_pipeline()
    pipeline = pipeline_cls()

    standby_text = """
    STANDBY LETTER OF CREDIT
    LC NUMBER: SBLC-022
    APPLICANT: XYZ Imports Ltd
    BENEFICIARY: ABC Exports Ltd
    CREDIT AMOUNT: USD 18000
    """.strip()

    result = asyncio.run(
        pipeline.process_document(
            extracted_text=standby_text,
            document_type="standby_letter_of_credit",
            filename="SBLC.pdf",
            extraction_artifacts_v1={},
        )
    )

    assert result["handled"] is True
    assert result["context_key"] == "lc"
    assert result["doc_info_patch"]["lc_subtype"] == "standby_letter_of_credit"


def test_inspection_certificate_dispatch_extracts_plain_result_labels() -> None:
    pipeline_cls = _load_launch_supporting_pipeline()
    pipeline = pipeline_cls()

    inspection_text = """
    INSPECTION CERTIFICATE
    INSPECTION CERT NO: INSP-022
    DATE: 2026-03-08
    LC REF: 100924060096
    RESULT: SATISFACTORY
    """.strip()

    result = asyncio.run(
        pipeline.process_document(
            extracted_text=inspection_text,
            document_type="inspection_certificate",
            filename="Inspection_Certificate.pdf",
            extraction_artifacts_v1={},
        )
    )

    assert result["handled"] is True
    assert result["support_only"] is True
    assert result["has_structured_data"] is False
    assert result["post_validation_target"] is None
    assert result["doc_info_patch"]["inspection_subtype"] == "inspection_certificate"
    assert result["doc_info_patch"]["extraction_status"] == "partial"
    assert result["context_payload"]["inspection_result"] == "SATISFACTORY"


def test_invoice_regex_fallback_stays_support_only_until_confirmed() -> None:
    pipeline_cls = _load_launch_supporting_pipeline()
    pipeline = pipeline_cls()
    pipeline._fallback_extractor = types.SimpleNamespace(
        extract_fields=lambda *_args, **_kwargs: [
            types.SimpleNamespace(
                field_name="invoice_date",
                value="2026-03-08",
                raw_text="Invoice Date: 2026-03-08",
                confidence=0.84,
            ),
            types.SimpleNamespace(
                field_name="invoice_number",
                value="INV-022",
                raw_text="Invoice No: INV-022",
                confidence=0.79,
            ),
        ]
    )

    result = asyncio.run(
        pipeline.process_document(
            extracted_text="COMMERCIAL INVOICE\nInvoice Date: 2026-03-08\nInvoice No: INV-022",
            document_type="commercial_invoice",
            filename="Invoice.pdf",
            extraction_artifacts_v1={},
        )
    )

    assert result["handled"] is True
    assert result["support_only"] is True
    assert result["has_structured_data"] is False
    assert result["validation_doc_type"] is None
    assert result["post_validation_target"] is None
    assert result["doc_info_patch"]["extraction_status"] == "partial"
    assert result["doc_info_patch"]["extraction_method"] == "regex_support"
    assert result["doc_info_patch"]["extraction_lane"] == "support_only"
    assert result["doc_info_patch"]["field_details"]["invoice_date"]["verification"] == "support_only"
    assert result["context_payload"]["invoice_date"] == "2026-03-08"


def test_invoice_ai_success_does_not_backfill_missing_fields_from_raw_text() -> None:
    async def _no_multimodal(*_args: Any, **_kwargs: Any) -> None:
        return None

    async def _ai_invoice(*_args: Any, **_kwargs: Any) -> Dict[str, Any]:
        return {
            "_status": "success",
            "_extraction_method": "ai_first",
            "_field_details": {
                "invoice_number": {
                    "value": "INV-100",
                    "verification": "confirmed",
                    "confidence": 0.93,
                }
            },
            "invoice_number": "INV-100",
            "extracted_fields": {
                "invoice_number": "INV-100",
            },
        }

    pipeline_cls = _load_launch_supporting_pipeline(
        overrides={
            "extract_invoice_ai_first": _ai_invoice,
            "extract_document_multimodal_first": _no_multimodal,
        }
    )
    pipeline = pipeline_cls()

    result = asyncio.run(
        pipeline.process_document(
            extracted_text="COMMERCIAL INVOICE\nInvoice Number: INV-100\nCurrency: USD\nAmount: 5000\n",
            document_type="commercial_invoice",
            filename="Invoice.pdf",
            extraction_artifacts_v1={},
        )
    )

    assert result["handled"] is True
    assert result["has_structured_data"] is True
    assert result["validation_doc_type"] == "invoice"
    assert result["doc_info_patch"]["extraction_lane"] == "document_ai"
    assert result["context_payload"]["invoice_number"] == "INV-100"
    assert result["context_payload"].get("currency") in (None, "")
    assert result["context_payload"].get("amount") in (None, "")
    assert result["doc_info_patch"]["extracted_fields"] == {"invoice_number": "INV-100"}


def test_iso_lc_path_marks_structured_iso_lane() -> None:
    async def _iso_extract(*_args: Any, **_kwargs: Any) -> Dict[str, Any]:
        return {
            "_extraction_method": "iso20022_camtoai",
            "_extraction_confidence": 0.97,
            "number": "LC-ISO-022",
            "applicant": "Applicant Co.",
            "beneficiary": "Beneficiary Co.",
        }

    pipeline_cls = _load_launch_supporting_pipeline(
        overrides={
            "detect_lc_format": lambda _text: "iso20022",
            "extract_iso20022_with_ai_fallback": _iso_extract,
            "_build_lc_user_facing_extracted_fields": lambda payload: {
                "lc_number": payload.get("number"),
                "applicant": payload.get("applicant"),
                "beneficiary": payload.get("beneficiary"),
            },
        }
    )
    pipeline = pipeline_cls()

    result = asyncio.run(
        pipeline.process_document(
            extracted_text="<Document>ISO LC</Document>",
            document_type="letter_of_credit",
            filename="LC_ISO.xml",
            extraction_artifacts_v1={},
        )
    )

    assert result["handled"] is True
    assert result["has_structured_data"] is True
    assert result["doc_info_patch"]["extraction_method"] == "iso20022_camtoai"
    assert result["doc_info_patch"]["extraction_lane"] == "structured_iso"
    assert result["lc_number"] == "LC-ISO-022"
