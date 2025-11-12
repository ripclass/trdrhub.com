"""
Bank Bulk Jobs API endpoints for templated runs, scheduling, and throttling.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status, Form, File, UploadFile
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from pydantic import BaseModel, Field

from ..database import get_db
from ..core.security import get_current_user, require_bank_or_admin, require_bank_admin
from ..models import User, BankTenant
from ..models.bulk_jobs import BulkJob, BulkTemplate, BulkItem, JobStatus, JobEventType
from ..services.bulk_processor import BulkProcessor
from ..services.audit_service import AuditService
from ..middleware.audit_middleware import create_audit_context
from ..models.audit_log import AuditAction, AuditResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bank/bulk-jobs", tags=["bank-bulk-jobs"])

bulk_processor = BulkProcessor()


# ===== Schemas =====

class BulkJobConfig(BaseModel):
    """Bulk job configuration."""
    description: Optional[str] = None
    throttle_rate: Optional[int] = Field(None, ge=1, le=1000, description="Items per minute")
    max_concurrent: Optional[int] = Field(None, ge=1, le=100, description="Max concurrent items")
    retry_on_failure: bool = True
    retry_attempts: int = Field(3, ge=0, le=10)
    notify_on_completion: bool = True
    notify_on_failure: bool = True


class BulkJobCreate(BaseModel):
    """Request to create a bulk job."""
    name: str = Field(..., min_length=1, max_length=256)
    job_type: str = Field(..., description="lc_validation, doc_verification, risk_analysis")
    config: BulkJobConfig = Field(default_factory=BulkJobConfig)
    template_id: Optional[UUID] = None
    priority: int = Field(0, ge=0, le=10)
    scheduled_at: Optional[datetime] = None


class BulkJobRead(BaseModel):
    """Bulk job response."""
    id: UUID
    name: str
    description: Optional[str]
    job_type: str
    status: str
    total_items: int
    processed_items: int
    succeeded_items: int
    failed_items: int
    skipped_items: int
    progress_percent: float
    priority: int
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    created_at: datetime
    estimated_completion: Optional[datetime] = None

    class Config:
        from_attributes = True


class BulkJobListResponse(BaseModel):
    """Response for listing bulk jobs."""
    items: List[BulkJobRead]
    total: int


class BulkTemplateCreate(BaseModel):
    """Request to create a bulk template."""
    name: str = Field(..., min_length=1, max_length=128)
    description: Optional[str] = None
    job_type: str
    config_template: Dict[str, Any] = Field(default_factory=dict)
    manifest_schema: Optional[Dict[str, Any]] = None
    validation_rules: Optional[Dict[str, Any]] = None
    is_public: bool = False
    allowed_roles: Optional[List[str]] = None


class BulkTemplateRead(BaseModel):
    """Bulk template response."""
    id: UUID
    name: str
    description: Optional[str]
    job_type: str
    config_template: Dict[str, Any]
    usage_count: int
    last_used_at: Optional[datetime] = None
    is_public: bool
    created_at: datetime

    class Config:
        from_attributes = True


class BulkTemplateListResponse(BaseModel):
    """Response for listing bulk templates."""
    items: List[BulkTemplateRead]
    total: int


# ===== Bulk Jobs Endpoints =====

@router.get("", response_model=BulkJobListResponse)
async def list_bulk_jobs(
    status_filter: Optional[JobStatus] = Query(None, alias="status"),
    job_type: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db)
):
    """List bulk jobs for the bank tenant."""
    # Get bank tenant
    bank_tenant = db.query(BankTenant).filter(
        BankTenant.company_id == current_user.company_id
    ).first()

    if not bank_tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bank tenant not found"
        )

    query = db.query(BulkJob).filter(
        BulkJob.tenant_id == bank_tenant.tenant_id
    )

    if status_filter:
        query = query.filter(BulkJob.status == status_filter.value)
    if job_type:
        query = query.filter(BulkJob.job_type == job_type)

    total = query.count()
    jobs = query.order_by(desc(BulkJob.created_at)).offset(skip).limit(limit).all()

    return BulkJobListResponse(
        items=[BulkJobRead.model_validate(job) for job in jobs],
        total=total
    )


@router.get("/{job_id}", response_model=BulkJobRead)
async def get_bulk_job(
    job_id: UUID,
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db)
):
    """Get a specific bulk job."""
    bank_tenant = db.query(BankTenant).filter(
        BankTenant.company_id == current_user.company_id
    ).first()

    if not bank_tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bank tenant not found"
        )

    job = db.query(BulkJob).filter(
        and_(
            BulkJob.id == job_id,
            BulkJob.tenant_id == bank_tenant.tenant_id
        )
    ).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bulk job not found"
        )

    return BulkJobRead.model_validate(job)


@router.post("", response_model=BulkJobRead, status_code=status.HTTP_201_CREATED)
async def create_bulk_job(
    job_data: BulkJobCreate,
    manifest_file: Optional[UploadFile] = File(None),
    current_user: User = Depends(require_bank_admin),
    db: Session = Depends(get_db),
    request = None
):
    """Create a new bulk job."""
    bank_tenant = db.query(BankTenant).filter(
        BankTenant.company_id == current_user.company_id
    ).first()

    if not bank_tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bank tenant not found"
        )

    # Load template if provided
    template_config = {}
    if job_data.template_id:
        template = db.query(BulkTemplate).filter(
            and_(
                BulkTemplate.id == job_data.template_id,
                or_(
                    BulkTemplate.tenant_id == bank_tenant.tenant_id,
                    BulkTemplate.is_public == True
                )
            )
        ).first()

        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found"
            )

        template_config = template.config_template
        template.usage_count += 1
        template.last_used_at = datetime.utcnow()
        db.flush()

    # Merge template config with job config
    config = {
        **template_config,
        **job_data.config.dict(exclude_unset=True)
    }

    # Handle manifest file upload
    s3_manifest_key = None
    if manifest_file:
        # In production, upload to S3
        # For now, store reference - job_id will be generated after job creation
        pass  # Will be handled after job creation

    # Create job
    job = await bulk_processor.create_job(
        db=db,
        tenant_id=bank_tenant.tenant_id,
        name=job_data.name,
        job_type=job_data.job_type,
        config=config,
        created_by=current_user.id,
        bank_alias=bank_tenant.bank_alias,
        priority=job_data.priority,
        s3_manifest_key=s3_manifest_key
    )

    # Schedule if scheduled_at is provided
    if job_data.scheduled_at:
        # In production, use a scheduler (e.g., Celery Beat, APScheduler)
        # For now, store in config
        job.config["scheduled_at"] = job_data.scheduled_at.isoformat()
        db.commit()

    # Audit log
    audit_service = AuditService(db)
    audit_context = create_audit_context(request) if request else {}
    audit_service.log_action(
        action=AuditAction.CREATE,
        user=current_user,
        correlation_id=audit_context.get('correlation_id', ''),
        resource_type="bulk_job",
        resource_id=str(job.id),
        details={
            "name": job.name,
            "job_type": job.job_type,
            "total_items": job.total_items
        },
        result=AuditResult.SUCCESS
    )

    return BulkJobRead.model_validate(job)


@router.post("/{job_id}/cancel", response_model=BulkJobRead)
async def cancel_bulk_job(
    job_id: UUID,
    current_user: User = Depends(require_bank_admin),
    db: Session = Depends(get_db)
):
    """Cancel a running bulk job."""
    bank_tenant = db.query(BankTenant).filter(
        BankTenant.company_id == current_user.company_id
    ).first()

    if not bank_tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bank tenant not found"
        )

    job = db.query(BulkJob).filter(
        and_(
            BulkJob.id == job_id,
            BulkJob.tenant_id == bank_tenant.tenant_id
        )
    ).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bulk job not found"
        )

    if job.status not in [JobStatus.PENDING, JobStatus.RUNNING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel job with status {job.status}"
        )

    job.status = JobStatus.CANCELLED
    job.finished_at = datetime.utcnow()
    db.commit()
    db.refresh(job)

    return BulkJobRead.model_validate(job)


# ===== Bulk Templates Endpoints =====

@router.get("/templates", response_model=BulkTemplateListResponse)
async def list_bulk_templates(
    job_type: Optional[str] = Query(None),
    include_public: bool = Query(True),
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db)
):
    """List bulk job templates."""
    bank_tenant = db.query(BankTenant).filter(
        BankTenant.company_id == current_user.company_id
    ).first()

    if not bank_tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bank tenant not found"
        )

    query = db.query(BulkTemplate).filter(
        or_(
            BulkTemplate.tenant_id == bank_tenant.tenant_id,
            BulkTemplate.is_public == True if include_public else False
        )
    )

    if job_type:
        query = query.filter(BulkTemplate.job_type == job_type)

    templates = query.order_by(desc(BulkTemplate.usage_count)).all()

    return BulkTemplateListResponse(
        items=[BulkTemplateRead.model_validate(t) for t in templates],
        total=len(templates)
    )


@router.post("/templates", response_model=BulkTemplateRead, status_code=status.HTTP_201_CREATED)
async def create_bulk_template(
    template_data: BulkTemplateCreate,
    current_user: User = Depends(require_bank_admin),
    db: Session = Depends(get_db),
    request = None
):
    """Create a new bulk job template."""
    bank_tenant = db.query(BankTenant).filter(
        BankTenant.company_id == current_user.company_id
    ).first()

    if not bank_tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bank tenant not found"
        )

    template = BulkTemplate(
        tenant_id=bank_tenant.tenant_id,
        name=template_data.name,
        description=template_data.description,
        job_type=template_data.job_type,
        config_template=template_data.config_template,
        manifest_schema=template_data.manifest_schema,
        validation_rules=template_data.validation_rules,
        created_by=current_user.id,
        is_public=template_data.is_public,
        allowed_roles=template_data.allowed_roles
    )

    db.add(template)
    db.commit()
    db.refresh(template)

    # Audit log
    audit_service = AuditService(db)
    audit_context = create_audit_context(request) if request else {}
    audit_service.log_action(
        action=AuditAction.CREATE,
        user=current_user,
        correlation_id=audit_context.get('correlation_id', ''),
        resource_type="bulk_template",
        resource_id=str(template.id),
        details={"name": template.name, "job_type": template.job_type},
        result=AuditResult.SUCCESS
    )

    return BulkTemplateRead.model_validate(template)


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bulk_template(
    template_id: UUID,
    current_user: User = Depends(require_bank_admin),
    db: Session = Depends(get_db)
):
    """Delete a bulk job template."""
    bank_tenant = db.query(BankTenant).filter(
        BankTenant.company_id == current_user.company_id
    ).first()

    if not bank_tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bank tenant not found"
        )

    template = db.query(BulkTemplate).filter(
        and_(
            BulkTemplate.id == template_id,
            BulkTemplate.tenant_id == bank_tenant.tenant_id
        )
    ).first()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    db.delete(template)
    db.commit()

