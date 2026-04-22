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
from ..models import User, UserRole, ValidationSession, Discrepancy, Document, WorkflowType
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


def _upload_fix_pack_and_sign(
    *,
    session_id: UUID,
    file_name: str,
    zip_bytes: bytes,
) -> str:
    """Upload a fix-pack ZIP to S3 and return a 24-hour signed URL.

    Falls back to the in-app /download route when S3 isn't configured
    (missing boto3 setup, stub mode, etc.) so local dev keeps working
    without cloud credentials.
    """
    import os

    bucket = os.getenv("FIX_PACK_BUCKET") or os.getenv("S3_BUCKET_NAME")
    if not bucket:
        logger.info("FIX_PACK_BUCKET/S3_BUCKET_NAME unset — falling back to local download URL")
        return f"/api/importer/supplier-fix-pack/{session_id}/download"

    try:
        import boto3  # type: ignore[import-not-found]

        key = f"fix-packs/{session_id}/{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.zip"
        s3 = boto3.client("s3")
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=zip_bytes,
            ContentType="application/zip",
            ContentDisposition=f'attachment; filename="{file_name}"',
        )
        signed_url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=86400,  # 24 hours
        )
        return signed_url
    except Exception as exc:
        # Never fail the whole request on S3 trouble — the fix-pack bytes
        # still exist in the ZIP the caller generated. Fall back to the
        # in-app download URL so the importer can still grab it.
        logger.warning("Fix-pack S3 upload failed, falling back to local URL: %s", exc)
        return f"/api/importer/supplier-fix-pack/{session_id}/download"


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
    """Response for bank precheck request — tightened verdict memo."""
    success: bool
    message: str
    request_id: str
    submitted_at: datetime
    bank_name: Optional[str] = None
    # Tightened-threshold verdict + breakdown + one-page memo
    precheck_verdict: Optional[str] = None  # approve | review | reject
    counts: Optional[Dict[str, int]] = None
    memo: Optional[str] = None


class AmendmentRequestRequest(BaseModel):
    """Request to generate an amendment request PDF for Moment 1 (Draft LC Review)."""
    validation_session_id: UUID


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

        # Upload to S3 and return a signed URL (24h expiry).
        # Falls back to the existing /download endpoint when S3 isn't
        # configured (local dev, USE_STUBS mode) so the API stays usable.
        download_url = _upload_fix_pack_and_sign(
            session_id=request.validation_session_id,
            file_name=file_name,
            zip_bytes=zip_buffer.getvalue(),
        )

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

        # Real email send via the existing Resend-backed EmailService.
        # When RESEND_API_KEY is unset (dev, CI) the service reports
        # enabled=false and we fall back to the previous simulate path so
        # the endpoint still succeeds locally.
        from ..services.notifications import EmailService

        email_subject = f"Document discrepancies for LC {lc_number}"
        narrative = request.message or (
            "We reviewed the presentation documents against the issued "
            "letter of credit and surfaced discrepancies that need to be "
            "resolved before the bank will accept the presentation. The "
            "attached fix pack details each item and the correction needed."
        )
        email_html = (
            f"<p>Hello,</p>"
            f"<p>{narrative}</p>"
            f"<p>Please see the attached fix pack for LC <strong>{lc_number}</strong> "
            f"and resubmit the corrected documents at your earliest convenience.</p>"
            f"<p>Review session: <code>{request.validation_session_id}</code></p>"
            f"<p>— {current_user.email}</p>"
        )

        email_service = EmailService()
        import hashlib
        notification_id = hashlib.md5(
            f"{request.validation_session_id}{request.supplier_email}{datetime.utcnow()}".encode()
        ).hexdigest()

        if email_service.enabled:
            try:
                send_result = await email_service.send(
                    to=request.supplier_email,
                    subject=email_subject,
                    html=email_html,
                    text=narrative,
                    reply_to=current_user.email,
                )
                if send_result.success and send_result.message_id:
                    notification_id = send_result.message_id
                elif not send_result.success:
                    logger.warning(
                        "Supplier notification send failed: %s", send_result.error
                    )
            except Exception as exc:  # pragma: no cover — network/timeout
                logger.error("EmailService.send raised: %s", exc, exc_info=True)
        else:
            logger.info(
                "RESEND_API_KEY not set — skipping real send for %s (LC %s)",
                request.supplier_email,
                lc_number,
            )

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

        # Precheck no longer rejects sessions with outstanding discrepancies —
        # the whole point is to evaluate the current presentation under
        # stricter thresholds. Pull findings from validation_results first
        # (richer examiner output), fall back to Discrepancy rows.
        from ..services.importer.bank_precheck import compute_precheck_verdict, build_memo

        results_blob: Dict[str, Any] = session.validation_results or {}
        structured_issues = (
            results_blob.get("issues")
            or results_blob.get("structured_result", {}).get("issues")
            or []
        )
        findings: list = list(structured_issues) if isinstance(structured_issues, list) else []

        if not findings:
            rows = db.query(Discrepancy).filter(
                Discrepancy.validation_session_id == session.id,
                Discrepancy.deleted_at.is_(None),
            ).all()
            findings = [
                {
                    "severity": d.severity,
                    "rule_id": d.rule_name,
                    "title": d.description,
                }
                for d in rows
            ]

        verdict_payload = compute_precheck_verdict(findings)
        memo = build_memo(session, verdict_payload, request.bank_name, request.notes)

        import hashlib
        request_id = hashlib.md5(
            f"{request.validation_session_id}{request.lc_number}{datetime.utcnow()}".encode()
        ).hexdigest()

        logger.info(
            "Bank precheck verdict=%s counts=%s for LC %s by user %s",
            verdict_payload["precheck_verdict"],
            verdict_payload["counts"],
            request.lc_number,
            current_user.id,
        )

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
            bank_name=request.bank_name,
            precheck_verdict=verdict_payload["precheck_verdict"],
            counts=verdict_payload["counts"],
            memo=memo,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to request bank precheck: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to request bank precheck"
        )


# ===== Amendment Request (Moment 1 — Draft LC Review) =====

@router.post("/amendment-request")
async def generate_amendment_request(
    request: AmendmentRequestRequest,
    current_user: User = Depends(require_importer_user),
    db: Session = Depends(get_db),
    http_request: Request = None,
):
    """Generate a PDF amendment request for a Draft LC Review session.

    The response streams back application/pdf; the importer hands the PDF
    to their issuing bank so the bank can amend the draft before issuance.
    """
    from ..services.importer.amendment_request import (
        build_amendment_request_pdf,
        extract_amendment_context,
    )

    session = db.query(ValidationSession).filter(
        ValidationSession.id == request.validation_session_id
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Validation session not found",
        )

    if session.user_id != current_user.id and current_user.role != UserRole.TENANT_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this session",
        )

    # Amendment request is only meaningful for draft-LC reviews.
    if session.workflow_type != WorkflowType.IMPORTER_DRAFT_LC.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Amendment requests are only available for importer_draft_lc sessions",
        )

    # Prefer the structured findings off validation_results (examiner output
    # carries richer current/suggested text). Fall back to Discrepancy rows
    # if the JSON blob is empty.
    results_blob: Dict[str, Any] = session.validation_results or {}
    structured_issues = (
        results_blob.get("issues")
        or results_blob.get("structured_result", {}).get("issues")
        or []
    )
    findings: list = list(structured_issues) if isinstance(structured_issues, list) else []

    if not findings:
        rows = db.query(Discrepancy).filter(
            Discrepancy.validation_session_id == session.id,
            Discrepancy.deleted_at.is_(None),
        ).all()
        findings = [
            {
                "rule_id": d.rule_name,
                "title": d.description,
                "severity": d.severity,
                "current_text": d.actual_value,
                "suggested_text": d.expected_value,
            }
            for d in rows
        ]

    try:
        context = extract_amendment_context(session, findings)
        pdf_bytes = build_amendment_request_pdf(context)
    except Exception as exc:
        logger.error("Amendment-request PDF render failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate amendment request PDF",
        )

    try:
        audit_service = AuditService(db)
        audit_context = create_audit_context(http_request) if http_request else {}
        audit_service.log_action(
            action=AuditAction.CREATE,
            user=current_user,
            correlation_id=audit_context.get("correlation_id", ""),
            resource_type="amendment_request",
            resource_id=str(session.id),
            details={
                "lc_number": context.get("lc_number"),
                "finding_count": len(context.get("findings") or []),
            },
            result=AuditResult.SUCCESS,
        )
    except Exception as exc:
        # Audit failure shouldn't kill the download.
        logger.warning("Amendment-request audit log failed: %s", exc)

    filename = f'amendment-request-{context.get("lc_number", "LC")}.pdf'
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )

