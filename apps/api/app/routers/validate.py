from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database import get_db
from app.models import UsageAction, User
from app.services.entitlements import EntitlementError, EntitlementService
from app.services.validator import validate_document


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

    results = validate_document(payload, doc_type)

    quota = entitlements.record_usage(
        current_user.company,
        UsageAction.VALIDATE,
        user_id=current_user.id,
        cost=Decimal("0.00"),
        description=f"Validation request for document type {doc_type}",
    )

    job_id = payload.get("job_id") or f"job_{uuid4()}"

    return {
        "status": "ok",
        "results": results,
        "job_id": str(job_id),
        "jobId": str(job_id),
        "quota": quota.to_dict(),
    }
