"""
Validation Router Modules

Split from the monolithic validate.py for maintainability.
Each module has a single responsibility.
"""

from .utilities import (
    # Severity utilities
    severity_rank,
    severity_to_status,
    normalize_issue_severity,
    priority_to_severity,
    # String utilities
    normalize_doc_match_key,
    strip_extension,
    coerce_issue_value,
    format_duration,
    # Field filtering
    filter_user_facing_fields,
)

from .doc_types import (
    label_to_doc_type,
    normalize_doc_type_key,
    humanize_doc_type,
    infer_document_type_from_name,
    fallback_doc_type,
)

from .issue_attribution import (
    resolve_issue_stats,
    collect_document_issue_stats,
    extract_document_names,
    extract_document_types,
    extract_document_ids,
    bump_issue_entry,
)

from .issue_resolver import (
    count_issue_severity,
    format_deterministic_issue,
)

from .document_builder import (
    build_document_summaries,
    build_document_lookup,
    match_issue_documents,
    build_documents_section,
)

from .response_builder import (
    compose_processing_summary,
    build_analytics_section,
    build_timeline_entries,
    build_document_processing_analytics,
    summarize_document_statuses,
)

from .lc_dates import (
    coerce_mt700_date_iso,
    extract_mt700_block_value,
    extract_mt700_timeline_fields,
    repair_lc_mt700_dates,
)

from .lc_intake import (
    extract_intake_only,
    coerce_text_list,
    infer_required_document_types_from_lc,
    resolve_legacy_workflow_lc_fields,
    prepare_extractor_outputs_for_structured_result,
    build_minimal_lc_structured_output,
    build_lc_intake_summary,
)

from .review_policy import (
    count_populated_canonical_fields,
    apply_extraction_guard,
    finalize_text_backed_extraction_status,
    stabilize_document_review_semantics,
    context_payload_for_doc_type,
    extract_day1_raw_candidates,
    day1_policy_for_doc,
    enforce_day1_runtime_policy,
    is_populated_field_value,
    assess_required_field_completeness,
    assess_coo_parse_completeness,
)

from .issues_pipeline import (
    _build_issue_context,
    _apply_issue_rewrite,
    _extract_field_decisions_from_payload,
    _build_document_field_hint_index,
    _build_unresolved_critical_context,
    _augment_doc_field_details_with_decisions,
    _augment_issues_with_field_decisions,
)

from .presentation_contract import (
    _classify_reason_semantics,
    _extract_rule_evidence_items,
    _classify_rules_signal_classes,
    _build_validation_contract,
    _run_validation_arbitration_escalation,
    _build_submission_eligibility_context,
)

from .ocr_runtime import (
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
)

__all__ = [
    # Utilities
    "severity_rank",
    "severity_to_status",
    "normalize_issue_severity",
    "priority_to_severity",
    "label_to_doc_type",
    "normalize_doc_type_key",
    "humanize_doc_type",
    "infer_document_type_from_name",
    "fallback_doc_type",
    "normalize_doc_match_key",
    "strip_extension",
    "coerce_issue_value",
    "format_duration",
    "filter_user_facing_fields",
    # Issue resolver
    "resolve_issue_stats",
    "collect_document_issue_stats",
    "extract_document_names",
    "extract_document_types",
    "extract_document_ids",
    "bump_issue_entry",
    "count_issue_severity",
    "format_deterministic_issue",
    # Document builder
    "build_document_summaries",
    "build_document_lookup",
    "match_issue_documents",
    "build_documents_section",
    # Response builder
    "compose_processing_summary",
    "build_analytics_section",
    "build_timeline_entries",
    "build_document_processing_analytics",
    "summarize_document_statuses",
    # LC dates / intake
    "coerce_mt700_date_iso",
    "extract_mt700_block_value",
    "extract_mt700_timeline_fields",
    "repair_lc_mt700_dates",
    "extract_intake_only",
    "coerce_text_list",
    "infer_required_document_types_from_lc",
    "resolve_legacy_workflow_lc_fields",
    "prepare_extractor_outputs_for_structured_result",
    "build_minimal_lc_structured_output",
    "build_lc_intake_summary",
    # Review policy
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
    # Issues / presentation contract
    "_build_issue_context",
    "_apply_issue_rewrite",
    "_extract_field_decisions_from_payload",
    "_build_document_field_hint_index",
    "_build_unresolved_critical_context",
    "_augment_doc_field_details_with_decisions",
    "_augment_issues_with_field_decisions",
    "_classify_reason_semantics",
    "_extract_rule_evidence_items",
    "_classify_rules_signal_classes",
    "_build_validation_contract",
    "_run_validation_arbitration_escalation",
    "_build_submission_eligibility_context",
    # OCR runtime
    "_empty_extraction_artifacts_v1",
    "_extraction_fallback_hotfix_enabled",
    "_ocr_compatibility_v1_enabled",
    "_stage_promotion_v1_enabled",
    "_ocr_adapter_runtime_payload_fix_v1_enabled",
    "_stage_threshold_tuning_v1_enabled",
    "_record_extraction_reason_code",
    "_record_extraction_stage",
    "_merge_extraction_artifacts",
    "_finalize_text_extraction_result",
    "_merge_text_sources",
    "_build_extraction_artifacts_from_ocr",
    "_scrape_binary_text_metadata",
    "_detect_input_mime_type",
    "_looks_like_plaintext_bytes",
    "_extract_plaintext_bytes",
    "_normalize_ocr_input",
    "_prepare_provider_ocr_payload",
    "_provider_runtime_limits",
    "_pdf_page_count",
    "_render_pdf_runtime_images",
    "_normalize_runtime_image_bytes",
    "_build_runtime_payload_entry",
    "_build_google_docai_payload_plan",
    "_build_textract_payload_plan",
    "_build_provider_runtime_payload_plan",
    "_build_provider_attempt_record",
    "_map_ocr_provider_error_code",
    "_get_viable_ocr_providers",
    "_score_stage_candidate",
    "_select_best_extraction_stage",
    "_extract_text_from_upload",
    "_try_secondary_ocr_adapter",
    "_try_ocr_providers",
]

