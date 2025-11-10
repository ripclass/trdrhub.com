"""
Importer-specific API endpoints for supplier fix pack and bank precheck.
"""

import logging
import zipfile
import io
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from pydantic import BaseModel, Field, EmailStr

from ..database import get_db
from ..core.security import get_current_user
from ..models import User, UserRole, ValidationSession, Discrepancy, Document
from ..services.audit_service import AuditService
from ..middleware.audit_middleware import create_audit_context
from ..models.audit_log import AuditAction, AuditResult
from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/importer", tags=["importer"])


def require_importer_user(current_user: User = Depends(get_current_user)) -> User:
    """Require user to be an importer."""
    if current_user.role not in [UserRole.IMPORTER, UserRole.TENANT_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only available for importer users"
        )
    return current_user


# ===== Schemas =====

class SupplierFixPackRequest(BaseModel):
    """Request to generate supplier fix pack."""
    validation_session_id: UUID
    lc_number: Optional[str] = None


class SupplierFixPackResponse(BaseModel):
    """Response with fix pack download URL."""
    download_url: str
    file_name: str
    generated_at: datetime
    issue_count: int


class NotifySupplierRequest(BaseModel):
    """Request to notify supplier with fix pack."""
    validation_session_id: UUID
    supplier_email: EmailStr
    message: Optional[str] = None
    lc_number: Optional[str] = None


class NotifySupplierResponse(BaseModel):
    """Response for supplier notification."""
    success: bool
    message: str
    notification_id: str
    sent_at: datetime


class BankPrecheckRequest(BaseModel):
    """Request for bank precheck review."""
    validation_session_id: UUID
    lc_number: str
    bank_name: Optional[str] = None
    notes: Optional[str] = None


class BankPrecheckResponse(BaseModel):
    """Response for bank precheck request."""
    success: bool
    message: str
    request_id: str
    submitted_at: datetime
    bank_name: Optional[str] = None


# ===== Supplier Fix Pack Endpoints =====

@router.post("/supplier-fix-pack", response_model=SupplierFixPackResponse)
async def generate_supplier_fix_pack(
    request: SupplierFixPackRequest,
    current_user: User = Depends(require_importer_user),
    db: Session = Depends(get_db),
    http_request: Request = None
):
    """
    Generate a supplier fix pack containing all issues and recommendations.
    Returns a download URL for the fix pack ZIP file.
    """
    try:
        # Find validation session
        session = db.query(ValidationSession).filter(
            and_(
                ValidationSession.id == request.validation_session_id,
                ValidationSession.company_id == current_user.company_id
            )
        ).first()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Validation session not found"
            )

        # Get all discrepancies for this session
        discrepancies = db.query(Discrepancy).filter(
            Discrepancy.validation_session_id == request.validation_session_id
        ).all()

        # Get all documents for this session
        documents = db.query(Document).filter(
            Document.validation_session_id == request.validation_session_id
        ).all()

        # Generate fix pack content
        lc_number = request.lc_number or session.lc_number or "UNKNOWN"
        issue_count = len(discrepancies)

        # Create fix pack content (text file)
        fix_pack_content = f"""Supplier Fix Pack - LC {lc_number}
==========================================

Generated: {datetime.utcnow().isoformat()}
LC Number: {lc_number}
Validation Session ID: {str(request.validation_session_id)}
Total Issues: {issue_count}
Compliance Rate: {round((1 - issue_count / max(len(documents), 1)) * 100, 1)}%

ISSUES REQUIRING CORRECTION:
{chr(10).join([f'''
{i+1}. {disc.title or 'Issue'} ({disc.severity.value.upper() if hasattr(disc.severity, 'value') else str(disc.severity).upper()})
   Document: {disc.document_id}
   Category: {disc.type.value if hasattr(disc.type, 'value') else str(disc.type)}
   Description: {disc.description or 'No description'}
   Rule: {disc.rule_id or 'N/A'}
   Recommendation: {disc.recommendation or 'Please review and correct'}
''' for i, disc in enumerate(discrepancies)]) if discrepancies else 'No issues found.'}

DOCUMENT STATUS SUMMARY:
{chr(10).join([f'''
- {doc.file_name} ({doc.document_type.value if hasattr(doc.document_type, 'value') else str(doc.document_type)})
  Status: {doc.status.value if hasattr(doc.status, 'value') else str(doc.status)}
  Uploaded: {doc.created_at.isoformat() if doc.created_at else 'Unknown'}
''' for doc in documents]) if documents else 'No documents found.'}

NEXT STEPS:
1. Review each issue above
2. Correct the documents as per recommendations
3. Re-upload corrected documents
4. Request re-validation

This fix pack contains all information needed to correct the discrepancies.
Please address all issues before resubmitting.

© 2024 LCopilot - AI-Powered Trade Document Analysis
"""

        # Create ZIP file in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr(
                f"Supplier_Fix_Pack_{lc_number}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.txt",
                fix_pack_content
            )
            # Optionally include original documents
            for doc in documents:
                if doc.s3_key:
                    # In production, fetch from S3 and add to ZIP
                    # For now, just add reference
                    zip_file.writestr(
                        f"documents/{doc.file_name}",
                        f"[Document reference: {doc.s3_key}]"
                    )

        zip_buffer.seek(0)
        file_name = f"Supplier_Fix_Pack_{lc_number}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.zip"

        # In production, upload to S3 and return signed URL
        # For now, return a data URL or store in memory
        # TODO: Upload to S3 and generate signed URL
        download_url = f"/api/importer/supplier-fix-pack/{request.validation_session_id}/download"

        # Store in session or temporary storage (for demo)
        # In production, use S3 with signed URLs

        # Audit log
        audit_service = AuditService(db)
        audit_context = create_audit_context(http_request) if http_request else {}
        audit_service.log_action(
            action=AuditAction.CREATE,
            user=current_user,
            correlation_id=audit_context.get('correlation_id', ''),
            resource_type="supplier_fix_pack",
            resource_id=str(request.validation_session_id),
            details={
                "lc_number": lc_number,
                "issue_count": issue_count,
                "file_name": file_name
            },
            result=AuditResult.SUCCESS
        )

        # Track telemetry (Phase 6)
        logger.info("Telemetry: supplier_fix_pack_generated", extra={
            "user_id": str(current_user.id),
            "company_id": str(current_user.company_id),
            "validation_session_id": str(request.validation_session_id),
            "lc_number": lc_number,
            "issue_count": issue_count
        })

        return SupplierFixPackResponse(
            download_url=download_url,
            file_name=file_name,
            generated_at=datetime.utcnow(),
            issue_count=issue_count
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate supplier fix pack: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate supplier fix pack"
        )


@router.get("/supplier-fix-pack/{validation_session_id}/download")
async def download_supplier_fix_pack(
    validation_session_id: UUID,
    current_user: User = Depends(require_importer_user),
    db: Session = Depends(get_db)
):
    """
    Download the supplier fix pack ZIP file.
    """
    try:
        # Find validation session
        session = db.query(ValidationSession).filter(
            and_(
                ValidationSession.id == validation_session_id,
                ValidationSession.company_id == current_user.company_id
            )
        ).first()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Validation session not found"
            )

        # Get discrepancies and documents
        discrepancies = db.query(Discrepancy).filter(
            Discrepancy.validation_session_id == validation_session_id
        ).all()

        documents = db.query(Document).filter(
            Document.validation_session_id == validation_session_id
        ).all()

        lc_number = session.lc_number or "UNKNOWN"
        issue_count = len(discrepancies)

        # Generate fix pack content
        fix_pack_content = f"""Supplier Fix Pack - LC {lc_number}
==========================================

Generated: {datetime.utcnow().isoformat()}
LC Number: {lc_number}
Validation Session ID: {str(validation_session_id)}
Total Issues: {issue_count}
Compliance Rate: {round((1 - issue_count / max(len(documents), 1)) * 100, 1)}%

ISSUES REQUIRING CORRECTION:
{chr(10).join([f'''
{i+1}. {disc.title or 'Issue'} ({disc.severity.value.upper() if hasattr(disc.severity, 'value') else str(disc.severity).upper()})
   Document: {disc.document_id}
   Category: {disc.type.value if hasattr(disc.type, 'value') else str(disc.type)}
   Description: {disc.description or 'No description'}
   Rule: {disc.rule_id or 'N/A'}
   Recommendation: {disc.recommendation or 'Please review and correct'}
''' for i, disc in enumerate(discrepancies)]) if discrepancies else 'No issues found.'}

DOCUMENT STATUS SUMMARY:
{chr(10).join([f'''
- {doc.file_name} ({doc.document_type.value if hasattr(doc.document_type, 'value') else str(doc.document_type)})
  Status: {doc.status.value if hasattr(doc.status, 'value') else str(doc.status)}
  Uploaded: {doc.created_at.isoformat() if doc.created_at else 'Unknown'}
''' for doc in documents]) if documents else 'No documents found.'}

NEXT STEPS:
1. Review each issue above
2. Correct the documents as per recommendations
3. Re-upload corrected documents
4. Request re-validation

This fix pack contains all information needed to correct the discrepancies.
Please address all issues before resubmitting.

© 2024 LCopilot - AI-Powered Trade Document Analysis
"""

        # Create ZIP file
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr(
                f"Supplier_Fix_Pack_{lc_number}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.txt",
                fix_pack_content
            )

        zip_buffer.seek(0)
        file_name = f"Supplier_Fix_Pack_{lc_number}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.zip"

        return StreamingResponse(
            io.BytesIO(zip_buffer.read()),
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={file_name}"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download supplier fix pack: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download supplier fix pack"
        )


@router.post("/notify-supplier", response_model=NotifySupplierResponse)
async def notify_supplier(
    request: NotifySupplierRequest,
    current_user: User = Depends(require_importer_user),
    db: Session = Depends(get_db),
    http_request: Request = None
):
    """
    Send supplier fix pack to supplier via email.
    """
    try:
        # Find validation session
        session = db.query(ValidationSession).filter(
            and_(
                ValidationSession.id == request.validation_session_id,
                ValidationSession.company_id == current_user.company_id
            )
        ).first()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Validation session not found"
            )

        lc_number = request.lc_number or session.lc_number or "UNKNOWN"

        # TODO: In production, integrate with email service (SendGrid, SES, etc.)
        # For now, simulate email sending
        import hashlib
        notification_id = hashlib.md5(
            f"{request.validation_session_id}{request.supplier_email}{datetime.utcnow()}".encode()
        ).hexdigest()

        logger.info(f"Would send fix pack email to {request.supplier_email} for LC {lc_number}")

        # Audit log
        audit_service = AuditService(db)
        audit_context = create_audit_context(http_request) if http_request else {}
        audit_service.log_action(
            action=AuditAction.CREATE,
            user=current_user,
            correlation_id=audit_context.get('correlation_id', ''),
            resource_type="supplier_notification",
            resource_id=notification_id,
            details={
                "lc_number": lc_number,
                "supplier_email": request.supplier_email,
                "validation_session_id": str(request.validation_session_id)
            },
            result=AuditResult.SUCCESS
        )

        # Track telemetry (Phase 6)
        logger.info("Telemetry: supplier_notify_sent", extra={
            "user_id": str(current_user.id),
            "company_id": str(current_user.company_id),
            "validation_session_id": str(request.validation_session_id),
            "lc_number": lc_number,
            "supplier_email": request.supplier_email,
            "notification_id": notification_id
        })

        return NotifySupplierResponse(
            success=True,
            message=f"Supplier fix pack sent to {request.supplier_email}",
            notification_id=notification_id,
            sent_at=datetime.utcnow()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to notify supplier: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to notify supplier"
        )


@router.post("/bank-precheck", response_model=BankPrecheckResponse)
async def request_bank_precheck(
    request: BankPrecheckRequest,
    current_user: User = Depends(require_importer_user),
    db: Session = Depends(get_db),
    http_request: Request = None
):
    """
    Request bank precheck review for an LC (optional feature).
    """
    try:
        # Find validation session
        session = db.query(ValidationSession).filter(
            and_(
                ValidationSession.id == request.validation_session_id,
                ValidationSession.company_id == current_user.company_id
            )
        ).first()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Validation session not found"
            )

        # Check if there are any discrepancies (should be none for precheck)
        discrepancy_count = db.query(Discrepancy).filter(
            Discrepancy.validation_session_id == request.validation_session_id
        ).count()

        if discrepancy_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot request bank precheck with {discrepancy_count} outstanding issues. Please resolve all issues first."
            )

        import hashlib
        request_id = hashlib.md5(
            f"{request.validation_session_id}{request.lc_number}{datetime.utcnow()}".encode()
        ).hexdigest()

        # TODO: In production, integrate with bank API or notification system
        # For now, simulate bank precheck request
        logger.info(f"Bank precheck requested for LC {request.lc_number} by user {current_user.id}")

        # Audit log
        audit_service = AuditService(db)
        audit_context = create_audit_context(http_request) if http_request else {}
        audit_service.log_action(
            action=AuditAction.CREATE,
            user=current_user,
            correlation_id=audit_context.get('correlation_id', ''),
            resource_type="bank_precheck_request",
            resource_id=request_id,
            details={
                "lc_number": request.lc_number,
                "bank_name": request.bank_name,
                "validation_session_id": str(request.validation_session_id)
            },
            result=AuditResult.SUCCESS
        )

        # Track telemetry (Phase 6)
        logger.info("Telemetry: bank_precheck_requested", extra={
            "user_id": str(current_user.id),
            "company_id": str(current_user.company_id),
            "validation_session_id": str(request.validation_session_id),
            "lc_number": request.lc_number,
            "bank_name": request.bank_name,
            "request_id": request_id
        })

        return BankPrecheckResponse(
            success=True,
            message=f"Bank precheck review requested for LC {request.lc_number}",
            request_id=request_id,
            submitted_at=datetime.utcnow(),
            bank_name=request.bank_name
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to request bank precheck: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to request bank precheck"
        )

