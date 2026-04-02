"""Validation result finalization extracted from pipeline_runner.py."""

from __future__ import annotations

import asyncio
import math
from dataclasses import asdict, is_dataclass
from datetime import date, datetime, time as dt_time
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List
from uuid import UUID, uuid4


_SHARED_NAMES = [
    'Any',
    'AuditAction',
    'AuditResult',
    'ComplianceScorer',
    'HTTPException',
    'SessionStatus',
    '_apply_cycle2_runtime_recovery',
    '_apply_validation_contract_decision_surfaces',
    '_apply_workflow_stage_contract_overrides',
    '_augment_doc_field_details_with_decisions',
    '_augment_issues_with_field_decisions',
    '_backfill_hybrid_secondary_surfaces',
    '_build_bank_submission_verdict',
    '_build_day1_relay_debug',
    '_build_document_extraction_v1',
    '_build_document_summaries',
    '_build_extraction_core_bundle',
    '_build_issue_provenance_v1',
    '_build_processing_summary_v2',
    '_build_submission_eligibility_context',
    '_build_validation_contract',
    '_count_issue_severity',
    '_extract_field_decisions_from_payload',
    '_partition_workflow_stage_issues',
    '_prepare_extractor_outputs_for_structured_result',
    '_response_shaping',
    '_run_validation_arbitration_escalation',
    '_sync_structured_result_collections',
    'build_customs_manifest_from_option_e',
    'build_unified_structured_result',
    'calculate_total_amendment_cost',
    'compute_customs_risk_from_option_e',
    'copy',
    'enforce_day1_response_contract',
    'func',
    'generate_amendments_for_issues',
    'json',
    'logger',
    'record_usage_manual',
    'run_sanctions_screening_for_validation',
    'settings',
    'status',
    'time',
    'validate_and_annotate_response',
]

SANCTIONS_TIMEOUT_SECONDS = 25.0
ARBITRATION_TIMEOUT_SECONDS = 15.0
USAGE_RECORD_TIMEOUT_SECONDS = 10.0


def _shared_get(shared: Any, name: str) -> Any:
    if isinstance(shared, dict):
        return shared[name]
    return getattr(shared, name)


def bind_shared(shared: Any) -> None:
    namespace = globals()
    missing_bindings: list[str] = []
    for name in _SHARED_NAMES:
        if name in namespace:
            continue
        try:
            namespace[name] = _shared_get(shared, name)
        except (KeyError, AttributeError):
            missing_bindings.append(name)
    if missing_bindings:
        raise RuntimeError(
            "Missing shared bindings for validation.result_finalization: "
            + ", ".join(sorted(missing_bindings))
        )


def _make_json_safe(value: Any) -> Any:
    """
    Recursively coerce runtime payloads into JSON-safe values.

    Degraded OCR/AI paths can surface values that are safe in Python but can fail
    JSON column persistence or HTTP serialization later in the pipeline.
    """
    if value is None or isinstance(value, (str, bool, int)):
        return value

    if isinstance(value, float):
        return value if math.isfinite(value) else None

    if isinstance(value, Decimal):
        try:
            coerced = float(value)
        except Exception:
            return str(value)
        return coerced if math.isfinite(coerced) else None

    if isinstance(value, (datetime, date, dt_time)):
        return value.isoformat()

    if isinstance(value, UUID):
        return str(value)

    if isinstance(value, Enum):
        return _make_json_safe(value.value)

    if isinstance(value, (bytes, bytearray, memoryview)):
        try:
            decoded = bytes(value).decode("utf-8")
            if decoded.isprintable():
                return decoded
        except Exception:
            pass
        return f"<binary:{len(bytes(value))} bytes>"

    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            sanitized[str(key)] = _make_json_safe(item)
        return sanitized

    if isinstance(value, (list, tuple, set)):
        return [_make_json_safe(item) for item in value]

    if hasattr(value, "model_dump") and callable(value.model_dump):
        try:
            return _make_json_safe(value.model_dump())
        except Exception:
            return str(value)

    if is_dataclass(value):
        try:
            return _make_json_safe(asdict(value))
        except Exception:
            return str(value)

    if hasattr(value, "to_dict") and callable(value.to_dict):
        try:
            return _make_json_safe(value.to_dict())
        except Exception:
            return str(value)

    return str(value)


def _suppress_advisory_findings_for_documentary_context(
    issues: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Keep documentary goods-mismatch findings primary in SME LC results.
    If the document set already has a direct goods inconsistency, suppress
    layered PRICE-VERIFY advisory/TBML findings from the final issue list.
    """
    if not issues:
        return []

    rules = {
        str(issue.get("rule") or issue.get("rule_id") or "").strip().upper()
        for issue in issues
        if isinstance(issue, dict)
    }
    has_goods_overlap = False
    for issue in issues:
        if not isinstance(issue, dict):
            continue
        overlap_keys = issue.get("overlap_keys")
        if not isinstance(overlap_keys, list):
            continue
        if any(
            str(key or "").strip() == "invoice.goods_description|lc.goods_description"
            for key in overlap_keys
        ):
            has_goods_overlap = True
            break
    if not has_goods_overlap and not rules.intersection({"CROSSDOC-INV-003", "CROSSDOC-GOODS-1"}):
        return issues

    return [
        issue
        for issue in issues
        if str(issue.get("rule") or issue.get("rule_id") or "").strip().upper()
        not in {"PRICE-VERIFY-1", "PRICE-VERIFY-2"}
    ]


def _retire_legacy_sanctions_block_surface(
    structured_result: dict[str, Any],
) -> dict[str, Any]:
    """
    Keep sanctions findings visible through structured issues and
    sanctions_screening, but retire the old boolean block surface so it cannot
    contradict validation_contract_v1.
    """
    if not isinstance(structured_result, dict):
        return {}

    sanctions_summary = structured_result.get("sanctions_screening")
    if isinstance(sanctions_summary, dict):
        sanctions_summary["legacy_block_surface_retired"] = True

    structured_result["sanctions_blocked"] = False
    structured_result["sanctions_block_reason"] = None
    return structured_result


def _resolve_result_user_type(request_user_type: Any, current_user: Any) -> str:
    explicit_user_type = str(request_user_type or "").strip().lower()
    if explicit_user_type:
        return explicit_user_type

    if current_user is None:
        return "unknown"

    role = getattr(current_user, "role", None)
    if role is None:
        return "unknown"

    enum_like_value = getattr(role, "value", None)
    if isinstance(enum_like_value, str) and enum_like_value.strip():
        return enum_like_value.strip().lower()

    role_text = str(role).strip().lower()
    return role_text or "unknown"


def _build_timeout_event(
    *,
    stage: str,
    label: str,
    timeout_seconds: float,
    fallback: str,
    source: str = "result_finalization",
) -> dict[str, Any]:
    return {
        "stage": stage,
        "label": label,
        "timeout_seconds": float(timeout_seconds),
        "fallback": fallback,
        "source": source,
    }


def _build_degraded_execution_summary(
    timeout_events: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    normalized_events: list[dict[str, Any]] = []
    for event in timeout_events or []:
        if not isinstance(event, dict):
            continue
        normalized_events.append(
            {
                "stage": str(event.get("stage") or "").strip(),
                "label": str(event.get("label") or "").strip(),
                "timeout_seconds": float(event.get("timeout_seconds") or 0.0),
                "fallback": str(event.get("fallback") or "").strip(),
                "source": str(event.get("source") or "").strip() or "unknown",
            }
        )

    stage_keys = {
        event["stage"]
        for event in normalized_events
        if event.get("stage")
    }
    return {
        "degraded": bool(normalized_events),
        "timeout_event_count": len(normalized_events),
        "stage_count": len(stage_keys),
        "timeout_events": normalized_events,
    }


async def _await_with_timeout(stage_label: str, coro, timeout_seconds: float, default: Any):
    try:
        return await asyncio.wait_for(coro, timeout_seconds), False
    except asyncio.TimeoutError:
        logger.warning(
            "%s timed out after %.1fs; continuing with degraded fallback",
            stage_label,
            timeout_seconds,
        )
        return default, True


async def finalize_validation_result(
    *,
    request,
    current_user,
    db,
    payload,
    files_list,
    start_time,
    timings,
    checkpoint,
    audit_service,
    audit_context,
    setup_state,
    execution_state,
):
    validation_session = setup_state["validation_session"]
    job_id = setup_state["job_id"]
    extracted_context = setup_state["extracted_context"]
    lc_context = setup_state["lc_context"]
    mt700 = lc_context.get("mt700") or {}

    v2_gate_result = execution_state["v2_gate_result"]
    v2_baseline = execution_state["v2_baseline"]
    db_rules_debug = execution_state["db_rules_debug"]
    bank_profile = execution_state["bank_profile"]
    requirement_graph = execution_state["requirement_graph"]
    extraction_confidence_summary = execution_state["extraction_confidence_summary"]
    ai_validation_summary = execution_state.get("ai_validation_summary")
    request_user_type = execution_state["request_user_type"]
    results = execution_state["results"]
    failed_results = execution_state["failed_results"]
    deduplicated_results = execution_state["deduplicated_results"]
    issue_cards = execution_state["issue_cards"]
    document_summaries = execution_state["document_summaries"]
    processing_duration = execution_state["processing_duration"]
    processing_summary = execution_state["processing_summary"]
    timeout_events = list(execution_state.get("timeout_events") or [])

    # Ensure document_summaries is a list (fallback to empty if malformed)
    final_documents = document_summaries if isinstance(document_summaries, list) else []

    # GUARANTEE: Always have non-empty documents for Option-E
    if not final_documents:
        logger.warning("final_documents empty - using files_list fallback")
        final_documents = _build_document_summaries(files_list, results, None)

    # Build extractor outputs from payload or extracted context
    extractor_outputs = _prepare_extractor_outputs_for_structured_result(payload)

    # Build Option-E structured result with proper error handling
    try:
        option_e_payload = build_unified_structured_result(
            session_documents=final_documents,
            extractor_outputs=extractor_outputs,
            legacy_payload=None,
        )
        structured_result = option_e_payload["structured_result"]
        if isinstance(ai_validation_summary, dict):
            structured_result["ai_validation"] = ai_validation_summary
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

        # Extract LC terms for requirement detection. Build the requirements graph
        # before document-set completeness so missing required docs are visible
        # in the same pass instead of appearing only after later response shaping.
        lc_terms = dict(structured_result.get("lc_data", {}) or {})
        requirements_graph_v1 = structured_result.get("requirements_graph_v1")
        if not isinstance(requirements_graph_v1, dict):
            requirements_graph_documents = (
                payload.get("documents")
                or structured_result.get("documents_structured")
                or structured_result.get("documents")
                or doc_list_for_composition
            )
            requirements_graph_v1 = _response_shaping.build_requirements_graph_v1(
                requirements_graph_documents
            )
            if isinstance(requirements_graph_v1, dict):
                structured_result["requirements_graph_v1"] = requirements_graph_v1
        if isinstance(requirements_graph_v1, dict):
            lc_terms["requirements_graph_v1"] = requirements_graph_v1
            lc_terms["requirementsGraphV1"] = requirements_graph_v1

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
        structured_result["issues"] = _suppress_advisory_findings_for_documentary_context(
            structured_result["issues"]
        )
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

        (
            updated_issues,
            sanctions_should_block,
            sanctions_summary,
        ), sanctions_timed_out = await _await_with_timeout(
            "Sanctions screening",
            run_sanctions_screening_for_validation(
                payload=payload,
                existing_issues=current_issues,
            ),
            SANCTIONS_TIMEOUT_SECONDS,
            (
                current_issues,
                False,
                {
                    "screened": False,
                    "timed_out": True,
                    "error": "sanctions screening timed out",
                },
            ),
        )

        # Update issues with sanctions results
        structured_result["issues"] = updated_issues

        # Add sanctions summary to result
        structured_result["sanctions_screening"] = sanctions_summary
        if sanctions_timed_out and isinstance(structured_result["sanctions_screening"], dict):
            structured_result["sanctions_screening"]["timed_out"] = True
            timeout_events.append(
                _build_timeout_event(
                    stage="sanctions_screening",
                    label="Sanctions screening",
                    timeout_seconds=SANCTIONS_TIMEOUT_SECONDS,
                    fallback="sanctions_overlay_skipped",
                )
            )

        if sanctions_should_block:
            logger.warning(
                "SANCTIONS MATCH DETECTED - LC processing should be blocked. "
                f"Summary: {sanctions_summary}"
            )
        _retire_legacy_sanctions_block_surface(structured_result)

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
            documents=payload.get("documents") or structured_result.get("documents") or structured_result.get("documents_structured") or [],
        )

        structured_result["submission_eligibility"] = {
            "can_submit": submission_can_submit,
            "reasons": submission_reasons,
            "missing_reason_codes": eligibility_context["missing_reason_codes"],
            "unresolved_critical_fields": eligibility_context["unresolved_critical_fields"],
            "unresolved_critical_statuses": eligibility_context["unresolved_critical_statuses"],
            "source": "validation",
        }
        structured_result["raw_submission_eligibility"] = copy.deepcopy(structured_result["submission_eligibility"])
        structured_result["effective_submission_eligibility"] = copy.deepcopy(structured_result["submission_eligibility"])

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
                "country": getattr(bank_profile, "country", "") or "",
                "region": getattr(bank_profile, "region", "") or "",
                "source_issuing_bank": lc_context.get("issuing_bank") or mt700.get("issuing_bank") or "",
                "source_advising_bank": lc_context.get("advising_bank") or mt700.get("advising_bank") or "",
                "special_requirements": list(getattr(bank_profile, "special_requirements", []) or []),
                "blocked_conditions": list(getattr(bank_profile, "blocked_conditions", []) or []),
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

        _response_shaping.materialize_document_fact_graphs_v1(document_summaries)
        structured_result["document_extraction_v1"] = _build_document_extraction_v1(
            document_summaries
        )
        workflow_stage = _response_shaping.build_workflow_stage(
            structured_result["document_extraction_v1"].get("documents", []),
            validation_status=structured_result.get("validation_status"),
        )
        structured_result["workflow_stage"] = workflow_stage
        structured_result["workflowStage"] = workflow_stage
        structured_result["requirements_graph_v1"] = _response_shaping.build_requirements_graph_v1(
            structured_result["document_extraction_v1"].get("documents", []),
        )
        structured_result["resolution_queue_v1"] = _response_shaping.build_resolution_queue_v1(
            structured_result["document_extraction_v1"].get("documents", []),
            workflow_stage=workflow_stage,
        )
        structured_result["fact_resolution_v1"] = _response_shaping.build_fact_resolution_v1(
            structured_result["document_extraction_v1"].get("documents", []),
            workflow_stage=workflow_stage,
            resolution_queue=structured_result.get("resolution_queue_v1"),
        )
        issue_partition = _partition_workflow_stage_issues(
            structured_result.get("issues") or [],
            structured_result["document_extraction_v1"].get("documents", []),
            workflow_stage,
        )
        if issue_partition["provisional_issues"]:
            structured_result["issues"] = issue_partition["final_issues"]
            structured_result["_provisional_issues"] = issue_partition["provisional_issues"]
            severity_breakdown = _count_issue_severity(structured_result["issues"])
            processing_summary_v2["total_issues"] = len(structured_result["issues"])
            processing_summary_v2["discrepancies"] = len(structured_result["issues"])
            processing_summary_v2["severity_breakdown"] = {
                "critical": severity_breakdown.get("critical", 0),
                "major": severity_breakdown.get("major", 0),
                "medium": 0,
                "minor": severity_breakdown.get("minor", 0),
            }
            logger.info(
                "Workflow stage partitioned %d provisional issue(s) out of final results",
                len(issue_partition["provisional_issues"]),
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
        if isinstance(structured_result.get("validation_contract_v1"), dict):
            structured_result["analytics"]["validation_contract_v1"] = structured_result.get("validation_contract_v1")

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
            documents=payload.get("documents") or structured_result.get("documents") or structured_result.get("documents_structured") or [],
        )

        structured_result["submission_eligibility"] = {
            "can_submit": can_submit,
            "reasons": submission_reasons,
            "missing_reason_codes": eligibility_context["missing_reason_codes"],
            "unresolved_critical_fields": eligibility_context["unresolved_critical_fields"],
            "unresolved_critical_statuses": eligibility_context["unresolved_critical_statuses"],
            "source": "validation",
        }
        structured_result["raw_submission_eligibility"] = copy.deepcopy(structured_result["submission_eligibility"])
        structured_result["effective_submission_eligibility"] = copy.deepcopy(structured_result["submission_eligibility"])
        structured_result["validation_contract_v1"] = _build_validation_contract(
            structured_result.get("ai_validation"),
            bank_verdict,
            structured_result.get("gate_result") or {},
            structured_result.get("effective_submission_eligibility") or structured_result.get("submission_eligibility") or {},
            issues=structured_result.get("issues") or [],
        )
        contract_payload, arbitration_timed_out = await _await_with_timeout(
            "Validation arbitration escalation",
            _run_validation_arbitration_escalation(
                structured_result.get("validation_contract_v1") or {},
                structured_result.get("ai_validation") or {},
                bank_verdict,
                structured_result.get("effective_submission_eligibility") or structured_result.get("submission_eligibility") or {},
            ),
            ARBITRATION_TIMEOUT_SECONDS,
            structured_result.get("validation_contract_v1") or {},
        )
        structured_result["validation_contract_v1"] = contract_payload
        if arbitration_timed_out and isinstance(structured_result["validation_contract_v1"], dict):
            structured_result["validation_contract_v1"]["timed_out"] = True
            timeout_events.append(
                _build_timeout_event(
                    stage="validation_arbitration",
                    label="Validation arbitration escalation",
                    timeout_seconds=ARBITRATION_TIMEOUT_SECONDS,
                    fallback="pre_arbitration_contract",
                )
            )
        workflow_overrides = _apply_workflow_stage_contract_overrides(
            structured_result.get("workflow_stage") or structured_result.get("workflowStage"),
            structured_result.get("bank_verdict"),
            structured_result.get("effective_submission_eligibility")
            or structured_result.get("submission_eligibility"),
            structured_result.get("validation_contract_v1"),
            resolution_queue=structured_result.get("resolution_queue_v1"),
        )
        structured_result["bank_verdict"] = workflow_overrides["bank_verdict"]
        structured_result["submission_eligibility"] = workflow_overrides["submission_eligibility"]
        structured_result["raw_submission_eligibility"] = copy.deepcopy(
            structured_result["submission_eligibility"]
        )
        structured_result["effective_submission_eligibility"] = copy.deepcopy(
            structured_result["submission_eligibility"]
        )
        structured_result["validation_contract_v1"] = workflow_overrides["validation_contract"]
        aligned_contract_surfaces = _apply_validation_contract_decision_surfaces(
            structured_result.get("bank_verdict"),
            structured_result.get("effective_submission_eligibility")
            or structured_result.get("submission_eligibility"),
            structured_result.get("validation_contract_v1"),
        )
        structured_result["bank_verdict"] = aligned_contract_surfaces["bank_verdict"]
        structured_result["submission_eligibility"] = aligned_contract_surfaces["submission_eligibility"]
        structured_result["raw_submission_eligibility"] = copy.deepcopy(
            structured_result["submission_eligibility"]
        )
        structured_result["effective_submission_eligibility"] = copy.deepcopy(
            structured_result["submission_eligibility"]
        )
        structured_result["validation_contract_v1"] = aligned_contract_surfaces["validation_contract"]
        structured_result["final_verdict"] = structured_result["validation_contract_v1"].get("final_verdict")
        structured_result.setdefault("processing_summary", {})
        structured_result["processing_summary"]["bank_verdict"] = (
            structured_result["bank_verdict"].get("verdict")
        )
        structured_result.setdefault("analytics", {})
        structured_result["analytics"]["validation_contract_v1"] = copy.deepcopy(
            structured_result["validation_contract_v1"]
        )
    except Exception as contract_err:
        logger.warning("Failed to build Phase A contracts: %s", contract_err, exc_info=True)

    degraded_execution = _build_degraded_execution_summary(timeout_events)
    structured_result["_degraded_execution_v1"] = copy.deepcopy(degraded_execution)
    telemetry_payload = {
        "UnifiedStructuredResultBuilt": True,
        "documents": len(structured_result.get("documents_structured", [])),
        "issues": len(structured_result.get("issues", [])),
        # Timing breakdown for performance analysis
        "timings": timings,
        "total_time_seconds": round(time.time() - start_time, 3),
        "degraded_execution": degraded_execution,
    }

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
            "user_type": _resolve_result_user_type(request_user_type, current_user),
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
            _, usage_record_timed_out = await _await_with_timeout(
                "Usage recording",
                record_usage_manual(
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
                ),
                USAGE_RECORD_TIMEOUT_SECONDS,
                None,
            )
            if usage_record_timed_out:
                logger.warning("Usage tracking timed out for validation job %s", job_id)
                timeout_events.append(
                    _build_timeout_event(
                        stage="usage_recording",
                        label="Usage recording",
                        timeout_seconds=USAGE_RECORD_TIMEOUT_SECONDS,
                        fallback="usage_record_skipped",
                    )
                )
        except Exception as usage_err:
            logger.warning(f"Failed to track usage: {usage_err}")

    degraded_execution = _build_degraded_execution_summary(timeout_events)
    structured_result["_degraded_execution_v1"] = copy.deepcopy(degraded_execution)
    telemetry_payload["degraded_execution"] = degraded_execution

    # =====================================================================
    # CONTRACT VALIDATION (Output-First Layer)
    # Validates response completeness and adds warnings for missing data
    # =====================================================================
    try:
        structured_result.pop("_validation_contract_error", None)
        structured_result = validate_and_annotate_response(structured_result)
        structured_result = _apply_cycle2_runtime_recovery(structured_result)
        structured_result = _backfill_hybrid_secondary_surfaces(structured_result)
        structured_result["_day1_hook_callsite_summary"] = payload.get("_day1_hook_callsite_summary") if isinstance(payload.get("_day1_hook_callsite_summary"), dict) else {}
        structured_result["_day1_relay_debug"] = _build_day1_relay_debug(structured_result)
        relay_surfaces = (structured_result.get("_day1_relay_debug") or {}).get("surfaces")
        if isinstance(relay_surfaces, dict):
            compact = {
                key: {
                    "docs": len(value or []),
                    "runtime_present": sum(1 for doc in (value or []) if isinstance(doc, dict) and doc.get("runtime_present")),
                }
                for key, value in relay_surfaces.items()
            }
            logger.info("validate.day1.relay surfaces=%s", compact)

        if bool(getattr(settings, "DAY1_CONTRACT_ENABLED", False)):
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
        else:
            logger.info("Day1 response contract overlay disabled (DAY1_CONTRACT_ENABLED=false)")
    except Exception as contract_err:
        structured_result["_validation_contract_error"] = str(contract_err)
        logger.warning(f"Contract validation failed (non-blocking): {contract_err}")

    structured_result = _make_json_safe(structured_result)
    telemetry_payload = _make_json_safe(telemetry_payload)
    db_rules_debug = _make_json_safe(db_rules_debug)

    if validation_session:
        validation_session.validation_results = {"structured_result": structured_result}
        validation_session.status = SessionStatus.COMPLETED.value
        validation_session.processing_completed_at = func.now()
        db.commit()
        db.refresh(validation_session)
    else:
        db.commit()

    # Add DB rules debug info to response
    structured_result["_db_rules_debug"] = db_rules_debug

    return _make_json_safe(
        _response_shaping.build_public_validation_envelope(
            job_id=str(job_id),
            structured_result=structured_result,
            telemetry=telemetry_payload,
        )
    )



__all__ = ["bind_shared", "finalize_validation_result"]
