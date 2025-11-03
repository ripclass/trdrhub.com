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
from app.services.validator import validate_document
from app.services import ValidationSessionService


router = APIRouter(prefix="/api/validate", tags=["validation"])


@router.post("/")
async def validate_doc(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    content_type = request.headers.get("content-type", "")
    payload: dict
    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        payload = {}
        for key, value in form.multi_items():
            if hasattr(value, "filename"):
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
        validation_session.validation_results = {
            "discrepancies": [r for r in results if not r.get("passed", False)],
            "results": results,
        }
        validation_session.status = SessionStatus.COMPLETED.value
        validation_session.processing_completed_at = func.now()
        db.commit()

    return {
        "status": "ok",
        "results": results,
        "job_id": str(job_id),
        "jobId": str(job_id),
        "quota": quota.to_dict(),
    }
