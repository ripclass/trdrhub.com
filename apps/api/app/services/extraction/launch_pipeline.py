from __future__ import annotations

from datetime import date
import json
import logging
import re
from typing import Any, Dict, List, Optional

from app.reference_data import get_country_registry, get_currency_registry, get_port_registry
from app.rules.extractors import DocumentFieldExtractor
from app.rules.models import DocumentType
from app.services.document_intelligence.ocr_quality_gate import OCRQualityGate
from app.services.extraction.ai_first_extractor import (
    extract_bl_ai_first,
    extract_coo_ai_first,
    extract_inspection_ai_first,
    extract_insurance_ai_first,
    extract_invoice_ai_first,
    extract_lc_ai_first,
    extract_packing_list_ai_first,
)
from app.services.extraction.iso20022_lc_extractor import (
    detect_iso20022_schema,
    extract_iso20022_with_ai_fallback,
)
from app.services.extraction.lc_taxonomy import build_lc_classification
from app.services.extraction.multimodal_document_extractor import extract_document_multimodal_first
from app.services.facts import (
    build_bl_fact_set,
    build_coo_fact_set,
    build_insurance_fact_set,
    build_inspection_fact_set,
    build_invoice_fact_set,
    build_lc_fact_set,
    build_packing_list_fact_set,
    build_supporting_fact_set,
)

logger = logging.getLogger(__name__)


CANONICAL_DOCUMENT_ALIASES = {
    "lc": "letter_of_credit",
    "l/c": "letter_of_credit",
    "mt700": "letter_of_credit",
    "swift mt": "swift_message",
    "swift": "swift_message",
    "invoice": "commercial_invoice",
    "commercial invoice": "commercial_invoice",
    "proforma": "proforma_invoice",
    "proforma invoice": "proforma_invoice",
    "bill of exchange": "draft_bill_of_exchange",
    "draft bill of exchange": "draft_bill_of_exchange",
    "promissory note": "promissory_note",
    "payment receipt": "payment_receipt",
    "debit note": "debit_note",
    "credit note": "credit_note",
    "bill of lading": "bill_of_lading",
    "b/l": "bill_of_lading",
    "bl": "bill_of_lading",
    "sea waybill": "sea_waybill",
    "air waybill": "air_waybill",
    "awb": "air_waybill",
    "ocean bill of lading": "ocean_bill_of_lading",
    "charter party bill of lading": "charter_party_bill_of_lading",
    "courier receipt": "courier_or_post_receipt_or_certificate_of_posting",
    "certificate of posting": "courier_or_post_receipt_or_certificate_of_posting",
    "packing": "packing_list",
    "packing list": "packing_list",
    "certificate of origin": "certificate_of_origin",
    "coo": "certificate_of_origin",
    "insurance": "insurance_certificate",
    "insurance certificate": "insurance_certificate",
    "weight list": "weight_certificate",
    "weight certificate": "weight_certificate",
    "lab test report": "lab_test_report",
    "certificate of conformity": "certificate_of_conformity",
    "shipment advice": "shipment_advice",
    "delivery note": "delivery_note",
}

INSURANCE_FAMILY_DOCUMENT_SUBTYPES = {
    "insurance_certificate": "insurance_certificate",
    "insurance_policy": "insurance_policy",
    "beneficiary_certificate": "beneficiary_certificate",
    "beneficiary_statement": "beneficiary_certificate",
    "manufacturer_certificate": "manufacturer_certificate",
    "manufacturers_certificate": "manufacturers_certificate",
    "conformity_certificate": "conformity_certificate",
    "certificate_of_conformity": "certificate_of_conformity",
    "non_manipulation_certificate": "non_manipulation_certificate",
    "halal_certificate": "halal_certificate",
    "kosher_certificate": "kosher_certificate",
    "organic_certificate": "organic_certificate",
}

INSPECTION_FAMILY_DOCUMENT_SUBTYPES = {
    "inspection_certificate": "inspection_certificate",
    "pre_shipment_inspection": "pre_shipment_inspection",
    "quality_certificate": "quality_certificate",
    "weight_list": "weight_certificate",
    "weight_certificate": "weight_certificate",
    "measurement_certificate": "measurement_certificate",
    "analysis_certificate": "analysis_certificate",
    "lab_test_report": "lab_test_report",
    "sgs_certificate": "sgs_certificate",
    "bureau_veritas_certificate": "bureau_veritas_certificate",
    "intertek_certificate": "intertek_certificate",
}

PAYMENT_FAMILY_DOCUMENT_SUBTYPES = {
    "draft_bill_of_exchange": "bill_of_exchange",
    "bill_of_exchange": "bill_of_exchange",
    "promissory_note": "promissory_note",
    "payment_receipt": "payment_receipt",
    "debit_note": "debit_note",
    "credit_note": "credit_note",
}

GENERIC_SUPPORTING_DOCUMENT_SUBTYPES = {
    "shipment_advice",
    "delivery_note",
    "other_specified_document",
    "supporting_document",
}

REGULATORY_FAMILY_DOCUMENT_SUBTYPES = {
    "certificate_of_origin": "certificate_of_origin",
    "gsp_form_a": "gsp_form_a",
    "eur1_movement_certificate": "eur1_movement_certificate",
    "customs_declaration": "customs_declaration",
    "export_license": "export_license",
    "import_license": "import_license",
    "phytosanitary_certificate": "phytosanitary_certificate",
    "fumigation_certificate": "fumigation_certificate",
    "health_certificate": "health_certificate",
    "veterinary_certificate": "veterinary_certificate",
    "sanitary_certificate": "sanitary_certificate",
    "cites_permit": "cites_permit",
    "radiation_certificate": "radiation_certificate",
}

MEASUREMENT_LABEL_ALIASES = {
    "gross": "gross_weight",
    "gross wt": "gross_weight",
    "gross weight": "gross_weight",
    "gr wt": "gross_weight",
    "g/w": "gross_weight",
    "net": "net_weight",
    "net wt": "net_weight",
    "net weight": "net_weight",
    "n/w": "net_weight",
    "measurements": "measurement_value",
    "measurement": "measurement_value",
    "dimensions": "measurement_value",
    "dimension": "measurement_value",
    "size": "measurement_value",
}


_SWIFT_MT_TAG_RE = re.compile(r":20:|:32B:|:40A:|:50:|:59:|:46A:|:47A:")


def _looks_like_swift_mt700(text: Optional[str]) -> bool:
    """Heuristic: does this text look like raw SWIFT MT700 format?

    Returns True only when we see multiple distinct MT700 colon-tag markers,
    because a single match could be accidental.
    """
    if not text or not isinstance(text, str):
        return False
    matches = _SWIFT_MT_TAG_RE.findall(text)
    return len(set(matches)) >= 2


def _extract_pdf_text_fast(file_bytes: Optional[bytes]) -> str:
    """Pull raw text out of a PDF using pdfminer.six (free, instant).

    Returns "" on any failure (non-PDF input, parser error, encrypted file).
    Used to give the vision LLM both the page images AND the actual text
    content — character-perfect text is more reliable than reading text
    out of a JPEG.
    """
    if not file_bytes:
        return ""
    try:
        from io import BytesIO
        from pdfminer.high_level import extract_text
        text = extract_text(BytesIO(file_bytes)) or ""
        return text.strip()
    except Exception:
        try:
            # Fallback: PyPDF2 (less accurate but more permissive on weird PDFs).
            from io import BytesIO
            from PyPDF2 import PdfReader  # type: ignore
            reader = PdfReader(BytesIO(file_bytes))
            chunks = []
            for page in reader.pages[:20]:
                chunk = page.extract_text() or ""
                if chunk.strip():
                    chunks.append(chunk)
            return "\n".join(chunks).strip()
        except Exception:
            return ""


def _build_lc_cross_doc_context(lc_context: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Pull the LC fields a supporting-doc extractor would want to cross-reference.

    Returned as a flat dict with canonical key names. Used as the
    `cross_doc_context` arg to extract_document_multimodal_first when
    extracting invoice / BL / packing / COO / etc.
    """
    if not isinstance(lc_context, dict) or not lc_context:
        return None
    out: Dict[str, Any] = {}
    for key in (
        "lc_number",
        "amount",
        "currency",
        "applicant",
        "beneficiary",
        "port_of_loading",
        "port_of_discharge",
        "latest_shipment_date",
        "expiry_date",
        "buyer_purchase_order_number",
        "exporter_bin",
        "exporter_tin",
        "goods_description",
    ):
        value = lc_context.get(key)
        if value not in (None, ""):
            out[key] = value
    return out or None


def _resolve_extraction_lane(*, extraction_method: Optional[str], support_only: bool = False) -> str:
    if support_only:
        return "support_only"
    method = str(extraction_method or "").strip().lower()
    if method.startswith("iso20022"):
        return "structured_iso"
    if method.startswith("mt700_structured"):
        return "structured_mt"
    if "ai" in method or "multimodal" in method:
        return "document_ai"
    if method in {"regex_support", "raw_text_support"}:
        return "support_only"
    return "unknown"


class LaunchExtractionPipeline:
    """Thin launch-focused extraction boundary.

    v1 scope:
    - LC-like docs
    - invoices
    - bill of lading

    This service does NOT run final business validation.
    It only:
    1) assesses text quality
    2) dispatches doc-type extraction
    3) applies narrow regex fallback
    4) returns normalized extraction payload
    """

    def __init__(self) -> None:
        self._quality_gate = OCRQualityGate()
        self._fallback_extractor = DocumentFieldExtractor()

    async def process_document(
        self,
        *,
        extracted_text: str,
        document_type: str,
        filename: str,
        extraction_artifacts_v1: Optional[Dict[str, Any]] = None,
        file_bytes: Optional[bytes] = None,
        content_type: Optional[str] = None,
        lc_context_for_cross_doc: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        extraction_artifacts_v1 = extraction_artifacts_v1 or {}
        normalized_doc_type = _canonicalize_launch_doc_type(str(document_type or "").strip().lower())
        quality_assessment = self._quality_gate.assess(
            extracted_text or "",
            ocr_confidence=extraction_artifacts_v1.get("ocr_confidence"),
            metadata=extraction_artifacts_v1,
        )
        # Build the LC cross-reference context once per document. The vision
        # LLM uses this to resolve fields like lc_number / buyer_purchase_order_number
        # that appear on every supporting doc. The LC itself never gets a
        # cross_doc context (it IS the source of truth).
        cross_doc_context = (
            None
            if normalized_doc_type in {
                "letter_of_credit",
                "swift_message",
                "lc_application",
                "bank_guarantee",
                "standby_letter_of_credit",
            }
            else _build_lc_cross_doc_context(lc_context_for_cross_doc)
        )
        # Stash on the instance so the per-doc processors can read it
        # without us threading the arg through every signature. Only valid
        # for the duration of this single dispatch call.
        self._current_cross_doc_context = cross_doc_context
        self._current_pdf_text = _extract_pdf_text_fast(file_bytes)

        if normalized_doc_type in {
            "letter_of_credit",
            "swift_message",
            "lc_application",
            "bank_guarantee",
            "standby_letter_of_credit",
        }:
            return await self._process_lc_like(
                extracted_text=extracted_text,
                document_type=normalized_doc_type,
                filename=filename,
                quality_assessment=quality_assessment,
                file_bytes=file_bytes,
                content_type=content_type,
            )

        if normalized_doc_type in {"commercial_invoice", "proforma_invoice"}:
            return await self._process_invoice(
                extracted_text=extracted_text,
                filename=filename,
                quality_assessment=quality_assessment,
                document_type=normalized_doc_type,
                file_bytes=file_bytes,
                content_type=content_type,
            )

        if normalized_doc_type in PAYMENT_FAMILY_DOCUMENT_SUBTYPES:
            return await self._process_invoice(
                extracted_text=extracted_text,
                filename=filename,
                quality_assessment=quality_assessment,
                document_type=normalized_doc_type,
                file_bytes=file_bytes,
                content_type=content_type,
                forced_subtype=PAYMENT_FAMILY_DOCUMENT_SUBTYPES[normalized_doc_type],
                post_validation_target=normalized_doc_type,
            )

        if normalized_doc_type in TRANSPORT_DOC_ALIASES:
            return await self._process_bl(
                extracted_text=extracted_text,
                filename=filename,
                quality_assessment=quality_assessment,
                document_type=normalized_doc_type,
                file_bytes=file_bytes,
                content_type=content_type,
                forced_subtype=(
                    None
                    if normalized_doc_type == "bill_of_lading"
                    else normalized_doc_type
                ),
                post_validation_target=normalized_doc_type,
            )

        if normalized_doc_type == "packing_list":
            return await self._process_packing_list(
                extracted_text=extracted_text,
                filename=filename,
                quality_assessment=quality_assessment,
                document_type=normalized_doc_type,
                file_bytes=file_bytes,
                content_type=content_type,
            )

        if normalized_doc_type in REGULATORY_FAMILY_DOCUMENT_SUBTYPES:
            return await self._process_certificate_of_origin(
                extracted_text=extracted_text,
                filename=filename,
                quality_assessment=quality_assessment,
                document_type=normalized_doc_type,
                file_bytes=file_bytes,
                content_type=content_type,
                forced_subtype=(
                    None
                    if normalized_doc_type == "certificate_of_origin"
                    else REGULATORY_FAMILY_DOCUMENT_SUBTYPES[normalized_doc_type]
                ),
                post_validation_target=normalized_doc_type,
            )

        if normalized_doc_type in INSURANCE_FAMILY_DOCUMENT_SUBTYPES:
            return await self._process_insurance_certificate(
                extracted_text=extracted_text,
                filename=filename,
                quality_assessment=quality_assessment,
                document_type=normalized_doc_type,
                file_bytes=file_bytes,
                content_type=content_type,
                forced_subtype=(
                    None
                    if normalized_doc_type == "insurance_certificate"
                    else INSURANCE_FAMILY_DOCUMENT_SUBTYPES[normalized_doc_type]
                ),
                post_validation_target=(
                    "beneficiary_certificate"
                    if normalized_doc_type in {"beneficiary_certificate", "beneficiary_statement"}
                    else normalized_doc_type
                ),
            )

        if normalized_doc_type in INSPECTION_FAMILY_DOCUMENT_SUBTYPES:
            return await self._process_inspection_certificate(
                extracted_text=extracted_text,
                filename=filename,
                quality_assessment=quality_assessment,
                document_type=normalized_doc_type,
                file_bytes=file_bytes,
                content_type=content_type,
                forced_subtype=(
                    None
                    if normalized_doc_type == "inspection_certificate"
                    else INSPECTION_FAMILY_DOCUMENT_SUBTYPES[normalized_doc_type]
                ),
                post_validation_target=normalized_doc_type,
            )

        if normalized_doc_type in GENERIC_SUPPORTING_DOCUMENT_SUBTYPES:
            return await self._process_supporting_document(
                extracted_text=extracted_text,
                filename=filename,
                quality_assessment=quality_assessment,
                document_type=normalized_doc_type,
                file_bytes=file_bytes,
                content_type=content_type,
            )

        return {"handled": False}

    async def _process_lc_like(self, *, extracted_text: str, document_type: str, filename: str, quality_assessment: Any, file_bytes: Optional[bytes] = None, content_type: Optional[str] = None) -> Dict[str, Any]:
        lc_format = detect_lc_format(extracted_text)
        lc_subtype = _detect_lc_financial_subtype(filename=filename, document_type=document_type, extracted_text=extracted_text)
        base_patch = {
            "ocr_quality": {
                "overall_score": quality_assessment.overall_score,
                "quality_level": quality_assessment.quality_level.value,
                "can_proceed": quality_assessment.can_proceed,
                "warnings": quality_assessment.warnings,
                "recommendations": quality_assessment.recommendations,
            },
            "review_reasons": list(quality_assessment.warnings or []),
        }

        try:
            if lc_format == "iso20022":
                iso_context = await extract_iso20022_with_ai_fallback(extracted_text, ai_threshold=0.5)
                user_facing_fields = _build_lc_user_facing_extracted_fields(iso_context)
                return {
                    "handled": True,
                    "context_key": "lc",
                    "context_payload": {
                        **iso_context,
                        "raw_text": extracted_text,
                        "source_type": document_type,
                        "format": lc_format,
                    },
                    "doc_info_patch": {
                        **base_patch,
                        "extracted_fields": user_facing_fields or iso_context,
                        "extraction_status": "success",
                        "extraction_method": iso_context.get("_extraction_method", "iso20022"),
                        "extraction_lane": _resolve_extraction_lane(
                            extraction_method=iso_context.get("_extraction_method", "iso20022"),
                        ),
                        "extraction_confidence": iso_context.get("_extraction_confidence", 0.0),
                    },
                    "has_structured_data": True,
                    "lc_number": iso_context.get("number"),
                    "validation_doc_type": None,
                    "post_validation_target": None,
                }

            # Pull raw PDF text via pdfminer so the vision LLM has BOTH the
            # rendered page images AND the actual text characters. Empty
            # string when extraction fails (image-only PDF, encrypted, etc.).
            pdf_text_for_vision = _extract_pdf_text_fast(file_bytes) or extracted_text
            multimodal_struct = await extract_document_multimodal_first(
                document_type=document_type,
                filename=filename,
                file_bytes=file_bytes,
                content_type=content_type,
                extracted_text=pdf_text_for_vision,
                subtype_hint=lc_subtype,
            )

            # If vision failed AND the extracted text looks like raw SWIFT
            # MT700 (has at least the :20: credit number tag), run the
            # deterministic MT700 regex parser before falling back to the
            # text-AI extractor. This gives us full MT700 field coverage
            # (17 mandatory + 8 optional fields) on plaintext LCs, where
            # the vision LLM can't render pages.
            if not multimodal_struct and _looks_like_swift_mt700(extracted_text):
                try:
                    from app.services.extraction.swift_mt700_full import (
                        parse_mt700_full as _parse_mt700_full,
                    )
                    from app.services.extraction.lc_document import LCDocument as _LCDocument
                    _swift_parsed = _parse_mt700_full(extracted_text)
                    _swift_lc = _LCDocument.from_swift_mt700_full(_swift_parsed)
                    if _swift_lc.lc_number:  # parser found a real LC number
                        multimodal_struct = _swift_lc.to_lc_context()
                        multimodal_struct["_extraction_method"] = "swift_mt700_full"
                        multimodal_struct["_status"] = "success"
                        logger.info(
                            "Launch pipeline: swift_mt700_full fallback extracted LC %s from %s",
                            _swift_lc.lc_number, filename,
                        )
                except Exception as _swift_exc:  # noqa: BLE001
                    logger.warning(
                        "swift_mt700_full fallback failed for %s: %s",
                        filename, _swift_exc, exc_info=False,
                    )

            lc_struct = multimodal_struct or await extract_lc_ai_first(extracted_text)
            extraction_status = lc_struct.get("_status", "unknown") if isinstance(lc_struct, dict) else "unknown"
            if lc_struct and extraction_status != "failed":
                extraction_method = lc_struct.get("_extraction_method", "unknown")
                extraction_lane = _resolve_extraction_lane(
                    extraction_method=extraction_method,
                )
                shaped_payload = _shape_lc_financial_payload(
                    lc_struct,
                    lc_subtype=lc_subtype,
                    raw_text=extracted_text,
                    source_type=document_type,
                    lc_format=lc_format,
                    allow_text_backfill=False,
                )
                # Run the shaped payload through the canonical LCDocument
                # model so the downstream context has consistent MT700-aligned
                # key names regardless of which extractor produced it. This
                # is non-destructive — we only ADD canonical aliases that
                # weren't already present, never overwrite.
                try:
                    from app.services.extraction.lc_document import LCDocument as _LCDocument
                    canonical_lc = _LCDocument.from_legacy_dict(shaped_payload)
                    canonical_keys = canonical_lc.to_lc_context()
                    for _k, _v in canonical_keys.items():
                        shaped_payload.setdefault(_k, _v)
                    shaped_payload["_canonical_lc_document"] = canonical_lc.model_dump(exclude_none=True)
                except Exception as _canonical_exc:  # noqa: BLE001 — never break extraction over normalization
                    logger.warning(
                        "LCDocument canonicalization failed for %s: %s",
                        filename, _canonical_exc, exc_info=False,
                    )
                lc_review = _assess_lc_financial_completeness(shaped_payload, lc_subtype=lc_subtype)
                user_facing_fields = _build_lc_user_facing_extracted_fields(shaped_payload)
                fact_graph_v1 = (
                    build_lc_fact_set(
                        {
                            **shaped_payload,
                            "document_type": document_type,
                            "lc_subtype": lc_subtype,
                            "extraction_lane": extraction_lane,
                            "extraction_method": extraction_method,
                            "extracted_fields": user_facing_fields,
                            "field_details": lc_struct.get("_field_details"),
                        }
                    )
                    if extraction_lane == "document_ai"
                    else None
                )
                return {
                    "handled": True,
                    "context_key": "lc",
                    "context_payload": {
                        **shaped_payload,
                        "lc_review": lc_review,
                        **({"fact_graph_v1": fact_graph_v1} if isinstance(fact_graph_v1, dict) else {}),
                    },
                    "doc_info_patch": {
                        **base_patch,
                        "lc_subtype": lc_subtype,
                        "lc_family": shaped_payload.get("lc_family"),
                        "extracted_fields": user_facing_fields or (lc_struct.get("extracted_fields") if isinstance(lc_struct.get("extracted_fields"), dict) else lc_struct),
                        "extraction_status": "success" if lc_review.get("parse_complete") else "partial",
                        "extraction_method": extraction_method,
                        "extraction_lane": extraction_lane,
                        "extraction_confidence": lc_struct.get("_extraction_confidence", 0.0),
                        "ai_first_status": extraction_status,
                        "field_details": lc_struct.get("_field_details"),
                        "status_counts": lc_struct.get("_status_counts"),
                        "parse_complete": lc_review.get("parse_complete"),
                        "parse_completeness": lc_review.get("required_ratio"),
                        "missing_required_fields": lc_review.get("missing_required_fields", []),
                        "required_fields_found": lc_review.get("required_found"),
                        "required_fields_total": lc_review.get("required_total"),
                        "review_reasons": list(base_patch.get("review_reasons") or []) + list(lc_review.get("review_reasons") or []),
                        **({"fact_graph_v1": fact_graph_v1} if isinstance(fact_graph_v1, dict) else {}),
                    },
                    "has_structured_data": True,
                    "lc_number": (
                        shaped_payload.get("number")
                        or shaped_payload.get("lc_number")
                        or shaped_payload.get("reference")
                    ),
                    "validation_doc_type": "lc",
                    "post_validation_target": "lc",
                }
        except Exception as exc:
            logger.warning("Launch pipeline LC AI extraction failed for %s: %s", filename, exc, exc_info=True)

        try:
            lc_fields = self._fallback_extractor.extract_fields(extracted_text, DocumentType.LETTER_OF_CREDIT)
            lc_context = _fields_to_lc_context(lc_fields)
            if lc_context:
                shaped_payload = _shape_lc_financial_payload(lc_context, lc_subtype=lc_subtype, raw_text=extracted_text, source_type=document_type, lc_format=lc_format)
                lc_review = _assess_lc_financial_completeness(shaped_payload, lc_subtype=lc_subtype)
                return _build_support_only_result(
                    context_key="lc",
                    context_payload={**shaped_payload, "lc_review": lc_review},
                    base_patch=base_patch,
                    extraction_method="regex_support",
                    field_details=lc_context.get("_field_details"),
                    review_payload=lc_review,
                    extra_doc_info={
                        "lc_subtype": lc_subtype,
                        "lc_family": shaped_payload.get("lc_family"),
                    },
                    lc_number=shaped_payload.get("number") or shaped_payload.get("lc_number"),
                )
        except Exception as exc:
            logger.warning("Launch pipeline LC regex fallback failed for %s: %s", filename, exc, exc_info=True)

        shaped_payload = _shape_lc_financial_payload({}, lc_subtype=lc_subtype, raw_text=extracted_text, source_type=document_type, lc_format=lc_format)
        lc_review = _assess_lc_financial_completeness(shaped_payload, lc_subtype=lc_subtype)
        return {
            "handled": True,
            "context_key": "lc",
            "context_payload": {**shaped_payload, "lc_review": lc_review},
            "doc_info_patch": {
                **base_patch,
                "lc_subtype": lc_subtype,
                "lc_family": shaped_payload.get("lc_family"),
                "parse_complete": lc_review.get("parse_complete"),
                "parse_completeness": lc_review.get("required_ratio"),
                "missing_required_fields": lc_review.get("missing_required_fields", []),
                "required_fields_found": lc_review.get("required_found"),
                "required_fields_total": lc_review.get("required_total"),
                "review_reasons": list(base_patch.get("review_reasons") or []) + list(lc_review.get("review_reasons") or []),
                "extraction_status": "failed",
                "extraction_error": "launch_pipeline_lc_extraction_failed",
            },
            "has_structured_data": False,
            "validation_doc_type": None,
            "post_validation_target": None,
        }

    async def _process_invoice(
        self,
        *,
        extracted_text: str,
        filename: str,
        quality_assessment: Any,
        document_type: str,
        file_bytes: Optional[bytes] = None,
        content_type: Optional[str] = None,
        forced_subtype: Optional[str] = None,
        post_validation_target: str = "invoice",
    ) -> Dict[str, Any]:
        invoice_subtype = forced_subtype or _detect_invoice_financial_subtype(filename=filename, extracted_text=extracted_text)
        base_patch = {
            "ocr_quality": {
                "overall_score": quality_assessment.overall_score,
                "quality_level": quality_assessment.quality_level.value,
                "can_proceed": quality_assessment.can_proceed,
                "warnings": quality_assessment.warnings,
                "recommendations": quality_assessment.recommendations,
            },
            "review_reasons": list(quality_assessment.warnings or []),
        }
        try:
            # Vision LLM looks at raw PDF page images first (no OCR text input).
            # The text-based AI extractor below is the fallback when vision fails.
            multimodal_struct = await extract_document_multimodal_first(
                document_type=document_type,
                filename=filename,
                file_bytes=file_bytes,
                content_type=content_type,
                extracted_text=getattr(self, "_current_pdf_text", "") or extracted_text,
                subtype_hint=invoice_subtype,
                cross_doc_context=getattr(self, "_current_cross_doc_context", None),
            )
            invoice_struct = multimodal_struct or await extract_invoice_ai_first(extracted_text)
            extraction_status = invoice_struct.get("_status", "unknown")
            if invoice_struct and extraction_status != "failed":
                shaped_payload = _shape_invoice_financial_payload(
                    invoice_struct,
                    invoice_subtype=invoice_subtype,
                    raw_text=extracted_text,
                    allow_text_backfill=False,
                )
                invoice_review = _assess_invoice_financial_completeness(shaped_payload, invoice_subtype=invoice_subtype)
                extracted_fields = (
                    invoice_struct.get("extracted_fields")
                    if isinstance(invoice_struct.get("extracted_fields"), dict)
                    else invoice_struct
                )
                extraction_lane = _resolve_extraction_lane(
                    extraction_method=invoice_struct.get("_extraction_method", "unknown"),
                )
                fact_graph_v1 = build_invoice_fact_set(
                    {
                        **{
                            key: value
                            for key, value in invoice_struct.items()
                            if not str(key).startswith("_")
                        },
                        **{
                            key: value
                            for key, value in shaped_payload.items()
                            if not str(key).startswith("_")
                        },
                        "document_type": document_type,
                        "invoice_subtype": invoice_subtype,
                        "extracted_fields": extracted_fields if isinstance(extracted_fields, dict) else {},
                        "field_details": invoice_struct.get("_field_details") if isinstance(invoice_struct.get("_field_details"), dict) else {},
                        "raw_text": extracted_text,
                        "extraction_method": invoice_struct.get("_extraction_method", "unknown"),
                        "extraction_lane": extraction_lane,
                    }
                )
                return {
                    "handled": True,
                    "context_key": "invoice",
                    "context_payload": {**shaped_payload, "invoice_review": invoice_review, "fact_graph_v1": fact_graph_v1},
                    "doc_info_patch": {
                        **base_patch,
                        "invoice_subtype": invoice_subtype,
                        "invoice_family": shaped_payload.get("invoice_family"),
                        "extracted_fields": extracted_fields if isinstance(extracted_fields, dict) else invoice_struct,
                        "extraction_status": "success" if invoice_review.get("parse_complete") else "partial",
                        "extraction_method": invoice_struct.get("_extraction_method", "unknown"),
                        "extraction_lane": extraction_lane,
                        "extraction_confidence": invoice_struct.get("_extraction_confidence", 0.0),
                        "ai_first_status": extraction_status,
                        "field_details": invoice_struct.get("_field_details"),
                        "fact_graph_v1": fact_graph_v1,
                        "status_counts": invoice_struct.get("_status_counts"),
                        "parse_complete": invoice_review.get("parse_complete"),
                        "parse_completeness": invoice_review.get("required_ratio"),
                        "missing_required_fields": invoice_review.get("missing_required_fields", []),
                        "required_fields_found": invoice_review.get("required_found"),
                        "required_fields_total": invoice_review.get("required_total"),
                        "review_reasons": list(base_patch.get("review_reasons") or []) + list(invoice_review.get("review_reasons") or []),
                    },
                    "has_structured_data": True,
                    "validation_doc_type": "invoice",
                    "post_validation_target": post_validation_target,
                }
        except Exception as exc:
            logger.warning("Launch pipeline invoice AI extraction failed for %s: %s", filename, exc, exc_info=True)

        try:
            invoice_fields = self._fallback_extractor.extract_fields(extracted_text, DocumentType.COMMERCIAL_INVOICE)
            invoice_context = _fields_to_flat_context(invoice_fields)
            if invoice_context:
                shaped_payload = _shape_invoice_financial_payload(invoice_context, invoice_subtype=invoice_subtype, raw_text=extracted_text)
                invoice_review = _assess_invoice_financial_completeness(shaped_payload, invoice_subtype=invoice_subtype)
                fact_graph_v1 = build_invoice_fact_set(
                    {
                        **{
                            key: value
                            for key, value in invoice_context.items()
                            if not str(key).startswith("_")
                        },
                        **{
                            key: value
                            for key, value in shaped_payload.items()
                            if not str(key).startswith("_")
                        },
                        "document_type": document_type,
                        "invoice_subtype": invoice_subtype,
                        "extracted_fields": {
                            key: value
                            for key, value in {
                                **invoice_context,
                                **shaped_payload,
                            }.items()
                            if not str(key).startswith("_")
                        },
                        "field_details": invoice_context.get("_field_details") if isinstance(invoice_context.get("_field_details"), dict) else {},
                        "raw_text": extracted_text,
                        "extraction_method": "regex_support",
                        "extraction_lane": "support_only",
                    }
                )
                result = _build_support_only_result(
                    context_key="invoice",
                    context_payload={**shaped_payload, "invoice_review": invoice_review},
                    base_patch=base_patch,
                    extraction_method="regex_support",
                    field_details=invoice_context.get("_field_details"),
                    review_payload=invoice_review,
                    extra_doc_info={
                        "invoice_subtype": invoice_subtype,
                        "invoice_family": shaped_payload.get("invoice_family"),
                    },
                )
                result["context_payload"]["fact_graph_v1"] = fact_graph_v1
                result["doc_info_patch"]["fact_graph_v1"] = fact_graph_v1
                return result
        except Exception as exc:
            logger.warning("Launch pipeline invoice regex fallback failed for %s: %s", filename, exc, exc_info=True)

        shaped_payload = _shape_invoice_financial_payload({}, invoice_subtype=invoice_subtype, raw_text=extracted_text)
        invoice_review = _assess_invoice_financial_completeness(shaped_payload, invoice_subtype=invoice_subtype)
        fact_graph_v1 = build_invoice_fact_set(
            {
                **{
                    key: value
                    for key, value in shaped_payload.items()
                    if not str(key).startswith("_")
                },
                "document_type": document_type,
                "invoice_subtype": invoice_subtype,
                "extracted_fields": {
                    key: value
                    for key, value in shaped_payload.items()
                    if not str(key).startswith("_")
                },
                "field_details": {},
                "raw_text": extracted_text,
                "extraction_method": "launch_pipeline_invoice_extraction_failed",
                "extraction_lane": "unknown",
            }
        )
        return {"handled": True, "context_key": "invoice", "context_payload": {**shaped_payload, "invoice_review": invoice_review, "fact_graph_v1": fact_graph_v1}, "doc_info_patch": {**base_patch, "invoice_subtype": invoice_subtype, "invoice_family": shaped_payload.get("invoice_family"), "fact_graph_v1": fact_graph_v1, "parse_complete": invoice_review.get("parse_complete"), "parse_completeness": invoice_review.get("required_ratio"), "missing_required_fields": invoice_review.get("missing_required_fields", []), "required_fields_found": invoice_review.get("required_found"), "required_fields_total": invoice_review.get("required_total"), "review_reasons": list(base_patch.get("review_reasons") or []) + list(invoice_review.get("review_reasons") or []), "extraction_status": "failed", "extraction_error": "launch_pipeline_invoice_extraction_failed"}, "has_structured_data": False, "validation_doc_type": None, "post_validation_target": None}

    async def _process_bl(
        self,
        *,
        extracted_text: str,
        filename: str,
        quality_assessment: Any,
        document_type: str,
        file_bytes: Optional[bytes] = None,
        content_type: Optional[str] = None,
        forced_subtype: Optional[str] = None,
        post_validation_target: str = "bill_of_lading",
    ) -> Dict[str, Any]:
        transport_subtype = forced_subtype or _detect_transport_subtype(filename=filename, extracted_text=extracted_text)
        base_patch = {
            "ocr_quality": {
                "overall_score": quality_assessment.overall_score,
                "quality_level": quality_assessment.quality_level.value,
                "can_proceed": quality_assessment.can_proceed,
                "warnings": quality_assessment.warnings,
                "recommendations": quality_assessment.recommendations,
            },
            "review_reasons": list(quality_assessment.warnings or []),
        }
        try:
            # Vision LLM looks at raw PDF page images first (no OCR text input).
            # The text-based AI extractor below is the fallback when vision fails.
            multimodal_struct = await extract_document_multimodal_first(
                document_type=document_type,
                filename=filename,
                file_bytes=file_bytes,
                content_type=content_type,
                extracted_text=getattr(self, "_current_pdf_text", "") or extracted_text,
                subtype_hint=transport_subtype,
                cross_doc_context=getattr(self, "_current_cross_doc_context", None),
            )
            bl_struct = multimodal_struct or await extract_bl_ai_first(extracted_text)
            extraction_status = bl_struct.get("_status", "unknown")
            if bl_struct and extraction_status != "failed":
                shaped_payload = _shape_transport_payload(
                    bl_struct,
                    transport_subtype=transport_subtype,
                    raw_text=extracted_text,
                    allow_text_backfill=False,
                )
                transport_review = _assess_transport_completeness(shaped_payload, transport_subtype=transport_subtype)
                fact_graph_v1 = build_bl_fact_set(
                    {
                        **{
                            key: value
                            for key, value in shaped_payload.items()
                            if not str(key).startswith("_")
                        },
                        "document_type": document_type,
                        "transport_subtype": transport_subtype,
                        "extracted_fields": bl_struct.get("extracted_fields") if isinstance(bl_struct.get("extracted_fields"), dict) else bl_struct,
                        "field_details": bl_struct.get("_field_details") if isinstance(bl_struct.get("_field_details"), dict) else {},
                        "raw_text": extracted_text,
                        "extraction_method": bl_struct.get("_extraction_method", "unknown"),
                        "extraction_lane": _resolve_extraction_lane(
                            extraction_method=bl_struct.get("_extraction_method", "unknown"),
                        ),
                    }
                )
                return {
                    "handled": True,
                    "context_key": "bill_of_lading",
                    "context_payload": {**shaped_payload, "transport_review": transport_review, "fact_graph_v1": fact_graph_v1},
                    "doc_info_patch": {
                        **base_patch,
                        "transport_subtype": transport_subtype,
                        "fact_graph_v1": fact_graph_v1,
                        "extracted_fields": bl_struct.get("extracted_fields") if isinstance(bl_struct.get("extracted_fields"), dict) else bl_struct,
                        "extraction_status": "success" if transport_review.get("parse_complete") else "partial",
                        "extraction_method": bl_struct.get("_extraction_method", "unknown"),
                        "extraction_lane": _resolve_extraction_lane(
                            extraction_method=bl_struct.get("_extraction_method", "unknown"),
                        ),
                        "extraction_confidence": bl_struct.get("_extraction_confidence", 0.0),
                        "ai_first_status": extraction_status,
                        "field_details": bl_struct.get("_field_details"),
                        "status_counts": bl_struct.get("_status_counts"),
                        "transport_family": shaped_payload.get("transport_family"),
                        "transport_mode": shaped_payload.get("transport_mode"),
                        "parse_complete": transport_review.get("parse_complete"),
                        "parse_completeness": transport_review.get("required_ratio"),
                        "missing_required_fields": transport_review.get("missing_required_fields", []),
                        "required_fields_found": transport_review.get("required_found"),
                        "required_fields_total": transport_review.get("required_total"),
                        "review_reasons": list(base_patch.get("review_reasons") or []) + list(transport_review.get("review_reasons") or []),
                    },
                    "has_structured_data": True,
                    "validation_doc_type": "bl",
                    "post_validation_target": post_validation_target,
                }
        except Exception as exc:
            logger.warning("Launch pipeline BL AI extraction failed for %s: %s", filename, exc, exc_info=True)

        try:
            bl_fields = self._fallback_extractor.extract_fields(extracted_text, DocumentType.BILL_OF_LADING)
            bl_context = _fields_to_flat_context(bl_fields)
            if bl_context:
                shaped_payload = _shape_transport_payload(bl_context, transport_subtype=transport_subtype, raw_text=extracted_text)
                transport_review = _assess_transport_completeness(shaped_payload, transport_subtype=transport_subtype)
                fact_graph_v1 = build_bl_fact_set(
                    {
                        **{
                            key: value
                            for key, value in shaped_payload.items()
                            if not str(key).startswith("_")
                        },
                        "document_type": document_type,
                        "transport_subtype": transport_subtype,
                        "extracted_fields": {
                            key: value
                            for key, value in {
                                **bl_context,
                                **shaped_payload,
                            }.items()
                            if not str(key).startswith("_")
                        },
                        "field_details": bl_context.get("_field_details") if isinstance(bl_context.get("_field_details"), dict) else {},
                        "raw_text": extracted_text,
                        "extraction_method": "regex_support",
                        "extraction_lane": "support_only",
                    }
                )
                result = _build_support_only_result(
                    context_key="bill_of_lading",
                    context_payload={**shaped_payload, "transport_review": transport_review},
                    base_patch=base_patch,
                    extraction_method="regex_support",
                    field_details=bl_context.get("_field_details"),
                    review_payload=transport_review,
                    extra_doc_info={
                        "transport_subtype": transport_subtype,
                        "transport_family": shaped_payload.get("transport_family"),
                        "transport_mode": shaped_payload.get("transport_mode"),
                    },
                )
                result["context_payload"]["fact_graph_v1"] = fact_graph_v1
                result["doc_info_patch"]["fact_graph_v1"] = fact_graph_v1
                return result
        except Exception as exc:
            logger.warning("Launch pipeline BL regex fallback failed for %s: %s", filename, exc, exc_info=True)

        shaped_payload = _shape_transport_payload({}, transport_subtype=transport_subtype, raw_text=extracted_text)
        transport_review = _assess_transport_completeness(shaped_payload, transport_subtype=transport_subtype)
        fact_graph_v1 = build_bl_fact_set(
            {
                **{
                    key: value
                    for key, value in shaped_payload.items()
                    if not str(key).startswith("_")
                },
                "document_type": document_type,
                "transport_subtype": transport_subtype,
                "extracted_fields": {
                    key: value
                    for key, value in shaped_payload.items()
                    if not str(key).startswith("_")
                },
                "field_details": {},
                "raw_text": extracted_text,
                "extraction_method": "launch_pipeline_bl_extraction_failed",
                "extraction_lane": "unknown",
            }
        )
        return {"handled": True, "context_key": "bill_of_lading", "context_payload": {**shaped_payload, "transport_review": transport_review, "fact_graph_v1": fact_graph_v1}, "doc_info_patch": {**base_patch, "transport_subtype": transport_subtype, "transport_family": shaped_payload.get("transport_family"), "transport_mode": shaped_payload.get("transport_mode"), "fact_graph_v1": fact_graph_v1, "parse_complete": transport_review.get("parse_complete"), "parse_completeness": transport_review.get("required_ratio"), "missing_required_fields": transport_review.get("missing_required_fields", []), "required_fields_found": transport_review.get("required_found"), "required_fields_total": transport_review.get("required_total"), "review_reasons": list(base_patch.get("review_reasons") or []) + list(transport_review.get("review_reasons") or []), "extraction_status": "failed", "extraction_error": "launch_pipeline_bl_extraction_failed"}, "has_structured_data": False, "validation_doc_type": None, "post_validation_target": None}

    async def _process_packing_list(self, *, extracted_text: str, filename: str, quality_assessment: Any, document_type: str, file_bytes: Optional[bytes] = None, content_type: Optional[str] = None) -> Dict[str, Any]:
        base_patch = {
            "ocr_quality": {
                "overall_score": quality_assessment.overall_score,
                "quality_level": quality_assessment.quality_level.value,
                "can_proceed": quality_assessment.can_proceed,
                "warnings": quality_assessment.warnings,
                "recommendations": quality_assessment.recommendations,
            },
            "review_reasons": list(quality_assessment.warnings or []),
        }
        try:
            # Vision LLM looks at raw PDF page images first (no OCR text input).
            # The text-based AI extractor below is the fallback when vision fails.
            multimodal_struct = await extract_document_multimodal_first(
                document_type=document_type,
                filename=filename,
                file_bytes=file_bytes,
                content_type=content_type,
                extracted_text=getattr(self, "_current_pdf_text", "") or extracted_text,
                cross_doc_context=getattr(self, "_current_cross_doc_context", None),
            )
            packing_struct = multimodal_struct or await extract_packing_list_ai_first(extracted_text)
            extraction_status = packing_struct.get("_status", "unknown")
            if packing_struct and extraction_status != "failed":
                extracted_fields = (
                    packing_struct.get("extracted_fields")
                    if isinstance(packing_struct.get("extracted_fields"), dict)
                    else packing_struct
                )
                extraction_lane = _resolve_extraction_lane(
                    extraction_method=packing_struct.get("_extraction_method", "unknown"),
                )
                fact_graph_v1 = build_packing_list_fact_set(
                    {
                        **{
                            key: value
                            for key, value in packing_struct.items()
                            if not str(key).startswith("_")
                        },
                        "document_type": document_type,
                        "extracted_fields": extracted_fields,
                        "field_details": packing_struct.get("_field_details"),
                        "raw_text": extracted_text,
                        "extraction_method": packing_struct.get("_extraction_method", "unknown"),
                        "extraction_lane": extraction_lane,
                    }
                )
                return {
                    "handled": True,
                    "context_key": "packing_list",
                    "context_payload": _apply_canonical_normalization(
                        {**packing_struct, "raw_text": extracted_text, "fact_graph_v1": fact_graph_v1}
                    ),
                    "doc_info_patch": {
                        **base_patch,
                        "extracted_fields": extracted_fields,
                        "extraction_status": "success",
                        "extraction_method": packing_struct.get("_extraction_method", "unknown"),
                        "extraction_lane": extraction_lane,
                        "extraction_confidence": packing_struct.get("_extraction_confidence", 0.0),
                        "ai_first_status": extraction_status,
                        "field_details": packing_struct.get("_field_details"),
                        "status_counts": packing_struct.get("_status_counts"),
                        "fact_graph_v1": fact_graph_v1,
                    },
                    "has_structured_data": True,
                    "validation_doc_type": "packing_list",
                    "post_validation_target": "packing_list",
                }
        except Exception as exc:
            logger.warning("Launch pipeline packing list AI extraction failed for %s: %s", filename, exc, exc_info=True)

        try:
            packing_fields = self._fallback_extractor.extract_fields(extracted_text, DocumentType.PACKING_LIST)
            packing_context = _fields_to_flat_context(packing_fields)
            if packing_context:
                result = _build_support_only_result(
                    context_key="packing_list",
                    context_payload=_apply_canonical_normalization({**packing_context, "raw_text": extracted_text}),
                    base_patch=base_patch,
                    extraction_method="regex_support",
                    field_details=packing_context.get("_field_details"),
                )
                fact_graph_v1 = build_packing_list_fact_set(
                    {
                        **{
                            key: value
                            for key, value in packing_context.items()
                            if not str(key).startswith("_")
                        },
                        "document_type": document_type,
                        "extracted_fields": {
                            key: value
                            for key, value in packing_context.items()
                            if not str(key).startswith("_")
                        },
                        "field_details": packing_context.get("_field_details"),
                        "raw_text": extracted_text,
                        "extraction_method": "regex_support",
                        "extraction_lane": "support_only",
                    }
                )
                result["context_payload"]["fact_graph_v1"] = fact_graph_v1
                result["doc_info_patch"]["fact_graph_v1"] = fact_graph_v1
                return result
        except Exception as exc:
            logger.warning("Launch pipeline packing list regex fallback failed for %s: %s", filename, exc, exc_info=True)

        fact_graph_v1 = build_packing_list_fact_set(
            {
                "document_type": document_type,
                "extracted_fields": {},
                "field_details": {},
                "raw_text": extracted_text,
                "extraction_method": "launch_pipeline_packing_list_extraction_failed",
                "extraction_lane": "unknown",
            }
        )
        return {
            "handled": True,
            "context_key": "packing_list",
            "context_payload": {"raw_text": extracted_text, "fact_graph_v1": fact_graph_v1},
            "doc_info_patch": {
                **base_patch,
                "fact_graph_v1": fact_graph_v1,
                "extraction_status": "failed",
                "extraction_error": "launch_pipeline_packing_list_extraction_failed",
            },
            "has_structured_data": False,
            "validation_doc_type": None,
            "post_validation_target": None,
        }

    async def _process_certificate_of_origin(
        self,
        *,
        extracted_text: str,
        filename: str,
        quality_assessment: Any,
        document_type: str,
        file_bytes: Optional[bytes] = None,
        content_type: Optional[str] = None,
        forced_subtype: Optional[str] = None,
        post_validation_target: str = "certificate_of_origin",
    ) -> Dict[str, Any]:
        regulatory_subtype = forced_subtype or _detect_regulatory_subtype(filename=filename, extracted_text=extracted_text)
        base_patch = {
            "ocr_quality": {
                "overall_score": quality_assessment.overall_score,
                "quality_level": quality_assessment.quality_level.value,
                "can_proceed": quality_assessment.can_proceed,
                "warnings": quality_assessment.warnings,
                "recommendations": quality_assessment.recommendations,
            },
            "review_reasons": list(quality_assessment.warnings or []),
        }
        try:
            # Vision LLM looks at raw PDF page images first (no OCR text input).
            # The text-based AI extractor below is the fallback when vision fails.
            multimodal_struct = await extract_document_multimodal_first(
                document_type=document_type,
                filename=filename,
                file_bytes=file_bytes,
                content_type=content_type,
                extracted_text=getattr(self, "_current_pdf_text", "") or extracted_text,
                subtype_hint=regulatory_subtype,
                cross_doc_context=getattr(self, "_current_cross_doc_context", None),
            )
            coo_struct = multimodal_struct or await extract_coo_ai_first(extracted_text)
            extraction_status = coo_struct.get("_status", "unknown")
            if coo_struct and extraction_status != "failed":
                shaped_payload = _shape_regulatory_payload(
                    coo_struct,
                    regulatory_subtype=regulatory_subtype,
                    raw_text=extracted_text,
                    allow_text_backfill=False,
                )
                regulatory_review = _assess_regulatory_completeness(shaped_payload, regulatory_subtype=regulatory_subtype)
                effective_extraction_status = "success" if regulatory_review.get("parse_complete") else "partial"
                extracted_fields = (
                    coo_struct.get("extracted_fields")
                    if isinstance(coo_struct.get("extracted_fields"), dict)
                    else coo_struct
                )
                extraction_lane = _resolve_extraction_lane(
                    extraction_method=coo_struct.get("_extraction_method", "unknown"),
                )
                fact_graph_v1 = build_coo_fact_set(
                    {
                        **{
                            key: value
                            for key, value in shaped_payload.items()
                            if not str(key).startswith("_")
                        },
                        "document_type": document_type,
                        "regulatory_subtype": regulatory_subtype,
                        "extracted_fields": extracted_fields,
                        "field_details": coo_struct.get("_field_details"),
                        "raw_text": extracted_text,
                        "extraction_method": coo_struct.get("_extraction_method", "unknown"),
                        "extraction_lane": extraction_lane,
                    }
                )
                return {
                    "handled": True,
                    "context_key": "certificate_of_origin",
                    "context_payload": {**shaped_payload, "regulatory_review": regulatory_review, "fact_graph_v1": fact_graph_v1},
                    "doc_info_patch": {
                        **base_patch,
                        "regulatory_subtype": regulatory_subtype,
                        "regulatory_family": shaped_payload.get("regulatory_family"),
                        "extracted_fields": extracted_fields,
                        "extraction_status": effective_extraction_status,
                        "parse_complete": regulatory_review.get("parse_complete"),
                        "parse_completeness": regulatory_review.get("required_ratio"),
                        "missing_required_fields": regulatory_review.get("missing_required_fields", []),
                        "required_fields_found": regulatory_review.get("required_found"),
                        "required_fields_total": regulatory_review.get("required_total"),
                        "extraction_method": coo_struct.get("_extraction_method", "unknown"),
                        "extraction_lane": extraction_lane,
                        "extraction_confidence": coo_struct.get("_extraction_confidence", 0.0),
                        "ai_first_status": extraction_status,
                        "field_details": coo_struct.get("_field_details"),
                        "status_counts": coo_struct.get("_status_counts"),
                        "review_reasons": list(base_patch.get("review_reasons") or []) + list(regulatory_review.get("review_reasons") or []),
                        "fact_graph_v1": fact_graph_v1,
                    },
                    "has_structured_data": True,
                    "validation_doc_type": "certificate_of_origin",
                    "post_validation_target": post_validation_target,
                }
        except Exception as exc:
            logger.warning("Launch pipeline COO AI extraction failed for %s: %s", filename, exc, exc_info=True)

        try:
            coo_fields = self._fallback_extractor.extract_fields(extracted_text, DocumentType.CERTIFICATE_OF_ORIGIN)
            coo_context = _fields_to_flat_context(coo_fields)
            if coo_context:
                shaped_payload = _shape_regulatory_payload(coo_context, regulatory_subtype=regulatory_subtype, raw_text=extracted_text)
                regulatory_review = _assess_regulatory_completeness(shaped_payload, regulatory_subtype=regulatory_subtype)
                result = _build_support_only_result(
                    context_key="certificate_of_origin",
                    context_payload={**shaped_payload, "regulatory_review": regulatory_review},
                    base_patch=base_patch,
                    extraction_method="regex_support",
                    field_details=coo_context.get("_field_details"),
                    review_payload=regulatory_review,
                    extra_doc_info={
                        "regulatory_subtype": regulatory_subtype,
                        "regulatory_family": shaped_payload.get("regulatory_family"),
                    },
                )
                fact_graph_v1 = build_coo_fact_set(
                    {
                        **{
                            key: value
                            for key, value in shaped_payload.items()
                            if not str(key).startswith("_")
                        },
                        "document_type": document_type,
                        "regulatory_subtype": regulatory_subtype,
                        "extracted_fields": {
                            key: value
                            for key, value in shaped_payload.items()
                            if not str(key).startswith("_")
                        },
                        "field_details": coo_context.get("_field_details"),
                        "raw_text": extracted_text,
                        "extraction_method": "regex_support",
                        "extraction_lane": "support_only",
                    }
                )
                result["context_payload"]["fact_graph_v1"] = fact_graph_v1
                result["doc_info_patch"]["fact_graph_v1"] = fact_graph_v1
                return result
        except Exception as exc:
            logger.warning("Launch pipeline COO regex fallback failed for %s: %s", filename, exc, exc_info=True)

        shaped_payload = _shape_regulatory_payload({}, regulatory_subtype=regulatory_subtype, raw_text=extracted_text)
        regulatory_review = _assess_regulatory_completeness(shaped_payload, regulatory_subtype=regulatory_subtype)
        fact_graph_v1 = build_coo_fact_set(
            {
                **{
                    key: value
                    for key, value in shaped_payload.items()
                    if not str(key).startswith("_")
                },
                "document_type": document_type,
                "regulatory_subtype": regulatory_subtype,
                "extracted_fields": {
                    key: value
                    for key, value in shaped_payload.items()
                    if not str(key).startswith("_")
                },
                "field_details": {},
                "raw_text": extracted_text,
                "extraction_method": "launch_pipeline_coo_extraction_failed",
                "extraction_lane": "unknown",
            }
        )
        return {"handled": True, "context_key": "certificate_of_origin", "context_payload": {**shaped_payload, "regulatory_review": regulatory_review, "fact_graph_v1": fact_graph_v1}, "doc_info_patch": {**base_patch, "regulatory_subtype": regulatory_subtype, "regulatory_family": shaped_payload.get("regulatory_family"), "fact_graph_v1": fact_graph_v1, "parse_complete": regulatory_review.get("parse_complete"), "parse_completeness": regulatory_review.get("required_ratio"), "missing_required_fields": regulatory_review.get("missing_required_fields", []), "required_fields_found": regulatory_review.get("required_found"), "required_fields_total": regulatory_review.get("required_total"), "review_reasons": list(base_patch.get("review_reasons") or []) + list(regulatory_review.get("review_reasons") or []), "extraction_status": "failed", "extraction_error": "launch_pipeline_coo_extraction_failed"}, "has_structured_data": False, "validation_doc_type": None, "post_validation_target": None}

    async def _process_insurance_certificate(
        self,
        *,
        extracted_text: str,
        filename: str,
        quality_assessment: Any,
        document_type: str,
        file_bytes: Optional[bytes] = None,
        content_type: Optional[str] = None,
        forced_subtype: Optional[str] = None,
        post_validation_target: str = "insurance_certificate",
    ) -> Dict[str, Any]:
        insurance_subtype = forced_subtype or _detect_insurance_subtype(filename=filename, extracted_text=extracted_text)
        base_patch = {
            "ocr_quality": {
                "overall_score": quality_assessment.overall_score,
                "quality_level": quality_assessment.quality_level.value,
                "can_proceed": quality_assessment.can_proceed,
                "warnings": quality_assessment.warnings,
                "recommendations": quality_assessment.recommendations,
            },
            "review_reasons": list(quality_assessment.warnings or []),
        }
        try:
            # Vision LLM looks at raw PDF page images first (no OCR text input).
            # The text-based AI extractor below is the fallback when vision fails.
            multimodal_struct = await extract_document_multimodal_first(
                document_type=document_type,
                filename=filename,
                file_bytes=file_bytes,
                content_type=content_type,
                extracted_text=getattr(self, "_current_pdf_text", "") or extracted_text,
                subtype_hint=insurance_subtype,
                cross_doc_context=getattr(self, "_current_cross_doc_context", None),
            )
            insurance_struct = multimodal_struct or await extract_insurance_ai_first(extracted_text)
            extraction_status = insurance_struct.get("_status", "unknown")
            if insurance_struct and extraction_status != "failed":
                shaped_payload = _shape_insurance_payload(
                    insurance_struct,
                    insurance_subtype=insurance_subtype,
                    raw_text=extracted_text,
                    allow_text_backfill=False,
                )
                insurance_review = _assess_insurance_completeness(shaped_payload, insurance_subtype=insurance_subtype)
                extracted_fields = (
                    insurance_struct.get("extracted_fields")
                    if isinstance(insurance_struct.get("extracted_fields"), dict)
                    else insurance_struct
                )
                extraction_lane = _resolve_extraction_lane(
                    extraction_method=insurance_struct.get("_extraction_method", "unknown"),
                )
                fact_graph_v1 = build_insurance_fact_set(
                    {
                        **{
                            key: value
                            for key, value in shaped_payload.items()
                            if not str(key).startswith("_")
                        },
                        "document_type": document_type,
                        "insurance_subtype": insurance_subtype,
                        "extracted_fields": extracted_fields,
                        "field_details": insurance_struct.get("_field_details"),
                        "raw_text": extracted_text,
                        "extraction_method": insurance_struct.get("_extraction_method", "unknown"),
                        "extraction_lane": extraction_lane,
                    }
                )
                return {
                    "handled": True,
                    "context_key": "insurance_certificate",
                    "context_payload": {**shaped_payload, "insurance_review": insurance_review, "fact_graph_v1": fact_graph_v1},
                    "doc_info_patch": {
                        **base_patch,
                        "insurance_subtype": insurance_subtype,
                        "insurance_family": shaped_payload.get("insurance_family"),
                        "fact_graph_v1": fact_graph_v1,
                        "extracted_fields": extracted_fields,
                        "extraction_status": "success" if insurance_review.get("parse_complete") else "partial",
                        "extraction_method": insurance_struct.get("_extraction_method", "unknown"),
                        "extraction_lane": extraction_lane,
                        "extraction_confidence": insurance_struct.get("_extraction_confidence", 0.0),
                        "ai_first_status": extraction_status,
                        "field_details": insurance_struct.get("_field_details"),
                        "status_counts": insurance_struct.get("_status_counts"),
                        "parse_complete": insurance_review.get("parse_complete"),
                        "parse_completeness": insurance_review.get("required_ratio"),
                        "missing_required_fields": insurance_review.get("missing_required_fields", []),
                        "required_fields_found": insurance_review.get("required_found"),
                        "required_fields_total": insurance_review.get("required_total"),
                        "review_reasons": list(base_patch.get("review_reasons") or []) + list(insurance_review.get("review_reasons") or []),
                    },
                    "has_structured_data": True,
                    "validation_doc_type": "insurance",
                    "post_validation_target": post_validation_target,
                }
        except Exception as exc:
            logger.warning("Launch pipeline insurance AI extraction failed for %s: %s", filename, exc, exc_info=True)

        try:
            insurance_fields = self._fallback_extractor.extract_fields(extracted_text, DocumentType.INSURANCE_CERTIFICATE)
            insurance_context = _fields_to_flat_context(insurance_fields)
            if insurance_context:
                shaped_payload = _shape_insurance_payload(insurance_context, insurance_subtype=insurance_subtype, raw_text=extracted_text)
                insurance_review = _assess_insurance_completeness(shaped_payload, insurance_subtype=insurance_subtype)
                result = _build_support_only_result(
                    context_key="insurance_certificate",
                    context_payload={**shaped_payload, "insurance_review": insurance_review},
                    base_patch=base_patch,
                    extraction_method="regex_support",
                    field_details=insurance_context.get("_field_details"),
                    review_payload=insurance_review,
                    extra_doc_info={
                        "insurance_subtype": insurance_subtype,
                        "insurance_family": shaped_payload.get("insurance_family"),
                    },
                )
                fact_graph_v1 = build_insurance_fact_set(
                    {
                        **{
                            key: value
                            for key, value in shaped_payload.items()
                            if not str(key).startswith("_")
                        },
                        "document_type": document_type,
                        "insurance_subtype": insurance_subtype,
                        "extracted_fields": {
                            key: value
                            for key, value in shaped_payload.items()
                            if not str(key).startswith("_")
                        },
                        "field_details": insurance_context.get("_field_details"),
                        "raw_text": extracted_text,
                        "extraction_method": "regex_support",
                        "extraction_lane": "support_only",
                    }
                )
                result["context_payload"]["fact_graph_v1"] = fact_graph_v1
                result["doc_info_patch"]["fact_graph_v1"] = fact_graph_v1
                return result
        except Exception as exc:
            logger.warning("Launch pipeline insurance regex fallback failed for %s: %s", filename, exc, exc_info=True)

        shaped_payload = _shape_insurance_payload({}, insurance_subtype=insurance_subtype, raw_text=extracted_text)
        insurance_review = _assess_insurance_completeness(shaped_payload, insurance_subtype=insurance_subtype)
        has_structured_values = _has_extracted_content(
            shaped_payload,
            ["policy_number", "certificate_number", "insured_amount", "issuer_name"],
        )
        if has_structured_values:
            result = _build_support_only_result(
                context_key="insurance_certificate",
                context_payload={**shaped_payload, "insurance_review": insurance_review},
                base_patch=base_patch,
                extraction_method="raw_text_support",
                field_details=_build_support_only_field_details_from_payload(
                    shaped_payload,
                    ["policy_number", "certificate_number", "insured_amount", "issuer_name"],
                ),
                review_payload=insurance_review,
                extra_doc_info={
                        "insurance_subtype": insurance_subtype,
                        "insurance_family": shaped_payload.get("insurance_family"),
                    },
            )
            fact_graph_v1 = build_insurance_fact_set(
                {
                    **{
                        key: value
                        for key, value in shaped_payload.items()
                        if not str(key).startswith("_")
                    },
                    "document_type": document_type,
                    "insurance_subtype": insurance_subtype,
                    "extracted_fields": {
                        key: value
                        for key, value in shaped_payload.items()
                        if not str(key).startswith("_")
                    },
                    "field_details": result["doc_info_patch"].get("field_details") or {},
                    "raw_text": extracted_text,
                    "extraction_method": "raw_text_support",
                    "extraction_lane": "support_only",
                }
            )
            result["context_payload"]["fact_graph_v1"] = fact_graph_v1
            result["doc_info_patch"]["fact_graph_v1"] = fact_graph_v1
            return result
        fact_graph_v1 = build_insurance_fact_set(
            {
                **{
                    key: value
                    for key, value in shaped_payload.items()
                    if not str(key).startswith("_")
                },
                "document_type": document_type,
                "insurance_subtype": insurance_subtype,
                "extracted_fields": {
                    key: value
                    for key, value in shaped_payload.items()
                    if not str(key).startswith("_")
                },
                "field_details": {},
                "raw_text": extracted_text,
                "extraction_method": "launch_pipeline_insurance_extraction_failed",
                "extraction_lane": "unknown",
            }
        )
        return {
            "handled": True,
            "context_key": "insurance_certificate",
            "context_payload": {**shaped_payload, "insurance_review": insurance_review, "fact_graph_v1": fact_graph_v1},
            "doc_info_patch": {
                **base_patch,
                "insurance_subtype": insurance_subtype,
                "insurance_family": shaped_payload.get("insurance_family"),
                "fact_graph_v1": fact_graph_v1,
                "parse_complete": insurance_review.get("parse_complete"),
                "parse_completeness": insurance_review.get("required_ratio"),
                "missing_required_fields": insurance_review.get("missing_required_fields", []),
                "required_fields_found": insurance_review.get("required_found"),
                "required_fields_total": insurance_review.get("required_total"),
                "review_reasons": list(base_patch.get("review_reasons") or []) + list(insurance_review.get("review_reasons") or []),
                "extraction_status": "failed",
                "extraction_error": "launch_pipeline_insurance_extraction_failed",
            },
            "has_structured_data": False,
            "validation_doc_type": None,
            "post_validation_target": None,
        }

    async def _process_supporting_document(self, *, extracted_text: str, filename: str, quality_assessment: Any, document_type: str, file_bytes: Optional[bytes] = None, content_type: Optional[str] = None) -> Dict[str, Any]:
        supporting_guess = _guess_supporting_document_subtype(filename=filename, extracted_text=extracted_text)
        # Vision LLM looks at raw PDF page images first (no OCR text input).
        multimodal_struct = await extract_document_multimodal_first(
            document_type=document_type,
            filename=filename,
            file_bytes=file_bytes,
            content_type=content_type,
            extracted_text=getattr(self, "_current_pdf_text", "") or extracted_text,
            subtype_hint=supporting_guess.get("subtype"),
            cross_doc_context=getattr(self, "_current_cross_doc_context", None),
        )
        base_patch = {
            "ocr_quality": {
                "overall_score": quality_assessment.overall_score,
                "quality_level": quality_assessment.quality_level.value,
                "can_proceed": quality_assessment.can_proceed,
                "warnings": quality_assessment.warnings,
                "recommendations": quality_assessment.recommendations,
            },
            "review_reasons": list(quality_assessment.warnings or []),
        }
        payload = _apply_canonical_normalization({
            **(multimodal_struct or {}),
            "raw_text": extracted_text,
            "supporting_subtype_guess": supporting_guess.get("subtype"),
            "supporting_family_guess": supporting_guess.get("family"),
            "guess_confidence": supporting_guess.get("confidence"),
            "guess_reasons": supporting_guess.get("reasons"),
            "document_summary": _summarize_supporting_document(extracted_text),
        })
        review_reasons = list(base_patch.get("review_reasons") or [])
        if supporting_guess.get("confidence", 0.0) < 0.5:
            review_reasons.append("supporting_document_low_confidence_classification")
        if len((extracted_text or '').strip()) < 80:
            review_reasons.append("supporting_document_sparse_text")
        extraction_method = (
            multimodal_struct.get("_extraction_method", "unknown")
            if isinstance(multimodal_struct, dict)
            else "unknown"
        )
        extraction_lane = _resolve_extraction_lane(extraction_method=extraction_method)
        field_details = (
            multimodal_struct.get("_field_details")
            if isinstance(multimodal_struct, dict) and isinstance(multimodal_struct.get("_field_details"), dict)
            else {}
        )
        fact_graph_v1 = build_supporting_fact_set(
            {
                **{
                    key: value
                    for key, value in payload.items()
                    if not str(key).startswith("_")
                },
                "document_type": document_type,
                "extracted_fields": {
                    key: value
                    for key, value in payload.items()
                    if not str(key).startswith("_")
                },
                "field_details": field_details,
                "raw_text": extracted_text,
                "extraction_method": extraction_method,
                "extraction_lane": extraction_lane,
            }
        )
        return {
            "handled": True,
            "context_key": "supporting_document",
            "context_payload": {**payload, "fact_graph_v1": fact_graph_v1},
            "doc_info_patch": {
                **base_patch,
                "extraction_status": "partial",
                "supporting_subtype_guess": supporting_guess.get("subtype"),
                "supporting_family_guess": supporting_guess.get("family"),
                "guess_confidence": supporting_guess.get("confidence"),
                "fact_graph_v1": fact_graph_v1,
                "field_details": field_details,
                "extraction_method": extraction_method,
                "extraction_lane": extraction_lane,
                "review_reasons": review_reasons,
            },
            "has_structured_data": True,
            "validation_doc_type": None,
            "post_validation_target": None,
        }

    async def _process_inspection_certificate(
        self,
        *,
        extracted_text: str,
        filename: str,
        quality_assessment: Any,
        document_type: str,
        file_bytes: Optional[bytes] = None,
        content_type: Optional[str] = None,
        forced_subtype: Optional[str] = None,
        post_validation_target: str = "inspection_certificate",
    ) -> Dict[str, Any]:
        inspection_subtype = forced_subtype or _detect_inspection_subtype(filename=filename, extracted_text=extracted_text)
        base_patch = {
            "ocr_quality": {
                "overall_score": quality_assessment.overall_score,
                "quality_level": quality_assessment.quality_level.value,
                "can_proceed": quality_assessment.can_proceed,
                "warnings": quality_assessment.warnings,
                "recommendations": quality_assessment.recommendations,
            },
            "review_reasons": list(quality_assessment.warnings or []),
        }
        try:
            # Vision LLM looks at raw PDF page images first (no OCR text input).
            # The text-based AI extractor below is the fallback when vision fails.
            multimodal_struct = await extract_document_multimodal_first(
                document_type=document_type,
                filename=filename,
                file_bytes=file_bytes,
                content_type=content_type,
                extracted_text=getattr(self, "_current_pdf_text", "") or extracted_text,
                subtype_hint=inspection_subtype,
                cross_doc_context=getattr(self, "_current_cross_doc_context", None),
            )
            inspection_struct = multimodal_struct or await extract_inspection_ai_first(extracted_text)
            extraction_status = inspection_struct.get("_status", "unknown")
            if inspection_struct and extraction_status != "failed":
                shaped_payload = _shape_inspection_payload(
                    inspection_struct,
                    inspection_subtype=inspection_subtype,
                    raw_text=extracted_text,
                    allow_text_backfill=False,
                )
                inspection_review = _assess_inspection_completeness(shaped_payload, inspection_subtype=inspection_subtype)
                extracted_fields = (
                    inspection_struct.get("extracted_fields")
                    if isinstance(inspection_struct.get("extracted_fields"), dict)
                    else inspection_struct
                )
                extraction_lane = _resolve_extraction_lane(
                    extraction_method=inspection_struct.get("_extraction_method", "unknown"),
                )
                fact_graph_v1 = build_inspection_fact_set(
                    {
                        **{
                            key: value
                            for key, value in shaped_payload.items()
                            if not str(key).startswith("_")
                        },
                        "document_type": document_type,
                        "inspection_subtype": inspection_subtype,
                        "extracted_fields": extracted_fields,
                        "field_details": inspection_struct.get("_field_details"),
                        "raw_text": extracted_text,
                        "extraction_method": inspection_struct.get("_extraction_method", "unknown"),
                        "extraction_lane": extraction_lane,
                    }
                )
                return {
                    "handled": True,
                    "context_key": "inspection_certificate",
                    "context_payload": {**shaped_payload, "inspection_review": inspection_review, "fact_graph_v1": fact_graph_v1},
                    "doc_info_patch": {
                        **base_patch,
                        "inspection_subtype": inspection_subtype,
                        "fact_graph_v1": fact_graph_v1,
                        "extracted_fields": extracted_fields,
                        "extraction_status": "success" if inspection_review.get("parse_complete") else "partial",
                        "extraction_method": inspection_struct.get("_extraction_method", "unknown"),
                        "extraction_lane": extraction_lane,
                        "extraction_confidence": inspection_struct.get("_extraction_confidence", 0.0),
                        "ai_first_status": extraction_status,
                        "field_details": inspection_struct.get("_field_details"),
                        "status_counts": inspection_struct.get("_status_counts"),
                        "inspection_family": shaped_payload.get("inspection_family"),
                        "inspection_subtype": inspection_subtype,
                        "parse_complete": inspection_review.get("parse_complete"),
                        "parse_completeness": inspection_review.get("required_ratio"),
                        "missing_required_fields": inspection_review.get("missing_required_fields", []),
                        "required_fields_found": inspection_review.get("required_found"),
                        "required_fields_total": inspection_review.get("required_total"),
                        "review_reasons": list(base_patch.get("review_reasons") or []) + list(inspection_review.get("review_reasons") or []),
                    },
                    "has_structured_data": True,
                    "validation_doc_type": "inspection",
                    "post_validation_target": post_validation_target,
                }
        except Exception as exc:
            logger.warning("Launch pipeline inspection AI extraction failed for %s: %s", filename, exc, exc_info=True)

        try:
            inspection_fields = self._fallback_extractor.extract_fields(extracted_text, DocumentType.INSPECTION_CERTIFICATE)
            inspection_context = _fields_to_flat_context(inspection_fields)
            if inspection_context:
                shaped_payload = _shape_inspection_payload(inspection_context, inspection_subtype=inspection_subtype, raw_text=extracted_text)
                inspection_review = _assess_inspection_completeness(shaped_payload, inspection_subtype=inspection_subtype)
                result = _build_support_only_result(
                    context_key="inspection_certificate",
                    context_payload={**shaped_payload, "inspection_review": inspection_review},
                    base_patch=base_patch,
                    extraction_method="regex_support",
                    field_details=inspection_context.get("_field_details"),
                    review_payload=inspection_review,
                    extra_doc_info={
                        "inspection_subtype": inspection_subtype,
                        "inspection_family": shaped_payload.get("inspection_family"),
                    },
                )
                fact_graph_v1 = build_inspection_fact_set(
                    {
                        **{
                            key: value
                            for key, value in shaped_payload.items()
                            if not str(key).startswith("_")
                        },
                        "document_type": document_type,
                        "inspection_subtype": inspection_subtype,
                        "extracted_fields": {
                            key: value
                            for key, value in shaped_payload.items()
                            if not str(key).startswith("_")
                        },
                        "field_details": inspection_context.get("_field_details"),
                        "raw_text": extracted_text,
                        "extraction_method": "regex_support",
                        "extraction_lane": "support_only",
                    }
                )
                result["context_payload"]["fact_graph_v1"] = fact_graph_v1
                result["doc_info_patch"]["fact_graph_v1"] = fact_graph_v1
                return result
        except Exception as exc:
            logger.warning("Launch pipeline inspection regex fallback failed for %s: %s", filename, exc, exc_info=True)

        shaped_payload = _shape_inspection_payload({}, inspection_subtype=inspection_subtype, raw_text=extracted_text)
        inspection_review = _assess_inspection_completeness(shaped_payload, inspection_subtype=inspection_subtype)
        has_structured_values = _has_extracted_content(
            shaped_payload,
            [
                "inspection_result",
                "quality_finding",
                "analysis_result",
                "gross_weight",
                "net_weight",
                "measurement_value",
                "inspection_agency",
            ],
        )
        if has_structured_values:
            result = _build_support_only_result(
                context_key="inspection_certificate",
                context_payload={**shaped_payload, "inspection_review": inspection_review},
                base_patch=base_patch,
                extraction_method="raw_text_support",
                field_details=_build_support_only_field_details_from_payload(
                    shaped_payload,
                    [
                        "inspection_result",
                        "quality_finding",
                        "analysis_result",
                        "gross_weight",
                        "net_weight",
                        "measurement_value",
                        "inspection_agency",
                    ],
                ),
                review_payload=inspection_review,
                extra_doc_info={
                        "inspection_subtype": inspection_subtype,
                        "inspection_family": shaped_payload.get("inspection_family"),
                    },
            )
            fact_graph_v1 = build_inspection_fact_set(
                {
                    **{
                        key: value
                        for key, value in shaped_payload.items()
                        if not str(key).startswith("_")
                    },
                    "document_type": document_type,
                    "inspection_subtype": inspection_subtype,
                    "extracted_fields": {
                        key: value
                        for key, value in shaped_payload.items()
                        if not str(key).startswith("_")
                    },
                    "field_details": result["doc_info_patch"].get("field_details") or {},
                    "raw_text": extracted_text,
                    "extraction_method": "raw_text_support",
                    "extraction_lane": "support_only",
                }
            )
            result["context_payload"]["fact_graph_v1"] = fact_graph_v1
            result["doc_info_patch"]["fact_graph_v1"] = fact_graph_v1
            return result
        fact_graph_v1 = build_inspection_fact_set(
            {
                **{
                    key: value
                    for key, value in shaped_payload.items()
                    if not str(key).startswith("_")
                },
                "document_type": document_type,
                "inspection_subtype": inspection_subtype,
                "extracted_fields": {
                    key: value
                    for key, value in shaped_payload.items()
                    if not str(key).startswith("_")
                },
                "field_details": {},
                "raw_text": extracted_text,
                "extraction_method": "launch_pipeline_inspection_extraction_failed",
                "extraction_lane": "unknown",
            }
        )
        return {
            "handled": True,
            "context_key": "inspection_certificate",
            "context_payload": {**shaped_payload, "inspection_review": inspection_review, "fact_graph_v1": fact_graph_v1},
            "doc_info_patch": {
                **base_patch,
                "inspection_subtype": inspection_subtype,
                "inspection_family": shaped_payload.get("inspection_family"),
                "fact_graph_v1": fact_graph_v1,
                "parse_complete": inspection_review.get("parse_complete"),
                "parse_completeness": inspection_review.get("required_ratio"),
                "missing_required_fields": inspection_review.get("missing_required_fields", []),
                "required_fields_found": inspection_review.get("required_found"),
                "required_fields_total": inspection_review.get("required_total"),
                "review_reasons": list(base_patch.get("review_reasons") or []) + list(inspection_review.get("review_reasons") or []),
                "extraction_status": "failed",
                "extraction_error": "launch_pipeline_inspection_extraction_failed",
            },
            "has_structured_data": False,
            "validation_doc_type": None,
            "post_validation_target": None,
        }


def _set_nested_value(root: Dict[str, Any], path: tuple[str, ...], value: Any) -> None:
    target = root
    for key in path[:-1]:
        child = target.get(key)
        if not isinstance(child, dict):
            child = {}
            target[key] = child
        target = child
    target[path[-1]] = value


def _build_support_only_field_detail(*, value: Any, raw_text: Optional[str], confidence: Any) -> Dict[str, Any]:
    detail: Dict[str, Any] = {
        "value": value,
        "verification": "support_only",
        "source": "regex_support",
    }
    if confidence is not None:
        detail["confidence"] = confidence
    snippet = str(raw_text or value or "").strip()
    if raw_text:
        detail["raw_text"] = raw_text
    if snippet:
        detail["raw_value"] = snippet
        detail["evidence"] = {
            "snippet": snippet,
            "source": "regex_support",
        }
    return detail


def _build_support_only_field_details_from_payload(
    payload: Optional[Dict[str, Any]],
    candidate_fields: List[str],
) -> Dict[str, Dict[str, Any]]:
    shaped = payload or {}
    field_details: Dict[str, Dict[str, Any]] = {}
    for field_name in candidate_fields:
        value = shaped.get(field_name)
        if not _is_populated_field_value(value):
            continue
        field_details[field_name] = _build_support_only_field_detail(
            value=value,
            raw_text=None,
            confidence=None,
        )
    return field_details


def _fields_to_lc_context(fields: List[Any]) -> Dict[str, Any]:
    lc_context: Dict[str, Any] = {}
    field_details: Dict[str, Dict[str, Any]] = {}
    for field in fields:
        value = str(getattr(field, "value", "") or "").strip()
        if not value:
            continue
        name = getattr(field, "field_name", "")
        raw_text = getattr(field, "raw_text", None)
        confidence = getattr(field, "confidence", None)
        field_details[name] = _build_support_only_field_detail(
            value=value,
            raw_text=raw_text,
            confidence=confidence,
        )
        if name == "lc_number":
            lc_context["number"] = value
        elif name == "issue_date":
            _set_nested_value(lc_context, ("dates", "issue"), value)
        elif name == "expiry_date":
            _set_nested_value(lc_context, ("dates", "expiry"), value)
        elif name == "latest_shipment_date":
            _set_nested_value(lc_context, ("dates", "latest_shipment"), value)
        elif name == "lc_amount":
            _set_nested_value(lc_context, ("amount", "value"), value)
        elif name == "applicant":
            _set_nested_value(lc_context, ("applicant", "name"), value)
        elif name == "beneficiary":
            _set_nested_value(lc_context, ("beneficiary", "name"), value)
        elif name == "port_of_loading":
            _set_nested_value(lc_context, ("ports", "loading"), value)
        elif name == "port_of_discharge":
            _set_nested_value(lc_context, ("ports", "discharge"), value)
        elif name == "goods_items":
            try:
                lc_context["goods_items"] = json.loads(value)
            except Exception:
                lc_context["goods_items"] = value
        else:
            lc_context[name] = value
    if field_details:
        lc_context["_field_details"] = field_details
    return lc_context


def _fields_to_flat_context(fields: List[Any]) -> Dict[str, Any]:
    context: Dict[str, Any] = {}
    field_details: Dict[str, Dict[str, Any]] = {}
    for field in fields:
        value = str(getattr(field, "value", "") or "").strip()
        if value:
            context[getattr(field, "field_name", "field")] = value
        details: Dict[str, Any] = {}
        confidence = getattr(field, "confidence", None)
        raw_text = getattr(field, "raw_text", None)
        if value:
            details = _build_support_only_field_detail(
                value=value,
                raw_text=raw_text,
                confidence=confidence,
            )
        if details:
            field_details[getattr(field, "field_name", "field")] = details
    if field_details:
        context["_field_details"] = field_details
    return context


def _build_support_only_extraction_resolution(
    field_details: Optional[Dict[str, Dict[str, Any]]],
) -> Optional[Dict[str, Any]]:
    if not isinstance(field_details, dict) or not field_details:
        return None
    fields = [
        {
            "field_name": field_name,
            "label": str(field_name).replace("_", " ").strip().title(),
            "verification": str((detail or {}).get("verification") or "support_only"),
        }
        for field_name, detail in field_details.items()
        if str(field_name or "").strip()
    ]
    unresolved_count = len(fields)
    if unresolved_count == 0:
        return None
    return {
        "required": True,
        "unresolved_count": unresolved_count,
        "summary": (
            f"{unresolved_count} extracted field"
            f"{'' if unresolved_count == 1 else 's'} need confirmation before validation can be treated as final."
        ),
        "fields": fields,
        "source": "regex_support",
    }


def _build_support_only_result(
    *,
    context_key: str,
    context_payload: Dict[str, Any],
    base_patch: Dict[str, Any],
    extraction_method: str,
    field_details: Optional[Dict[str, Dict[str, Any]]],
    review_payload: Optional[Dict[str, Any]] = None,
    extra_doc_info: Optional[Dict[str, Any]] = None,
    lc_number: Optional[str] = None,
) -> Dict[str, Any]:
    review_payload = review_payload or {}
    extra_doc_info = extra_doc_info or {}
    extraction_resolution = _build_support_only_extraction_resolution(field_details)
    review_reasons = list(base_patch.get("review_reasons") or []) + list(review_payload.get("review_reasons") or [])
    doc_info_patch: Dict[str, Any] = {
        **base_patch,
        **extra_doc_info,
        "field_details": field_details or {},
        "extraction_status": "partial" if field_details else "failed",
        "extraction_method": extraction_method,
        "extraction_lane": _resolve_extraction_lane(
            extraction_method=extraction_method,
            support_only=bool(field_details),
        ),
        "parse_complete": review_payload.get("parse_complete"),
        "parse_completeness": review_payload.get("required_ratio"),
        "missing_required_fields": review_payload.get("missing_required_fields", []),
        "required_fields_found": review_payload.get("required_found"),
        "required_fields_total": review_payload.get("required_total"),
        "review_reasons": review_reasons,
        "extraction_resolution": extraction_resolution,
        "extractionResolution": extraction_resolution,
    }
    if doc_info_patch["extraction_status"] == "failed":
        doc_info_patch["extraction_error"] = f"launch_pipeline_{context_key}_fallback_support_only"
    return {
        "handled": True,
        "context_key": context_key,
        "context_payload": {
            **context_payload,
            "_field_details": field_details or {},
            "extraction_resolution": extraction_resolution,
            "extractionResolution": extraction_resolution,
        },
        "doc_info_patch": doc_info_patch,
        "has_structured_data": False,
        "support_only": bool(field_details),
        "lc_number": lc_number,
        "validation_doc_type": None,
        "post_validation_target": None,
    }


def _is_populated_field_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) > 0
    return True


def _assess_required_field_completeness(extracted_fields: Optional[Dict[str, Any]], required_fields: List[str]) -> Dict[str, Any]:
    fields = extracted_fields or {}
    found_required = [field for field in required_fields if _is_populated_field_value(fields.get(field))]
    required_total = len(required_fields)
    required_found = len(found_required)
    ratio = (required_found / required_total) if required_total else 0.0
    return {
        "required_fields": list(required_fields),
        "required_total": required_total,
        "required_found": required_found,
        "missing_required_fields": [field for field in required_fields if field not in found_required],
        "required_ratio": round(ratio, 4),
    }


def _build_extraction_resolution_metrics(
    *,
    missing_required_fields: List[str],
    parse_complete: bool,
) -> Dict[str, Any]:
    normalized_missing = [str(field).strip() for field in (missing_required_fields or []) if str(field or "").strip()]
    unresolved_count = len(normalized_missing)
    required = unresolved_count > 0 or parse_complete is False
    if unresolved_count > 0:
        summary = (
            f"{unresolved_count} extracted field"
            f"{'' if unresolved_count == 1 else 's'} still need confirmation before validation can be treated as final."
        )
    elif required:
        summary = "Extraction is still incomplete and needs confirmation before validation can be treated as final."
    else:
        summary = ""
    return {
        "required": required,
        "unresolved_count": unresolved_count,
        "summary": summary,
        "fields": [
            {
                "field_name": field,
                "label": str(field).replace("_", " ").strip().title(),
                "verification": "not_found",
            }
            for field in normalized_missing
        ],
        "source": "ai_extraction",
    }


def _assess_coo_parse_completeness(extracted_fields: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    required_fields = [
        "country_of_origin",
        "exporter_name",
        "importer_name",
        "goods_description",
    ]
    metrics = _assess_required_field_completeness(extracted_fields, required_fields)
    has_country = _is_populated_field_value((extracted_fields or {}).get("country_of_origin"))
    min_required_found = 3
    parse_complete = bool(has_country and metrics["required_found"] >= min_required_found)
    metrics.update(
        {
            "min_required_for_verified": min_required_found,
            "has_country_of_origin": has_country,
            "has_certificate_number": _is_populated_field_value((extracted_fields or {}).get("certificate_number")),
            "parse_complete": parse_complete,
            "review_reasons": [],
            "extraction_resolution": _build_extraction_resolution_metrics(
                missing_required_fields=metrics.get("missing_required_fields") or [],
                parse_complete=parse_complete,
            ),
        }
    )
    return metrics


TRANSPORT_DOC_ALIASES = {
    "bill_of_lading",
    "ocean_bill_of_lading",
    "charter_party_bill_of_lading",
    "sea_waybill",
    "air_waybill",
    "multimodal_transport_document",
    "combined_transport_document",
    "railway_consignment_note",
    "road_transport_document",
    "forwarders_certificate_of_receipt",
    "forwarder_certificate_of_receipt",
    "house_bill_of_lading",
    "master_bill_of_lading",
    "delivery_order",
    "mates_receipt",
    "shipping_company_certificate",
    "warehouse_receipt",
    "cargo_manifest",
    "courier_or_post_receipt_or_certificate_of_posting",
}

REGULATORY_DOC_ALIASES = {
    "certificate_of_origin",
    "gsp_form_a",
    "eur1_movement_certificate",
    "customs_declaration",
    "export_license",
    "import_license",
    "phytosanitary_certificate",
    "fumigation_certificate",
    "health_certificate",
    "veterinary_certificate",
    "sanitary_certificate",
    "cites_permit",
    "radiation_certificate",
}

INSURANCE_DOC_ALIASES = {
    "insurance_certificate",
    "insurance_policy",
    "beneficiary_certificate",
    "beneficiary_statement",
    "manufacturer_certificate",
    "manufacturers_certificate",
    "conformity_certificate",
    "certificate_of_conformity",
    "non_manipulation_certificate",
    "halal_certificate",
    "kosher_certificate",
    "organic_certificate",
}

INSPECTION_DOC_ALIASES = {
    "inspection_certificate",
    "pre_shipment_inspection",
    "quality_certificate",
    "weight_certificate",
    "weight_list",
    "measurement_certificate",
    "analysis_certificate",
    "lab_test_report",
    "sgs_certificate",
    "bureau_veritas_certificate",
    "intertek_certificate",
}


def _canonicalize_launch_doc_type(doc_type: str) -> str:
    normalized = str(doc_type or "").strip().lower().replace("-", "_").replace(" ", "_")
    transport_aliases = globals().get("TRANSPORT_DOC_ALIASES", set()) or set()
    regulatory_aliases = globals().get("REGULATORY_DOC_ALIASES", set()) or set()
    insurance_aliases = globals().get("INSURANCE_DOC_ALIASES", set()) or set()
    inspection_aliases = globals().get("INSPECTION_DOC_ALIASES", set()) or set()
    if normalized in transport_aliases:
        return normalized
    if normalized in regulatory_aliases:
        return normalized
    if normalized in insurance_aliases:
        return normalized
    if normalized in inspection_aliases:
        return normalized
    return normalized


def _detect_transport_subtype(*, filename: str, extracted_text: str) -> str:
    haystack = f"{filename or ''}\n{extracted_text or ''}".lower()
    checks = [
        ("air_waybill", ["air waybill", " air waybill", "awb", "air transport document", "airport of departure", "airport of destination"]),
        ("sea_waybill", ["sea waybill", "seawaybill", "sea-waybill"]),
        ("ocean_bill_of_lading", ["ocean bill of lading", "ocean b/l"]),
        ("charter_party_bill_of_lading", ["charter party bill of lading", "charter party b/l", "charterparty"]),
        ("multimodal_transport_document", ["multimodal transport", "combined transport", "at least two different modes of transport"]),
        ("railway_consignment_note", ["railway consignment", "rail consignment", "railway receipt"]),
        ("road_transport_document", ["road transport document", "cmr", "truck consignment", "road consignment"]),
        ("courier_or_post_receipt_or_certificate_of_posting", ["courier receipt", "post receipt", "certificate of posting", "postal receipt"]),
        ("forwarders_certificate_of_receipt", ["forwarder's certificate of receipt", "forwarders certificate of receipt", "fcr"]),
        ("house_bill_of_lading", ["house bill of lading", "house b/l", "hbl"]),
        ("master_bill_of_lading", ["master bill of lading", "master b/l", "mbl"]),
        ("delivery_order", ["delivery order"]),
        ("mates_receipt", ["mate's receipt", "mates receipt"]),
        ("shipping_company_certificate", ["shipping company certificate"]),
    ]
    for subtype, patterns in checks:
        if any(pattern in haystack for pattern in patterns):
            return subtype
    return "bill_of_lading"


def _guess_supporting_document_subtype(*, filename: str, extracted_text: str) -> Dict[str, Any]:
    haystack = f"{filename or ''}\n{extracted_text or ''}".lower()
    families = [
        ("transport_document", ["bill of lading", "waybill", "awb", "transport", "shipment", "vessel", "voyage"]),
        ("inspection_testing_quality", ["inspection", "test report", "analysis", "quality", "sgs", "intertek", "bureau veritas"]),
        ("origin_customs_regulatory", ["origin", "customs", "license", "permit", "phytosanitary", "fumigation", "health certificate"]),
        ("insurance_compliance_special_certificates", ["insurance", "policy", "conformity", "halal", "kosher", "organic", "certificate"]),
        ("commercial_payment_instruments", ["invoice", "receipt", "note", "bill of exchange", "promissory"]),
        ("lc_financial_undertakings", ["letter of credit", "bank guarantee", "standby lc", "sblc", "swift mt"]),
    ]
    for family, markers in families:
        hits = [marker for marker in markers if marker in haystack]
        if hits:
            confidence = min(0.9, 0.35 + 0.15 * len(hits))
            return {
                "family": family,
                "subtype": hits[0].replace(' ', '_').replace('-', '_'),
                "confidence": round(confidence, 2),
                "reasons": hits,
            }
    return {"family": "unknown", "subtype": "unknown", "confidence": 0.1, "reasons": []}


def _summarize_supporting_document(text: str) -> Dict[str, Any]:
    raw = (text or '').strip()
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    return {
        "line_count": len(lines),
        "char_count": len(raw),
        "first_line": lines[0] if lines else None,
        "preview": raw[:240] if raw else None,
    }


def _assess_invoice_financial_completeness(payload: Optional[Dict[str, Any]], *, invoice_subtype: str) -> Dict[str, Any]:
    subtype_required = {
        "bill_of_exchange": ["instrument_number", "amount"],
        "promissory_note": ["instrument_number", "amount"],
        "payment_receipt": ["receipt_number", "amount"],
        "debit_note": ["instrument_number", "amount"],
        "credit_note": ["instrument_number", "amount"],
        "commercial_invoice": ["invoice_number", "amount"],
    }
    required_fields = subtype_required.get(invoice_subtype, ["invoice_number", "amount"])
    metrics = _assess_required_field_completeness(payload, required_fields)
    parse_complete = metrics.get("required_found", 0) >= max(1, min(2, metrics.get("required_total", 0)))
    metrics.update(
        {
            "parse_complete": parse_complete,
            "review_reasons": [],
            "extraction_resolution": _build_extraction_resolution_metrics(
                missing_required_fields=metrics.get("missing_required_fields") or [],
                parse_complete=parse_complete,
            ),
        }
    )
    return metrics


def _detect_invoice_financial_subtype(*, filename: str, extracted_text: str) -> str:
    haystack = f"{filename or ''}\n{extracted_text or ''}".lower()
    checks = [
        ("bill_of_exchange", ["bill of exchange", "draft bill", "draft"]),
        ("promissory_note", ["promissory note"]),
        ("payment_receipt", ["payment receipt", "receipt"]),
        ("debit_note", ["debit note"]),
        ("credit_note", ["credit note"]),
    ]
    for subtype, patterns in checks:
        if any(pattern in haystack for pattern in patterns):
            return subtype
    return "commercial_invoice"


def _shape_invoice_financial_payload(
    payload: Dict[str, Any],
    *,
    invoice_subtype: str,
    raw_text: str,
    allow_text_backfill: bool = True,
) -> Dict[str, Any]:
    shaped = dict(payload or {})
    shaped["raw_text"] = raw_text
    shaped["invoice_subtype"] = invoice_subtype
    shaped["invoice_family"] = "commercial_payment_instruments"

    def _first(*values):
        for value in values:
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            return value
        return None

    shaped["invoice_number"] = _first(
        shaped.get("invoice_number"),
        _extract_label_value(raw_text, ["invoice no", "invoice number"]) if allow_text_backfill else None,
    )
    shaped["instrument_number"] = _first(
        shaped.get("instrument_number"),
        shaped.get("invoice_number"),
        _extract_label_value(raw_text, ["bill no", "draft no", "note no", "reference no", "debit note no", "credit note no"]) if allow_text_backfill else None,
    )
    shaped["lc_reference"] = _first(
        shaped.get("lc_reference"),
        shaped.get("lc_number"),
        _extract_label_value(
            raw_text,
            [
                "lc no",
                "lc number",
                "lc ref",
                "lc reference",
                "letter of credit no",
                "letter of credit number",
                "credit number",
            ],
        ) if allow_text_backfill else None,
    )
    shaped["lc_number"] = _first(shaped.get("lc_number"), shaped.get("lc_reference"))
    if invoice_subtype == "payment_receipt":
        shaped["receipt_number"] = _first(
            shaped.get("receipt_number"),
            _extract_label_value(raw_text, ["receipt no", "receipt number"]) if allow_text_backfill else None,
        )
    else:
        shaped["receipt_number"] = shaped.get("receipt_number")
    shaped["amount"] = _first(
        shaped.get("amount"),
        _extract_amount_value(raw_text, ["amount", "total amount", "receipt amount", "note amount"]) if allow_text_backfill else None,
    )
    shaped["currency"] = _first(shaped.get("currency"), _extract_label_value(raw_text, ["currency"]) if allow_text_backfill else None)
    return _apply_canonical_normalization(shaped)


def _assess_lc_financial_completeness(payload: Optional[Dict[str, Any]], *, lc_subtype: str) -> Dict[str, Any]:
    subtype_required = {
        "bank_guarantee": ["applicant", "beneficiary", "amount", "guarantee_reference"],
        "standby_letter_of_credit": ["applicant", "beneficiary", "amount", "lc_number"],
        "letter_of_credit": ["applicant", "beneficiary", "amount"],
        "swift_message": ["applicant", "beneficiary"],
        "lc_application": ["applicant", "beneficiary"],
    }
    required_fields = subtype_required.get(lc_subtype, ["applicant", "beneficiary"])
    metrics = _assess_required_field_completeness(payload, required_fields)
    parse_complete = metrics.get("required_found", 0) >= max(1, min(3, metrics.get("required_total", 0)))
    metrics.update(
        {
            "parse_complete": parse_complete,
            "review_reasons": [],
            "extraction_resolution": _build_extraction_resolution_metrics(
                missing_required_fields=metrics.get("missing_required_fields") or [],
                parse_complete=parse_complete,
            ),
        }
    )
    return metrics


def _detect_lc_financial_subtype(*, filename: str, document_type: str, extracted_text: str) -> str:
    haystack = f"{filename or ''}\n{document_type or ''}\n{extracted_text or ''}".lower()
    if any(token in haystack for token in ["bank guarantee"]):
        return "bank_guarantee"
    if any(token in haystack for token in ["standby letter of credit", "standby lc", "sblc"]):
        return "standby_letter_of_credit"
    return str(document_type or "letter_of_credit").strip().lower() or "letter_of_credit"


def _coerce_mt700_date_iso(value: Any) -> Optional[str]:
    raw_value = str(value or "").strip()
    if not raw_value:
        return None

    match = re.search(r"(\d{6}|\d{8})", raw_value)
    if not match:
        return None

    digits = match.group(1)
    try:
        if len(digits) == 6:
            year = int(digits[:2])
            month = int(digits[2:4])
            day = int(digits[4:6])
            full_year = 2000 + year if year < 80 else 1900 + year
        else:
            full_year = int(digits[:4])
            month = int(digits[4:6])
            day = int(digits[6:8])
        return date(full_year, month, day).isoformat()
    except ValueError:
        return None


def _extract_mt700_timeline_fields(raw_text: str) -> Dict[str, Any]:
    source = raw_text or ""
    if not source:
        return {}

    def _find(pattern: str) -> Optional[str]:
        match = re.search(pattern, source, flags=re.IGNORECASE)
        if not match:
            return None
        value = str(match.group(1) or "").strip()
        return value or None

    issue_raw = _find(r":?31C:\s*([^\n\r]+)")
    expiry_raw = _find(r":?31D:\s*([^\n\r]+)")
    latest_raw = _find(r":?44C:\s*([^\n\r]+)")

    timeline: Dict[str, Any] = {}
    issue_date = _coerce_mt700_date_iso(issue_raw)
    expiry_date = _coerce_mt700_date_iso(expiry_raw)
    latest_shipment_date = _coerce_mt700_date_iso(latest_raw)

    if issue_date:
        timeline["issue_date"] = issue_date
    if expiry_date:
        timeline["expiry_date"] = expiry_date
    if latest_shipment_date:
        timeline["latest_shipment_date"] = latest_shipment_date

    if expiry_raw:
        place = re.sub(r"^\s*\d{6,8}", "", expiry_raw).strip(" ,-/")
        if place:
            timeline["place_of_expiry"] = re.sub(r"\s+", " ", place)

    return timeline


def _shape_lc_financial_payload(
    payload: Dict[str, Any],
    *,
    lc_subtype: str,
    raw_text: str,
    source_type: str,
    lc_format: str,
    allow_text_backfill: bool = True,
) -> Dict[str, Any]:
    shaped = dict(payload or {})
    shaped["raw_text"] = raw_text
    shaped["source_type"] = source_type
    shaped["format"] = lc_format
    shaped["lc_subtype"] = lc_subtype
    shaped["lc_family"] = "lc_financial_undertakings"

    def _first(*values):
        for value in values:
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            return value
        return None

    applicant = shaped.get("applicant")
    beneficiary = shaped.get("beneficiary")
    issuing_bank = shaped.get("issuing_bank")
    advising_bank = shaped.get("advising_bank")
    amount = shaped.get("amount")
    ports = shaped.get("ports") if isinstance(shaped.get("ports"), dict) else {}
    if isinstance(applicant, dict):
        applicant_address = applicant.get("address") if isinstance(applicant.get("address"), dict) else {}
        shaped["applicant_country"] = _first(
            shaped.get("applicant_country"),
            applicant.get("country"),
            applicant.get("country_name"),
            applicant_address.get("country"),
            applicant_address.get("country_name"),
        )
        shaped["applicant"] = applicant.get("name") or applicant.get("value")
    if isinstance(beneficiary, dict):
        beneficiary_address = beneficiary.get("address") if isinstance(beneficiary.get("address"), dict) else {}
        shaped["beneficiary_country"] = _first(
            shaped.get("beneficiary_country"),
            beneficiary.get("country"),
            beneficiary.get("country_name"),
            beneficiary_address.get("country"),
            beneficiary_address.get("country_name"),
        )
        shaped["beneficiary"] = beneficiary.get("name") or beneficiary.get("value")
    if isinstance(issuing_bank, dict):
        issuing_bank_address = issuing_bank.get("address") if isinstance(issuing_bank.get("address"), dict) else {}
        shaped["issuing_bank_country"] = _first(
            shaped.get("issuing_bank_country"),
            issuing_bank.get("country"),
            issuing_bank.get("country_name"),
            issuing_bank_address.get("country"),
            issuing_bank_address.get("country_name"),
        )
    if isinstance(advising_bank, dict):
        advising_bank_address = advising_bank.get("address") if isinstance(advising_bank.get("address"), dict) else {}
        shaped["advising_bank_country"] = _first(
            shaped.get("advising_bank_country"),
            advising_bank.get("country"),
            advising_bank.get("country_name"),
            advising_bank_address.get("country"),
            advising_bank_address.get("country_name"),
        )
    if isinstance(amount, dict):
        shaped["amount"] = amount.get("value") or amount.get("amount")
        shaped["currency"] = _first(shaped.get("currency"), amount.get("currency"))
    if ports:
        shaped["port_of_loading"] = _first(
            shaped.get("port_of_loading"),
            ports.get("loading"),
            ports.get("port_of_loading"),
        )
        shaped["port_of_discharge"] = _first(
            shaped.get("port_of_discharge"),
            ports.get("discharge"),
            ports.get("port_of_discharge"),
        )

    shaped["applicant"] = _first(shaped.get("applicant"), _extract_label_value(raw_text, ["applicant", "buyer", "importer"]) if allow_text_backfill else None)
    shaped["beneficiary"] = _first(shaped.get("beneficiary"), _extract_label_value(raw_text, ["beneficiary", "seller", "exporter"]) if allow_text_backfill else None)
    shaped["amount"] = _first(shaped.get("amount"), _extract_amount_value(raw_text, ["amount", "guarantee amount", "credit amount"]) if allow_text_backfill else None)
    shaped["currency"] = _first(shaped.get("currency"), _extract_label_value(raw_text, ["currency"]) if allow_text_backfill else None)
    shaped["lc_number"] = _first(
        shaped.get("lc_number"),
        shaped.get("number"),
        shaped.get("reference"),
        _extract_label_value(raw_text, ["lc number", "credit number", "reference number"]) if allow_text_backfill else None,
    )
    shaped["guarantee_reference"] = _first(
        shaped.get("guarantee_reference"),
        _extract_label_value(raw_text, ["guarantee no", "guarantee number", "reference number"]) if allow_text_backfill else None,
    )

    if lc_format == "mt700":
        mt700_timeline = _extract_mt700_timeline_fields(raw_text)
        issue_date = mt700_timeline.get("issue_date")
        expiry_date = mt700_timeline.get("expiry_date")
        latest_shipment_date = mt700_timeline.get("latest_shipment_date")
        place_of_expiry = mt700_timeline.get("place_of_expiry")

        if issue_date:
            shaped["issue_date"] = issue_date
        if expiry_date:
            shaped["expiry_date"] = expiry_date
        if latest_shipment_date:
            shaped["latest_shipment_date"] = latest_shipment_date
            shaped["latest_shipment"] = latest_shipment_date
        if place_of_expiry:
            shaped["place_of_expiry"] = place_of_expiry

        timeline = shaped.get("timeline") if isinstance(shaped.get("timeline"), dict) else {}
        if issue_date:
            timeline["issue_date"] = issue_date
        if expiry_date:
            timeline["expiry_date"] = expiry_date
        if latest_shipment_date:
            timeline["latest_shipment"] = latest_shipment_date
        if place_of_expiry:
            timeline["place_of_expiry"] = place_of_expiry
        if timeline:
            shaped["timeline"] = timeline

        dates = shaped.get("dates") if isinstance(shaped.get("dates"), dict) else {}
        if issue_date:
            dates["issue"] = issue_date
            dates["issue_date"] = issue_date
        if expiry_date:
            dates["expiry"] = expiry_date
            dates["expiry_date"] = expiry_date
        if latest_shipment_date:
            dates["latest_shipment"] = latest_shipment_date
            dates["latest_shipment_date"] = latest_shipment_date
        if place_of_expiry:
            dates["place_of_expiry"] = place_of_expiry
        if dates:
            shaped["dates"] = dates

    return _apply_canonical_normalization(shaped)


def _build_lc_user_facing_extracted_fields(payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    shaped = payload or {}

    def _first(*values):
        for value in values:
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            return value
        return None

    def _normalize_text_list(values: Any) -> List[str]:
        if not isinstance(values, list):
            return []
        items: List[str] = []
        seen = set()
        for value in values:
            if isinstance(value, dict):
                text = str(
                    value.get("raw_text")
                    or value.get("display_name")
                    or value.get("code")
                    or ""
                ).strip()
            else:
                text = str(value or "").strip()
            if not text:
                continue
            lowered = text.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            items.append(text)
        return items

    dates = shaped.get("dates") if isinstance(shaped.get("dates"), dict) else {}
    ports = shaped.get("ports") if isinstance(shaped.get("ports"), dict) else {}
    lc_classification = shaped.get("lc_classification") if isinstance(shaped.get("lc_classification"), dict) else {}
    mt700_payload = shaped.get("mt700") if isinstance(shaped.get("mt700"), dict) else {}
    mt700_timeline = _extract_mt700_timeline_fields(
        str(mt700_payload.get("raw_text") or shaped.get("raw_text") or "")
    )

    required_documents = _normalize_text_list(
        _first(
            shaped.get("required_documents_detailed"),
            lc_classification.get("required_documents"),
            shaped.get("required_documents"),
        )
    )
    requirement_conditions = _normalize_text_list(
        _first(
            shaped.get("requirement_conditions"),
            lc_classification.get("requirement_conditions"),
        )
    )
    unmapped_requirements = _normalize_text_list(
        _first(
            shaped.get("unmapped_requirements"),
            lc_classification.get("unmapped_requirements"),
        )
    )

    user_facing_fields = {
        "lc_number": _first(shaped.get("lc_number"), shaped.get("number"), shaped.get("reference")),
        "issue_date": _first(
            mt700_timeline.get("issue_date"),
            shaped.get("issue_date"),
            dates.get("issue"),
            dates.get("issue_date"),
        ),
        "expiry_date": _first(
            mt700_timeline.get("expiry_date"),
            shaped.get("expiry_date"),
            dates.get("expiry"),
            dates.get("expiry_date"),
        ),
        "latest_shipment_date": _first(
            mt700_timeline.get("latest_shipment_date"),
            shaped.get("latest_shipment_date"),
            shaped.get("latest_shipment"),
            dates.get("latest_shipment"),
            dates.get("latest_shipment_date"),
        ),
        "place_of_expiry": _first(
            mt700_timeline.get("place_of_expiry"),
            shaped.get("place_of_expiry"),
            dates.get("place_of_expiry"),
        ),
        "applicant": shaped.get("applicant"),
        "beneficiary": shaped.get("beneficiary"),
        "issuing_bank": shaped.get("issuing_bank"),
        "advising_bank": shaped.get("advising_bank"),
        "port_of_loading": _first(
            shaped.get("port_of_loading"),
            ports.get("loading"),
            ports.get("port_of_loading"),
        ),
        "port_of_discharge": _first(
            shaped.get("port_of_discharge"),
            ports.get("discharge"),
            ports.get("port_of_discharge"),
        ),
        "amount": shaped.get("amount"),
        "currency": shaped.get("currency"),
        "incoterm": shaped.get("incoterm"),
        "ucp_reference": shaped.get("ucp_reference"),
        "goods_description": shaped.get("goods_description"),
        "exporter_bin": shaped.get("exporter_bin"),
        "exporter_tin": shaped.get("exporter_tin"),
        "documents_required": required_documents,
        "requirement_conditions": requirement_conditions,
        "unmapped_requirements": unmapped_requirements,
        "additional_conditions": _normalize_text_list(shaped.get("additional_conditions")),
    }

    return {
        key: value
        for key, value in user_facing_fields.items()
        if value not in (None, "", [])
    }


def _assess_insurance_completeness(payload: Optional[Dict[str, Any]], *, insurance_subtype: str) -> Dict[str, Any]:
    attestation_style_subtypes = {
        "beneficiary_certificate",
        "manufacturer_certificate",
        "manufacturers_certificate",
        "conformity_certificate",
        "certificate_of_conformity",
        "non_manipulation_certificate",
        "halal_certificate",
        "kosher_certificate",
        "organic_certificate",
    }
    subtype_required = {
        "insurance_policy": ["policy_number", "insured_amount"],
        "insurance_certificate": ["policy_number", "insured_amount"],
    }
    if insurance_subtype in attestation_style_subtypes:
        fields = payload or {}
        core_fields = ["issuer_name", "issue_date", "lc_reference", "certificate_number"]
        found_core = [field for field in core_fields if _is_populated_field_value(fields.get(field))]
        required_total = len(core_fields)
        required_found = len(found_core)
        parse_complete = required_found >= 1
        metrics = {
            "required_fields": list(core_fields),
            "required_total": required_total,
            "required_found": required_found,
            "missing_required_fields": [] if parse_complete else ["issuer_name", "issue_date", "lc_reference"],
            "required_ratio": round((required_found / required_total), 4) if required_total else 0.0,
        }
    else:
        required_fields = subtype_required.get(insurance_subtype, ["policy_number"])
        metrics = _assess_required_field_completeness(payload, required_fields)
        parse_complete = metrics.get("required_found", 0) >= max(1, min(2, metrics.get("required_total", 0)))
    metrics.update(
        {
            "parse_complete": parse_complete,
            "review_reasons": [],
            "extraction_resolution": _build_extraction_resolution_metrics(
                missing_required_fields=metrics.get("missing_required_fields") or [],
                parse_complete=parse_complete,
            ),
        }
    )
    return metrics


def _detect_insurance_subtype(*, filename: str, extracted_text: str) -> str:
    haystack = f"{filename or ''}\n{extracted_text or ''}".lower()
    checks = [
        ("insurance_policy", ["insurance policy", "policy"]),
        ("beneficiary_certificate", ["beneficiary certificate"]),
        ("manufacturer_certificate", ["manufacturer certificate", "manufacturer's certificate", "manufacturers certificate"]),
        ("conformity_certificate", ["conformity certificate", "certificate of conformity"]),
        ("non_manipulation_certificate", ["non-manipulation certificate"]),
        ("halal_certificate", ["halal certificate"]),
        ("kosher_certificate", ["kosher certificate"]),
        ("organic_certificate", ["organic certificate"]),
    ]
    for subtype, patterns in checks:
        if any(pattern in haystack for pattern in patterns):
            return subtype
    return "insurance_certificate"


def _shape_insurance_payload(
    payload: Dict[str, Any],
    *,
    insurance_subtype: str,
    raw_text: str,
    allow_text_backfill: bool = True,
) -> Dict[str, Any]:
    shaped = dict(payload or {})
    shaped["raw_text"] = raw_text
    shaped["insurance_subtype"] = insurance_subtype
    shaped["insurance_family"] = "insurance_compliance_special_certificates"

    def _first(*values):
        for value in values:
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            return value
        return None

    shaped["policy_number"] = _first(
        shaped.get("policy_number"),
        shaped.get("certificate_number"),
        _extract_label_value(
            raw_text,
            [
                "policy no",
                "policy number",
                "certificate no",
                "certificate number",
                "certificate ref",
                "cert ref",
                "beneficiary cert ref",
            ],
        ) if allow_text_backfill else None,
    )
    shaped["certificate_number"] = _first(shaped.get("certificate_number"), shaped.get("policy_number"))
    shaped["lc_reference"] = _first(
        shaped.get("lc_reference"),
        shaped.get("lc_number"),
        _extract_label_value(
            raw_text,
            [
                "lc no",
                "lc number",
                "lc ref",
                "lc reference",
                "letter of credit no",
                "letter of credit number",
                "credit number",
            ],
        ) if allow_text_backfill else None,
    )
    shaped["lc_number"] = _first(shaped.get("lc_number"), shaped.get("lc_reference"))
    shaped["insured_amount"] = _first(
        shaped.get("insured_amount"),
        _extract_amount_value(raw_text, ["insured amount", "sum insured", "coverage amount"]) if allow_text_backfill else None,
    )
    shaped["issuer_name"] = _first(
        shaped.get("issuer_name"),
        shaped.get("insurer"),
        shaped.get("issuing_authority"),
        _extract_label_value(raw_text, ["insurer", "insurance company", "underwriter", "issued by", "issuer"]) if allow_text_backfill else None,
    )
    return _apply_canonical_normalization(shaped)


def _assess_regulatory_completeness(payload: Optional[Dict[str, Any]], *, regulatory_subtype: str) -> Dict[str, Any]:
    if regulatory_subtype == "certificate_of_origin":
        metrics = _assess_coo_parse_completeness(payload)
        if metrics.get("parse_complete"):
            metrics["missing_required_fields"] = []
        metrics.update(
            {
                "review_reasons": [],
                "extraction_resolution": _build_extraction_resolution_metrics(
                    missing_required_fields=metrics.get("missing_required_fields") or [],
                    parse_complete=bool(metrics.get("parse_complete")),
                ),
            }
        )
        return metrics

    subtype_required = {
        "gsp_form_a": ["certificate_number", "country_of_origin"],
        "eur1_movement_certificate": ["certificate_number", "country_of_origin"],
        "customs_declaration": ["declaration_reference"],
        "export_license": ["license_number"],
        "import_license": ["license_number"],
        "phytosanitary_certificate": ["certificate_number", "issuing_authority"],
        "fumigation_certificate": ["certificate_number", "issuing_authority"],
        "health_certificate": ["certificate_number", "issuing_authority"],
        "veterinary_certificate": ["certificate_number", "issuing_authority"],
        "sanitary_certificate": ["certificate_number", "issuing_authority"],
        "cites_permit": ["permit_number"],
        "radiation_certificate": ["certificate_number"],
    }
    required_fields = subtype_required.get(regulatory_subtype, ["certificate_number"])
    metrics = _assess_required_field_completeness(payload, required_fields)
    parse_complete = metrics.get("required_found", 0) >= max(1, min(2, metrics.get("required_total", 0)))
    metrics.update(
        {
            "parse_complete": parse_complete,
            "review_reasons": [],
            "extraction_resolution": _build_extraction_resolution_metrics(
                missing_required_fields=metrics.get("missing_required_fields") or [],
                parse_complete=parse_complete,
            ),
        }
    )
    return metrics


def _detect_regulatory_subtype(*, filename: str, extracted_text: str) -> str:
    haystack = f"{filename or ''}\n{extracted_text or ''}".lower()
    checks = [
        ("gsp_form_a", ["gsp form a", "form a"]),
        ("eur1_movement_certificate", ["eur.1", "eur1", "movement certificate"]),
        ("customs_declaration", ["customs declaration"]),
        ("export_license", ["export license"]),
        ("import_license", ["import license"]),
        ("phytosanitary_certificate", ["phytosanitary"]),
        ("fumigation_certificate", ["fumigation"]),
        ("health_certificate", ["health certificate"]),
        ("veterinary_certificate", ["veterinary certificate"]),
        ("sanitary_certificate", ["sanitary certificate"]),
        ("cites_permit", ["cites permit"]),
        ("radiation_certificate", ["radiation certificate"]),
    ]
    for subtype, patterns in checks:
        if any(pattern in haystack for pattern in patterns):
            return subtype
    return "certificate_of_origin"


def _shape_regulatory_payload(
    payload: Dict[str, Any],
    *,
    regulatory_subtype: str,
    raw_text: str,
    allow_text_backfill: bool = True,
) -> Dict[str, Any]:
    shaped = dict(payload or {})
    shaped["raw_text"] = raw_text
    shaped["regulatory_subtype"] = regulatory_subtype
    shaped["regulatory_family"] = "origin_customs_regulatory"

    def _first(*values):
        for value in values:
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            return value
        return None

    shaped["certificate_number"] = _first(
        shaped.get("certificate_number"),
        _extract_label_value(raw_text, ["certificate no", "certificate number"]) if allow_text_backfill else None,
    )
    shaped["exporter_name"] = _first(
        shaped.get("exporter_name"),
        shaped.get("exporter"),
        _extract_label_value(raw_text, ["exporter", "seller", "consignor"]) if allow_text_backfill else None,
    )
    shaped["importer_name"] = _first(
        shaped.get("importer_name"),
        shaped.get("importer"),
        _extract_label_value(raw_text, ["importer", "buyer", "consignee"]) if allow_text_backfill else None,
    )
    shaped["goods_description"] = _first(
        shaped.get("goods_description"),
        shaped.get("goods"),
        _extract_label_value(raw_text, ["goods description", "description of goods", "goods", "commodity"]) if allow_text_backfill else None,
    )
    shaped["country_of_origin"] = _first(
        shaped.get("country_of_origin"),
        shaped.get("origin_country"),
        _extract_label_value(raw_text, ["country of origin", "origin"]) if allow_text_backfill else None,
    )
    shaped["issuing_authority"] = _first(
        shaped.get("issuing_authority"),
        shaped.get("certifying_authority"),
        _extract_label_value(raw_text, ["issued by", "issuing authority", "chamber of commerce", "authority"]) if allow_text_backfill else None,
    )
    shaped["license_number"] = _first(
        shaped.get("license_number"),
        _extract_label_value(raw_text, ["license no", "license number"]) if allow_text_backfill else None,
    )
    shaped["declaration_reference"] = _first(
        shaped.get("declaration_reference"),
        _extract_label_value(raw_text, ["declaration no", "declaration number", "customs declaration no"]) if allow_text_backfill else None,
    )
    shaped["permit_number"] = _first(
        shaped.get("permit_number"),
        _extract_label_value(raw_text, ["permit no", "permit number"]) if allow_text_backfill else None,
    )
    shaped["lc_reference"] = _first(
        shaped.get("lc_reference"),
        shaped.get("lc_number"),
        _extract_label_value(
            raw_text,
            [
                "lc no",
                "lc number",
                "lc ref",
                "lc reference",
                "letter of credit no",
                "letter of credit number",
            ],
        ) if allow_text_backfill else None,
    )
    shaped["lc_number"] = _first(shaped.get("lc_number"), shaped.get("lc_reference"))
    return _apply_canonical_normalization(shaped)


def _assess_inspection_completeness(payload: Optional[Dict[str, Any]], *, inspection_subtype: str) -> Dict[str, Any]:
    subtype_required = {
        "pre_shipment_inspection": ["inspection_result"],
        "quality_certificate": ["quality_finding"],
        "weight_certificate": ["gross_weight"],
        "measurement_certificate": ["measurement_value"],
        "analysis_certificate": ["analysis_result"],
        "lab_test_report": ["analysis_result"],
        "sgs_certificate": ["inspection_result"],
        "bureau_veritas_certificate": ["inspection_result"],
        "intertek_certificate": ["inspection_result"],
        "inspection_certificate": ["inspection_result"],
    }
    required_fields = subtype_required.get(inspection_subtype, ["inspection_agency", "inspection_result"])
    metrics = _assess_required_field_completeness(payload, required_fields)
    parse_complete = metrics.get("required_found", 0) >= max(1, min(2, metrics.get("required_total", 0)))
    metrics.update(
        {
            "parse_complete": parse_complete,
            "review_reasons": [],
            "extraction_resolution": _build_extraction_resolution_metrics(
                missing_required_fields=metrics.get("missing_required_fields") or [],
                parse_complete=parse_complete,
            ),
        }
    )
    return metrics


def _detect_inspection_subtype(*, filename: str, extracted_text: str) -> str:
    haystack = f"{filename or ''}\n{extracted_text or ''}".lower()
    checks = [
        ("pre_shipment_inspection", ["pre-shipment inspection", "pre shipment inspection", "psi"]),
        ("quality_certificate", ["quality certificate", "quality cert", "quality finding"]),
        ("weight_certificate", ["weight certificate", "weight list", "gross weight", "net weight"]),
        ("measurement_certificate", ["measurement certificate", "measurements", "dimension"]),
        ("analysis_certificate", ["analysis certificate", "analysis result", "chemical analysis"]),
        ("lab_test_report", ["lab test report", "laboratory test report", "lab report"]),
        ("sgs_certificate", ["sgs certificate", "sgs"]),
        ("bureau_veritas_certificate", ["bureau veritas certificate", "bureau veritas"]),
        ("intertek_certificate", ["intertek certificate", "intertek"]),
    ]
    for subtype, patterns in checks:
        if any(pattern in haystack for pattern in patterns):
            return subtype
    return "inspection_certificate"


def _shape_inspection_payload(
    payload: Dict[str, Any],
    *,
    inspection_subtype: str,
    raw_text: str,
    allow_text_backfill: bool = True,
) -> Dict[str, Any]:
    shaped = dict(payload or {})
    shaped["raw_text"] = raw_text
    shaped["inspection_subtype"] = inspection_subtype
    shaped["inspection_family"] = "inspection_testing_quality"

    def _first(*values):
        for value in values:
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            return value
        return None

    shaped["inspection_agency"] = _first(
        shaped.get("inspection_agency"),
        shaped.get("inspection_company"),
        _extract_label_value(raw_text, ["inspection company", "inspection agency", "inspector", "surveyed by", "inspection by"]) if allow_text_backfill else None,
    )
    shaped["inspection_result"] = _first(
        shaped.get("inspection_result"),
        shaped.get("inspection_results"),
        _extract_label_value(raw_text, ["inspection result", "findings", "observations", "results", "result"]) if allow_text_backfill else None,
    )
    shaped["quality_finding"] = _first(
        shaped.get("quality_finding"),
        shaped.get("inspection_result"),
        shaped.get("inspection_results"),
        _extract_label_value(raw_text, ["quality finding", "quality result"]) if allow_text_backfill else None,
    )
    shaped["analysis_result"] = _first(
        shaped.get("analysis_result"),
        shaped.get("inspection_result"),
        shaped.get("inspection_results"),
        _extract_label_value(raw_text, ["analysis result", "test result", "lab result"]) if allow_text_backfill else None,
    )
    shaped["gross_weight"] = _first(
        shaped.get("gross_weight"),
        _extract_label_value(raw_text, ["gross weight", "gross wt", "gross", "g/w", "g w"]) if allow_text_backfill else None,
    )
    shaped["net_weight"] = _first(
        shaped.get("net_weight"),
        _extract_label_value(raw_text, ["net weight", "net wt", "net", "n/w", "n w"]) if allow_text_backfill else None,
    )
    measurement_candidate = _first(
        shaped.get("measurement_value"),
        shaped.get("dimensions"),
        _extract_label_value(raw_text, ["measurements", "dimensions", "dimension", "size"]) if allow_text_backfill else None,
    )
    if isinstance(measurement_candidate, str):
        normalized_candidate = measurement_candidate.strip()
        upper_candidate = normalized_candidate.upper()
        if upper_candidate in {"CERTIFICATE", "MEASUREMENT CERTIFICATE", "MEASUREMENTS CERTIFICATE", "DIMENSION CERTIFICATE"}:
            measurement_candidate = None
    shaped["measurement_value"] = measurement_candidate
    return _apply_canonical_normalization(shaped)


def _assess_transport_completeness(payload: Optional[Dict[str, Any]], *, transport_subtype: str) -> Dict[str, Any]:
    subtype_required = {
        "air_waybill": ["airway_bill_number", "airport_of_departure", "airport_of_destination", "shipper", "consignee"],
        "sea_waybill": ["port_of_loading", "port_of_discharge", "shipper", "consignee"],
        "ocean_bill_of_lading": ["port_of_loading", "port_of_discharge", "shipper", "consignee"],
        "charter_party_bill_of_lading": ["carriage_vessel_name", "shipper", "consignee"],
        "house_bill_of_lading": ["transport_reference_number", "shipper", "consignee"],
        "master_bill_of_lading": ["transport_reference_number", "shipper", "consignee"],
        "multimodal_transport_document": ["transport_mode_chain", "port_of_loading", "port_of_discharge"],
        "railway_consignment_note": ["consignment_reference", "consignee"],
        "road_transport_document": ["consignment_reference", "consignee"],
        "courier_or_post_receipt_or_certificate_of_posting": ["consignment_reference", "consignee"],
        "forwarders_certificate_of_receipt": ["consignment_reference", "shipper"],
        "delivery_order": ["consignment_reference", "consignee"],
        "mates_receipt": ["carriage_vessel_name"],
        "shipping_company_certificate": ["carriage_vessel_name"],
        "bill_of_lading": ["port_of_loading", "port_of_discharge", "shipper", "consignee"],
    }
    required_fields = subtype_required.get(transport_subtype, ["shipper", "consignee"])
    metrics = _assess_required_field_completeness(payload, required_fields)
    parse_complete = metrics.get("required_found", 0) >= max(1, min(3, metrics.get("required_total", 0)))
    metrics.update(
        {
            "parse_complete": parse_complete,
            "review_reasons": [],
            "extraction_resolution": _build_extraction_resolution_metrics(
                missing_required_fields=metrics.get("missing_required_fields") or [],
                parse_complete=parse_complete,
            ),
        }
    )
    return metrics


def _shape_transport_payload(
    payload: Dict[str, Any],
    *,
    transport_subtype: str,
    raw_text: str,
    allow_text_backfill: bool = True,
) -> Dict[str, Any]:
    shaped = dict(payload or {})
    shaped["raw_text"] = raw_text
    shaped["transport_subtype"] = transport_subtype

    mode_map = {
        "air_waybill": ("transport_document", "air"),
        "sea_waybill": ("transport_document", "sea"),
        "ocean_bill_of_lading": ("transport_document", "sea"),
        "charter_party_bill_of_lading": ("transport_document", "sea"),
        "multimodal_transport_document": ("transport_document", "multimodal"),
        "railway_consignment_note": ("transport_document", "rail"),
        "road_transport_document": ("transport_document", "road"),
        "courier_or_post_receipt_or_certificate_of_posting": ("transport_document", "courier"),
        "forwarders_certificate_of_receipt": ("transport_document", "forwarder"),
        "house_bill_of_lading": ("transport_document", "sea"),
        "master_bill_of_lading": ("transport_document", "sea"),
        "delivery_order": ("transport_document", "delivery"),
        "mates_receipt": ("transport_document", "sea"),
        "shipping_company_certificate": ("transport_document", "sea"),
        "bill_of_lading": ("transport_document", "sea"),
    }
    family, mode = mode_map.get(transport_subtype, ("transport_document", "unknown"))
    shaped["transport_family"] = family
    shaped["transport_mode"] = mode

    def _first(*values):
        for value in values:
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            return value
        return None

    if transport_subtype == "air_waybill":
        shaped["airport_of_departure"] = _first(
            shaped.get("airport_of_departure"),
            shaped.get("port_of_loading"),
            _extract_label_value(raw_text, ["airport of departure", "departure airport"]) if allow_text_backfill else None,
        )
        shaped["airport_of_destination"] = _first(
            shaped.get("airport_of_destination"),
            shaped.get("port_of_discharge"),
            _extract_label_value(raw_text, ["airport of destination", "destination airport"]) if allow_text_backfill else None,
        )
        shaped["airway_bill_number"] = _first(
            shaped.get("airway_bill_number"),
            shaped.get("awb_number"),
            shaped.get("bl_number"),
            _extract_label_value(raw_text, ["awb no", "awb number", "air waybill no", "air waybill number"]) if allow_text_backfill else None,
        )
    elif transport_subtype in {"sea_waybill", "ocean_bill_of_lading", "charter_party_bill_of_lading", "house_bill_of_lading", "master_bill_of_lading", "mates_receipt", "shipping_company_certificate"}:
        shaped["transport_reference_number"] = _first(
            shaped.get("transport_reference_number"),
            shaped.get("bl_number"),
            shaped.get("bill_number"),
        )
        shaped["carriage_vessel_name"] = _first(shaped.get("carriage_vessel_name"), shaped.get("vessel_name"))
        shaped["carriage_voyage_number"] = _first(shaped.get("carriage_voyage_number"), shaped.get("voyage_number"))
    elif transport_subtype == "multimodal_transport_document":
        shaped["transport_mode_chain"] = _first(
            shaped.get("transport_mode_chain"),
            _extract_label_value(raw_text, ["mode chain", "modes of transport", "transport modes"]) if allow_text_backfill else None,
            "multimodal",
        )
    elif transport_subtype in {"railway_consignment_note", "road_transport_document", "courier_or_post_receipt_or_certificate_of_posting", "forwarders_certificate_of_receipt", "delivery_order"}:
        shaped["consignment_reference"] = _first(
            shaped.get("consignment_reference"),
            shaped.get("bl_number"),
            shaped.get("receipt_number"),
            _extract_label_value(raw_text, ["consignment note", "consignment no", "document no", "fcr no", "delivery order no", "courier receipt no", "post receipt no", "certificate of posting no"]) if allow_text_backfill else None,
        )

    return _apply_canonical_normalization(shaped)


def _normalize_lookup_key(value: str) -> str:
    compact = re.sub(r"[^a-z0-9]+", " ", str(value or "").strip().lower())
    return re.sub(r"\s+", " ", compact).strip()


def _normalize_country_value(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    raw = value.strip()
    if not raw:
        return value
    country = get_country_registry().resolve(raw)
    if country:
        return country.name
    return raw


def _normalize_port_value(value: Any, country_hint: Optional[str] = None) -> Dict[str, Any]:
    result = {"value": value, "code": None, "country_code": None, "country_name": None}
    if not isinstance(value, str):
        return result
    raw = value.strip()
    if not raw:
        result["value"] = raw
        return result
    hint = None
    if isinstance(country_hint, str) and country_hint.strip():
        country = get_country_registry().resolve(country_hint.strip())
        hint = country.alpha2 if country else country_hint.strip().upper()
    port = get_port_registry().resolve(raw, country_hint=hint)
    if port:
        result.update({
            "value": port.name,
            "code": port.code,
            "country_code": port.country_code,
            "country_name": port.country_name,
        })
        return result
    result["value"] = raw
    return result


def _normalize_currency_value(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    raw = value.strip()
    if not raw:
        return value
    registry = get_currency_registry()
    normalized = registry.normalize(raw)
    if normalized:
        return normalized
    token_match = re.search(r"\b([A-Z]{3})\b", raw.upper())
    if token_match and registry.is_valid(token_match.group(1)):
        return token_match.group(1)
    return raw


def _normalize_measurement_label(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    key = _normalize_lookup_key(value)
    return MEASUREMENT_LABEL_ALIASES.get(key, value.strip())


def _normalize_document_alias(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    key = _normalize_lookup_key(value)
    direct = CANONICAL_DOCUMENT_ALIASES.get(key)
    if direct:
        return direct
    snake = re.sub(r"\s+", "_", key)
    return CANONICAL_DOCUMENT_ALIASES.get(snake, value.strip())


# Legacy -> canonical field-name aliases. The vision LLM (and some regex
# parsers) return these alternate names and the rest of the pipeline wants
# the canonical form. Applied at the top of _apply_canonical_normalization
# so every shape function benefits without individual patching.
_FIELD_NAME_ALIASES: Dict[str, str] = {
    # Invoice
    "seller_name": "seller",
    "buyer_name": "buyer",
    "seller_address": "seller_address",
    "buyer_address": "buyer_address",
    "lc_reference": "lc_number",
    "buyer_po_number": "buyer_purchase_order_number",
    "purchase_order_number": "buyer_purchase_order_number",
    "po_number": "buyer_purchase_order_number",
    # Regulatory / COO
    "exporter_name": "exporter",
    "importer_name": "importer",
    "certifying_authority": "issuing_authority",
    "origin_country": "country_of_origin",
    # Packing list
    "packing_size_breakdown": "size_breakdown",
    "number_of_packages": "total_packages",
    # Transport / BL
    "bl_date": "issue_date",
    "bill_of_lading_number": "bl_number",
    # Insurance & attestation
    "insured_party": "beneficiary",
    "insurance_company": "issuer",
    # Inspection
    "inspection_number": "certificate_number",
    # BIN / TIN variants
    "exporter_bin_number": "exporter_bin",
    "exporter_tin_number": "exporter_tin",
    "bin_number": "exporter_bin",
    "tin_number": "exporter_tin",
    "bin": "exporter_bin",
    "tin": "exporter_tin",
    # LC MT700 field aliases — the vision LLM keeps returning these legacy
    # names even though the new schemas ask for the canonical ones.
    "lc_type": "form_of_documentary_credit",
    "form_of_doc_credit": "form_of_documentary_credit",
    "ucp_reference": "applicable_rules",
    "credit_form": "form_of_documentary_credit",
}


_AVAILABLE_BY_KEYWORDS = ("PAYMENT", "ACCEPTANCE", "NEGOTIATION", "DEFERRED", "MIXED")


def _split_lc_availability_value(payload: Dict[str, Any]) -> None:
    """Split a combined `available_with` value into available_with + available_by.

    Vision LLM often returns Field 41a's two halves glued together, e.g.
    `available_with = "ANY BANK IN USA / BY NEGOTIATION"` or just
    `available_with = "BY NEGOTIATION"`. We detect the method keywords
    (PAYMENT / ACCEPTANCE / NEGOTIATION / DEFERRED / MIXED) and lift them
    into the canonical `available_by` field.
    """
    raw = payload.get("available_with")
    if not isinstance(raw, str) or not raw.strip():
        return
    if payload.get("available_by"):
        return  # already set, don't overwrite
    text = raw.strip()
    upper = text.upper()
    matched_method: Optional[str] = None
    for kw in _AVAILABLE_BY_KEYWORDS:
        if kw in upper:
            matched_method = kw
            break
    if not matched_method:
        return
    payload["available_by"] = matched_method
    # Try to recover the bank-name half by stripping the "BY <METHOD>" tail.
    import re as _re
    cleaned = _re.sub(r"(?i)\bby\s+" + matched_method + r"\b.*$", "", text).strip(" /,;\n")
    if cleaned and cleaned.upper() != upper:
        payload["available_with"] = cleaned
    elif cleaned == "" or cleaned.upper() == matched_method:
        # The original value was JUST the method (e.g. "BY NEGOTIATION"),
        # not a real bank name. Clear available_with so the user can fill it.
        payload["available_with"] = None


def _split_lc_expiry_place(payload: Dict[str, Any]) -> None:
    """Recover `expiry_place` from a glued `expiry_date` like '2026-10-15USA'.

    The vision LLM sometimes leaves the place stuck on the end of the date
    when Field 31D is the unspaced SWIFT format `261015USA`.
    """
    if payload.get("expiry_place"):
        return
    expiry = payload.get("expiry_date")
    if not isinstance(expiry, str):
        return
    # Look for an ISO date prefix followed by trailing letters.
    import re as _re
    m = _re.match(r"(\d{4}-\d{2}-\d{2})\s*([A-Za-z][A-Za-z\s,]+)$", expiry.strip())
    if m:
        payload["expiry_date"] = m.group(1)
        payload["expiry_place"] = m.group(2).strip()


def _canonicalize_field_names(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Rename legacy field-name aliases to canonical names in-place.

    Preserves the original alias key too, so any downstream code that greps
    for the old name still works. Only copies the value to the canonical key
    when the canonical key isn't already populated with something non-empty.
    """
    if not isinstance(payload, dict):
        return payload
    for alias, canonical in _FIELD_NAME_ALIASES.items():
        if alias not in payload:
            continue
        alias_value = payload.get(alias)
        if alias_value is None or alias_value == "":
            continue
        existing = payload.get(canonical)
        # Only populate canonical when it's absent / empty.
        if existing is None or existing == "":
            payload[canonical] = alias_value
    # Value-level splits for Field 41a and 31D where the LLM glues two
    # things into one string.
    _split_lc_availability_value(payload)
    _split_lc_expiry_place(payload)
    return payload


def _apply_canonical_normalization(payload: Dict[str, Any]) -> Dict[str, Any]:
    shaped = _canonicalize_field_names(dict(payload or {}))
    normalization_meta = shaped.get("normalization") if isinstance(shaped.get("normalization"), dict) else {}

    for field in ("currency",):
        if field in shaped:
            original = shaped.get(field)
            normalized = _normalize_currency_value(original)
            shaped[field] = normalized
            if normalized != original:
                normalization_meta[field] = {"raw": original, "canonical": normalized}

    for field in (
        "country_of_origin",
        "origin_country",
        "country",
        "country_name",
        "applicant_country",
        "beneficiary_country",
        "issuing_bank_country",
        "advising_bank_country",
        "port_of_loading_country",
        "port_of_discharge_country",
    ):
        if field in shaped:
            original = shaped.get(field)
            normalized = _normalize_country_value(original)
            shaped[field] = normalized
            if normalized != original:
                normalization_meta[field] = {"raw": original, "canonical": normalized}

    country_hint = shaped.get("country_of_origin") or shaped.get("origin_country") or shaped.get("country") or shaped.get("country_name")
    port_fields = (
        "port_of_loading",
        "port_of_discharge",
        "port_of_receipt",
        "place_of_receipt",
        "place_of_delivery",
        "final_destination",
        "airport_of_departure",
        "airport_of_destination",
    )
    for field in port_fields:
        if field in shaped:
            original = shaped.get(field)
            port_norm = _normalize_port_value(original, country_hint=country_hint)
            shaped[field] = port_norm["value"]
            if port_norm.get("code"):
                normalization_meta[field] = {
                    "raw": original,
                    "canonical": port_norm["value"],
                    "unlocode": port_norm.get("code"),
                    "country_code": port_norm.get("country_code"),
                    "country_name": port_norm.get("country_name"),
                }
                shaped[f"{field}_unlocode"] = port_norm.get("code")
                if port_norm.get("country_code"):
                    shaped.setdefault(f"{field}_country_code", port_norm.get("country_code"))
                if port_norm.get("country_name"):
                    shaped.setdefault(f"{field}_country_name", port_norm.get("country_name"))

    for field in ("source_type", "supporting_subtype_guess", "document_type"):
        if field in shaped:
            original = shaped.get(field)
            normalized = _normalize_document_alias(original)
            shaped[field] = normalized
            if normalized != original:
                normalization_meta[field] = {"raw": original, "canonical": normalized}

    measurement_aliases = shaped.get("measurement_aliases") if isinstance(shaped.get("measurement_aliases"), dict) else {}
    for label_field, canonical_field in list(MEASUREMENT_LABEL_ALIASES.items()):
        if label_field in shaped and canonical_field not in shaped:
            shaped[canonical_field] = shaped.get(label_field)
            measurement_aliases[label_field] = canonical_field

    for key, value in list(shaped.items()):
        canonical_key = _normalize_measurement_label(key)
        if canonical_key != key and canonical_key not in shaped and value not in (None, ""):
            shaped[canonical_key] = value
            measurement_aliases[key] = canonical_key

    if measurement_aliases:
        shaped["measurement_aliases"] = measurement_aliases
        normalization_meta.setdefault("measurement_aliases", dict(measurement_aliases))

    if normalization_meta:
        shaped["normalization"] = normalization_meta

    shaped["lc_classification"] = build_lc_classification(shaped)
    return shaped


def _has_extracted_content(payload: Optional[Dict[str, Any]], candidate_fields: List[str]) -> bool:
    if not isinstance(payload, dict):
        return False
    for field in candidate_fields:
        value = payload.get(field)
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        if isinstance(value, (list, dict)) and not value:
            continue
        return True
    return False


def _extract_label_value(text: str, labels: List[str]) -> Optional[str]:
    source = text or ""
    for label in labels:
        pattern = rf"(?:{re.escape(label)})\s*[:\-]?\s*([^\n\r]+)"
        match = re.search(pattern, source, flags=re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            if value:
                return value
    return None


def _extract_amount_value(text: str, labels: List[str]) -> Optional[str]:
    source = text or ""
    for label in labels:
        pattern = rf"(?:{re.escape(label)})\s*[:\-]?\s*([A-Z]{{3}}\s*[0-9][0-9,\.]*|[0-9][0-9,\.]*\s*[A-Z]{{3}}|[0-9][0-9,\.]*)"
        match = re.search(pattern, source, flags=re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            if value:
                return value
    return None


def detect_lc_format(raw_lc_text: Optional[str]) -> str:
    if not raw_lc_text:
        return "unknown"
    stripped = raw_lc_text.strip()
    schema_type, _ = detect_iso20022_schema(raw_lc_text)
    if schema_type:
        return "iso20022"
    if stripped.startswith("<?xml") or stripped.startswith("<Document"):
        return "xml_other"
    lowered = raw_lc_text.lower()
    if re.search(r"(?im)^\s*:?\s*20\s*:\s*", raw_lc_text) and re.search(
        r"(?im)^\s*:?\s*(40A|40E|32B)\s*:\s*",
        raw_lc_text,
    ):
        return "mt700"
    if re.search(r"(?im)^\s*:?\s*(27|31C|45A|46A|47A)\s*:\s*", raw_lc_text):
        return "mt700"
    if any(token in lowered for token in ("letter of credit", "documentary credit", "standby letter of credit")):
        return "pdf_text"
    return "unknown"


_launch_pipeline_singleton: Optional[LaunchExtractionPipeline] = None


def get_launch_extraction_pipeline() -> LaunchExtractionPipeline:
    global _launch_pipeline_singleton
    if _launch_pipeline_singleton is None:
        _launch_pipeline_singleton = LaunchExtractionPipeline()
    return _launch_pipeline_singleton
