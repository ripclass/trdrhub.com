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
from typing import Optional, List, Dict, Any, Tuple, Set
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
    # LC dates / intake
    backfill_lc_mt700_sources as _backfill_lc_mt700_sources,
    coerce_mt700_date_iso as _coerce_mt700_date_iso,
    extract_mt700_block_value as _extract_mt700_block_value,
    extract_mt700_timeline_fields as _extract_mt700_timeline_fields,
    repair_lc_mt700_dates as _repair_lc_mt700_dates,
    extract_intake_only as _extract_intake_only,
    coerce_text_list as _coerce_text_list,
    infer_required_document_types_from_lc as _infer_required_document_types_from_lc,
    resolve_legacy_workflow_lc_fields as _resolve_legacy_workflow_lc_fields,
    prepare_extractor_outputs_for_structured_result as _prepare_extractor_outputs_for_structured_result,
    build_minimal_lc_structured_output as _build_minimal_lc_structured_output,
    build_lc_intake_summary as _build_lc_intake_summary,
    # Review policy
    count_populated_canonical_fields as _count_populated_canonical_fields,
    apply_extraction_guard as _apply_extraction_guard,
    finalize_text_backed_extraction_status as _finalize_text_backed_extraction_status,
    stabilize_document_review_semantics as _stabilize_document_review_semantics,
    context_payload_for_doc_type as _context_payload_for_doc_type,
    extract_day1_raw_candidates as _extract_day1_raw_candidates,
    day1_policy_for_doc as _day1_policy_for_doc,
    enforce_day1_runtime_policy as _enforce_day1_runtime_policy,
    is_populated_field_value as _is_populated_field_value,
    assess_required_field_completeness as _assess_required_field_completeness,
    assess_coo_parse_completeness as _assess_coo_parse_completeness,
    # Issues / presentation contract
    _build_issue_context,
    _apply_issue_rewrite,
    _extract_field_decisions_from_payload,
    _build_document_field_hint_index,
    _build_unresolved_critical_context,
    _augment_doc_field_details_with_decisions,
    _augment_issues_with_field_decisions,
    _classify_reason_semantics,
    _extract_rule_evidence_items,
    _classify_rules_signal_classes,
    _build_validation_contract,
    _run_validation_arbitration_escalation,
    _build_submission_eligibility_context,
    sync_structured_result_collections as _sync_structured_result_collections,
    apply_cycle2_runtime_recovery as _apply_cycle2_runtime_recovery,
    backfill_hybrid_secondary_surfaces as _backfill_hybrid_secondary_surfaces,
    # OCR runtime
    _empty_extraction_artifacts_v1,
    _extraction_fallback_hotfix_enabled,
    _ocr_compatibility_v1_enabled,
    _stage_promotion_v1_enabled,
    _ocr_adapter_runtime_payload_fix_v1_enabled,
    _stage_threshold_tuning_v1_enabled,
    _record_extraction_reason_code,
    _record_extraction_stage,
    _merge_extraction_artifacts,
    _finalize_text_extraction_result,
    _merge_text_sources,
    _build_extraction_artifacts_from_ocr,
    _scrape_binary_text_metadata,
    _detect_input_mime_type,
    _looks_like_plaintext_bytes,
    _extract_plaintext_bytes,
    _normalize_ocr_input,
    _prepare_provider_ocr_payload,
    _provider_runtime_limits,
    _pdf_page_count,
    _render_pdf_runtime_images,
    _normalize_runtime_image_bytes,
    _build_runtime_payload_entry,
    _build_google_docai_payload_plan,
    _build_textract_payload_plan,
    _build_provider_runtime_payload_plan,
    _build_provider_attempt_record,
    _map_ocr_provider_error_code,
    _get_viable_ocr_providers,
    _score_stage_candidate,
    _select_best_extraction_stage,
    _extract_text_from_upload,
    _try_secondary_ocr_adapter,
    _try_ocr_providers,
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
from app.services.extraction.launch_pipeline import get_launch_extraction_pipeline
from app.services.extraction.iso20022_lc_extractor import detect_iso20022_schema
from app.services.extraction.lc_taxonomy import (
    build_lc_classification,
    normalize_required_documents,
    extract_requirement_conditions,
    extract_unmapped_requirements,
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
from app.services.validation.day1_contract import enforce_day1_response_contract
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


def _extract_workflow_lc_type(lc_context: Dict[str, Any]) -> Optional[str]:
    classification = lc_context.get("lc_classification")
    if isinstance(classification, dict):
        workflow = normalize_lc_type(str(classification.get("workflow_orientation") or "").strip().lower())
        if workflow and workflow != LCType.UNKNOWN.value:
            return workflow
    raw_lc_type = (
        lc_context.get("lc_type")
        or lc_context.get("form_of_doc_credit")
        or (lc_context.get("mt700") or {}).get("form_of_doc_credit")
    )
    if raw_lc_type is None:
        return None
    workflow = normalize_lc_type(str(raw_lc_type).strip().lower())
    if workflow == LCType.UNKNOWN.value:
        return None
    return workflow




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


def _extract_extraction_resolution_from_context_payload(context_payload: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not isinstance(context_payload, dict):
        return None
    direct = context_payload.get("extraction_resolution")
    if isinstance(direct, dict):
        return direct
    for key, value in context_payload.items():
        if not str(key or "").endswith("_review") or not isinstance(value, dict):
            continue
        extraction_resolution = value.get("extraction_resolution")
        if isinstance(extraction_resolution, dict):
            return extraction_resolution
    return None
















def _build_day1_relay_debug(structured_result: Dict[str, Any]) -> Dict[str, Any]:
    def _surface_docs(path: str) -> List[Dict[str, Any]]:
        if path == "documents":
            docs = structured_result.get("documents")
        elif path == "processing_summary.documents":
            docs = (structured_result.get("processing_summary") or {}).get("documents")
        elif path == "processing_summary_v2.documents":
            docs = (structured_result.get("processing_summary_v2") or {}).get("documents")
        elif path == "document_extraction_v1.documents":
            docs = (structured_result.get("document_extraction_v1") or {}).get("documents")
        else:
            docs = None
        return [doc for doc in docs if isinstance(doc, dict)] if isinstance(docs, list) else []

    def _doc_runtime_summary(doc: Dict[str, Any]) -> Dict[str, Any]:
        runtime = doc.get("day1_runtime") if isinstance(doc.get("day1_runtime"), dict) else {}
        if not runtime and isinstance(doc.get("day1Runtime"), dict):
            runtime = doc.get("day1Runtime")
        hook = doc.get("_day1_runtime_hook") if isinstance(doc.get("_day1_runtime_hook"), dict) else {}
        errors = runtime.get("errors") if isinstance(runtime.get("errors"), list) else []
        return {
            "filename": doc.get("filename") or doc.get("name"),
            "document_type": doc.get("document_type") or doc.get("documentType") or doc.get("type"),
            "runtime_present": bool(runtime),
            "coverage": int(runtime.get("coverage") or 0) if runtime else 0,
            "threshold": int(runtime.get("threshold") or 0) if runtime else 0,
            "fallback_stage": runtime.get("fallback_stage") if runtime else None,
            "error_codes": [str(code) for code in errors if isinstance(code, str)],
            "hook_callsite_reached": bool(hook.get("callsite_reached")),
            "hook_invoked": bool(hook.get("invoked")),
            "hook_attached": bool(hook.get("attached")),
            "hook_runtime_present": bool(hook.get("post_enforce_runtime_present")),
            "hook_skipped": bool(hook.get("skipped")),
            "hook_skip_reason": str(hook.get("reason") or ""),
        }

    surfaces: Dict[str, List[Dict[str, Any]]] = {}
    for surface in [
        "documents",
        "processing_summary.documents",
        "processing_summary_v2.documents",
        "document_extraction_v1.documents",
    ]:
        docs = _surface_docs(surface)
        surfaces[surface] = [_doc_runtime_summary(doc) for doc in docs]

    return {
        "patch_markers": {
            "runtime_passthrough": True,
            "policy_mode": "doc_type",
            "ocr_pdf_retry": "normalized_image_before_binary_scrape",
        },
        "surfaces": surfaces,
    }




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
        # Create demo company first when the surrounding schema exists.
        # In minimal/local validation-only runtimes, the companies table may not be present.
        from sqlalchemy import text
        from sqlalchemy.exc import SQLAlchemyError
        demo_company_id = None
        try:
            result = db.execute(text("SELECT id FROM companies WHERE name = :name"), {"name": "Demo Company"})
            demo_company_row = result.first()
            
            if not demo_company_row:
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
        except SQLAlchemyError:
            db.rollback()
            demo_company_id = None
        
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
    """Get current user, allowing demo fallback only when explicitly enabled."""
    if authorization and authorization.startswith("Bearer "):
        from app.core.security import get_current_user
        from fastapi.security import HTTPAuthorizationCredentials

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=authorization[7:],
        )
        return await get_current_user(credentials=credentials, db=db)

    if settings.ENABLE_PUBLIC_VALIDATE_DEMO and not settings.is_production():
        return get_or_create_demo_user(db)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
    )








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
        uses_fact_resolution = _response_shaping._uses_fact_resolution_contract(detail)

        status = _derive_document_status(
            detail.get("extraction_status"),
            stats.get("max_severity") if stats else None,
            parse_complete=None if uses_fact_resolution else parse_complete_flag,
        )
        discrepancy_count = stats.get("count", 0) if stats else 0

        summary = {
            "id": detail_id,
            "name": filename or f"Document {index + 1}",
            "type": _humanize_doc_type(normalized_type),
            "documentType": normalized_type,
            "status": status,
            "discrepancyCount": discrepancy_count,
            "extractedFields": _filter_user_facing_fields(detail.get("extracted_fields") or {}),
            "field_details": detail.get("field_details") or detail.get("fieldDetails") or detail.get("_field_details") or {},
            "fieldDetails": detail.get("fieldDetails") or detail.get("field_details") or detail.get("_field_details") or {},
            "extraction_lane": detail.get("extraction_lane") or detail.get("extractionLane"),
            "extractionLane": detail.get("extractionLane") or detail.get("extraction_lane"),
            "extraction_resolution": detail.get("extraction_resolution") or detail.get("extractionResolution"),
            "extractionResolution": detail.get("extractionResolution") or detail.get("extraction_resolution"),
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
        return _response_shaping.sanitize_public_document_contract_v1(summary)

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


def _looks_like_letter_of_credit_text(extracted_text: Optional[str]) -> bool:
    """Return True when OCR text contains strong LC/MT700-style signals."""
    if not extracted_text:
        return False

    text = str(extracted_text or "").strip()
    if len(text) < 50:
        return False

    normalized = text.upper()
    strong_patterns = [
        r":40[A-E]:",
        r":45A:",
        r":46A:",
        r":47A:",
        r"DOCUMENTARY\s*CREDIT",
        r"LETTER\s*OF\s*CREDIT",
        r"IRREVOCABLE",
        r"UCP\s*600",
        r"MT\s*700",
    ]
    matched = sum(1 for pattern in strong_patterns if re.search(pattern, normalized, re.IGNORECASE))
    return matched >= 2


def _explicit_title_document_type(extracted_text: Optional[str]) -> Optional[str]:
    if not extracted_text:
        return None
    normalized = re.sub(r"\s+", " ", str(extracted_text or "").strip().lower())
    if len(normalized) < 20:
        return None

    title_rules = [
        ("letter_of_credit", ["documentary credit number", "letter of credit", "documents required", "additional conditions"]),
        ("commercial_invoice", ["commercial invoice", "invoice no", "total invoice value"]),
        ("bill_of_lading", ["bill of lading", "b/l no", "clean on board"]),
        ("packing_list", ["packing list", "marks & numbers", "packing list no"]),
        ("beneficiary_certificate", ["beneficiary certificate", "we, beneficiary", "hereby certify that"]),
        ("weight_list", ["weight list", "gross weight", "net weight"]),
        ("insurance_certificate", ["insurance certificate", "insured value", "cover:"]),
        ("certificate_of_origin", ["certificate of origin", "country of origin"]),
    ]

    for canonical_type, markers in title_rules:
        if canonical_type == "weight_list":
            if "weight list" in normalized and ("gross weight" in normalized or "net weight" in normalized):
                return canonical_type
            continue
        if sum(1 for marker in markers if marker in normalized) >= 2:
            return canonical_type
        if markers[0] in normalized[:220]:
            return canonical_type
    return None


def _supporting_guess_to_canonical_type(subtype: Optional[str], family: Optional[str]) -> Optional[str]:
    subtype_key = str(subtype or "").strip().lower().replace("-", "_").replace(" ", "_")
    family_key = str(family or "").strip().lower()

    subtype_map = {
        "bill_of_lading": "bill_of_lading",
        "waybill": "air_waybill",
        "awb": "air_waybill",
        "packing_list": "packing_list",
        "weight_list": "weight_list",
        "weight_certificate": "weight_certificate",
        "commercial_invoice": "commercial_invoice",
        "invoice": "commercial_invoice",
        "certificate_of_origin": "certificate_of_origin",
        "origin": "certificate_of_origin",
        "insurance": "insurance_certificate",
        "insurance_policy": "insurance_policy",
        "insurance_certificate": "insurance_certificate",
        "inspection": "inspection_certificate",
        "inspection_certificate": "inspection_certificate",
        "analysis": "analysis_certificate",
        "analysis_certificate": "analysis_certificate",
        "test_report": "lab_test_report",
        "quality": "quality_certificate",
        "quality_certificate": "quality_certificate",
        "sgs": "sgs_certificate",
        "intertek": "intertek_certificate",
        "bureau_veritas": "bureau_veritas_certificate",
        "phytosanitary": "phytosanitary_certificate",
        "fumigation": "fumigation_certificate",
        "health_certificate": "health_certificate",
        "beneficiary_certificate": "beneficiary_certificate",
        "beneficiary_statement": "beneficiary_certificate",
        "conformity": "conformity_certificate",
        "conformity_certificate": "conformity_certificate",
        "halal": "halal_certificate",
        "kosher": "kosher_certificate",
        "organic": "organic_certificate",
        "bank_guarantee": "letter_of_credit",
        "standby_letter_of_credit": "letter_of_credit",
    }
    if subtype_key in subtype_map:
        return subtype_map[subtype_key]

    family_map = {
        "transport_document": "bill_of_lading",
        "inspection_testing_quality": "inspection_certificate",
        "origin_customs_regulatory": "certificate_of_origin",
        "insurance_compliance_special_certificates": "insurance_certificate",
        "commercial_payment_instruments": "commercial_invoice",
        "lc_financial_undertakings": "letter_of_credit",
    }
    return family_map.get(family_key)


def _maybe_promote_supporting_document_from_known_trade_set(
    *,
    filename: Optional[str],
    extracted_text: Optional[str],
) -> Optional[Dict[str, Any]]:
    try:
        from app.services.extraction.launch_pipeline import _guess_supporting_document_subtype
    except Exception as exc:
        logger.debug("Supporting subtype guess unavailable for %s: %s", filename, exc)
        return None

    guess = _guess_supporting_document_subtype(
        filename=filename or "",
        extracted_text=extracted_text or "",
    ) or {}
    confidence = float(guess.get("confidence") or 0.0)
    subtype = guess.get("subtype")
    family = guess.get("family")
    canonical_type = _supporting_guess_to_canonical_type(subtype, family)
    if not canonical_type or confidence < 0.55:
        return None

    return {
        "document_type": canonical_type,
        "confidence": confidence,
        "confidence_level": "medium" if confidence < 0.75 else "high",
        "is_reliable": True,
        "reasoning": "Known trade-document subtype inferred from supporting-document classifier over OCR text.",
        "matched_patterns": list(guess.get("reasons") or []),
        "supporting_subtype_guess": subtype,
        "supporting_family_guess": family,
    }


def _maybe_promote_document_type_from_content(
    *,
    filename: Optional[str],
    current_type: str,
    extracted_text: Optional[str],
    required_document_types: Optional[List[str]] = None,
    has_primary_lc_anchor: bool = False,
) -> Dict[str, Any]:
    """
    Use OCR/text content to promote weak filename-based guesses.

    Important: this is intentionally conservative.
    We only override the incoming type when the current type is generic/weak
    (for example `supporting_document`) and content classification is reliable.
    This avoids trampling explicit user choices while still rescuing uploads like
    `img123.pdf` that actually contain an LC/invoice/B/L/etc.
    """
    result: Dict[str, Any] = {
        "document_type": current_type,
        "content_classification": None,
        "promoted": False,
    }
    required_doc_set = {str(item).strip().lower() for item in (required_document_types or []) if str(item).strip()}

    if not extracted_text or len((extracted_text or "").strip()) < 50:
        return result

    weak_types = {
        "supporting_document",
        "other",
        "unknown",
    }

    explicit_type = _explicit_title_document_type(extracted_text)
    if current_type in weak_types and explicit_type and explicit_type in required_doc_set and explicit_type != "letter_of_credit":
        result["document_type"] = explicit_type
        result["promoted"] = True
        result["content_classification"] = {
            "document_type": explicit_type,
            "confidence": 0.98,
            "confidence_level": "high",
            "is_reliable": True,
            "reasoning": "Explicit document-title/header markers matched a document required by the resolved LC.",
            "matched_patterns": ["explicit_document_title_markers", "lc_required_doc_prior"],
        }
        logger.info(
            "Promoted document type from explicit OCR title + LC requirement for %s: %s -> %s",
            filename,
            current_type,
            explicit_type,
        )
        return result

    if current_type in weak_types and explicit_type and explicit_type != "letter_of_credit":
        result["document_type"] = explicit_type
        result["promoted"] = True
        result["content_classification"] = {
            "document_type": explicit_type,
            "confidence": 0.96,
            "confidence_level": "high",
            "is_reliable": True,
            "reasoning": "Explicit document-title/header markers detected directly from OCR text.",
            "matched_patterns": ["explicit_document_title_markers"],
        }
        logger.info(
            "Promoted document type from explicit OCR title for %s: %s -> %s",
            filename,
            current_type,
            explicit_type,
        )
        return result

    if current_type in weak_types and explicit_type == "letter_of_credit" and _looks_like_letter_of_credit_text(extracted_text):
        if has_primary_lc_anchor:
            result["document_type"] = "duplicate_lc_candidate"
            result["promoted"] = True
            result["content_classification"] = {
                "document_type": "duplicate_lc_candidate",
                "confidence": 0.86,
                "confidence_level": "high",
                "is_reliable": True,
                "reasoning": "Strong LC-like structure detected, but a primary LC anchor already exists for this job.",
                "matched_patterns": ["strong_lc_text_markers", "explicit_document_title_markers", "existing_lc_anchor"],
            }
            logger.info(
                "Demoted extra LC-like document for %s: %s -> duplicate_lc_candidate because primary LC already exists",
                filename,
                current_type,
            )
            return result
        result["document_type"] = "letter_of_credit"
        result["promoted"] = True
        result["content_classification"] = {
            "document_type": "letter_of_credit",
            "confidence": 0.95,
            "confidence_level": "high",
            "is_reliable": True,
            "reasoning": "Strong LC/MT700 textual markers detected directly from OCR text.",
            "matched_patterns": ["strong_lc_text_markers", "explicit_document_title_markers"],
        }
        logger.info(
            "Promoted document type from strong LC markers for %s: %s -> letter_of_credit",
            filename,
            current_type,
        )
        return result

    if current_type in weak_types:
        supporting_promotion = _maybe_promote_supporting_document_from_known_trade_set(
            filename=filename,
            extracted_text=extracted_text,
        )
        if supporting_promotion:
            result["document_type"] = str(supporting_promotion.get("document_type") or current_type)
            result["promoted"] = True
            result["content_classification"] = {
                "document_type": supporting_promotion.get("document_type"),
                "confidence": supporting_promotion.get("confidence"),
                "confidence_level": supporting_promotion.get("confidence_level"),
                "is_reliable": supporting_promotion.get("is_reliable"),
                "reasoning": supporting_promotion.get("reasoning"),
                "matched_patterns": supporting_promotion.get("matched_patterns") or [],
                "supporting_subtype_guess": supporting_promotion.get("supporting_subtype_guess"),
                "supporting_family_guess": supporting_promotion.get("supporting_family_guess"),
            }
            logger.info(
                "Promoted supporting document from known trade set for %s: %s -> %s (confidence=%.2f)",
                filename,
                current_type,
                result["document_type"],
                float(supporting_promotion.get("confidence") or 0.0),
            )
            return result

    try:
        from app.models import DocumentType
        from app.services.document_intelligence import get_doc_type_classifier
    except Exception as exc:
        logger.debug("Content classifier unavailable for %s: %s", filename, exc)
        return result

    fallback_type = None
    try:
        fallback_type = DocumentType(current_type)
    except Exception:
        fallback_type = DocumentType.SUPPORTING_DOCUMENT

    try:
        classifier = get_doc_type_classifier()
        classification = classifier.classify(
            text=extracted_text,
            filename=filename,
            fallback_type=fallback_type,
        )
    except Exception as exc:
        logger.warning("Content classification failed for %s: %s", filename, exc)
        return result

    classification_payload = {
        "document_type": classification.document_type.value,
        "confidence": classification.confidence,
        "confidence_level": classification.confidence_level.value,
        "is_reliable": classification.is_reliable,
        "reasoning": classification.reasoning,
        "matched_patterns": classification.matched_patterns,
    }
    result["content_classification"] = classification_payload

    classified_type = classification.document_type.value
    if (
        classification.is_reliable
        and classified_type
        and classified_type != current_type
        and current_type in weak_types
    ):
        result["document_type"] = classified_type
        result["promoted"] = True
        logger.info(
            "Promoted document type from content for %s: %s -> %s (confidence=%.2f)",
            filename,
            current_type,
            classified_type,
            classification.confidence,
        )

    return result


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
        "certificate_of_origin",
        "insurance_certificate",
        "insurance_policy",
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
        "beneficiary_certificate",
        "manufacturer_certificate",
        "conformity_certificate",
        "non_manipulation_certificate",
        "phytosanitary_certificate",
        "fumigation_certificate",
        "health_certificate",
        "veterinary_certificate",
        "sanitary_certificate",
        "halal_certificate",
        "kosher_certificate",
        "organic_certificate",
        "gsp_form_a",
        "eur1_movement_certificate",
        "customs_declaration",
        "export_license",
        "import_license",
        "air_waybill",
        "sea_waybill",
        "road_transport_document",
        "railway_consignment_note",
        "forwarder_certificate_of_receipt",
        "shipping_company_certificate",
        "warehouse_receipt",
        "cargo_manifest",
        "supporting_document",
    }
    documents_presence: Dict[str, Dict[str, Any]] = {
        doc_type: {"present": False, "count": 0} for doc_type in known_doc_types
    }

    # ===========================================================================
    # PARALLEL OCR EXTRACTION - Process all files concurrently for better performance
    # This significantly speeds up 10-12 document batches (from ~6min to ~2min)
    # ===========================================================================
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
    # ===========================================================================

    lc_required_document_types = _infer_required_document_types_from_lc(context.get("lc") or {})
    primary_lc_anchor_seen = False

    for idx, upload_file in enumerate(files_list):
        filename = getattr(upload_file, "filename", f"document_{idx+1}")
        content_type = getattr(upload_file, "content_type", "unknown")
        document_type = _resolve_document_type(filename, idx, normalized_tags)
        document_id = str(uuid4())
        doc_process_started_at = time.perf_counter()
        doc_info: Dict[str, Any] = {
            "id": document_id,
            "filename": filename,
            "document_type": document_type,
            "extracted_fields": {},
            "extraction_status": "empty",
            "timings_ms": {},
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
        ocr_elapsed_ms = extraction_artifacts_v1.get("total_time_ms")
        if ocr_elapsed_ms is not None:
            try:
                doc_info.setdefault("timings_ms", {})["ocr"] = round(float(ocr_elapsed_ms), 2)
            except Exception:
                pass

        artifacts_index = context.setdefault("document_artifacts_v1", {})
        artifacts_index[document_id] = extraction_artifacts_v1

        if idx in extraction_errors:
            logger.warning(f"? OCR extraction error for {filename}: {extraction_errors[idx]}")

        allows_multimodal_lc_bootstrap = document_type in {"letter_of_credit", "swift_message", "lc_application"}
        if not extracted_text and not allows_multimodal_lc_bootstrap:
            logger.warning(f"? No text extracted from {filename} - skipping field extraction")
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
        if extracted_text:
            logger.info(f"? Extracted {len(extracted_text)} characters from {filename}")
        else:
            logger.info("validate.extraction.multimodal_lc_bootstrap file=%s doc_type=%s proceeding_without_route_text=%s", filename, document_type, True)

        content_type_resolution = _maybe_promote_document_type_from_content(
            filename=filename,
            current_type=document_type,
            extracted_text=extracted_text,
            required_document_types=lc_required_document_types,
            has_primary_lc_anchor=primary_lc_anchor_seen,
        )
        doc_info["content_classification"] = content_type_resolution.get("content_classification")
        if content_type_resolution.get("promoted"):
            doc_info["original_document_type"] = document_type
            document_type = str(content_type_resolution.get("document_type") or document_type)
            doc_info["document_type"] = document_type
            doc_info["document_type_resolution"] = "content_promoted"
        else:
            doc_info["document_type_resolution"] = "tag_or_filename"

        if document_type == "letter_of_credit":
            primary_lc_anchor_seen = True
        elif document_type == "duplicate_lc_candidate":
            doc_info.setdefault("review_flags", []).append("extra_lc_like_document")

        launch_pipeline_result: Optional[Dict[str, Any]] = None
        launch_pipeline = get_launch_extraction_pipeline()
        launch_pipeline_started_at = time.perf_counter()
        if document_type in ("letter_of_credit", "swift_message", "lc_application", "commercial_invoice", "proforma_invoice", "bill_of_lading", "packing_list", "certificate_of_origin", "insurance_certificate", "insurance_policy", "inspection_certificate", "pre_shipment_inspection", "quality_certificate", "weight_certificate", "weight_list", "measurement_certificate", "analysis_certificate", "lab_test_report", "sgs_certificate", "bureau_veritas_certificate", "intertek_certificate", "beneficiary_certificate", "manufacturer_certificate", "conformity_certificate", "non_manipulation_certificate", "phytosanitary_certificate", "fumigation_certificate", "health_certificate", "veterinary_certificate", "sanitary_certificate", "halal_certificate", "kosher_certificate", "organic_certificate", "gsp_form_a", "eur1_movement_certificate", "customs_declaration", "export_license", "import_license", "air_waybill", "sea_waybill", "road_transport_document", "railway_consignment_note", "forwarder_certificate_of_receipt", "shipping_company_certificate", "warehouse_receipt", "cargo_manifest", "supporting_document"):
            try:
                file_bytes = await upload_file.read()
                await upload_file.seek(0)
                launch_pipeline_result = await launch_pipeline.process_document(
                    extracted_text=extracted_text,
                    document_type=document_type,
                    filename=filename,
                    extraction_artifacts_v1=extraction_artifacts_v1,
                    file_bytes=file_bytes,
                    content_type=content_type,
                )
            except Exception as launch_exc:
                logger.warning("Launch extraction pipeline failed for %s: %s", filename, launch_exc, exc_info=True)
                launch_pipeline_result = None
        doc_info.setdefault("timings_ms", {})["launch_pipeline"] = round((time.perf_counter() - launch_pipeline_started_at) * 1000, 2)

        try:
            if launch_pipeline_result and launch_pipeline_result.get("handled"):
                context_key = launch_pipeline_result.get("context_key")
                context_payload = launch_pipeline_result.get("context_payload") or {}
                support_only = bool(launch_pipeline_result.get("support_only"))
                if context_key and isinstance(context_payload, dict):
                    if support_only:
                        support_candidates = context.setdefault("_support_candidates", {})
                        support_bucket = support_candidates.setdefault(context_key, [])
                        if isinstance(support_bucket, list):
                            support_bucket.append(context_payload)
                    else:
                        target_ctx = context.setdefault(context_key, {})
                        if context_key == "lc" and "raw_text" not in target_ctx:
                            context["lc_text"] = extracted_text
                            target_ctx["source_type"] = document_type
                        target_ctx.update(context_payload)

                validation_doc_type = launch_pipeline_result.get("validation_doc_type")
                if validation_doc_type and context_key and isinstance(context.get(context_key), dict):
                    two_stage_started_at = time.perf_counter()
                    validated_payload, validation_summary = _apply_two_stage_validation(
                        context[context_key], validation_doc_type, filename, job_id=job_id
                    )
                    if context_key == "lc":
                        validated_payload = _repair_lc_mt700_dates(validated_payload) or validated_payload
                    context[context_key].update(validated_payload)
                    launch_pipeline_result.setdefault("doc_info_patch", {})["validation_summary"] = validation_summary
                    doc_info.setdefault("timings_ms", {})["two_stage_validation"] = round((time.perf_counter() - two_stage_started_at) * 1000, 2)
                    if context_key == "lc":
                        context["lc_structured_output"] = validated_payload

                if not support_only and launch_pipeline_result.get("lc_number") and not context.get("lc_number"):
                    context["lc_number"] = launch_pipeline_result.get("lc_number")

                if context_key == "lc" and not support_only:
                    lc_required_document_types = _infer_required_document_types_from_lc(context.get("lc") or {})
                    primary_lc_anchor_seen = True

                doc_info.update(launch_pipeline_result.get("doc_info_patch") or {})
                has_structured_data = bool(launch_pipeline_result.get("has_structured_data")) or has_structured_data

                if doc_info.get("extracted_fields"):
                    doc_info["raw_text_preview"] = extracted_text[:500]
                elif extracted_text:
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
                    if isinstance(context_payload.get("fact_graph_v1"), dict):
                        doc_info["fact_graph_v1"] = context_payload.get("fact_graph_v1")
                        doc_info["factGraphV1"] = context_payload.get("fact_graph_v1")
                    extraction_resolution = _extract_extraction_resolution_from_context_payload(context_payload)
                    if extraction_resolution:
                        doc_info["extraction_resolution"] = extraction_resolution
                        doc_info["extractionResolution"] = extraction_resolution

                doc_info.setdefault("_day1_runtime_hook", {})
                doc_info["_day1_runtime_hook"]["callsite_reached"] = True
                _enforce_day1_runtime_policy(doc_info, context_payload if isinstance(context_payload, dict) else {}, document_type, extracted_text)
                doc_info["_day1_runtime_hook"]["post_enforce_runtime_present"] = bool(isinstance(doc_info.get("day1_runtime"), dict) and doc_info.get("day1_runtime"))
                logger.info(
                    "validate.day1.hook file=%s doc_type=%s invoked=%s attached=%s runtime_present=%s",
                    filename,
                    document_type,
                    bool((doc_info.get("_day1_runtime_hook") or {}).get("invoked")),
                    bool((doc_info.get("_day1_runtime_hook") or {}).get("attached")),
                    bool((doc_info.get("_day1_runtime_hook") or {}).get("post_enforce_runtime_present")),
                )
                _apply_extraction_guard(doc_info, extracted_text)
                _finalize_text_backed_extraction_status(doc_info, document_type, extracted_text)
                _stabilize_document_review_semantics(doc_info, extracted_text)
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
                doc_info.setdefault("timings_ms", {})["document_total"] = round((time.perf_counter() - doc_process_started_at) * 1000, 2)
                logger.info(
                    "validate.extraction.timing file=%s doc_type=%s ocr_ms=%s launch_pipeline_ms=%s two_stage_ms=%s total_ms=%s",
                    filename,
                    document_type,
                    (doc_info.get("timings_ms") or {}).get("ocr"),
                    (doc_info.get("timings_ms") or {}).get("launch_pipeline"),
                    (doc_info.get("timings_ms") or {}).get("two_stage_validation"),
                    (doc_info.get("timings_ms") or {}).get("document_total"),
                )
                debug_extraction_trace.append(trace_payload)

                document_details.append(doc_info)
                entry = documents_presence.setdefault(
                    document_type,
                    {"present": False, "count": 0},
                )
                entry["present"] = True
                entry["count"] += 1
                continue
            else:
                # LaunchExtractionPipeline is the authoritative structured-extraction boundary.
                # If it does not handle a document, keep only raw text/native evidence here and
                # do not run a second route-owned extractor stack.
                doc_info["raw_text_preview"] = extracted_text[:500]
                if doc_info.get("extraction_status") in (None, "empty"):
                    doc_info["extraction_status"] = "text_only"
                extra_context = context.setdefault(document_type, {})
                if isinstance(extra_context, dict):
                    extra_context["raw_text"] = extra_context.get("raw_text") or extracted_text
                    extra_context["extraction_artifacts_v1"] = extraction_artifacts_v1
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
            if isinstance(context_payload.get("fact_graph_v1"), dict):
                doc_info["fact_graph_v1"] = context_payload.get("fact_graph_v1")
                doc_info["factGraphV1"] = context_payload.get("fact_graph_v1")

        doc_info.setdefault("_day1_runtime_hook", {})
        doc_info["_day1_runtime_hook"]["callsite_reached"] = True
        _enforce_day1_runtime_policy(doc_info, context_payload if isinstance(context_payload, dict) else {}, document_type, extracted_text)
        doc_info["_day1_runtime_hook"]["post_enforce_runtime_present"] = bool(isinstance(doc_info.get("day1_runtime"), dict) and doc_info.get("day1_runtime"))
        logger.info(
            "validate.day1.hook file=%s doc_type=%s invoked=%s attached=%s runtime_present=%s",
            filename,
            document_type,
            bool((doc_info.get("_day1_runtime_hook") or {}).get("invoked")),
            bool((doc_info.get("_day1_runtime_hook") or {}).get("attached")),
            bool((doc_info.get("_day1_runtime_hook") or {}).get("post_enforce_runtime_present")),
        )
        _apply_extraction_guard(doc_info, extracted_text)
        _finalize_text_backed_extraction_status(doc_info, document_type, extracted_text)
        _stabilize_document_review_semantics(doc_info, extracted_text)
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
    hook_docs = [doc for doc in (document_details or []) if isinstance(doc, dict)]
    context["_day1_hook_callsite_summary"] = {
        "documents_total": len(hook_docs),
        "day1_hook_attempted_docs": sum(1 for doc in hook_docs if bool((doc.get("_day1_runtime_hook") or {}).get("callsite_reached"))),
        "day1_hook_invoked_docs": sum(1 for doc in hook_docs if bool((doc.get("_day1_runtime_hook") or {}).get("invoked"))),
        "day1_hook_attached_docs": sum(1 for doc in hook_docs if bool((doc.get("_day1_runtime_hook") or {}).get("attached"))),
        "hook_filenames": [str(doc.get("filename") or doc.get("name") or "") for doc in hook_docs if bool((doc.get("_day1_runtime_hook") or {}).get("callsite_reached"))],
    }
    if context.get("lc"):
        context["lc"] = _backfill_lc_mt700_sources(
            _normalize_lc_payload_structures(context["lc"]),
            context,
        )
        context["lc"] = _repair_lc_mt700_dates(context["lc"]) or context["lc"]
        if not isinstance(context["lc"].get("lc_classification"), dict):
            context["lc"]["lc_classification"] = build_lc_classification(context["lc"], context)

    # GUARANTEE: Always provide lc_structured_output for Option-E builder
    # Even if extraction failed, provide a minimal structure
    if "lc_structured_output" not in context:
        lc_data = context.get("lc") or {}
        context["lc_structured_output"] = _build_minimal_lc_structured_output(lc_data, context)

    return context


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
            "extraction_lane": doc.get("extraction_lane") or doc.get("extractionLane"),
            "issues_count": 0,
            "raw_text_preview": doc.get("raw_text_preview"),  # Keep preview text
            "ocr_confidence": doc.get("ocr_confidence"),
            "review_required": bool(doc.get("review_required") or doc.get("reviewRequired")),
            "review_reasons": doc.get("review_reasons") or doc.get("reviewReasons") or [],
            "critical_field_states": doc.get("critical_field_states") or doc.get("criticalFieldStates") or {},
            "extraction_resolution": doc.get("extraction_resolution") or doc.get("extractionResolution"),
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
    _response_shaping.materialize_document_fact_graphs_v1(docs_structured)
    document_extraction = _build_document_extraction_v1(docs_structured)
    workflow_stage = _response_shaping.build_workflow_stage(
        document_extraction.get("documents", []),
        validation_status="blocked",
    )
    resolution_queue_v1 = _response_shaping.build_resolution_queue_v1(
        document_extraction.get("documents", [])
    )
    fact_resolution_v1 = _response_shaping.build_fact_resolution_v1(
        document_extraction.get("documents", []),
        workflow_stage=workflow_stage,
        resolution_queue=resolution_queue_v1,
    )
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
        "raw_submission_eligibility": {
            "can_submit": False,
            "reasons": ["validation_blocked"],
            "missing_reason_codes": eligibility_context["missing_reason_codes"],
            "unresolved_critical_fields": unresolved_critical_fields,
            "unresolved_critical_statuses": ["rejected"] if unresolved_critical_fields else [],
            "source": "validation",
        },
        "effective_submission_eligibility": {
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
        "resolution_queue_v1": resolution_queue_v1,
        "fact_resolution_v1": fact_resolution_v1,
        "workflow_stage": workflow_stage,
        "workflowStage": workflow_stage,
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

    def _coerce_sequence(value: Any) -> Any:
        parsed_value = _parse_json_if_possible(value)
        if isinstance(parsed_value, list):
            return parsed_value
        if isinstance(parsed_value, str):
            text = parsed_value.strip()
            if text.startswith("[") and text.endswith("]"):
                try:
                    import ast
                    coerced = ast.literal_eval(text)
                    if isinstance(coerced, list):
                        return coerced
                except Exception:
                    return [text]
            return [text] if text else []
        return value

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

    for list_key in ("documents_required", "required_documents", "additional_conditions", "clauses", "goods"):
        if list_key in parsed:
            parsed[list_key] = _coerce_sequence(parsed.get(list_key))

    if "goods_items" in parsed:
        parsed["goods_items"] = _coerce_goods_items(parsed.get("goods_items"))

    if not parsed.get("goods") and parsed.get("goods_description"):
        parsed["goods"] = [{"description": parsed.get("goods_description")}]

    mt700 = parsed.get("mt700")
    if isinstance(mt700, dict):
        blocks = mt700.get("blocks") or {}
        if isinstance(blocks, dict):
            sanitized_blocks = {k: v for k, v in blocks.items() if v not in (None, "", [], {})}
            mt700["blocks"] = sanitized_blocks
        mt700["raw_text"] = mt700.get("raw_text") or parsed.get("raw_text")
        parsed["mt700"] = mt700

    issuer = parsed.get("issuer")
    if isinstance(issuer, str):
        issuer_clean = issuer.strip()
        upper_issuer = issuer_clean.upper()
        if upper_issuer.startswith(("1)", "2)", "3)", "4)", "5)")) or "FULL SET CLEAN ON BOARD" in upper_issuer:
            parsed["issuer"] = None

    bl_number = parsed.get("bl_number")
    if isinstance(bl_number, str) and bl_number.strip().upper() in {"CONSIGNED", "TO ORDER", "TO THE ORDER"}:
        parsed["bl_number"] = None

    return parsed


def _set_nested_value(container: Dict[str, Any], path: Tuple[str, ...], value: Any) -> None:
    current = container
    for segment in path[:-1]:
        current = current.setdefault(segment, {})
    current[path[-1]] = value
from app.routers.validate_run import build_router as _build_validate_run_router
from app.routers.validate_customs import build_router as _build_validate_customs_router
from app.routers.validate_results import build_router as _build_validate_results_router

router.include_router(_build_validate_run_router(globals()))
router.include_router(_build_validate_customs_router(globals()))
router.include_router(_build_validate_results_router(globals()))
