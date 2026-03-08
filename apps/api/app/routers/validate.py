from decimal import Decimal, InvalidOperation
from uuid import uuid4
from datetime import datetime, timedelta
import asyncio
import json
import copy
import os
import time

import logging
from io import BytesIO
from contextlib import contextmanager

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database import get_db
from app.models import UsageAction, User, ValidationSession, SessionStatus, UserRole, Document
from app.models.company import Company, PlanType, CompanyStatus
from app.services.entitlements import EntitlementError, EntitlementService
from app.services.validator import (
    validate_document,
    validate_document_async,
    apply_bank_policy,
    filter_informational_issues,
)
from app.services.crossdoc import (
    build_issue_cards,
    DEFAULT_LABELS,
)
from app.services.sanctions_lcopilot import (
    run_sanctions_screening_for_validation,
    extract_parties_from_lc,
)
from app.services.ai_issue_rewriter import rewrite_issue
from app.services import ValidationSessionService
from app.services.audit_service import AuditService
from app.middleware.audit_middleware import create_audit_context
from app.models.audit_log import AuditAction, AuditResult
from app.utils.file_validation import validate_upload_file
from app.config import settings
from app.core.lc_types import LCType, VALID_LC_TYPES, normalize_lc_type
from app.services.lc_classifier import detect_lc_type
from fastapi import Header
from typing import Optional, List, Dict, Any, Tuple
import re

from app.services.validation.alias_normalization import canonical_field_key, extract_direct_token_recovery
from app.services.extraction_core.review_metadata import (
    annotate_documents_with_review_metadata as _annotate_documents_with_review_metadata,
    build_extraction_core_bundle as _build_extraction_core_bundle,
)

# Import refactored validation utilities (from split modules)
from app.routers.validation import (
    # Utilities
    severity_rank as _severity_rank,
    severity_to_status as _severity_to_status,
    normalize_issue_severity as _normalize_issue_severity,
    priority_to_severity as _priority_to_severity,
    normalize_doc_match_key as _normalize_doc_match_key,
    strip_extension as _strip_extension,
    coerce_issue_value as _coerce_issue_value,
    format_duration as _format_duration,
    filter_user_facing_fields as _filter_user_facing_fields,
    # Document builder
    build_document_summaries as _build_document_summaries,
    build_document_lookup as _build_document_lookup,
    match_issue_documents as _match_issue_documents,
    build_documents_section as _build_documents_section,
)

from app.routers.validation.issue_attribution import (
    resolve_issue_stats as _resolve_issue_stats,
    collect_document_issue_stats as _collect_document_issue_stats,
    extract_document_names as _extract_document_names,
    extract_document_types as _extract_document_types,
    extract_document_ids as _extract_document_ids,
    bump_issue_entry as _bump_issue_entry,
)

from app.routers.validation.response_shaping import (
    compose_processing_summary as _compose_processing_summary,
    count_issue_severity as _count_issue_severity,
    summarize_document_statuses as _summarize_document_statuses,
    build_processing_summary as _build_processing_summary,
    build_processing_summary_v2 as _build_processing_summary_v2,
    build_document_extraction_v1 as _build_document_extraction_v1,
    build_issue_provenance_v1 as _build_issue_provenance_v1,
    build_bank_submission_verdict as _build_bank_submission_verdict,
    build_processing_timeline as _build_processing_timeline,
)

from app.routers.validation import issue_attribution as _issue_attribution
from app.routers.validation import response_shaping as _response_shaping
from app.routers.validation import response_builder as _response_builder

from app.routers.validation.doc_types import (
    label_to_doc_type as _label_to_doc_type,
    normalize_doc_type_key as _normalize_doc_type_key,
    humanize_doc_type as _humanize_doc_type,
    infer_document_type_from_name as _infer_document_type_from_name,
    fallback_doc_type as _fallback_doc_type,
    canonical_document_tag as _canonical_document_tag,
    resolve_document_type as _resolve_document_type,
    infer_document_type as _infer_document_type,
    doc_type_to_display_name as _doc_type_to_display_name,
)

from app.routers.validation.request_parsing import (
    extract_request_user_type as _extract_request_user_type,
    should_force_json_rules as _should_force_json_rules,
    resolve_shipment_context as _resolve_shipment_context,
    extract_lc_type_override as _extract_lc_type_override_helper,
)

from pydantic import BaseModel, Field, ValidationError, model_validator
from app.utils.logger import TRACE_LOG_LEVEL
from app.services.customs.customs_pack import build_customs_manifest_from_option_e
from app.services.customs.customs_pack_full import CustomsPackBuilderFull
from app.utils.usage_tracker import record_usage_manual
from app.services.extraction.lc_extractor import (
    extract_lc_structured,
    extract_lc_structured_with_ai_fallback,
)
from app.services.extraction.ai_first_extractor import (
    extract_lc_ai_first,
    extract_invoice_ai_first,
    extract_bl_ai_first,
    extract_packing_list_ai_first,
    extract_coo_ai_first,
    extract_insurance_ai_first,
    extract_inspection_ai_first,
)
from app.services.extraction.structured_lc_builder import build_unified_structured_result
from app.services.risk.customs_risk import compute_customs_risk_from_option_e

# V2 Validation Pipeline imports
from app.services.validation.pipeline import (
    ValidationPipeline,
    ValidationInput,
    ValidationOutput,
)
from app.services.validation.validation_gate import ValidationGate, GateStatus
from app.services.validation.compliance_scorer import ComplianceScorer
from app.services.extraction.lc_baseline import LCBaseline, FieldResult, FieldPriority, ExtractionStatus

# Hybrid validation pipeline imports
from app.services.validation.llm_requirement_parser import (
    parse_lc_requirements_sync_v2,
    get_cached_requirements,
    infer_document_type,
    RequirementGraph,
)
from app.services.validation.party_matcher import parties_match, PartyMatchResult
from app.services.validation.amendment_generator import (
    generate_amendments_for_issues,
    calculate_total_amendment_cost,
    AmendmentDraft,
)
from app.services.validation.bank_profiles import (
    get_bank_profile,
    detect_bank_from_lc,
    BankProfile,
)
from app.services.validation.confidence_weighting import (
    batch_adjust_issues,
    calculate_overall_extraction_confidence,
)
from app.services.validation.response_contract_validator import (
    validate_and_annotate_response,
)
from app.services.validation.day1_normalizers import (
    normalize_bin,
    normalize_tin,
    normalize_voyage,
    normalize_weight,
    validate_gross_net_pair,
    normalize_date,
    normalize_issuer,
)
from app.services.validation.day1_fallback import resolve_fallback_chain
from app.services.validation.day1_configs import load_day1_schema
from app.services.validation.day1_contract import enforce_day1_response_contract
from app.services.validation.day1_retrieval_guard import apply_anchor_evidence_floor
from app.services.rules_service import get_ucp_description_sync, get_isbp_description_sync
from app.services.extraction.two_stage_extractor import (
    TwoStageExtractor,
    ExtractedField,
    ExtractionStatus as TwoStageStatus,
)

# Global two-stage extractor instance
_two_stage_extractor: Optional[TwoStageExtractor] = None


def _get_two_stage_extractor() -> TwoStageExtractor:
    """Get or create the two-stage extractor singleton."""
    global _two_stage_extractor
    if _two_stage_extractor is None:
        _two_stage_extractor = TwoStageExtractor()
    return _two_stage_extractor


def _sync_structured_result_collections(structured_result: Dict[str, Any]) -> None:
    """Keep top-level document/timeline aliases aligned for downstream consumers."""
    if not isinstance(structured_result, dict):
        return

    lc_structured = structured_result.get("lc_structured") or {}
    documents = structured_result.get("documents") or structured_result.get("documents_structured")
    if not documents and isinstance(lc_structured, dict):
        documents = lc_structured.get("documents_structured")

    if isinstance(documents, list):
        structured_result.setdefault("documents", documents)
        structured_result.setdefault("documents_structured", documents)

    if "timeline" not in structured_result and isinstance(lc_structured, dict):
        timeline = lc_structured.get("timeline")
        if isinstance(timeline, list):
            structured_result["timeline"] = timeline


def _build_issue_dedup_key(issue: Dict[str, Any]) -> str:
    """Build a deterministic dedup key that preserves per-document discrepancies."""

    def _normalize_list(value: Any) -> List[str]:
        if isinstance(value, list):
            items = value
        elif value in (None, ""):
            items = []
        else:
            items = [value]
        return sorted(str(item) for item in items if item not in (None, ""))

    dedup_payload = {
        "rule": issue.get("rule") or "",
        "title": issue.get("title") or "",
        "ruleset_domain": issue.get("ruleset_domain") or "",
        "field": issue.get("field") or issue.get("field_name") or "",
        "document_ids": _normalize_list(
            issue.get("document_ids") or issue.get("documentId")
        ),
        "document_names": _normalize_list(
            issue.get("document_names")
            or issue.get("documents")
            or issue.get("documentName")
            or issue.get("document_name")
        ),
        "document_types": _normalize_list(
            issue.get("document_types")
            or issue.get("documentType")
            or issue.get("document_type")
        ),
        "expected": str(issue.get("expected") or ""),
        "found": str(issue.get("found") or issue.get("actual") or ""),
    }
    return json.dumps(dedup_payload, sort_keys=True)


def _extract_lc_type_override(payload: Dict[str, Any]) -> Optional[str]:
    """Extract LC type overrides from request payload.

    Mirrors app.routers.validation.request_parsing.extract_lc_type_override
    but kept here so tests can compile it directly.
    """
    options = payload.get("options") or {}
    candidates = [
        payload.get("lc_type_override"),
        payload.get("lcTypeOverride"),
        options.get("lc_type_override"),
        options.get("lc_type"),
        payload.get("lcType"),
        payload.get("lc_type_selection"),
        payload.get("requested_lc_type"),
    ]
    for candidate in candidates:
        normalized = normalize_lc_type(candidate)
        if normalized in VALID_LC_TYPES:
            if normalized == LCType.UNKNOWN.value:
                return LCType.UNKNOWN.value
            return normalized
        if candidate and str(candidate).strip().lower() == "auto":
            return None
    return None

# _filter_user_facing_fields moved to app.routers.validation.utilities


def _count_populated_canonical_fields(fields: Optional[Dict[str, Any]]) -> int:
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


def _resolve_doc_llm_trace(fields: Optional[Dict[str, Any]], extraction_method: Optional[str], has_two_stage: bool = False) -> Dict[str, Any]:
    fields = fields or {}
    provider = fields.get("_llm_provider") or fields.get("_ai_provider")
    model = fields.get("_llm_model")
    router_layer = fields.get("_llm_router_layer")
    extractor_path = "ai_first" if extraction_method == "ai_first" else "fallback"
    if has_two_stage and extraction_method == "ai_first":
        extractor_path = "hybrid"
    return {
        "provider": provider,
        "model": model,
        "router_layer": router_layer,
        "extractor_path": extractor_path,
    }


def _build_document_extraction_payload(
    *,
    doc_type: str,
    file_name: str,
    job_id: Optional[str],
    ocr_text_len: int,
    extractor_path: str,
    llm_provider: Optional[str],
    llm_model: Optional[str],
    router_layer: Optional[str],
    ai_response_present: bool,
    ai_parse_success: bool,
    canonical_before_two_stage: int,
    canonical_after_two_stage: int,
    extraction_status: str,
    downgrade_reason: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "event": "validation_document_extraction",
        "doc_type": doc_type,
        "file_name": file_name,
        "job_id": job_id,
        "ocr_text_len": ocr_text_len,
        "extractor_path": extractor_path,
        "llm_provider": llm_provider,
        "llm_model": llm_model,
        "router_layer": router_layer,
        "ai_response_present": ai_response_present,
        "ai_parse_success": ai_parse_success,
        "canonical_field_count_before_two_stage": canonical_before_two_stage,
        "canonical_field_count_after_two_stage": canonical_after_two_stage,
        "extraction_status": extraction_status,
        "downgrade_reason": downgrade_reason,
    }


def _log_document_extraction_telemetry(
    *,
    doc_type: str,
    file_name: str,
    job_id: Optional[str],
    ocr_text_len: int,
    extractor_path: str,
    llm_provider: Optional[str],
    llm_model: Optional[str],
    router_layer: Optional[str],
    ai_response_present: bool,
    ai_parse_success: bool,
    canonical_before_two_stage: int,
    canonical_after_two_stage: int,
    extraction_status: str,
    downgrade_reason: Optional[str] = None,
) -> None:
    payload = _build_document_extraction_payload(
        doc_type=doc_type,
        file_name=file_name,
        job_id=job_id,
        ocr_text_len=ocr_text_len,
        extractor_path=extractor_path,
        llm_provider=llm_provider,
        llm_model=llm_model,
        router_layer=router_layer,
        ai_response_present=ai_response_present,
        ai_parse_success=ai_parse_success,
        canonical_before_two_stage=canonical_before_two_stage,
        canonical_after_two_stage=canonical_after_two_stage,
        extraction_status=extraction_status,
        downgrade_reason=downgrade_reason,
    )
    logger.info("validate.extraction.telemetry %s", json.dumps(payload, default=str))


def _apply_extraction_guard(doc_info: Dict[str, Any], extracted_text: str) -> None:
    status_now = str(doc_info.get("extraction_status") or "unknown")
    if status_now not in {"success", "partial"}:
        return
    ocr_len = len(extracted_text or "")
    extracted_fields = doc_info.get("extracted_fields") or {}
    populated = _count_populated_canonical_fields(extracted_fields)
    if ocr_len >= 500 and populated == 0:
        doc_info["extraction_status"] = "partial"
        doc_info["downgrade_reason"] = "rich_ocr_text_but_no_parsed_fields"


def _finalize_text_backed_extraction_status(
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


def _context_payload_for_doc_type(context: Dict[str, Any], document_type: str) -> Dict[str, Any]:
    if document_type in ("letter_of_credit", "swift_message", "lc_application"):
        return context.get("lc") or {}
    if document_type in ("commercial_invoice", "proforma_invoice"):
        return context.get("invoice") or {}
    if document_type == "bill_of_lading":
        return context.get("bill_of_lading") or {}
    if document_type == "packing_list":
        return context.get("packing_list") or {}
    if document_type == "certificate_of_origin":
        return context.get("certificate_of_origin") or {}
    if document_type == "insurance_certificate":
        return context.get("insurance_certificate") or {}
    if document_type == "inspection_certificate":
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


def _extract_day1_raw_candidates(doc_info: Dict[str, Any], context_payload: Dict[str, Any]) -> Dict[str, Optional[str]]:
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


def _day1_policy_for_doc(document_type: str) -> Dict[str, Any]:
    """Doc-type aware Day-1 runtime coverage policy."""
    defaults = {"fields": ["issuer", "doc_date"], "threshold": 2}
    policy_map: Dict[str, Dict[str, Any]] = {
        "letter_of_credit": {"fields": ["issuer", "doc_date"], "threshold": 2},
        "swift_message": {"fields": ["issuer", "doc_date"], "threshold": 2},
        "lc_application": {"fields": ["issuer", "doc_date"], "threshold": 2},
        "commercial_invoice": {"fields": ["issuer", "doc_date", "bin", "tin", "gross_weight", "net_weight"], "threshold": 2},
        "proforma_invoice": {"fields": ["issuer", "doc_date", "bin", "tin", "gross_weight", "net_weight"], "threshold": 2},
        "bill_of_lading": {"fields": ["issuer", "voyage", "gross_weight", "net_weight", "doc_date", "bin", "tin"], "threshold": 2},
        "packing_list": {"fields": ["issuer", "doc_date", "gross_weight", "net_weight"], "threshold": 3},
        "certificate_of_origin": {"fields": ["issuer", "doc_date", "bin", "tin"], "threshold": 2},
        "insurance_certificate": {"fields": ["issuer", "doc_date"], "threshold": 1},
        "inspection_certificate": {"fields": ["issuer", "doc_date"], "threshold": 1},
    }
    policy = policy_map.get(str(document_type or "").strip().lower(), defaults)
    fields = [f for f in (policy.get("fields") or []) if f in {"issuer", "bin", "tin", "voyage", "gross_weight", "net_weight", "doc_date"}]
    if not fields:
        fields = list(defaults["fields"])
    threshold = int(policy.get("threshold") or len(fields))
    threshold = max(1, min(threshold, len(fields)))
    return {"fields": fields, "threshold": threshold}


def _enforce_day1_runtime_policy(doc_info: Dict[str, Any], context_payload: Dict[str, Any], document_type: str, extracted_text: str) -> None:
    # only enforce for target doc families
    if document_type not in {
        "letter_of_credit", "swift_message", "lc_application", "commercial_invoice", "proforma_invoice",
        "bill_of_lading", "packing_list", "certificate_of_origin", "insurance_certificate", "inspection_certificate",
    }:
        return

    raw = _extract_day1_raw_candidates(doc_info, context_payload)
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
    day1_policy = _day1_policy_for_doc(document_type)
    active_fields = day1_policy["fields"]
    threshold = int(day1_policy["threshold"])
    coverage = sum(1 for field_name in active_fields if field_ok.get(field_name, False))

    # approximate stage classification for Day-1 fallback telemetry
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


def _apply_direct_token_recovery(
    doc_payload: Dict[str, Any],
    extraction_artifacts_v1: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Recover deterministic token fields directly from merged text/spans and attach evidence metadata."""
    if not isinstance(doc_payload, dict):
        return doc_payload

    raw_text = str(doc_payload.get("raw_text") or "")
    extraction_artifacts = extraction_artifacts_v1 if isinstance(extraction_artifacts_v1, dict) else (
        doc_payload.get("extraction_artifacts_v1") if isinstance(doc_payload.get("extraction_artifacts_v1"), dict) else {}
    )
    recovered = extract_direct_token_recovery(raw_text=raw_text, extraction_artifacts=extraction_artifacts)

    extracted_fields = doc_payload.get("extracted_fields") if isinstance(doc_payload.get("extracted_fields"), dict) else {}
    field_details = doc_payload.get("_field_details") if isinstance(doc_payload.get("_field_details"), dict) else {}

    def _normalized_key(value: Any) -> str:
        return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())

    def _value_tokens(value: Any) -> set[str]:
        return {
            token
            for token in re.findall(r"[a-z0-9]{3,}", str(value or "").lower())
            if token
        }

    def _recovery_value_compatible(field_name: str, existing_value: Any, recovered_value: Any) -> bool:
        if existing_value in (None, "", [], {}) or recovered_value in (None, "", [], {}):
            return True

        existing_text = str(existing_value).strip()
        recovered_text = str(recovered_value).strip()
        if not existing_text or not recovered_text:
            return False

        if field_name == "issue_date":
            existing_digits = re.sub(r"\D", "", existing_text)
            recovered_digits = re.sub(r"\D", "", recovered_text)
            if not existing_digits or not recovered_digits:
                return False
            return (
                existing_digits == recovered_digits
                or existing_digits.endswith(recovered_digits)
                or recovered_digits.endswith(existing_digits)
                or existing_digits in recovered_digits
                or recovered_digits in existing_digits
            )

        if field_name in {"gross_weight", "net_weight"}:
            existing_digits = re.sub(r"\D", "", existing_text)
            recovered_digits = re.sub(r"\D", "", recovered_text)
            return bool(existing_digits and existing_digits == recovered_digits)

        if field_name == "issuer":
            existing_tokens = _value_tokens(existing_text)
            recovered_tokens = _value_tokens(recovered_text)
            if not existing_tokens or not recovered_tokens:
                return _normalized_key(existing_text) == _normalized_key(recovered_text)
            shared = len(existing_tokens.intersection(recovered_tokens))
            minimum = min(2, len(recovered_tokens))
            return shared >= max(1, minimum)

        return _normalized_key(existing_text) == _normalized_key(recovered_text)

    for field_name in (
        "buyer_po_number",
        "exporter_bin",
        "exporter_tin",
        "invoice_number",
        "bl_number",
        "issue_date",
        "issuer",
        "voyage_number",
        "gross_weight",
        "net_weight",
    ):
        item = recovered.get(field_name) or {}
        reason = str(item.get("reason") or "missing_in_source")
        value = item.get("value")
        snippet = item.get("evidence_snippet")
        confidence = item.get("confidence")
        source = item.get("source")

        existing_value = extracted_fields.get(field_name)
        if existing_value in (None, "", [], {}) and field_name in doc_payload:
            existing_value = doc_payload.get(field_name)
        compatible = _recovery_value_compatible(field_name, existing_value, value)

        if value not in (None, "") and field_name not in doc_payload:
            doc_payload[field_name] = value
        if value not in (None, "") and field_name not in extracted_fields:
            extracted_fields[field_name] = value

        existing_detail = field_details.get(field_name) if isinstance(field_details.get(field_name), dict) else {}
        merged_detail = dict(existing_detail or {})
        if reason != "missing_in_source" or not merged_detail:
            merged_detail["reason"] = reason
        if source:
            merged_detail["source"] = source
        if compatible and snippet:
            merged_detail["evidence_snippet"] = snippet
            merged_detail["evidence"] = {
                "text_span": snippet,
                "page": 1,
                "source": source,
                "confidence": confidence,
            }
        if compatible and confidence is not None:
            existing_confidence = merged_detail.get("confidence")
            try:
                existing_confidence_value = float(existing_confidence) if existing_confidence is not None else None
            except (TypeError, ValueError):
                existing_confidence_value = None
            if (
                existing_confidence_value is None
                or float(confidence) >= existing_confidence_value
                or not merged_detail.get("evidence_snippet")
            ):
                merged_detail["confidence"] = confidence

        field_details[field_name] = merged_detail

    if extracted_fields:
        doc_payload["extracted_fields"] = extracted_fields
    if field_details:
        doc_payload["_field_details"] = field_details
    if extraction_artifacts:
        doc_payload["extraction_artifacts_v1"] = extraction_artifacts

    return doc_payload


def _apply_two_stage_validation(
    extracted_fields: Dict[str, Any],
    document_type: str,
    filename: str = "",
    job_id: Optional[str] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Apply two-stage validation to extracted fields.
    
    Stage 1: AI extraction (already done - passed as extracted_fields)
    Stage 2: Deterministic validation using reference data
    
    Args:
        extracted_fields: Dictionary of field_name -> value or {value, confidence}
        document_type: Type of document (lc, invoice, bl, etc.)
        filename: Original filename for logging
        
    Returns:
        Tuple of:
        - validated_fields: Normalized/validated version of extracted_fields
        - validation_summary: Stats about trusted/review/untrusted fields
    """
    if not extracted_fields:
        return {}, {"total": 0, "trusted": 0, "review": 0, "untrusted": 0}
    
    try:
        extractor = _get_two_stage_extractor()

        # Prefer canonical AI-first contract payload when present.
        source_fields = extracted_fields
        contract_fields = extracted_fields.get("extracted_fields")
        if isinstance(contract_fields, dict):
            source_fields = contract_fields

        canonical_before = _count_populated_canonical_fields(source_fields)
        logger.info(
            "validate.two_stage.entry %s",
            json.dumps(
                {
                    "doc_type": document_type,
                    "file_name": filename,
                    "job_id": job_id,
                    "canonical_field_count_before": canonical_before,
                },
                default=str,
            ),
        )

        # Convert to format expected by two-stage extractor.
        canonical_fields = dict(source_fields) if isinstance(source_fields, dict) else {}
        ai_extraction: Dict[str, Any] = {}
        for field_name, value in source_fields.items():
            if not isinstance(field_name, str):
                continue
            if field_name.startswith("_"):
                continue
            if field_name == "raw_text":
                continue
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            if isinstance(value, (list, tuple, set, dict)) and len(value) == 0:
                continue

            canonical_name = canonical_field_key(field_name)
            candidate_names = [field_name]
            if canonical_name != field_name:
                candidate_names.append(canonical_name)

            if isinstance(value, dict):
                # Accept only structured field payloads, skip nested contract containers.
                if "value" in value or "text" in value or "confidence" in value:
                    for candidate_name in candidate_names:
                        ai_extraction[candidate_name] = value
                    if canonical_name in {"exporter_bin", "exporter_tin"} and canonical_name not in canonical_fields:
                        canonical_fields[canonical_name] = value.get("value") or value.get("text")
                else:
                    continue
            else:
                # Wrap raw scalar/list values with a default confidence.
                wrapped = {"value": value, "confidence": 0.7}
                for candidate_name in candidate_names:
                    ai_extraction[candidate_name] = wrapped
                if canonical_name in {"exporter_bin", "exporter_tin"} and canonical_name not in canonical_fields:
                    canonical_fields[canonical_name] = value
        
        if not ai_extraction:
            summary = {
                "total": 0,
                "trusted": 0,
                "review": 0,
                "untrusted": 0,
                "canonical_field_count_before": canonical_before,
                "canonical_field_count_after": canonical_before,
                "diagnostic_reason": "two_stage_skipped_no_fields",
            }
            logger.info(
                "validate.two_stage.exit %s",
                json.dumps(
                    {
                        "doc_type": document_type,
                        "file_name": filename,
                        "job_id": job_id,
                        **summary,
                    },
                    default=str,
                ),
            )
            return extracted_fields, summary
        
        # Run two-stage validation
        validated = extractor.process(ai_extraction, document_type)
        summary = extractor.get_extraction_summary(validated)
        
        # Build output with normalized values and validation metadata.
        # Keep original shape, but also update canonical field map for downstream consumers.
        validated_fields = dict(extracted_fields)
        validation_details: Dict[str, Dict[str, Any]] = {}
        
        for field_name, field_result in validated.items():
            normalized_value = (
                field_result.normalized_value
                if field_result.normalized_value is not None
                else field_result.raw_value
            )
            validated_fields[field_name] = normalized_value
            canonical_fields[field_name] = normalized_value
            
            # Add validation metadata
            validation_details[field_name] = {
                "status": field_result.status.value,
                "ai_confidence": field_result.ai_confidence,
                "validation_score": field_result.validation_score,
                "final_confidence": field_result.final_confidence,
                "issues": field_result.issues,
            }

        # Preserve canonical contract map when present (AI-first path).
        if isinstance(contract_fields, dict):
            validated_fields["extracted_fields"] = canonical_fields

        canonical_after = _count_populated_canonical_fields(canonical_fields)
        summary["canonical_field_count_before"] = canonical_before
        summary["canonical_field_count_after"] = canonical_after
        
        # Add validation metadata to the fields dict
        validated_fields["_two_stage_validation"] = {
            "summary": summary,
            "fields": validation_details,
        }
        
        logger.info(
            "Two-stage validation for %s [%s]: total=%d trusted=%d review=%d untrusted=%d",
            document_type, filename,
            summary.get("total", 0),
            summary.get("trusted", 0),
            summary.get("review", 0),
            summary.get("untrusted", 0),
        )
        logger.info(
            "validate.two_stage.exit %s",
            json.dumps(
                {
                    "doc_type": document_type,
                    "file_name": filename,
                    "job_id": job_id,
                    **summary,
                },
                default=str,
            ),
        )
        
        return validated_fields, summary
        
    except Exception as e:
        logger.warning("Two-stage validation failed for %s [%s]: %s", document_type, filename, e)
        # Return original fields on error
        return extracted_fields, {"total": 0, "trusted": 0, "review": 0, "untrusted": 0, "error": str(e)}


router = APIRouter(prefix="/api/validate", tags=["validation"])
logger = logging.getLogger(__name__)
PROFILE_DB = os.getenv("ENABLE_QUERY_PROFILING", "false").lower() == "true"


@contextmanager
def _profile_section(label: str):
    start = time.perf_counter()
    yield
    if PROFILE_DB:
        elapsed = (time.perf_counter() - start) * 1000
        logger.info("profile[%s]=%.2fms", label, elapsed)


def get_or_create_demo_user(db: Session) -> User:
    """Get or create a demo user for unauthenticated validation requests."""
    demo_email = "demo@trdrhub.com"
    user = db.query(User).filter(User.email == demo_email).first()
    
    if not user:
        # Create demo company first
        # Use raw SQL to avoid schema mismatch issues
        from sqlalchemy import text
        result = db.execute(text("SELECT id FROM companies WHERE name = :name"), {"name": "Demo Company"})
        demo_company_row = result.first()
        
        if not demo_company_row:
            # Insert demo company using raw SQL (matching actual schema)
            company_id = uuid4()
            db.execute(
                text("""
                    INSERT INTO companies (id, name, type, created_at, updated_at)
                    VALUES (:id, :name, :type, NOW(), NOW())
                """),
                {
                    "id": company_id,
                    "name": "Demo Company",
                    "type": "sme"
                }
            )
            db.flush()
            demo_company_id = company_id
        else:
            demo_company_id = demo_company_row[0]
        
        # Create demo user
        # Use pre-computed bcrypt hash to avoid bcrypt backend initialization issues in production
        # This is a bcrypt hash of "demo123" - demo users don't need real password security
        DEMO_PASSWORD_HASH = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.GQaEJSdVsqVfkG"
        user = User(
            email=demo_email,
            hashed_password=DEMO_PASSWORD_HASH,  # Pre-computed hash for "demo123"
            full_name="Demo User",
            role=UserRole.EXPORTER,
            is_active=True,
            company_id=demo_company_id,
            onboarding_completed=True,
            status="active",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    
    return user


async def get_user_optional(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> User:
    """Get current user if authenticated, otherwise return demo user."""
    if authorization and authorization.startswith("Bearer "):
        try:
            from app.core.security import get_current_user
            from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
            security = HTTPBearer()
            credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=authorization[7:])
            return await get_current_user(credentials=credentials, db=db)
        except:
            pass
    
    # Return demo user for unauthenticated requests
    return get_or_create_demo_user(db)


@router.post("/")
async def validate_doc(
    request: Request,
    current_user: User = Depends(get_user_optional),
    db: Session = Depends(get_db),
):
    """Validate LC documents."""
    import time
    start_time = time.time()
    
    # ==========================================================================
    # TIMING TELEMETRY - Track where time is spent
    # ==========================================================================
    timings: Dict[str, float] = {}
    
    def checkpoint(name: str) -> None:
        """Record time elapsed since start for a named checkpoint."""
        timings[name] = round(time.time() - start_time, 3)
    
    checkpoint("request_received")
    
    audit_service = AuditService(db)
    audit_context = create_audit_context(request)
    
    document_summaries: List[Dict[str, Any]] = []

    try:
        content_type = request.headers.get("content-type", "")
        payload: dict
        files_list = []  # Collect files for validation
        
        if content_type.startswith("multipart/form-data"):
            form = await request.form()
            payload = {}
            for key, value in form.multi_items():
                # Check if this is a file upload (UploadFile instance)
                if hasattr(value, "filename") and hasattr(value, "read"):
                    # This is a file upload - validate it
                    file_obj = value
                    header_bytes = await file_obj.read(8)
                    await file_obj.seek(0)  # Reset for processing
                    
                    # Content-based validation
                    is_valid, error_message = validate_upload_file(
                        header_bytes,
                        filename=file_obj.filename,
                        content_type=file_obj.content_type
                    )
                    
                    if not is_valid:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Invalid file content for {file_obj.filename}: {error_message}. File content does not match declared type."
                        )
                    
                    files_list.append(file_obj)
                    continue
                
                # Safely handle form field values - ensure they're strings
                # Handle potential encoding issues by converting to string safely
                # Skip if this looks like binary data (might be misidentified file)
                if isinstance(value, bytes):
                    # Check if this looks like binary data (PDF, image, etc.)
                    # PDFs start with %PDF, images have magic bytes
                    if len(value) > 4 and (
                        value.startswith(b'%PDF') or 
                        value.startswith(b'\x89PNG') or 
                        value.startswith(b'\xff\xd8\xff') or
                        value.startswith(b'GIF8') or
                        value.startswith(b'PK\x03\x04')  # ZIP
                    ):
                        # This is likely a file that wasn't properly identified
                        # Skip it or log a warning, but don't try to decode as text
                        continue
                    
                    # If value is bytes, try to decode as UTF-8, fallback to latin-1
                    try:
                        payload[key] = value.decode('utf-8')
                    except UnicodeDecodeError:
                        # Fallback to latin-1 which can decode any byte sequence
                        try:
                            payload[key] = value.decode('latin-1')
                        except Exception:
                            # If all decoding fails, skip this field
                            continue
                elif isinstance(value, str):
                    payload[key] = value
                else:
                    # Convert other types to string, but skip if it's a file-like object
                    if hasattr(value, 'read') or hasattr(value, 'filename'):
                        continue
                    try:
                        payload[key] = str(value)
                    except Exception:
                        # Skip if conversion fails
                        continue
        else:
            payload = await request.json()

        # Parse JSON fields safely (document_tags, metadata)
        if "document_tags" in payload and isinstance(payload["document_tags"], str):
            try:
                payload["document_tags"] = json.loads(payload["document_tags"])
            except (json.JSONDecodeError, TypeError, UnicodeDecodeError):
                # If parsing fails, set to empty dict
                payload["document_tags"] = {}
        
        if "metadata" in payload and isinstance(payload["metadata"], str):
            try:
                payload["metadata"] = json.loads(payload["metadata"])
            except (json.JSONDecodeError, TypeError, UnicodeDecodeError):
                # If parsing fails, set to None
                payload["metadata"] = None

        doc_type = (
            payload.get("document_type")
            or payload.get("documentType")
            or "letter_of_credit"
        )
        payload["document_type"] = doc_type
        if not doc_type:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing document_type")

        checkpoint("form_parsed")

        # Build job context early so async extraction/two-stage telemetry always
        # emits a stable job_id sourced from server context (not request payload).
        metadata = payload.get("metadata")
        user_type = payload.get("userType") or payload.get("user_type")
        validation_session = None
        job_id = None
        if user_type in ["bank", "exporter", "importer"] or metadata:
            session_service = ValidationSessionService(db)
            validation_session = session_service.create_session(current_user)
            if current_user.company_id:
                validation_session.company_id = current_user.company_id
            validation_session.status = SessionStatus.PROCESSING.value
            validation_session.processing_started_at = func.now()
            db.commit()
            job_id = str(validation_session.id)
            checkpoint("session_created")
        else:
            job_id = str(uuid4())

        # Extract structured data from uploaded files (respecting any document tags)
        document_tags = payload.get("document_tags")
        extracted_context = await _build_document_context(
            files_list,
            document_tags,
            job_id=job_id,
        )
        checkpoint("ocr_extraction_complete")
        if extracted_context:
            logger.info(
                "Extracted context from %d files. Keys: %s",
                len(files_list),
                list(extracted_context.keys()),
            )
            document_details = extracted_context.get("documents") or []
            if document_details:
                status_counts: Dict[str, int] = {}
                for doc in document_details:
                    extraction_stat = doc.get("extraction_status") or "unknown"
                    status_counts[extraction_stat] = status_counts.get(extraction_stat, 0) + 1
                logger.info(
                    "Document extraction status summary: total=%d details=%s",
                    len(document_details),
                    status_counts,
                )
            payload.update(extracted_context)
        else:
            logger.warning("No structured data extracted from %d uploaded files", len(files_list))
        if payload.get("lc"):
            payload["lc"] = _normalize_lc_payload_structures(payload["lc"])
        
        # =====================================================================
        # NO LC FOUND GATE - Block early if no LC document detected
        # This prevents expensive validation on incomplete document sets
        # =====================================================================
        user_type = payload.get("userType") or payload.get("user_type")
        documents_presence = (
            extracted_context.get("documents_presence") if extracted_context else {}
        ) or {}
        detected_doc_types = [
            doc.get("documentType") or doc.get("document_type")
            for doc in (extracted_context.get("documents") if extracted_context else []) or []
        ]
        
        # Check if any LC-like document was found
        lc_document_types = {"letter_of_credit", "swift_message", "lc_application"}
        has_lc_document = (
            any(documents_presence.get(dt, {}).get("present") for dt in lc_document_types) or
            any(dt in lc_document_types for dt in detected_doc_types) or
            bool(payload.get("lc", {}).get("raw_text"))  # Also check if LC data exists
        )
        
        # Block if no LC found on Exporter dashboard (LC is required for validation)
        if user_type == "exporter" and not has_lc_document and len(files_list) > 0:
            logger.warning(
                f"No LC document found in {len(files_list)} uploaded files. "
                f"Detected types: {detected_doc_types}"
            )
            return {
                "status": "blocked",
                "block_reason": "no_lc_found",
                "error": {
                    "error_code": "NO_LC_FOUND",
                    "title": "No Letter of Credit Found",
                    "message": "We couldn't detect a Letter of Credit in your uploaded documents.",
                    "detail": f"Detected document types: {', '.join(set(detected_doc_types)) or 'None identified'}",
                    "action": "Add Letter of Credit",
                    "help_text": (
                        "The Letter of Credit (MT700/MT760/SWIFT message) is required "
                        "as the baseline for compliance checking. Please upload your LC document."
                    ),
                },
                "detected_documents": [
                    {"type": dt, "filename": doc.get("name") or doc.get("filename")}
                    for doc, dt in zip(
                        (extracted_context.get("documents") if extracted_context else []) or [],
                        detected_doc_types
                    )
                ],
                "message": "Please upload your Letter of Credit (MT700/MT760) to proceed with validation.",
                "action_required": "Add Letter of Credit",
            }
        
        context_contains_structured_data = any(
            key in payload for key in ("lc", "invoice", "bill_of_lading", "documents")
        )
        
        if context_contains_structured_data:
            logger.info(f"Payload contains structured data: {list(payload.keys())}")
        else:
            logger.warning("Payload does not contain structured data - JSON rules will be skipped")

        lc_context = payload.get("lc") or {}
        shipment_context = _resolve_shipment_context(payload)
        
        # First, check if LC type was extracted from the document (from :40A: or AI extraction)
        extracted_lc_type = (
            lc_context.get("lc_type") or 
            lc_context.get("form_of_doc_credit") or
            (lc_context.get("mt700") or {}).get("form_of_doc_credit")
        )
        extracted_lc_type_confidence = lc_context.get("lc_type_confidence", 0)
        extracted_lc_type_reason = lc_context.get("lc_type_reason", "")
        
        # If extracted, use it; otherwise fall back to import/export detection
        override_lc_type = _extract_lc_type_override(payload)
        
        if extracted_lc_type and str(extracted_lc_type).lower() not in ["unknown", "none", ""]:
            # Use extracted LC type from document
            lc_type = str(extracted_lc_type).lower().replace(" ", "_")
            lc_type_reason = extracted_lc_type_reason or f"Extracted from LC document: {extracted_lc_type}"
            lc_type_confidence = extracted_lc_type_confidence if extracted_lc_type_confidence > 0 else 0.85
            lc_type_source = lc_context.get("lc_type_source", "document_extraction")
            lc_type_guess = {"lc_type": lc_type, "reason": lc_type_reason, "confidence": lc_type_confidence}
            logger.info(f"LC type from document extraction: {lc_type} (confidence={lc_type_confidence})")
        else:
            # Fall back to import/export detection based on country relationships
            lc_type_guess = detect_lc_type(lc_context, shipment_context)
            lc_type_source = "auto"
            lc_type = lc_type_guess["lc_type"]
            lc_type_reason = lc_type_guess["reason"]
            lc_type_confidence = lc_type_guess["confidence"]
            
            # AI Enhancement: If rule-based confidence is low, use AI for better accuracy
            if lc_type_confidence < 0.70 or lc_type == LCType.UNKNOWN.value:
                try:
                    from app.services.document_intelligence import detect_lc_type_ai
                    lc_text = context.get("lc_text") or lc_context.get("raw_text", "")
                    if lc_text and len(lc_text) > 100:
                        ai_result = await detect_lc_type_ai(lc_text)
                        if ai_result.get("confidence", 0) > lc_type_confidence:
                            lc_type = ai_result.get("lc_type", lc_type)
                            lc_type_reason = ai_result.get("reason", lc_type_reason)
                            lc_type_confidence = ai_result.get("confidence", lc_type_confidence)
                            lc_type_source = "ai"
                            lc_type_guess = {
                                "lc_type": lc_type,
                                "reason": lc_type_reason,
                                "confidence": lc_type_confidence,
                                "is_draft": ai_result.get("is_draft", False),
                            }
                            logger.info(f"AI improved LC type detection: {lc_type} (confidence={lc_type_confidence})")
                except Exception as ai_err:
                    logger.warning(f"AI LC type detection failed, using rule-based: {ai_err}")
        
        # Override takes precedence
        if override_lc_type:
            lc_type = override_lc_type
            lc_type_source = "override"
        payload["lc_type"] = lc_type
        payload["lc_type_reason"] = lc_type_reason
        payload["lc_type_confidence"] = lc_type_confidence
        payload["lc_type_source"] = lc_type_source
        payload["lc_detection"] = {
            "auto": lc_type_guess,
            "lc_type": lc_type,
            "source": lc_type_source,
        }
        logger.info(
            "LC type detection: auto=%s override=%s final=%s confidence=%.2f reason=%s",
            lc_type_guess["lc_type"],
            override_lc_type,
            lc_type,
            lc_type_confidence,
            lc_type_reason,
        )
        lc_type_is_unknown = lc_type == LCType.UNKNOWN.value
        is_draft_lc = lc_type_guess.get("is_draft", False) or lc_type == "draft"
        checkpoint("lc_type_detected")

        # =====================================================================
        # DASHBOARD/LC TYPE VALIDATION
        # Ensure LC type matches the dashboard being used
        # =====================================================================
        user_type = payload.get("userType") or payload.get("user_type")
        
        # Check for mismatched dashboard/LC type
        dashboard_lc_mismatch = None
        if user_type == "exporter" and lc_type == "import":
            dashboard_lc_mismatch = {
                "error_code": "WRONG_DASHBOARD",
                "title": "Import LC on Exporter Dashboard",
                "message": "This appears to be an Import Letter of Credit where you are the APPLICANT (buyer).",
                "detail": f"Detection: {lc_type_reason}",
                "action": "Go to Importer Dashboard",
                "redirect_url": "/importer/upload",
            }
        elif user_type == "exporter" and is_draft_lc:
            dashboard_lc_mismatch = {
                "error_code": "DRAFT_LC_ON_EXPORTER",
                "title": "Draft LC Detected",
                "message": "This appears to be a Draft Letter of Credit that hasn't been issued yet.",
                "detail": "The Exporter Dashboard validates documents against ISSUED LCs. For draft LC review, use the Importer Dashboard.",
                "action": "Go to Importer Dashboard",
                "redirect_url": "/importer/upload",
            }
        elif user_type == "importer" and lc_type == "export" and lc_type_confidence > 0.75:
            dashboard_lc_mismatch = {
                "error_code": "WRONG_DASHBOARD",
                "title": "Export LC on Importer Dashboard",
                "message": "This appears to be an Export Letter of Credit where you are the BENEFICIARY (seller).",
                "detail": f"Detection: {lc_type_reason}",
                "action": "Go to Exporter Dashboard",
                "redirect_url": "/exporter/upload",
            }
        
        # If mismatch detected with high confidence, return early with clear message
        if dashboard_lc_mismatch and lc_type_confidence > 0.70:
            logger.warning(
                f"Dashboard/LC type mismatch: user_type={user_type}, lc_type={lc_type}, "
                f"confidence={lc_type_confidence}, is_draft={is_draft_lc}"
            )
            return {
                "status": "blocked",
                "block_reason": "dashboard_lc_mismatch",
                "error": dashboard_lc_mismatch,
                "lc_detection": {
                    "lc_type": lc_type,
                    "confidence": lc_type_confidence,
                    "reason": lc_type_reason,
                    "is_draft": is_draft_lc,
                    "source": lc_type_source,
                },
                "message": dashboard_lc_mismatch["message"],
                "action_required": dashboard_lc_mismatch["action"],
                "redirect_url": dashboard_lc_mismatch["redirect_url"],
            }

        # =====================================================================
        # ATTACH CONTEXT METADATA + PERSIST DOCUMENTS
        # Session was created before extraction so telemetry carries correct job_id.
        # =====================================================================
        if validation_session is not None:
            extracted_payload = dict(validation_session.extracted_data or {})

            # Store metadata based on user type
            if metadata:
                try:
                    if isinstance(metadata, str):
                        metadata = json.loads(metadata)
                    org_id = None
                    if hasattr(request, 'state') and hasattr(request.state, 'org_id'):
                        org_id = request.state.org_id
                    extracted_payload["bank_metadata"] = {
                        "client_name": metadata.get("clientName"),
                        "lc_number": metadata.get("lcNumber"),
                        "date_received": metadata.get("dateReceived"),
                        "org_id": org_id,
                    }
                except (json.JSONDecodeError, TypeError):
                    pass
            elif user_type in ["exporter", "importer"]:
                lc_number = payload.get("lc_number") or payload.get("lcNumber")
                workflow_type = payload.get("workflow_type") or payload.get("workflowType")
                if lc_number or workflow_type:
                    extracted_payload.update(
                        {
                            "lc_number": lc_number,
                            "user_type": user_type,
                            "workflow_type": workflow_type,
                        }
                    )

            debug_trace = extracted_context.get("_debug_extraction_trace") if isinstance(extracted_context, dict) else None
            if isinstance(debug_trace, list):
                extracted_payload["_debug_extraction_trace"] = debug_trace

            validation_session.extracted_data = extracted_payload or None

            db.commit()

            # =====================================================================
            # PERSIST DOCUMENTS TO DATABASE
            # This enables customs pack generation and document retrieval
            # =====================================================================
            try:
                document_list = payload.get("documents") or []
                for idx, doc_info in enumerate(document_list):
                    doc_record = Document(
                        validation_session_id=validation_session.id,
                        document_type=doc_info.get("document_type") or doc_info.get("type") or "unknown",
                        original_filename=doc_info.get("filename") or doc_info.get("name") or f"document_{idx + 1}.pdf",
                        s3_key=f"validation/{validation_session.id}/{doc_info.get('filename', f'doc_{idx}')}",  # Placeholder
                        file_size=doc_info.get("file_size") or doc_info.get("size") or 0,
                        content_type=doc_info.get("content_type") or "application/pdf",
                        ocr_text=doc_info.get("raw_text_preview") or doc_info.get("raw_text") or "",
                        ocr_confidence=doc_info.get("ocr_confidence"),
                        extracted_fields={
                            **(doc_info.get("extracted_fields") or {}),
                            "_extraction_artifacts_v1": doc_info.get("extraction_artifacts_v1") or _empty_extraction_artifacts_v1(
                                raw_text=doc_info.get("raw_text") or doc_info.get("raw_text_preview") or "",
                                ocr_confidence=doc_info.get("ocr_confidence"),
                            ),
                        },
                    )
                    db.add(doc_record)
                db.commit()
                logger.info("Persisted %d documents to database for session %s", len(document_list), job_id)
            except Exception as doc_persist_error:
                logger.warning("Failed to persist documents to DB: %s", doc_persist_error)
                # Don't fail validation if document persistence fails

        # =====================================================================
        # V2 VALIDATION PIPELINE - PRIMARY FLOW
        # This is the core validation engine. Legacy flow is disabled.
        # If LC extraction fails (missing critical fields), we block validation.
        # =====================================================================
        v2_gate_result = None
        v2_baseline = None
        v2_issues = []
        v2_crossdoc_issues = []
        
        try:
            # Build LCBaseline from extracted context
            v2_baseline = _build_lc_baseline_from_context(lc_context)
            
            # Run validation gate
            v2_gate = ValidationGate()
            v2_gate_result = v2_gate.check_from_baseline(v2_baseline)
            
            logger.info(
                "V2 Validation Gate: status=%s can_proceed=%s completeness=%.1f%% critical=%.1f%%",
                v2_gate_result.status.value,
                v2_gate_result.can_proceed,
                v2_gate_result.completeness * 100,
                v2_gate_result.critical_completeness * 100,
            )
            checkpoint("validation_gate_complete")
            
            # =====================================================================
            # BLOCKED RESPONSE - Return immediately if gate blocks
            # This is the key fix: NO more "100% compliant with N/A fields"
            # =====================================================================
            if not v2_gate_result.can_proceed:
                logger.warning(
                    "V2 Gate BLOCKED: %s. Missing critical: %s",
                    v2_gate_result.block_reason,
                    v2_gate_result.missing_critical,
                )
                
                # Build blocked response
                processing_duration = time.time() - start_time
                blocked_result = _build_blocked_structured_result(
                    v2_gate_result=v2_gate_result,
                    v2_baseline=v2_baseline,
                    lc_type=lc_type,
                    processing_duration=processing_duration,
                    documents=payload.get("documents") or [],
                )
                
                # Store blocked result in validation session so it can be retrieved later
                if validation_session:
                    validation_session.status = SessionStatus.COMPLETED.value
                    validation_session.processing_completed_at = func.now()
                    validation_session.validation_results = {
                        "structured_result": blocked_result,
                        "validation_blocked": True,
                        "block_reason": v2_gate_result.block_reason,
                    }
                    db.commit()
                
                return {
                    "job_id": str(job_id),
                    "jobId": str(job_id),
                    "structured_result": blocked_result,
                    "telemetry": {
                        "validation_blocked": True,
                        "block_reason": v2_gate_result.block_reason,
                        "timings": timings,
                        "total_time_seconds": round(time.time() - start_time, 3),
                    },
                }
            # =====================================================================
            
            # Gate passed - run v2 IssueEngine (without full rule execution)
            from app.services.validation.issue_engine import IssueEngine
            
            # Create IssueEngine without RuleExecutor to avoid running all 2,159 rules
            # Full rule execution is DISABLED due to false positives from country-specific rules
            issue_engine = IssueEngine()
            
            v2_issues = issue_engine.generate_extraction_issues(v2_baseline)
            logger.info("V2 IssueEngine generated %d extraction issues", len(v2_issues))
            
            # =================================================================
            # EXECUTE DATABASE RULES (2500+ rules from DB)
            # Filters by jurisdiction, document_type, and domain
            # =================================================================
            db_rule_issues = []
            db_rules_debug = {"enabled": False, "status": "not_started"}
            try:
                # =============================================================
                # DYNAMIC JURISDICTION & DOMAIN DETECTION
                # Detects relevant rulesets based on LC and document content
                # =============================================================
                lc_ctx = extracted_context.get("lc") or payload.get("lc") or {}
                mt700 = lc_ctx.get("mt700") or {}
                coo = payload.get("certificate_of_origin") or {}
                invoice = payload.get("invoice") or {}
                bl = payload.get("bill_of_lading") or {}
                
                # Country code mapping (common variations)
                COUNTRY_CODE_MAP = {
                    "bangladesh": "bd", "peoples republic of bangladesh": "bd",
                    "india": "in", "republic of india": "in",
                    "china": "cn", "peoples republic of china": "cn", "prc": "cn",
                    "united states": "us", "usa": "us", "united states of america": "us",
                    "united arab emirates": "ae", "uae": "ae",
                    "saudi arabia": "sa", "kingdom of saudi arabia": "sa",
                    "singapore": "sg", "republic of singapore": "sg",
                    "hong kong": "hk", "hong kong sar": "hk",
                    "germany": "de", "federal republic of germany": "de",
                    "united kingdom": "uk", "great britain": "uk", "gb": "uk",
                    "japan": "jp", "turkey": "tr", "pakistan": "pk",
                    "indonesia": "id", "malaysia": "my", "thailand": "th",
                    "vietnam": "vn", "philippines": "ph", "south korea": "kr",
                    "brazil": "br", "mexico": "mx", "egypt": "eg",
                }
                
                def normalize_country(country_str: str) -> str:
                    """Convert country name/code to 2-letter ISO code."""
                    if not country_str:
                        return ""
                    country_lower = country_str.lower().strip()
                    # Already a 2-letter code?
                    if len(country_lower) == 2:
                        return country_lower
                    return COUNTRY_CODE_MAP.get(country_lower, "")
                
                # Detect jurisdictions from multiple sources
                detected_jurisdictions = set()
                
                # From LC
                for field in ["jurisdiction", "country", "issuing_bank_country", "advising_bank_country"]:
                    val = normalize_country(lc_ctx.get(field, "") or mt700.get(field, ""))
                    if val:
                        detected_jurisdictions.add(val)
                
                # From beneficiary (exporter) - usually the exporter's country matters most
                beneficiary = lc_ctx.get("beneficiary") or mt700.get("beneficiary") or {}
                if isinstance(beneficiary, dict):
                    val = normalize_country(beneficiary.get("country", ""))
                    if val:
                        detected_jurisdictions.add(val)
                elif isinstance(beneficiary, str):
                    # Try to extract country from address string
                    for country, code in COUNTRY_CODE_MAP.items():
                        if country in beneficiary.lower():
                            detected_jurisdictions.add(code)
                            break
                
                # From Certificate of Origin
                origin_country = normalize_country(
                    coo.get("country_of_origin") or 
                    coo.get("origin_country") or 
                    coo.get("country") or ""
                )
                if origin_country:
                    detected_jurisdictions.add(origin_country)
                
                # From Invoice seller address
                seller_country = normalize_country(
                    invoice.get("seller_country") or
                    invoice.get("exporter_country") or ""
                )
                if seller_country:
                    detected_jurisdictions.add(seller_country)
                
                # From B/L port of loading (often indicates export country)
                port_of_loading = (bl.get("port_of_loading") or "").lower()
                if "chittagong" in port_of_loading or "dhaka" in port_of_loading or "mongla" in port_of_loading:
                    detected_jurisdictions.add("bd")
                elif "shanghai" in port_of_loading or "shenzhen" in port_of_loading or "ningbo" in port_of_loading:
                    detected_jurisdictions.add("cn")
                elif "mumbai" in port_of_loading or "chennai" in port_of_loading or "nhava sheva" in port_of_loading:
                    detected_jurisdictions.add("in")
                
                # Build supplement domains dynamically
                supplement_domains = ["icc.isbp745", "icc.lcopilot.crossdoc"]
                
                # Add jurisdiction-specific regulations
                for jur in detected_jurisdictions:
                    if jur and jur != "global":
                        supplement_domains.append(f"regulations.{jur}")
                
                # Add sanctions screening
                supplement_domains.append("sanctions.screening")
                
                # Primary jurisdiction (prefer exporter's country)
                primary_jurisdiction = "global"
                if origin_country:
                    primary_jurisdiction = origin_country
                elif seller_country:
                    primary_jurisdiction = seller_country
                elif detected_jurisdictions:
                    primary_jurisdiction = list(detected_jurisdictions)[0]
                
                logger.info(
                    "Dynamic jurisdiction detection: primary=%s, all=%s, supplements=%s",
                    primary_jurisdiction, list(detected_jurisdictions), supplement_domains
                )
                
                # Build document data for rule engine
                db_rule_payload = {
                    "jurisdiction": primary_jurisdiction,
                    "domain": "icc.ucp600",
                    "supplement_domains": supplement_domains,
                    # LC data
                    "lc": lc_ctx,
                    "lc_number": v2_baseline.lc_number if v2_baseline else None,
                    "amount": v2_baseline.amount if v2_baseline else None,
                    "currency": v2_baseline.currency if v2_baseline else None,
                    "expiry_date": v2_baseline.expiry_date if v2_baseline else None,
                    # Documents
                    "invoice": payload.get("invoice"),
                    "bill_of_lading": payload.get("bill_of_lading"),
                    "insurance": payload.get("insurance"),
                    "certificate_of_origin": payload.get("certificate_of_origin"),
                    "packing_list": payload.get("packing_list"),
                    # Extracted context
                    "extracted_context": extracted_context,
                }
                
                # Determine primary document type for filtering
                primary_doc_type = "letter_of_credit"
                if payload.get("invoice"):
                    primary_doc_type = "commercial_invoice"
                
                logger.info(
                    "Executing DB rules: jurisdiction=%s, domain=icc.ucp600, supplements=%s, doc_type=%s",
                    primary_jurisdiction, supplement_domains, primary_doc_type
                )
                
                db_rule_issues = await validate_document_async(
                    document_data=db_rule_payload,
                    document_type=primary_doc_type,
                )
                
                # Filter out N/A and passed rules, keep only failures
                db_rule_issues = [
                    issue for issue in db_rule_issues
                    if not issue.get("passed", False) and not issue.get("not_applicable", False)
                ]
                
                logger.info("DB rules executed: %d issues found (after filtering)", len(db_rule_issues))
                
                # Store debug info for response
                db_rules_debug = {
                    "enabled": True,
                    "domain": "icc.ucp600",
                    "supplements": supplement_domains,
                    "primary_jurisdiction": primary_jurisdiction,
                    "detected_jurisdictions": list(detected_jurisdictions),
                    "issues_found": len(db_rule_issues),
                }
                
            except Exception as db_rule_err:
                logger.warning("DB rule execution failed (continuing with other validators): %s", str(db_rule_err))
                db_rules_debug = {
                    "enabled": False,
                    "error": str(db_rule_err),
                }
            
            # Run v2 CrossDocValidator
            from app.services.validation.crossdoc_validator import CrossDocValidator
            crossdoc_validator = CrossDocValidator()
            crossdoc_result = crossdoc_validator.validate_all(
                lc_baseline=v2_baseline,
                invoice=payload.get("invoice"),
                bill_of_lading=payload.get("bill_of_lading"),
                insurance=payload.get("insurance"),
                certificate_of_origin=payload.get("certificate_of_origin"),
                packing_list=payload.get("packing_list"),
            )
            v2_crossdoc_issues = crossdoc_result.issues
            logger.info("V2 CrossDocValidator found %d issues", len(v2_crossdoc_issues))
            checkpoint("crossdoc_validation_complete")
            
            # =================================================================
            # PRICE VERIFICATION (LCopilot Integration)
            # =================================================================
            try:
                from app.services.crossdoc import run_price_verification_checks
                
                price_verify_payload = {
                    "invoice": payload.get("invoice") or {},
                    "lc": payload.get("lc") or extracted_context.get("lc") or {},
                    "documents": payload.get("documents") or extracted_context.get("documents") or [],
                }
                
                price_issues = await run_price_verification_checks(
                    payload=price_verify_payload,
                    include_tbml_checks=True,
                )
                
                if price_issues:
                    logger.info("Price verification found %d issues", len(price_issues))
                    v2_crossdoc_issues.extend(price_issues)
            except Exception as e:
                logger.warning(f"Price verification skipped: {e}")
            
            # =================================================================
            # AI VALIDATION ENGINE
            # =================================================================
            from app.services.validation.ai_validator import run_ai_validation, AIValidationIssue
            
            # Build LC data for AI from multiple potential sources
            lc_data_for_ai = {}
            
            # Get raw text from extracted_context (built from uploaded files)
            # The LC raw text is stored in context["lc"]["raw_text"] or context["lc_text"]
            lc_context = extracted_context.get("lc") or {}
            lc_raw_text = (
                lc_context.get("raw_text") or  # Primary: from lc object in extracted_context
                extracted_context.get("lc_text") or  # Alternative: direct lc_text
                (payload.get("lc") or {}).get("raw_text") or  # Fallback: from payload
                ""
            )
            lc_data_for_ai["raw_text"] = lc_raw_text
            logger.info(f"AI Validation: LC raw_text length = {len(lc_raw_text)} chars")
            
            # Get goods description from various locations
            mt700 = lc_context.get("mt700") or {}
            lc_data_for_ai["goods_description"] = (
                lc_context.get("goods_description") or
                mt700.get("goods_description") or 
                mt700.get("45A") or
                ""
            )
            logger.info(f"AI Validation: goods_description length = {len(lc_data_for_ai['goods_description'])} chars")
            
            # Get goods list
            lc_data_for_ai["goods"] = (
                lc_context.get("goods") or 
                lc_context.get("goods_items") or 
                mt700.get("goods") or
                []
            )
            
            # Get documents from both payload and extracted_context
            documents_for_ai = (
                extracted_context.get("documents") or  # Primary: from extraction
                payload.get("documents") or  # Fallback: from payload
                []
            )
            logger.info(f"AI Validation: {len(documents_for_ai)} documents to check")
            
            ai_issues, ai_metadata = await run_ai_validation(
                lc_data=lc_data_for_ai,
                documents=documents_for_ai,
                extracted_context=extracted_context,
            )
            
            logger.info(
                "AI Validation: found %d issues (critical=%d, major=%d)",
                len(ai_issues),
                ai_metadata.get("critical_issues", 0),
                ai_metadata.get("major_issues", 0),
            )
            
            # Convert AI issues to same format as crossdoc issues
            for ai_issue in ai_issues:
                v2_crossdoc_issues.append(ai_issue)
            checkpoint("ai_validation_complete")
            
            # =================================================================
            # HYBRID VALIDATION ENHANCEMENTS
            # =================================================================
            
            # 1. Bank Profile Detection
            bank_profile = None
            try:
                bank_profile = detect_bank_from_lc({
                    "issuing_bank": lc_context.get("issuing_bank") or mt700.get("issuing_bank") or "",
                    "advising_bank": lc_context.get("advising_bank") or mt700.get("advising_bank") or "",
                    "raw_text": lc_raw_text,
                })
                logger.info(f"Bank profile detected: {bank_profile.bank_code} ({bank_profile.strictness.value})")
            except Exception as e:
                logger.warning(f"Bank profile detection failed: {e}")
                bank_profile = get_bank_profile()  # Default profile
            
            # 2. Enhanced Requirement Parsing (v2 with caching)
            requirement_graph = None
            try:
                requirement_graph = parse_lc_requirements_sync_v2(lc_raw_text)
                if requirement_graph:
                    logger.info(
                        f"RequirementGraph: {len(requirement_graph.required_documents)} docs, "
                        f"{len(requirement_graph.tolerances)} tolerances, "
                        f"{len(requirement_graph.contradictions)} contradictions"
                    )
                    # Store tolerances in metadata for downstream use
                    ai_metadata["tolerances"] = {
                        k: v.to_dict() if hasattr(v, 'to_dict') else {
                            "field": v.field,
                            "tolerance_percent": v.tolerance_percent,
                            "source": v.source.value,
                        }
                        for k, v in requirement_graph.tolerances.items()
                    }
                    ai_metadata["contradictions"] = [
                        {"clause_1": c.clause_1, "clause_2": c.clause_2, "resolution": c.resolution}
                        for c in requirement_graph.contradictions
                    ]
            except Exception as e:
                logger.warning(f"RequirementGraph parsing failed: {e}")
            
            # 3. Calculate overall extraction confidence
            extraction_confidence_summary = None
            try:
                extraction_confidence_summary = calculate_overall_extraction_confidence(extracted_context)
                logger.info(
                    f"Extraction confidence: avg={extraction_confidence_summary.get('average_confidence', 0):.2f}, "
                    f"lowest={extraction_confidence_summary.get('lowest_confidence_document', 'N/A')}"
                )
            except Exception as e:
                logger.warning(f"Extraction confidence calculation failed: {e}")
            
        except Exception as e:
            logger.error("V2 pipeline error: %s", e, exc_info=True)
            # Don't fall back to legacy - just log the error
            # v2_gate_result remains None, issues remain empty
        # =====================================================================

        # Ensure user has a company (demo user will have one)
        if not current_user.company:
            # Try to get or create company for user
            demo_company = db.query(Company).filter(Company.name == "Demo Company").first()
            if not demo_company:
                demo_company = Company(
                    name="Demo Company",
                    contact_email=current_user.email or "demo@trdrhub.com",
                    plan=PlanType.FREE,
                    status=CompanyStatus.ACTIVE,
                )
                db.add(demo_company)
                db.flush()
            current_user.company_id = demo_company.id
            db.commit()
            db.refresh(current_user)

        # Skip quota checks for demo user (allows validation to work without billing)
        if current_user.email != "demo@trdrhub.com":
            entitlements = EntitlementService(db)
            try:
                entitlements.enforce_quota(current_user.company, UsageAction.VALIDATE)
            except EntitlementError as exc:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail={
                        "code": "quota_exceeded",
                        "message": exc.message,
                        "quota": exc.result.to_dict(),
                        "next_action_url": exc.next_action_url,
                    },
                ) from exc

        # =====================================================================
        # V2 VALIDATION - PRIMARY PATH (Legacy disabled)
        # Note: Session was already created above, before gating check
        # =====================================================================
        request_user_type = _extract_request_user_type(payload)
        
        # Build unified issues list from v2 components
        results = []  # Legacy results - empty
        failed_results = []
        
        checkpoint("pre_issue_conversion")
        
        # =================================================================
        # BATCH LOOKUP: Collect all UCP/ISBP refs FIRST, then ONE query each
        # This replaces N individual DB queries with just 2 batch queries
        # =================================================================
        from app.services.rules_service import batch_lookup_descriptions
        
        all_ucp_refs = []
        all_isbp_refs = []
        
        # Collect refs from v2_issues
        if v2_issues:
            for issue in v2_issues:
                issue_dict = issue.to_dict() if hasattr(issue, 'to_dict') else issue
                ucp_ref = issue_dict.get("ucp_reference")
                isbp_ref = issue_dict.get("isbp_reference")
                if ucp_ref and not issue_dict.get("ucp_description"):
                    all_ucp_refs.append(ucp_ref)
                if isbp_ref and not issue_dict.get("isbp_description"):
                    all_isbp_refs.append(isbp_ref)
        
        # Collect refs from crossdoc issues
        if v2_crossdoc_issues:
            for issue in v2_crossdoc_issues:
                issue_dict = issue.to_dict() if hasattr(issue, 'to_dict') else issue
                ucp_ref = issue_dict.get("ucp_reference") or issue_dict.get("ucp_article") or ""
                isbp_ref = issue_dict.get("isbp_reference") or issue_dict.get("isbp_paragraph") or ""
                if ucp_ref and not issue_dict.get("ucp_description"):
                    all_ucp_refs.append(ucp_ref)
                if isbp_ref and not issue_dict.get("isbp_description"):
                    all_isbp_refs.append(isbp_ref)
        
        # Collect refs from DB rule issues
        if db_rule_issues:
            for issue in db_rule_issues:
                issue_dict = issue if isinstance(issue, dict) else issue.to_dict() if hasattr(issue, 'to_dict') else {}
                ucp_ref = issue_dict.get("ucp_reference") or issue_dict.get("ucp_article") or ""
                isbp_ref = issue_dict.get("isbp_reference") or issue_dict.get("isbp_paragraph") or ""
                if ucp_ref and not issue_dict.get("ucp_description"):
                    all_ucp_refs.append(ucp_ref)
                if isbp_ref and not issue_dict.get("isbp_description"):
                    all_isbp_refs.append(isbp_ref)
        
        # BATCH LOOKUP: 2 queries instead of N
        ucp_desc_cache, isbp_desc_cache = batch_lookup_descriptions(all_ucp_refs, all_isbp_refs)
        logger.info(f"Batch lookup: {len(ucp_desc_cache)} UCP refs, {len(isbp_desc_cache)} ISBP refs")
        
        # Helper to get description from cache
        def _get_ucp_desc(ref: str) -> Optional[str]:
            if not ref:
                return None
            # Try cache first, no fallback to individual query
            return ucp_desc_cache.get(ref) or ucp_desc_cache.get(ref.replace("Article ", "").replace("UCP600 ", ""))
        
        def _get_isbp_desc(ref: str) -> Optional[str]:
            if not ref:
                return None
            return isbp_desc_cache.get(ref) or isbp_desc_cache.get(ref.replace("ISBP745 ", "").replace("¶", ""))
        
        # Convert v2 issues to legacy format for compatibility
        if v2_issues:
            for issue in v2_issues:
                issue_dict = issue.to_dict() if hasattr(issue, 'to_dict') else issue
                ucp_ref = issue_dict.get("ucp_reference")
                isbp_ref = issue_dict.get("isbp_reference")
                failed_results.append({
                    "rule": issue_dict.get("rule", "V2-ISSUE"),
                    "title": issue_dict.get("title", "Validation Issue"),
                    "passed": False,
                    "severity": issue_dict.get("severity", "major"),
                    "message": issue_dict.get("message", ""),
                    "expected": issue_dict.get("expected", ""),
                    "found": issue_dict.get("found", issue_dict.get("actual", "")),
                    "suggested_fix": issue_dict.get("suggested_fix", issue_dict.get("suggestion", "")),
                    "documents": issue_dict.get("documents", []),
                    "ucp_reference": ucp_ref,
                    "isbp_reference": isbp_ref,
                    "ucp_description": issue_dict.get("ucp_description") or _get_ucp_desc(ucp_ref),
                    "isbp_description": issue_dict.get("isbp_description") or _get_isbp_desc(isbp_ref),
                    "display_card": True,
                    "ruleset_domain": "icc.lcopilot.extraction",
                })
        
        # Add cross-doc issues (including AI validator issues)
        if v2_crossdoc_issues:
            for issue in v2_crossdoc_issues:
                issue_dict = issue.to_dict() if hasattr(issue, 'to_dict') else issue
                
                # Handle both CrossDocIssue and AIValidationIssue formats
                # CrossDocIssue uses: "rule", "ucp_article", "actual"
                # AIValidationIssue uses: "rule", "ucp_reference", "actual"
                ucp_ref = issue_dict.get("ucp_reference") or issue_dict.get("ucp_article") or ""
                isbp_ref = issue_dict.get("isbp_reference") or issue_dict.get("isbp_paragraph") or ""
                failed_results.append({
                    "rule": issue_dict.get("rule") or issue_dict.get("rule_id") or "CROSSDOC-ISSUE",
                    "title": issue_dict.get("title", "Cross-Document Issue"),
                    "passed": False,
                    "severity": issue_dict.get("severity", "major"),
                    "message": issue_dict.get("message", ""),
                    "expected": issue_dict.get("expected", ""),
                    "found": issue_dict.get("actual") or issue_dict.get("found") or "",
                    "suggested_fix": issue_dict.get("suggestion") or issue_dict.get("suggested_fix") or "",
                    "documents": issue_dict.get("documents") or issue_dict.get("document_names") or [issue_dict.get("source_doc", ""), issue_dict.get("target_doc", "")],
                    "ucp_reference": ucp_ref,
                    "isbp_reference": isbp_ref,
                    "ucp_description": issue_dict.get("ucp_description") or _get_ucp_desc(ucp_ref),
                    "isbp_description": issue_dict.get("isbp_description") or _get_isbp_desc(isbp_ref),
                    "display_card": True,
                    "ruleset_domain": issue_dict.get("ruleset_domain") or "icc.lcopilot.crossdoc",
                    "auto_generated": issue_dict.get("auto_generated", False),
                })
        
        # Add DB rule issues (2500+ rules from database)
        if db_rule_issues:
            for issue in db_rule_issues:
                issue_dict = issue if isinstance(issue, dict) else issue.to_dict() if hasattr(issue, 'to_dict') else {}
                ucp_ref = issue_dict.get("ucp_reference") or issue_dict.get("ucp_article") or ""
                isbp_ref = issue_dict.get("isbp_reference") or issue_dict.get("isbp_paragraph") or ""
                failed_results.append({
                    "rule": issue_dict.get("rule") or issue_dict.get("rule_id") or "DB-RULE",
                    "title": issue_dict.get("title", "Validation Rule"),
                    "passed": False,
                    "severity": issue_dict.get("severity", "major"),
                    "message": issue_dict.get("message", ""),
                    "expected": issue_dict.get("expected", ""),
                    "found": issue_dict.get("actual") or issue_dict.get("found") or "",
                    "suggested_fix": issue_dict.get("suggestion") or issue_dict.get("suggested_fix") or "",
                    "documents": issue_dict.get("documents") or [],
                    "ucp_reference": ucp_ref,
                    "isbp_reference": isbp_ref,
                    "ucp_description": issue_dict.get("ucp_description") or _get_ucp_desc(ucp_ref),
                    "isbp_description": issue_dict.get("isbp_description") or _get_isbp_desc(isbp_ref),
                    "display_card": True,
                    "ruleset_domain": issue_dict.get("ruleset_domain") or "icc.ucp600",
                })
            logger.info("Added %d DB rule issues to failed_results", len(db_rule_issues))
        
        # Add LC type unknown warning if applicable
        if lc_type_is_unknown:
            failed_results.append(
                {
                    "rule": "LC-TYPE-UNKNOWN",
                    "title": "LC Type Not Determined",
                    "passed": False,
                    "severity": "warning",
                    "message": (
                        "We could not determine whether this LC is an import or export workflow. "
                        "Advanced trade-specific checks were disabled for safety."
                    ),
                    "documents": ["Letter of Credit"],
                    "document_names": ["Letter of Credit"],
                    "display_card": True,
                    "ruleset_domain": "system.lc_type",
                    "not_applicable": False,
                }
            )
        
        # =====================================================================
        # DEDUPLICATION - Remove duplicate issues by rule ID
        # =====================================================================
        seen_rules = set()
        deduplicated_results = []
        for issue in failed_results:
            dedup_key = _build_issue_dedup_key(issue)
            if dedup_key not in seen_rules:
                seen_rules.add(dedup_key)
                deduplicated_results.append(issue)
            else:
                logger.debug(
                    "Removed duplicate issue: %s",
                    issue.get("rule") or issue.get("title") or dedup_key,
                )
        
        if len(failed_results) != len(deduplicated_results):
            logger.warning(
                "Deduplication removed %d duplicate issues",
                len(failed_results) - len(deduplicated_results)
            )
        
        if validation_session and current_user.is_bank_user() and current_user.company_id:
            try:
                policy_results = await apply_bank_policy(
                    validation_results=deduplicated_results,
                    bank_id=str(current_user.company_id),
                    document_data=payload,
                    db_session=db,
                    validation_session_id=str(validation_session.id),
                    user_id=str(current_user.id),
                )
                deduplicated_results = [
                    issue for issue in policy_results if not issue.get("passed", False)
                ]
            except Exception as e:
                logger.warning("Bank policy application skipped: %s", e)

        results = list(deduplicated_results)

        logger.info(
            "V2 Validation: total_issues=%d (extraction=%d crossdoc=%d db_rules=%d) after_dedup=%d",
            len(failed_results),
            len(v2_issues) if v2_issues else 0,
            len(v2_crossdoc_issues) if v2_crossdoc_issues else 0,
            len(db_rule_issues) if db_rule_issues else 0,
            len(deduplicated_results),
        )

        issue_cards, reference_issues = build_issue_cards(deduplicated_results)
        checkpoint("issue_cards_built")

        # Record usage - link to session if created (skip for demo user)
        quota = None
        company_size, tolerance_percent = _determine_company_size(current_user, payload)
        payload["company_profile"] = {
            "size": company_size,
            "invoice_amount_tolerance_percent": float(tolerance_percent),
        }
        tolerance_value, amount_limit = _compute_invoice_amount_bounds(payload, tolerance_percent)
        if tolerance_value is not None:
            payload["invoice_amount_tolerance_value"] = tolerance_value
        if amount_limit is not None:
            payload["invoice_amount_limit"] = amount_limit
        
        if current_user.email != "demo@trdrhub.com":
            entitlements = EntitlementService(db)
            quota = entitlements.record_usage(
                current_user.company,
                UsageAction.VALIDATE,
                user_id=current_user.id,
                cost=Decimal("0.00"),
                description=f"Validation request for document type {doc_type}",
                session_id=validation_session.id if validation_session else None,
            )

        document_details_for_summaries = payload.get("documents")
        logger.info(
            "Building document summaries: files_list=%d details=%d issues=%d",
            len(files_list) if files_list else 0,
            len(document_details_for_summaries) if document_details_for_summaries else 0,
            len(deduplicated_results) if deduplicated_results else 0,
        )
        # FIX: Use deduplicated_results (actual issues) instead of empty results list
        # This ensures document issue counts are correctly linked to each document
        document_summaries = _build_document_summaries(
            files_list,
            deduplicated_results,  # Was 'results' which was always empty!
            document_details_for_summaries,
        )
        if document_summaries:
            doc_status_counts: Dict[str, int] = {}
            for summary in document_summaries:
                doc_status_val = summary.get("status") or "unknown"
                doc_status_counts[doc_status_val] = doc_status_counts.get(doc_status_val, 0) + 1
            logger.info(
                "Document summaries built: total=%d status_breakdown=%s",
                len(document_summaries),
                doc_status_counts,
            )
        else:
            logger.warning(
                "Document summaries are empty: no documents captured for job %s", job_id
            )
        
        checkpoint("document_summaries_built")
        
        processing_duration = time.time() - start_time
        processing_summary = _build_processing_summary(
            document_summaries,
            processing_duration,
            len(deduplicated_results),
        )

        # Ensure document_summaries is a list (fallback to empty if malformed)
        final_documents = document_summaries if isinstance(document_summaries, list) else []
        
        # GUARANTEE: Always have non-empty documents for Option-E
        if not final_documents:
            logger.warning("final_documents empty - using files_list fallback")
            final_documents = _build_document_summaries(files_list, results, None)
        
        # Build extractor outputs from payload or extracted context
        extractor_outputs = payload.get("lc_structured_output") if payload else None
        if not extractor_outputs and payload:
            # Fallback: build from LC detection results
            extractor_outputs = {
                "lc_type": payload.get("lc_type", "unknown"),
                "lc_type_reason": payload.get("lc_type_reason", "Auto-detected"),
                "lc_type_confidence": payload.get("lc_type_confidence", 0),
                "lc_type_source": payload.get("lc_type_source", "auto"),
                "mt700": (payload.get("lc") or {}).get("mt700") or {"blocks": {}, "raw_text": None, "version": "mt700_v1"},
                "goods": (payload.get("lc") or {}).get("goods") or (payload.get("lc") or {}).get("goods_items") or [],
                "clauses": (payload.get("lc") or {}).get("clauses") or [],
                "timeline": [],
                "issues": [],
            }
        
        # Build Option-E structured result with proper error handling
        try:
            option_e_payload = build_unified_structured_result(
                session_documents=final_documents,
                extractor_outputs=extractor_outputs,
                legacy_payload=None,
            )
            structured_result = option_e_payload["structured_result"]
            checkpoint("structured_result_built")
        except Exception as e:
            import traceback
            logger.error(
                "Option-E builder failed in /api/validate: %s: %s",
                type(e).__name__,
                str(e),
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "traceback": traceback.format_exc(),
                    "job_id": str(job_id) if job_id else None,
                    "document_count": len(final_documents),
                },
                exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error_code": "option_e_builder_failed",
                    "message": f"{type(e).__name__}: {str(e)}"
                }
            )

        # Customs risk/pack computation (guarded - skip on error, don't crash endpoint)
        structured_result.setdefault("analytics", {})
        try:
            customs_risk = compute_customs_risk_from_option_e(structured_result)
            structured_result["analytics"]["customs_risk"] = customs_risk
        except Exception as e:
            logger.warning(
                "Customs risk computation skipped: %s: %s",
                type(e).__name__,
                str(e),
                exc_info=True
            )
            structured_result["analytics"]["customs_risk"] = None

        try:
            customs_pack = build_customs_manifest_from_option_e(structured_result)
            structured_result["customs_pack"] = customs_pack
        except Exception as e:
            logger.warning(
                "Customs pack build skipped: %s: %s",
                type(e).__name__,
                str(e),
                exc_info=True
            )
            structured_result["customs_pack"] = None

        _sync_structured_result_collections(structured_result)

        extraction_core_bundle = payload.get("_extraction_core_v1") if isinstance(payload, dict) else None
        if not isinstance(extraction_core_bundle, dict):
            extraction_core_bundle = (
                _build_extraction_core_bundle(payload.get("documents") or [])
                if isinstance(payload, dict)
                else None
            )
        if isinstance(extraction_core_bundle, dict):
            structured_result["_extraction_core_v1"] = extraction_core_bundle

        try:
            _response_shaping.attach_extraction_observability(document_summaries)
            _response_shaping.attach_extraction_observability(
                structured_result.get("documents") if isinstance(structured_result.get("documents"), list) else []
            )
            _response_shaping.attach_extraction_observability(
                structured_result.get("documents_structured")
                if isinstance(structured_result.get("documents_structured"), list)
                else []
            )
            _sync_structured_result_collections(structured_result)
            extraction_diagnostics = _response_shaping.build_extraction_diagnostics(
                structured_result.get("documents")
                if isinstance(structured_result.get("documents"), list)
                else structured_result.get("documents_structured")
                if isinstance(structured_result.get("documents_structured"), list)
                else document_summaries,
                extraction_core_bundle if isinstance(extraction_core_bundle, dict) else None,
            )
            if isinstance(extraction_diagnostics, dict):
                structured_result["_extraction_diagnostics"] = extraction_diagnostics
        except Exception as exc:
            logger.warning("Extraction diagnostics shaping skipped: %s", exc, exc_info=True)

        # Merge actual processing_summary values into structured_result
        # This ensures processing_time_display and other fields are populated
        # FIX: Merge ALL fields including status counts, verified, warnings, etc.
        if structured_result.get("processing_summary") and processing_summary:
            structured_result["processing_summary"].update({
                # Timing fields
                "processing_time_seconds": processing_summary.get("processing_time_seconds"),
                "processing_time_display": processing_summary.get("processing_time_display"),
                "processing_time_ms": processing_summary.get("processing_time_ms"),
                "extraction_quality": processing_summary.get("extraction_quality"),
                # Status counts - CRITICAL for frontend display
                "verified": processing_summary.get("verified", 0),
                "warnings": processing_summary.get("warnings", 0),
                "errors": processing_summary.get("errors", 0),
                "successful_extractions": processing_summary.get("verified", 0),
                "failed_extractions": processing_summary.get("errors", 0),
                # Status distribution for SummaryStrip
                "status_counts": processing_summary.get("status_counts", {}),
                "document_status": processing_summary.get("document_status", {}),
                # Compliance (will be overwritten by v2 scorer later, but set baseline)
                "compliance_rate": processing_summary.get("compliance_rate", 0),
                "discrepancies": processing_summary.get("discrepancies", 0),
            })
        # Also update analytics with processing time
        if structured_result.get("analytics"):
            structured_result["analytics"]["processing_time_display"] = processing_summary.get("processing_time_display")
        
        # =====================================================================
        # DOCUMENT SET COMPOSITION ANALYTICS
        # Track document types, missing docs, and completeness per UCP600 norms
        # =====================================================================
        try:
            from app.services.validation.crossdoc_validator import validate_document_set_completeness
            
            # Document type normalizer - handles aliases like "lc" -> "letter_of_credit"
            def normalize_document_type(doc_type: str) -> str:
                """Normalize document type to canonical form."""
                if not doc_type:
                    return "unknown"
                normalized = doc_type.lower().strip().replace("-", "_").replace(" ", "_")
                
                # Alias mapping
                aliases = {
                    "lc": "letter_of_credit",
                    "l/c": "letter_of_credit",
                    "mt700": "letter_of_credit",
                    "mt760": "letter_of_credit",
                    "invoice": "commercial_invoice",
                    "bl": "bill_of_lading",
                    "b/l": "bill_of_lading",
                    "bol": "bill_of_lading",
                    "coo": "certificate_of_origin",
                    "co": "certificate_of_origin",
                    "pl": "packing_list",
                    "insurance": "insurance_certificate",
                    "inspection": "inspection_certificate",
                }
                return aliases.get(normalized, normalized)

            # Build document list for composition analysis
            doc_list_for_composition = []
            detected_types_debug = []
            for doc in (
                structured_result.get("documents")
                or structured_result.get("documents_structured")
                or []
            ):
                raw_type = doc.get("documentType", doc.get("type", doc.get("document_type", "supporting_document")))
                # Normalize using shared document types (handles ALL aliases)
                normalized_type = normalize_document_type(raw_type)
                detected_types_debug.append(f"{raw_type} -> {normalized_type}")
                doc_list_for_composition.append({
                    "document_type": normalized_type,
                    "filename": doc.get("name", doc.get("filename", "unknown")),
                })
            
            logger.info(f"Document composition analysis: {detected_types_debug}")

            # Extract LC terms for requirement detection
            lc_terms = structured_result.get("lc_data", {})
            
            # Check if LC is already confirmed present (from earlier checks or extraction)
            # This prevents duplicate "Missing LC" issues
            lc_types = {"letter_of_credit", "swift_message", "lc_application"}
            lc_confirmed = (
                any(d["document_type"] in lc_types for d in doc_list_for_composition) or
                bool(structured_result.get("lc_data", {}).get("lc_number")) or
                bool(structured_result.get("lc_structured"))
            )
            
            if lc_confirmed:
                logger.info("LC document confirmed present - will skip 'Missing LC' check in composition validator")

            # Validate document set completeness
            composition_result = validate_document_set_completeness(
                documents=doc_list_for_composition,
                lc_terms=lc_terms,
                skip_lc_check=lc_confirmed,  # Skip if LC already confirmed
            )
            
            # Add composition to analytics
            if structured_result.get("analytics"):
                structured_result["analytics"]["document_composition"] = composition_result.get("composition", {})
                structured_result["analytics"]["lc_only_mode"] = composition_result.get("composition", {}).get("lc_only_mode", False)
            
            # Add composition issues to the issues list (informational warnings)
            composition_issues = composition_result.get("issues", [])
            if composition_issues:
                existing_issues = structured_result.get("issues") or []
                structured_result["issues"] = existing_issues + composition_issues
                logger.info(f"Added {len(composition_issues)} document composition warnings")
                
        except Exception as comp_error:
            logger.warning(f"Document composition analytics failed: {comp_error}")

        # =====================================================================
        # MERGE ISSUE CARDS INTO STRUCTURED RESULT
        # issue_cards were built from failed_results at line 603 but need to be
        # added to structured_result for the frontend to display them
        # =====================================================================
        if issue_cards:
            existing_issues = structured_result.get("issues") or []
            # Convert issue_cards to dict format if they're not already
            formatted_issues = []
            for card in issue_cards:
                if isinstance(card, dict):
                    formatted_issues.append(card)
                elif hasattr(card, 'to_dict'):
                    formatted_issues.append(card.to_dict())
                elif hasattr(card, '__dict__'):
                    formatted_issues.append(card.__dict__)
                else:
                    formatted_issues.append({"title": str(card), "severity": "minor"})
            
            # Merge with any existing issues (from crossdoc, etc.)
            structured_result["issues"] = existing_issues + formatted_issues
            logger.info("Added %d issue cards to structured_result (total issues: %d)", 
                       len(formatted_issues), len(structured_result["issues"]))
        
        # NOTE: v2_crossdoc_issues are already included in issue_cards via failed_results
        # Do NOT add them again here - that was causing DUPLICATE issues!

        # =====================================================================
        # SANCTIONS SCREENING - Auto-screen LC parties
        # Screen applicant, beneficiary, banks, and other parties
        # =====================================================================
        checkpoint("pre_sanctions_screening")
        
        sanctions_summary = None
        sanctions_should_block = False
        
        try:
            current_issues = structured_result.get("issues") or []
            
            updated_issues, sanctions_should_block, sanctions_summary = await run_sanctions_screening_for_validation(
                payload=payload,
                existing_issues=current_issues,
            )
            
            # Update issues with sanctions results
            structured_result["issues"] = updated_issues
            
            # Add sanctions summary to result
            structured_result["sanctions_screening"] = sanctions_summary
            
            if sanctions_should_block:
                logger.warning(
                    "SANCTIONS MATCH DETECTED - LC processing should be blocked. "
                    f"Summary: {sanctions_summary}"
                )
                # Add sanctions blocked flag
                structured_result["sanctions_blocked"] = True
                structured_result["sanctions_block_reason"] = (
                    f"{sanctions_summary.get('matches', 0)} sanctioned party match(es) found. "
                    "LC processing halted pending compliance review."
                )
            else:
                structured_result["sanctions_blocked"] = False
                
            if sanctions_summary:
                logger.info(
                    "Sanctions screening complete: %d parties screened, %d matches, %d potential matches",
                    sanctions_summary.get("parties_screened", 0),
                    sanctions_summary.get("matches", 0),
                    sanctions_summary.get("potential_matches", 0),
                )
                
        except Exception as e:
            logger.error(f"Sanctions screening failed: {e}", exc_info=True)
            # Don't block on screening errors - log and continue
            structured_result["sanctions_screening"] = {
                "screened": False,
                "error": str(e),
            }
        checkpoint("post_sanctions_screening")

        # =====================================================================
        # V2 VALIDATION PIPELINE - FINAL SCORING
        # Apply v2 compliance scoring and add structured metadata
        # =====================================================================
        try:
            # Always add v2 fields (gate passed at this point)
            structured_result["validation_blocked"] = False
            structured_result["validation_status"] = "processing"

            field_decisions = _extract_field_decisions_from_payload(payload)
            _augment_issues_with_field_decisions(structured_result.get("issues") or [], field_decisions)
            _augment_doc_field_details_with_decisions(payload.get("documents") or [])
            
            if v2_gate_result is not None:
                # Add gate result
                structured_result["gate_result"] = v2_gate_result.to_dict()
                
                # Add extraction summary
                structured_result["extraction_summary"] = {
                    "completeness": round(v2_gate_result.completeness * 100, 1),
                    "critical_completeness": round(v2_gate_result.critical_completeness * 100, 1),
                    "missing_critical": v2_gate_result.missing_critical,
                    "missing_required": v2_gate_result.missing_required,
                }
            
            # Add LC baseline to structured result
            if v2_baseline:
                structured_result["lc_baseline"] = {
                    "lc_number": v2_baseline.lc_number.value,
                    "amount": v2_baseline.amount.value,
                    "currency": v2_baseline.currency.value,
                    "applicant": v2_baseline.applicant.value,
                    "beneficiary": v2_baseline.beneficiary.value,
                    "expiry_date": v2_baseline.expiry_date.value,
                    "latest_shipment": v2_baseline.latest_shipment.value,
                    "port_of_loading": v2_baseline.port_of_loading.value,
                    "port_of_discharge": v2_baseline.port_of_discharge.value,
                    "goods_description": v2_baseline.goods_description.value,
                    "incoterm": v2_baseline.incoterm.value,
                    "extraction_completeness": round(v2_baseline.extraction_completeness * 100, 1),
                    "critical_completeness": round(v2_baseline.critical_completeness * 100, 1),
                }
            
            # Calculate v2 compliance score
            v2_scorer = ComplianceScorer()
            all_issues = structured_result.get("issues") or []
            
            # Calculate compliance with v2 scorer
            extraction_completeness = v2_gate_result.completeness if v2_gate_result else 1.0
            v2_score = v2_scorer.calculate_from_issues(
                all_issues,
                extraction_completeness=extraction_completeness,
            )
            
            # Update validation status based on score
            structured_result["validation_status"] = v2_score.level.value
            
            # Override compliance rate with v2 calculation
            if structured_result.get("analytics"):
                compliance_pct = int(round(v2_score.score))
                structured_result["analytics"]["lc_compliance_score"] = compliance_pct
                structured_result["analytics"]["compliance_score"] = compliance_pct  # Frontend alias
                structured_result["analytics"]["compliance_level"] = v2_score.level.value
                structured_result["analytics"]["compliance_cap_reason"] = v2_score.cap_reason
                structured_result["analytics"]["issue_counts"] = {
                    "critical": v2_score.critical_count,
                    "major": v2_score.major_count,
                    "minor": v2_score.minor_count,
                }
            
            if structured_result.get("processing_summary"):
                structured_result["processing_summary"]["compliance_rate"] = int(round(v2_score.score))
                structured_result["processing_summary"]["severity_breakdown"] = {
                    "critical": v2_score.critical_count,
                    "major": v2_score.major_count,
                    "medium": 0,
                    "minor": v2_score.minor_count,
                }
            
            logger.info(
                "V2 compliance scoring: score=%.1f%% level=%s issues=%d (critical=%d major=%d minor=%d)",
                v2_score.score,
                v2_score.level.value,
                len(all_issues),
                v2_score.critical_count,
                v2_score.major_count,
                v2_score.minor_count,
            )
            
            # =====================================================================
            # BANK SUBMISSION VERDICT
            # =====================================================================
            bank_verdict = _build_bank_submission_verdict(
                critical_count=v2_score.critical_count,
                major_count=v2_score.major_count,
                minor_count=v2_score.minor_count,
                compliance_score=v2_score.score,
                all_issues=all_issues,
            )
            structured_result["bank_verdict"] = bank_verdict
            
            if structured_result.get("processing_summary"):
                structured_result["processing_summary"]["bank_verdict"] = bank_verdict.get("verdict")
            
            logger.info(
                "Bank verdict: %s (action_required=%d)",
                bank_verdict.get("verdict"),
                len(bank_verdict.get("action_items", [])),
            )

            submission_reasons = []
            submission_can_submit = True
            if structured_result.get("validation_blocked"):
                submission_can_submit = False
                submission_reasons.append("validation_blocked")
            if not bank_verdict:
                submission_can_submit = False
                submission_reasons.append("bank_verdict_missing")
            elif not bank_verdict.get("can_submit", False):
                submission_can_submit = False
                submission_reasons.append(
                    f"bank_verdict_{str(bank_verdict.get('verdict', 'unknown')).lower()}"
                )

            eligibility_context = _build_submission_eligibility_context(
                structured_result.get("gate_result") or {},
                field_decisions,
            )

            structured_result["submission_eligibility"] = {
                "can_submit": submission_can_submit,
                "reasons": submission_reasons,
                "missing_reason_codes": eligibility_context["missing_reason_codes"],
                "unresolved_critical_fields": eligibility_context["unresolved_critical_fields"],
                "unresolved_critical_statuses": eligibility_context["unresolved_critical_statuses"],
                "source": "validation",
            }
            
            # =====================================================================
            # AMENDMENT GENERATION (for fixable discrepancies)
            # =====================================================================
            try:
                lc_number = (
                    lc_context.get("lc_number") or
                    mt700.get("20") or
                    extracted_context.get("lc", {}).get("lc_number") or
                    "UNKNOWN"
                )
                lc_amount = lc_context.get("amount") or mt700.get("32B_amount") or 0
                lc_currency = lc_context.get("currency") or mt700.get("32B_currency") or "USD"
                
                amendments = generate_amendments_for_issues(
                    issues=all_issues,
                    lc_data={
                        "lc_number": lc_number,
                        "amount": lc_amount,
                        "currency": lc_currency,
                    }
                )
                
                if amendments:
                    amendment_cost = calculate_total_amendment_cost(amendments)
                    structured_result["amendments_available"] = {
                        "count": len(amendments),
                        "total_estimated_fee_usd": amendment_cost.get("total_estimated_fee_usd", 0),
                        "amendments": [a.to_dict() for a in amendments],
                    }
                    logger.info(f"Generated {len(amendments)} amendment drafts")
            except Exception as e:
                logger.warning(f"Amendment generation failed: {e}")
            
            # =====================================================================
            # CONFIDENCE WEIGHTING (adjust severity based on OCR confidence)
            # =====================================================================
            try:
                if extraction_confidence_summary:
                    structured_result["extraction_confidence"] = extraction_confidence_summary
                    
                    # Add recommendations if low confidence
                    if extraction_confidence_summary.get("average_confidence", 1.0) < 0.6:
                        existing_recommendations = bank_verdict.get("action_items", [])
                        for rec in extraction_confidence_summary.get("recommendations", []):
                            existing_recommendations.append({
                                "priority": "medium",
                                "issue": "Low OCR Confidence",
                                "action": rec,
                            })
            except Exception as e:
                logger.warning(f"Confidence metadata failed: {e}")
            
            # =====================================================================
            # BANK PROFILE METADATA
            # =====================================================================
            if bank_profile:
                structured_result["bank_profile"] = {
                    "bank_code": bank_profile.bank_code,
                    "bank_name": bank_profile.bank_name,
                    "strictness": bank_profile.strictness.value,
                }
            
            # =====================================================================
            # TOLERANCE METADATA (for audit trail)
            # =====================================================================
            if requirement_graph and requirement_graph.tolerances:
                structured_result["tolerances_applied"] = {
                    k: {
                        "tolerance_percent": v.tolerance_percent,
                        "source": v.source.value,
                        "explicit": v.explicit,
                    }
                    for k, v in requirement_graph.tolerances.items()
                }
            
        except Exception as e:
            logger.warning("V2 scoring failed: %s", e, exc_info=True)
        # =====================================================================

        checkpoint("response_building")

        # =====================================================================
        # Phase A Contracts: Canonical metrics + provenance payloads
        # =====================================================================
        try:
            processing_summary_v2 = _build_processing_summary_v2(
                structured_result.get("processing_summary"),
                document_summaries,
                structured_result.get("issues") or [],
                compliance_rate=structured_result.get("analytics", {}).get("lc_compliance_score")
                if isinstance(structured_result.get("analytics"), dict)
                else None,
            )
            structured_result["processing_summary_v2"] = processing_summary_v2

            structured_result["document_extraction_v1"] = _build_document_extraction_v1(
                document_summaries
            )
            issue_provenance_input: List[Dict[str, Any]] = []
            if isinstance(deduplicated_results, list) and deduplicated_results:
                issue_provenance_input.extend(deduplicated_results)

            existing_keys = {
                str(item.get("id") or item.get("rule") or item.get("rule_id"))
                for item in issue_provenance_input
                if isinstance(item, dict)
            }

            for issue in structured_result.get("issues") or []:
                if not isinstance(issue, dict):
                    continue
                key = str(issue.get("id") or issue.get("rule") or issue.get("rule_id"))
                if key and key in existing_keys:
                    continue
                issue_provenance_input.append(issue)

            if not issue_provenance_input:
                issue_provenance_input = structured_result.get("issues") or []

            structured_result["issue_provenance_v1"] = _build_issue_provenance_v1(
                issue_provenance_input
            )

            # Backfill legacy processing_summary with canonical metrics (backward compatible)
            structured_result.setdefault("processing_summary", {})
            structured_result["processing_summary"].update(
                {
                    "total_documents": processing_summary_v2.get("total_documents"),
                    "successful_extractions": processing_summary_v2.get("successful_extractions"),
                    "failed_extractions": processing_summary_v2.get("failed_extractions"),
                    "total_issues": processing_summary_v2.get("total_issues"),
                    "severity_breakdown": processing_summary_v2.get("severity_breakdown"),
                    "documents": processing_summary_v2.get("documents"),
                    "documents_found": processing_summary_v2.get("documents_found"),
                    "verified": processing_summary_v2.get("verified"),
                    "warnings": processing_summary_v2.get("warnings"),
                    "errors": processing_summary_v2.get("errors"),
                    "status_counts": processing_summary_v2.get("status_counts"),
                    "document_status": processing_summary_v2.get("document_status"),
                    "compliance_rate": processing_summary_v2.get("compliance_rate"),
                    "processing_time_seconds": processing_summary_v2.get("processing_time_seconds"),
                    "processing_time_display": processing_summary_v2.get("processing_time_display"),
                    "processing_time_ms": processing_summary_v2.get("processing_time_ms"),
                    "extraction_quality": processing_summary_v2.get("extraction_quality"),
                    "discrepancies": processing_summary_v2.get("discrepancies"),
                }
            )

            structured_result.setdefault("analytics", {})
            structured_result["analytics"]["issue_counts"] = _count_issue_severity(
                structured_result.get("issues") or []
            )
            structured_result["analytics"]["document_status_distribution"] = (
                processing_summary_v2.get("status_counts")
            )

            customs_pack = structured_result.get("customs_pack")
            if isinstance(customs_pack, dict):
                manifest = customs_pack.get("manifest") or []
                manifest_count = len(manifest) if isinstance(manifest, list) else 0
                customs_pack["manifest_count"] = manifest_count
                customs_pack["ready"] = bool(manifest_count)
                if manifest_count == 0:
                    structured_result["analytics"]["customs_ready_score"] = 0

            bank_verdict = structured_result.get("bank_verdict") or {}
            validation_blocked = structured_result.get("validation_blocked", False)
            submission_reasons = []
            can_submit = True
            if validation_blocked:
                can_submit = False
                submission_reasons.append("validation_blocked")
            if not bank_verdict:
                can_submit = False
                submission_reasons.append("bank_verdict_missing")
            elif not bank_verdict.get("can_submit", False):
                can_submit = False
                submission_reasons.append(
                    f"bank_verdict_{str(bank_verdict.get('verdict', 'unknown')).lower()}"
                )

            eligibility_context = _build_submission_eligibility_context(
                structured_result.get("gate_result") or {},
                field_decisions,
            )

            structured_result["submission_eligibility"] = {
                "can_submit": can_submit,
                "reasons": submission_reasons,
                "missing_reason_codes": eligibility_context["missing_reason_codes"],
                "unresolved_critical_fields": eligibility_context["unresolved_critical_fields"],
                "unresolved_critical_statuses": eligibility_context["unresolved_critical_statuses"],
                "source": "validation",
            }
        except Exception as contract_err:
            logger.warning("Failed to build Phase A contracts: %s", contract_err, exc_info=True)
        
        telemetry_payload = {
            "UnifiedStructuredResultBuilt": True,
            "documents": len(structured_result.get("documents_structured", [])),
            "issues": len(structured_result.get("issues", [])),
            # Timing breakdown for performance analysis
            "timings": timings,
            "total_time_seconds": round(time.time() - start_time, 3),
        }

        if validation_session:
            validation_session.validation_results = {"structured_result": structured_result}
            validation_session.status = SessionStatus.COMPLETED.value
            validation_session.processing_completed_at = func.now()
            db.commit()
            db.refresh(validation_session)
        else:
            db.commit()

        if request_user_type == "bank" and validation_session:
            duration_ms = int((time.time() - start_time) * 1000)
            metadata_dict = payload.get("metadata") or {}
            if isinstance(metadata_dict, str):
                try:
                    metadata_dict = json.loads(metadata_dict)
                except Exception:
                    metadata_dict = {}
            audit_service.log_action(
                action=AuditAction.UPLOAD,
                user=current_user,
                correlation_id=audit_context['correlation_id'],
                resource_type="bank_validation",
                resource_id=str(validation_session.id),
                lc_number=metadata_dict.get("lcNumber") or metadata_dict.get("lc_number"),
                ip_address=audit_context['ip_address'],
                user_agent=audit_context['user_agent'],
                endpoint=audit_context['endpoint'],
                http_method=audit_context['http_method'],
                result=AuditResult.SUCCESS,
                duration_ms=duration_ms,
                audit_metadata={
                    "client_name": metadata_dict.get("clientName") or metadata_dict.get("client_name"),
                    "date_received": metadata_dict.get("dateReceived") or metadata_dict.get("date_received"),
                    "discrepancy_count": len(failed_results),
                    "document_count": len(payload.get("files", [])) if isinstance(payload.get("files"), list) else 0,
                },
            )

        logger.info(
            "Validation completed",
            extra={
                "job_id": str(job_id),
                "user_type": request_user_type or (current_user.role.value if hasattr(current_user, "role") else "unknown"),
                "rules_evaluated": len(results),
                "failed_rules": len(failed_results),
                "issue_cards": len(issue_cards),
                "json_pipeline": True,
            },
        )

        # Track usage for billing
        if current_user and hasattr(current_user, 'company_id') and current_user.company_id:
            try:
                doc_count = len(payload.get("files", [])) if isinstance(payload.get("files"), list) else len(files_list)
                await record_usage_manual(
                    db=db,
                    company_id=current_user.company_id,
                    user_id=current_user.id if hasattr(current_user, 'id') else None,
                    operation="lc_validation",
                    tool="lcopilot",
                    quantity=1,  # One validation session
                    log_data={
                        "job_id": str(job_id),
                        "document_count": doc_count,
                        "rules_evaluated": len(results),
                        "discrepancies": len(failed_results),
                    },
                    description=f"LC validation: {doc_count} documents, {len(failed_results)} issues"
                )
            except Exception as usage_err:
                logger.warning(f"Failed to track usage: {usage_err}")

        # =====================================================================
        # CONTRACT VALIDATION (Output-First Layer)
        # Validates response completeness and adds warnings for missing data
        # =====================================================================
        try:
            structured_result = validate_and_annotate_response(structured_result)
            structured_result = enforce_day1_response_contract(structured_result)
            if structured_result.get("_contract_warnings"):
                logger.info(
                    "Contract validation: %d warnings added to response",
                    len(structured_result.get("_contract_warnings", []))
                )
            day1_contract = structured_result.get("_day1_contract") if isinstance(structured_result, dict) else None
            if isinstance(day1_contract, dict):
                logger.info(
                    "Day1 response contract: status=%s docs=%s violations=%s",
                    day1_contract.get("status"),
                    day1_contract.get("documents_checked"),
                    len(day1_contract.get("violations") or []),
                )
            day1_metrics = structured_result.get("_day1_metrics") if isinstance(structured_result, dict) else None
            if isinstance(day1_metrics, dict):
                logger.info(
                    "Day1 telemetry counters: docs=%s RET_NO_HIT=%s RET_LOW_RELEVANCE=%s",
                    day1_metrics.get("documents_total"),
                    day1_metrics.get("ret_no_hit"),
                    day1_metrics.get("ret_low_relevance"),
                )
        except Exception as contract_err:
            logger.warning(f"Contract validation failed (non-blocking): {contract_err}")

        # Add DB rules debug info to response
        structured_result["_db_rules_debug"] = db_rules_debug

        return {
            "job_id": str(job_id),
            "jobId": str(job_id),
            "structured_result": structured_result,
            "telemetry": telemetry_payload,
        }
    except HTTPException:
        raise
    except UnicodeDecodeError as e:
        # Handle encoding errors specifically
        import logging
        logging.getLogger(__name__).error(f"Encoding error during file upload: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File encoding error: Unable to process uploaded file. Please ensure files are valid PDFs or images. Error: {str(e)}"
        )
    except Exception as e:
        # Log the full error with stack trace
        import traceback
        error_traceback = traceback.format_exc()
        logger.error(
            f"Validation endpoint exception: {type(e).__name__}: {str(e)}",
            extra={
                "error_type": type(e).__name__,
                "error_message": str(e),
                "user_id": current_user.id if current_user else None,
                "endpoint": "/api/validate",
                "traceback": error_traceback,
            },
            exc_info=True
        )
        
        # Log failed validation if bank operation
        user_type = payload.get("userType") or payload.get("user_type") if 'payload' in locals() else None
        if user_type == "bank" and 'validation_session' in locals() and validation_session:
            duration_ms = int((time.time() - start_time) * 1000)
            audit_service.log_action(
                action=AuditAction.UPLOAD,
                user=current_user,
                correlation_id=audit_context['correlation_id'],
                resource_type="bank_validation",
                resource_id=str(validation_session.id) if validation_session else "unknown",
                ip_address=audit_context['ip_address'],
                user_agent=audit_context['user_agent'],
                endpoint=audit_context['endpoint'],
                http_method=audit_context['http_method'],
                result=AuditResult.ERROR,
                duration_ms=duration_ms,
                error_message=str(e),
            )
        raise


def _is_populated_field_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) > 0
    return True


def _assess_required_field_completeness(
    extracted_fields: Optional[Dict[str, Any]],
    required_fields: List[str],
) -> Dict[str, Any]:
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
    """Compute parse completeness signal for COO extraction quality gating."""
    required_fields = [
        "certificate_number",
        "country_of_origin",
        "exporter_name",
        "importer_name",
        "goods_description",
        "certifying_authority",
    ]
    metrics = _assess_required_field_completeness(extracted_fields, required_fields)

    # COO must at least include country + certificate and a minimally useful set of required fields.
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


def _build_document_summaries(
    files_list: List[Any],
    results: List[Dict[str, Any]],
    document_details: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Create lightweight document summaries for downstream consumers."""
    details = document_details or []
    issue_by_name, issue_by_type, issue_by_id = _collect_document_issue_stats(results)

    def _derive_document_status(
        extraction_status: Optional[str],
        max_severity: Optional[str],
        parse_complete: Optional[bool] = None,
    ) -> str:
        extraction = (extraction_status or "").lower()
        if extraction in {"error", "failed", "empty"}:
            return "error"
        severity_status = _severity_to_status(max_severity)
        if severity_status in {"error", "warning"}:
            return severity_status
        if extraction in {"partial", "pending", "text_only", "parse_failed"}:
            return "warning"
        if parse_complete is False:
            return "warning"
        return "success"

    def _build_summary_from_detail(detail: Dict[str, Any], index: int) -> Dict[str, Any]:
        filename = detail.get("filename") or detail.get("name")
        doc_type = detail.get("document_type") or _infer_document_type_from_name(filename, index)
        # FIX: Normalize doc_type to canonical form (e.g., "Bill of Lading" -> "bill_of_lading")
        # This ensures it matches the keys in issue_by_type
        normalized_type = _normalize_doc_type_key(doc_type) or doc_type or "supporting_document"
        detail_id = detail.get("id") or str(uuid4())
        stats = _resolve_issue_stats(
            detail_id,
            filename,
            normalized_type,
            issue_by_name,
            issue_by_type,
            issue_by_id,
        )
        parse_complete_flag = detail.get("parse_complete")
        if parse_complete_flag is None:
            parse_complete_flag = detail.get("parseComplete")
        if parse_complete_flag is not None:
            parse_complete_flag = bool(parse_complete_flag)

        status = _derive_document_status(
            detail.get("extraction_status"),
            stats.get("max_severity") if stats else None,
            parse_complete=parse_complete_flag,
        )
        discrepancy_count = stats.get("count", 0) if stats else 0

        return {
            "id": detail_id,
            "name": filename or f"Document {index + 1}",
            "type": _humanize_doc_type(normalized_type),
            "documentType": normalized_type,
            "status": status,
            "discrepancyCount": discrepancy_count,
            "extractedFields": _filter_user_facing_fields(detail.get("extracted_fields") or {}),
            "ocrConfidence": detail.get("ocr_confidence"),
            "extractionStatus": detail.get("extraction_status"),
            "parse_complete": parse_complete_flag,
            "parseComplete": parse_complete_flag,
            "parse_completeness": detail.get("parse_completeness"),
            "parseCompleteness": detail.get("parse_completeness"),
            "missing_required_fields": detail.get("missing_required_fields") or [],
            "required_fields_found": detail.get("required_fields_found"),
            "required_fields_total": detail.get("required_fields_total"),
            "review_required": bool(detail.get("review_required") or detail.get("reviewRequired")),
            "reviewRequired": bool(detail.get("review_required") or detail.get("reviewRequired")),
            "review_reasons": detail.get("review_reasons") or detail.get("reviewReasons") or [],
            "reviewReasons": detail.get("review_reasons") or detail.get("reviewReasons") or [],
            "critical_field_states": detail.get("critical_field_states") or detail.get("criticalFieldStates") or {},
            "criticalFieldStates": detail.get("critical_field_states") or detail.get("criticalFieldStates") or {},
            "extraction_artifacts_v1": detail.get("extraction_artifacts_v1") or _empty_extraction_artifacts_v1(
                raw_text=detail.get("raw_text") or detail.get("raw_text_preview") or "",
                ocr_confidence=detail.get("ocr_confidence"),
            ),
        }

    if details:
        logger.info(
            "Building document summaries from details: %d documents found",
            len(details),
        )
        return [_build_summary_from_detail(detail, index) for index, detail in enumerate(details)]

    if not files_list:
        # GUARANTEE: Never return empty - create a placeholder document if nothing available
        logger.warning("No document details or files_list available - creating placeholder document")
        return [
            {
                "id": str(uuid4()),
                "name": "No documents uploaded",
                "type": "Supporting Document",
                "documentType": "supporting_document",
                "status": "warning",
                "discrepancyCount": 0,
                "extractedFields": {},
                "ocrConfidence": None,
                "extractionStatus": "unknown",
                "extraction_artifacts_v1": _empty_extraction_artifacts_v1(),
            }
        ]

    summaries: List[Dict[str, Any]] = []
    for index, file_obj in enumerate(files_list):
        filename = getattr(file_obj, "filename", None)
        inferred_type = _infer_document_type_from_name(filename, index)
        stats = _resolve_issue_stats(
            None,
            filename,
            inferred_type,
            issue_by_name,
            issue_by_type,
            issue_by_id,
        )
        doc_status = _derive_document_status(None, stats.get("max_severity") if stats else None)
        discrepancy_count = stats.get("count", 0) if stats else 0
        summaries.append(
            {
                "id": str(uuid4()),
                "name": filename or f"Document {index + 1}",
                "type": _humanize_doc_type(inferred_type),
                "documentType": inferred_type,
                "status": doc_status,
                "discrepancyCount": discrepancy_count,
                "extractedFields": {},
                "ocrConfidence": None,
                "extractionStatus": "unknown",
                "extraction_artifacts_v1": _empty_extraction_artifacts_v1(),
            }
        )

    # GUARANTEE: Never return empty list
    if not summaries:
        logger.warning("Document summaries still empty after processing - adding placeholder")
        summaries.append({
            "id": str(uuid4()),
            "name": "Document",
            "type": "Supporting Document",
            "documentType": "supporting_document",
            "status": "warning",
            "discrepancyCount": 0,
            "extractedFields": {},
            "ocrConfidence": None,
            "extractionStatus": "unknown",
            "extraction_artifacts_v1": _empty_extraction_artifacts_v1(),
        })

    return summaries


async def _build_document_context(
    files_list: List[Any],
    document_tags: Optional[Dict[str, Any]] = None,
    job_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Attempt to extract basic structured fields from uploaded documents.

    Returns a dictionary that can be merged into the validation payload (e.g. {"lc": {...}}).
    Also stores raw_text and sets extraction_status.
    """
    if not files_list:
        logger.debug("No files provided for extraction")
        return {"extraction_status": "empty"}

    try:
        from app.rules.extractors import DocumentFieldExtractor, ISO20022ParseError, extract_iso20022_lc
        from app.rules.models import DocumentType
        from app.services.extraction.lc_extractor import extract_lc_structured as extract_lc
    except ImportError as e:
        logger.warning(f"DocumentFieldExtractor not available; skipping text extraction: {e}")
        return {"extraction_status": "error", "extraction_error": str(e)}

    extractor = DocumentFieldExtractor()
    normalized_tags: Dict[str, str] = {}
    if isinstance(document_tags, dict):
        for raw_name, raw_value in document_tags.items():
            if not raw_name:
                continue
            canonical = _canonical_document_tag(str(raw_value)) if raw_value else None
            if canonical:
                normalized_tags[raw_name.lower()] = canonical
                # Also index by filename without extension for convenience
                base_name = raw_name.rsplit(".", 1)[0].lower()
                normalized_tags.setdefault(base_name, canonical)

    context: Dict[str, Any] = {}
    document_details: List[Dict[str, Any]] = []
    debug_extraction_trace: List[Dict[str, Any]] = []
    has_structured_data = False
    known_doc_types = {
        "letter_of_credit",
        "swift_message",
        "lc_application",
        "proforma_invoice",
        "commercial_invoice",
        "bill_of_lading",
        "packing_list",
        "insurance_certificate",
        "certificate_of_origin",
        "inspection_certificate",
        "supporting_document",
    }
    documents_presence: Dict[str, Dict[str, Any]] = {
        doc_type: {"present": False, "count": 0} for doc_type in known_doc_types
    }

    # ═══════════════════════════════════════════════════════════════════════════
    # PARALLEL OCR EXTRACTION - Process all files concurrently for better performance
    # This significantly speeds up 10-12 document batches (from ~6min to ~2min)
    # ═══════════════════════════════════════════════════════════════════════════
    ocr_concurrency = max(1, int(os.getenv("OCR_MAX_CONCURRENCY", str(settings.OCR_MAX_CONCURRENCY))))
    ocr_semaphore = asyncio.Semaphore(ocr_concurrency)
    
    async def _extract_with_semaphore(idx: int, upload_file) -> tuple:
        """Extract text with concurrency limit."""
        async with ocr_semaphore:
            filename = getattr(upload_file, "filename", f"document_{idx+1}")
            document_type = _resolve_document_type(filename, idx, normalized_tags)
            logger.info(f"[OCR {idx+1}/{len(files_list)}] Starting extraction for {filename}")
            try:
                extraction_result = await _extract_text_from_upload(upload_file, document_type=document_type)
                text = extraction_result.get("text") or ""
                artifacts = extraction_result.get("artifacts") or _empty_extraction_artifacts_v1(raw_text=text)
                logger.info(f"[OCR {idx+1}/{len(files_list)}] Completed {filename}: {len(text) if text else 0} chars")
                return (idx, text, artifacts, None)
            except Exception as e:
                logger.warning(f"[OCR {idx+1}/{len(files_list)}] Failed {filename}: {e}")
                return (idx, None, _empty_extraction_artifacts_v1(), str(e))
    
    # Run all OCR extractions in parallel (bounded by semaphore)
    logger.info(f"Starting parallel OCR extraction for {len(files_list)} files (concurrency={ocr_concurrency})")
    ocr_start = time.time()
    ocr_tasks = [_extract_with_semaphore(i, f) for i, f in enumerate(files_list)]
    ocr_results = await asyncio.gather(*ocr_tasks, return_exceptions=True)
    
    # Build lookup dicts from OCR stage results
    extracted_texts: Dict[int, Optional[str]] = {}
    extraction_artifacts_by_idx: Dict[int, Dict[str, Any]] = {}
    extraction_errors: Dict[int, str] = {}
    for result in ocr_results:
        if isinstance(result, Exception):
            logger.error(f"OCR task failed with exception: {result}")
            continue
        idx, text, artifacts, error = result
        extracted_texts[idx] = text
        extraction_artifacts_by_idx[idx] = artifacts or _empty_extraction_artifacts_v1(raw_text=text or "")
        if error:
            extraction_errors[idx] = error
    
    ocr_elapsed = time.time() - ocr_start
    logger.info(f"Parallel OCR complete: {len(extracted_texts)} files in {ocr_elapsed:.2f}s")
    # ═══════════════════════════════════════════════════════════════════════════

    for idx, upload_file in enumerate(files_list):
        filename = getattr(upload_file, "filename", f"document_{idx+1}")
        content_type = getattr(upload_file, "content_type", "unknown")
        document_type = _resolve_document_type(filename, idx, normalized_tags)
        document_id = str(uuid4())
        doc_info: Dict[str, Any] = {
            "id": document_id,
            "filename": filename,
            "document_type": document_type,
            "extracted_fields": {},
            "extraction_status": "empty",
        }
        if normalized_tags and filename:
            lower_name = filename.lower()
            doc_info["tag"] = normalized_tags.get(lower_name) or normalized_tags.get(lower_name.rsplit(".", 1)[0])
        
        logger.info(f"Processing file {idx+1}/{len(files_list)}: {filename} (type: {document_type}, content-type: {content_type})")
        
        # Use pre-extracted text + artifacts from parallel OCR phase
        extracted_text = extracted_texts.get(idx)
        extraction_artifacts_v1 = extraction_artifacts_by_idx.get(idx) or _empty_extraction_artifacts_v1(raw_text=extracted_text or "")
        doc_info["extraction_artifacts_v1"] = extraction_artifacts_v1
        doc_info["ocr_confidence"] = extraction_artifacts_v1.get("ocr_confidence")

        artifacts_index = context.setdefault("document_artifacts_v1", {})
        artifacts_index[document_id] = extraction_artifacts_v1

        if idx in extraction_errors:
            logger.warning(f"⚠ OCR extraction error for {filename}: {extraction_errors[idx]}")
        if not extracted_text:
            logger.warning(f"⚠ No text extracted from {filename} - skipping field extraction")
            doc_info["extraction_status"] = "empty"
            logger.info(
                "validate.extraction.final file=%s doc_type=%s status=%s fallback=%s reason_codes=%s",
                filename,
                document_type,
                doc_info["extraction_status"],
                bool(extraction_artifacts_v1.get("fallback_activated")),
                extraction_artifacts_v1.get("reason_codes") or [],
            )
            document_details.append(doc_info)
            continue
        
        logger.info(f"✓ Extracted {len(extracted_text)} characters from {filename}")

        try:
            # Treat LC, SWIFT messages, and LC applications as LC-like documents
            is_lc_like = document_type in ("letter_of_credit", "swift_message", "lc_application")
            
            if is_lc_like:
                lc_payload = context.setdefault("lc", {})
                if "raw_text" not in lc_payload:
                    lc_payload["raw_text"] = extracted_text
                    context["lc_text"] = extracted_text
                    # Track the source document type for importer draft LC analysis
                    lc_payload["source_type"] = document_type

                lc_format = detect_lc_format(extracted_text)
                lc_payload["format"] = lc_format

                if lc_format == "iso20022":
                    # Use enhanced ISO 20022 extractor with AI fallback
                    try:
                        from app.services.extraction.iso20022_lc_extractor import (
                            extract_iso20022_with_ai_fallback,
                            ISO20022ParseError as ISO20022Error,
                        )
                        
                        iso_context = await extract_iso20022_with_ai_fallback(
                            extracted_text,
                            ai_threshold=0.5,
                        )
                        
                        extraction_method = iso_context.get("_extraction_method", "iso20022")
                        extraction_confidence = iso_context.get("_extraction_confidence", 0.0)
                        
                        logger.info(
                            f"ISO 20022 extraction from {filename}: method={extraction_method} "
                            f"confidence={extraction_confidence:.2f}"
                        )
                        
                        lc_payload.update(iso_context)
                        has_structured_data = True
                        doc_info["extracted_fields"] = iso_context
                        doc_info["extraction_status"] = "success"
                        doc_info["extraction_method"] = extraction_method
                        doc_info["extraction_confidence"] = extraction_confidence
                        
                        logger.info(f"ISO20022 LC context keys: {list(lc_payload.keys())}")
                        if not context.get("lc_number") and iso_context.get("number"):
                            context["lc_number"] = iso_context["number"]
                            
                    except Exception as exc:
                        logger.warning(f"ISO20022 LC extraction failed for {filename}: {exc}", exc_info=True)
                        doc_info["extraction_status"] = "failed"
                        doc_info["extraction_error"] = str(exc)
                else:
                    # Use AI-FIRST extraction for OCR/plaintext LC documents
                    # This runs AI as PRIMARY, then validates with regex
                    try:
                        # AI-first extraction (PRIMARY)
                        lc_struct = await extract_lc_ai_first(extracted_text)
                        extraction_method = lc_struct.get("_extraction_method", "unknown")
                        extraction_confidence = lc_struct.get("_extraction_confidence", 0.0)
                        extraction_status = lc_struct.get("_status", "unknown")
                        
                        logger.info(
                            f"AI-first extraction from {filename}: method={extraction_method} "
                            f"confidence={extraction_confidence:.2f} status={extraction_status} "
                            f"keys={list(lc_struct.keys())}"
                        )
                        
                        if lc_struct and extraction_status != "failed":
                            # AI-first already includes validation, but apply two-stage for normalization
                            validated_lc, validation_summary = _apply_two_stage_validation(
                                lc_struct, "lc", filename, job_id=job_id
                            )
                            
                            lc_payload.update(validated_lc)
                            context["lc_structured_output"] = validated_lc
                            has_structured_data = True
                            logger.info(f"LC context keys: {list(lc_payload.keys())}")
                            
                            # Get LC number from various possible keys
                            lc_number = (
                                validated_lc.get("number") or 
                                validated_lc.get("lc_number") or
                                validated_lc.get("reference")
                            )
                            if not context.get("lc_number") and lc_number:
                                context["lc_number"] = lc_number
                            
                            doc_info["extracted_fields"] = (
                                validated_lc.get("extracted_fields")
                                if isinstance(validated_lc.get("extracted_fields"), dict)
                                else validated_lc
                            )
                            doc_info["extraction_status"] = "success"
                            doc_info["extraction_method"] = extraction_method
                            doc_info["extraction_confidence"] = extraction_confidence
                            doc_info["validation_summary"] = validation_summary
                            doc_info["ai_first_status"] = extraction_status
                            
                            # Include field-level details if available
                            if "_field_details" in lc_struct:
                                doc_info["field_details"] = lc_struct["_field_details"]
                            if "_status_counts" in lc_struct:
                                doc_info["status_counts"] = lc_struct["_status_counts"]
                        else:
                            logger.warning(f"AI-first extraction failed for {filename}, status={extraction_status}")
                    except Exception as extract_error:
                        logger.warning(f"LC extraction (with AI) failed for {filename}: {extract_error}", exc_info=True)
                        # Ultimate fallback to basic field extractor
                        try:
                            lc_fields = extractor.extract_fields(extracted_text, DocumentType.LETTER_OF_CREDIT)
                            logger.info(f"Fallback: Extracted {len(lc_fields)} fields from LC document {filename}")
                            lc_context = _fields_to_lc_context(lc_fields)
                            if lc_context:
                                # Apply two-stage validation to fallback extraction
                                validated_lc, validation_summary = _apply_two_stage_validation(
                                    lc_context, "lc", filename, job_id=job_id
                                )
                                
                                lc_payload.update(validated_lc)
                                has_structured_data = True
                                logger.info(f"LC context keys: {list(lc_payload.keys())}")
                                if not context.get("lc_number") and validated_lc.get("number"):
                                    context["lc_number"] = validated_lc["number"]
                                doc_info["extracted_fields"] = (
                                    validated_lc.get("extracted_fields")
                                    if isinstance(validated_lc.get("extracted_fields"), dict)
                                    else validated_lc
                                )
                                doc_info["extraction_status"] = "success"
                                doc_info["validation_summary"] = validation_summary
                            else:
                                logger.warning(f"No LC context created from {len(lc_fields)} extracted fields")
                        except Exception as fallback_error:
                            logger.error(f"Both LC extraction methods failed for {filename}: {fallback_error}", exc_info=True)
                            doc_info["extraction_status"] = "failed"
                            doc_info["extraction_error"] = str(fallback_error)
            elif document_type in ("commercial_invoice", "proforma_invoice"):
                # Use AI-FIRST extraction for invoices (including proforma invoices)
                try:
                    invoice_struct = await extract_invoice_ai_first(extracted_text)
                    extraction_method = invoice_struct.get("_extraction_method", "unknown")
                    extraction_confidence = invoice_struct.get("_extraction_confidence", 0.0)
                    extraction_status = invoice_struct.get("_status", "unknown")
                    
                    logger.info(
                        f"AI-first invoice extraction from {filename}: method={extraction_method} "
                        f"confidence={extraction_confidence:.2f} status={extraction_status}"
                    )
                    
                    if invoice_struct and extraction_status != "failed":
                        # Apply two-stage validation for normalization
                        validated_invoice, validation_summary = _apply_two_stage_validation(
                            invoice_struct, "invoice", filename, job_id=job_id
                        )
                        
                        if "invoice" not in context:
                            context["invoice"] = {}
                        context["invoice"]["raw_text"] = extracted_text
                        context["invoice"].update(validated_invoice)
                        has_structured_data = True
                        doc_info["extracted_fields"] = (
                            validated_invoice.get("extracted_fields")
                            if isinstance(validated_invoice.get("extracted_fields"), dict)
                            else validated_invoice
                        )
                        doc_info["extraction_status"] = "success"
                        doc_info["extraction_method"] = extraction_method
                        doc_info["extraction_confidence"] = extraction_confidence
                        doc_info["validation_summary"] = validation_summary
                        doc_info["ai_first_status"] = extraction_status
                        
                        if "_field_details" in invoice_struct:
                            doc_info["field_details"] = invoice_struct["_field_details"]
                        if "_status_counts" in invoice_struct:
                            doc_info["status_counts"] = invoice_struct["_status_counts"]
                        
                        logger.info(f"Invoice context keys: {list(context['invoice'].keys())}")
                    else:
                        logger.warning(f"AI-first invoice extraction failed for {filename}")
                except Exception as inv_err:
                    logger.warning(f"Invoice AI extraction failed for {filename}: {inv_err}", exc_info=True)
                    # Fallback to regex
                    invoice_fields = extractor.extract_fields(extracted_text, DocumentType.COMMERCIAL_INVOICE)
                    invoice_context = _fields_to_flat_context(invoice_fields)
                    if invoice_context:
                        validated_invoice, validation_summary = _apply_two_stage_validation(
                            invoice_context, "invoice", filename, job_id=job_id
                        )
                        if "invoice" not in context:
                            context["invoice"] = {}
                        context["invoice"]["raw_text"] = extracted_text
                        context["invoice"].update(validated_invoice)
                        has_structured_data = True
                        doc_info["extracted_fields"] = (
                            validated_invoice.get("extracted_fields")
                            if isinstance(validated_invoice.get("extracted_fields"), dict)
                            else validated_invoice
                        )
                        doc_info["extraction_status"] = "success"
                        doc_info["extraction_method"] = "regex_fallback"
                        doc_info["validation_summary"] = validation_summary
                        field_details = validated_invoice.get("_field_details") or invoice_context.get("_field_details")
                        if field_details:
                            doc_info["field_details"] = field_details
            elif document_type == "bill_of_lading":
                # Use AI-FIRST extraction for Bill of Lading
                try:
                    bl_struct = await extract_bl_ai_first(extracted_text)
                    extraction_method = bl_struct.get("_extraction_method", "unknown")
                    extraction_confidence = bl_struct.get("_extraction_confidence", 0.0)
                    extraction_status = bl_struct.get("_status", "unknown")
                    
                    logger.info(
                        f"AI-first B/L extraction from {filename}: method={extraction_method} "
                        f"confidence={extraction_confidence:.2f} status={extraction_status}"
                    )
                    
                    if bl_struct and extraction_status != "failed":
                        # Apply two-stage validation for normalization
                        validated_bl, validation_summary = _apply_two_stage_validation(
                            bl_struct, "bl", filename, job_id=job_id
                        )
                        
                        if "bill_of_lading" not in context:
                            context["bill_of_lading"] = {}
                        context["bill_of_lading"]["raw_text"] = extracted_text
                        context["bill_of_lading"].update(validated_bl)
                        has_structured_data = True
                        doc_info["extracted_fields"] = (
                            validated_bl.get("extracted_fields")
                            if isinstance(validated_bl.get("extracted_fields"), dict)
                            else validated_bl
                        )
                        doc_info["extraction_status"] = "success"
                        doc_info["extraction_method"] = extraction_method
                        doc_info["extraction_confidence"] = extraction_confidence
                        doc_info["validation_summary"] = validation_summary
                        doc_info["ai_first_status"] = extraction_status
                        
                        if "_field_details" in bl_struct:
                            doc_info["field_details"] = bl_struct["_field_details"]
                        if "_status_counts" in bl_struct:
                            doc_info["status_counts"] = bl_struct["_status_counts"]
                        
                        logger.info(f"B/L context keys: {list(context['bill_of_lading'].keys())}")
                    else:
                        logger.warning(f"AI-first B/L extraction failed for {filename}")
                except Exception as bl_err:
                    logger.warning(f"B/L AI extraction failed for {filename}: {bl_err}", exc_info=True)
                    # Fallback to regex
                    bl_fields = extractor.extract_fields(extracted_text, DocumentType.BILL_OF_LADING)
                    bl_context = _fields_to_flat_context(bl_fields)
                    if bl_context:
                        validated_bl, validation_summary = _apply_two_stage_validation(
                            bl_context, "bl", filename, job_id=job_id
                        )
                        if "bill_of_lading" not in context:
                            context["bill_of_lading"] = {}
                        context["bill_of_lading"]["raw_text"] = extracted_text
                        context["bill_of_lading"].update(validated_bl)
                        has_structured_data = True
                        doc_info["extracted_fields"] = (
                            validated_bl.get("extracted_fields")
                            if isinstance(validated_bl.get("extracted_fields"), dict)
                            else validated_bl
                        )
                        doc_info["extraction_status"] = "success"
                        doc_info["extraction_method"] = "regex_fallback"
                        doc_info["validation_summary"] = validation_summary
                        field_details = validated_bl.get("_field_details") or bl_context.get("_field_details")
                        if field_details:
                            doc_info["field_details"] = field_details
            elif document_type == "packing_list":
                # Use AI-FIRST extraction for packing list
                try:
                    packing_struct = await extract_packing_list_ai_first(extracted_text)
                    extraction_method = packing_struct.get("_extraction_method", "unknown")
                    extraction_confidence = packing_struct.get("_extraction_confidence", 0.0)
                    extraction_status = packing_struct.get("_status", "unknown")
                    
                    logger.info(
                        f"AI-first packing list extraction from {filename}: method={extraction_method} "
                        f"confidence={extraction_confidence:.2f} status={extraction_status}"
                    )
                    
                    if packing_struct and extraction_status != "failed":
                        validated_packing, validation_summary = _apply_two_stage_validation(
                            packing_struct, "packing_list", filename, job_id=job_id
                        )
                        
                        pkg_ctx = context.setdefault("packing_list", {})
                        pkg_ctx["raw_text"] = extracted_text
                        pkg_ctx.update(validated_packing)
                        has_structured_data = True
                        doc_info["extracted_fields"] = (
                            validated_packing.get("extracted_fields")
                            if isinstance(validated_packing.get("extracted_fields"), dict)
                            else validated_packing
                        )
                        doc_info["extraction_status"] = "success"
                        doc_info["extraction_method"] = extraction_method
                        doc_info["extraction_confidence"] = extraction_confidence
                        doc_info["validation_summary"] = validation_summary
                        doc_info["ai_first_status"] = extraction_status
                        
                        if "_field_details" in packing_struct:
                            doc_info["field_details"] = packing_struct["_field_details"]
                        
                        logger.info(f"Packing list context keys: {list(pkg_ctx.keys())}")
                    else:
                        logger.warning(f"AI-first packing list extraction failed for {filename}")
                except Exception as packing_err:
                    logger.warning(f"Packing list AI extraction failed for {filename}: {packing_err}", exc_info=True)
                    packing_fields = extractor.extract_fields(extracted_text, DocumentType.PACKING_LIST)
                    packing_context = _fields_to_flat_context(packing_fields)
                    if packing_context:
                        validated_packing, validation_summary = _apply_two_stage_validation(
                            packing_context, "packing_list", filename, job_id=job_id
                        )
                        pkg_ctx = context.setdefault("packing_list", {})
                        pkg_ctx["raw_text"] = extracted_text
                        pkg_ctx.update(validated_packing)
                        has_structured_data = True
                        doc_info["extracted_fields"] = (
                            validated_packing.get("extracted_fields")
                            if isinstance(validated_packing.get("extracted_fields"), dict)
                            else validated_packing
                        )
                        doc_info["extraction_status"] = "success"
                        doc_info["extraction_method"] = "regex_fallback"
                        doc_info["validation_summary"] = validation_summary
                        field_details = validated_packing.get("_field_details") or packing_context.get("_field_details")
                        if field_details:
                            doc_info["field_details"] = field_details
            elif document_type == "certificate_of_origin":
                # Use AI-FIRST extraction for certificate of origin
                try:
                    coo_struct = await extract_coo_ai_first(extracted_text)
                    extraction_method = coo_struct.get("_extraction_method", "unknown")
                    extraction_confidence = coo_struct.get("_extraction_confidence", 0.0)
                    extraction_status = coo_struct.get("_status", "unknown")
                    
                    logger.info(
                        f"AI-first CoO extraction from {filename}: method={extraction_method} "
                        f"confidence={extraction_confidence:.2f} status={extraction_status}"
                    )
                    
                    if coo_struct and extraction_status != "failed":
                        validated_coo, validation_summary = _apply_two_stage_validation(
                            coo_struct, "certificate_of_origin", filename, job_id=job_id
                        )

                        coo_completeness = _assess_coo_parse_completeness(validated_coo)
                        parse_complete = bool(coo_completeness.get("parse_complete"))
                        effective_extraction_status = "success" if parse_complete else "partial"

                        coo_ctx = context.setdefault("certificate_of_origin", {})
                        coo_ctx["raw_text"] = extracted_text
                        coo_ctx.update(validated_coo)
                        has_structured_data = True
                        doc_info["extracted_fields"] = (
                            validated_coo.get("extracted_fields")
                            if isinstance(validated_coo.get("extracted_fields"), dict)
                            else validated_coo
                        )
                        doc_info["extraction_status"] = effective_extraction_status
                        doc_info["parse_complete"] = parse_complete
                        doc_info["parse_completeness"] = coo_completeness.get("required_ratio")
                        doc_info["missing_required_fields"] = coo_completeness.get("missing_required_fields", [])
                        doc_info["required_fields_found"] = coo_completeness.get("required_found")
                        doc_info["required_fields_total"] = coo_completeness.get("required_total")
                        doc_info["extraction_method"] = extraction_method
                        doc_info["extraction_confidence"] = extraction_confidence
                        doc_info["validation_summary"] = validation_summary
                        doc_info["ai_first_status"] = extraction_status

                        if "_field_details" in coo_struct:
                            doc_info["field_details"] = coo_struct["_field_details"]

                        logger.info(
                            "Certificate of origin parse completeness for %s: parse_complete=%s required=%s/%s",
                            filename,
                            parse_complete,
                            coo_completeness.get("required_found"),
                            coo_completeness.get("required_total"),
                        )
                        logger.info(f"Certificate of origin context keys: {list(coo_ctx.keys())}")
                    else:
                        logger.warning(f"AI-first CoO extraction failed for {filename}")
                except Exception as coo_err:
                    logger.warning(f"CoO AI extraction failed for {filename}: {coo_err}", exc_info=True)
                    coo_fields = extractor.extract_fields(extracted_text, DocumentType.CERTIFICATE_OF_ORIGIN)
                    coo_context = _fields_to_flat_context(coo_fields)
                    if coo_context:
                        validated_coo, validation_summary = _apply_two_stage_validation(
                            coo_context, "certificate_of_origin", filename, job_id=job_id
                        )
                        coo_completeness = _assess_coo_parse_completeness(validated_coo)
                        parse_complete = bool(coo_completeness.get("parse_complete"))
                        effective_extraction_status = "success" if parse_complete else "partial"

                        coo_ctx = context.setdefault("certificate_of_origin", {})
                        coo_ctx["raw_text"] = extracted_text
                        coo_ctx.update(validated_coo)
                        has_structured_data = True
                        doc_info["extracted_fields"] = (
                            validated_coo.get("extracted_fields")
                            if isinstance(validated_coo.get("extracted_fields"), dict)
                            else validated_coo
                        )
                        doc_info["extraction_status"] = effective_extraction_status
                        doc_info["parse_complete"] = parse_complete
                        doc_info["parse_completeness"] = coo_completeness.get("required_ratio")
                        doc_info["missing_required_fields"] = coo_completeness.get("missing_required_fields", [])
                        doc_info["required_fields_found"] = coo_completeness.get("required_found")
                        doc_info["required_fields_total"] = coo_completeness.get("required_total")
                        doc_info["extraction_method"] = "regex_fallback"
                        doc_info["validation_summary"] = validation_summary
                        field_details = validated_coo.get("_field_details") or coo_context.get("_field_details")
                        if field_details:
                            doc_info["field_details"] = field_details
            elif document_type == "insurance_certificate":
                # Use AI-FIRST extraction for insurance certificate
                try:
                    insurance_struct = await extract_insurance_ai_first(extracted_text)
                    extraction_method = insurance_struct.get("_extraction_method", "unknown")
                    extraction_confidence = insurance_struct.get("_extraction_confidence", 0.0)
                    extraction_status = insurance_struct.get("_status", "unknown")
                    
                    logger.info(
                        f"AI-first insurance extraction from {filename}: method={extraction_method} "
                        f"confidence={extraction_confidence:.2f} status={extraction_status}"
                    )
                    
                    if insurance_struct and extraction_status != "failed":
                        validated_insurance, validation_summary = _apply_two_stage_validation(
                            insurance_struct, "insurance", filename, job_id=job_id
                        )
                        
                        insurance_ctx = context.setdefault("insurance_certificate", {})
                        insurance_ctx["raw_text"] = extracted_text
                        insurance_ctx.update(validated_insurance)
                        has_structured_data = True
                        doc_info["extracted_fields"] = (
                            validated_insurance.get("extracted_fields")
                            if isinstance(validated_insurance.get("extracted_fields"), dict)
                            else validated_insurance
                        )
                        doc_info["extraction_status"] = "success"
                        doc_info["extraction_method"] = extraction_method
                        doc_info["extraction_confidence"] = extraction_confidence
                        doc_info["validation_summary"] = validation_summary
                        doc_info["ai_first_status"] = extraction_status
                        
                        if "_field_details" in insurance_struct:
                            doc_info["field_details"] = insurance_struct["_field_details"]
                        
                        logger.info(f"Insurance context keys: {list(insurance_ctx.keys())}")
                    else:
                        logger.warning(f"AI-first insurance extraction failed for {filename}")
                except Exception as ins_err:
                    logger.warning(f"Insurance AI extraction failed for {filename}: {ins_err}", exc_info=True)
                    insurance_fields = extractor.extract_fields(extracted_text, DocumentType.INSURANCE_CERTIFICATE)
                    insurance_context = _fields_to_flat_context(insurance_fields)
                    if insurance_context:
                        validated_insurance, validation_summary = _apply_two_stage_validation(
                            insurance_context, "insurance", filename, job_id=job_id
                        )
                        insurance_ctx = context.setdefault("insurance_certificate", {})
                        insurance_ctx["raw_text"] = extracted_text
                        insurance_ctx.update(validated_insurance)
                        has_structured_data = True
                        doc_info["extracted_fields"] = (
                            validated_insurance.get("extracted_fields")
                            if isinstance(validated_insurance.get("extracted_fields"), dict)
                            else validated_insurance
                        )
                        doc_info["extraction_status"] = "success"
                        doc_info["extraction_method"] = "regex_fallback"
                        doc_info["validation_summary"] = validation_summary
                        field_details = validated_insurance.get("_field_details") or insurance_context.get("_field_details")
                        if field_details:
                            doc_info["field_details"] = field_details
            elif document_type == "inspection_certificate":
                # Use AI-FIRST extraction for inspection certificate
                try:
                    inspection_struct = await extract_inspection_ai_first(extracted_text)
                    extraction_method = inspection_struct.get("_extraction_method", "unknown")
                    extraction_confidence = inspection_struct.get("_extraction_confidence", 0.0)
                    extraction_status = inspection_struct.get("_status", "unknown")
                    
                    logger.info(
                        f"AI-first inspection extraction from {filename}: method={extraction_method} "
                        f"confidence={extraction_confidence:.2f} status={extraction_status}"
                    )
                    
                    if inspection_struct and extraction_status != "failed":
                        validated_inspection, validation_summary = _apply_two_stage_validation(
                            inspection_struct, "inspection", filename, job_id=job_id
                        )
                        
                        inspection_ctx = context.setdefault("inspection_certificate", {})
                        inspection_ctx["raw_text"] = extracted_text
                        inspection_ctx.update(validated_inspection)
                        has_structured_data = True
                        doc_info["extracted_fields"] = (
                            validated_inspection.get("extracted_fields")
                            if isinstance(validated_inspection.get("extracted_fields"), dict)
                            else validated_inspection
                        )
                        doc_info["extraction_status"] = "success"
                        doc_info["extraction_method"] = extraction_method
                        doc_info["extraction_confidence"] = extraction_confidence
                        doc_info["validation_summary"] = validation_summary
                        doc_info["ai_first_status"] = extraction_status
                        
                        if "_field_details" in inspection_struct:
                            doc_info["field_details"] = inspection_struct["_field_details"]
                        
                        logger.info(f"Inspection context keys: {list(inspection_ctx.keys())}")
                    else:
                        logger.warning(f"AI-first inspection extraction failed for {filename}")
                except Exception as insp_err:
                    logger.warning(f"Inspection AI extraction failed for {filename}: {insp_err}", exc_info=True)
                    inspection_fields = extractor.extract_fields(extracted_text, DocumentType.INSPECTION_CERTIFICATE)
                    inspection_context = _fields_to_flat_context(inspection_fields)
                    if inspection_context:
                        validated_inspection, validation_summary = _apply_two_stage_validation(
                            inspection_context, "inspection", filename, job_id=job_id
                        )
                        inspection_ctx = context.setdefault("inspection_certificate", {})
                        inspection_ctx["raw_text"] = extracted_text
                        inspection_ctx.update(validated_inspection)
                        has_structured_data = True
                        doc_info["extracted_fields"] = (
                            validated_inspection.get("extracted_fields")
                            if isinstance(validated_inspection.get("extracted_fields"), dict)
                            else validated_inspection
                        )
                        doc_info["extraction_status"] = "success"
                        doc_info["extraction_method"] = "regex_fallback"
                        doc_info["validation_summary"] = validation_summary
                        field_details = validated_inspection.get("_field_details") or inspection_context.get("_field_details")
                        if field_details:
                            doc_info["field_details"] = field_details
            else:
                # For other document types, retain raw text for downstream use
                doc_info["raw_text_preview"] = extracted_text[:500]
                doc_info["extraction_status"] = "text_only"
                extra_context = context.setdefault(document_type, {})
                extra_context["raw_text"] = extracted_text
        except Exception as e:
            logger.error(f"Error extracting fields from {filename}: {e}", exc_info=True)
            _finalize_text_backed_extraction_status(doc_info, document_type, extracted_text or "")
            logger.info(
                "validate.extraction.final file=%s doc_type=%s status=%s fallback=%s reason_codes=%s",
                filename,
                document_type,
                doc_info.get("extraction_status"),
                bool(extraction_artifacts_v1.get("fallback_activated")),
                extraction_artifacts_v1.get("reason_codes") or [],
            )
            document_details.append(doc_info)
            continue

        if doc_info.get("extracted_fields"):
            doc_info["raw_text_preview"] = extracted_text[:500]
        elif extracted_text:
            # Ensure at least a preview is available for OCR overview
            doc_info["raw_text_preview"] = extracted_text[:500]
            if doc_info.get("extraction_status") == "empty" and not _extraction_fallback_hotfix_enabled():
                doc_info["extraction_status"] = "text_only"

        context_payload = _context_payload_for_doc_type(context, document_type)
        if isinstance(context_payload, dict):
            context_payload["raw_text"] = context_payload.get("raw_text") or extracted_text
            context_payload["extraction_artifacts_v1"] = extraction_artifacts_v1
            _apply_direct_token_recovery(context_payload, extraction_artifacts_v1)
            if isinstance(context_payload.get("extracted_fields"), dict):
                doc_info["extracted_fields"] = context_payload.get("extracted_fields")
            if isinstance(context_payload.get("_field_details"), dict):
                doc_info["field_details"] = context_payload.get("_field_details")

        _enforce_day1_runtime_policy(doc_info, context_payload if isinstance(context_payload, dict) else {}, document_type, extracted_text)
        _apply_extraction_guard(doc_info, extracted_text)
        _finalize_text_backed_extraction_status(doc_info, document_type, extracted_text)
        summary = doc_info.get("validation_summary") or {}
        llm_trace = _resolve_doc_llm_trace(
            context_payload if isinstance(context_payload, dict) else {},
            doc_info.get("extraction_method"),
            has_two_stage=bool(summary),
        )
        canonical_before = int(summary.get("canonical_field_count_before") or _count_populated_canonical_fields(doc_info.get("extracted_fields") or {}))
        canonical_after = int(summary.get("canonical_field_count_after") or _count_populated_canonical_fields(doc_info.get("extracted_fields") or {}))
        extraction_status_now = str(doc_info.get("extraction_status") or "unknown")
        downgrade_reason = doc_info.get("downgrade_reason")
        if not downgrade_reason and extraction_status_now in {"partial", "error", "failed"}:
            downgrade_reason = doc_info.get("extraction_error") or doc_info.get("ai_first_status") or "downgraded"

        trace_payload = _build_document_extraction_payload(
            doc_type=document_type,
            file_name=filename,
            job_id=job_id,
            ocr_text_len=len(extracted_text or ""),
            extractor_path=llm_trace.get("extractor_path") or "fallback",
            llm_provider=llm_trace.get("provider"),
            llm_model=llm_trace.get("model"),
            router_layer=llm_trace.get("router_layer"),
            ai_response_present=canonical_before > 0 or bool(doc_info.get("ai_first_status")),
            ai_parse_success=canonical_before > 0,
            canonical_before_two_stage=canonical_before,
            canonical_after_two_stage=canonical_after,
            extraction_status=extraction_status_now,
            downgrade_reason=downgrade_reason,
        )
        _log_document_extraction_telemetry(
            doc_type=document_type,
            file_name=filename,
            job_id=job_id,
            ocr_text_len=len(extracted_text or ""),
            extractor_path=llm_trace.get("extractor_path") or "fallback",
            llm_provider=llm_trace.get("provider"),
            llm_model=llm_trace.get("model"),
            router_layer=llm_trace.get("router_layer"),
            ai_response_present=canonical_before > 0 or bool(doc_info.get("ai_first_status")),
            ai_parse_success=canonical_before > 0,
            canonical_before_two_stage=canonical_before,
            canonical_after_two_stage=canonical_after,
            extraction_status=extraction_status_now,
            downgrade_reason=downgrade_reason,
        )
        logger.info(
            "validate.extraction.final file=%s doc_type=%s status=%s fallback=%s reason_codes=%s",
            filename,
            document_type,
            extraction_status_now,
            bool(extraction_artifacts_v1.get("fallback_activated")),
            extraction_artifacts_v1.get("reason_codes") or [],
        )
        debug_extraction_trace.append(trace_payload)

        document_details.append(doc_info)
        entry = documents_presence.setdefault(
            document_type,
            {"present": False, "count": 0},
        )
        entry["present"] = True
        entry["count"] += 1

    text_backed_documents = any(
        bool(((doc.get("extraction_artifacts_v1") or {}).get("raw_text") or "").strip())
        or bool((doc.get("raw_text_preview") or "").strip())
        for doc in document_details
    )

    # Set extraction status
    if has_structured_data:
        context["extraction_status"] = "success"
        logger.info(f"Final extracted context structure: {list(context.keys())}")
    elif any(key in context for key in ("lc", "invoice", "bill_of_lading")) or (
        _extraction_fallback_hotfix_enabled() and text_backed_documents
    ):
        # We have raw_text but no structured fields
        context["extraction_status"] = "partial"
        logger.warning("Extracted raw text but no structured fields could be parsed")
    else:
        context["extraction_status"] = "empty"
        logger.warning("No context extracted from any files")
    
    if document_details:
        _augment_doc_field_details_with_decisions(document_details)
        extraction_core_bundle = _annotate_documents_with_review_metadata(document_details)
        if isinstance(extraction_core_bundle, dict):
            context["_extraction_core_v1"] = extraction_core_bundle
        context["documents"] = document_details

    context["documents_presence"] = documents_presence
    context["documents_summary"] = documents_presence
    context["_debug_extraction_trace"] = debug_extraction_trace
    if context.get("lc"):
        context["lc"] = _normalize_lc_payload_structures(context["lc"])

    # GUARANTEE: Always provide lc_structured_output for Option-E builder
    # Even if extraction failed, provide a minimal structure
    if "lc_structured_output" not in context:
        lc_data = context.get("lc") or {}
        context["lc_structured_output"] = {
            "lc_type": lc_data.get("type") or "unknown",
            "lc_type_reason": "Extracted from uploaded documents" if lc_data else "No LC data extracted",
            "lc_type_confidence": 50 if lc_data else 0,
            "lc_type_source": "auto",
            "mt700": lc_data.get("mt700") or {"blocks": {}, "raw_text": lc_data.get("raw_text"), "version": "mt700_v1"},
            "goods": lc_data.get("goods") or lc_data.get("goods_items") or [],
            "clauses": lc_data.get("clauses") or lc_data.get("additional_conditions") or [],
            "timeline": [],
            "issues": [],
        }

    return context


def detect_lc_format(raw_lc_text: Optional[str]) -> str:
    """
    Detect whether an LC payload is ISO 20022 XML or MT700 text.
    Defaults to MT700 when no XML signature is present.
    """

    if not raw_lc_text:
        return "mt700"

    snippet = raw_lc_text.strip()
    lowered = snippet.lower()
    if "<document" in lowered and "xmlns" in lowered:
        return "iso20022"
    if snippet.startswith("<?xml") and "<Document" in snippet:
        return "iso20022"
    return "mt700"


def _build_issue_context(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a context snapshot from the validation payload for AI issue rewriting.
    Extracts key document data that helps the AI produce accurate issue descriptions.
    """
    lc = payload.get("lc") or payload.get("lc_data") or {}
    invoice = payload.get("invoice") or {}
    bill_of_lading = payload.get("bill_of_lading") or payload.get("billOfLading") or {}
    bl_fields = bill_of_lading.get("extracted_fields") if isinstance(bill_of_lading.get("extracted_fields"), dict) else {}
    certificate_of_origin = payload.get("certificate_of_origin") or payload.get("certificateOfOrigin") or {}
    insurance = payload.get("insurance") or payload.get("insurance_certificate") or {}
    packing_list = payload.get("packing_list") or payload.get("packingList") or {}
    
    return {
        "lc": {
            "goods_description": lc.get("goods_description"),
            "goods_items": lc.get("goods_items"),
            "incoterm": lc.get("incoterm"),
            "ports": lc.get("ports"),
            "dates": lc.get("dates"),
            "applicant": lc.get("applicant"),
            "beneficiary": lc.get("beneficiary"),
            "amount": lc.get("amount") or lc.get("lc_amount"),
            "currency": lc.get("currency"),
        },
        "invoice": {
            "goods_description": invoice.get("goods_description") or invoice.get("product_description"),
            "amount": invoice.get("invoice_amount") or invoice.get("amount"),
            "currency": invoice.get("currency"),
            "hs_code": invoice.get("hs_code"),
            "consignee": invoice.get("consignee"),
            "shipper": invoice.get("shipper"),
        },
        "bill_of_lading": {
            "goods_description": bill_of_lading.get("goods_description") or bl_fields.get("goods_description"),
            "port_of_loading": bill_of_lading.get("port_of_loading") or bl_fields.get("port_of_loading"),
            "port_of_discharge": bill_of_lading.get("port_of_discharge") or bl_fields.get("port_of_discharge"),
            "vessel": bill_of_lading.get("vessel") or bill_of_lading.get("vessel_name") or bl_fields.get("vessel_name"),
            "voyage_number": bill_of_lading.get("voyage_number") or bl_fields.get("voyage_number"),
            "gross_weight": bill_of_lading.get("gross_weight") or bl_fields.get("gross_weight"),
            "net_weight": bill_of_lading.get("net_weight") or bl_fields.get("net_weight"),
            "on_board_date": bill_of_lading.get("on_board_date") or bill_of_lading.get("shipped_on_board_date") or bl_fields.get("shipped_on_board_date"),
            "consignee": bill_of_lading.get("consignee") or bl_fields.get("consignee"),
            "shipper": bill_of_lading.get("shipper") or bl_fields.get("shipper"),
        },
        "certificate_of_origin": {
            "origin_country": certificate_of_origin.get("origin_country") or certificate_of_origin.get("country_of_origin"),
            "goods_description": certificate_of_origin.get("goods_description"),
        },
        "insurance": {
            "coverage_amount": insurance.get("coverage_amount") or insurance.get("amount"),
            "currency": insurance.get("currency"),
            "risks_covered": insurance.get("risks_covered"),
        },
        "packing_list": {
            "total_packages": packing_list.get("total_packages"),
            "gross_weight": packing_list.get("gross_weight"),
            "net_weight": packing_list.get("net_weight"),
        },
        "metadata": {
            "lc_number": payload.get("lc_number") or payload.get("lcNumber"),
            "user_type": payload.get("user_type") or payload.get("userType"),
            "workflow_type": payload.get("workflow_type") or payload.get("workflowType"),
        },
    }


def _determine_company_size(current_user: User, payload: Dict[str, Any]) -> Tuple[str, Decimal]:
    """Infer company size from user/company metadata."""
    size = str(payload.get("company_size") or "").strip().lower()
    onboarding_company = ((current_user.onboarding_data or {}).get("company") or {}) if current_user else {}
    if onboarding_company:
        size = (onboarding_company.get("size") or size).strip().lower()
    if not size and getattr(current_user, "company", None):
        company = current_user.company
        if isinstance(company.event_metadata, dict):
            meta_size = company.event_metadata.get("company_size")
            if meta_size:
                size = str(meta_size).strip().lower()
    if size not in {"sme", "medium", "large"}:
        size = "sme"
    tolerance_map = {
        "sme": Decimal("10.0"),
        "medium": Decimal("5.0"),
        "large": Decimal("2.0"),
    }
    tolerance_percent = tolerance_map.get(size, Decimal("7.5"))
    return size, tolerance_percent


def _compute_invoice_amount_bounds(payload: Dict[str, Any], tolerance_percent: Decimal) -> Tuple[Optional[float], Optional[float]]:
    """Compute absolute tolerance amount and allowed invoice limit."""
    # Handle both formats: {"value": 125000} (legacy) and 125000 (AI-first)
    lc_data = payload.get("lc") or {}
    amount_raw = lc_data.get("amount")
    
    if isinstance(amount_raw, dict):
        # Legacy format: {"value": 125000}
        lc_amount_value = amount_raw.get("value")
    else:
        # AI-first format: direct number
        lc_amount_value = amount_raw
    
    lc_amount_decimal = _coerce_decimal(lc_amount_value)
    if lc_amount_decimal is None:
        return None, None
    tolerance_value = lc_amount_decimal * tolerance_percent / Decimal("100")
    limit = lc_amount_decimal + tolerance_value
    return float(tolerance_value), float(limit)


def _coerce_decimal(value: Any) -> Optional[Decimal]:
    """Lightweight decimal coercion used for tolerance math."""
    if value is None:
        return None
    try:
        if isinstance(value, Decimal):
            return value
        if isinstance(value, (int, float)):
            return Decimal(str(value))
        if isinstance(value, str):
            normalized = value.replace(",", "").strip()
            if not normalized:
                return None
            return Decimal(normalized)
    except InvalidOperation:
        return None
    return None


def _empty_extraction_artifacts_v1(
    raw_text: str = "",
    ocr_confidence: Optional[float] = None,
) -> Dict[str, Any]:
    return {
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
    }


def _extraction_fallback_hotfix_enabled() -> bool:
    raw = str(os.getenv("LCCOPILOT_EXTRACTION_FALLBACK_HOTFIX", "1") or "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _ocr_compatibility_v1_enabled() -> bool:
    raw = str(os.getenv("LCCOPILOT_OCR_COMPATIBILITY_V1_ENABLED", "1") or "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _stage_promotion_v1_enabled() -> bool:
    raw = str(os.getenv("LCCOPILOT_STAGE_PROMOTION_V1_ENABLED", "1") or "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _ocr_adapter_runtime_payload_fix_v1_enabled() -> bool:
    raw = str(os.getenv("LCCOPILOT_OCR_ADAPTER_RUNTIME_PAYLOAD_FIX_V1_ENABLED", "1") or "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _stage_threshold_tuning_v1_enabled() -> bool:
    raw = str(os.getenv("LCCOPILOT_STAGE_THRESHOLD_TUNING_V1_ENABLED", "1") or "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _record_extraction_reason_code(artifacts: Dict[str, Any], reason_code: Optional[str]) -> None:
    if not reason_code:
        return
    reasons = artifacts.setdefault("reason_codes", [])
    if reason_code not in reasons:
        reasons.append(reason_code)


def _record_extraction_stage(
    artifacts: Dict[str, Any],
    *,
    filename: str,
    stage: str,
    text: str = "",
    error_code: Optional[str] = None,
    error: Optional[str] = None,
    fallback: bool = False,
) -> None:
    attempted = artifacts.setdefault("attempted_stages", [])
    if stage not in attempted:
        attempted.append(stage)

    text_length = len((text or "").strip())
    artifacts.setdefault("text_length_by_stage", {})[stage] = text_length

    if fallback:
        artifacts["fallback_activated"] = True

    if error_code or error:
        stage_errors = artifacts.setdefault("stage_errors", {})
        entries = stage_errors.setdefault(stage, [])
        if error_code and error_code not in entries:
            entries.append(error_code)
        if error:
            error_text = str(error)
            if error_text and error_text not in entries:
                entries.append(error_text)

    if error_code:
        _record_extraction_reason_code(artifacts, error_code)

    logger.info(
        "validate.extraction.stage file=%s stage=%s text_len=%s fallback=%s error_code=%s",
        filename,
        stage,
        text_length,
        bool(artifacts.get("fallback_activated")),
        error_code,
    )


def _merge_extraction_artifacts(base: Dict[str, Any], overlay: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    result = dict(base or {})
    if not isinstance(overlay, dict):
        return result

    for key, value in overlay.items():
        if key in {"attempted_stages", "reason_codes"}:
            merged = list(result.get(key) or [])
            for item in value or []:
                if item not in merged:
                    merged.append(item)
            result[key] = merged
        elif key in {"text_length_by_stage"}:
            merged_map = dict(result.get(key) or {})
            merged_map.update(value or {})
            result[key] = merged_map
        elif key in {"stage_errors"}:
            merged_errors = dict(result.get(key) or {})
            for stage_name, errors in (value or {}).items():
                existing = list(merged_errors.get(stage_name) or [])
                for entry in errors or []:
                    if entry not in existing:
                        existing.append(entry)
                merged_errors[stage_name] = existing
            result[key] = merged_errors
        elif key in {"provider_attempts"}:
            existing_attempts = list(result.get(key) or [])
            existing_attempts.extend(value or [])
            result[key] = existing_attempts
        elif value not in (None, "", [], {}):
            result[key] = value

    return result


def _finalize_text_extraction_result(
    artifacts: Dict[str, Any],
    *,
    stage: str,
    text: str,
) -> Dict[str, Any]:
    artifacts["final_stage"] = stage
    artifacts["selected_stage"] = artifacts.get("selected_stage") or stage
    artifacts["final_text_length"] = len((text or "").strip())
    artifacts["raw_text"] = text or ""
    return {"text": text or "", "artifacts": artifacts}


def _merge_text_sources(*texts: Optional[str]) -> str:
    """Merge text sources into a deduplicated line stream while preserving order."""
    merged_lines: List[str] = []
    seen: set[str] = set()
    for text in texts:
        if not text:
            continue
        for line in str(text).splitlines():
            normalized = re.sub(r"\s+", " ", line).strip()
            if not normalized:
                continue
            key = normalized.lower()
            if key in seen:
                continue
            seen.add(key)
            merged_lines.append(normalized)
    return "\n".join(merged_lines)


def _build_extraction_artifacts_from_ocr(
    raw_text: str,
    provider_result: Optional[Any] = None,
    ocr_confidence: Optional[float] = None,
) -> Dict[str, Any]:
    artifacts = _empty_extraction_artifacts_v1(raw_text=raw_text, ocr_confidence=ocr_confidence)

    if not provider_result:
        return artifacts

    confidence = provider_result.overall_confidence
    if isinstance(confidence, (int, float)):
        artifacts["ocr_confidence"] = float(confidence)

    metadata = provider_result.metadata if isinstance(provider_result.metadata, dict) else {}
    artifacts["tables"] = metadata.get("tables") or []
    artifacts["key_value_candidates"] = (
        metadata.get("key_value_candidates")
        or metadata.get("key_value_pairs")
        or metadata.get("entities")
        or []
    )

    spans: List[Dict[str, Any]] = []
    bboxes: List[Dict[str, Any]] = []
    for element in provider_result.elements or []:
        span_entry: Dict[str, Any] = {
            "text": element.text,
            "confidence": element.confidence,
            "element_type": element.element_type,
        }
        bbox_entry: Optional[Dict[str, Any]] = None
        if element.bounding_box:
            bbox_entry = {
                "x1": element.bounding_box.x1,
                "y1": element.bounding_box.y1,
                "x2": element.bounding_box.x2,
                "y2": element.bounding_box.y2,
                "page": element.bounding_box.page,
            }
            span_entry["bbox"] = bbox_entry

        spans.append(span_entry)
        if bbox_entry:
            bboxes.append(bbox_entry)

    artifacts["spans"] = spans
    artifacts["bbox"] = bboxes
    return artifacts


def _scrape_binary_text_metadata(file_bytes: bytes) -> str:
    """Best-effort printable-text scrape from binary payloads as a final recovery stage."""
    if not file_bytes:
        return ""

    decoded = file_bytes.decode("latin-1", errors="ignore")
    text_segments = re.findall(r"\(([^()]{6,200})\)", decoded)
    if not text_segments:
        text_segments = re.findall(r"[A-Za-z0-9][A-Za-z0-9:/,.\-() ]{5,}", decoded)

    candidates: List[str] = []
    seen: set[str] = set()
    for segment in text_segments:
        normalized = re.sub(r"\s+", " ", segment).strip()
        if len(normalized) < 6:
            continue
        lower = normalized.lower()
        if lower in seen:
            continue
        if lower in {"obj", "endobj", "stream", "endstream", "xref", "trailer"}:
            continue
        noise_count = sum(1 for ch in normalized if ch in "<>{}[]\\")
        if noise_count > max(3, len(normalized) // 6):
            continue
        seen.add(lower)
        candidates.append(normalized)
        if len(candidates) >= 80:
            break

    return "\n".join(candidates)


_STAGE_FIELD_PATTERNS = {
    "issue_date": [r"\b\d{4}-\d{2}-\d{2}\b", r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b"],
    "bin_tin": [
        r"\b(?:bin|tin|vat\s*reg(?:istration)?|tax\s*id|etin)\b",
        r"\b[0-9OISBL][0-9OISBL\-\s]{9,18}\b",
    ],
    "gross_weight": [
        r"\bgross(?:\s+weight|\s+wt|\s+wgt)?\b",
        r"\bgross\s*/\s*net\b",
        r"\b[0-9OISBL]+(?:[.,][0-9OISBL]+)?\s?(kg|kgs|kilograms?|lb|lbs|mt|ton|tonne)\b",
    ],
    "net_weight": [
        r"\bnet(?:\s+weight|\s+wt|\s+wgt)?\b",
        r"\bgross\s*/\s*net\b",
        r"\b[0-9OISBL]+(?:[.,][0-9OISBL]+)?\s?(kg|kgs|kilograms?|lb|lbs|mt|ton|tonne)\b",
    ],
    "issuer": [r"\bissuer\b", r"\bissuing bank\b", r"\bseller\b", r"\bexporter\b", r"\bcarrier\b", r"\bauthority\b"],
    "voyage": [r"\bvoyage\b", r"\bvessel\b", r"\bvsl\b"],
}

_STAGE_CRITICAL_FIELD_TO_ANCHOR_FIELD = {
    "bin_tin": "bin",
    "voyage": "voyage",
    "gross_weight": "gross_weight",
    "net_weight": "net_weight",
    "issue_date": "doc_date",
    "issuer": "issuer",
}


def _detect_input_mime_type(file_bytes: bytes, filename: str, content_type: Optional[str]) -> str:
    detected = str(content_type or "").strip().lower()
    if file_bytes.startswith(b"%PDF"):
        return "application/pdf"
    if file_bytes[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if file_bytes[:2] == b"\xff\xd8":
        return "image/jpeg"
    if file_bytes[:4] in (b"II*\x00", b"MM\x00*"):
        return "image/tiff"
    if _looks_like_plaintext_bytes(file_bytes):
        return "text/plain"
    if detected and detected != "application/octet-stream":
        return detected
    lowered_name = (filename or "").lower()
    if lowered_name.endswith(".pdf"):
        return "application/pdf"
    if lowered_name.endswith(".png"):
        return "image/png"
    if lowered_name.endswith(".jpg") or lowered_name.endswith(".jpeg"):
        return "image/jpeg"
    if lowered_name.endswith(".tif") or lowered_name.endswith(".tiff"):
        return "image/tiff"
    return "application/octet-stream"


def _looks_like_plaintext_bytes(file_bytes: bytes) -> bool:
    sample = bytes(file_bytes[:4096] or b"")
    if not sample:
        return False
    if sample.startswith(b"%PDF") or sample[:8] == b"\x89PNG\r\n\x1a\n" or sample[:2] == b"\xff\xd8" or sample[:4] in (b"II*\x00", b"MM\x00*"):
        return False
    if b"\x00" in sample:
        return False
    printable = 0
    alpha = 0
    for byte in sample:
        if byte in (9, 10, 13) or 32 <= byte <= 126:
            printable += 1
            if 65 <= byte <= 90 or 97 <= byte <= 122:
                alpha += 1
    ratio = float(printable) / float(len(sample))
    return ratio >= 0.92 and alpha >= 8


def _extract_plaintext_bytes(file_bytes: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            decoded = file_bytes.decode(encoding)
        except Exception:
            continue
        cleaned = decoded.replace("\x00", "").strip()
        if cleaned:
            return cleaned
    return ""


def _normalize_ocr_input(
    file_bytes: bytes,
    filename: str,
    content_type: str,
    provider_name: Optional[str] = None,
) -> Dict[str, Any]:
    detected_mime = _detect_input_mime_type(file_bytes, filename, content_type)
    dpi = max(72, int(getattr(settings, "OCR_NORMALIZATION_DPI", 300) or 300))
    if not getattr(settings, "OCR_NORMALIZATION_SHIM_ENABLED", True):
        return {
            "content": file_bytes,
            "content_type": detected_mime,
            "original_content_type": detected_mime,
            "page_count": 1,
            "dpi": dpi,
            "error_code": None,
            "error": None,
        }

    if detected_mime == "application/pdf":
        page_count = 0
        try:
            from PyPDF2 import PdfReader  # type: ignore[reportMissingImports]

            page_count = len(PdfReader(BytesIO(file_bytes)).pages)
        except Exception:
            page_count = 0

        if (
            page_count and page_count > int(getattr(settings, "OCR_MAX_PAGES", 50) or 50)
        ) or len(file_bytes) > int(getattr(settings, "OCR_MAX_BYTES", 50 * 1024 * 1024) or (50 * 1024 * 1024)):
            return {
                "content": file_bytes,
                "content_type": detected_mime,
                "original_content_type": detected_mime,
                "page_count": page_count,
                "dpi": dpi,
                "error_code": None,
                "error": "normalization_guardrail_skip",
            }

        try:
            from pdf2image import convert_from_bytes  # type: ignore
            from PIL import ImageOps  # type: ignore

            rendered_pages = convert_from_bytes(file_bytes, dpi=dpi, fmt="png", thread_count=1)
            if not rendered_pages:
                raise ValueError("pdf_render_empty")
            normalized_pages = []
            for image in rendered_pages:
                normalized = ImageOps.exif_transpose(image)
                if normalized.mode != "RGB":
                    normalized = normalized.convert("RGB")
                normalized_pages.append(normalized)

            buffer = BytesIO()
            normalized_pages[0].save(
                buffer,
                format="TIFF",
                save_all=True,
                append_images=normalized_pages[1:],
                compression="tiff_deflate",
                dpi=(dpi, dpi),
            )
            return {
                "content": buffer.getvalue(),
                "content_type": "image/tiff",
                "original_content_type": detected_mime,
                "page_count": len(normalized_pages),
                "dpi": dpi,
                "provider": provider_name,
                "error_code": None,
                "error": None,
            }
        except Exception as exc:
            return {
                "content": file_bytes,
                "content_type": detected_mime,
                "original_content_type": detected_mime,
                "page_count": page_count or 1,
                "dpi": dpi,
                "provider": provider_name,
                "error_code": "OCR_UNSUPPORTED_FORMAT",
                "error": str(exc),
            }

    if detected_mime.startswith("image/"):
        try:
            from PIL import Image, ImageOps  # type: ignore

            image = Image.open(BytesIO(file_bytes))
            normalized = ImageOps.exif_transpose(image)
            if normalized.mode != "RGB":
                normalized = normalized.convert("RGB")

            buffer = BytesIO()
            normalized.save(buffer, format="PNG", dpi=(dpi, dpi))
            return {
                "content": buffer.getvalue(),
                "content_type": "image/png",
                "original_content_type": detected_mime,
                "page_count": 1,
                "dpi": dpi,
                "provider": provider_name,
                "error_code": None,
                "error": None,
            }
        except Exception as exc:
            return {
                "content": file_bytes,
                "content_type": detected_mime,
                "original_content_type": detected_mime,
                "page_count": 1,
                "dpi": dpi,
                "provider": provider_name,
                "error_code": "OCR_UNSUPPORTED_FORMAT",
                "error": str(exc),
            }

    return {
        "content": file_bytes,
        "content_type": detected_mime,
        "original_content_type": detected_mime,
        "page_count": 1,
        "dpi": dpi,
        "provider": provider_name,
        "error_code": "OCR_UNSUPPORTED_FORMAT",
        "error": "unsupported_input_mime",
    }


def _prepare_provider_ocr_payload(
    provider_name: str,
    file_bytes: bytes,
    filename: str,
    content_type: str,
) -> Dict[str, Any]:
    normalized_input = _normalize_ocr_input(file_bytes, filename, content_type, provider_name)
    original_mime = _detect_input_mime_type(file_bytes, filename, content_type)

    compat_enabled = _ocr_compatibility_v1_enabled()
    if not compat_enabled:
        normalized_input["bytes_sent"] = len(normalized_input.get("content") or b"")
        normalized_input["payload_source"] = "normalized"
        return normalized_input

    provider_key = str(provider_name or "").strip().lower()
    max_bytes_default = int(getattr(settings, "OCR_MAX_BYTES", 50 * 1024 * 1024) or (50 * 1024 * 1024))
    max_pages_default = int(getattr(settings, "OCR_MAX_PAGES", 50) or 50)
    preferences = {
        "google_documentai": {
            "preferred_pdf_mimes": ("image/tiff", "image/png", "application/pdf"),
            "supported_mimes": {"application/pdf", "image/png", "image/jpeg", "image/tiff"},
            "max_bytes": min(max_bytes_default, 20 * 1024 * 1024),
            "max_pages": max_pages_default,
        },
        "aws_textract": {
            "preferred_pdf_mimes": ("image/tiff", "application/pdf", "image/png"),
            "supported_mimes": {"application/pdf", "image/png", "image/jpeg", "image/tiff"},
            "max_bytes": min(max_bytes_default, 10 * 1024 * 1024),
            "max_pages": min(max_pages_default, 20),
        },
        "ocr_service": {
            "preferred_pdf_mimes": ("image/tiff", "image/png", "application/pdf"),
            "supported_mimes": {"application/pdf", "image/png", "image/jpeg", "image/tiff"},
            "max_bytes": min(max_bytes_default, 20 * 1024 * 1024),
            "max_pages": max_pages_default,
        },
        "deepseek_ocr": {
            "preferred_pdf_mimes": ("image/tiff", "image/png"),
            "supported_mimes": {"image/png", "image/jpeg", "image/tiff"},
            "max_bytes": min(max_bytes_default, 10 * 1024 * 1024),
            "max_pages": min(max_pages_default, 10),
        },
    }.get(
        provider_key,
        {
            "preferred_pdf_mimes": ("image/tiff", "image/png", "application/pdf"),
            "supported_mimes": {"application/pdf", "image/png", "image/jpeg", "image/tiff"},
            "max_bytes": max_bytes_default,
            "max_pages": max_pages_default,
        },
    )

    page_count = int(normalized_input.get("page_count") or 1)
    if page_count > int(preferences.get("max_pages") or max_pages_default):
        return {
            "content": b"",
            "content_type": normalized_input.get("content_type") or original_mime,
            "original_content_type": original_mime,
            "page_count": page_count,
            "dpi": normalized_input.get("dpi"),
            "provider": provider_name,
            "bytes_sent": 0,
            "payload_source": "guardrail_rejected",
            "error_code": "OCR_UNSUPPORTED_FORMAT",
            "error": f"page_limit_exceeded:{page_count}",
        }

    preferred_pdf_mimes = tuple(preferences.get("preferred_pdf_mimes") or ())
    supported_mimes = set(preferences.get("supported_mimes") or set())
    max_bytes = int(preferences.get("max_bytes") or max_bytes_default)

    candidates: List[Tuple[bytes, str, str]] = []
    if original_mime == "application/pdf":
        if normalized_input.get("error_code") is None:
            candidates.append(
                (
                    normalized_input.get("content") or b"",
                    str(normalized_input.get("content_type") or ""),
                    "normalized",
                )
            )
        elif "application/pdf" in supported_mimes:
            candidates.append((file_bytes, original_mime, "original"))
        candidates = sorted(
            candidates,
            key=lambda item: preferred_pdf_mimes.index(item[1])
            if item[1] in preferred_pdf_mimes
            else len(preferred_pdf_mimes),
        )
    elif normalized_input.get("error_code") is None:
        candidates.append(
            (
                normalized_input.get("content") or b"",
                str(normalized_input.get("content_type") or ""),
                "normalized",
            )
        )
        if original_mime != str(normalized_input.get("content_type") or ""):
            candidates.append((file_bytes, original_mime, "original"))
    else:
        candidates.append((file_bytes, original_mime, "original"))

    for content_bytes, payload_mime, payload_source in candidates:
        if payload_mime not in supported_mimes:
            continue
        if not content_bytes:
            continue
        if len(content_bytes) > max_bytes:
            continue
        return {
            "content": content_bytes,
            "content_type": payload_mime,
            "original_content_type": original_mime,
            "page_count": page_count,
            "dpi": normalized_input.get("dpi"),
            "provider": provider_name,
            "bytes_sent": len(content_bytes),
            "payload_source": payload_source,
            "error_code": None,
            "error": None,
        }

    return {
        "content": b"",
        "content_type": normalized_input.get("content_type") or original_mime,
        "original_content_type": original_mime,
        "page_count": page_count,
        "dpi": normalized_input.get("dpi"),
        "provider": provider_name,
        "bytes_sent": 0,
        "payload_source": "unsupported",
        "error_code": normalized_input.get("error_code") or "OCR_UNSUPPORTED_FORMAT",
        "error": normalized_input.get("error") or "provider_payload_incompatible",
    }


def _provider_runtime_limits(provider_name: str) -> Dict[str, Any]:
    provider_key = str(provider_name or "").strip().lower()
    max_pages_default = int(getattr(settings, "OCR_MAX_PAGES", 50) or 50)
    max_bytes_default = int(getattr(settings, "OCR_MAX_BYTES", 50 * 1024 * 1024) or (50 * 1024 * 1024))
    limits = {
        "google_documentai": {
            "supported_mimes": {"application/pdf", "image/png", "image/jpeg", "image/tiff"},
            "max_pages": max_pages_default,
            "max_bytes": min(max_bytes_default, 20 * 1024 * 1024),
        },
        "ocr_service": {
            "supported_mimes": {"application/pdf", "image/png", "image/jpeg", "image/tiff"},
            "max_pages": max_pages_default,
            "max_bytes": min(max_bytes_default, 20 * 1024 * 1024),
        },
        "aws_textract": {
            "supported_mimes": {"image/png", "image/jpeg"},
            "max_pages": min(max_pages_default, 15),
            "max_bytes": min(max_bytes_default, 5 * 1024 * 1024),
        },
    }
    return limits.get(
        provider_key,
        {
            "supported_mimes": {"application/pdf", "image/png", "image/jpeg", "image/tiff"},
            "max_pages": max_pages_default,
            "max_bytes": max_bytes_default,
        },
    )


def _pdf_page_count(file_bytes: bytes) -> int:
    try:
        from PyPDF2 import PdfReader  # type: ignore[reportMissingImports]

        return len(PdfReader(BytesIO(file_bytes)).pages)
    except Exception:
        return 0


def _render_pdf_runtime_images(
    file_bytes: bytes,
    *,
    dpi: int,
    output_format: str,
) -> List[bytes]:
    from pdf2image import convert_from_bytes  # type: ignore
    from PIL import ImageOps  # type: ignore

    fmt = output_format.upper()
    save_format = "JPEG" if fmt == "JPEG" else "PNG"
    rendered_pages = convert_from_bytes(file_bytes, dpi=dpi, fmt=save_format.lower(), thread_count=1)
    page_payloads: List[bytes] = []
    for image in rendered_pages:
        normalized = ImageOps.exif_transpose(image)
        if fmt == "JPEG":
            if normalized.mode != "RGB":
                normalized = normalized.convert("RGB")
        elif normalized.mode != "RGB":
            normalized = normalized.convert("RGB")
        buffer = BytesIO()
        save_kwargs: Dict[str, Any] = {"format": save_format, "dpi": (dpi, dpi)}
        if save_format == "JPEG":
            save_kwargs["quality"] = 90
        normalized.save(buffer, **save_kwargs)
        page_payloads.append(buffer.getvalue())
    return page_payloads


def _normalize_runtime_image_bytes(
    file_bytes: bytes,
    *,
    dpi: int,
    output_format: str,
) -> bytes:
    from PIL import Image, ImageOps  # type: ignore

    image = Image.open(BytesIO(file_bytes))
    normalized = ImageOps.exif_transpose(image)
    save_format = "JPEG" if output_format.upper() == "JPEG" else "PNG"
    if save_format == "JPEG":
        if normalized.mode != "RGB":
            normalized = normalized.convert("RGB")
    elif normalized.mode != "RGB":
        normalized = normalized.convert("RGB")
    buffer = BytesIO()
    save_kwargs: Dict[str, Any] = {"format": save_format, "dpi": (dpi, dpi)}
    if save_format == "JPEG":
        save_kwargs["quality"] = 90
    normalized.save(buffer, **save_kwargs)
    return buffer.getvalue()


def _build_runtime_payload_entry(
    *,
    provider_name: str,
    file_bytes: bytes,
    filename: str,
    input_mime: str,
    normalized_mime: str,
    page_count: int,
    bytes_sent: int,
    payload_source: str,
    retry_used: bool,
    dpi: Optional[int] = None,
    page_index: Optional[int] = None,
) -> Dict[str, Any]:
    return {
        "provider": provider_name,
        "content": file_bytes,
        "filename": filename,
        "content_type": normalized_mime,
        "input_mime": input_mime,
        "normalized_mime": normalized_mime,
        "page_count": int(page_count or 1),
        "page_index": int(page_index or 1),
        "dpi": dpi,
        "bytes_sent": int(bytes_sent),
        "payload_source": payload_source,
        "retry_used": bool(retry_used),
    }


def _build_google_docai_payload_plan(
    provider_name: str,
    file_bytes: bytes,
    filename: str,
    content_type: str,
) -> Dict[str, Any]:
    input_mime = _detect_input_mime_type(file_bytes, filename, content_type)
    limits = _provider_runtime_limits(provider_name)
    dpi = max(72, int(getattr(settings, "OCR_NORMALIZATION_DPI", 300) or 300))
    page_count = _pdf_page_count(file_bytes) if input_mime == "application/pdf" else 1

    if page_count and page_count > int(limits["max_pages"]):
        return {"groups": [], "aggregate_pages": False, "error_code": "OCR_UNSUPPORTED_FORMAT", "error": f"page_limit_exceeded:{page_count}"}
    if len(file_bytes) > int(limits["max_bytes"]):
        return {"groups": [], "aggregate_pages": False, "error_code": "OCR_UNSUPPORTED_FORMAT", "error": f"byte_limit_exceeded:{len(file_bytes)}"}

    groups: List[List[Dict[str, Any]]] = []
    if input_mime == "application/pdf":
        primary = _build_runtime_payload_entry(
            provider_name=provider_name,
            file_bytes=file_bytes,
            filename=filename,
            input_mime=input_mime,
            normalized_mime="application/pdf",
            page_count=max(1, page_count),
            bytes_sent=len(file_bytes),
            payload_source="runtime_pdf_direct",
            retry_used=False,
            dpi=dpi,
        )
        fallback_groups = [primary]
        try:
            normalized = _normalize_ocr_input(file_bytes, filename, content_type, provider_name)
            if normalized.get("error_code") is None and normalized.get("content"):
                fallback_groups.append(
                    _build_runtime_payload_entry(
                        provider_name=provider_name,
                        file_bytes=normalized.get("content") or b"",
                        filename=filename,
                        input_mime=input_mime,
                        normalized_mime=str(normalized.get("content_type") or "image/tiff"),
                        page_count=int(normalized.get("page_count") or page_count or 1),
                        bytes_sent=len(normalized.get("content") or b""),
                        payload_source="runtime_pdf_retry_image",
                        retry_used=True,
                        dpi=int(normalized.get("dpi") or dpi),
                    )
                )
        except Exception:
            pass
        groups.append(fallback_groups)
    elif input_mime.startswith("image/"):
        try:
            primary_bytes = _normalize_runtime_image_bytes(file_bytes, dpi=dpi, output_format="PNG")
            group = [
                _build_runtime_payload_entry(
                    provider_name=provider_name,
                    file_bytes=primary_bytes,
                    filename=filename,
                    input_mime=input_mime,
                    normalized_mime="image/png",
                    page_count=1,
                    bytes_sent=len(primary_bytes),
                    payload_source="runtime_image_png",
                    retry_used=False,
                    dpi=dpi,
                )
            ]
            if input_mime != "image/png":
                group.append(
                    _build_runtime_payload_entry(
                        provider_name=provider_name,
                        file_bytes=file_bytes,
                        filename=filename,
                        input_mime=input_mime,
                        normalized_mime=input_mime,
                        page_count=1,
                        bytes_sent=len(file_bytes),
                        payload_source="runtime_image_original",
                        retry_used=True,
                        dpi=dpi,
                    )
                )
            groups.append(group)
        except Exception as exc:
            return {"groups": [], "aggregate_pages": False, "error_code": "OCR_UNSUPPORTED_FORMAT", "error": str(exc)}
    else:
        return {"groups": [], "aggregate_pages": False, "error_code": "OCR_UNSUPPORTED_FORMAT", "error": "unsupported_input_mime"}

    return {"groups": groups, "aggregate_pages": False, "error_code": None, "error": None}


def _build_textract_payload_plan(
    provider_name: str,
    file_bytes: bytes,
    filename: str,
    content_type: str,
) -> Dict[str, Any]:
    input_mime = _detect_input_mime_type(file_bytes, filename, content_type)
    limits = _provider_runtime_limits(provider_name)
    dpi = max(72, int(getattr(settings, "OCR_NORMALIZATION_DPI", 300) or 300))

    groups: List[List[Dict[str, Any]]] = []
    try:
        if input_mime == "application/pdf":
            png_pages = _render_pdf_runtime_images(file_bytes, dpi=dpi, output_format="PNG")
            jpeg_pages = _render_pdf_runtime_images(file_bytes, dpi=dpi, output_format="JPEG")
            page_count = len(png_pages)
            if page_count > int(limits["max_pages"]):
                return {"groups": [], "aggregate_pages": True, "error_code": "OCR_UNSUPPORTED_FORMAT", "error": f"page_limit_exceeded:{page_count}"}
            for page_index, page_bytes in enumerate(png_pages, start=1):
                if len(page_bytes) > int(limits["max_bytes"]):
                    return {"groups": [], "aggregate_pages": True, "error_code": "OCR_UNSUPPORTED_FORMAT", "error": f"byte_limit_exceeded:{len(page_bytes)}"}
                group = [
                    _build_runtime_payload_entry(
                        provider_name=provider_name,
                        file_bytes=page_bytes,
                        filename=filename,
                        input_mime=input_mime,
                        normalized_mime="image/png",
                        page_count=page_count,
                        page_index=page_index,
                        bytes_sent=len(page_bytes),
                        payload_source="runtime_pdf_page_png",
                        retry_used=False,
                        dpi=dpi,
                    )
                ]
                if page_index <= len(jpeg_pages):
                    group.append(
                        _build_runtime_payload_entry(
                            provider_name=provider_name,
                            file_bytes=jpeg_pages[page_index - 1],
                            filename=filename,
                            input_mime=input_mime,
                            normalized_mime="image/jpeg",
                            page_count=page_count,
                            page_index=page_index,
                            bytes_sent=len(jpeg_pages[page_index - 1]),
                            payload_source="runtime_pdf_page_jpeg_retry",
                            retry_used=True,
                            dpi=dpi,
                        )
                    )
                groups.append(group)
        elif input_mime.startswith("image/"):
            png_bytes = _normalize_runtime_image_bytes(file_bytes, dpi=dpi, output_format="PNG")
            jpeg_bytes = _normalize_runtime_image_bytes(file_bytes, dpi=dpi, output_format="JPEG")
            groups.append(
                [
                    _build_runtime_payload_entry(
                        provider_name=provider_name,
                        file_bytes=png_bytes,
                        filename=filename,
                        input_mime=input_mime,
                        normalized_mime="image/png",
                        page_count=1,
                        bytes_sent=len(png_bytes),
                        payload_source="runtime_image_png",
                        retry_used=False,
                        dpi=dpi,
                    ),
                    _build_runtime_payload_entry(
                        provider_name=provider_name,
                        file_bytes=jpeg_bytes,
                        filename=filename,
                        input_mime=input_mime,
                        normalized_mime="image/jpeg",
                        page_count=1,
                        bytes_sent=len(jpeg_bytes),
                        payload_source="runtime_image_jpeg_retry",
                        retry_used=True,
                        dpi=dpi,
                    ),
                ]
            )
        else:
            return {"groups": [], "aggregate_pages": False, "error_code": "OCR_UNSUPPORTED_FORMAT", "error": "unsupported_input_mime"}
    except Exception as exc:
        return {"groups": [], "aggregate_pages": False, "error_code": "OCR_UNSUPPORTED_FORMAT", "error": str(exc)}

    return {"groups": groups, "aggregate_pages": True, "error_code": None, "error": None}


def _build_provider_runtime_payload_plan(
    provider_name: str,
    file_bytes: bytes,
    filename: str,
    content_type: str,
) -> Dict[str, Any]:
    if not _ocr_adapter_runtime_payload_fix_v1_enabled():
        payload = _prepare_provider_ocr_payload(provider_name, file_bytes, filename, content_type)
        if payload.get("error_code"):
            return {
                "groups": [],
                "aggregate_pages": False,
                "error_code": payload.get("error_code"),
                "error": payload.get("error"),
            }
        return {
            "groups": [[
                _build_runtime_payload_entry(
                    provider_name=provider_name,
                    file_bytes=payload.get("content") or b"",
                    filename=filename,
                    input_mime=str(payload.get("original_content_type") or payload.get("content_type") or content_type),
                    normalized_mime=str(payload.get("content_type") or content_type),
                    page_count=int(payload.get("page_count") or 1),
                    bytes_sent=int(payload.get("bytes_sent") or len(payload.get("content") or b"")),
                    payload_source=str(payload.get("payload_source") or "normalized"),
                    retry_used=False,
                    dpi=payload.get("dpi"),
                )
            ]],
            "aggregate_pages": False,
            "error_code": None,
            "error": None,
        }

    provider_key = str(provider_name or "").strip().lower()
    if provider_key in {"google_documentai", "ocr_service"}:
        return _build_google_docai_payload_plan(provider_name, file_bytes, filename, content_type)
    if provider_key == "aws_textract":
        return _build_textract_payload_plan(provider_name, file_bytes, filename, content_type)
    return _build_google_docai_payload_plan(provider_name, file_bytes, filename, content_type)


def _build_provider_attempt_record(
    *,
    stage: str,
    provider_name: str,
    payload: Dict[str, Any],
    text: str,
    status: str,
    error_code: Optional[str] = None,
    error: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "stage": stage,
        "provider": provider_name,
        "attempt_number": int(payload.get("attempt_number") or 1),
        "status": status,
        "text_len": len((text or "").strip()),
        "error_code": error_code,
        "error": error,
        "input_mime": payload.get("input_mime"),
        "normalized_mime": payload.get("normalized_mime"),
        "retry_used": bool(payload.get("retry_used")),
        "page_index": int(payload.get("page_index") or 1),
        "page_count": int(payload.get("page_count") or 1),
        "bytes_sent": int(payload.get("bytes_sent") or 0),
        "payload_source": payload.get("payload_source"),
    }


def _map_ocr_provider_error_code(error: Optional[str]) -> Optional[str]:
    if not error:
        return None
    lowered = str(error).strip().lower()
    if not lowered:
        return None
    if any(
        token in lowered
        for token in (
            "unsupported",
            "invalid mime",
            "content type",
            "content-type",
            "mime type",
            "bad format",
            "invalid document format",
            "unsupporteddocumentexception",
            "unsupported document",
            "unsupported file type",
            "format",
        )
    ):
        return "OCR_UNSUPPORTED_FORMAT"
    if any(
        token in lowered
        for token in (
            "empty_output",
            "empty output",
            "empty result",
            "empty_result",
            "no text",
            "no_ocr_provider_returned_text",
            "no text extracted",
            "no output",
            "blank document",
        )
    ):
        return "OCR_EMPTY_RESULT"
    if any(token in lowered for token in ("processor not found", "processor_not_found", "document ai processor not found")):
        return "OCR_PROCESSOR_NOT_FOUND"
    if "processor" in lowered and "not found" in lowered:
        return "OCR_PROCESSOR_NOT_FOUND"
    if any(
        token in lowered
        for token in (
            "permission denied",
            "forbidden",
            "access denied",
            "not authorized",
            "not allowed",
            "insufficient permissions",
            "status code 403",
        )
    ):
        return "OCR_PERMISSION_DENIED"
    if any(
        token in lowered
        for token in (
            "unauthenticated",
            "authentication failed",
            "auth failed",
            "auth failure",
            "invalid credentials",
            "invalid api key",
            "api key",
            "credential",
            "credentials",
            "expiredtoken",
            "signaturedoesnotmatch",
            "could not load default credentials",
            "status code 401",
        )
    ):
        return "OCR_AUTH_FAILURE"
    if any(
        token in lowered
        for token in (
            "timeout",
            "timed out",
            "deadline exceeded",
            "read timed out",
            "connect timeout",
            "request timeout",
        )
    ):
        return "OCR_TIMEOUT"
    if any(
        token in lowered
        for token in (
            "connection reset",
            "connection error",
            "connection refused",
            "connection aborted",
            "connection closed",
            "network",
            "dns",
            "temporary failure in name resolution",
            "name or service not known",
            "failed to establish a new connection",
            "service unavailable",
            "ssl",
            "tls",
            "unreachable",
            "proxyerror",
            "remote disconnected",
        )
    ):
        return "OCR_NETWORK_ERROR"
    return "OCR_UNKNOWN_PROVIDER_ERROR"


def _score_stage_candidate(stage: str, text: str, document_type: Optional[str]) -> Dict[str, Any]:
    stripped = str(text or "").strip()
    total_chars = len(stripped)
    non_space_chars = sum(1 for ch in stripped if not ch.isspace())
    alnum_chars = sum(1 for ch in stripped if ch.isalnum())
    target_chars = max(100, int(getattr(settings, "OCR_MIN_TEXT_CHARS_FOR_SKIP", 1200) or 1200))
    text_len_score = min(1.0, float(total_chars) / float(target_chars))
    alnum_ratio_score = min(1.0, float(alnum_chars) / float(max(1, non_space_chars)))

    critical_fields: List[str] = []
    stage_tuning: Dict[str, Any] = {}
    anchor_hit_score = 0.0
    try:
        from app.services.extraction_core.profiles import load_profile
        from app.services.validation.day1_retrieval_guard import evaluate_anchor_evidence

        if document_type:
            profile = load_profile(document_type) or {}
            critical_fields = list(profile.get("critical_fields") or [])
            stage_tuning = profile.get("stage_tuning") if isinstance(profile.get("stage_tuning"), dict) else {}
        anchor_checks = evaluate_anchor_evidence(stripped, min_score=0.0)
        relevant_anchor_scores = [
            anchor_checks[anchor_field].score
            for field_name in critical_fields
            for anchor_field in [_STAGE_CRITICAL_FIELD_TO_ANCHOR_FIELD.get(field_name)]
            if anchor_field and anchor_field in anchor_checks
        ]
        if relevant_anchor_scores:
            anchor_hit_score = sum(relevant_anchor_scores) / float(len(relevant_anchor_scores))
    except Exception:
        critical_fields = critical_fields or []
        anchor_hit_score = 0.0

    field_pattern_hits = 0
    field_pattern_total = 0
    for field_name in critical_fields:
        patterns = _STAGE_FIELD_PATTERNS.get(field_name) or []
        if not patterns:
            continue
        field_pattern_total += 1
        if any(re.search(pattern, stripped, re.IGNORECASE) for pattern in patterns):
            field_pattern_hits += 1
    field_pattern_score = (
        float(field_pattern_hits) / float(field_pattern_total)
        if field_pattern_total
        else 0.0
    )

    weights = {
        "text_len_score": float(getattr(settings, "OCR_STAGE_WEIGHT_TEXT_LEN", 0.30) or 0.30),
        "alnum_ratio_score": float(getattr(settings, "OCR_STAGE_WEIGHT_ALNUM_RATIO", 0.20) or 0.20),
        "anchor_hit_score": float(getattr(settings, "OCR_STAGE_WEIGHT_ANCHOR_HIT", 0.25) or 0.25),
        "field_pattern_score": float(getattr(settings, "OCR_STAGE_WEIGHT_FIELD_PATTERN", 0.25) or 0.25),
    }
    weight_total = sum(weights.values()) or 1.0
    overall_score = (
        (text_len_score * weights["text_len_score"])
        + (alnum_ratio_score * weights["alnum_ratio_score"])
        + (anchor_hit_score * weights["anchor_hit_score"])
        + (field_pattern_score * weights["field_pattern_score"])
    ) / weight_total

    target_field_hits = 0
    top3_anchor_hits = 0
    top3_numeric_hits = 0
    top3_quality_score = 0.0
    if document_type:
        try:
            from app.services.extraction_core.review_metadata import _preparse_document_fields

            parsed = _preparse_document_fields(stripped, document_type)
            top3_fields = [field_name for field_name in critical_fields if field_name in {"bin_tin", "gross_weight", "net_weight"}]
            target_field_hits = sum(
                1
                for field_name in ("bin_tin", "gross_weight", "net_weight")
                if getattr(parsed.get(field_name), "state", None) == "found"
            )
            top3_anchor_hits = sum(
                1
                for field_name in top3_fields
                if bool(getattr(parsed.get(field_name), "anchor_hit", False))
            )
            top3_numeric_hits = sum(
                1
                for field_name in top3_fields
                if getattr(parsed.get(field_name), "state", None) == "found"
                and getattr(parsed.get(field_name), "value_normalized", None) not in (None, "", [], {})
            )
            if top3_fields:
                numeric_weight = float(stage_tuning.get("top3_numeric_weight", 0.7) or 0.7)
                anchor_weight = float(stage_tuning.get("top3_anchor_weight", 0.3) or 0.3)
                weight_sum = max(0.1, numeric_weight + anchor_weight)
                top3_quality_score = min(
                    1.0,
                    (
                        (float(top3_numeric_hits) * numeric_weight)
                        + (float(top3_anchor_hits) * anchor_weight)
                    ) / (float(len(top3_fields)) * weight_sum),
                )
        except Exception:
            target_field_hits = 0
            top3_anchor_hits = 0
            top3_numeric_hits = 0
            top3_quality_score = 0.0

    source_preference_bonus = 0.0
    if stage != "binary_metadata_scrape" and (anchor_hit_score > 0 or field_pattern_score > 0):
        source_preference_bonus += 0.08
    if target_field_hits:
        source_preference_bonus += min(0.18, 0.06 * float(target_field_hits))
    if _stage_threshold_tuning_v1_enabled() and stage != "binary_metadata_scrape" and top3_quality_score > 0:
        source_preference_bonus += min(0.12, 0.10 * float(top3_quality_score))

    selection_score = overall_score + source_preference_bonus

    return {
        "stage": stage,
        "overall_score": round(overall_score, 6),
        "selection_score": round(selection_score, 6),
        "text_len_score": round(text_len_score, 6),
        "alnum_ratio_score": round(alnum_ratio_score, 6),
        "anchor_hit_score": round(anchor_hit_score, 6),
        "field_pattern_score": round(field_pattern_score, 6),
        "source_preference_bonus": round(source_preference_bonus, 6),
        "target_field_hits": int(target_field_hits),
        "top3_anchor_hits": int(top3_anchor_hits),
        "top3_numeric_hits": int(top3_numeric_hits),
        "top3_quality_score": round(top3_quality_score, 6),
        "text_length": total_chars,
    }


def _select_best_extraction_stage(
    stage_candidates: Dict[str, str],
    artifacts: Dict[str, Any],
    document_type: Optional[str],
) -> Optional[Dict[str, Any]]:
    if not stage_candidates:
        artifacts["stage_scores"] = {}
        artifacts["selected_stage"] = None
        artifacts["rejected_stages"] = {}
        return None

    profile: Dict[str, Any] = {}
    critical_fields: List[str] = []
    stage_tuning: Dict[str, Any] = {}
    if document_type:
        try:
            from app.services.extraction_core.profiles import load_profile

            profile = load_profile(document_type) or {}
            critical_fields = list(profile.get("critical_fields") or [])
            stage_tuning = profile.get("stage_tuning") if isinstance(profile.get("stage_tuning"), dict) else {}
        except Exception:
            profile = {}
            critical_fields = []
            stage_tuning = {}

    stage_scores = {
        stage: _score_stage_candidate(stage, text, document_type)
        for stage, text in stage_candidates.items()
    }
    priorities = list(getattr(settings, "OCR_STAGE_SELECTION_PRIORITY", []) or [])
    priority_index = {stage: index for index, stage in enumerate(priorities)}
    top3_fields = [field_name for field_name in critical_fields if field_name in {"bin_tin", "gross_weight", "net_weight"}]
    threshold_tuning_enabled = _stage_threshold_tuning_v1_enabled() and bool(top3_fields)
    binary_min_quality = float(stage_tuning.get("top3_binary_min_quality", 0.58) or 0.58)
    binary_min_target_hits = int(stage_tuning.get("top3_binary_min_target_hits", 1) or 1)
    promotion_min_quality = float(stage_tuning.get("top3_promotion_min_quality", 0.34) or 0.34)
    promotion_min_target_hits = int(stage_tuning.get("top3_promotion_min_target_hits", 1) or 1)

    selection_reason = "highest_selection_score"
    binary_penalty_applied = False
    binary_rejected_for_top3 = False
    promoted_from_stage: Optional[str] = None
    promotion_candidates: List[str] = []
    if _stage_promotion_v1_enabled() and "binary_metadata_scrape" in stage_scores:
        binary_score = stage_scores.get("binary_metadata_scrape") or {}
        binary_low_quality_for_top3 = bool(
            threshold_tuning_enabled
            and (
                float(binary_score.get("top3_quality_score", 0.0) or 0.0) < binary_min_quality
                or int(binary_score.get("target_field_hits", 0) or 0) < binary_min_target_hits
            )
        )
        promotion_candidates = [
            stage
            for stage, score in stage_scores.items()
            if stage != "binary_metadata_scrape"
            and (
                (
                    threshold_tuning_enabled
                    and (
                        int(score.get("target_field_hits", 0) or 0) >= promotion_min_target_hits
                        or (
                            float(score.get("top3_quality_score", 0.0) or 0.0) >= promotion_min_quality
                            and int(score.get("top3_anchor_hits", 0) or 0) > 0
                            and float(score.get("field_pattern_score", 0.0) or 0.0) > 0.0
                        )
                    )
                )
                or score.get("target_field_hits", 0) > 0
                or (
                    score.get("anchor_hit_score", 0.0) > 0
                    and score.get("field_pattern_score", 0.0) > 0
                )
            )
        ]
        if promotion_candidates:
            binary_penalty_applied = True
            binary_rejected_for_top3 = binary_low_quality_for_top3
            penalty = 0.38 if binary_low_quality_for_top3 else 0.24
            stage_scores["binary_metadata_scrape"]["binary_scrape_penalty"] = round(penalty, 6)
            stage_scores["binary_metadata_scrape"]["selection_score"] = round(
                stage_scores["binary_metadata_scrape"].get("selection_score", stage_scores["binary_metadata_scrape"].get("overall_score", 0.0)) - penalty,
                6,
            )
            selection_reason = "binary_scrape_rejected_low_top3_quality" if binary_low_quality_for_top3 else "binary_scrape_penalized"
        else:
            stage_scores["binary_metadata_scrape"]["binary_scrape_penalty"] = 0.0

    if getattr(settings, "OCR_STAGE_SCORER_ENABLED", True):
        ordered_candidates = sorted(
            stage_candidates.items(),
            key=lambda item: (
                stage_scores[item[0]].get("selection_score", stage_scores[item[0]].get("overall_score", 0.0)),
                -priority_index.get(item[0], len(priority_index)),
            ),
            reverse=True,
        )
    else:
        ordered_candidates = sorted(
            stage_candidates.items(),
            key=lambda item: priority_index.get(item[0], len(priority_index)),
        )

    selected_stage, selected_text = ordered_candidates[0]
    if (
        _stage_promotion_v1_enabled()
        and selected_stage == "binary_metadata_scrape"
        and promotion_candidates
    ):
        promoted_stage, _ = max(
            (
                (stage, stage_scores[stage])
                for stage in promotion_candidates
            ),
            key=lambda item: (
                item[1].get("target_field_hits", 0),
                item[1].get("anchor_hit_score", 0.0),
                item[1].get("field_pattern_score", 0.0),
                item[1].get("selection_score", item[1].get("overall_score", 0.0)),
                -priority_index.get(item[0], len(priority_index)),
            ),
        )
        promoted_from_stage = selected_stage
        selected_stage = promoted_stage
        selected_text = stage_candidates[promoted_stage]
        selection_reason = "binary_scrape_rejected_low_top3_quality" if binary_rejected_for_top3 else "anchor_promoted_over_binary_scrape"
    elif (
        _stage_promotion_v1_enabled()
        and binary_penalty_applied
        and selected_stage in promotion_candidates
    ):
        selection_reason = "binary_scrape_rejected_low_top3_quality" if binary_rejected_for_top3 else "anchor_promoted_over_binary_scrape"
    elif (
        threshold_tuning_enabled
        and selected_stage == "binary_metadata_scrape"
        and float(stage_scores[selected_stage].get("top3_quality_score", 0.0) or 0.0) < binary_min_quality
    ):
        selection_reason = "binary_scrape_only_available"

    selected_score = stage_scores[selected_stage].get("selection_score", stage_scores[selected_stage].get("overall_score", 0.0))
    rejected_stages = {}
    for stage, _text in ordered_candidates:
        if stage == selected_stage:
            continue
        rejected_stages[stage] = {
            "reason": (
                "lower_score"
                if stage_scores[stage].get("selection_score", stage_scores[stage].get("overall_score", 0.0)) < selected_score
                else "tie_break_priority"
            ),
            "score": stage_scores[stage].get("selection_score", stage_scores[stage].get("overall_score", 0.0)),
        }

    artifacts["stage_scores"] = stage_scores
    artifacts["selected_stage"] = selected_stage
    artifacts["rejected_stages"] = rejected_stages
    artifacts["stage_selection_rationale"] = {
        "selected_stage": selected_stage,
        "reason": selection_reason,
        "binary_scrape_penalty_applied": binary_penalty_applied,
        "binary_rejected_for_top3": binary_rejected_for_top3,
        "promoted_from_stage": promoted_from_stage,
        "promotion_candidates": promotion_candidates[:6],
        "binary_min_quality": round(binary_min_quality, 4),
        "binary_quality_score": round(float((stage_scores.get("binary_metadata_scrape") or {}).get("top3_quality_score", 0.0) or 0.0), 4),
        "selected_stage_quality_score": round(float(stage_scores[selected_stage].get("top3_quality_score", 0.0) or 0.0), 4),
    }
    return {"stage": selected_stage, "text": selected_text}


async def _extract_text_from_upload(upload_file: Any, document_type: Optional[str] = None) -> Dict[str, Any]:
    """Extract text + normalized OCR artifacts from an uploaded file."""
    filename = getattr(upload_file, "filename", "unknown")
    content_type = getattr(upload_file, "content_type", "unknown")
    hotfix_enabled = _extraction_fallback_hotfix_enabled()

    logger.log(TRACE_LOG_LEVEL, "Starting text extraction for %s (type=%s)", filename, content_type)

    try:
        file_bytes = await upload_file.read()
        await upload_file.seek(0)
        logger.info(f"✓ Read {len(file_bytes)} bytes from {filename}")
    except Exception as e:
        logger.error(f"✗ Failed to read file {filename}: {e}", exc_info=True)
        artifacts = _empty_extraction_artifacts_v1()
        _record_extraction_stage(
            artifacts,
            filename=filename,
            stage="read_upload",
            error="file_read_failed",
        )
        _record_extraction_reason_code(artifacts, "EXTRACTION_EMPTY_ALL_STAGES")
        return _finalize_text_extraction_result(artifacts, stage="read_upload", text="")

    if not file_bytes:
        logger.warning(f"⚠ Empty file content for {filename}")
        artifacts = _empty_extraction_artifacts_v1()
        _record_extraction_stage(
            artifacts,
            filename=filename,
            stage="read_upload",
            error="file_bytes_empty",
        )
        _record_extraction_reason_code(artifacts, "EXTRACTION_EMPTY_ALL_STAGES")
        return _finalize_text_extraction_result(artifacts, stage="read_upload", text="")

    artifacts = _empty_extraction_artifacts_v1()
    text_output = ""
    pypdf_text = ""
    stage_candidates: Dict[str, str] = {}
    detected_input_mime = _detect_input_mime_type(file_bytes, filename, content_type)

    def _choose_stage() -> Optional[Dict[str, Any]]:
        selector = globals().get("_select_best_extraction_stage")
        if callable(selector):
            return selector(stage_candidates, artifacts, document_type)
        if not stage_candidates:
            return None
        stage_name, stage_text = next(iter(stage_candidates.items()))
        artifacts["selected_stage"] = stage_name
        artifacts["stage_scores"] = artifacts.get("stage_scores") or {}
        artifacts["rejected_stages"] = artifacts.get("rejected_stages") or {}
        return {"stage": stage_name, "text": stage_text}

    min_chars_for_skip = max(1, int(getattr(settings, "OCR_MIN_TEXT_CHARS_FOR_SKIP", 1200) or 1200))

    if detected_input_mime == "text/plain":
        logger.info("validate.extraction.stage_entered file=%s stage=%s", filename, "plaintext_native")
        text_output = _extract_plaintext_bytes(file_bytes)
        _record_extraction_stage(artifacts, filename=filename, stage="plaintext_native", text=text_output)
    else:
        logger.info("validate.extraction.stage_entered file=%s stage=%s", filename, "pdfminer_native")
        try:
            from pdfminer.high_level import extract_text  # type: ignore
            text_output = extract_text(BytesIO(file_bytes))
            _record_extraction_stage(artifacts, filename=filename, stage="pdfminer_native", text=text_output)
        except Exception as exc:
            _record_extraction_stage(
                artifacts,
                filename=filename,
                stage="pdfminer_native",
                error=str(exc),
            )

        # Fallback plain-text extraction pass if pdfminer is empty/weak
        if len((text_output or "").strip()) < min_chars_for_skip:
            logger.info("validate.extraction.stage_entered file=%s stage=%s", filename, "pypdf_native")
            try:
                from PyPDF2 import PdfReader  # type: ignore[reportMissingImports]
                reader = PdfReader(BytesIO(file_bytes))
                pieces = []
                for page in reader.pages:
                    try:
                        pieces.append(page.extract_text() or "")
                    except Exception:
                        continue
                pypdf_text = "\n".join(pieces)
                _record_extraction_stage(artifacts, filename=filename, stage="pypdf_native", text=pypdf_text)
                if len((pypdf_text or "").strip()) > len((text_output or "").strip()):
                    text_output = pypdf_text
            except Exception as exc:
                _record_extraction_stage(
                    artifacts,
                    filename=filename,
                    stage="pypdf_native",
                    error=str(exc),
                )

    text_output_clean = (text_output or "").strip()
    if text_output_clean:
        stage_candidates["plaintext_native" if detected_input_mime == "text/plain" else "native_pdf_text"] = text_output

    # If direct PDF text is already rich enough, skip OCR provider calls.
    if len(text_output_clean) >= min_chars_for_skip:
        selection = _choose_stage()
        return _finalize_text_extraction_result(
            artifacts,
            stage=(selection or {}).get("stage") or ("plaintext_native" if detected_input_mime == "text/plain" else "native_pdf_text"),
            text=(selection or {}).get("text") or text_output,
        )

    if not text_output_clean:
        _record_extraction_reason_code(artifacts, "PARSER_EMPTY_OUTPUT")

    if not settings.OCR_ENABLED:
        if text_output_clean:
            selection = _choose_stage()
            return _finalize_text_extraction_result(
                artifacts,
                stage=(selection or {}).get("stage") or ("plaintext_native" if detected_input_mime == "text/plain" else "native_pdf_text"),
                text=(selection or {}).get("text") or text_output,
            )
        if hotfix_enabled:
            fallback_text = _scrape_binary_text_metadata(file_bytes)
            _record_extraction_stage(
                artifacts,
                filename=filename,
                stage="binary_metadata_scrape",
                text=fallback_text,
                fallback=True,
            )
            if (fallback_text or "").strip():
                _record_extraction_reason_code(artifacts, "FALLBACK_TEXT_RECOVERED")
                stage_candidates["binary_metadata_scrape"] = fallback_text
                selection = _choose_stage()
                return _finalize_text_extraction_result(
                    artifacts,
                    stage=(selection or {}).get("stage") or "binary_metadata_scrape",
                    text=(selection or {}).get("text") or fallback_text,
                )
        _record_extraction_reason_code(artifacts, "EXTRACTION_EMPTY_ALL_STAGES")
        return _finalize_text_extraction_result(
            artifacts,
            stage="plaintext_native" if detected_input_mime == "text/plain" else "native_pdf_text",
            text="",
        )

    if detected_input_mime == "text/plain":
        if text_output_clean:
            selection = _choose_stage()
            return _finalize_text_extraction_result(
                artifacts,
                stage=(selection or {}).get("stage") or "plaintext_native",
                text=(selection or {}).get("text") or text_output,
            )
        if hotfix_enabled:
            fallback_text = _scrape_binary_text_metadata(file_bytes)
            _record_extraction_stage(
                artifacts,
                filename=filename,
                stage="binary_metadata_scrape",
                text=fallback_text,
                fallback=True,
            )
            if (fallback_text or "").strip():
                _record_extraction_reason_code(artifacts, "FALLBACK_TEXT_RECOVERED")
                stage_candidates["binary_metadata_scrape"] = fallback_text
                selection = _choose_stage()
                return _finalize_text_extraction_result(
                    artifacts,
                    stage=(selection or {}).get("stage") or "binary_metadata_scrape",
                    text=(selection or {}).get("text") or fallback_text,
                )
        _record_extraction_reason_code(artifacts, "EXTRACTION_EMPTY_ALL_STAGES")
        return _finalize_text_extraction_result(artifacts, stage="plaintext_native", text="")

    page_count = 0
    try:
        from PyPDF2 import PdfReader  # type: ignore[reportMissingImports]
        page_count = len(PdfReader(BytesIO(file_bytes)).pages)
    except Exception:
        page_count = 1 if detected_input_mime.startswith("image/") else 0

    if page_count > settings.OCR_MAX_PAGES or len(file_bytes) > settings.OCR_MAX_BYTES:
        if text_output_clean:
            selection = _choose_stage()
            return _finalize_text_extraction_result(
                artifacts,
                stage=(selection or {}).get("stage") or "native_pdf_text",
                text=(selection or {}).get("text") or text_output,
            )
        if hotfix_enabled:
            fallback_text = _scrape_binary_text_metadata(file_bytes)
            _record_extraction_stage(
                artifacts,
                filename=filename,
                stage="binary_metadata_scrape",
                text=fallback_text,
                fallback=True,
            )
            if (fallback_text or "").strip():
                _record_extraction_reason_code(artifacts, "FALLBACK_TEXT_RECOVERED")
                stage_candidates["binary_metadata_scrape"] = fallback_text
                selection = _choose_stage()
                return _finalize_text_extraction_result(
                    artifacts,
                    stage=(selection or {}).get("stage") or "binary_metadata_scrape",
                    text=(selection or {}).get("text") or fallback_text,
                )
        _record_extraction_reason_code(artifacts, "EXTRACTION_EMPTY_ALL_STAGES")
        return _finalize_text_extraction_result(artifacts, stage="native_pdf_text", text="")

    ocr_result = await _try_ocr_providers(file_bytes, filename, content_type)
    ocr_text = ocr_result.get("text") or ""
    ocr_artifacts = ocr_result.get("artifacts") or _empty_extraction_artifacts_v1(raw_text=ocr_text)
    artifacts = _merge_extraction_artifacts(artifacts, ocr_artifacts)
    ocr_text_clean = (ocr_text or "").strip()

    _record_extraction_stage(
        artifacts,
        filename=filename,
        stage="ocr_provider_primary",
        text=ocr_text,
        error_code=ocr_artifacts.get("error_code") if not ocr_text_clean else None,
        error=ocr_artifacts.get("error") if not ocr_text_clean else None,
        fallback=not bool(text_output_clean),
    )

    merged_text = _merge_text_sources(text_output_clean, ocr_text_clean, pypdf_text)

    # If OCR is available, prefer merged evidence to maximize deterministic token recall.
    if ocr_text_clean:
        if not text_output_clean:
            _record_extraction_reason_code(artifacts, "FALLBACK_TEXT_RECOVERED")
        stage_candidates["ocr_provider_primary"] = merged_text or ocr_text
        selection = _choose_stage()
        return _finalize_text_extraction_result(
            artifacts,
            stage=(selection or {}).get("stage") or "ocr_provider_primary",
            text=(selection or {}).get("text") or (merged_text or ocr_text),
        )

    if hotfix_enabled:
        secondary_result = await _try_secondary_ocr_adapter(file_bytes, filename, content_type)
        secondary_text = secondary_result.get("text") or ""
        secondary_artifacts = secondary_result.get("artifacts") or _empty_extraction_artifacts_v1(raw_text=secondary_text)
        artifacts = _merge_extraction_artifacts(artifacts, secondary_artifacts)
        secondary_text_clean = (secondary_text or "").strip()

        _record_extraction_stage(
            artifacts,
            filename=filename,
            stage="ocr_secondary",
            text=secondary_text,
            error_code=secondary_artifacts.get("error_code") if not secondary_text_clean else None,
            error=secondary_artifacts.get("error") if not secondary_text_clean else None,
            fallback=True,
        )

        if secondary_text_clean:
            _record_extraction_reason_code(artifacts, "FALLBACK_TEXT_RECOVERED")
            stage_candidates["ocr_secondary"] = _merge_text_sources(text_output_clean, secondary_text_clean, ocr_text_clean)
            selection = _choose_stage()
            return _finalize_text_extraction_result(
                artifacts,
                stage=(selection or {}).get("stage") or "ocr_secondary",
                text=(selection or {}).get("text") or _merge_text_sources(text_output_clean, secondary_text_clean, ocr_text_clean),
            )

        binary_text = _scrape_binary_text_metadata(file_bytes)
        _record_extraction_stage(
            artifacts,
            filename=filename,
            stage="binary_metadata_scrape",
            text=binary_text,
            fallback=True,
        )
        if (binary_text or "").strip():
            _record_extraction_reason_code(artifacts, "FALLBACK_TEXT_RECOVERED")
            stage_candidates["binary_metadata_scrape"] = _merge_text_sources(text_output_clean, binary_text)
            selection = _choose_stage()
            return _finalize_text_extraction_result(
                artifacts,
                stage=(selection or {}).get("stage") or "binary_metadata_scrape",
                text=(selection or {}).get("text") or _merge_text_sources(text_output_clean, binary_text),
            )

    # No OCR available: return best extracted direct text.
    if text_output_clean:
        selection = _choose_stage()
        return _finalize_text_extraction_result(
            artifacts,
            stage=(selection or {}).get("stage") or "native_pdf_text",
            text=(selection or {}).get("text") or text_output,
        )

    _record_extraction_reason_code(
        artifacts,
        ocr_artifacts.get("error_code") or "OCR_PROVIDER_UNAVAILABLE",
    )
    _record_extraction_reason_code(artifacts, "EXTRACTION_EMPTY_ALL_STAGES")
    return _finalize_text_extraction_result(artifacts, stage="ocr_provider_primary", text="")


async def _try_secondary_ocr_adapter(file_bytes: bytes, filename: str, content_type: str) -> Dict[str, Any]:
    """Attempt a deterministic secondary OCR path that bypasses the factory adapter chain."""
    artifacts = _empty_extraction_artifacts_v1()
    provider_attempts: List[Dict[str, Any]] = []
    plan = _build_provider_runtime_payload_plan("ocr_service", file_bytes, filename, content_type)
    first_group = (plan.get("groups") or [[]])[0] if isinstance(plan.get("groups"), list) else []
    first_payload = first_group[0] if first_group else {}
    artifacts["normalization"] = {
        "original_mime": first_payload.get("input_mime"),
        "normalized_mime": first_payload.get("normalized_mime"),
        "page_count": first_payload.get("page_count"),
        "dpi": first_payload.get("dpi"),
        "bytes_sent": first_payload.get("bytes_sent"),
        "payload_source": first_payload.get("payload_source"),
    }

    record_runtime_failure = None
    record_runtime_success = None
    try:
        from app.services.ocr_diagnostics import record_ocr_runtime_failure, record_ocr_runtime_success
    except Exception:
        record_ocr_runtime_failure = None
        record_ocr_runtime_success = None

    def _record_runtime(
        *,
        provider_name: str,
        error_code: Optional[str],
        error_message: Optional[str],
        stage: str,
        attempt_number: int,
        payload: Dict[str, Any],
        success: bool = False,
    ) -> None:
        if success:
            if callable(record_runtime_success):
                try:
                    record_runtime_success(provider_name, stage=stage)
                except Exception:
                    return
            return
        if callable(record_runtime_failure) and error_code:
            try:
                record_runtime_failure(
                    provider_name,
                    error_code=error_code,
                    error_message=error_message,
                    stage=stage,
                    attempt_number=attempt_number,
                    normalized_mime=payload.get("normalized_mime"),
                    page_count=int(payload.get("page_count") or 1),
                    bytes_sent=int(payload.get("bytes_sent") or 0),
                )
            except Exception:
                return

    if plan.get("error_code"):
        artifacts["provider_attempts"] = [
            {
                "stage": "ocr_secondary",
                "provider": "ocr_service",
                "status": "guardrail_rejected",
                "text_len": 0,
                "error": plan.get("error"),
                "error_code": plan.get("error_code"),
                "input_mime": _detect_input_mime_type(file_bytes, filename, content_type),
                "normalized_mime": None,
                "retry_used": False,
                "page_index": 1,
                "page_count": 1,
                "bytes_sent": 0,
                "payload_source": "plan_error",
            }
        ]
        artifacts["error_code"] = plan.get("error_code")
        artifacts["error"] = plan.get("error")
        return {"text": "", "artifacts": artifacts}

    try:
        from app.services.ocr_service import get_ocr_service

        service = get_ocr_service()
        if not await service.health_check():
            first_attempt_number = len(provider_attempts) + 1
            unhealthy_payload = dict(first_payload)
            unhealthy_payload["attempt_number"] = first_attempt_number
            provider_attempts.append(
                _build_provider_attempt_record(
                    stage="ocr_secondary",
                    provider_name="ocr_service",
                    payload=unhealthy_payload,
                    text="",
                    status="unhealthy",
                    error_code="OCR_PROVIDER_UNAVAILABLE",
                    error="service_unhealthy",
                )
            )
            _record_runtime(
                provider_name="ocr_service",
                error_code="OCR_PROVIDER_UNAVAILABLE",
                error_message="service_unhealthy",
                stage="ocr_secondary",
                attempt_number=first_attempt_number,
                payload=unhealthy_payload,
            )
            artifacts["provider_attempts"] = provider_attempts
            artifacts["error_code"] = "OCR_PROVIDER_UNAVAILABLE"
            artifacts["error"] = "service_unhealthy"
            return {"text": "", "artifacts": artifacts}

        collected_texts: List[str] = []
        confidences: List[float] = []
        selected_payload = first_payload

        for group in plan.get("groups") or []:
            group_success = False
            for payload in group:
                attempt_number = len(provider_attempts) + 1
                payload = dict(payload)
                payload["attempt_number"] = attempt_number
                logger.info(
                    "validate.extraction.provider_input provider=%s attempt=%s original_mime=%s normalized_mime=%s page_count=%s dpi=%s bytes_sent=%s payload_source=%s retry_used=%s",
                    "ocr_service",
                    attempt_number,
                    payload.get("input_mime"),
                    payload.get("normalized_mime"),
                    payload.get("page_count"),
                    payload.get("dpi"),
                    payload.get("bytes_sent"),
                    payload.get("payload_source"),
                    payload.get("retry_used"),
                )
                result = await asyncio.wait_for(
                    service.extract_text(
                        payload.get("content") or file_bytes,
                        filename=payload.get("filename") or filename,
                        content_type=payload.get("normalized_mime") or content_type,
                    ),
                    timeout=settings.OCR_TIMEOUT_SEC,
                )
                text = result.get("text") or ""
                error = result.get("error")
                success = bool((text or "").strip()) and not error
                error_code = None if success else (result.get("error_code") or (_map_ocr_provider_error_code(error) if error else "OCR_EMPTY_RESULT"))
                provider_attempts.append(
                    _build_provider_attempt_record(
                        stage="ocr_secondary",
                        provider_name="ocr_service",
                        payload=payload,
                        text=text,
                        status="success" if success else "empty_output" if not error else "error",
                        error_code=error_code,
                        error=error,
                    )
                )
                logger.info(
                    "validate.extraction.provider_response provider=%s attempt=%s status=%s error_code=%s error=%s text_len=%s retry_used=%s",
                    "ocr_service",
                    attempt_number,
                    provider_attempts[-1]["status"],
                    error_code,
                    error,
                    provider_attempts[-1]["text_len"],
                    provider_attempts[-1]["retry_used"],
                )
                if success:
                    _record_runtime(
                        provider_name="ocr_service",
                        error_code=None,
                        error_message=None,
                        stage="ocr_secondary",
                        attempt_number=attempt_number,
                        payload=payload,
                        success=True,
                    )
                    selected_payload = payload
                    collected_texts.append(text)
                    confidence = result.get("confidence")
                    if isinstance(confidence, (int, float)):
                        confidences.append(float(confidence))
                    group_success = True
                    break
                logger.warning(
                    "validate.extraction.provider_failure provider=%s attempt=%s normalized_mime=%s page_count=%s bytes_sent=%s error_code=%s",
                    "ocr_service",
                    attempt_number,
                    payload.get("normalized_mime"),
                    payload.get("page_count"),
                    payload.get("bytes_sent"),
                    error_code,
                )
                _record_runtime(
                    provider_name="ocr_service",
                    error_code=error_code,
                    error_message=error,
                    stage="ocr_secondary",
                    attempt_number=attempt_number,
                    payload=payload,
                )
                should_retry_normalized_pdf = (
                    str(payload.get("payload_source") or "") == "runtime_pdf_direct"
                    and str(error_code or "") in {"OCR_UNSUPPORTED_FORMAT", "OCR_EMPTY_RESULT"}
                )
                if error_code != "OCR_UNSUPPORTED_FORMAT" and not should_retry_normalized_pdf:
                    break
            if group_success and not plan.get("aggregate_pages"):
                break
    except asyncio.TimeoutError as exc:
        timeout_attempt_number = len(provider_attempts) + 1
        timeout_payload = dict(first_payload)
        timeout_payload["attempt_number"] = timeout_attempt_number
        provider_attempts.append(
            _build_provider_attempt_record(
                stage="ocr_secondary",
                provider_name="ocr_service",
                payload=timeout_payload,
                text="",
                status="timeout",
                error_code="OCR_TIMEOUT",
                error="timeout",
            )
        )
        _record_runtime(
            provider_name="ocr_service",
            error_code="OCR_TIMEOUT",
            error_message=str(exc),
            stage="ocr_secondary",
            attempt_number=timeout_attempt_number,
            payload=timeout_payload,
        )
        artifacts["provider_attempts"] = provider_attempts
        artifacts["error_code"] = "OCR_TIMEOUT"
        artifacts["error"] = str(exc)
        return {"text": "", "artifacts": artifacts}
    except Exception as exc:
        error_attempt_number = len(provider_attempts) + 1
        error_payload = dict(first_payload)
        error_payload["attempt_number"] = error_attempt_number
        error_code = _map_ocr_provider_error_code(str(exc)) or "OCR_UNKNOWN_PROVIDER_ERROR"
        provider_attempts.append(
            _build_provider_attempt_record(
                stage="ocr_secondary",
                provider_name="ocr_service",
                payload=error_payload,
                text="",
                status="error",
                error_code=error_code,
                error=str(exc),
            )
        )
        _record_runtime(
            provider_name="ocr_service",
            error_code=error_code,
            error_message=str(exc),
            stage="ocr_secondary",
            attempt_number=error_attempt_number,
            payload=error_payload,
        )
        artifacts["provider_attempts"] = provider_attempts
        artifacts["error_code"] = error_code
        artifacts["error"] = str(exc)
        return {"text": "", "artifacts": artifacts}

    if collected_texts:
        merged_text = _merge_text_sources(*collected_texts)
        success_artifacts = _empty_extraction_artifacts_v1(
            raw_text=merged_text,
            ocr_confidence=(sum(confidences) / len(confidences)) if confidences else None,
        )
        success_artifacts["provider_attempts"] = provider_attempts
        success_artifacts["provider"] = "ocr_service"
        success_artifacts["normalization"] = {
            "original_mime": selected_payload.get("input_mime"),
            "normalized_mime": selected_payload.get("normalized_mime"),
            "page_count": selected_payload.get("page_count"),
            "dpi": selected_payload.get("dpi"),
            "bytes_sent": selected_payload.get("bytes_sent"),
            "payload_source": selected_payload.get("payload_source"),
        }
        return {"text": merged_text, "artifacts": success_artifacts}

    artifacts["provider_attempts"] = provider_attempts
    artifacts["error_code"] = next((attempt.get("error_code") for attempt in provider_attempts if attempt.get("error_code")), None) or "OCR_EMPTY_RESULT"
    artifacts["error"] = next((attempt.get("error") for attempt in provider_attempts if attempt.get("error")), None) or "secondary_ocr_empty_result"
    return {"text": "", "artifacts": artifacts}


async def _try_ocr_providers(file_bytes: bytes, filename: str, content_type: str) -> Dict[str, Any]:
    """Try OCR providers in configured order; return text + normalized artifacts."""
    from uuid import uuid4
    from app.ocr.factory import get_ocr_factory

    provider_map = {
        "gdocai": "google_documentai",
        "textract": "aws_textract",
    }
    provider_order = settings.OCR_PROVIDER_ORDER or ["gdocai", "textract"]
    attempts: List[Dict[str, Any]] = []
    record_runtime_failure = None
    record_runtime_success = None

    try:
        from app.services.ocr_diagnostics import record_ocr_runtime_failure, record_ocr_runtime_success
    except Exception:
        record_runtime_failure = None
        record_runtime_success = None

    def _record_runtime(
        *,
        provider_name: str,
        error_code: Optional[str],
        error_message: Optional[str],
        stage: str,
        attempt_number: int,
        payload: Dict[str, Any],
        success: bool = False,
    ) -> None:
        if success:
            if callable(record_runtime_success):
                try:
                    record_runtime_success(provider_name, stage=stage)
                except Exception:
                    return
            return
        if callable(record_runtime_failure) and error_code:
            try:
                record_runtime_failure(
                    provider_name,
                    error_code=error_code,
                    error_message=error_message,
                    stage=stage,
                    attempt_number=attempt_number,
                    normalized_mime=payload.get("normalized_mime"),
                    page_count=int(payload.get("page_count") or 1),
                    bytes_sent=int(payload.get("bytes_sent") or 0),
                )
            except Exception:
                return

    try:
        factory = get_ocr_factory()
        provider_order = list(getattr(factory, "configured_providers", None) or provider_order)
        all_adapters = factory.get_all_adapters()
        adapter_map = {adapter.provider_name: adapter for adapter in all_adapters}

        for provider_name in provider_order:
            full_provider_name = provider_map.get(provider_name, provider_name)
            adapter = adapter_map.get(full_provider_name)
            if not adapter:
                attempt_number = len(attempts) + 1
                attempts.append(
                    {
                        "stage": "ocr_provider_primary",
                        "provider": full_provider_name,
                        "attempt_number": attempt_number,
                        "status": "missing_adapter",
                        "text_len": 0,
                        "error": "missing_adapter",
                        "error_code": "OCR_PROVIDER_UNAVAILABLE",
                        "input_mime": _detect_input_mime_type(file_bytes, filename, content_type),
                        "normalized_mime": None,
                        "retry_used": False,
                        "page_index": 1,
                        "page_count": 1,
                        "bytes_sent": 0,
                        "payload_source": "missing_adapter",
                    }
                )
                _record_runtime(
                    provider_name=full_provider_name,
                    error_code="OCR_PROVIDER_UNAVAILABLE",
                    error_message="missing_adapter",
                    stage="ocr_provider_primary",
                    attempt_number=attempt_number,
                    payload={},
                )
                continue

            plan = _build_provider_runtime_payload_plan(full_provider_name, file_bytes, filename, content_type)
            first_group = (plan.get("groups") or [[]])[0] if isinstance(plan.get("groups"), list) else []
            first_payload = first_group[0] if first_group else {}
            if plan.get("error_code"):
                attempt_number = len(attempts) + 1
                attempts.append(
                    {
                        "stage": "ocr_provider_primary",
                        "provider": full_provider_name,
                        "attempt_number": attempt_number,
                        "status": "guardrail_rejected",
                        "text_len": 0,
                        "error": plan.get("error"),
                        "error_code": plan.get("error_code"),
                        "input_mime": _detect_input_mime_type(file_bytes, filename, content_type),
                        "normalized_mime": None,
                        "retry_used": False,
                        "page_index": 1,
                        "page_count": 1,
                        "bytes_sent": 0,
                        "payload_source": "plan_error",
                    }
                )
                continue

            try:
                if not await adapter.health_check():
                    unhealthy_attempt_number = len(attempts) + 1
                    unhealthy_payload = dict(first_payload)
                    unhealthy_payload["attempt_number"] = unhealthy_attempt_number
                    attempts.append(
                        _build_provider_attempt_record(
                            stage="ocr_provider_primary",
                            provider_name=full_provider_name,
                            payload=unhealthy_payload,
                            text="",
                            status="unhealthy",
                            error_code="OCR_PROVIDER_UNAVAILABLE",
                            error="provider_unhealthy",
                        )
                    )
                    _record_runtime(
                        provider_name=full_provider_name,
                        error_code="OCR_PROVIDER_UNAVAILABLE",
                        error_message="provider_unhealthy",
                        stage="ocr_provider_primary",
                        attempt_number=unhealthy_attempt_number,
                        payload=unhealthy_payload,
                    )
                    continue

                collected_texts: List[str] = []
                provider_results: List[Any] = []
                selected_payload = first_payload

                for group in plan.get("groups") or []:
                    group_success = False
                    for payload in group:
                        attempt_number = len(attempts) + 1
                        payload = dict(payload)
                        payload["attempt_number"] = attempt_number
                        logger.info(
                            "validate.extraction.provider_input provider=%s attempt=%s original_mime=%s normalized_mime=%s page_count=%s dpi=%s bytes_sent=%s payload_source=%s retry_used=%s",
                            full_provider_name,
                            attempt_number,
                            payload.get("input_mime"),
                            payload.get("normalized_mime"),
                            payload.get("page_count"),
                            payload.get("dpi"),
                            payload.get("bytes_sent"),
                            payload.get("payload_source"),
                            payload.get("retry_used"),
                        )
                        result = await asyncio.wait_for(
                            adapter.process_file_bytes(
                                payload.get("content") or file_bytes,
                                payload.get("filename") or filename,
                                payload.get("normalized_mime") or content_type,
                                uuid4(),
                            ),
                            timeout=settings.OCR_TIMEOUT_SEC,
                        )
                        text = getattr(result, "full_text", "") or ""
                        error_text = getattr(result, "error", None)
                        success = bool((text or "").strip()) and not error_text
                        error_code = None if success else (_map_ocr_provider_error_code(error_text) if error_text else "OCR_EMPTY_RESULT")
                        attempts.append(
                            _build_provider_attempt_record(
                                stage="ocr_provider_primary",
                                provider_name=full_provider_name,
                                payload=payload,
                                text=text,
                                status="success" if success else "empty_output" if not error_text else "error",
                                error_code=error_code,
                                error=error_text,
                            )
                        )
                        logger.info(
                            "validate.extraction.provider_response provider=%s attempt=%s status=%s error_code=%s error=%s text_len=%s retry_used=%s",
                            full_provider_name,
                            attempt_number,
                            attempts[-1]["status"],
                            error_code,
                            error_text,
                            attempts[-1]["text_len"],
                            attempts[-1]["retry_used"],
                        )
                        if success:
                            _record_runtime(
                                provider_name=full_provider_name,
                                error_code=None,
                                error_message=None,
                                stage="ocr_provider_primary",
                                attempt_number=attempt_number,
                                payload=payload,
                                success=True,
                            )
                            selected_payload = payload
                            collected_texts.append(text)
                            provider_results.append(result)
                            group_success = True
                            break
                        logger.warning(
                            "validate.extraction.provider_failure provider=%s attempt=%s normalized_mime=%s page_count=%s bytes_sent=%s error_code=%s",
                            full_provider_name,
                            attempt_number,
                            payload.get("normalized_mime"),
                            payload.get("page_count"),
                            payload.get("bytes_sent"),
                            error_code,
                        )
                        _record_runtime(
                            provider_name=full_provider_name,
                            error_code=error_code,
                            error_message=error_text,
                            stage="ocr_provider_primary",
                            attempt_number=attempt_number,
                            payload=payload,
                        )
                        should_retry_normalized_pdf = (
                            str(payload.get("payload_source") or "") == "runtime_pdf_direct"
                            and str(error_code or "") in {"OCR_UNSUPPORTED_FORMAT", "OCR_EMPTY_RESULT"}
                        )
                        if error_code != "OCR_UNSUPPORTED_FORMAT" and not should_retry_normalized_pdf:
                            break
                    if group_success and not plan.get("aggregate_pages"):
                        break

                if collected_texts:
                    merged_text = _merge_text_sources(*collected_texts)
                    confidence_values = [
                        float(result.overall_confidence)
                        for result in provider_results
                        if isinstance(getattr(result, "overall_confidence", None), (int, float))
                    ]
                    average_confidence = (
                        sum(confidence_values) / len(confidence_values)
                        if confidence_values
                        else None
                    )
                    artifacts = _build_extraction_artifacts_from_ocr(
                        raw_text=merged_text,
                        provider_result=provider_results[0] if provider_results else None,
                        ocr_confidence=average_confidence,
                    )
                    artifacts["provider_attempts"] = attempts
                    artifacts["provider"] = full_provider_name
                    artifacts["normalization"] = {
                        "original_mime": selected_payload.get("input_mime"),
                        "normalized_mime": selected_payload.get("normalized_mime"),
                        "page_count": selected_payload.get("page_count"),
                        "dpi": selected_payload.get("dpi"),
                        "bytes_sent": selected_payload.get("bytes_sent"),
                        "payload_source": selected_payload.get("payload_source"),
                    }
                    return {"text": merged_text, "artifacts": artifacts}
            except asyncio.TimeoutError as exc:
                timeout_attempt_number = len(attempts) + 1
                timeout_payload = dict(first_payload)
                timeout_payload["attempt_number"] = timeout_attempt_number
                attempts.append(
                    _build_provider_attempt_record(
                        stage="ocr_provider_primary",
                        provider_name=full_provider_name,
                        payload=timeout_payload,
                        text="",
                        status="timeout",
                        error_code="OCR_TIMEOUT",
                        error="timeout",
                    )
                )
                logger.warning(
                    "validate.extraction.provider_failure provider=%s attempt=%s normalized_mime=%s page_count=%s bytes_sent=%s error_code=%s",
                    full_provider_name,
                    timeout_attempt_number,
                    timeout_payload.get("normalized_mime"),
                    timeout_payload.get("page_count"),
                    timeout_payload.get("bytes_sent"),
                    "OCR_TIMEOUT",
                )
                _record_runtime(
                    provider_name=full_provider_name,
                    error_code="OCR_TIMEOUT",
                    error_message=str(exc),
                    stage="ocr_provider_primary",
                    attempt_number=timeout_attempt_number,
                    payload=timeout_payload,
                )
                continue
            except Exception as exc:
                error_attempt_number = len(attempts) + 1
                error_payload = dict(first_payload)
                error_payload["attempt_number"] = error_attempt_number
                error_code = _map_ocr_provider_error_code(str(exc)) or "OCR_UNKNOWN_PROVIDER_ERROR"
                attempts.append(
                    _build_provider_attempt_record(
                        stage="ocr_provider_primary",
                        provider_name=full_provider_name,
                        payload=error_payload,
                        text="",
                        status="error",
                        error_code=error_code,
                        error=str(exc),
                    )
                )
                logger.warning(
                    "validate.extraction.provider_failure provider=%s attempt=%s normalized_mime=%s page_count=%s bytes_sent=%s error_code=%s",
                    full_provider_name,
                    error_attempt_number,
                    error_payload.get("normalized_mime"),
                    error_payload.get("page_count"),
                    error_payload.get("bytes_sent"),
                    error_code,
                )
                _record_runtime(
                    provider_name=full_provider_name,
                    error_code=error_code,
                    error_message=str(exc),
                    stage="ocr_provider_primary",
                    attempt_number=error_attempt_number,
                    payload=error_payload,
                )
                continue

        artifacts = _empty_extraction_artifacts_v1()
        artifacts["provider_attempts"] = attempts
        last_plan = _build_provider_runtime_payload_plan(provider_map.get(provider_order[0], provider_order[0]), file_bytes, filename, content_type)
        last_group = (last_plan.get("groups") or [[]])[0] if isinstance(last_plan.get("groups"), list) else []
        last_input = last_group[0] if last_group else {}
        artifacts["normalization"] = {
            "original_mime": last_input.get("input_mime"),
            "normalized_mime": last_input.get("normalized_mime"),
            "page_count": last_input.get("page_count"),
            "dpi": last_input.get("dpi"),
            "bytes_sent": last_input.get("bytes_sent"),
            "payload_source": last_input.get("payload_source"),
        }
        attempt_error_code = next(
            (attempt.get("error_code") for attempt in attempts if attempt.get("error_code")),
            None,
        )
        artifacts["error_code"] = attempt_error_code or "OCR_EMPTY_RESULT"
        artifacts["error"] = "no_ocr_provider_returned_text"
        return {"text": "", "artifacts": artifacts}
    except Exception as exc:
        artifacts = _empty_extraction_artifacts_v1()
        artifacts["provider_attempts"] = attempts
        fallback_plan = _build_provider_runtime_payload_plan(provider_map.get(provider_order[0], provider_order[0]), file_bytes, filename, content_type)
        fallback_group = (fallback_plan.get("groups") or [[]])[0] if isinstance(fallback_plan.get("groups"), list) else []
        fallback_input = fallback_group[0] if fallback_group else {}
        artifacts["normalization"] = {
            "original_mime": fallback_input.get("input_mime"),
            "normalized_mime": fallback_input.get("normalized_mime"),
            "page_count": fallback_input.get("page_count"),
            "dpi": fallback_input.get("dpi"),
            "bytes_sent": fallback_input.get("bytes_sent"),
            "payload_source": fallback_input.get("payload_source"),
        }
        artifacts["error_code"] = _map_ocr_provider_error_code(str(exc)) or "OCR_UNKNOWN_PROVIDER_ERROR"
        artifacts["error"] = str(exc)
        return {"text": "", "artifacts": artifacts}


def _severity_rank(severity: Optional[str]) -> int:
    order = {
        "critical": 3,
        "error": 3,
        "major": 2,
        "warning": 2,
        "warn": 2,
        "minor": 1,
    }
    if not severity:
        return 0
    return order.get(severity.lower(), 1)


def _severity_to_status(severity: Optional[str]) -> str:
    if not severity:
        return "success"
    normalized = severity.lower()
    if normalized in {"critical", "error"}:
        return "error"
    if normalized in {"major", "warning", "warn", "minor"}:
        return "warning"
    return "success"


def _build_blocked_structured_result(
    v2_gate_result,
    v2_baseline: LCBaseline,
    lc_type: str,
    processing_duration: float,
    documents: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Build a structured_result for blocked validation.
    
    This is returned when the validation gate blocks (missing LC, critical fields missing).
    The response is HTTP 200 with validation_blocked=true.
    """
    # Build blocking issues
    blocking_issues = []
    for issue in v2_gate_result.blocking_issues:
        if isinstance(issue, dict):
            blocking_issues.append(issue)
        elif hasattr(issue, 'to_dict'):
            blocking_issues.append(issue.to_dict())
    
    # Build document list - PRESERVE extraction data even when validation is blocked
    # The extraction succeeded, we're blocking validation due to missing LC fields
    # Don't throw away the extraction work!
    docs_structured = []
    for i, doc in enumerate(documents):
        # Preserve actual extraction status and fields
        actual_extraction_status = doc.get("extraction_status") or "unknown"
        actual_extracted_fields = doc.get("extracted_fields") or {}
        
        empty_artifacts_builder = globals().get("_empty_extraction_artifacts_v1")
        fallback_artifacts = (
            empty_artifacts_builder(
                raw_text=doc.get("raw_text") or doc.get("raw_text_preview") or "",
                ocr_confidence=doc.get("ocr_confidence"),
            )
            if callable(empty_artifacts_builder)
            else {
                "ocr": {},
                "parsing": {},
                "normalization": {},
                "raw_text": doc.get("raw_text") or doc.get("raw_text_preview") or "",
                "ocr_confidence": doc.get("ocr_confidence"),
            }
        )

        docs_structured.append({
            "document_id": doc.get("id") or str(uuid4()),
            "filename": doc.get("filename") or doc.get("name") or f"Document {i+1}",
            "document_type": doc.get("document_type") or "supporting_document",
            "extraction_status": actual_extraction_status,  # Keep real status
            "extracted_fields": actual_extracted_fields,    # Keep real data
            "issues_count": 0,
            "raw_text_preview": doc.get("raw_text_preview"),  # Keep preview text
            "ocr_confidence": doc.get("ocr_confidence"),
            "review_required": bool(doc.get("review_required") or doc.get("reviewRequired")),
            "review_reasons": doc.get("review_reasons") or doc.get("reviewReasons") or [],
            "critical_field_states": doc.get("critical_field_states") or doc.get("criticalFieldStates") or {},
            "extraction_artifacts_v1": doc.get("extraction_artifacts_v1") or fallback_artifacts,
        })
    
    # Processing time display
    if processing_duration < 1:
        time_display = f"{int(processing_duration * 1000)}ms"
    else:
        time_display = f"{processing_duration:.1f}s"
    
    processing_summary = {
        "total_documents": len(documents),
        "successful_extractions": sum(1 for d in documents if d.get("extraction_status") == "success"),
        "failed_extractions": sum(1 for d in documents if d.get("extraction_status") in ("failed", "error", "empty")),
        "partial_extractions": sum(
            1 for d in documents if d.get("extraction_status") in ("text_only", "partial", "parse_failed")
        ),
        "total_issues": len(blocking_issues),
        "compliance_rate": 0,  # 0 because validation is blocked
        "processing_time_seconds": round(processing_duration, 2),
        "processing_time_display": time_display,
        "severity_breakdown": {
            "critical": len(blocking_issues),
            "major": 0,
            "medium": 0,
            "minor": 0,
        },
    }

    _response_shaping.attach_extraction_observability(docs_structured)
    document_extraction = _build_document_extraction_v1(docs_structured)
    processing_summary_v2 = _build_processing_summary_v2(
        processing_summary,
        document_extraction.get("documents", []),
        blocking_issues,
        compliance_rate=0,
    )

    gate_dict = v2_gate_result.to_dict()
    eligibility_context = _build_submission_eligibility_context(gate_dict, {})
    unresolved_critical_fields = [
        {
            "field": field,
            "status": "rejected",
            "reason_code": "unknown",
        }
        for field in (v2_gate_result.missing_critical or [])
    ]

    result = {
        "version": "structured_result_v1",
        
        # V2 blocked status
        "validation_blocked": True,
        "validation_status": "blocked",
        "submission_eligibility": {
            "can_submit": False,
            "reasons": ["validation_blocked"],
            "missing_reason_codes": eligibility_context["missing_reason_codes"],
            "unresolved_critical_fields": unresolved_critical_fields,
            "unresolved_critical_statuses": ["rejected"] if unresolved_critical_fields else [],
            "source": "validation",
        },
        
        # Gate result
        "gate_result": gate_dict,
        
        # Extraction summary
        "extraction_summary": {
            "completeness": round(v2_gate_result.completeness * 100, 1),
            "critical_completeness": round(v2_gate_result.critical_completeness * 100, 1),
            "missing_critical": v2_gate_result.missing_critical,
            "missing_required": v2_gate_result.missing_required,
        },
        
        # LC baseline (partial data)
        "lc_baseline": {
            "lc_number": v2_baseline.lc_number.value if v2_baseline else None,
            "amount": v2_baseline.amount.value if v2_baseline else None,
            "currency": v2_baseline.currency.value if v2_baseline else None,
            "applicant": v2_baseline.applicant.value if v2_baseline else None,
            "beneficiary": v2_baseline.beneficiary.value if v2_baseline else None,
            "extraction_completeness": round(v2_baseline.extraction_completeness * 100, 1) if v2_baseline else 0,
            "critical_completeness": round(v2_baseline.critical_completeness * 100, 1) if v2_baseline else 0,
        },
        
        # Issues (blocking issues)
        "issues": blocking_issues,
        
        # Documents
        "documents_structured": docs_structured,
        
        # Processing summary - count ACTUAL extraction results
        "processing_summary": processing_summary,
        "processing_summary_v2": processing_summary_v2,
        "document_extraction_v1": document_extraction,
        "issue_provenance_v1": _build_issue_provenance_v1(blocking_issues),
        
        # Analytics
        "analytics": {
            "extraction_accuracy": round(v2_gate_result.completeness * 100) if v2_gate_result else 0,
            "lc_compliance_score": 0,
            "compliance_level": "blocked",
            "compliance_cap_reason": v2_gate_result.block_reason,
            "customs_ready_score": 0,
            "documents_processed": len(documents),
            "issue_counts": {
                "critical": len(blocking_issues),
                "major": 0,
                "medium": 0,
                "minor": 0,
            },
            "document_risk": [],
        },
        
        # Timeline
        "timeline": [
            {
                "title": "Documents Uploaded",
                "status": "completed",
                "description": f"{len(documents)} documents received",
            },
            {
                "title": "LC Extraction",
                "status": "error",
                "description": v2_gate_result.block_reason or "Extraction failed",
            },
            {
                "title": "Validation",
                "status": "blocked",
                "description": "Validation blocked due to missing LC data",
            },
        ],
        
        # LC structured (minimal)
        "lc_structured": {
            "mt700": {"blocks": {}, "raw_text": None, "version": "mt700_v1"},
            "goods": [],
            "clauses": [],
            "timeline": [],
        },
        
        # Type info
        "lc_type": lc_type,
        "lc_type_reason": "Blocked - LC extraction incomplete",
        "lc_type_confidence": 0,
        
        # Customs (empty)
        "customs_pack": None,
        "ai_enrichment": None,
    }

    extraction_core_bundle = _build_extraction_core_bundle(documents)
    if isinstance(extraction_core_bundle, dict):
        result["_extraction_core_v1"] = extraction_core_bundle
    extraction_diagnostics = _response_shaping.build_extraction_diagnostics(
        docs_structured,
        extraction_core_bundle if isinstance(extraction_core_bundle, dict) else None,
    )
    if isinstance(extraction_diagnostics, dict):
        result["_extraction_diagnostics"] = extraction_diagnostics

    return result



def _build_lc_baseline_from_context(lc_context: Dict[str, Any]) -> LCBaseline:
    """
    Build LCBaseline from extracted LC context.
    
    This is the bridge between the legacy extraction and the v2 validation pipeline.
    Supports both flat lc_context fields and nested mt700 blocks.
    """
    from app.services.extraction.lc_baseline import (
        LCBaseline, FieldResult, FieldPriority, ExtractionStatus,
        PartyInfo, AmountInfo, PortInfo,
    )
    
    baseline = LCBaseline()
    
    # Extract MT700 blocks if present
    mt700 = lc_context.get("mt700", {})
    blocks = mt700.get("blocks", {}) if isinstance(mt700, dict) else {}

    raw_text = lc_context.get("raw_text") or (lc_context.get("lc_structured") or {}).get("raw_text") or ""
    evidence_map = (
        lc_context.get("field_evidence")
        or lc_context.get("_field_evidence")
        or lc_context.get("evidence")
        or (lc_context.get("lc_structured") or {}).get("field_evidence")
        or (lc_context.get("lc_structured") or {}).get("_field_evidence")
        or (lc_context.get("lc_structured") or {}).get("evidence")
        or {}
    )
    
    # Helper to apply evidence map
    def _apply_evidence(field_result: FieldResult, evidence: Any) -> None:
        if not evidence:
            return
        if isinstance(evidence, str):
            field_result.evidence_text = evidence
            return
        if isinstance(evidence, dict):
            field_result.evidence_text = (
                evidence.get("text")
                or evidence.get("snippet")
                or evidence.get("raw")
                or evidence.get("value")
            )
            field_result.evidence_page = evidence.get("page")
            field_result.evidence_location = (
                evidence.get("location")
                or evidence.get("bbox")
                or evidence.get("span")
            )

    def _extract_snippet(value: Any) -> Optional[str]:
        if not raw_text:
            return None
        if value is None:
            return None
        value_str = str(value).strip()
        if not value_str:
            return None
        lowered = raw_text.lower()
        idx = lowered.find(value_str.lower())
        if idx == -1:
            return None
        window = 60
        start = max(0, idx - window)
        end = min(len(raw_text), idx + len(value_str) + window)
        return raw_text[start:end].strip()

    def _get_evidence(field_key: str, *fallback_keys: str) -> Any:
        for key in (field_key, *fallback_keys):
            if key in evidence_map:
                return evidence_map.get(key)
        return None
    
    # Helper to set field with proper status
    def set_field(
        field_result: FieldResult,
        value: Any,
        confidence: float = 0.8,
        source: str = "context",
        evidence: Any = None,
    ):
        if value is not None and value != "" and value != {}:
            field_result.value = value
            field_result.status = ExtractionStatus.EXTRACTED
            field_result.confidence = confidence
            field_result.source = source
            _apply_evidence(field_result, evidence)
            if field_result.priority == FieldPriority.CRITICAL and not field_result.evidence_text:
                snippet = _extract_snippet(value)
                if snippet:
                    field_result.evidence_text = snippet
        else:
            field_result.status = ExtractionStatus.MISSING
            field_result.confidence = 0.0
    
    # Helper to get value from multiple keys
    def get_value(*keys, from_blocks=False):
        for key in keys:
            if from_blocks and key in blocks:
                return blocks[key]
            if key in lc_context:
                val = lc_context[key]
                if val is not None and val != "":
                    return val
        return None
    
    # =====================================================================
    # LC Number (MT700 Field 20)
    # =====================================================================
    lc_number = get_value("number", "lc_number", "documentaryCredit", "doc_credit_number")
    if not lc_number:
        lc_number = blocks.get("20")  # MT700 field 20
    set_field(
        baseline.lc_number,
        lc_number,
        evidence=_get_evidence("lc_number", "number", "20")
    )
    
    # =====================================================================
    # LC Type
    # =====================================================================
    lc_type = get_value("lc_type", "form_of_doc_credit", "type")
    if not lc_type:
        lc_type = blocks.get("40A")  # MT700 field 40A - Form of Documentary Credit
    set_field(baseline.lc_type, lc_type)
    
    # =====================================================================
    # Amount (MT700 Field 32B)
    # =====================================================================
    amount_raw = get_value("amount", "credit_amount", "value")
    currency = get_value("currency", "ccy")
    
    if not amount_raw and blocks.get("32B"):
        # Parse MT700 32B: "USD100000.00"
        field_32b = blocks["32B"]
        if isinstance(field_32b, str) and len(field_32b) >= 3:
            currency = field_32b[:3]
            try:
                amount_raw = float(field_32b[3:].replace(",", ""))
            except ValueError:
                amount_raw = field_32b[3:]
    
    # Parse amount value
    amount_value = None
    if amount_raw:
        if isinstance(amount_raw, dict):
            amount_value = amount_raw.get("value")
            if not currency:
                currency = amount_raw.get("currency")
        elif isinstance(amount_raw, (int, float)):
            amount_value = float(amount_raw)
        elif isinstance(amount_raw, str):
            try:
                amount_value = float(amount_raw.replace(",", ""))
            except ValueError:
                pass
    
    set_field(
        baseline.amount,
        amount_value,
        evidence=_get_evidence("amount", "lc_amount", "32B_amount", "32B")
    )
    
    # Currency field
    set_field(
        baseline.currency,
        currency,
        evidence=_get_evidence("currency", "32B_currency", "ccy")
    )
    
    # Store structured amount info
    if amount_value is not None or currency:
        baseline._amount_info = AmountInfo(value=amount_value, currency=currency)
    
    # =====================================================================
    # Applicant (MT700 Field 50)
    # =====================================================================
    applicant = get_value("applicant", "applicant_name", "buyer")
    if not applicant:
        applicant = blocks.get("50")  # MT700 field 50
    
    if applicant:
        if isinstance(applicant, dict):
            baseline._applicant_info = PartyInfo(
                name=applicant.get("name"),
                address=applicant.get("address"),
                country=applicant.get("country"),
            )
            applicant = applicant.get("name")
        elif isinstance(applicant, str):
            baseline._applicant_info = PartyInfo(name=applicant)
    set_field(
        baseline.applicant,
        applicant,
        evidence=_get_evidence("applicant", "applicant_name", "50")
    )
    
    # =====================================================================
    # Beneficiary (MT700 Field 59)
    # =====================================================================
    beneficiary = get_value("beneficiary", "beneficiary_name", "seller")
    if not beneficiary:
        beneficiary = blocks.get("59")  # MT700 field 59
    
    if beneficiary:
        if isinstance(beneficiary, dict):
            baseline._beneficiary_info = PartyInfo(
                name=beneficiary.get("name"),
                address=beneficiary.get("address"),
                country=beneficiary.get("country"),
            )
            beneficiary = beneficiary.get("name")
        elif isinstance(beneficiary, str):
            baseline._beneficiary_info = PartyInfo(name=beneficiary)
    set_field(
        baseline.beneficiary,
        beneficiary,
        evidence=_get_evidence("beneficiary", "beneficiary_name", "59")
    )
    
    # =====================================================================
    # Banks
    # =====================================================================
    issuing_bank = get_value("issuing_bank", "issuer", "issuing_bank_name")
    if not issuing_bank:
        issuing_bank = blocks.get("52A") or blocks.get("52D")  # MT700 field 52
    set_field(baseline.issuing_bank, issuing_bank)
    
    advising_bank = get_value("advising_bank", "advising_bank_name")
    if not advising_bank:
        advising_bank = blocks.get("57A") or blocks.get("57D")  # MT700 field 57
    set_field(baseline.advising_bank, advising_bank)
    
    # =====================================================================
    # Dates (MT700 Fields 31C, 31D, 44C)
    # Also check nested "dates" structure from legacy fallback extraction
    # =====================================================================
    dates_nested = lc_context.get("dates") or {}
    
    issue_date = get_value("issue_date", "date_of_issue")
    if not issue_date:
        issue_date = blocks.get("31C")  # MT700 field 31C - Date of Issue
    if not issue_date:
        issue_date = dates_nested.get("issue")  # Legacy fallback: dates.issue
    set_field(baseline.issue_date, issue_date)
    
    expiry_date = get_value("expiry_date", "expiry", "validity_date")
    if not expiry_date:
        expiry_date = blocks.get("31D")  # MT700 field 31D - Date and Place of Expiry
    if not expiry_date:
        expiry_date = dates_nested.get("expiry")  # Legacy fallback: dates.expiry
    set_field(baseline.expiry_date, expiry_date)
    
    latest_shipment = get_value("latest_shipment", "latest_shipment_date", "shipment_date")
    if not latest_shipment:
        latest_shipment = blocks.get("44C")  # MT700 field 44C - Latest Date of Shipment
    if not latest_shipment:
        latest_shipment = dates_nested.get("latest_shipment")  # Legacy fallback: dates.latest_shipment
    set_field(baseline.latest_shipment, latest_shipment)
    
    # =====================================================================
    # Ports (MT700 Fields 44E, 44F)
    # =====================================================================
    port_of_loading = get_value("port_of_loading", "loading_port", "pol")
    if not port_of_loading:
        port_of_loading = blocks.get("44E")  # MT700 field 44E - Port of Loading
    
    if port_of_loading:
        if isinstance(port_of_loading, dict):
            baseline._port_of_loading_info = PortInfo(
                name=port_of_loading.get("name") or port_of_loading.get("port"),
                country=port_of_loading.get("country"),
            )
            port_of_loading = baseline._port_of_loading_info.name
        elif isinstance(port_of_loading, str):
            baseline._port_of_loading_info = PortInfo(name=port_of_loading)
    set_field(baseline.port_of_loading, port_of_loading)
    
    port_of_discharge = get_value("port_of_discharge", "discharge_port", "pod")
    if not port_of_discharge:
        port_of_discharge = blocks.get("44F")  # MT700 field 44F - Port of Discharge
    
    if port_of_discharge:
        if isinstance(port_of_discharge, dict):
            baseline._port_of_discharge_info = PortInfo(
                name=port_of_discharge.get("name") or port_of_discharge.get("port"),
                country=port_of_discharge.get("country"),
            )
            port_of_discharge = baseline._port_of_discharge_info.name
        elif isinstance(port_of_discharge, str):
            baseline._port_of_discharge_info = PortInfo(name=port_of_discharge)
    set_field(baseline.port_of_discharge, port_of_discharge)
    
    # =====================================================================
    # Goods Description (MT700 Field 45A)
    # =====================================================================
    goods_description = get_value("goods_description", "description", "goods", "merchandise")
    if not goods_description:
        goods_description = blocks.get("45A")  # MT700 field 45A - Description of Goods
    
    # Handle goods as list of dicts or strings
    if isinstance(goods_description, list):
        desc_parts = []
        for g in goods_description:
            if isinstance(g, dict):
                # Extract description from goods item dict
                desc = g.get("description") or g.get("line") or g.get("text") or ""
                hs = g.get("hs_code", "")
                qty = g.get("quantity", {})
                qty_str = ""
                if isinstance(qty, dict) and qty.get("value"):
                    qty_str = f", QTY: {qty.get('value')} {qty.get('unit', 'PCS')}"
                elif qty:
                    qty_str = f", QTY: {qty}"
                if desc:
                    item_desc = f"{desc}{' HS: ' + hs if hs else ''}{qty_str}"
                    desc_parts.append(item_desc)
            elif isinstance(g, str) and g.strip():
                desc_parts.append(g.strip())
        goods_description = "\n".join(desc_parts) if desc_parts else None
    set_field(baseline.goods_description, goods_description)
    
    # =====================================================================
    # Incoterm (often in goods or separate field)
    # =====================================================================
    incoterm = get_value("incoterm", "trade_terms", "delivery_terms")
    set_field(baseline.incoterm, incoterm, confidence=0.6)
    
    # =====================================================================
    # Documents Required (MT700 Field 46A)
    # =====================================================================
    documents_required = get_value("documents_required", "required_documents")
    if not documents_required:
        documents_required = blocks.get("46A")  # MT700 field 46A - Documents Required
    
    if documents_required:
        if isinstance(documents_required, list):
            baseline._documents_list = documents_required
        elif isinstance(documents_required, str):
            baseline._documents_list = [documents_required]
    set_field(baseline.documents_required, documents_required)
    
    # =====================================================================
    # Additional Conditions (MT700 Field 47A)
    # =====================================================================
    # Look in multiple places - extraction stores as clauses_47a, structured as additional_conditions
    additional_conditions = get_value("additional_conditions", "conditions", "clauses_47a", "clauses")
    if not additional_conditions:
        additional_conditions = blocks.get("47A")  # MT700 field 47A - Additional Conditions
    # Also check inside lc_structured if present
    if not additional_conditions:
        lc_structured = lc_context.get("lc_structured", {})
        additional_conditions = lc_structured.get("additional_conditions") or lc_structured.get("clauses_47a")
    
    if additional_conditions:
        if isinstance(additional_conditions, list):
            baseline._conditions_list = additional_conditions
        elif isinstance(additional_conditions, str):
            baseline._conditions_list = [additional_conditions]
        logger.info(
            "47A Additional Conditions found: %d condition(s), sample: %s",
            len(baseline._conditions_list) if baseline._conditions_list else 0,
            str(baseline._conditions_list[0])[:100] if baseline._conditions_list else "none",
        )
    else:
        # Enhanced debugging for missing 47A
        logger.warning("47A Additional Conditions NOT FOUND in LC context")
        # Log what keys are available for debugging
        context_keys = list(lc_context.keys()) if lc_context else []
        lc_struct_keys = list((lc_context.get("lc_structured") or {}).keys())
        blocks_keys = list(blocks.keys())
        logger.debug(
            "47A DEBUG: context_keys=%s, lc_structured_keys=%s, blocks_keys=%s",
            context_keys[:20], lc_struct_keys[:20], blocks_keys[:20]
        )
    set_field(baseline.additional_conditions, additional_conditions)
    
    # =====================================================================
    # UCP Reference
    # =====================================================================
    ucp_reference = get_value("ucp_reference", "applicable_rules")
    if not ucp_reference:
        ucp_reference = blocks.get("40E")  # MT700 field 40E - Applicable Rules
    set_field(baseline.ucp_reference, ucp_reference)
    
    # Log extraction summary
    logger.info(
        "LCBaseline from context: completeness=%.1f%% critical=%.1f%% missing_critical=%s",
        baseline.extraction_completeness * 100,
        baseline.critical_completeness * 100,
        [f.field_name for f in baseline.get_missing_critical()],
    )
    
    return baseline


def _apply_issue_rewrite(issue: Dict[str, Any], rewrite_payload: Dict[str, Any]) -> None:
    title = rewrite_payload.get("title")
    if title:
        issue["title"] = title

    description = rewrite_payload.get("description")
    if description:
        issue["description"] = description
        issue["message"] = description

    expected = rewrite_payload.get("expected")
    if expected is not None:
        issue["expected"] = expected

    found = rewrite_payload.get("found")
    if found is not None:
        issue["found"] = found
        issue["actual"] = found

    suggestion = rewrite_payload.get("suggested_fix") or rewrite_payload.get("suggestion")
    if suggestion is not None:
        issue["suggested_fix"] = suggestion
        issue["suggestion"] = suggestion

    documents = rewrite_payload.get("documents")
    if documents:
        issue["documents"] = documents
        issue["document_names"] = documents

    priority = rewrite_payload.get("priority")
    severity = _priority_to_severity(priority, issue.get("severity"))
    issue["severity"] = severity
    if priority:
        issue["priority"] = priority


def _priority_to_severity(priority: Optional[str], fallback: Optional[str]) -> str:
    candidate = (priority or fallback or "minor").lower()
    if candidate in {"critical", "high"}:
        return "critical"
    if candidate in {"major", "medium", "warn", "warning"}:
        return "major"
    return "minor"


def _normalize_issue_severity(value: Optional[str]) -> str:
    """Normalize issue severity to standard values: critical, major, minor."""
    if not value:
        return "minor"
    normalized = value.lower()
    if normalized in {"critical", "high"}:
        return "critical"
    if normalized in {"major", "medium", "warn", "warning"}:
        return "major"
    return "minor"


def _format_deterministic_issue(result: Dict[str, Any]) -> Dict[str, Any]:
    issue_id = str(result.get("rule") or result.get("rule_id") or uuid4())
    severity = _normalize_issue_severity(result.get("severity"))
    priority = result.get("priority") or severity
    documents = _extract_document_names(result)
    expected = result.get("expected") or result.get("expected_value")
    found = result.get("found") or result.get("actual_value")
    suggestion = result.get("suggestion")
    expected_outcome = result.get("expected_outcome") or {}
    if not suggestion:
        suggestion = expected_outcome.get("invalid") or expected_outcome.get("message")

    return {
        "id": issue_id,
        "title": result.get("title") or result.get("rule") or "Rule Breach",
        "severity": severity,
        "priority": priority,
        "documents": documents,
        "description": result.get("message") or "",
        "expected": _coerce_issue_value(expected),
        "found": _coerce_issue_value(found),
        "suggested_fix": _coerce_issue_value(suggestion),
        "ucp_reference": _coerce_issue_value(result.get("rule")),
    }


def _coerce_issue_value(value: Any) -> str:
    if not value:
        return ""
    if isinstance(value, (dict, list)):
        try:
            return json.dumps(value, ensure_ascii=False)
        except Exception:
            return str(value)
    return str(value)


def _build_document_lookup(
    documents: List[Dict[str, Any]]
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, List[str]]]:
    meta: Dict[str, Dict[str, Any]] = {}
    key_map: Dict[str, List[str]] = {}

    for doc in documents:
        doc_id = doc.get("id")
        if not doc_id:
            continue
        display_name = doc.get("name") or doc.get("type") or doc.get("documentType") or doc_id
        meta[doc_id] = {
            "document_id": doc_id,
            "name": doc.get("name"),
            "display": display_name,
            "type": doc.get("documentType") or doc.get("type"),
        }
        candidate_keys = {
            _normalize_doc_match_key(display_name),
            _normalize_doc_match_key(doc.get("name")),
            _normalize_doc_match_key(_strip_extension(doc.get("name"))),
            _normalize_doc_match_key(doc.get("documentType")),
            _normalize_doc_match_key(doc.get("type")),
        }
        for key in filter(None, candidate_keys):
            key_map.setdefault(key, []).append(doc_id)

    return meta, key_map


def _match_issue_documents(
    issue: Dict[str, Any],
    doc_meta: Dict[str, Dict[str, Any]],
    key_map: Dict[str, List[str]],
) -> Tuple[List[str], List[str]]:
    matched: List[str] = []
    matched_ids: List[str] = []

    requested = issue.get("documents") or []
    if isinstance(requested, str):
        requested = [requested]

    for raw in requested:
        key = _normalize_doc_match_key(raw)
        if not key:
            continue
        for doc_id in key_map.get(key, []):
            if doc_id in matched_ids:
                continue
            meta = doc_meta.get(doc_id)
            if not meta:
                continue
            matched.append(meta.get("name") or meta.get("display") or meta.get("type") or doc_id)
            matched_ids.append(doc_id)

    return matched, matched_ids


def _normalize_doc_match_key(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    normalized = re.sub(r"[^a-z0-9]", "", str(value).lower())
    return normalized or None


def _strip_extension(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    if "." not in value:
        return value
    return value.rsplit(".", 1)[0]


def _build_documents_section(
    documents: List[Dict[str, Any]],
    issue_counts: Dict[str, int],
) -> List[Dict[str, Any]]:
    section: List[Dict[str, Any]] = []
    for doc in documents:
        doc_id = doc.get("id") or str(uuid4())
        extraction_status = (
            doc.get("extractionStatus")
            or doc.get("extraction_status")
            or doc.get("status")
            or "unknown"
        )
        section.append(
            {
                "document_id": doc_id,
                "document_type": _humanize_doc_type(doc.get("documentType") or doc.get("type")),
                "filename": doc.get("name"),
                "extraction_status": extraction_status,
                "extracted_fields": _filter_user_facing_fields(doc.get("extractedFields") or doc.get("extracted_fields") or {}),
                "issues_count": issue_counts.get(doc_id, 0),
            }
        )
    return section


def _build_analytics_section(
    summary: Dict[str, Any],
    documents: List[Dict[str, Any]],
    issues: List[Dict[str, Any]],
) -> Dict[str, Any]:
    return _response_builder.build_analytics_section(summary, documents, issues)


def _build_timeline_entries() -> List[Dict[str, str]]:
    return _response_builder.build_timeline_entries()

def _build_document_processing_analytics(
    document_summaries: List[Dict[str, Any]],
    processing_summary: Dict[str, Any],
) -> Dict[str, Any]:
    return _response_builder.build_document_processing_analytics(document_summaries, processing_summary)


def _format_duration(duration_seconds: float) -> str:
    if not duration_seconds:
        return "0s"
    minutes = duration_seconds / 60
    if minutes >= 1:
        return f"{minutes:.1f} minutes"
    return f"{duration_seconds:.1f} seconds"


def _fields_to_lc_context(fields: List[Any]) -> Dict[str, Any]:
    """Convert extracted LC fields into nested context for rule evaluation."""
    lc_context: Dict[str, Any] = {}

    for field in fields:
        value = (field.value or "").strip()
        if not value:
            continue

        name = field.field_name
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
        elif name == "applicant_address":
            _set_nested_value(lc_context, ("applicant", "address"), value)
        elif name == "applicant_country":
            _set_nested_value(lc_context, ("applicant", "country"), value)
        elif name == "beneficiary":
            _set_nested_value(lc_context, ("beneficiary", "name"), value)
        elif name == "beneficiary_address":
            _set_nested_value(lc_context, ("beneficiary", "address"), value)
        elif name == "beneficiary_country":
            _set_nested_value(lc_context, ("beneficiary", "country"), value)
        elif name == "port_of_loading":
            _set_nested_value(lc_context, ("ports", "loading"), value)
        elif name == "port_of_discharge":
            _set_nested_value(lc_context, ("ports", "discharge"), value)
        elif name == "goods_description":
            lc_context["goods_description"] = value
        elif name == "goods_items":
            try:
                lc_context["goods_items"] = json.loads(value)
            except (TypeError, ValueError):
                lc_context["goods_items"] = value
        elif name == "incoterm":
            lc_context["incoterm"] = value
        elif name == "ucp_reference":
            lc_context["ucp_reference"] = value
        elif name == "additional_conditions":
            lc_context["additional_conditions"] = value
        else:
            lc_context[name] = value

    return lc_context


def _fields_to_flat_context(fields: List[Any]) -> Dict[str, Any]:
    """Convert generic extracted fields to a flat dictionary."""
    context: Dict[str, Any] = {}
    field_details: Dict[str, Dict[str, Any]] = {}
    for field in fields:
        value = (field.value or "").strip()
        if value:
            context[field.field_name] = value
        details: Dict[str, Any] = {}
        reason = getattr(field, "reason", None)
        if reason:
            details["reason"] = reason
        confidence = getattr(field, "confidence", None)
        if confidence is not None:
            details["confidence"] = confidence
        raw_text = getattr(field, "raw_text", None)
        if raw_text:
            details["raw_text"] = raw_text
        if details:
            field_details[field.field_name] = details
    if field_details:
        context["_field_details"] = field_details
    return context


def _extract_field_decisions_from_payload(payload: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Best-effort extraction of LC field decisions from current payload/context."""
    if not isinstance(payload, dict):
        return {}

    for candidate in (
        payload.get("lc"),
        payload.get("lc_structured_output"),
        payload.get("extracted_fields"),
    ):
        if isinstance(candidate, dict):
            decisions = candidate.get("_field_decisions")
            if isinstance(decisions, dict):
                return decisions
    return {}


def _build_unresolved_critical_context(field_decisions: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return unresolved critical field diagnostics with mandatory status + reason_code."""
    unresolved: List[Dict[str, Any]] = []
    for field, decision in (field_decisions or {}).items():
        if not isinstance(decision, dict):
            continue
        status = str(decision.get("status") or "").strip().lower()
        if status not in {"retry", "rejected"}:
            continue
        reason_code = str(decision.get("reason_code") or "").strip()
        if not reason_code:
            reason_code = "unknown"
        entry = {
            "field": field,
            "status": status,
            "reason_code": reason_code,
        }
        if "retry_trace" in decision:
            entry["retry_trace"] = decision.get("retry_trace")
        unresolved.append(entry)
    return unresolved


def _augment_doc_field_details_with_decisions(documents: List[Dict[str, Any]]) -> None:
    """Inject decision/status/reason/retry_trace into document field_details (in-place)."""
    for doc in documents or []:
        if not isinstance(doc, dict):
            continue
        extracted_fields = doc.get("extracted_fields") or {}
        if not isinstance(extracted_fields, dict):
            continue

        field_decisions = extracted_fields.get("_field_decisions")
        if not isinstance(field_decisions, dict) or not field_decisions:
            continue

        field_details = doc.get("field_details")
        if not isinstance(field_details, dict):
            field_details = {}
            doc["field_details"] = field_details

        for field, decision in field_decisions.items():
            if not isinstance(decision, dict):
                continue
            details = field_details.get(field)
            if not isinstance(details, dict):
                details = {}
                field_details[field] = details

            details["decision_status"] = str(decision.get("status") or details.get("decision_status") or "unknown").lower()
            details["reason_code"] = str(decision.get("reason_code") or details.get("reason_code") or "unknown")
            details["decision"] = {
                "status": details["decision_status"],
                "reason_code": details["reason_code"],
            }
            if "retry_trace" in decision:
                details["retry_trace"] = decision.get("retry_trace")


def _augment_issues_with_field_decisions(
    issues: List[Dict[str, Any]],
    field_decisions: Dict[str, Dict[str, Any]],
) -> None:
    """Inject decision status/reason_code in issue payload where a field decision exists."""
    if not issues or not field_decisions:
        return

    for issue in issues:
        if not isinstance(issue, dict):
            continue
        field_name = (
            issue.get("field")
            or issue.get("field_name")
            or issue.get("source_field")
            or issue.get("lc_field")
        )
        if not field_name:
            continue
        decision = field_decisions.get(str(field_name))
        if not isinstance(decision, dict):
            continue

        issue["decision_status"] = str(decision.get("status") or issue.get("decision_status") or "unknown").lower()
        issue["reason_code"] = str(decision.get("reason_code") or issue.get("reason_code") or "unknown")
        issue["decision"] = {
            "status": issue["decision_status"],
            "reason_code": issue["reason_code"],
        }


def _build_submission_eligibility_context(
    gate_result: Dict[str, Any],
    field_decisions: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Aggregate missing reason codes + unresolved critical statuses for submission eligibility."""
    unresolved = _build_unresolved_critical_context(field_decisions)
    reasons = set((gate_result or {}).get("missing_reason_codes") or [])
    statuses = set()
    for item in unresolved:
        reasons.add(item.get("reason_code") or "unknown")
        statuses.add(item.get("status") or "unknown")

    return {
        "missing_reason_codes": sorted(str(r) for r in reasons if r),
        "unresolved_critical_fields": unresolved,
        "unresolved_critical_statuses": sorted(str(s) for s in statuses if s),
    }


def _parse_json_if_possible(value: Any) -> Any:
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("{") or stripped.startswith("["):
            try:
                return json.loads(stripped)
            except json.JSONDecodeError:
                logger.warning("Failed to parse JSON string in LC payload; leaving raw text")
                return value
    return value


def _coerce_goods_items(value: Any) -> List[Dict[str, Any]]:
    parsed = _parse_json_if_possible(value)
    if isinstance(parsed, list):
        return parsed
    if isinstance(parsed, dict):
        return [parsed]
    return []


def _normalize_lc_payload_structures(lc_payload: Any) -> Dict[str, Any]:
    parsed = _parse_json_if_possible(lc_payload)
    if not isinstance(parsed, dict):
        return {}

    nested_keys = (
        "applicant",
        "beneficiary",
        "ports",
        "dates",
        "amount",
        "issuing_bank",
        "advising_bank",
    )
    for key in nested_keys:
        if key in parsed:
            nested = _parse_json_if_possible(parsed[key])
            if isinstance(nested, dict):
                parsed[key] = nested

    if "goods_items" in parsed:
        parsed["goods_items"] = _coerce_goods_items(parsed.get("goods_items"))

    return parsed


def _set_nested_value(container: Dict[str, Any], path: Tuple[str, ...], value: Any) -> None:
    current = container
    for segment in path[:-1]:
        current = current.setdefault(segment, {})
    current[path[-1]] = value


@router.get("/customs-pack/{session_id}")
async def generate_customs_pack(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Build the customs pack ZIP, upload to S3, and return a signed URL.
    The FE should read .customs_pack.download_url and redirect the browser to it.
    """
    from uuid import UUID
    
    try:
        session_uuid = UUID(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID format"
        )
    
    session = (
        db.query(ValidationSession)
        .filter(
            ValidationSession.id == session_uuid,
            ValidationSession.deleted_at.is_(None)
        )
        .first()
    )
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Validation session not found"
        )
    
    # Check access - user must own the session or be admin
    if session.user_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Validate session has been processed
    validation_results = session.validation_results or {}
    if not validation_results:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Session has no validation_results yet. Please run validation first."
        )
    
    # Build the customs pack
    try:
        builder = CustomsPackBuilderFull()
        result = builder.build_and_upload(db=db, session_id=session_id)
    except ValueError as e:
        # Session not found or invalid
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to build customs pack for session {session_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate customs pack: {str(e)}"
        )
    
    return {"customs_pack": result}


# =============================================================================
# V2 ENDPOINT: SME-Focused Validation Response (Output-First)
# =============================================================================
# This endpoint returns the new SME contract format - cleaner, simpler, and
# focused on what SME users actually need to see.
# =============================================================================

@router.post("/v2")
async def validate_doc_v2(
    request: Request,
    current_user: User = Depends(get_user_optional),
    db: Session = Depends(get_db),
):
    """
    V2 Validation Endpoint - SME-focused response format.
    
    This endpoint runs the same validation logic but returns a cleaner,
    more focused response designed for SME/Corporation users.
    
    Response follows the SMEValidationResponse contract:
    - lc_summary: LC header info
    - verdict: The big answer (PASS/FIX_REQUIRED/LIKELY_REJECT)
    - issues: Grouped by must_fix and should_fix
    - documents: Grouped by good, has_issues, missing
    - processing: Metadata
    """
    from app.services.validation.sme_response_builder import adapt_from_structured_result
    
    # Run the existing validation
    try:
        v1_response = await validate_doc(request, current_user, db)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"V2 validation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation failed: {str(e)}"
        )
    
    # Extract job_id and structured_result
    job_id = v1_response.get("job_id", "unknown")
    structured_result = v1_response.get("structured_result", {})
    
    # Transform to SME contract format
    try:
        sme_response = adapt_from_structured_result(
            structured_result=structured_result,
            session_id=job_id,
        )
        
        # Return the clean SME response
        return {
            "version": "2.0",
            "job_id": job_id,
            "data": sme_response.to_dict(),
            # Also include v1 for debugging during transition
            "_v1_structured_result": structured_result if request.headers.get("X-Include-V1") else None,
        }
    except Exception as e:
        logger.error(f"V2 response transformation failed: {e}", exc_info=True)
        # Fall back to v1 response
        return {
            "version": "1.0",
            "job_id": job_id,
            "data": structured_result,
            "_transformation_error": str(e),
        }


@router.get("/v2/session/{session_id}")
async def get_validation_result_v2(
    session_id: str,
    current_user: User = Depends(get_user_optional),
    db: Session = Depends(get_db),
):
    """
    Get validation results in V2 SME format for an existing session.
    Uses lenient auth to support sessions created anonymously.
    """
    from app.services.validation.sme_response_builder import adapt_from_structured_result
    
    # Get the session
    session = db.query(ValidationSession).filter(
        ValidationSession.id == session_id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Validation session {session_id} not found"
        )
    
    # Lenient access check - allow if:
    # 1. User owns the session
    # 2. User is admin
    # 3. Session was created anonymously (demo user)
    # For now, we allow access since sessions may have been created before auth was enforced
    # TODO: Add stricter access control once session ownership is properly tracked
    
    # Get stored validation results
    raw_results = session.validation_results or {}
    if not raw_results:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Session has no validation results yet"
        )
    
    # Unwrap if stored in nested format: {"structured_result": {...}}
    if "structured_result" in raw_results:
        structured_result = raw_results["structured_result"]
    else:
        structured_result = raw_results
    
    # Debug: Log what keys are available in structured_result
    logger.info(f"V2 session {session_id} - stored keys: {list(structured_result.keys())}")
    logger.info(f"V2 session {session_id} - lc_data keys: {list(structured_result.get('lc_data', {}).keys()) if isinstance(structured_result.get('lc_data'), dict) else 'N/A'}")
    logger.info(f"V2 session {session_id} - documents count: {len(structured_result.get('documents_structured', []))}")
    logger.info(f"V2 session {session_id} - issues count: {len(structured_result.get('issues', []))}")
    logger.info(f"V2 session {session_id} - crossdoc count: {len(structured_result.get('crossdoc_issues', []))}")
    
    # Transform to SME format
    try:
        sme_response = adapt_from_structured_result(
            structured_result=structured_result,
            session_id=session_id,
        )
        
        return {
            "version": "2.0",
            "session_id": session_id,
            "data": sme_response.to_dict(),
        }
    except Exception as e:
        logger.error(f"V2 transformation failed for session {session_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to transform results: {str(e)}"
        )

