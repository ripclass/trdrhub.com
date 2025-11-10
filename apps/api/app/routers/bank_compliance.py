"""
Bank Compliance API endpoints.

Handles data retention policies, export requests, and data deletion requests for bank tenants.
"""

import os
import uuid
import zipfile
import io
from datetime import datetime, timedelta
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
import logging

from ..database import get_db
from app.models import User
from app.models.admin import RetentionPolicy
from ..core.security import get_current_user, require_bank_or_admin
from ..services.audit_service import AuditService
from ..models.audit_log import AuditAction, AuditResult

router = APIRouter(prefix="/bank/compliance", tags=["bank-compliance"])
logger = logging.getLogger(__name__)

# Data retention request models (in-memory for MVP, use DB table in production)
# Format: {request_id: {"type": str, "status": str, "user_id": UUID, "bank_id": UUID, ...}}
_data_retention_requests: dict = {}


@router.get("/retention-policy")
async def get_retention_policy(
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db)
):
    """
    Get data retention policy for the bank tenant.
    
    Returns the retention policy configuration for the bank's data.
    """
    if not current_user.is_bank_user() or not current_user.company_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Retention policy is only available for bank users"
        )
    
    # Query retention policies applicable to this bank
    # For MVP, return default policy. In production, query RetentionPolicy table
    # filtered by organization_id matching company_id
    
    # Default retention periods (days)
    default_policy = {
        "profile": 2555,  # 7 years
        "validation_sessions": 1825,  # 5 years
        "documents": 1825,  # 5 years
        "analytics": 1095,  # 3 years
        "billing": 2555,  # 7 years
        "audit_logs": 3650,  # 10 years
    }
    
    # Try to get bank-specific policy from DB
    bank_policy = db.query(RetentionPolicy).filter(
        and_(
            RetentionPolicy.is_active == True,
            # In production, match by organization_id == company_id
        )
    ).first()
    
    if bank_policy:
        # Map policy to response format
        return {
            "bank_id": str(current_user.company_id),
            "data_types": {
                bank_policy.data_type: {
                    "retention_period_days": bank_policy.retention_period_days,
                    "archive_after_days": bank_policy.archive_after_days,
                    "delete_after_days": bank_policy.delete_after_days,
                    "legal_basis": bank_policy.legal_basis,
                }
            },
            "default_retention_days": bank_policy.retention_period_days,
            "updated_at": bank_policy.created_at.isoformat() if bank_policy.created_at else None,
        }
    
    return {
        "bank_id": str(current_user.company_id),
        "data_types": {
            data_type: {
                "retention_period_days": days,
                "archive_after_days": None,
                "delete_after_days": None,
                "legal_basis": "Regulatory compliance and business operations",
            }
            for data_type, days in default_policy.items()
        },
        "default_retention_days": 1825,
        "updated_at": None,
    }


@router.post("/export")
async def request_data_export(
    data_scope: List[str] = Query(..., description="List of data types to export"),
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db)
):
    """
    Request data export for the bank tenant.
    
    Creates an export request that will be processed asynchronously.
    Returns a request ID that can be used to check status and download.
    """
    if not current_user.is_bank_user() or not current_user.company_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Data export is only available for bank users"
        )
    
    if not data_scope:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one data type must be specified"
        )
    
    # Validate data scope
    valid_scopes = ["profile", "validation_sessions", "documents", "analytics", "billing", "audit_logs"]
    invalid_scopes = [s for s in data_scope if s not in valid_scopes]
    if invalid_scopes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid data types: {', '.join(invalid_scopes)}"
        )
    
    # Create export request
    request_id = str(uuid.uuid4())
    _data_retention_requests[request_id] = {
        "id": request_id,
        "type": "download",
        "status": "pending",
        "user_id": str(current_user.id),
        "bank_id": str(current_user.company_id),
        "data_scope": data_scope,
        "requested_at": datetime.utcnow().isoformat(),
        "completed_at": None,
        "expires_at": (datetime.utcnow() + timedelta(days=7)).isoformat(),
        "download_url": None,
    }
    
    # Log audit event
    audit_service = AuditService(db)
    audit_service.log_action(
        action=AuditAction.VIEW_DATA,
        user=current_user,
        resource_type="data_export",
        resource_id=request_id,
        result=AuditResult.SUCCESS,
        audit_metadata={
            "action": "request_data_export",
            "bank_tenant_id": str(current_user.company_id),
            "data_scope": data_scope,
            "note": "Data export request created (async processing)"
        }
    )
    
    # In production, trigger async job to generate export
    # For MVP, simulate immediate completion
    logger.info(f"Data export requested: {request_id} for bank {current_user.company_id}")
    
    return {
        "success": True,
        "request_id": request_id,
        "status": "pending",
        "message": "Export request submitted. You will be notified when ready.",
        "estimated_completion": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
    }


@router.get("/export/{request_id}")
async def get_export_status(
    request_id: str,
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db)
):
    """
    Get status of a data export request.
    """
    if not current_user.is_bank_user() or not current_user.company_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Export status is only available for bank users"
        )
    
    request = _data_retention_requests.get(request_id)
    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export request not found"
        )
    
    # Verify request belongs to current bank
    if request.get("bank_id") != str(current_user.company_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access export requests from other tenants"
        )
    
    return {
        "request_id": request_id,
        "type": request.get("type"),
        "status": request.get("status"),
        "data_scope": request.get("data_scope"),
        "requested_at": request.get("requested_at"),
        "completed_at": request.get("completed_at"),
        "expires_at": request.get("expires_at"),
        "download_url": request.get("download_url"),
    }


@router.get("/export/{request_id}/download")
async def download_export(
    request_id: str,
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db)
):
    """
    Download the exported data as a ZIP file.
    """
    if not current_user.is_bank_user() or not current_user.company_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Export download is only available for bank users"
        )
    
    request = _data_retention_requests.get(request_id)
    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export request not found"
        )
    
    # Verify request belongs to current bank
    if request.get("bank_id") != str(current_user.company_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access export requests from other tenants"
        )
    
    if request.get("status") != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Export is not ready. Current status: {request.get('status')}"
        )
    
    # In production, generate actual ZIP from stored export
    # For MVP, create a mock ZIP file
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Add a README
        zip_file.writestr("README.txt", f"""
Data Export for Bank Tenant: {request.get('bank_id')}
Request ID: {request_id}
Export Date: {request.get('completed_at')}
Data Types: {', '.join(request.get('data_scope', []))}

This is a mock export. In production, this would contain:
- Profile information (JSON)
- Validation sessions (JSON)
- Documents (PDF/Images)
- Analytics data (CSV)
- Billing records (CSV)
- Audit logs (JSON)
        """.strip())
        
        # Add mock data files
        for data_type in request.get("data_scope", []):
            zip_file.writestr(f"{data_type}.json", f'{{"type": "{data_type}", "exported_at": "{datetime.utcnow().isoformat()}", "data": []}}')
    
    zip_buffer.seek(0)
    
    # Log download
    audit_service = AuditService(db)
    audit_service.log_action(
        action=AuditAction.VIEW_DATA,
        user=current_user,
        resource_type="data_export",
        resource_id=request_id,
        result=AuditResult.SUCCESS,
        audit_metadata={
            "action": "download_data_export",
            "bank_tenant_id": str(current_user.company_id),
            "note": "Data export downloaded"
        }
    )
    
    return StreamingResponse(
        io.BytesIO(zip_buffer.read()),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="bank_data_export_{request_id}.zip"'
        }
    )


@router.post("/erase")
async def request_data_erasure(
    reason: str = Query(..., description="Reason for data deletion"),
    data_scope: str = Query("all", description="Scope: 'all' or specific data type"),
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db)
):
    """
    Request data deletion (right to be forgotten) for the bank tenant.
    
    Creates a deletion request that will be processed after a grace period.
    """
    if not current_user.is_bank_user() or not current_user.company_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Data erasure is only available for bank users"
        )
    
    if not reason or len(reason.strip()) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reason must be at least 10 characters"
        )
    
    # Validate data scope
    valid_scopes = ["all", "profile", "validation_sessions", "documents", "analytics", "billing", "audit_logs"]
    if data_scope not in valid_scopes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid data scope. Must be one of: {', '.join(valid_scopes)}"
        )
    
    # Create deletion request
    request_id = str(uuid.uuid4())
    _data_retention_requests[request_id] = {
        "id": request_id,
        "type": "deletion",
        "status": "pending",
        "user_id": str(current_user.id),
        "bank_id": str(current_user.company_id),
        "data_scope": [data_scope] if data_scope != "all" else ["all"],
        "reason": reason,
        "requested_at": datetime.utcnow().isoformat(),
        "completed_at": None,
        "scheduled_deletion_at": (datetime.utcnow() + timedelta(days=14)).isoformat(),  # 14-day grace period
    }
    
    # Log audit event
    audit_service = AuditService(db)
    audit_service.log_action(
        action=AuditAction.DELETE_DATA,
        user=current_user,
        resource_type="data_deletion",
        resource_id=request_id,
        result=AuditResult.SUCCESS,
        audit_metadata={
            "action": "request_data_deletion",
            "bank_tenant_id": str(current_user.company_id),
            "data_scope": data_scope,
            "reason": reason[:200],  # Truncate for audit log
            "note": "Data deletion request created (14-day grace period)"
        }
    )
    
    logger.warning(f"Data deletion requested: {request_id} for bank {current_user.company_id} - Reason: {reason[:100]}")
    
    return {
        "success": True,
        "request_id": request_id,
        "status": "pending",
        "message": "Deletion request submitted. Data will be deleted after 14-day grace period.",
        "scheduled_deletion_at": _data_retention_requests[request_id]["scheduled_deletion_at"],
    }


@router.get("/requests")
async def list_retention_requests(
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db)
):
    """
    List all data retention requests (export/deletion) for the bank tenant.
    """
    if not current_user.is_bank_user() or not current_user.company_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Retention requests are only available for bank users"
        )
    
    # Filter requests for current bank
    bank_requests = [
        req for req in _data_retention_requests.values()
        if req.get("bank_id") == str(current_user.company_id)
    ]
    
    # Sort by requested_at descending
    bank_requests.sort(key=lambda x: x.get("requested_at", ""), reverse=True)
    
    return {
        "requests": bank_requests,
        "total": len(bank_requests),
    }


@router.post("/requests/{request_id}/cancel")
async def cancel_retention_request(
    request_id: str,
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db)
):
    """
    Cancel a pending data retention request.
    """
    if not current_user.is_bank_user() or not current_user.company_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot cancel requests for non-bank users"
        )
    
    request = _data_retention_requests.get(request_id)
    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found"
        )
    
    # Verify request belongs to current bank
    if request.get("bank_id") != str(current_user.company_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot cancel requests from other tenants"
        )
    
    if request.get("status") not in ["pending", "processing"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel request with status: {request.get('status')}"
        )
    
    # Update status
    request["status"] = "cancelled"
    request["cancelled_at"] = datetime.utcnow().isoformat()
    
    # Log cancellation
    audit_service = AuditService(db)
    audit_service.log_action(
        action=AuditAction.UPDATE_DATA,
        user=current_user,
        resource_type="data_retention",
        resource_id=request_id,
        result=AuditResult.SUCCESS,
        audit_metadata={
            "action": "cancel_retention_request",
            "bank_tenant_id": str(current_user.company_id),
            "request_type": request.get("type"),
            "note": "Data retention request cancelled"
        }
    )
    
    return {
        "success": True,
        "message": "Request cancelled successfully",
        "request_id": request_id,
    }

