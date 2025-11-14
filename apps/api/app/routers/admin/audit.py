"""
Admin Audit API - Audit trail exploration and verification
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from uuid import UUID
import logging
import json
import io
import csv

from app.database import get_db
from app.services.audit_service import AuditService
from app.models.audit import AuditLogEntry
from app.models import User
from app.core.security import require_admin
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


class AuditEntryResponse(BaseModel):
    id: UUID
    sequence_number: int
    tenant_id: str
    actor_id: Optional[UUID]
    actor_role: Optional[str]
    resource_type: str
    resource_id: str
    action: str
    severity: str
    before_hash: Optional[str]
    after_hash: Optional[str]
    prev_entry_hash: Optional[str]
    entry_hash: str
    metadata: Optional[dict]
    created_at: datetime


class ChainVerificationResponse(BaseModel):
    is_valid: bool
    total_entries: int
    violations: List[dict]
    verified_at: datetime


class AdminAuditEventIn(BaseModel):
    section: str
    action: str
    actor: str
    actorRole: str
    entityId: Optional[str] = None
    metadata: Optional[dict] = None


@router.get("/audit/entries", response_model=List[AuditEntryResponse])
async def search_audit_entries(
    tenant_id: str = Query(..., description="Tenant ID"),
    actor_id: Optional[UUID] = Query(None, description="Filter by actor ID"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    resource_id: Optional[str] = Query(None, description="Filter by resource ID"),
    action: Optional[str] = Query(None, description="Filter by action"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db)
):
    """Search audit entries with filters"""
    try:
        entries, total_count = await AuditService.search_entries(
            db=db,
            tenant_id=tenant_id,
            actor_id=actor_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            severity=severity,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset
        )

        # Add total count to response headers
        response = Response()
        response.headers["X-Total-Count"] = str(total_count)

        return [
            AuditEntryResponse(
                id=entry.id,
                sequence_number=entry.sequence_number,
                tenant_id=entry.tenant_id,
                actor_id=entry.actor_id,
                actor_role=entry.actor_role,
                resource_type=entry.resource_type,
                resource_id=entry.resource_id,
                action=entry.action,
                severity=entry.severity,
                before_hash=entry.before_hash,
                after_hash=entry.after_hash,
                prev_entry_hash=entry.prev_entry_hash,
                entry_hash=entry.entry_hash,
                metadata=entry.metadata,
                created_at=entry.created_at
            )
            for entry in entries
        ]

    except Exception as e:
        logger.error(f"Failed to search audit entries: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/audit/log-action")
async def log_admin_action(
    event: AdminAuditEventIn,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Record a lightweight admin action for UI interactions."""
    audit_service = AuditService(db)
    audit_service.log_action(
        action=f"admin.{event.section}.{event.action}",
        user=current_user,
        resource_type=event.section,
        resource_id=event.entityId,
        audit_metadata={
            "actor": event.actor,
            "actor_role": event.actorRole,
            **(event.metadata or {}),
        },
    )
    return {"success": True}


@router.get("/audit/entries/{entry_id}", response_model=AuditEntryResponse)
async def get_audit_entry(
    entry_id: UUID,
    db: Session = Depends(get_db)
):
    """Get specific audit entry by ID"""
    try:
        entry = db.query(AuditLogEntry).filter(AuditLogEntry.id == entry_id).first()

        if not entry:
            raise HTTPException(status_code=404, detail="Audit entry not found")

        return AuditEntryResponse(
            id=entry.id,
            sequence_number=entry.sequence_number,
            tenant_id=entry.tenant_id,
            actor_id=entry.actor_id,
            actor_role=entry.actor_role,
            resource_type=entry.resource_type,
            resource_id=entry.resource_id,
            action=entry.action,
            severity=entry.severity,
            before_hash=entry.before_hash,
            after_hash=entry.after_hash,
            prev_entry_hash=entry.prev_entry_hash,
            entry_hash=entry.entry_hash,
            metadata=entry.metadata,
            created_at=entry.created_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get audit entry: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/audit/verify", response_model=ChainVerificationResponse)
async def verify_audit_chain(
    tenant_id: str = Query(..., description="Tenant ID"),
    resource_id: Optional[str] = Query(None, description="Verify specific resource"),
    start_sequence: Optional[int] = Query(None, description="Start sequence number"),
    end_sequence: Optional[int] = Query(None, description="End sequence number"),
    db: Session = Depends(get_db)
):
    """Verify integrity of audit chain"""
    try:
        is_valid, violations = await AuditService.verify_chain(
            db=db,
            resource_id=resource_id,
            tenant_id=tenant_id,
            start_sequence=start_sequence,
            end_sequence=end_sequence
        )

        # Count total entries in verification range
        entries, total_count = await AuditService.search_entries(
            db=db,
            tenant_id=tenant_id,
            resource_id=resource_id,
            limit=1
        )

        return ChainVerificationResponse(
            is_valid=is_valid,
            total_entries=total_count,
            violations=violations,
            verified_at=datetime.now()
        )

    except Exception as e:
        logger.error(f"Failed to verify audit chain: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/audit/export")
async def export_audit_trail(
    tenant_id: str = Query(..., description="Tenant ID"),
    format: str = Query("json", regex="^(json|csv|pdf)$", description="Export format"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    include_verification: bool = Query(True, description="Include chain verification"),
    db: Session = Depends(get_db)
):
    """Export audit trail for compliance reporting"""
    try:
        export_data = await AuditService.export_audit_trail(
            db=db,
            tenant_id=tenant_id,
            format=format,
            start_date=start_date,
            end_date=end_date,
            include_verification=include_verification
        )

        if format == "json":
            return _stream_json_export(export_data, tenant_id)
        elif format == "csv":
            return _stream_csv_export(export_data, tenant_id)
        elif format == "pdf":
            return _stream_pdf_export(export_data, tenant_id)
        else:
            raise HTTPException(status_code=400, detail="Unsupported export format")

    except Exception as e:
        logger.error(f"Failed to export audit trail: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


def _stream_json_export(export_data: dict, tenant_id: str) -> StreamingResponse:
    """Stream JSON export"""
    json_str = json.dumps(export_data, indent=2, default=str)

    def generate():
        yield json_str.encode()

    filename = f"audit_trail_{tenant_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    return StreamingResponse(
        generate(),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


def _stream_csv_export(export_data: dict, tenant_id: str) -> StreamingResponse:
    """Stream CSV export"""

    def generate():
        output = io.StringIO()
        writer = csv.writer(output)

        # Write headers
        headers = [
            "ID", "Sequence", "Tenant ID", "Actor ID", "Actor Role",
            "Resource Type", "Resource ID", "Action", "Severity",
            "Before Hash", "After Hash", "Entry Hash", "Created At"
        ]
        writer.writerow(headers)

        # Write data rows
        for entry in export_data.get("entries", []):
            writer.writerow([
                entry["id"],
                entry["sequence_number"],
                entry["tenant_id"],
                entry["actor_id"],
                entry["actor_role"],
                entry["resource_type"],
                entry["resource_id"],
                entry["action"],
                entry["severity"],
                entry["before_hash"],
                entry["after_hash"],
                entry["entry_hash"],
                entry["created_at"]
            ])

        yield output.getvalue().encode()

    filename = f"audit_trail_{tenant_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


def _stream_pdf_export(export_data: dict, tenant_id: str) -> StreamingResponse:
    """Stream PDF export (simplified implementation)"""

    def generate():
        # For now, return a simple text representation
        # In production, use a proper PDF library like reportlab
        content = f"""AUDIT TRAIL REPORT
Tenant: {tenant_id}
Generated: {datetime.now().isoformat()}

Total Entries: {export_data.get('total_entries', 0)}

Verification Status: {'VALID' if export_data.get('verification', {}).get('is_valid', False) else 'INVALID'}

This is a simplified PDF export. In production, implement proper PDF generation.
"""
        yield content.encode()

    filename = f"audit_trail_{tenant_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

    return StreamingResponse(
        generate(),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/audit/stats")
async def get_audit_stats(
    tenant_id: str = Query(..., description="Tenant ID"),
    db: Session = Depends(get_db)
):
    """Get audit statistics for admin dashboard"""
    try:
        # Get total entries
        total_entries = db.query(AuditLogEntry).filter(
            AuditLogEntry.tenant_id == tenant_id
        ).count()

        # Get entries by severity
        severity_stats = db.query(
            AuditLogEntry.severity,
            db.func.count(AuditLogEntry.id).label('count')
        ).filter(
            AuditLogEntry.tenant_id == tenant_id
        ).group_by(AuditLogEntry.severity).all()

        # Get entries by action
        action_stats = db.query(
            AuditLogEntry.action,
            db.func.count(AuditLogEntry.id).label('count')
        ).filter(
            AuditLogEntry.tenant_id == tenant_id
        ).group_by(AuditLogEntry.action).limit(10).all()

        # Get recent activity (last 24 hours)
        recent_cutoff = datetime.now() - timedelta(hours=24)
        recent_entries = db.query(AuditLogEntry).filter(
            AuditLogEntry.tenant_id == tenant_id,
            AuditLogEntry.created_at >= recent_cutoff
        ).count()

        return {
            "tenant_id": tenant_id,
            "total_entries": total_entries,
            "recent_entries_24h": recent_entries,
            "severity_breakdown": [
                {"severity": severity, "count": count}
                for severity, count in severity_stats
            ],
            "top_actions": [
                {"action": action, "count": count}
                for action, count in action_stats
            ]
        }

    except Exception as e:
        logger.error(f"Failed to get audit stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")