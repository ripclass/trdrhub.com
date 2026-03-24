"""Document review-policy helpers for validation routes."""

from __future__ import annotations

from datetime import datetime
import logging
import os
from typing import Any, Dict, List, Optional

from app.services.validation.day1_configs import load_day1_schema
from app.services.validation.day1_fallback import resolve_fallback_chain
from app.services.validation.day1_normalizers import (
    normalize_bin,
    normalize_date,
    normalize_issuer,
    normalize_tin,
    normalize_voyage,
    normalize_weight,
    validate_gross_net_pair,
)
from app.services.validation.day1_retrieval_guard import apply_anchor_evidence_floor


logger = logging.getLogger(__name__)


def count_populated_canonical_fields(fields: Optional[Dict[str, Any]]) -> int:
    if not isinstance(fields, dict):
        return 0
    count = 0
    for key, value in fields.items():
        if not isinstance(key, str) or key.startswith("_"):
            continue
        if value in (None, "", [], {}):
            continue
        count += 1
    return count


def apply_extraction_guard(doc_info: Dict[str, Any], extracted_text: str) -> None:
    status_now = str(doc_info.get("extraction_status") or "unknown")
    if status_now not in {"success", "partial"}:
        return
    ocr_len = len(extracted_text or "")
    extracted_fields = doc_info.get("extracted_fields") or {}
    populated = count_populated_canonical_fields(extracted_fields)
    if ocr_len >= 500 and populated == 0:
        doc_info["extraction_status"] = "partial"
        doc_info["downgrade_reason"] = "rich_ocr_text_but_no_parsed_fields"


def _extraction_fallback_hotfix_enabled() -> bool:
    raw = str(os.getenv("LCCOPILOT_EXTRACTION_FALLBACK_HOTFIX", "1") or "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def finalize_text_backed_extraction_status(
    doc_info: Dict[str, Any],
    document_type: str,
    extracted_text: str,
) -> None:
    if not _extraction_fallback_hotfix_enabled():
        return

    if not (extracted_text or "").strip():
        return

    extracted_fields = doc_info.get("extracted_fields") or {}
    if isinstance(extracted_fields, dict) and extracted_fields:
        return

    status_now = str(doc_info.get("extraction_status") or "empty").lower()
    if status_now in {"success", "partial"}:
        return

    if document_type == "supporting_document":
        doc_info["extraction_status"] = "text_only"
    else:
        doc_info["extraction_status"] = "parse_failed"
    doc_info.setdefault("downgrade_reason", "text_recovered_but_fields_unresolved")


def stabilize_document_review_semantics(doc_info: Dict[str, Any], extracted_text: str) -> None:
    extracted_fields = doc_info.get("extracted_fields") or {}
    if not isinstance(extracted_fields, dict):
        extracted_fields = {}

    review_reasons = list(doc_info.get("review_reasons") or doc_info.get("reviewReasons") or [])
    reason_codes = set(doc_info.get("reason_codes") or [])
    status_now = str(doc_info.get("extraction_status") or "unknown").lower()
    text_len = len((extracted_text or "").strip())
    populated = count_populated_canonical_fields(extracted_fields)
    parse_complete = doc_info.get("parse_complete")

    strong_native_recovery = text_len >= 180 and populated >= 2
    if strong_native_recovery and status_now in {"text_only", "parse_failed"}:
        doc_info["extraction_status"] = "partial" if populated < 4 or parse_complete is False else "success"
        doc_info.setdefault("downgrade_reason", "native_text_recovered")

    if strong_native_recovery and review_reasons:
        filtered_reasons = [r for r in review_reasons if str(r) != "OCR_AUTH_ERROR"]
        if filtered_reasons != review_reasons:
            review_reasons = filtered_reasons
            doc_info["review_reasons"] = filtered_reasons
            doc_info["reviewReasons"] = filtered_reasons

        if not review_reasons and not reason_codes.intersection({"LOW_CONFIDENCE_CRITICAL", "FORMAT_INVALID"}):
            doc_info["review_required"] = False
            doc_info["reviewRequired"] = False


def context_payload_for_doc_type(context: Dict[str, Any], document_type: str) -> Dict[str, Any]:
    if document_type in ("letter_of_credit", "swift_message", "lc_application"):
        return context.get("lc") or {}
    if document_type in ("commercial_invoice", "proforma_invoice"):
        return context.get("invoice") or {}
    if document_type == "bill_of_lading":
        return context.get("bill_of_lading") or {}
    if document_type == "packing_list":
        return context.get("packing_list") or {}
    if document_type in {
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
    }:
        return context.get("certificate_of_origin") or {}
    if document_type in {
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
    }:
        return context.get("insurance_certificate") or {}
    if document_type in {
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
    }:
        return context.get("inspection_certificate") or {}
    return {}


def _first_non_empty(*values: Any) -> Optional[str]:
    for value in values:
        if value in (None, "", [], {}):
            continue
        if isinstance(value, (dict, list)):
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def extract_day1_raw_candidates(doc_info: Dict[str, Any], context_payload: Dict[str, Any]) -> Dict[str, Optional[str]]:
    extracted_fields = doc_info.get("extracted_fields") if isinstance(doc_info.get("extracted_fields"), dict) else {}

    def _pick(*keys: str) -> Optional[str]:
        for key in keys:
            if key in extracted_fields:
                value = _first_non_empty(extracted_fields.get(key))
                if value:
                    return value
            if key in context_payload:
                value = _first_non_empty(context_payload.get(key))
                if value:
                    return value
        return None

    return {
        "issuer": _pick("issuer", "issuer_name", "seller_name", "seller", "exporter_name", "shipper", "carrier", "beneficiary"),
        "bin": _pick("bin", "exporter_bin", "importer_bin", "seller_bin"),
        "tin": _pick("tin", "exporter_tin", "importer_tin", "tax_id"),
        "voyage": _pick("voyage", "voyage_number", "bl_voyage_no"),
        "gross_weight": _pick("gross_weight", "gross_wt", "weight_gross", "gross", "total_gross_weight"),
        "net_weight": _pick("net_weight", "net_wt", "weight_net", "net", "total_net_weight"),
        "doc_date": _pick("doc_date", "issue_date", "date", "invoice_date", "bl_date", "date_of_issue", "shipped_on_board_date"),
    }


def day1_policy_for_doc(document_type: str) -> Dict[str, Any]:
    """Doc-type aware Day-1 runtime coverage policy."""
    defaults = {"fields": ["issuer", "doc_date"], "threshold": 2}
    policy_map: Dict[str, Dict[str, Any]] = {
        "letter_of_credit": {"fields": ["issuer", "doc_date"], "threshold": 2},
        "swift_message": {"fields": ["issuer", "doc_date"], "threshold": 2},
        "lc_application": {"fields": ["issuer", "doc_date"], "threshold": 2},
        "commercial_invoice": {"fields": ["issuer", "doc_date", "bin", "tin"], "threshold": 2},
        "proforma_invoice": {"fields": ["issuer", "doc_date", "bin", "tin"], "threshold": 2},
        "bill_of_lading": {"fields": ["issuer", "voyage", "gross_weight", "net_weight", "doc_date", "bin", "tin"], "threshold": 2},
        "packing_list": {"fields": ["issuer", "doc_date", "gross_weight", "net_weight"], "threshold": 3},
        "certificate_of_origin": {"fields": ["issuer", "doc_date", "bin", "tin"], "threshold": 2},
        "gsp_form_a": {"fields": ["issuer", "doc_date"], "threshold": 1},
        "eur1_movement_certificate": {"fields": ["issuer", "doc_date"], "threshold": 1},
        "insurance_certificate": {"fields": ["issuer", "doc_date"], "threshold": 1},
        "insurance_policy": {"fields": ["issuer", "doc_date"], "threshold": 1},
        "inspection_certificate": {"fields": ["issuer", "doc_date"], "threshold": 1},
        "pre_shipment_inspection": {"fields": ["issuer", "doc_date"], "threshold": 1},
        "quality_certificate": {"fields": ["issuer", "doc_date"], "threshold": 1},
        "weight_certificate": {"fields": ["issuer", "doc_date", "gross_weight", "net_weight"], "threshold": 1},
        "weight_list": {"fields": ["issuer", "doc_date", "gross_weight", "net_weight"], "threshold": 1},
        "measurement_certificate": {"fields": ["issuer", "doc_date"], "threshold": 1},
        "analysis_certificate": {"fields": ["issuer", "doc_date"], "threshold": 1},
        "lab_test_report": {"fields": ["issuer", "doc_date"], "threshold": 1},
        "sgs_certificate": {"fields": ["issuer", "doc_date"], "threshold": 1},
        "bureau_veritas_certificate": {"fields": ["issuer", "doc_date"], "threshold": 1},
        "intertek_certificate": {"fields": ["issuer", "doc_date"], "threshold": 1},
        "beneficiary_certificate": {"fields": ["issuer", "doc_date"], "threshold": 1},
        "manufacturer_certificate": {"fields": ["issuer", "doc_date"], "threshold": 1},
        "conformity_certificate": {"fields": ["issuer", "doc_date"], "threshold": 1},
        "non_manipulation_certificate": {"fields": ["issuer", "doc_date"], "threshold": 1},
        "phytosanitary_certificate": {"fields": ["issuer", "doc_date"], "threshold": 1},
        "fumigation_certificate": {"fields": ["issuer", "doc_date"], "threshold": 1},
        "health_certificate": {"fields": ["issuer", "doc_date"], "threshold": 1},
        "veterinary_certificate": {"fields": ["issuer", "doc_date"], "threshold": 1},
        "sanitary_certificate": {"fields": ["issuer", "doc_date"], "threshold": 1},
        "halal_certificate": {"fields": ["issuer", "doc_date"], "threshold": 1},
        "kosher_certificate": {"fields": ["issuer", "doc_date"], "threshold": 1},
        "organic_certificate": {"fields": ["issuer", "doc_date"], "threshold": 1},
        "customs_declaration": {"fields": ["issuer", "doc_date"], "threshold": 1},
        "export_license": {"fields": ["issuer", "doc_date"], "threshold": 1},
        "import_license": {"fields": ["issuer", "doc_date"], "threshold": 1},
        "air_waybill": {"fields": ["issuer", "doc_date", "voyage"], "threshold": 1},
        "sea_waybill": {"fields": ["issuer", "doc_date", "voyage"], "threshold": 1},
        "road_transport_document": {"fields": ["issuer", "doc_date"], "threshold": 1},
        "railway_consignment_note": {"fields": ["issuer", "doc_date"], "threshold": 1},
        "forwarder_certificate_of_receipt": {"fields": ["issuer", "doc_date"], "threshold": 1},
        "shipping_company_certificate": {"fields": ["issuer", "doc_date"], "threshold": 1},
        "warehouse_receipt": {"fields": ["issuer", "doc_date"], "threshold": 1},
        "cargo_manifest": {"fields": ["issuer", "doc_date"], "threshold": 1},
    }
    policy = policy_map.get(str(document_type or "").strip().lower(), defaults)
    fields = [f for f in (policy.get("fields") or []) if f in {"issuer", "bin", "tin", "voyage", "gross_weight", "net_weight", "doc_date"}]
    if not fields:
        fields = list(defaults["fields"])
    threshold = int(policy.get("threshold") or len(fields))
    threshold = max(1, min(threshold, len(fields)))
    return {"fields": fields, "threshold": threshold}


def enforce_day1_runtime_policy(doc_info: Dict[str, Any], context_payload: Dict[str, Any], document_type: str, extracted_text: str) -> None:
    doc_info["_day1_runtime_hook"] = {
        "invoked": True,
        "document_type": document_type,
    }
    if document_type not in {
        "letter_of_credit", "swift_message", "lc_application", "commercial_invoice", "proforma_invoice",
        "bill_of_lading", "packing_list", "certificate_of_origin", "insurance_certificate", "inspection_certificate",
    }:
        doc_info["_day1_runtime_hook"]["skipped"] = True
        doc_info["_day1_runtime_hook"]["reason"] = "unsupported_document_type"
        return

    raw = extract_day1_raw_candidates(doc_info, context_payload)
    guarded_raw, retrieval_errors, anchor_scores = apply_anchor_evidence_floor(raw, extracted_text, min_score=0.15)

    bin_n = normalize_bin(guarded_raw.get("bin"))
    tin_n = normalize_tin(guarded_raw.get("tin"))
    voy_n = normalize_voyage(guarded_raw.get("voyage"))
    gross_n = normalize_weight(guarded_raw.get("gross_weight"))
    net_n = normalize_weight(guarded_raw.get("net_weight"))
    date_n = normalize_date(guarded_raw.get("doc_date"))
    issuer_n = normalize_issuer(guarded_raw.get("issuer"))

    field_ok = {
        "issuer": issuer_n.valid,
        "bin": bin_n.valid,
        "tin": tin_n.valid,
        "voyage": voy_n.valid,
        "gross_weight": gross_n.valid,
        "net_weight": net_n.valid,
        "doc_date": date_n.valid,
    }
    day1_policy = day1_policy_for_doc(document_type)
    active_fields = day1_policy["fields"]
    threshold = int(day1_policy["threshold"])
    coverage = sum(1 for field_name in active_fields if field_ok.get(field_name, False))

    extraction_method = str(doc_info.get("extraction_method") or "").lower()
    native_fields = guarded_raw if extraction_method in {"native", "pdf_native"} else {}
    ocr_fields = guarded_raw if extraction_method in {"regex_fallback", "fallback", "ocr", ""} else {}
    llm_fields = guarded_raw if "ai" in extraction_method or "llm" in extraction_method else {}
    fallback_decision = resolve_fallback_chain(native_fields=native_fields, ocr_fields=ocr_fields, llm_fields=llm_fields, threshold=5)

    day1_errors: List[str] = list(retrieval_errors)
    for result in (issuer_n, bin_n, tin_n, voy_n, date_n):
        if result.error_code:
            day1_errors.append(result.error_code)
    for result in (gross_n, net_n):
        if result.error_code:
            day1_errors.append(result.error_code)
    pair_error = validate_gross_net_pair(gross_n, net_n)
    if pair_error:
        day1_errors.append(pair_error)

    day1_payload = {
        "schema_version": "v1.0.0-day1",
        "meta": {
            "schema_version": "v1.0.0-day1",
            "parser_stage": fallback_decision.selected_stage,
            "source_type": "pdf_native" if fallback_decision.selected_stage == "native" else "pdf_scanned",
            "doc_id": str(doc_info.get("id") or ""),
            "parsed_at": datetime.utcnow().isoformat() + "Z",
        },
        "fields": {
            "issuer": {"value": guarded_raw.get("issuer"), "normalized": issuer_n.normalized},
            "bin": {"value": guarded_raw.get("bin"), "normalized": bin_n.normalized},
            "tin": {"value": guarded_raw.get("tin"), "normalized": tin_n.normalized},
            "voyage": {"value": guarded_raw.get("voyage"), "normalized": voy_n.normalized},
            "gross_weight": {"value": guarded_raw.get("gross_weight"), "normalized_kg": gross_n.normalized_kg, "unit": gross_n.unit},
            "net_weight": {"value": guarded_raw.get("net_weight"), "normalized_kg": net_n.normalized_kg, "unit": net_n.unit},
            "doc_date": {"value": guarded_raw.get("doc_date"), "iso_date": date_n.normalized},
        },
        "confidence": {
            "overall": round(float(coverage) / float(max(1, len(active_fields))), 3),
            "by_field": {k: (1.0 if v else 0.0) for k, v in field_ok.items()},
        },
        "raw": {"text": extracted_text[:1000], "tokens": []},
        "errors": [{"code": code, "message": code} for code in sorted(set(day1_errors))],
    }

    schema = load_day1_schema()
    required_top = set(schema.get("required") or [])
    schema_ok = required_top.issubset(set(day1_payload.keys()))

    doc_info["day1_runtime"] = {
        "coverage": coverage,
        "threshold": threshold,
        "active_fields": active_fields,
        "schema_version": "v1.0.0-day1",
        "fallback_stage": fallback_decision.selected_stage,
        "schema_ok": schema_ok,
        "errors": sorted(set(day1_errors)),
        "anchor_scores": anchor_scores,
    }
    doc_info["_day1_runtime_hook"]["attached"] = True
    doc_info["_day1_runtime_hook"]["coverage"] = coverage
    doc_info["_day1_runtime_hook"]["threshold"] = threshold

    if not schema_ok:
        doc_info["extraction_status"] = "failed"
        doc_info["downgrade_reason"] = "day1_schema_invalid"
    elif coverage < threshold and len(extracted_text or "") >= 100:
        doc_info["extraction_status"] = "partial"
        doc_info["downgrade_reason"] = "day1_coverage_below_threshold"

    logger.info(
        "validate.day1.runtime doc=%s type=%s stage=%s coverage=%s/%s schema_ok=%s errors=%s",
        doc_info.get("filename"),
        document_type,
        fallback_decision.selected_stage,
        coverage,
        len(active_fields),
        schema_ok,
        sorted(set(day1_errors)),
    )


def is_populated_field_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) > 0
    return True


def assess_required_field_completeness(
    extracted_fields: Optional[Dict[str, Any]],
    required_fields: List[str],
) -> Dict[str, Any]:
    fields = extracted_fields or {}
    found_required = [field for field in required_fields if is_populated_field_value(fields.get(field))]
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


def assess_coo_parse_completeness(extracted_fields: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute parse completeness signal for COO extraction quality gating."""
    required_fields = [
        "country_of_origin",
        "exporter_name",
        "importer_name",
        "goods_description",
        "certifying_authority",
    ]
    metrics = assess_required_field_completeness(extracted_fields, required_fields)
    has_country = is_populated_field_value((extracted_fields or {}).get("country_of_origin"))
    min_required_found = 3
    parse_complete = bool(has_country and metrics["required_found"] >= min_required_found)

    metrics.update(
        {
            "min_required_for_verified": min_required_found,
            "has_country_of_origin": has_country,
            "has_certificate_number": is_populated_field_value((extracted_fields or {}).get("certificate_number")),
            "parse_complete": parse_complete,
        }
    )
    return metrics


__all__ = [
    "count_populated_canonical_fields",
    "apply_extraction_guard",
    "finalize_text_backed_extraction_status",
    "stabilize_document_review_semantics",
    "context_payload_for_doc_type",
    "extract_day1_raw_candidates",
    "day1_policy_for_doc",
    "enforce_day1_runtime_policy",
    "is_populated_field_value",
    "assess_required_field_completeness",
    "assess_coo_parse_completeness",
]
