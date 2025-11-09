from decimal import Decimal
from uuid import uuid4
import json

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database import get_db
from app.models import UsageAction, User, ValidationSession, SessionStatus
from app.services.entitlements import EntitlementError, EntitlementService
from app.services.validator import validate_document, validate_document_async, enrich_validation_results_with_ai
from app.services import ValidationSessionService
from app.services.audit_service import AuditService
from app.middleware.audit_middleware import create_audit_context
from app.models.audit_log import AuditAction, AuditResult
from app.utils.file_validation import validate_upload_file


router = APIRouter(prefix="/api/validate", tags=["validation"])


@router.post("/")
async def validate_doc(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Validate LC documents."""
    import time
    start_time = time.time()
    
    audit_service = AuditService(db)
    audit_context = create_audit_context(request)
    
    try:
        content_type = request.headers.get("content-type", "")
        payload: dict
        files_list = []  # Collect files for validation
        
        if content_type.startswith("multipart/form-data"):
            form = await request.form()
            payload = {}
            for key, value in form.multi_items():
                if hasattr(value, "filename"):
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
                payload[key] = value
        else:
            payload = await request.json()

        doc_type = (
            payload.get("document_type")
            or payload.get("documentType")
            or "letter_of_credit"
        )
        payload["document_type"] = doc_type
        if not doc_type:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing document_type")

        if not current_user.company:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is not associated with a company",
            )

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
        
        # Create ValidationSession for bank operations or if metadata is provided
        validation_session = None
        if user_type == "bank" or metadata:
            session_service = ValidationSessionService(db)
            validation_session = session_service.create_session(current_user)
            
            # Set company_id if available
            if current_user.company_id:
                validation_session.company_id = current_user.company_id
            
            # Store bank metadata in extracted_data
            if metadata:
                try:
                    # Parse metadata if it's a string
                    if isinstance(metadata, str):
                        metadata = json.loads(metadata)
                    
                    # Store bank metadata
                    extracted_data = {
                        "bank_metadata": {
                            "client_name": metadata.get("clientName"),
                            "lc_number": metadata.get("lcNumber"),
                            "date_received": metadata.get("dateReceived"),
                        }
                    }
                    validation_session.extracted_data = extracted_data
                except (json.JSONDecodeError, TypeError):
                    # If metadata parsing fails, continue without it
                    pass
            
            # Update session status to processing
            validation_session.status = SessionStatus.PROCESSING.value
            validation_session.processing_started_at = func.now()
            db.commit()
            
            job_id = str(validation_session.id)
        else:
            job_id = payload.get("job_id") or f"job_{uuid4()}"

        # Use async validation if JSON rules are enabled
        from app.services.validator import validate_document_async, validate_document
        import os
        
        use_json_rules = os.getenv("USE_JSON_RULES", "false").lower() == "true"
        if use_json_rules:
            # Use async validation (router is already async)
            results = await validate_document_async(payload, doc_type)
        else:
            results = validate_document(payload, doc_type)

        # Record usage - link to session if created
        quota = entitlements.record_usage(
            current_user.company,
            UsageAction.VALIDATE,
            user_id=current_user.id,
            cost=Decimal("0.00"),
            description=f"Validation request for document type {doc_type}",
            session_id=validation_session.id if validation_session else None,
        )

        # Update session status if created
        if validation_session:
            # Optionally enrich with AI (if feature flag enabled)
            ai_enrichment = {}
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
            
            validation_session.validation_results = {
                "discrepancies": [r for r in results if not r.get("passed", False)],
                "results": results,
                **ai_enrichment  # Merge AI enrichment if present
            }
            validation_session.status = SessionStatus.COMPLETED.value
            validation_session.processing_completed_at = func.now()
            db.commit()
            
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
                        "discrepancy_count": len([r for r in results if not r.get("passed", False)]),
                        "document_count": len(payload.get("files", [])) if isinstance(payload.get("files"), list) else 0,
                    }
                )

        return {
            "status": "ok",
            "results": results,
            "job_id": str(job_id),
            "jobId": str(job_id),
            "quota": quota.to_dict(),
        }
    except HTTPException:
        raise
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
