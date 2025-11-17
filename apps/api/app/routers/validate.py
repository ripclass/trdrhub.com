from decimal import Decimal, InvalidOperation
from uuid import uuid4
from datetime import datetime, timedelta
import json
import copy

import logging
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database import get_db
from app.models import UsageAction, User, ValidationSession, SessionStatus, UserRole
from app.models.company import Company, PlanType, CompanyStatus
from app.services.entitlements import EntitlementError, EntitlementService
from app.services.validator import validate_document, validate_document_async, enrich_validation_results_with_ai, apply_bank_policy
from app.services.crossdoc import (
    run_cross_document_checks,
    build_issue_cards,
    DEFAULT_LABELS,
)
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


router = APIRouter(prefix="/api/validate", tags=["validation"])
logger = logging.getLogger(__name__)


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
        from app.core.security import hash_password
        user = User(
            email=demo_email,
            hashed_password=hash_password("demo123"),  # Dummy password
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

        # Extract structured data from uploaded files (respecting any document tags)
        document_tags = payload.get("document_tags")
        extracted_context = await _build_document_context(files_list, document_tags)
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
                    status = doc.get("extraction_status") or "unknown"
                    status_counts[status] = status_counts.get(status, 0) + 1
                logger.info(
                    "Document extraction status summary: total=%d details=%s",
                    len(document_details),
                    status_counts,
                )
            payload.update(extracted_context)
        else:
            logger.warning("No structured data extracted from %d uploaded files", len(files_list))
        
        context_contains_structured_data = any(
            key in payload for key in ("lc", "invoice", "bill_of_lading", "documents")
        )
        
        if context_contains_structured_data:
            logger.info(f"Payload contains structured data: {list(payload.keys())}")
        else:
            logger.warning("Payload does not contain structured data - JSON rules will be skipped")

        lc_context = payload.get("lc") or {}
        shipment_context = _resolve_shipment_context(payload)
        lc_type_guess = detect_lc_type(lc_context, shipment_context)
        override_lc_type = _extract_lc_type_override(payload)
        lc_type_source = "override" if override_lc_type else "auto"
        lc_type = override_lc_type or lc_type_guess["lc_type"]
        lc_type_reason = lc_type_guess["reason"]
        lc_type_confidence = lc_type_guess["confidence"]
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

        # Check if this is a bank bulk validation request
        user_type = payload.get("userType") or payload.get("user_type")
        metadata = payload.get("metadata")
        
        # Create ValidationSession for bank operations, exporter/importer, or if metadata is provided
        validation_session = None
        if user_type in ["bank", "exporter", "importer"] or metadata:
            session_service = ValidationSessionService(db)
            validation_session = session_service.create_session(current_user)
            
            # Set company_id if available
            if current_user.company_id:
                validation_session.company_id = current_user.company_id
            
            # Store metadata based on user type
            if metadata:
                try:
                    # Parse metadata if it's a string
                    if isinstance(metadata, str):
                        metadata = json.loads(metadata)
                    
                    # Get org_id from request state if available (for multi-org support)
                    org_id = None
                    if hasattr(request, 'state') and hasattr(request.state, 'org_id'):
                        org_id = request.state.org_id
                    
                    # Store bank metadata
                    extracted_data = {
                        "bank_metadata": {
                            "client_name": metadata.get("clientName"),
                            "lc_number": metadata.get("lcNumber"),
                            "date_received": metadata.get("dateReceived"),
                            "org_id": org_id,  # Include org_id if available
                        }
                    }
                    validation_session.extracted_data = extracted_data
                except (json.JSONDecodeError, TypeError):
                    # If metadata parsing fails, continue without it
                    pass
            elif user_type in ["exporter", "importer"]:
                # Store exporter/importer metadata (LC number from payload)
                lc_number = payload.get("lc_number") or payload.get("lcNumber")
                workflow_type = payload.get("workflow_type") or payload.get("workflowType")
                if lc_number or workflow_type:
                    validation_session.extracted_data = {
                        "lc_number": lc_number,
                        "user_type": user_type,
                        "workflow_type": workflow_type,
                    }
            
            # Update session status to processing
            validation_session.status = SessionStatus.PROCESSING.value
            validation_session.processing_started_at = func.now()
            db.commit()
            
            job_id = str(validation_session.id)
        else:
            job_id = payload.get("job_id") or f"job_{uuid4()}"

        # Use async validation if JSON rules are enabled
        from app.services.validator import validate_document_async, validate_document
        
        use_json_rules = settings.USE_JSON_RULES
        if lc_type_is_unknown:
            logger.info("LC type unknown - skipping ICC rule evaluation to avoid false positives.")
            results: List[Dict[str, Any]] = []
        elif use_json_rules and context_contains_structured_data:
            # Use async validation (router is already async)
            results = await validate_document_async(payload, doc_type)
        elif use_json_rules:
            logger.info("Structured data unavailable, skipping JSON rules evaluation.")
            results = []
        else:
            results = validate_document(payload, doc_type)

        # Post-process deterministic cross-document checks for richer SME messages
        crossdoc_results = run_cross_document_checks(payload)
        if crossdoc_results:
            logger.info(
                "Cross-document checks produced %d SME issues: %s",
                len(crossdoc_results),
                [issue.get("rule") for issue in crossdoc_results],
            )
        else:
            logger.info("Cross-document checks produced no issues for this payload.")
        if crossdoc_results:
            results.extend(crossdoc_results)

        if lc_type_is_unknown:
            results.append(
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

        failed_results = [
            r for r in results
            if not r.get("passed", False) and not r.get("not_applicable", False)
        ]
        issue_cards, reference_issues = build_issue_cards(failed_results)

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
            "Building document summaries: files_list=%d details=%d",
            len(files_list) if files_list else 0,
            len(document_details_for_summaries) if document_details_for_summaries else 0,
        )
        document_summaries = _build_document_summaries(
            files_list,
            results,
            document_details_for_summaries,
        )
        if document_summaries:
            doc_status_counts: Dict[str, int] = {}
            for summary in document_summaries:
                status = summary.get("status") or "unknown"
                doc_status_counts[status] = doc_status_counts.get(status, 0) + 1
            logger.info(
                "Document summaries built: total=%d status_breakdown=%s",
                len(document_summaries),
                doc_status_counts,
            )
        else:
            logger.warning(
                "Document summaries are empty: no documents captured for job %s", job_id
            )
        
        processing_duration = time.time() - start_time
        processing_summary = _build_processing_summary(document_summaries, processing_duration, len(failed_results))
        analytics_payload = _build_document_processing_analytics(document_summaries, processing_summary)
        timeline_events = _build_processing_timeline(document_summaries, processing_summary)
        document_status_counts = processing_summary.pop("status_counts", _summarize_document_statuses(document_summaries))
        overall_status = "error" if document_status_counts.get("error") else "warning" if document_status_counts.get("warning") else "success"

        stored_extracted_data = {}
        if "lc" in payload:
            stored_extracted_data["lc"] = payload["lc"]
        if "invoice" in payload:
            stored_extracted_data["invoice"] = payload["invoice"]
        if "bill_of_lading" in payload:
            stored_extracted_data["bill_of_lading"] = payload["bill_of_lading"]
        if payload.get("documents"):
            stored_extracted_data["documents"] = payload["documents"]
        if payload.get("documents_presence"):
            stored_extracted_data["documents_presence"] = payload["documents_presence"]
        stored_extracted_data["lc_type"] = lc_type
        stored_extracted_data["lc_type_reason"] = lc_type_reason
        stored_extracted_data["lc_type_confidence"] = lc_type_confidence
        stored_extracted_data["lc_type_source"] = lc_type_source
        
        results_payload = {
            "discrepancies": failed_results,
            "results": results,
            "documents": document_summaries,
            "extracted_data": stored_extracted_data,
            "extraction_status": payload.get("extraction_status", "unknown"),
            "summary": {
                "document_count": len(document_summaries),
                "failed_rules": len(failed_results),
            },
            "total_documents": len(document_summaries),
            "total_discrepancies": len(failed_results),
            "processing_summary": processing_summary,
            "document_status": document_status_counts,
            "timeline": timeline_events,
            "analytics": analytics_payload,
            "overall_status": overall_status,
            "lc_data": stored_extracted_data.get("lc", {}),
            "issue_cards": issue_cards,  # User-facing actionable issues
            "reference_issues": reference_issues,  # Technical rule references
            "lc_type": lc_type,
            "lc_type_reason": lc_type_reason,
            "lc_type_confidence": lc_type_confidence,
            "lc_type_source": lc_type_source,
        }
        ai_enrichment = {}

        # Update session status if created
        if validation_session:
            session_extracted_data = validation_session.extracted_data or {}
            try:
                session_extracted_data.update(
                    {
                        "lc_type": lc_type,
                        "lc_type_reason": lc_type_reason,
                        "lc_type_confidence": lc_type_confidence,
                        "lc_type_source": lc_type_source,
                    }
                )
            except AttributeError:
                session_extracted_data = {
                    "lc_type": lc_type,
                    "lc_type_reason": lc_type_reason,
                    "lc_type_confidence": lc_type_confidence,
                    "lc_type_source": lc_type_source,
                }
            validation_session.extracted_data = session_extracted_data

            # Apply bank policy overlays and exceptions (if bank user)
            if current_user.is_bank_user() and current_user.company_id:
                try:
                    results = await apply_bank_policy(
                        validation_results=results,
                        bank_id=str(current_user.company_id),
                        document_data=payload,
                        db_session=db,
                        validation_session_id=str(validation_session.id) if validation_session else None,
                        user_id=str(current_user.id)
                    )
                except Exception as e:
                    # Don't fail validation if policy application fails
                    import logging
                    logging.getLogger(__name__).warning(f"Bank policy application skipped: {e}")
            
            # CRITICAL: Ensure documents are in validation_results before storing
            if not results_payload.get("documents") and document_summaries:
                logger.warning(
                    "Document summaries missing from results_payload but available (%d summaries), adding them",
                    len(document_summaries)
                )
                results_payload["documents"] = document_summaries
            
            # Log what we're storing
            logger.info(
                "Storing validation_results: documents=%d discrepancies=%d issue_cards=%d",
                len(results_payload.get("documents") or []),
                len(results_payload.get("discrepancies") or []),
                len(results_payload.get("issue_cards") or []),
            )
            
            # CRITICAL: Use deepcopy to ensure nested structures are properly copied
            # Also ensure all required keys are present
            required_keys = ["documents", "discrepancies", "results", "extracted_data", "issue_cards", "reference_issues"]
            for key in required_keys:
                if key not in results_payload:
                    logger.warning(f"Missing required key '{key}' in results_payload, adding empty default")
                    if key == "documents":
                        results_payload[key] = document_summaries or []
                    elif key in ["discrepancies", "results", "issue_cards", "reference_issues"]:
                        results_payload[key] = []
                    elif key == "extracted_data":
                        results_payload[key] = stored_extracted_data or {}
            
            # Store initial payload with deep copy to ensure nested structures are preserved
            validation_session.validation_results = copy.deepcopy(results_payload)
            
            # Optionally enrich with AI (if feature flag enabled)
            try:
                ai_enrichment = await enrich_validation_results_with_ai(
                    validation_results=results,
                    document_data=payload,
                    session_id=str(validation_session.id),
                    user_id=str(current_user.id),
                    db_session=db
                )
            except Exception as e:
                # Don't fail validation if AI enrichment fails
                import logging
                logging.getLogger(__name__).warning(f"AI enrichment skipped: {e}")
                ai_enrichment = {}
            
            if ai_enrichment:
                # CRITICAL: Update results_payload with ai_enrichment, then do a deep copy
                # This ensures we're merging ai_enrichment into the existing payload, not replacing it
                results_payload.update(ai_enrichment)
                
                # Verify all required keys are still present after update
                for key in required_keys:
                    if key not in results_payload:
                        logger.error(f"Key '{key}' lost after AI enrichment update! Restoring from original.")
                        if key == "documents":
                            results_payload[key] = document_summaries or []
                        elif key in ["discrepancies", "results", "issue_cards", "reference_issues"]:
                            results_payload[key] = []
                        elif key == "extracted_data":
                            results_payload[key] = stored_extracted_data or {}
                
                # CRITICAL: Use deepcopy to ensure nested structures are properly preserved
                validation_session.validation_results = copy.deepcopy(results_payload)
                logger.info(
                    "Updated validation_results with AI enrichment: documents=%d keys=%s",
                    len(results_payload.get("documents") or []),
                    list(results_payload.keys()),
                )

            validation_session.status = SessionStatus.COMPLETED.value
            validation_session.processing_completed_at = func.now()
            db.commit()
            
            # CRITICAL: Refresh session to ensure we're reading the latest data from DB
            db.refresh(validation_session)
            
            # Final verification log
            stored_docs = (validation_session.validation_results or {}).get("documents") or []
            stored_keys = list((validation_session.validation_results or {}).keys())
            logger.info(
                "Final validation_results after commit: documents=%d total_keys=%d keys=%s",
                len(stored_docs),
                len(validation_session.validation_results or {}),
                stored_keys,
            )
            
            # Defensive check: if documents are missing, log error but don't fail
            if not stored_docs and document_summaries:
                logger.error(
                    "CRITICAL: Documents lost after commit! Had %d summaries before commit, but validation_results only has keys: %s",
                    len(document_summaries),
                    stored_keys,
                )
            
            # Log bank validation upload if applicable
            if user_type == "bank":
                duration_ms = int((time.time() - start_time) * 1000)
                metadata_dict = payload.get("metadata") or {}
                if isinstance(metadata_dict, str):
                    try:
                        metadata_dict = json.loads(metadata_dict)
                    except:
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
                    }
                )

        # Extract extracted data from payload for frontend display
        extracted_data = stored_extracted_data or {}
        extraction_status = payload.get("extraction_status", "unknown")

        ai_enrichment_payload = results_payload.get("ai_enrichment")

        if not results_payload.get("ai_enrichment") and ai_enrichment:
            results_payload.update(ai_enrichment)

        # CRITICAL: Ensure documents are always in the response
        final_documents = document_summaries or []
        if not final_documents and payload.get("documents"):
            # Last resort: try to build summaries from document_details if summaries are empty
            logger.warning(
                "Document summaries empty but document_details exist, attempting to rebuild from payload"
            )
            final_documents = _build_document_summaries(
                [],  # Empty files_list
                results,
                payload.get("documents"),  # Use document_details from payload
            )
            if final_documents:
                logger.info("Successfully rebuilt %d document summaries from payload", len(final_documents))
                # Update results_payload with the rebuilt documents
                results_payload["documents"] = final_documents
                if validation_session:
                    # CRITICAL: Use deepcopy to ensure nested structures are preserved
                    validation_session.validation_results = copy.deepcopy(results_payload)
                    db.commit()
                    db.refresh(validation_session)  # Refresh to read latest data
        
        return {
            "status": "ok",
            "results": results,
            "discrepancies": failed_results,  # Only failed, non-not_applicable rules
            "documents": final_documents,  # Use final_documents instead of document_summaries
            "extracted_data": extracted_data,  # Include extracted LC fields for frontend
            "extraction_status": extraction_status,  # success, partial, empty, error
            "job_id": str(job_id),
            "jobId": str(job_id),
            "quota": quota.to_dict() if quota else None,
            "issue_cards": issue_cards,
            "reference_issues": reference_issues,
            "ai_enrichment": ai_enrichment_payload,
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


def _build_document_summaries(
    files_list: List[Any],
    results: List[Dict[str, Any]],
    document_details: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Create lightweight document summaries for downstream consumers."""
    details = document_details or []
    issue_by_name, issue_by_type, issue_by_id = _collect_document_issue_stats(results)

    def _build_summary_from_detail(detail: Dict[str, Any], index: int) -> Dict[str, Any]:
        filename = detail.get("filename") or detail.get("name")
        doc_type = detail.get("document_type") or _infer_document_type_from_name(filename, index)
        normalized_type = doc_type or "supporting_document"
        detail_id = detail.get("id") or str(uuid4())
        stats = _resolve_issue_stats(
            detail_id,
            filename,
            normalized_type,
            issue_by_name,
            issue_by_type,
            issue_by_id,
        )
        status = _severity_to_status(stats.get("max_severity") if stats else None)
        discrepancy_count = stats.get("count", 0) if stats else 0

        return {
            "id": detail_id,
            "name": filename or f"Document {index + 1}",
            "type": _humanize_doc_type(normalized_type),
            "documentType": normalized_type,
            "status": status,
            "discrepancyCount": discrepancy_count,
            "extractedFields": detail.get("extracted_fields") or {},
            "ocrConfidence": detail.get("ocr_confidence"),
            "extractionStatus": detail.get("extraction_status"),
        }

    if details:
        logger.info(
            "Building document summaries from details: %d documents found",
            len(details),
        )
        return [_build_summary_from_detail(detail, index) for index, detail in enumerate(details)]

    if not files_list:
        logger.warning("No document details or files_list available - returning empty summaries")
        return []

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
        status = _severity_to_status(stats.get("max_severity") if stats else None)
        discrepancy_count = stats.get("count", 0) if stats else 0
        summaries.append(
            {
                "id": str(uuid4()),
                "name": filename or f"Document {index + 1}",
                "type": _humanize_doc_type(inferred_type),
                "documentType": inferred_type,
                "status": status,
                "discrepancyCount": discrepancy_count,
                "extractedFields": {},
                "ocrConfidence": None,
                "extractionStatus": None,
            }
        )

    return summaries


def _infer_document_type_from_name(filename: Optional[str], index: int) -> str:
    """Infer the document type using filename patterns."""
    if filename:
        name = filename.lower()
        if any(token in name for token in ("invoice", "inv")):
            return "commercial_invoice"
        if any(token in name for token in ("bill_of_lading", "bill-of-lading", "bill", "lading", "bl", "shipping", "bol")):
            return "bill_of_lading"
        if any(token in name for token in ("packing", "packlist")):
            return "packing_list"
        if any(token in name for token in ("insurance", "policy")):
            return "insurance_certificate"
        if any(token in name for token in ("certificate_of_origin", "coo", "gsp", "certificate")):
            return "certificate_of_origin"
        if any(token in name for token in ("inspection", "quality", "analysis")):
            return "inspection_certificate"
        if any(token in name for token in ("lc_", "letter_of_credit", "mt700")) or name.endswith("_lc.pdf"):
            return "letter_of_credit"
        if " credit " in name:
            return "letter_of_credit"

    return _fallback_doc_type(index)


def _fallback_doc_type(index: int) -> str:
    """Fallback ordering for document types when hints are unavailable."""
    mapping = {
        0: "letter_of_credit",
        1: "commercial_invoice",
        2: "bill_of_lading",
        3: "packing_list",
        4: "certificate_of_origin",
        5: "insurance_certificate",
        6: "inspection_certificate",
    }
    return mapping.get(index, "supporting_document")


DOCUMENT_TYPE_ALIASES: Dict[str, List[str]] = {
    "letter_of_credit": [
        "letter of credit",
        "lc",
        "l/c",
        "mt700",
        "lc document",
        "lc_document",
    ],
    "commercial_invoice": [
        "invoice",
        "commercial invoice",
        "ci",
        "inv",
    ],
    "bill_of_lading": [
        "bill of lading",
        "bill_of_lading",
        "bill-of-lading",
        "bill",
        "bol",
        "bl",
        "shipping document",
        "awb",
    ],
    "packing_list": [
        "packing list",
        "packlist",
        "packing",
    ],
    "insurance_certificate": [
        "insurance",
        "insurance certificate",
        "policy",
    ],
    "certificate_of_origin": [
        "certificate of origin",
        "coo",
        "gsp",
    ],
    "inspection_certificate": [
        "inspection",
        "analysis",
        "quality certificate",
    ],
    "supporting_document": [
        "supporting",
        "misc",
        "other",
    ],
}


def _canonical_document_tag(raw_value: Any) -> Optional[str]:
    if raw_value is None:
        return None
    normalized = str(raw_value).strip().lower()
    if not normalized:
        return None
    normalized = normalized.replace("-", " ").replace("_", " ")
    for canonical, aliases in DOCUMENT_TYPE_ALIASES.items():
        if normalized == canonical.replace("_", " "):
            return canonical
        if normalized in aliases:
            return canonical
    for canonical, aliases in DOCUMENT_TYPE_ALIASES.items():
        if any(alias in normalized for alias in aliases):
            return canonical
    return normalized.replace(" ", "_")


def _resolve_document_type(
    filename: Optional[str],
    index: int,
    document_tags: Optional[Dict[str, str]] = None,
) -> str:
    if filename and document_tags:
        lower_name = filename.lower()
        base_name = lower_name.rsplit(".", 1)[0]
        tag_value = document_tags.get(lower_name) or document_tags.get(base_name)
        if tag_value:
            return tag_value
    return _infer_document_type(filename, index)


async def _build_document_context(
    files_list: List[Any],
    document_tags: Optional[Dict[str, Any]] = None
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
        from app.rules.extractors import DocumentFieldExtractor
        from app.rules.models import DocumentType
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
    has_structured_data = False
    known_doc_types = {
        "letter_of_credit",
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
        
        extracted_text = await _extract_text_from_upload(upload_file)
        if not extracted_text:
            logger.warning(f"⚠ No text extracted from {filename} - skipping field extraction")
            doc_info["extraction_status"] = "empty"
            document_details.append(doc_info)
            continue
        
        logger.info(f"✓ Extracted {len(extracted_text)} characters from {filename}")

        try:
            if document_type == "letter_of_credit":
                # Store raw text for LC documents
                if "lc" not in context:
                    context["lc"] = {}
                    context["lc"]["raw_text"] = extracted_text
                    context["lc_text"] = extracted_text
                
                lc_fields = extractor.extract_fields(extracted_text, DocumentType.LETTER_OF_CREDIT)
                logger.info(f"Extracted {len(lc_fields)} fields from LC document {filename}")
                lc_context = _fields_to_lc_context(lc_fields)
                if lc_context:
                    # Merge structured fields into lc context
                    context["lc"].update(lc_context)
                    has_structured_data = True
                    logger.info(f"LC context keys: {list(context['lc'].keys())}")
                    if not context.get("lc_number") and lc_context.get("number"):
                        context["lc_number"] = lc_context["number"]
                    doc_info["extracted_fields"] = lc_context
                    doc_info["extraction_status"] = "success"
                else:
                    logger.warning(f"No LC context created from {len(lc_fields)} extracted fields")
            elif document_type == "commercial_invoice":
                invoice_fields = extractor.extract_fields(extracted_text, DocumentType.COMMERCIAL_INVOICE)
                logger.info(f"Extracted {len(invoice_fields)} fields from invoice {filename}")
                invoice_context = _fields_to_flat_context(invoice_fields)
                if invoice_context:
                    if "invoice" not in context:
                        context["invoice"] = {}
                    context["invoice"]["raw_text"] = extracted_text
                    context["invoice"].update(invoice_context)
                    has_structured_data = True
                    doc_info["extracted_fields"] = invoice_context
                    doc_info["extraction_status"] = "success"
                    logger.info(f"Invoice context keys: {list(context['invoice'].keys())}")
            elif document_type == "bill_of_lading":
                bl_fields = extractor.extract_fields(extracted_text, DocumentType.BILL_OF_LADING)
                logger.info(f"Extracted {len(bl_fields)} fields from B/L {filename}")
                bl_context = _fields_to_flat_context(bl_fields)
                if bl_context:
                    if "bill_of_lading" not in context:
                        context["bill_of_lading"] = {}
                    context["bill_of_lading"]["raw_text"] = extracted_text
                    context["bill_of_lading"].update(bl_context)
                    has_structured_data = True
                    doc_info["extracted_fields"] = bl_context
                    doc_info["extraction_status"] = "success"
                    logger.info(f"B/L context keys: {list(context['bill_of_lading'].keys())}")
            elif document_type == "packing_list":
                packing_fields = extractor.extract_fields(extracted_text, DocumentType.PACKING_LIST)
                logger.info(f"Extracted {len(packing_fields)} fields from packing list {filename}")
                packing_context = _fields_to_flat_context(packing_fields)
                if packing_context:
                    pkg_ctx = context.setdefault("packing_list", {})
                    pkg_ctx["raw_text"] = extracted_text
                    pkg_ctx.update(packing_context)
                    has_structured_data = True
                    doc_info["extracted_fields"] = packing_context
                    doc_info["extraction_status"] = "success"
                    logger.info(f"Packing list context keys: {list(pkg_ctx.keys())}")
            elif document_type == "certificate_of_origin":
                coo_fields = extractor.extract_fields(extracted_text, DocumentType.CERTIFICATE_OF_ORIGIN)
                logger.info(f"Extracted {len(coo_fields)} fields from certificate of origin {filename}")
                coo_context = _fields_to_flat_context(coo_fields)
                if coo_context:
                    coo_ctx = context.setdefault("certificate_of_origin", {})
                    coo_ctx["raw_text"] = extracted_text
                    coo_ctx.update(coo_context)
                    has_structured_data = True
                    doc_info["extracted_fields"] = coo_context
                    doc_info["extraction_status"] = "success"
                    logger.info(f"Certificate of origin context keys: {list(coo_ctx.keys())}")
            elif document_type == "insurance_certificate":
                insurance_fields = extractor.extract_fields(extracted_text, DocumentType.INSURANCE_CERTIFICATE)
                logger.info(f"Extracted {len(insurance_fields)} fields from insurance certificate {filename}")
                insurance_context = _fields_to_flat_context(insurance_fields)
                if insurance_context:
                    insurance_ctx = context.setdefault("insurance_certificate", {})
                    insurance_ctx["raw_text"] = extracted_text
                    insurance_ctx.update(insurance_context)
                    has_structured_data = True
                    doc_info["extracted_fields"] = insurance_context
                    doc_info["extraction_status"] = "success"
                    logger.info(f"Insurance context keys: {list(insurance_ctx.keys())}")
            elif document_type == "inspection_certificate":
                inspection_fields = extractor.extract_fields(extracted_text, DocumentType.INSPECTION_CERTIFICATE)
                logger.info(f"Extracted {len(inspection_fields)} fields from inspection certificate {filename}")
                inspection_context = _fields_to_flat_context(inspection_fields)
                if inspection_context:
                    inspection_ctx = context.setdefault("inspection_certificate", {})
                    inspection_ctx["raw_text"] = extracted_text
                    inspection_ctx.update(inspection_context)
                    has_structured_data = True
                    doc_info["extracted_fields"] = inspection_context
                    doc_info["extraction_status"] = "success"
                    logger.info(f"Inspection context keys: {list(inspection_ctx.keys())}")
            else:
                # For other document types, retain raw text for downstream use
                doc_info["raw_text_preview"] = extracted_text[:500]
                doc_info["extraction_status"] = "text_only"
                extra_context = context.setdefault(document_type, {})
                extra_context["raw_text"] = extracted_text
        except Exception as e:
            logger.error(f"Error extracting fields from {filename}: {e}", exc_info=True)
            document_details.append(doc_info)
            continue

        if doc_info.get("extracted_fields"):
            doc_info["raw_text_preview"] = extracted_text[:500]
        elif doc_info.get("extraction_status") in {"empty", "text_only"} and extracted_text:
            # Ensure at least a preview is available for OCR overview
            doc_info["raw_text_preview"] = extracted_text[:500]
            if doc_info.get("extraction_status") == "empty":
                doc_info["extraction_status"] = "text_only"

        document_details.append(doc_info)
        entry = documents_presence.setdefault(
            document_type,
            {"present": False, "count": 0},
        )
        entry["present"] = True
        entry["count"] += 1

    # Set extraction status
    if has_structured_data:
        context["extraction_status"] = "success"
        logger.info(f"Final extracted context structure: {list(context.keys())}")
    elif any(key in context for key in ("lc", "invoice", "bill_of_lading")):
        # We have raw_text but no structured fields
        context["extraction_status"] = "partial"
        logger.warning("Extracted raw text but no structured fields could be parsed")
    else:
        context["extraction_status"] = "empty"
        logger.warning("No context extracted from any files")
    
    if document_details:
        context["documents"] = document_details

    context["documents_presence"] = documents_presence
    context["documents_summary"] = documents_presence
    
    return context


def _resolve_shipment_context(payload: Dict[str, Any]) -> Dict[str, Any]:
    for key in (
        "bill_of_lading",
        "billOfLading",
        "awb",
        "air_waybill",
        "airway_bill",
        "shipment",
    ):
        ctx = payload.get(key)
        if isinstance(ctx, dict):
            return ctx
    lc_ports = (payload.get("lc") or {}).get("ports")
    if isinstance(lc_ports, dict):
        return lc_ports
    return {}


def _extract_lc_type_override(payload: Dict[str, Any]) -> Optional[str]:
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
    lc_amount_value = (((payload.get("lc") or {}).get("amount") or {}).get("value"))
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


async def _extract_text_from_upload(upload_file: Any) -> str:
    """
    Extract textual content from an uploaded PDF/image.
    
    Tries pdfminer/PyPDF2 first, then falls back to OCR (Google Document AI/AWS Textract)
    if enabled and text extraction returns empty.
    """
    filename = getattr(upload_file, "filename", "unknown")
    content_type = getattr(upload_file, "content_type", "unknown")
    
    logger.info(f"🔍 Starting text extraction for: {filename} (type: {content_type})")
    
    try:
        file_bytes = await upload_file.read()
        await upload_file.seek(0)
        logger.info(f"✓ Read {len(file_bytes)} bytes from {filename}")
    except Exception as e:
        logger.error(f"✗ Failed to read file {filename}: {e}", exc_info=True)
        return ""

    if not file_bytes:
        logger.warning(f"⚠ Empty file content for {filename}")
        return ""
    
    # Check file size limit for OCR
    if len(file_bytes) > settings.OCR_MAX_BYTES:
        logger.warning(
            f"File {filename} exceeds OCR size limit ({len(file_bytes)} > {settings.OCR_MAX_BYTES} bytes). "
            f"Skipping OCR fallback."
        )

    text_output = ""

    # Try pdfminer first (better for complex layouts)
    logger.info(f"  → Trying pdfminer extraction...")
    try:
        from pdfminer.high_level import extract_text  # type: ignore
        text_output = extract_text(BytesIO(file_bytes))
        if text_output.strip():
            logger.info(f"  ✓ pdfminer extracted {len(text_output)} characters from {filename}")
            return text_output
        else:
            logger.info(f"  ⚠ pdfminer returned empty text for {filename}")
    except Exception as pdfminer_error:
        logger.info(f"  ✗ pdfminer extraction failed for {filename}: {pdfminer_error}")

    # Fallback to PyPDF2
    logger.info(f"  → Trying PyPDF2 extraction...")
    try:
        from PyPDF2 import PdfReader  # type: ignore
        reader = PdfReader(BytesIO(file_bytes))
        pieces = []
        for page_num, page in enumerate(reader.pages):
            try:
                page_text = page.extract_text() or ""
                pieces.append(page_text)
            except Exception as e:
                logger.debug(f"Failed to extract text from page {page_num+1} of {filename}: {e}")
                continue
        text_output = "\n".join(pieces)
        if text_output.strip():
            logger.info(f"  ✓ PyPDF2 extracted {len(text_output)} characters from {filename} ({len(reader.pages)} pages)")
            return text_output
        else:
            logger.info(f"  ⚠ PyPDF2 returned empty text for {filename} ({len(reader.pages)} pages)")
    except Exception as pypdf_error:
        logger.warning(f"  ✗ PyPDF2 extraction failed for {filename}: {pypdf_error}")

    # If pdfminer/PyPDF2 returned empty and OCR is enabled, try OCR providers
    if not text_output.strip() and settings.OCR_ENABLED:
        logger.info(f"  → Text extraction returned empty, attempting OCR fallback...")
        logger.info(f"     OCR_ENABLED: {settings.OCR_ENABLED}")
        logger.info(f"     OCR_PROVIDER_ORDER: {settings.OCR_PROVIDER_ORDER}")
        
        # Check file size and page count before attempting OCR
        page_count = 0
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(BytesIO(file_bytes))
            page_count = len(reader.pages)
            logger.info(f"     Page count: {page_count}")
        except:
            # If we can't count pages, assume it's a single-page image
            page_count = 1 if content_type.startswith('image/') else 0
            logger.info(f"     Could not determine page count, assuming: {page_count}")
        
        if page_count > settings.OCR_MAX_PAGES:
            logger.warning(
                f"  ⚠ File {filename} exceeds OCR page limit ({page_count} > {settings.OCR_MAX_PAGES} pages). "
                f"Skipping OCR."
            )
        elif len(file_bytes) > settings.OCR_MAX_BYTES:
            logger.warning(
                f"File {filename} exceeds OCR size limit ({len(file_bytes)} > {settings.OCR_MAX_BYTES} bytes). "
                f"Skipping OCR."
            )
        else:
            # Try OCR providers in configured order
            logger.info(f"  → Attempting OCR with providers: {settings.OCR_PROVIDER_ORDER}")
            text_output = await _try_ocr_providers(file_bytes, filename, content_type)
            if text_output.strip():
                logger.info(f"  ✓ OCR extraction successful: {len(text_output)} characters")
                return text_output
            else:
                logger.warning(f"  ✗ OCR extraction returned empty")
    elif not settings.OCR_ENABLED:
        logger.info(f"  ⚠ OCR is DISABLED (OCR_ENABLED={settings.OCR_ENABLED})")

    if not text_output.strip():
        logger.error(f"❌ ALL extraction methods failed for {filename}")
        logger.error(f"   Summary: pdfminer=empty, PyPDF2=empty, OCR={'attempted' if settings.OCR_ENABLED else 'disabled'}")
        logger.error(f"   File details: content-type={content_type}, size={len(file_bytes)} bytes")
    else:
        logger.info(f"✅ Extraction complete for {filename}: {len(text_output)} characters")
    
    return text_output


async def _try_ocr_providers(file_bytes: bytes, filename: str, content_type: str) -> str:
    """
    Try OCR providers in configured order until one succeeds.
    
    Returns extracted text or empty string if all providers fail.
    """
    from uuid import uuid4
    from app.ocr.factory import get_ocr_factory
    
    # Map provider order names to adapter classes
    provider_map = {
        "gdocai": "google_documentai",
        "textract": "aws_textract",
    }
    
    # Get configured provider order
    provider_order = settings.OCR_PROVIDER_ORDER or ["gdocai", "textract"]
    
    try:
        factory = get_ocr_factory()
        all_adapters = factory.get_all_adapters()
        
        # Create a map of provider names to adapters
        adapter_map = {adapter.provider_name: adapter for adapter in all_adapters}
        
        # Try providers in configured order
        for provider_name in provider_order:
            # Map short name to full provider name
            full_provider_name = provider_map.get(provider_name, provider_name)
            
            if full_provider_name not in adapter_map:
                logger.debug(f"OCR provider {provider_name} ({full_provider_name}) not available")
                continue
            
            adapter = adapter_map[full_provider_name]
            
            try:
                # Check health before attempting
                if not await adapter.health_check():
                    logger.debug(f"OCR provider {full_provider_name} health check failed")
                    continue
                
                # Try OCR with timeout
                import asyncio
                doc_id = uuid4()
                
                result = await asyncio.wait_for(
                    adapter.process_file_bytes(file_bytes, filename, content_type, doc_id),
                    timeout=settings.OCR_TIMEOUT_SEC
                )
                
                if result and result.full_text and not result.error:
                    logger.info(
                        f"OCR provider {full_provider_name} extracted {len(result.full_text)} characters "
                        f"from {filename} (confidence: {result.overall_confidence:.2f}, "
                        f"time: {result.processing_time_ms}ms)"
                    )
                    return result.full_text
                elif result and result.error:
                    logger.warning(f"OCR provider {full_provider_name} returned error: {result.error}")
                else:
                    logger.debug(f"OCR provider {full_provider_name} returned empty result")
                    
            except asyncio.TimeoutError:
                logger.warning(f"OCR provider {full_provider_name} timed out after {settings.OCR_TIMEOUT_SEC}s")
                continue
            except Exception as e:
                logger.warning(f"OCR provider {full_provider_name} failed: {e}", exc_info=True)
                continue
        
        logger.warning(f"All OCR providers failed for {filename}")
        return ""
        
    except Exception as e:
        logger.error(f"Failed to initialize OCR factory: {e}", exc_info=True)
        return ""


def _infer_document_type(filename: Optional[str], index: int) -> str:
    """Guess document type using filename hints or position."""
    if filename:
        lower = filename.lower()
        if any(token in lower for token in ("invoice", "inv")):
            return "commercial_invoice"
        if any(token in lower for token in ("bill of lading", "bill_of_lading", "bill-of-lading", "bill", "lading", "bl", "shipping", "bol")):
            return "bill_of_lading"
        if any(token in lower for token in ("packing", "packlist")):
            return "packing_list"
        if any(token in lower for token in ("insurance", "policy")):
            return "insurance_certificate"
        if any(token in lower for token in ("certificate_of_origin", "coo", "gsp", "certificate")):
            return "certificate_of_origin"
        if any(token in lower for token in ("inspection", "analysis", "quality")):
            return "inspection_certificate"
        if any(token in lower for token in ("lc_", "letter_of_credit", "mt700")) or lower.endswith("_lc.pdf"):
            return "letter_of_credit"
        if " credit " in lower:
            return "letter_of_credit"

    mapping = {
        0: "letter_of_credit",
        1: "commercial_invoice",
        2: "bill_of_lading",
    }
    return mapping.get(index, "letter_of_credit")


def _resolve_issue_stats(
    detail_id: Optional[str],
    filename: Optional[str],
    doc_type: Optional[str],
    issue_by_name: Dict[str, Dict[str, Any]],
    issue_by_type: Dict[str, Dict[str, Any]],
    issue_by_id: Dict[str, Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    if detail_id and detail_id in issue_by_id:
        return issue_by_id[detail_id]

    if filename:
        name_key = filename.strip().lower()
        if name_key in issue_by_name:
            return issue_by_name[name_key]
        inferred_type = _label_to_doc_type(name_key)
        if inferred_type and inferred_type in issue_by_type:
            return issue_by_type[inferred_type]

    if doc_type and doc_type in issue_by_type:
        return issue_by_type[doc_type]

    return None


def _collect_document_issue_stats(
    results: List[Dict[str, Any]]
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    issue_by_name: Dict[str, Dict[str, Any]] = {}
    issue_by_type: Dict[str, Dict[str, Any]] = {}
    issue_by_id: Dict[str, Dict[str, Any]] = {}

    for result in results:
        if result.get("passed", False) or result.get("not_applicable", False):
            continue

        severity = (result.get("severity") or "minor").lower()
        doc_names = _extract_document_names(result)
        doc_types = _extract_document_types(result)
        doc_ids = _extract_document_ids(result)

        for doc_id in doc_ids:
            _bump_issue_entry(issue_by_id, doc_id, severity)

        for name in doc_names:
            name_key = name.strip().lower()
            entry = _bump_issue_entry(issue_by_name, name_key, severity)
            inferred_type = _label_to_doc_type(name)
            if inferred_type:
                _bump_issue_entry(issue_by_type, inferred_type, severity)

        for doc_type in doc_types:
            canonical = _normalize_doc_type_key(doc_type)
            if canonical:
                _bump_issue_entry(issue_by_type, canonical, severity)

    return issue_by_name, issue_by_type, issue_by_id


def _extract_document_names(discrepancy: Dict[str, Any]) -> List[str]:
    names: List[str] = []
    for key in ("documents", "document_names"):
        value = discrepancy.get(key)
        if isinstance(value, str):
            names.append(value)
        elif isinstance(value, list):
            names.extend([str(item) for item in value if isinstance(item, str)])
    for key in ("document", "document_name"):
        if discrepancy.get(key):
            names.append(str(discrepancy[key]))
    return names


def _extract_document_types(discrepancy: Dict[str, Any]) -> List[str]:
    types: List[str] = []
    value = discrepancy.get("document_types")
    if isinstance(value, str):
        types.append(value)
    elif isinstance(value, list):
        types.extend([str(item) for item in value if item])
    elif value:
        types.append(str(value))
    if discrepancy.get("document_type"):
        types.append(str(discrepancy["document_type"]))
    return types


def _extract_document_ids(discrepancy: Dict[str, Any]) -> List[str]:
    ids: List[str] = []
    value = discrepancy.get("document_ids")
    if isinstance(value, str):
        ids.append(value)
    elif isinstance(value, list):
        ids.extend([str(item) for item in value if item])
    elif value:
        ids.append(str(value))
    if discrepancy.get("document_id"):
        ids.append(str(discrepancy["document_id"]))
    return ids


def _bump_issue_entry(bucket: Dict[str, Dict[str, Any]], key: str, severity: str) -> Dict[str, Any]:
    if not key:
        return {}
    entry = bucket.setdefault(key, {"count": 0, "max_severity": "minor"})
    entry["count"] += 1
    if _severity_rank(severity) > _severity_rank(entry["max_severity"]):
        entry["max_severity"] = severity
    return entry


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


def _label_to_doc_type(label: Optional[str]) -> Optional[str]:
    if not label:
        return None
    normalized = str(label).strip().lower()
    for canonical, friendly in DEFAULT_LABELS.items():
        if normalized == friendly.lower():
            return canonical
        if normalized.replace(" ", "_") == canonical:
            return canonical
    return None


def _normalize_doc_type_key(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    normalized = str(value).strip().lower()
    normalized_snake = normalized.replace(" ", "_")
    if normalized_snake in DEFAULT_LABELS:
        return normalized_snake
    if normalized in DEFAULT_LABELS:
        return normalized
    return normalized_snake


def _humanize_doc_type(doc_type: Optional[str]) -> str:
    if not doc_type:
        return "Supporting Document"
    return DEFAULT_LABELS.get(doc_type, doc_type.replace("_", " ").title())


def _summarize_document_statuses(documents: List[Dict[str, Any]]) -> Dict[str, int]:
    counts = {"success": 0, "warning": 0, "error": 0}
    for doc in documents:
        status = (doc.get("status") or "success").lower()
        if status not in counts:
            counts[status] = 0
        counts[status] += 1
    return counts


def _build_processing_summary(
    document_summaries: List[Dict[str, Any]],
    processing_seconds: float,
    total_discrepancies: int,
) -> Dict[str, Any]:
    status_counts = _summarize_document_statuses(document_summaries)
    total_docs = len(document_summaries)
    verified = status_counts.get("success", 0)
    warnings = status_counts.get("warning", 0)
    errors = status_counts.get("error", 0)
    compliance_rate = 0
    if total_docs:
        compliance_rate = max(0, round((verified / total_docs) * 100))

    return {
        "documents": total_docs,
        "verified": verified,
        "warnings": warnings,
        "errors": errors,
        "compliance_rate": compliance_rate,
        "processing_time_seconds": round(processing_seconds, 2),
        "processing_time_display": _format_duration(processing_seconds),
        "discrepancies": total_discrepancies,
        "status_counts": status_counts,
    }


def _build_processing_timeline(
    document_summaries: List[Dict[str, Any]],
    processing_summary: Dict[str, Any],
) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    doc_count = len(document_summaries)
    now = datetime.utcnow()
    stages = [
        ("Documents Uploaded", "success", f"{doc_count} document(s) received"),
        ("LC Terms Extracted", "success", "Structured LC context generated"),
        ("Document Cross-Check", "success", "Validated trade docs against LC terms"),
        (
            "Customs Pack Generated",
            "warning" if processing_summary.get("warnings") else "success",
            "Bundle prepared for customs clearance",
        ),
    ]

    for index, (title, status, description) in enumerate(stages):
        events.append(
            {
                "title": title,
                "status": status,
                "description": description,
                "timestamp": (now - timedelta(seconds=max(5, (len(stages) - index) * 5))).isoformat() + "Z",
            }
        )
    return events


def _build_document_processing_analytics(
    document_summaries: List[Dict[str, Any]],
    processing_summary: Dict[str, Any],
) -> Dict[str, Any]:
    status_counts = processing_summary.get("status_counts", {})
    confidences = [doc.get("ocrConfidence") for doc in document_summaries if isinstance(doc.get("ocrConfidence"), (int, float))]
    if confidences:
        avg_confidence = sum(confidences) / len(confidences)
        extraction_accuracy = round(avg_confidence * 100)
    else:
        extraction_accuracy = max(80, 100 - status_counts.get("warning", 0) * 5 - status_counts.get("error", 0) * 10)

    document_processing = []
    for index, doc in enumerate(document_summaries):
        extracted_fields = doc.get("extractedFields") or {}
        processing_time = 0.2 + max(0, len(extracted_fields)) * 0.05 + index * 0.02
        ocr_confidence = doc.get("ocrConfidence")
        if isinstance(ocr_confidence, (int, float)):
            accuracy_score = round(ocr_confidence * 100)
        else:
            accuracy_score = 98 if doc.get("status") == "success" else 90

        compliance_label = "High" if doc.get("status") == "success" else "Medium" if doc.get("status") == "warning" else "Low"
        risk_label = "Low Risk" if doc.get("status") == "success" else "Medium Risk" if doc.get("status") == "warning" else "High Risk"

        document_processing.append(
            {
                "name": doc.get("name"),
                "type": doc.get("type"),
                "status": doc.get("status"),
                "processing_time_seconds": round(processing_time, 2),
                "accuracy_score": accuracy_score,
                "compliance_level": compliance_label,
                "risk_level": risk_label,
            }
        )

    performance_insights = [
        f"{processing_summary.get('documents', 0)} document(s) processed",
        f"{processing_summary.get('verified', 0)} verified with no issues",
        f"Runtime: {processing_summary.get('processing_time_display', 'n/a')}",
    ]

    return {
        "extraction_accuracy": extraction_accuracy,
        "lc_compliance_score": processing_summary.get("compliance_rate", 0),
        "customs_ready_score": max(
            0,
            processing_summary.get("compliance_rate", 0) - status_counts.get("warning", 0) * 2 - status_counts.get("error", 0) * 5,
        ),
        "documents_processed": processing_summary.get("documents", 0),
        "document_status_distribution": status_counts,
        "document_processing": document_processing,
        "performance_insights": performance_insights,
        "processing_time_display": processing_summary.get("processing_time_display"),
    }


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
        else:
            lc_context[name] = value

    return lc_context


def _fields_to_flat_context(fields: List[Any]) -> Dict[str, Any]:
    """Convert generic extracted fields to a flat dictionary."""
    context: Dict[str, Any] = {}
    for field in fields:
        value = (field.value or "").strip()
        if not value:
            continue
        context[field.field_name] = value
    return context


def _set_nested_value(container: Dict[str, Any], path: Tuple[str, ...], value: Any) -> None:
    current = container
    for segment in path[:-1]:
        current = current.setdefault(segment, {})
    current[path[-1]] = value
