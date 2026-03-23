"""Validation run routes split from validate.py."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter


_SHARED_NAMES = ['Any', 'AuditAction', 'AuditResult', 'AuditService', 'Company', 'CompanyStatus', 'ComplianceScorer', 'CrossDocValidator', 'Decimal', 'Depends', 'Dict', 'Document', 'EntitlementError', 'EntitlementService', 'HTTPException', 'IssueEngine', 'LCType', 'List', 'Optional', 'PlanType', 'Request', 'Session', 'SessionStatus', 'UsageAction', 'User', 'ValidationGate', 'ValidationSessionService', '_apply_cycle2_runtime_recovery', '_augment_doc_field_details_with_decisions', '_augment_issues_with_field_decisions', '_backfill_hybrid_secondary_surfaces', '_build_bank_submission_verdict', '_build_blocked_structured_result', '_build_day1_relay_debug', '_build_document_context', '_build_document_extraction_v1', '_build_document_summaries', '_build_extraction_core_bundle', '_build_issue_dedup_key', '_build_issue_provenance_v1', '_build_lc_baseline_from_context', '_build_lc_intake_summary', '_build_processing_summary', '_build_processing_summary_v2', '_build_submission_eligibility_context', '_build_validation_contract', '_coerce_text_list', '_compute_invoice_amount_bounds', '_count_issue_severity', '_determine_company_size', '_empty_extraction_artifacts_v1', '_extract_field_decisions_from_payload', '_extract_intake_only', '_extract_lc_type_override', '_extract_request_user_type', '_extract_workflow_lc_type', '_infer_required_document_types_from_lc', '_normalize_lc_payload_structures', '_prepare_extractor_outputs_for_structured_result', '_resolve_shipment_context', '_response_shaping', '_run_validation_arbitration_escalation', '_sync_structured_result_collections', 'adapt_from_structured_result', 'apply_bank_policy', 'batch_lookup_descriptions', 'build_customs_manifest_from_option_e', 'build_issue_cards', 'build_lc_classification', 'build_unified_structured_result', 'calculate_overall_extraction_confidence', 'calculate_total_amendment_cost', 'compute_customs_risk_from_option_e', 'context', 'copy', 'country_str', 'create_audit_context', 'detect_bank_from_lc', 'detect_lc_type', 'detect_lc_type_ai', 'enforce_day1_response_contract', 'extract_requirement_conditions', 'extract_unmapped_requirements', 'func', 'generate_amendments_for_issues', 'get_bank_profile', 'get_db', 'get_user_optional', 'json', 'logger', 'logging', 'name', 'normalize_required_documents', 'parse_lc_requirements_sync_v2', 'record_usage_manual', 'ref', 'run_ai_validation', 'run_price_verification_checks', 'run_sanctions_screening_for_validation', 'settings', 'status', 'time', 'traceback', 'uuid4', 'validate_and_annotate_response', 'validate_doc', 'validate_document_async', 'validate_document_set_completeness', 'validate_upload_file']


def _shared_get(shared: Any, name: str) -> Any:
    if isinstance(shared, dict):
        return shared[name]
    return getattr(shared, name)


def _bind_shared(shared: Any) -> None:
    namespace = globals()
    for name in _SHARED_NAMES:
        if name in namespace:
            continue
        try:
            namespace[name] = _shared_get(shared, name)
        except (KeyError, AttributeError):
            continue


def build_router(shared: Any) -> APIRouter:
    _bind_shared(shared)
    router = APIRouter()

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

            intake_only = _extract_intake_only(payload)

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
                    if isinstance(lc_ctx, dict) and not isinstance(lc_ctx.get("lc_classification"), dict):
                        lc_ctx["lc_classification"] = build_lc_classification(lc_ctx, payload)
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
                structured_result["ai_validation"] = {
                    "issue_count": len(ai_issues),
                    "critical_issues": int(ai_metadata.get("critical_issues", 0) or 0),
                    "major_issues": int(ai_metadata.get("major_issues", 0) or 0),
                    "minor_issues": int(ai_metadata.get("minor_issues", 0) or 0),
                    "documents_checked": len(documents_for_ai) if isinstance(documents_for_ai, list) else 0,
                    "derived_ai_verdict": (
                        "reject" if int(ai_metadata.get("critical_issues", 0) or 0) > 0 else (
                            "warn" if int(ai_metadata.get("major_issues", 0) or 0) > 0 else "pass"
                        )
                    ),
                    "metadata": ai_metadata or {},
                }
            
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
                return isbp_desc_cache.get(ref) or isbp_desc_cache.get(ref.replace("ISBP745 ", "").replace("?", ""))
        
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
            extractor_outputs = _prepare_extractor_outputs_for_structured_result(payload)
        
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
                structured_result["validation_contract_v1"] = await _run_validation_arbitration_escalation(
                    structured_result.get("validation_contract_v1") or {},
                    structured_result.get("ai_validation") or {},
                    bank_verdict,
                    structured_result.get("effective_submission_eligibility") or structured_result.get("submission_eligibility") or {},
                )
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
                logger.warning(f"Contract validation failed (non-blocking): {contract_err}")

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

    router.add_api_route("/", validate_doc, methods=["POST"])
    router.add_api_route("/v2", validate_doc_v2, methods=["POST"])

    return router


__all__ = ["build_router"]
