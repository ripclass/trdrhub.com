from decimal import Decimal
from uuid import uuid4
import json

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database import get_db
from app.models import UsageAction, User, ValidationSession, SessionStatus, UserRole
from app.models.company import Company, PlanType, CompanyStatus
from app.services.entitlements import EntitlementError, EntitlementService
from app.services.validator import validate_document, validate_document_async, enrich_validation_results_with_ai, apply_bank_policy
from app.services import ValidationSessionService
from app.services.audit_service import AuditService
from app.middleware.audit_middleware import create_audit_context
from app.models.audit_log import AuditAction, AuditResult
from app.utils.file_validation import validate_upload_file
from fastapi import Header
from typing import Optional, List, Dict, Any
from app.config import settings


router = APIRouter(prefix="/api/validate", tags=["validation"])


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
        if use_json_rules:
            # Use async validation (router is already async)
            results = await validate_document_async(payload, doc_type)
        else:
            results = validate_document(payload, doc_type)

        failed_results = [r for r in results if not r.get("passed", False)]

        # Record usage - link to session if created (skip for demo user)
        quota = None
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

        # Update session status if created
        if validation_session:
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
            
            document_summaries = _build_document_summaries(files_list, results)

            validation_session.validation_results = {
                "discrepancies": failed_results,
                "results": results,
                "documents": document_summaries,
                "summary": {
                    "document_count": len(document_summaries),
                    "failed_rules": len(failed_results),
                },
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
                        "discrepancy_count": len(failed_results),
                        "document_count": len(payload.get("files", [])) if isinstance(payload.get("files"), list) else 0,
                    }
                )

        if not document_summaries:
            document_summaries = _build_document_summaries(files_list, results)

        return {
            "status": "ok",
            "results": results,
            "documents": document_summaries,
            "job_id": str(job_id),
            "jobId": str(job_id),
            "quota": quota.to_dict() if quota else None,
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


def _build_document_summaries(files_list: List[Any], results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Create lightweight document summaries for downstream consumers."""
    if not files_list:
        return []

    has_failures = any(not r.get("passed", False) for r in results)
    status = "warning" if has_failures else "success"
    discrepancy_count = len([r for r in results if not r.get("passed", False)])

    summaries: List[Dict[str, Any]] = []
    for index, file_obj in enumerate(files_list):
        filename = getattr(file_obj, "filename", None)
        summaries.append(
            {
                "id": str(uuid4()),
                "name": filename or f"Document {index + 1}",
                "type": _infer_document_type_from_name(filename, index),
                "status": status,
                "discrepancyCount": discrepancy_count,
                "extractedFields": {},
                "ocrConfidence": None,
            }
        )

    return summaries


def _infer_document_type_from_name(filename: Optional[str], index: int) -> str:
    """Infer the document type using filename patterns."""
    if filename:
        name = filename.lower()
        if any(token in name for token in ("lc", "letter", "credit", "mt700")):
            return "letter_of_credit"
        if any(token in name for token in ("invoice", "inv")):
            return "commercial_invoice"
        if any(token in name for token in ("bill", "lading", "bl", "shipping")):
            return "bill_of_lading"
        if any(token in name for token in ("packing", "packlist")):
            return "packing_list"
        if any(token in name for token in ("certificate_of_origin", "coo", "certificate", "gsp")):
            return "certificate"

    return _fallback_doc_type(index)


def _fallback_doc_type(index: int) -> str:
    """Fallback ordering for document types when hints are unavailable."""
    mapping = {
        0: "letter_of_credit",
        1: "commercial_invoice",
        2: "bill_of_lading",
    }
    return mapping.get(index, "supporting_document")
