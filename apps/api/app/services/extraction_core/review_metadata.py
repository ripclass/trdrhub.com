from __future__ import annotations

import os
from dataclasses import asdict
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .contract import DocumentExtraction, EvidenceRef, ExtractionBundle, FieldExtraction
from .field_states import infer_field_state
from .gate import evaluate_review_gate
from .profiles import load_profile

EXTRACTION_CORE_V1_ENV = "LCCOPILOT_EXTRACTION_CORE_V1_ENABLED"

_DEFAULT_FIELD_ALIASES: Dict[str, Tuple[str, ...]] = {
    "issue_date": ("issue_date", "date", "invoice_date", "bl_date", "date_of_issue", "doc_date"),
    "issuer": ("issuer", "issuer_name"),
    "gross_weight": ("gross_weight", "gross_wt", "weight_gross", "gross", "total_gross_weight"),
    "net_weight": ("net_weight", "net_wt", "weight_net", "net", "total_net_weight"),
    "voyage": ("voyage", "voyage_number", "bl_voyage_no"),
    "bin_tin": ("bin_tin", "exporter_bin", "exporter_tin", "bin", "tin", "seller_bin", "tax_id"),
}

_DOC_FIELD_ALIASES: Dict[str, Dict[str, Tuple[str, ...]]] = {
    "letter_of_credit": {
        "issuer": ("issuer", "issuing_bank", "issuer_name", "issuing_bank_name"),
        "issue_date": ("issue_date", "date_of_issue", "doc_date"),
    },
    "commercial_invoice": {
        "issuer": ("issuer", "seller_name", "seller", "exporter_name", "shipper"),
        "issue_date": ("issue_date", "invoice_date", "date", "doc_date"),
        "bin_tin": ("bin_tin", "exporter_bin", "exporter_tin", "bin", "tin", "seller_bin", "tax_id"),
    },
    "bill_of_lading": {
        "issuer": ("issuer", "carrier", "shipper"),
        "issue_date": ("issue_date", "bl_date", "date", "date_of_issue", "shipped_on_board_date"),
        "voyage": ("voyage", "voyage_number", "bl_voyage_no"),
        "bin_tin": ("bin_tin", "exporter_bin", "exporter_tin", "bin", "tin", "seller_bin", "tax_id"),
    },
    "packing_list": {
        "issuer": ("issuer", "shipper", "seller_name", "exporter_name"),
        "issue_date": ("issue_date", "date", "packing_list_date", "doc_date"),
    },
}

_PARSE_FAILURE_MARKERS = ("parse", "invalid", "failed", "error", "format", "rejected", "retry")


def extraction_core_v1_enabled() -> bool:
    raw = str(os.getenv(EXTRACTION_CORE_V1_ENV, "1") or "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _field_aliases(field_name: str, document_type: str) -> Tuple[str, ...]:
    aliases: List[str] = []
    aliases.extend((_DOC_FIELD_ALIASES.get(document_type) or {}).get(field_name, ()))
    aliases.extend(_DEFAULT_FIELD_ALIASES.get(field_name, (field_name,)))
    aliases.append(field_name)
    return tuple(dict.fromkeys(alias for alias in aliases if alias))


def _extract_field_value(value: Any) -> Any:
    if isinstance(value, dict):
        for key in ("value", "normalized_value", "normalized", "text", "raw_value", "raw"):
            if key in value:
                return value.get(key)
    return value


def _coerce_confidence(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return None
    if confidence > 1:
        confidence = confidence / 100.0
    if confidence < 0:
        return 0.0
    if confidence > 1:
        return 1.0
    return confidence


def _normalize_text(value: Any) -> str:
    if value in (None, "", [], {}):
        return ""
    return str(value).strip()


def _extract_value_and_details(
    document: Dict[str, Any],
    extracted_fields: Dict[str, Any],
    field_details: Dict[str, Dict[str, Any]],
    field_name: str,
    document_type: str,
) -> Tuple[str, Any, Dict[str, Any], List[Dict[str, Any]]]:
    aliases = _field_aliases(field_name, document_type)
    selected_key = aliases[0] if aliases else field_name
    selected_value: Any = None
    selected_details: Dict[str, Any] = {}
    detail_candidates: List[Dict[str, Any]] = []

    for key in aliases:
        details = field_details.get(key) if isinstance(field_details.get(key), dict) else {}
        if details:
            detail_candidates.append(details)
        raw_value = None
        if isinstance(extracted_fields, dict) and key in extracted_fields:
            raw_value = extracted_fields.get(key)
        elif key in document:
            raw_value = document.get(key)
        value = _extract_field_value(raw_value)

        if selected_value in (None, "", [], {}) and value not in (None, "", [], {}):
            selected_key = key
            selected_value = value
            selected_details = details
        elif not selected_details and details:
            selected_key = key
            selected_details = details

    return selected_key, selected_value, selected_details, detail_candidates


def _infer_parse_error(detail_candidates: Iterable[Dict[str, Any]]) -> bool:
    for details in detail_candidates:
        if not isinstance(details, dict):
            continue
        if details.get("parse_error") is True:
            return True
        markers = [
            details.get("status"),
            details.get("reason"),
            details.get("reason_code"),
            details.get("decision_status"),
        ]
        issues = details.get("issues")
        if isinstance(issues, list):
            markers.extend(issues)
        for marker in markers:
            text = _normalize_text(marker).lower()
            if text and any(flag in text for flag in _PARSE_FAILURE_MARKERS):
                return True
    return False


def _snippet_from_text(raw_text: str, value: Any) -> Optional[str]:
    needle = _normalize_text(value)
    haystack = _normalize_text(raw_text)
    if not needle or not haystack:
        return None
    lower_haystack = haystack.lower()
    lower_needle = needle.lower()
    index = lower_haystack.find(lower_needle)
    if index < 0:
        return None
    start = max(0, index - 40)
    end = min(len(haystack), index + len(needle) + 40)
    return haystack[start:end]


def _build_evidence_refs(details: Dict[str, Any], value: Any, raw_text: str) -> List[EvidenceRef]:
    evidence_refs: List[EvidenceRef] = []
    raw_candidates: List[Any] = []

    for key in ("evidence", "evidence_span", "evidence_spans", "spans"):
        if key in details:
            raw_candidates.append(details.get(key))

    if not raw_candidates:
        inline_text = None
        for key in ("evidence_snippet", "text_span", "raw_text", "snippet", "text"):
            candidate = _normalize_text(details.get(key))
            if candidate:
                inline_text = candidate
                break
        if not inline_text:
            inline_text = _snippet_from_text(raw_text, value)
        if inline_text:
            raw_candidates.append(
                {
                    "page": details.get("page") or details.get("page_number") or 1,
                    "text_span": inline_text,
                    "bbox": details.get("bbox"),
                    "source_layer": details.get("source") or details.get("source_layer"),
                    "confidence": details.get("confidence"),
                }
            )

    for candidate in raw_candidates:
        items = candidate if isinstance(candidate, list) else [candidate]
        for item in items:
            if isinstance(item, str):
                text_span = item.strip()
                page = 1
                bbox = None
                source_layer = None
                confidence = None
            elif isinstance(item, dict):
                text_span = _normalize_text(
                    item.get("text_span")
                    or item.get("text")
                    or item.get("snippet")
                    or item.get("raw")
                    or item.get("value")
                )
                page = int(item.get("page") or item.get("page_number") or 1)
                bbox = item.get("bbox")
                source_layer = item.get("source_layer") or item.get("source")
                confidence = item.get("confidence")
            else:
                continue
            if not text_span:
                continue
            evidence_refs.append(
                EvidenceRef(
                    page=page if page >= 1 else 1,
                    text_span=text_span,
                    bbox=bbox if isinstance(bbox, list) else None,
                    source_layer=_normalize_text(source_layer) or None,
                    confidence=_coerce_confidence(confidence),
                )
            )
    return evidence_refs


def _field_confidence(document: Dict[str, Any], details: Dict[str, Any]) -> float:
    for candidate in (
        details.get("final_confidence"),
        details.get("confidence"),
        details.get("ai_confidence"),
        document.get("extraction_confidence"),
        document.get("ocr_confidence"),
        document.get("ocrConfidence"),
    ):
        confidence = _coerce_confidence(candidate)
        if confidence is not None:
            return confidence
    return 0.0


def _reason_codes(state: str, details: Dict[str, Any]) -> List[str]:
    codes: List[str] = []
    for key in ("reason_code", "reason", "status", "decision_status"):
        text = _normalize_text(details.get(key)).lower()
        if text:
            codes.append(text)
    if state != "found":
        codes.append(state)
    return sorted(dict.fromkeys(codes))


def build_document_extraction(document: Dict[str, Any]) -> DocumentExtraction:
    doc_type = str(
        document.get("document_type")
        or document.get("documentType")
        or "supporting_document"
    )
    extracted_fields = (
        document.get("extracted_fields")
        if isinstance(document.get("extracted_fields"), dict)
        else document.get("extractedFields")
        if isinstance(document.get("extractedFields"), dict)
        else {}
    )
    field_details = (
        document.get("field_details")
        if isinstance(document.get("field_details"), dict)
        else document.get("_field_details")
        if isinstance(document.get("_field_details"), dict)
        else {}
    )
    extraction_artifacts = (
        document.get("extraction_artifacts_v1")
        if isinstance(document.get("extraction_artifacts_v1"), dict)
        else {}
    )
    raw_text = _normalize_text(
        extraction_artifacts.get("raw_text")
        or document.get("raw_text")
        or document.get("raw_text_preview")
    )

    profile = load_profile(doc_type)
    critical_fields = profile.get("critical_fields") or []
    review_gate = profile.get("review_gate") if isinstance(profile.get("review_gate"), dict) else {}
    min_confidence = float(review_gate.get("min_confidence", 0.80) or 0.80)
    require_evidence = bool(review_gate.get("require_evidence", True))

    fields: List[FieldExtraction] = []
    for field_name in critical_fields:
        _, value, details, detail_candidates = _extract_value_and_details(
            document,
            extracted_fields if isinstance(extracted_fields, dict) else {},
            field_details if isinstance(field_details, dict) else {},
            str(field_name),
            doc_type,
        )
        state = infer_field_state(value, parse_error=_infer_parse_error(detail_candidates))
        fields.append(
            FieldExtraction(
                name=str(field_name),
                value_raw=details.get("raw_value", value),
                value_normalized=value,
                state=state,
                confidence=_field_confidence(document, details),
                evidence=_build_evidence_refs(details, value, raw_text),
                reason_codes=_reason_codes(state, details),
            )
        )

    decision = evaluate_review_gate(
        fields,
        critical_fields,
        min_confidence=min_confidence,
        require_evidence=require_evidence,
    )

    return DocumentExtraction(
        doc_id=str(document.get("id") or document.get("document_id") or ""),
        doc_type_predicted=doc_type,
        doc_type_confidence=_coerce_confidence(document.get("doc_type_confidence")) or 0.0,
        fields=fields,
        review_required=decision.review_required,
        review_reasons=decision.reasons,
        profile_version=str(profile.get("version") or "profiles-v1"),
    )


def build_extraction_core_bundle(
    documents: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    if not extraction_core_v1_enabled():
        return None

    document_extractions = [
        build_document_extraction(document)
        for document in (documents or [])
        if isinstance(document, dict)
    ]
    bundle = ExtractionBundle(
        documents=document_extractions,
        meta={
            "feature_flag": EXTRACTION_CORE_V1_ENV,
            "documents_evaluated": len(document_extractions),
            "review_required_count": sum(1 for doc in document_extractions if doc.review_required),
        },
    )
    bundle_dict = asdict(bundle)
    bundle_dict["version"] = "extraction_core_v1"
    bundle_dict["enabled"] = True
    return bundle_dict


def annotate_documents_with_review_metadata(
    documents: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    bundle = build_extraction_core_bundle(documents)
    if not bundle:
        return None

    bundle_documents = bundle.get("documents") if isinstance(bundle.get("documents"), list) else []
    for document, extraction_doc in zip(documents or [], bundle_documents):
        if not isinstance(document, dict) or not isinstance(extraction_doc, dict):
            continue
        critical_field_states = {
            field.get("name"): field.get("state")
            for field in extraction_doc.get("fields", [])
            if isinstance(field, dict) and field.get("name")
        }
        review_required = bool(extraction_doc.get("review_required", False))
        review_reasons = extraction_doc.get("review_reasons") or []

        document["review_required"] = review_required
        document["reviewRequired"] = review_required
        document["review_reasons"] = review_reasons
        document["reviewReasons"] = review_reasons
        document["critical_field_states"] = critical_field_states
        document["criticalFieldStates"] = critical_field_states

    return bundle
