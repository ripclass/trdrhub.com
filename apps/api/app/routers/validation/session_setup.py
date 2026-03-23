"""Validation session/input setup extracted from pipeline_runner.py."""

from __future__ import annotations

from typing import Any

from .lc_dates import backfill_lc_mt700_sources, repair_lc_mt700_dates


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


async def prepare_validation_session(
    *,
    request,
    current_user,
    db,
    payload,
    files_list,
    intake_only,
    checkpoint,
    start_time,
    runtime_context,
):
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
    runtime_context["validation_session"] = validation_session
    runtime_context["job_id"] = job_id

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
        normalized_lc = _normalize_lc_payload_structures(payload["lc"])
        normalized_lc = backfill_lc_mt700_sources(normalized_lc, extracted_context) or normalized_lc
        payload["lc"] = repair_lc_mt700_dates(normalized_lc) or normalized_lc

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
            "continuation_allowed": False,
            "intake_mode": bool(intake_only),
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
    extracted_workflow_lc_type = _extract_workflow_lc_type(lc_context)
    extracted_lc_type_confidence = lc_context.get("lc_type_confidence", 0)
    extracted_lc_type_reason = lc_context.get("lc_type_reason", "")

    # If extracted, use it; otherwise fall back to import/export detection
    override_lc_type = _extract_lc_type_override(payload)

    if extracted_workflow_lc_type:
        # Use extracted LC type from document
        lc_type = extracted_workflow_lc_type
        lc_type_reason = extracted_lc_type_reason or f"Extracted workflow from LC document: {extracted_workflow_lc_type}"
        lc_type_confidence = extracted_lc_type_confidence if extracted_lc_type_confidence > 0 else 0.85
        lc_type_source = lc_context.get("lc_type_source", "document_extraction")
        lc_type_guess = {"lc_type": lc_type, "reason": lc_type_reason, "confidence": lc_type_confidence}
        logger.info(f"LC type from document extraction: {lc_type} (confidence={lc_type_confidence})")
    else:
        # Fall back to import/export detection based on country relationships
        lc_type_guess = detect_lc_type(
            lc_context,
            shipment_context,
            request_context={
                "user_type": user_type,
                "workflow_type": payload.get("workflow_type") or payload.get("workflowType"),
                "company_country": getattr(current_user.company, "country", None) if getattr(current_user, "company", None) else None,
            },
        )
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
        "confidence_mode": lc_type_guess.get("confidence_mode"),
        "detection_basis": lc_type_guess.get("detection_basis"),
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
                "confidence_mode": lc_type_guess.get("confidence_mode"),
                "detection_basis": lc_type_guess.get("detection_basis"),
            },
            "message": dashboard_lc_mismatch["message"],
            "action_required": dashboard_lc_mismatch["action"],
            "redirect_url": dashboard_lc_mismatch["redirect_url"],
            "continuation_allowed": False,
            "intake_mode": bool(intake_only),
        }

    if intake_only:
        lc_summary = _build_lc_intake_summary(lc_context)
        required_documents_detailed = normalize_required_documents(lc_context)
        required_document_types = _infer_required_document_types_from_lc(lc_context)
        requirement_conditions = extract_requirement_conditions(lc_context)
        unmapped_requirements = extract_unmapped_requirements(lc_context)
        special_conditions = _coerce_text_list(
            lc_context.get("additional_conditions")
            or lc_context.get("clauses")
            or lc_context.get("clauses_47a")
        )
        documents_required = [
            str(item.get("raw_text") or item.get("display_name") or item.get("code")).strip()
            for item in required_documents_detailed
            if isinstance(item, dict) and str(item.get("raw_text") or item.get("display_name") or item.get("code")).strip()
        ]
        intake_status = "resolved" if has_lc_document else "invalid"
        return {
            "status": intake_status,
            "intake_mode": True,
            "continuation_allowed": bool(has_lc_document),
            "is_lc": bool(has_lc_document),
            "job_id": job_id,
            "jobId": job_id,
            "lc_detection": {
                "lc_type": lc_type,
                "confidence": lc_type_confidence,
                "reason": lc_type_reason,
                "is_draft": is_draft_lc,
                "source": lc_type_source,
                "confidence_mode": lc_type_guess.get("confidence_mode"),
                "detection_basis": lc_type_guess.get("detection_basis"),
            },
            "lc_summary": lc_summary,
            "required_document_types": required_document_types,
            "documents_required": documents_required,
            "required_documents_detailed": required_documents_detailed,
            "requirement_conditions": requirement_conditions,
            "unmapped_requirements": unmapped_requirements,
            "special_conditions": special_conditions,
            "detected_documents": [
                {
                    "type": doc.get("documentType") or doc.get("document_type"),
                    "filename": doc.get("name") or doc.get("filename"),
                    "document_type_resolution": doc.get("document_type_resolution"),
                }
                for doc in (extracted_context.get("documents") if extracted_context else []) or []
            ],
            "message": "LC intake resolved. Upload supporting documents next." if has_lc_document else "We could not confirm a valid LC.",
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

    return {
        "metadata": metadata,
        "user_type": user_type,
        "validation_session": validation_session,
        "job_id": job_id,
        "extracted_context": extracted_context,
        "documents_presence": documents_presence,
        "detected_doc_types": detected_doc_types,
        "has_lc_document": has_lc_document,
        "lc_context": lc_context,
        "shipment_context": shipment_context,
        "lc_type": lc_type,
        "lc_type_reason": lc_type_reason,
        "lc_type_confidence": lc_type_confidence,
        "lc_type_source": lc_type_source,
        "lc_type_guess": lc_type_guess,
        "lc_type_is_unknown": lc_type_is_unknown,
        "is_draft_lc": is_draft_lc,
    }


__all__ = ["bind_shared", "prepare_validation_session"]
