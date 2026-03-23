"""Validation pipeline runner extracted from validate_run.py."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from app.routers.validation.result_finalization import bind_shared as bind_result_finalization_shared
from app.routers.validation.result_finalization import finalize_validation_result
from app.routers.validation.session_setup import bind_shared as bind_session_setup_shared
from app.routers.validation.session_setup import prepare_validation_session
from app.routers.validation.validation_execution import bind_shared as bind_validation_execution_shared
from app.routers.validation.validation_execution import execute_validation_pipeline


_SHARED_NAMES = ['Any', 'AuditAction', 'AuditResult', 'AuditService', 'Company', 'CompanyStatus', 'ComplianceScorer', 'CrossDocValidator', 'Decimal', 'Depends', 'Dict', 'Document', 'EntitlementError', 'EntitlementService', 'HTTPException', 'IssueEngine', 'LCType', 'List', 'Optional', 'PlanType', 'Request', 'Session', 'SessionStatus', 'UsageAction', 'User', 'ValidationGate', 'ValidationSessionService', '_apply_cycle2_runtime_recovery', '_augment_doc_field_details_with_decisions', '_augment_issues_with_field_decisions', '_backfill_hybrid_secondary_surfaces', '_build_bank_submission_verdict', '_build_blocked_structured_result', '_build_day1_relay_debug', '_build_document_context', '_build_document_extraction_v1', '_build_document_summaries', '_build_extraction_core_bundle', '_build_issue_dedup_key', '_build_issue_provenance_v1', '_build_lc_baseline_from_context', '_build_lc_intake_summary', '_build_processing_summary', '_build_processing_summary_v2', '_build_submission_eligibility_context', '_build_validation_contract', '_coerce_text_list', '_compute_invoice_amount_bounds', '_count_issue_severity', '_determine_company_size', '_empty_extraction_artifacts_v1', '_extract_field_decisions_from_payload', '_extract_intake_only', '_extract_lc_type_override', '_extract_request_user_type', '_extract_workflow_lc_type', '_infer_required_document_types_from_lc', '_normalize_lc_payload_structures', '_prepare_extractor_outputs_for_structured_result', '_resolve_shipment_context', '_response_shaping', '_run_validation_arbitration_escalation', '_sync_structured_result_collections', 'adapt_from_structured_result', 'apply_bank_policy', 'batch_lookup_descriptions', 'build_customs_manifest_from_option_e', 'build_issue_cards', 'build_lc_classification', 'build_unified_structured_result', 'calculate_overall_extraction_confidence', 'calculate_total_amendment_cost', 'compute_customs_risk_from_option_e', 'context', 'copy', 'country_str', 'create_audit_context', 'detect_bank_from_lc', 'detect_lc_type', 'detect_lc_type_ai', 'enforce_day1_response_contract', 'extract_requirement_conditions', 'extract_unmapped_requirements', 'func', 'generate_amendments_for_issues', 'get_bank_profile', 'get_db', 'get_user_optional', 'json', 'logger', 'logging', 'name', 'normalize_required_documents', 'parse_lc_requirements_sync_v2', 'record_usage_manual', 'ref', 'run_ai_validation', 'run_price_verification_checks', 'run_sanctions_screening_for_validation', 'settings', 'status', 'time', 'traceback', 'uuid4', 'validate_and_annotate_response', 'validate_doc', 'validate_document_async', 'validate_document_set_completeness', 'validate_upload_file']


def _shared_get(shared: Any, name: str) -> Any:
    if isinstance(shared, dict):
        return shared[name]
    return getattr(shared, name)


def bind_shared(shared: Any) -> None:
    namespace = globals()
    for name in _SHARED_NAMES:
        if name in namespace:
            continue
        try:
            namespace[name] = _shared_get(shared, name)
        except (KeyError, AttributeError):
            continue
    bind_stage_modules(shared)


async def run_validate_pipeline(
    *,
    request,
    current_user,
    db,
    payload,
    files_list,
    doc_type,
    intake_only,
    start_time,
    timings,
    checkpoint,
    audit_service,
    audit_context,
    runtime_context,
):
    setup_state = await prepare_validation_session(
        request=request,
        current_user=current_user,
        db=db,
        payload=payload,
        files_list=files_list,
        intake_only=intake_only,
        checkpoint=checkpoint,
        start_time=start_time,
        runtime_context=runtime_context,
    )
    if isinstance(setup_state, dict) and ("status" in setup_state or "structured_result" in setup_state):
        return setup_state

    execution_state = await execute_validation_pipeline(
        request=request,
        current_user=current_user,
        db=db,
        payload=payload,
        files_list=files_list,
        doc_type=doc_type,
        checkpoint=checkpoint,
        start_time=start_time,
        setup_state=setup_state,
    )
    if isinstance(execution_state, dict) and "structured_result" in execution_state and "telemetry" in execution_state:
        return execution_state

    return await finalize_validation_result(
        request=request,
        current_user=current_user,
        db=db,
        payload=payload,
        files_list=files_list,
        start_time=start_time,
        timings=timings,
        checkpoint=checkpoint,
        audit_service=audit_service,
        audit_context=audit_context,
        setup_state=setup_state,
        execution_state=execution_state,
    )


def bind_stage_modules(shared: Any) -> None:
    bind_session_setup_shared(shared)
    bind_validation_execution_shared(shared)
    bind_result_finalization_shared(shared)


__all__ = ["bind_shared", "bind_stage_modules", "run_validate_pipeline"]
