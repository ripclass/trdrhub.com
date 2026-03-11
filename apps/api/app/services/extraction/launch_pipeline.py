from __future__ import annotations

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
from app.services.extraction.iso20022_lc_extractor import extract_iso20022_with_ai_fallback

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
    "bill of lading": "bill_of_lading",
    "b/l": "bill_of_lading",
    "bl": "bill_of_lading",
    "sea waybill": "sea_waybill",
    "air waybill": "air_waybill",
    "awb": "air_waybill",
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
    ) -> Dict[str, Any]:
        extraction_artifacts_v1 = extraction_artifacts_v1 or {}
        normalized_doc_type = _canonicalize_launch_doc_type(str(document_type or "").strip().lower())
        quality_assessment = self._quality_gate.assess(
            extracted_text or "",
            ocr_confidence=extraction_artifacts_v1.get("ocr_confidence"),
            metadata=extraction_artifacts_v1,
        )

        if normalized_doc_type in {"letter_of_credit", "swift_message", "lc_application"}:
            return await self._process_lc_like(
                extracted_text=extracted_text,
                document_type=normalized_doc_type,
                filename=filename,
                quality_assessment=quality_assessment,
            )

        if normalized_doc_type in {"commercial_invoice", "proforma_invoice"}:
            return await self._process_invoice(
                extracted_text=extracted_text,
                filename=filename,
                quality_assessment=quality_assessment,
            )

        if normalized_doc_type == "bill_of_lading":
            return await self._process_bl(
                extracted_text=extracted_text,
                filename=filename,
                quality_assessment=quality_assessment,
            )

        if normalized_doc_type == "packing_list":
            return await self._process_packing_list(
                extracted_text=extracted_text,
                filename=filename,
                quality_assessment=quality_assessment,
            )

        if normalized_doc_type == "certificate_of_origin":
            return await self._process_certificate_of_origin(
                extracted_text=extracted_text,
                filename=filename,
                quality_assessment=quality_assessment,
            )

        if normalized_doc_type == "insurance_certificate":
            return await self._process_insurance_certificate(
                extracted_text=extracted_text,
                filename=filename,
                quality_assessment=quality_assessment,
            )

        if normalized_doc_type == "inspection_certificate":
            return await self._process_inspection_certificate(
                extracted_text=extracted_text,
                filename=filename,
                quality_assessment=quality_assessment,
            )

        if normalized_doc_type == "supporting_document":
            return await self._process_supporting_document(
                extracted_text=extracted_text,
                filename=filename,
                quality_assessment=quality_assessment,
            )

        return {"handled": False}

    async def _process_lc_like(self, *, extracted_text: str, document_type: str, filename: str, quality_assessment: Any) -> Dict[str, Any]:
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
                        "extracted_fields": iso_context,
                        "extraction_status": "success",
                        "extraction_method": iso_context.get("_extraction_method", "iso20022"),
                        "extraction_confidence": iso_context.get("_extraction_confidence", 0.0),
                    },
                    "has_structured_data": True,
                    "lc_number": iso_context.get("number"),
                    "validation_doc_type": None,
                    "post_validation_target": None,
                }

            lc_struct = await extract_lc_ai_first(extracted_text)
            extraction_status = lc_struct.get("_status", "unknown")
            if lc_struct and extraction_status != "failed":
                shaped_payload = _shape_lc_financial_payload(lc_struct, lc_subtype=lc_subtype, raw_text=extracted_text, source_type=document_type, lc_format=lc_format)
                lc_review = _assess_lc_financial_completeness(shaped_payload, lc_subtype=lc_subtype)
                return {
                    "handled": True,
                    "context_key": "lc",
                    "context_payload": {**shaped_payload, "lc_review": lc_review},
                    "doc_info_patch": {
                        **base_patch,
                        "lc_subtype": lc_subtype,
                        "lc_family": shaped_payload.get("lc_family"),
                        "extracted_fields": lc_struct.get("extracted_fields") if isinstance(lc_struct.get("extracted_fields"), dict) else lc_struct,
                        "extraction_status": "success" if lc_review.get("parse_complete") else "partial",
                        "extraction_method": lc_struct.get("_extraction_method", "unknown"),
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
                return {
                    "handled": True,
                    "context_key": "lc",
                    "context_payload": {**shaped_payload, "lc_review": lc_review},
                    "doc_info_patch": {
                        **base_patch,
                        "lc_subtype": lc_subtype,
                        "lc_family": shaped_payload.get("lc_family"),
                        "extracted_fields": lc_context,
                        "extraction_status": "success" if lc_review.get("parse_complete") else "partial",
                        "extraction_method": "regex_fallback",
                        "parse_complete": lc_review.get("parse_complete"),
                        "parse_completeness": lc_review.get("required_ratio"),
                        "missing_required_fields": lc_review.get("missing_required_fields", []),
                        "required_fields_found": lc_review.get("required_found"),
                        "required_fields_total": lc_review.get("required_total"),
                        "review_reasons": list(base_patch.get("review_reasons") or []) + list(lc_review.get("review_reasons") or []),
                    },
                    "has_structured_data": True,
                    "lc_number": shaped_payload.get("number") or shaped_payload.get("lc_number"),
                    "validation_doc_type": "lc",
                    "post_validation_target": "lc",
                }
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

    async def _process_invoice(self, *, extracted_text: str, filename: str, quality_assessment: Any) -> Dict[str, Any]:
        invoice_subtype = _detect_invoice_financial_subtype(filename=filename, extracted_text=extracted_text)
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
            invoice_struct = await extract_invoice_ai_first(extracted_text)
            extraction_status = invoice_struct.get("_status", "unknown")
            if invoice_struct and extraction_status != "failed":
                shaped_payload = _shape_invoice_financial_payload(invoice_struct, invoice_subtype=invoice_subtype, raw_text=extracted_text)
                invoice_review = _assess_invoice_financial_completeness(shaped_payload, invoice_subtype=invoice_subtype)
                return {
                    "handled": True,
                    "context_key": "invoice",
                    "context_payload": {**shaped_payload, "invoice_review": invoice_review},
                    "doc_info_patch": {
                        **base_patch,
                        "invoice_subtype": invoice_subtype,
                        "invoice_family": shaped_payload.get("invoice_family"),
                        "extracted_fields": invoice_struct.get("extracted_fields") if isinstance(invoice_struct.get("extracted_fields"), dict) else invoice_struct,
                        "extraction_status": "success" if invoice_review.get("parse_complete") else "partial",
                        "extraction_method": invoice_struct.get("_extraction_method", "unknown"),
                        "extraction_confidence": invoice_struct.get("_extraction_confidence", 0.0),
                        "ai_first_status": extraction_status,
                        "field_details": invoice_struct.get("_field_details"),
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
                    "post_validation_target": "invoice",
                }
        except Exception as exc:
            logger.warning("Launch pipeline invoice AI extraction failed for %s: %s", filename, exc, exc_info=True)

        try:
            invoice_fields = self._fallback_extractor.extract_fields(extracted_text, DocumentType.COMMERCIAL_INVOICE)
            invoice_context = _fields_to_flat_context(invoice_fields)
            if invoice_context:
                shaped_payload = _shape_invoice_financial_payload(invoice_context, invoice_subtype=invoice_subtype, raw_text=extracted_text)
                invoice_review = _assess_invoice_financial_completeness(shaped_payload, invoice_subtype=invoice_subtype)
                return {
                    "handled": True,
                    "context_key": "invoice",
                    "context_payload": {**shaped_payload, "invoice_review": invoice_review},
                    "doc_info_patch": {
                        **base_patch,
                        "invoice_subtype": invoice_subtype,
                        "invoice_family": shaped_payload.get("invoice_family"),
                        "extracted_fields": invoice_context,
                        "extraction_status": "success" if invoice_review.get("parse_complete") else "partial",
                        "extraction_method": "regex_fallback",
                        "field_details": invoice_context.get("_field_details"),
                        "parse_complete": invoice_review.get("parse_complete"),
                        "parse_completeness": invoice_review.get("required_ratio"),
                        "missing_required_fields": invoice_review.get("missing_required_fields", []),
                        "required_fields_found": invoice_review.get("required_found"),
                        "required_fields_total": invoice_review.get("required_total"),
                        "review_reasons": list(base_patch.get("review_reasons") or []) + list(invoice_review.get("review_reasons") or []),
                    },
                    "has_structured_data": True,
                    "validation_doc_type": "invoice",
                    "post_validation_target": "invoice",
                }
        except Exception as exc:
            logger.warning("Launch pipeline invoice regex fallback failed for %s: %s", filename, exc, exc_info=True)

        shaped_payload = _shape_invoice_financial_payload({}, invoice_subtype=invoice_subtype, raw_text=extracted_text)
        invoice_review = _assess_invoice_financial_completeness(shaped_payload, invoice_subtype=invoice_subtype)
        return {"handled": True, "context_key": "invoice", "context_payload": {**shaped_payload, "invoice_review": invoice_review}, "doc_info_patch": {**base_patch, "invoice_subtype": invoice_subtype, "invoice_family": shaped_payload.get("invoice_family"), "parse_complete": invoice_review.get("parse_complete"), "parse_completeness": invoice_review.get("required_ratio"), "missing_required_fields": invoice_review.get("missing_required_fields", []), "required_fields_found": invoice_review.get("required_found"), "required_fields_total": invoice_review.get("required_total"), "review_reasons": list(base_patch.get("review_reasons") or []) + list(invoice_review.get("review_reasons") or []), "extraction_status": "failed", "extraction_error": "launch_pipeline_invoice_extraction_failed"}, "has_structured_data": False, "validation_doc_type": None, "post_validation_target": None}

    async def _process_bl(self, *, extracted_text: str, filename: str, quality_assessment: Any) -> Dict[str, Any]:
        transport_subtype = _detect_transport_subtype(filename=filename, extracted_text=extracted_text)
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
            bl_struct = await extract_bl_ai_first(extracted_text)
            extraction_status = bl_struct.get("_status", "unknown")
            if bl_struct and extraction_status != "failed":
                shaped_payload = _shape_transport_payload(bl_struct, transport_subtype=transport_subtype, raw_text=extracted_text)
                transport_review = _assess_transport_completeness(shaped_payload, transport_subtype=transport_subtype)
                return {
                    "handled": True,
                    "context_key": "bill_of_lading",
                    "context_payload": {**shaped_payload, "transport_review": transport_review},
                    "doc_info_patch": {
                        **base_patch,
                        "transport_subtype": transport_subtype,
                        "extracted_fields": bl_struct.get("extracted_fields") if isinstance(bl_struct.get("extracted_fields"), dict) else bl_struct,
                        "extraction_status": "success" if transport_review.get("parse_complete") else "partial",
                        "extraction_method": bl_struct.get("_extraction_method", "unknown"),
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
                    "post_validation_target": "bill_of_lading",
                }
        except Exception as exc:
            logger.warning("Launch pipeline BL AI extraction failed for %s: %s", filename, exc, exc_info=True)

        try:
            bl_fields = self._fallback_extractor.extract_fields(extracted_text, DocumentType.BILL_OF_LADING)
            bl_context = _fields_to_flat_context(bl_fields)
            if bl_context:
                shaped_payload = _shape_transport_payload(bl_context, transport_subtype=transport_subtype, raw_text=extracted_text)
                transport_review = _assess_transport_completeness(shaped_payload, transport_subtype=transport_subtype)
                return {
                    "handled": True,
                    "context_key": "bill_of_lading",
                    "context_payload": {**shaped_payload, "transport_review": transport_review},
                    "doc_info_patch": {
                        **base_patch,
                        "transport_subtype": transport_subtype,
                        "extracted_fields": bl_context,
                        "extraction_status": "success" if transport_review.get("parse_complete") else "partial",
                        "extraction_method": "regex_fallback",
                        "field_details": bl_context.get("_field_details"),
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
                    "post_validation_target": "bill_of_lading",
                }
        except Exception as exc:
            logger.warning("Launch pipeline BL regex fallback failed for %s: %s", filename, exc, exc_info=True)

        shaped_payload = _shape_transport_payload({}, transport_subtype=transport_subtype, raw_text=extracted_text)
        transport_review = _assess_transport_completeness(shaped_payload, transport_subtype=transport_subtype)
        return {"handled": True, "context_key": "bill_of_lading", "context_payload": {**shaped_payload, "transport_review": transport_review}, "doc_info_patch": {**base_patch, "transport_subtype": transport_subtype, "transport_family": shaped_payload.get("transport_family"), "transport_mode": shaped_payload.get("transport_mode"), "parse_complete": transport_review.get("parse_complete"), "parse_completeness": transport_review.get("required_ratio"), "missing_required_fields": transport_review.get("missing_required_fields", []), "required_fields_found": transport_review.get("required_found"), "required_fields_total": transport_review.get("required_total"), "review_reasons": list(base_patch.get("review_reasons") or []) + list(transport_review.get("review_reasons") or []), "extraction_status": "failed", "extraction_error": "launch_pipeline_bl_extraction_failed"}, "has_structured_data": False, "validation_doc_type": None, "post_validation_target": None}

    async def _process_packing_list(self, *, extracted_text: str, filename: str, quality_assessment: Any) -> Dict[str, Any]:
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
            packing_struct = await extract_packing_list_ai_first(extracted_text)
            extraction_status = packing_struct.get("_status", "unknown")
            if packing_struct and extraction_status != "failed":
                return {
                    "handled": True,
                    "context_key": "packing_list",
                    "context_payload": _apply_canonical_normalization({**packing_struct, "raw_text": extracted_text}),
                    "doc_info_patch": {
                        **base_patch,
                        "extracted_fields": packing_struct.get("extracted_fields") if isinstance(packing_struct.get("extracted_fields"), dict) else packing_struct,
                        "extraction_status": "success",
                        "extraction_method": packing_struct.get("_extraction_method", "unknown"),
                        "extraction_confidence": packing_struct.get("_extraction_confidence", 0.0),
                        "ai_first_status": extraction_status,
                        "field_details": packing_struct.get("_field_details"),
                        "status_counts": packing_struct.get("_status_counts"),
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
                return {
                    "handled": True,
                    "context_key": "packing_list",
                    "context_payload": _apply_canonical_normalization({**packing_context, "raw_text": extracted_text}),
                    "doc_info_patch": {
                        **base_patch,
                        "extracted_fields": packing_context,
                        "extraction_status": "success",
                        "extraction_method": "regex_fallback",
                        "field_details": packing_context.get("_field_details"),
                    },
                    "has_structured_data": True,
                    "validation_doc_type": "packing_list",
                    "post_validation_target": "packing_list",
                }
        except Exception as exc:
            logger.warning("Launch pipeline packing list regex fallback failed for %s: %s", filename, exc, exc_info=True)

        return {"handled": True, "context_key": "packing_list", "context_payload": {"raw_text": extracted_text}, "doc_info_patch": {**base_patch, "extraction_status": "failed", "extraction_error": "launch_pipeline_packing_list_extraction_failed"}, "has_structured_data": False, "validation_doc_type": None, "post_validation_target": None}

    async def _process_certificate_of_origin(self, *, extracted_text: str, filename: str, quality_assessment: Any) -> Dict[str, Any]:
        regulatory_subtype = _detect_regulatory_subtype(filename=filename, extracted_text=extracted_text)
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
            coo_struct = await extract_coo_ai_first(extracted_text)
            extraction_status = coo_struct.get("_status", "unknown")
            if coo_struct and extraction_status != "failed":
                shaped_payload = _shape_regulatory_payload(coo_struct, regulatory_subtype=regulatory_subtype, raw_text=extracted_text)
                regulatory_review = _assess_regulatory_completeness(shaped_payload, regulatory_subtype=regulatory_subtype)
                effective_extraction_status = "success" if regulatory_review.get("parse_complete") else "partial"
                return {
                    "handled": True,
                    "context_key": "certificate_of_origin",
                    "context_payload": {**shaped_payload, "regulatory_review": regulatory_review},
                    "doc_info_patch": {
                        **base_patch,
                        "regulatory_subtype": regulatory_subtype,
                        "regulatory_family": shaped_payload.get("regulatory_family"),
                        "extracted_fields": coo_struct.get("extracted_fields") if isinstance(coo_struct.get("extracted_fields"), dict) else coo_struct,
                        "extraction_status": effective_extraction_status,
                        "parse_complete": regulatory_review.get("parse_complete"),
                        "parse_completeness": regulatory_review.get("required_ratio"),
                        "missing_required_fields": regulatory_review.get("missing_required_fields", []),
                        "required_fields_found": regulatory_review.get("required_found"),
                        "required_fields_total": regulatory_review.get("required_total"),
                        "extraction_method": coo_struct.get("_extraction_method", "unknown"),
                        "extraction_confidence": coo_struct.get("_extraction_confidence", 0.0),
                        "ai_first_status": extraction_status,
                        "field_details": coo_struct.get("_field_details"),
                        "status_counts": coo_struct.get("_status_counts"),
                        "review_reasons": list(base_patch.get("review_reasons") or []) + list(regulatory_review.get("review_reasons") or []),
                    },
                    "has_structured_data": True,
                    "validation_doc_type": "certificate_of_origin",
                    "post_validation_target": "certificate_of_origin",
                }
        except Exception as exc:
            logger.warning("Launch pipeline COO AI extraction failed for %s: %s", filename, exc, exc_info=True)

        try:
            coo_fields = self._fallback_extractor.extract_fields(extracted_text, DocumentType.CERTIFICATE_OF_ORIGIN)
            coo_context = _fields_to_flat_context(coo_fields)
            if coo_context:
                shaped_payload = _shape_regulatory_payload(coo_context, regulatory_subtype=regulatory_subtype, raw_text=extracted_text)
                regulatory_review = _assess_regulatory_completeness(shaped_payload, regulatory_subtype=regulatory_subtype)
                effective_extraction_status = "success" if regulatory_review.get("parse_complete") else "partial"
                return {
                    "handled": True,
                    "context_key": "certificate_of_origin",
                    "context_payload": {**shaped_payload, "regulatory_review": regulatory_review},
                    "doc_info_patch": {
                        **base_patch,
                        "regulatory_subtype": regulatory_subtype,
                        "regulatory_family": shaped_payload.get("regulatory_family"),
                        "extracted_fields": coo_context,
                        "extraction_status": effective_extraction_status,
                        "parse_complete": regulatory_review.get("parse_complete"),
                        "parse_completeness": regulatory_review.get("required_ratio"),
                        "missing_required_fields": regulatory_review.get("missing_required_fields", []),
                        "required_fields_found": regulatory_review.get("required_found"),
                        "required_fields_total": regulatory_review.get("required_total"),
                        "extraction_method": "regex_fallback",
                        "field_details": coo_context.get("_field_details"),
                        "review_reasons": list(base_patch.get("review_reasons") or []) + list(regulatory_review.get("review_reasons") or []),
                    },
                    "has_structured_data": True,
                    "validation_doc_type": "certificate_of_origin",
                    "post_validation_target": "certificate_of_origin",
                }
        except Exception as exc:
            logger.warning("Launch pipeline COO regex fallback failed for %s: %s", filename, exc, exc_info=True)

        shaped_payload = _shape_regulatory_payload({}, regulatory_subtype=regulatory_subtype, raw_text=extracted_text)
        regulatory_review = _assess_regulatory_completeness(shaped_payload, regulatory_subtype=regulatory_subtype)
        return {"handled": True, "context_key": "certificate_of_origin", "context_payload": {**shaped_payload, "regulatory_review": regulatory_review}, "doc_info_patch": {**base_patch, "regulatory_subtype": regulatory_subtype, "regulatory_family": shaped_payload.get("regulatory_family"), "parse_complete": regulatory_review.get("parse_complete"), "parse_completeness": regulatory_review.get("required_ratio"), "missing_required_fields": regulatory_review.get("missing_required_fields", []), "required_fields_found": regulatory_review.get("required_found"), "required_fields_total": regulatory_review.get("required_total"), "review_reasons": list(base_patch.get("review_reasons") or []) + list(regulatory_review.get("review_reasons") or []), "extraction_status": "failed", "extraction_error": "launch_pipeline_coo_extraction_failed"}, "has_structured_data": False, "validation_doc_type": None, "post_validation_target": None}

    async def _process_insurance_certificate(self, *, extracted_text: str, filename: str, quality_assessment: Any) -> Dict[str, Any]:
        insurance_subtype = _detect_insurance_subtype(filename=filename, extracted_text=extracted_text)
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
            insurance_struct = await extract_insurance_ai_first(extracted_text)
            extraction_status = insurance_struct.get("_status", "unknown")
            if insurance_struct and extraction_status != "failed":
                shaped_payload = _shape_insurance_payload(insurance_struct, insurance_subtype=insurance_subtype, raw_text=extracted_text)
                insurance_review = _assess_insurance_completeness(shaped_payload, insurance_subtype=insurance_subtype)
                return {
                    "handled": True,
                    "context_key": "insurance_certificate",
                    "context_payload": {**shaped_payload, "insurance_review": insurance_review},
                    "doc_info_patch": {
                        **base_patch,
                        "insurance_subtype": insurance_subtype,
                        "insurance_family": shaped_payload.get("insurance_family"),
                        "extracted_fields": insurance_struct.get("extracted_fields") if isinstance(insurance_struct.get("extracted_fields"), dict) else insurance_struct,
                        "extraction_status": "success" if insurance_review.get("parse_complete") else "partial",
                        "extraction_method": insurance_struct.get("_extraction_method", "unknown"),
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
                    "post_validation_target": "insurance_certificate",
                }
        except Exception as exc:
            logger.warning("Launch pipeline insurance AI extraction failed for %s: %s", filename, exc, exc_info=True)

        try:
            insurance_fields = self._fallback_extractor.extract_fields(extracted_text, DocumentType.INSURANCE_CERTIFICATE)
            insurance_context = _fields_to_flat_context(insurance_fields)
            if insurance_context:
                shaped_payload = _shape_insurance_payload(insurance_context, insurance_subtype=insurance_subtype, raw_text=extracted_text)
                insurance_review = _assess_insurance_completeness(shaped_payload, insurance_subtype=insurance_subtype)
                return {
                    "handled": True,
                    "context_key": "insurance_certificate",
                    "context_payload": {**shaped_payload, "insurance_review": insurance_review},
                    "doc_info_patch": {
                        **base_patch,
                        "insurance_subtype": insurance_subtype,
                        "insurance_family": shaped_payload.get("insurance_family"),
                        "extracted_fields": insurance_context,
                        "extraction_status": "success" if insurance_review.get("parse_complete") else "partial",
                        "extraction_method": "regex_fallback",
                        "field_details": insurance_context.get("_field_details"),
                        "parse_complete": insurance_review.get("parse_complete"),
                        "parse_completeness": insurance_review.get("required_ratio"),
                        "missing_required_fields": insurance_review.get("missing_required_fields", []),
                        "required_fields_found": insurance_review.get("required_found"),
                        "required_fields_total": insurance_review.get("required_total"),
                        "review_reasons": list(base_patch.get("review_reasons") or []) + list(insurance_review.get("review_reasons") or []),
                    },
                    "has_structured_data": True,
                    "validation_doc_type": "insurance",
                    "post_validation_target": "insurance_certificate",
                }
        except Exception as exc:
            logger.warning("Launch pipeline insurance regex fallback failed for %s: %s", filename, exc, exc_info=True)

        shaped_payload = _shape_insurance_payload({}, insurance_subtype=insurance_subtype, raw_text=extracted_text)
        insurance_review = _assess_insurance_completeness(shaped_payload, insurance_subtype=insurance_subtype)
        return {"handled": True, "context_key": "insurance_certificate", "context_payload": {**shaped_payload, "insurance_review": insurance_review}, "doc_info_patch": {**base_patch, "insurance_subtype": insurance_subtype, "insurance_family": shaped_payload.get("insurance_family"), "parse_complete": insurance_review.get("parse_complete"), "parse_completeness": insurance_review.get("required_ratio"), "missing_required_fields": insurance_review.get("missing_required_fields", []), "required_fields_found": insurance_review.get("required_found"), "required_fields_total": insurance_review.get("required_total"), "review_reasons": list(base_patch.get("review_reasons") or []) + list(insurance_review.get("review_reasons") or []), "extraction_status": "failed", "extraction_error": "launch_pipeline_insurance_extraction_failed"}, "has_structured_data": False, "validation_doc_type": None, "post_validation_target": None}

    async def _process_supporting_document(self, *, extracted_text: str, filename: str, quality_assessment: Any) -> Dict[str, Any]:
        supporting_guess = _guess_supporting_document_subtype(filename=filename, extracted_text=extracted_text)
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
        return {
            "handled": True,
            "context_key": "supporting_document",
            "context_payload": payload,
            "doc_info_patch": {
                **base_patch,
                "extraction_status": "partial",
                "supporting_subtype_guess": supporting_guess.get("subtype"),
                "supporting_family_guess": supporting_guess.get("family"),
                "guess_confidence": supporting_guess.get("confidence"),
                "review_reasons": review_reasons,
            },
            "has_structured_data": True,
            "validation_doc_type": None,
            "post_validation_target": None,
        }

    async def _process_inspection_certificate(self, *, extracted_text: str, filename: str, quality_assessment: Any) -> Dict[str, Any]:
        inspection_subtype = _detect_inspection_subtype(filename=filename, extracted_text=extracted_text)
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
            inspection_struct = await extract_inspection_ai_first(extracted_text)
            extraction_status = inspection_struct.get("_status", "unknown")
            if inspection_struct and extraction_status != "failed":
                shaped_payload = _shape_inspection_payload(inspection_struct, inspection_subtype=inspection_subtype, raw_text=extracted_text)
                inspection_review = _assess_inspection_completeness(shaped_payload, inspection_subtype=inspection_subtype)
                return {
                    "handled": True,
                    "context_key": "inspection_certificate",
                    "context_payload": {**shaped_payload, "inspection_review": inspection_review},
                    "doc_info_patch": {
                        **base_patch,
                        "inspection_subtype": inspection_subtype,
                        "extracted_fields": inspection_struct.get("extracted_fields") if isinstance(inspection_struct.get("extracted_fields"), dict) else inspection_struct,
                        "extraction_status": "success" if inspection_review.get("parse_complete") else "partial",
                        "extraction_method": inspection_struct.get("_extraction_method", "unknown"),
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
                    "post_validation_target": "inspection_certificate",
                }
        except Exception as exc:
            logger.warning("Launch pipeline inspection AI extraction failed for %s: %s", filename, exc, exc_info=True)

        try:
            inspection_fields = self._fallback_extractor.extract_fields(extracted_text, DocumentType.INSPECTION_CERTIFICATE)
            inspection_context = _fields_to_flat_context(inspection_fields)
            if inspection_context:
                shaped_payload = _shape_inspection_payload(inspection_context, inspection_subtype=inspection_subtype, raw_text=extracted_text)
                inspection_review = _assess_inspection_completeness(shaped_payload, inspection_subtype=inspection_subtype)
                return {
                    "handled": True,
                    "context_key": "inspection_certificate",
                    "context_payload": {**shaped_payload, "inspection_review": inspection_review},
                    "doc_info_patch": {
                        **base_patch,
                        "inspection_subtype": inspection_subtype,
                        "extracted_fields": inspection_context,
                        "extraction_status": "success" if inspection_review.get("parse_complete") else "partial",
                        "extraction_method": "regex_fallback",
                        "field_details": inspection_context.get("_field_details"),
                        "inspection_family": shaped_payload.get("inspection_family"),
                        "parse_complete": inspection_review.get("parse_complete"),
                        "parse_completeness": inspection_review.get("required_ratio"),
                        "missing_required_fields": inspection_review.get("missing_required_fields", []),
                        "required_fields_found": inspection_review.get("required_found"),
                        "required_fields_total": inspection_review.get("required_total"),
                        "review_reasons": list(base_patch.get("review_reasons") or []) + list(inspection_review.get("review_reasons") or []),
                    },
                    "has_structured_data": True,
                    "validation_doc_type": "inspection",
                    "post_validation_target": "inspection_certificate",
                }
        except Exception as exc:
            logger.warning("Launch pipeline inspection regex fallback failed for %s: %s", filename, exc, exc_info=True)

        shaped_payload = _shape_inspection_payload({}, inspection_subtype=inspection_subtype, raw_text=extracted_text)
        inspection_review = _assess_inspection_completeness(shaped_payload, inspection_subtype=inspection_subtype)
        return {"handled": True, "context_key": "inspection_certificate", "context_payload": {**shaped_payload, "inspection_review": inspection_review}, "doc_info_patch": {**base_patch, "inspection_subtype": inspection_subtype, "inspection_family": shaped_payload.get("inspection_family"), "parse_complete": inspection_review.get("parse_complete"), "parse_completeness": inspection_review.get("required_ratio"), "missing_required_fields": inspection_review.get("missing_required_fields", []), "required_fields_found": inspection_review.get("required_found"), "required_fields_total": inspection_review.get("required_total"), "review_reasons": list(base_patch.get("review_reasons") or []) + list(inspection_review.get("review_reasons") or []), "extraction_status": "failed", "extraction_error": "launch_pipeline_inspection_extraction_failed"}, "has_structured_data": False, "validation_doc_type": None, "post_validation_target": None}


def _set_nested_value(root: Dict[str, Any], path: tuple[str, ...], value: Any) -> None:
    target = root
    for key in path[:-1]:
        child = target.get(key)
        if not isinstance(child, dict):
            child = {}
            target[key] = child
        target = child
    target[path[-1]] = value


def _fields_to_lc_context(fields: List[Any]) -> Dict[str, Any]:
    lc_context: Dict[str, Any] = {}
    for field in fields:
        value = str(getattr(field, "value", "") or "").strip()
        if not value:
            continue
        name = getattr(field, "field_name", "")
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
        if confidence is not None:
            details["confidence"] = confidence
        raw_text = getattr(field, "raw_text", None)
        if raw_text:
            details["raw_text"] = raw_text
        if details:
            field_details[getattr(field, "field_name", "field")] = details
    if field_details:
        context["_field_details"] = field_details
    return context


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


def _assess_coo_parse_completeness(extracted_fields: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    required_fields = [
        "certificate_number",
        "country_of_origin",
        "exporter_name",
        "importer_name",
        "goods_description",
    ]
    metrics = _assess_required_field_completeness(extracted_fields, required_fields)
    has_country = _is_populated_field_value((extracted_fields or {}).get("country_of_origin"))
    has_certificate = _is_populated_field_value((extracted_fields or {}).get("certificate_number"))
    min_required_found = 3
    parse_complete = bool(has_country and has_certificate and metrics["required_found"] >= min_required_found)
    metrics.update(
        {
            "min_required_for_verified": min_required_found,
            "has_country_of_origin": has_country,
            "has_certificate_number": has_certificate,
            "parse_complete": parse_complete,
        }
    )
    return metrics


TRANSPORT_DOC_ALIASES = {
    "bill_of_lading",
    "ocean_bill_of_lading",
    "sea_waybill",
    "air_waybill",
    "multimodal_transport_document",
    "combined_transport_document",
    "railway_consignment_note",
    "road_transport_document",
    "forwarders_certificate_of_receipt",
    "house_bill_of_lading",
    "master_bill_of_lading",
    "delivery_order",
    "mates_receipt",
    "shipping_company_certificate",
}


def _canonicalize_launch_doc_type(doc_type: str) -> str:
    normalized = str(doc_type or "").strip().lower().replace("-", "_").replace(" ", "_")
    if normalized in TRANSPORT_DOC_ALIASES:
        return "bill_of_lading"
    return normalized


def _detect_transport_subtype(*, filename: str, extracted_text: str) -> str:
    haystack = f"{filename or ''}\n{extracted_text or ''}".lower()
    checks = [
        ("air_waybill", ["air waybill", " air waybill", "awb", "air transport document", "airport of departure", "airport of destination"]),
        ("sea_waybill", ["sea waybill", "seawaybill", "sea-waybill"]),
        ("ocean_bill_of_lading", ["ocean bill of lading", "ocean b/l"]),
        ("multimodal_transport_document", ["multimodal transport", "combined transport", "at least two different modes of transport"]),
        ("railway_consignment_note", ["railway consignment", "rail consignment", "railway receipt"]),
        ("road_transport_document", ["road transport document", "cmr", "truck consignment", "road consignment"]),
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
    review_reasons = []
    if not parse_complete:
        review_reasons.append(f"invoice_{invoice_subtype}_missing_critical_fields")
    if metrics.get("missing_required_fields"):
        review_reasons.extend([f"missing:{field}" for field in metrics["missing_required_fields"]])
    metrics.update({"parse_complete": parse_complete, "review_reasons": review_reasons})
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


def _shape_invoice_financial_payload(payload: Dict[str, Any], *, invoice_subtype: str, raw_text: str) -> Dict[str, Any]:
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
        _extract_label_value(raw_text, ["invoice no", "invoice number"]),
    )
    shaped["instrument_number"] = _first(
        shaped.get("instrument_number"),
        shaped.get("invoice_number"),
        _extract_label_value(raw_text, ["bill no", "draft no", "note no", "reference no", "debit note no", "credit note no"]),
    )
    if invoice_subtype == "payment_receipt":
        shaped["receipt_number"] = _first(
            shaped.get("receipt_number"),
            _extract_label_value(raw_text, ["receipt no", "receipt number"]),
        )
    else:
        shaped["receipt_number"] = shaped.get("receipt_number")
    shaped["amount"] = _first(
        shaped.get("amount"),
        _extract_amount_value(raw_text, ["amount", "total amount", "receipt amount", "note amount"]),
    )
    shaped["currency"] = _first(shaped.get("currency"), _extract_label_value(raw_text, ["currency"]))
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
    review_reasons = []
    if not parse_complete:
        review_reasons.append(f"lc_{lc_subtype}_missing_critical_fields")
    if metrics.get("missing_required_fields"):
        review_reasons.extend([f"missing:{field}" for field in metrics["missing_required_fields"]])
    metrics.update({"parse_complete": parse_complete, "review_reasons": review_reasons})
    return metrics


def _detect_lc_financial_subtype(*, filename: str, document_type: str, extracted_text: str) -> str:
    haystack = f"{filename or ''}\n{document_type or ''}\n{extracted_text or ''}".lower()
    if any(token in haystack for token in ["bank guarantee"]):
        return "bank_guarantee"
    if any(token in haystack for token in ["standby letter of credit", "standby lc", "sblc"]):
        return "standby_letter_of_credit"
    return str(document_type or "letter_of_credit").strip().lower() or "letter_of_credit"


def _shape_lc_financial_payload(payload: Dict[str, Any], *, lc_subtype: str, raw_text: str, source_type: str, lc_format: str) -> Dict[str, Any]:
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
    amount = shaped.get("amount")
    if isinstance(applicant, dict):
        shaped["applicant"] = applicant.get("name") or applicant.get("value")
    if isinstance(beneficiary, dict):
        shaped["beneficiary"] = beneficiary.get("name") or beneficiary.get("value")
    if isinstance(amount, dict):
        shaped["amount"] = amount.get("value") or amount.get("amount")
        shaped["currency"] = _first(shaped.get("currency"), amount.get("currency"))

    shaped["applicant"] = _first(shaped.get("applicant"), _extract_label_value(raw_text, ["applicant", "buyer", "importer"]))
    shaped["beneficiary"] = _first(shaped.get("beneficiary"), _extract_label_value(raw_text, ["beneficiary", "seller", "exporter"]))
    shaped["amount"] = _first(shaped.get("amount"), _extract_amount_value(raw_text, ["amount", "guarantee amount", "credit amount"]))
    shaped["currency"] = _first(shaped.get("currency"), _extract_label_value(raw_text, ["currency"]))
    shaped["lc_number"] = _first(shaped.get("lc_number"), shaped.get("number"), shaped.get("reference"), _extract_label_value(raw_text, ["lc number", "credit number", "reference number"]))
    shaped["guarantee_reference"] = _first(shaped.get("guarantee_reference"), _extract_label_value(raw_text, ["guarantee no", "guarantee number", "reference number"]))
    return _apply_canonical_normalization(shaped)


def _assess_insurance_completeness(payload: Optional[Dict[str, Any]], *, insurance_subtype: str) -> Dict[str, Any]:
    subtype_required = {
        "insurance_policy": ["policy_number", "insured_amount"],
        "beneficiary_certificate": ["certificate_number"],
        "manufacturers_certificate": ["certificate_number"],
        "certificate_of_conformity": ["certificate_number"],
        "non_manipulation_certificate": ["certificate_number"],
        "halal_certificate": ["certificate_number"],
        "kosher_certificate": ["certificate_number"],
        "organic_certificate": ["certificate_number"],
        "insurance_certificate": ["policy_number", "insured_amount"],
    }
    required_fields = subtype_required.get(insurance_subtype, ["policy_number"])
    metrics = _assess_required_field_completeness(payload, required_fields)
    parse_complete = metrics.get("required_found", 0) >= max(1, min(2, metrics.get("required_total", 0)))
    review_reasons = []
    if not parse_complete:
        review_reasons.append(f"insurance_{insurance_subtype}_missing_critical_fields")
    if metrics.get("missing_required_fields"):
        review_reasons.extend([f"missing:{field}" for field in metrics["missing_required_fields"]])
    metrics.update({"parse_complete": parse_complete, "review_reasons": review_reasons})
    return metrics


def _detect_insurance_subtype(*, filename: str, extracted_text: str) -> str:
    haystack = f"{filename or ''}\n{extracted_text or ''}".lower()
    checks = [
        ("insurance_policy", ["insurance policy", "policy"]),
        ("beneficiary_certificate", ["beneficiary certificate"]),
        ("manufacturers_certificate", ["manufacturer's certificate", "manufacturers certificate"]),
        ("certificate_of_conformity", ["certificate of conformity"]),
        ("non_manipulation_certificate", ["non-manipulation certificate"]),
        ("halal_certificate", ["halal certificate"]),
        ("kosher_certificate", ["kosher certificate"]),
        ("organic_certificate", ["organic certificate"]),
    ]
    for subtype, patterns in checks:
        if any(pattern in haystack for pattern in patterns):
            return subtype
    return "insurance_certificate"


def _shape_insurance_payload(payload: Dict[str, Any], *, insurance_subtype: str, raw_text: str) -> Dict[str, Any]:
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
        _extract_label_value(raw_text, ["policy no", "policy number", "certificate no", "certificate number"]),
    )
    shaped["insured_amount"] = _first(
        shaped.get("insured_amount"),
        _extract_amount_value(raw_text, ["insured amount", "sum insured", "coverage amount"]),
    )
    shaped["issuer_name"] = _first(
        shaped.get("issuer_name"),
        shaped.get("insurer"),
        shaped.get("issuing_authority"),
        _extract_label_value(raw_text, ["insurer", "insurance company", "underwriter", "issued by", "issuer"]),
    )
    return _apply_canonical_normalization(shaped)


def _assess_regulatory_completeness(payload: Optional[Dict[str, Any]], *, regulatory_subtype: str) -> Dict[str, Any]:
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
        "certificate_of_origin": ["certificate_number", "country_of_origin"],
    }
    required_fields = subtype_required.get(regulatory_subtype, ["certificate_number"])
    metrics = _assess_required_field_completeness(payload, required_fields)
    parse_complete = metrics.get("required_found", 0) >= max(1, min(2, metrics.get("required_total", 0)))
    review_reasons = []
    if not parse_complete:
        review_reasons.append(f"regulatory_{regulatory_subtype}_missing_critical_fields")
    if metrics.get("missing_required_fields"):
        review_reasons.extend([f"missing:{field}" for field in metrics["missing_required_fields"]])
    metrics.update({"parse_complete": parse_complete, "review_reasons": review_reasons})
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


def _shape_regulatory_payload(payload: Dict[str, Any], *, regulatory_subtype: str, raw_text: str) -> Dict[str, Any]:
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
        _extract_label_value(raw_text, ["certificate no", "certificate number"]),
    )
    shaped["country_of_origin"] = _first(
        shaped.get("country_of_origin"),
        shaped.get("origin_country"),
        _extract_label_value(raw_text, ["country of origin", "origin"]),
    )
    shaped["issuing_authority"] = _first(
        shaped.get("issuing_authority"),
        shaped.get("certifying_authority"),
        _extract_label_value(raw_text, ["issued by", "issuing authority", "chamber of commerce", "authority"]),
    )
    shaped["license_number"] = _first(
        shaped.get("license_number"),
        _extract_label_value(raw_text, ["license no", "license number"]),
    )
    shaped["declaration_reference"] = _first(
        shaped.get("declaration_reference"),
        _extract_label_value(raw_text, ["declaration no", "declaration number", "customs declaration no"]),
    )
    shaped["permit_number"] = _first(
        shaped.get("permit_number"),
        _extract_label_value(raw_text, ["permit no", "permit number"]),
    )
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
    review_reasons = []
    if not parse_complete:
        review_reasons.append(f"inspection_{inspection_subtype}_missing_critical_fields")
    if metrics.get("missing_required_fields"):
        review_reasons.extend([f"missing:{field}" for field in metrics["missing_required_fields"]])
    metrics.update({
        "parse_complete": parse_complete,
        "review_reasons": review_reasons,
    })
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


def _shape_inspection_payload(payload: Dict[str, Any], *, inspection_subtype: str, raw_text: str) -> Dict[str, Any]:
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
        _extract_label_value(raw_text, ["inspection company", "inspection agency", "inspector", "surveyed by", "inspection by"]),
    )
    shaped["inspection_result"] = _first(
        shaped.get("inspection_result"),
        shaped.get("inspection_results"),
        _extract_label_value(raw_text, ["inspection result", "findings", "observations", "results"]),
    )
    shaped["quality_finding"] = _first(
        shaped.get("quality_finding"),
        shaped.get("inspection_result"),
        shaped.get("inspection_results"),
        _extract_label_value(raw_text, ["quality finding", "quality result"]),
    )
    shaped["analysis_result"] = _first(
        shaped.get("analysis_result"),
        shaped.get("inspection_result"),
        shaped.get("inspection_results"),
        _extract_label_value(raw_text, ["analysis result", "test result", "lab result"]),
    )
    shaped["gross_weight"] = _first(
        shaped.get("gross_weight"),
        _extract_label_value(raw_text, ["gross weight", "gross wt", "gross", "g/w", "g w"]),
    )
    shaped["net_weight"] = _first(
        shaped.get("net_weight"),
        _extract_label_value(raw_text, ["net weight", "net wt", "net", "n/w", "n w"]),
    )
    measurement_candidate = _first(
        shaped.get("measurement_value"),
        shaped.get("dimensions"),
        _extract_label_value(raw_text, ["measurements", "dimensions", "dimension", "size"]),
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
        "house_bill_of_lading": ["transport_reference_number", "shipper", "consignee"],
        "master_bill_of_lading": ["transport_reference_number", "shipper", "consignee"],
        "multimodal_transport_document": ["transport_mode_chain", "port_of_loading", "port_of_discharge"],
        "railway_consignment_note": ["consignment_reference", "consignee"],
        "road_transport_document": ["consignment_reference", "consignee"],
        "forwarders_certificate_of_receipt": ["consignment_reference", "shipper"],
        "delivery_order": ["consignment_reference", "consignee"],
        "mates_receipt": ["carriage_vessel_name"],
        "shipping_company_certificate": ["carriage_vessel_name"],
        "bill_of_lading": ["port_of_loading", "port_of_discharge", "shipper", "consignee"],
    }
    required_fields = subtype_required.get(transport_subtype, ["shipper", "consignee"])
    metrics = _assess_required_field_completeness(payload, required_fields)
    parse_complete = metrics.get("required_found", 0) >= max(1, min(3, metrics.get("required_total", 0)))
    review_reasons = []
    if not parse_complete:
        review_reasons.append(f"transport_{transport_subtype}_missing_critical_fields")
    if metrics.get("missing_required_fields"):
        review_reasons.extend([f"missing:{field}" for field in metrics["missing_required_fields"]])
    metrics.update({
        "parse_complete": parse_complete,
        "review_reasons": review_reasons,
    })
    return metrics


def _shape_transport_payload(payload: Dict[str, Any], *, transport_subtype: str, raw_text: str) -> Dict[str, Any]:
    shaped = dict(payload or {})
    shaped["raw_text"] = raw_text
    shaped["transport_subtype"] = transport_subtype

    mode_map = {
        "air_waybill": ("transport_document", "air"),
        "sea_waybill": ("transport_document", "sea"),
        "ocean_bill_of_lading": ("transport_document", "sea"),
        "multimodal_transport_document": ("transport_document", "multimodal"),
        "railway_consignment_note": ("transport_document", "rail"),
        "road_transport_document": ("transport_document", "road"),
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
            _extract_label_value(raw_text, ["airport of departure", "departure airport"]),
        )
        shaped["airport_of_destination"] = _first(
            shaped.get("airport_of_destination"),
            shaped.get("port_of_discharge"),
            _extract_label_value(raw_text, ["airport of destination", "destination airport"]),
        )
        shaped["airway_bill_number"] = _first(
            shaped.get("airway_bill_number"),
            shaped.get("awb_number"),
            shaped.get("bl_number"),
            _extract_label_value(raw_text, ["awb no", "awb number", "air waybill no", "air waybill number"]),
        )
    elif transport_subtype in {"sea_waybill", "ocean_bill_of_lading", "house_bill_of_lading", "master_bill_of_lading", "mates_receipt", "shipping_company_certificate"}:
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
            _extract_label_value(raw_text, ["mode chain", "modes of transport", "transport modes"]),
            "multimodal",
        )
    elif transport_subtype in {"railway_consignment_note", "road_transport_document", "forwarders_certificate_of_receipt", "delivery_order"}:
        shaped["consignment_reference"] = _first(
            shaped.get("consignment_reference"),
            shaped.get("bl_number"),
            _extract_label_value(raw_text, ["consignment note", "consignment no", "document no", "fcr no", "delivery order no"]),
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


def _apply_canonical_normalization(payload: Dict[str, Any]) -> Dict[str, Any]:
    shaped = dict(payload or {})
    normalization_meta = shaped.get("normalization") if isinstance(shaped.get("normalization"), dict) else {}

    for field in ("currency",):
        if field in shaped:
            original = shaped.get(field)
            normalized = _normalize_currency_value(original)
            shaped[field] = normalized
            if normalized != original:
                normalization_meta[field] = {"raw": original, "canonical": normalized}

    for field in ("country_of_origin", "origin_country", "country", "country_name"):
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

    return shaped


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
        return "mt700"
    snippet = raw_lc_text.strip()
    lowered = snippet[:1200].lower()
    if "<?xml" in lowered or "documentarycreditnotification" in lowered or "tsmt" in lowered or "mx" in lowered:
        return "iso20022"
    return "mt700"


_launch_pipeline_singleton: Optional[LaunchExtractionPipeline] = None


def get_launch_extraction_pipeline() -> LaunchExtractionPipeline:
    global _launch_pipeline_singleton
    if _launch_pipeline_singleton is None:
        _launch_pipeline_singleton = LaunchExtractionPipeline()
    return _launch_pipeline_singleton
