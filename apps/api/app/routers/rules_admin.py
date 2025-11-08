"""
Admin API endpoints for ruleset management (upload, validate, publish, rollback).
"""
import json
import hashlib
from pathlib import Path
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..database import get_db
from ..models import User
from ..models.ruleset import Ruleset, RulesetStatus, RulesetAudit, RulesetAuditAction
from ..core.security import require_admin, get_current_user
from ..schemas.ruleset import (
    RulesetCreate,
    RulesetResponse,
    RulesetListQuery,
    RulesetListResponse,
    ValidationReport,
    RulesetUploadResponse,
    ActiveRulesetResponse,
    RulesetAuditResponse
)
from ..services.rules_storage import RulesStorageService

try:
    import jsonschema
    from jsonschema import validate, ValidationError
except ImportError:
    # Fallback if jsonschema not installed
    jsonschema = None
    validate = None
    ValidationError = Exception


router = APIRouter(prefix="/admin/rulesets", tags=["admin-rules"])


def _load_ruleset_schema() -> dict:
    """Load the ruleset JSON schema."""
    schema_path = Path(__file__).parent.parent / "schemas" / "rules" / "ruleset.schema.json"
    if not schema_path.exists():
        raise FileNotFoundError(f"Ruleset schema not found at {schema_path}")
    with open(schema_path, 'r') as f:
        return json.load(f)


def _validate_ruleset_json(rules_json: list) -> ValidationReport:
    """
    Validate ruleset JSON against schema.
    
    Returns ValidationReport with validation results.
    """
    errors = []
    warnings = []
    
    if not jsonschema:
        warnings.append("jsonschema library not installed - skipping schema validation")
        return ValidationReport(valid=True, rule_count=len(rules_json), warnings=warnings)
    
    try:
        schema = _load_ruleset_schema()
        validate(instance=rules_json, schema=schema)
    except ValidationError as e:
        errors.append(f"Schema validation failed: {e.message}")
        if e.path:
            errors.append(f"  Path: {'/'.join(str(p) for p in e.path)}")
    except Exception as e:
        errors.append(f"Validation error: {str(e)}")
    
    # Additional validation: check for duplicate rule_ids
    rule_ids = [rule.get("rule_id") for rule in rules_json if isinstance(rule, dict)]
    duplicates = [rid for rid in rule_ids if rule_ids.count(rid) > 1]
    if duplicates:
        warnings.append(f"Duplicate rule_ids found: {set(duplicates)}")
    
    # Extract metadata
    domains = set(rule.get("domain") for rule in rules_json if isinstance(rule, dict) and rule.get("domain"))
    jurisdictions = set(rule.get("jurisdiction") for rule in rules_json if isinstance(rule, dict) and rule.get("jurisdiction"))
    
    metadata = {
        "domains": list(domains),
        "jurisdictions": list(jurisdictions),
        "rule_ids": rule_ids[:10]  # First 10 for preview
    }
    
    return ValidationReport(
        valid=len(errors) == 0,
        rule_count=len(rules_json),
        errors=errors,
        warnings=warnings,
        metadata=metadata
    )


@router.post("/upload", response_model=RulesetUploadResponse)
async def upload_ruleset(
    file: UploadFile = File(..., description="JSON file containing ruleset"),
    domain: str = Query(..., description="Rule domain (e.g., 'icc')"),
    jurisdiction: str = Query(default="global", description="Jurisdiction"),
    ruleset_version: str = Query(..., description="Semantic version (e.g., '1.0.0')"),
    rulebook_version: str = Query(..., description="Rulebook version (e.g., 'UCP600:2007')"),
    effective_from: Optional[str] = Query(None, description="Effective start date (ISO format)"),
    effective_to: Optional[str] = Query(None, description="Effective end date (ISO format)"),
    notes: Optional[str] = Query(None, description="Optional notes"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Upload a new ruleset JSON file.
    
    Validates the JSON against schema, uploads to Supabase Storage,
    and creates a draft ruleset record.
    """
    # Read and parse JSON file
    try:
        content = await file.read()
        rules_json = json.loads(content.decode('utf-8'))
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read file: {str(e)}"
        )
    
    # Validate JSON schema
    validation = _validate_ruleset_json(rules_json)
    
    if not validation.valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "Ruleset validation failed",
                "errors": validation.errors,
                "warnings": validation.warnings
            }
        )
    
    # Upload to Supabase Storage
    storage_service = RulesStorageService()
    try:
        upload_result = storage_service.upload_ruleset(
            rules_json=rules_json,
            domain=domain,
            jurisdiction=jurisdiction,
            ruleset_version=ruleset_version,
            rulebook_version=rulebook_version
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Storage upload failed: {str(e)}"
        )
    
    # Parse effective dates
    effective_from_dt = None
    effective_to_dt = None
    if effective_from:
        try:
            from datetime import datetime
            effective_from_dt = datetime.fromisoformat(effective_from.replace('Z', '+00:00'))
        except ValueError:
            pass
    if effective_to:
        try:
            from datetime import datetime
            effective_to_dt = datetime.fromisoformat(effective_to.replace('Z', '+00:00'))
        except ValueError:
            pass
    
    # Create ruleset record
    ruleset = Ruleset(
        domain=domain,
        jurisdiction=jurisdiction,
        ruleset_version=ruleset_version,
        rulebook_version=rulebook_version,
        file_path=upload_result["file_path"],
        status=RulesetStatus.DRAFT.value,
        effective_from=effective_from_dt,
        effective_to=effective_to_dt,
        checksum_md5=upload_result["checksum_md5"],
        rule_count=upload_result["rule_count"],
        created_by=current_user.id,
        notes=notes
    )
    db.add(ruleset)
    db.flush()  # Get ID
    
    # Create audit log
    audit = RulesetAudit(
        ruleset_id=ruleset.id,
        action=RulesetAuditAction.UPLOAD.value,
        actor_id=current_user.id,
        detail={
            "validation": validation.dict(),
            "file_size": upload_result.get("file_size")
        }
    )
    db.add(audit)
    
    # Also log validation action
    if validation.valid:
        validate_audit = RulesetAudit(
            ruleset_id=ruleset.id,
            action=RulesetAuditAction.VALIDATE.value,
            actor_id=current_user.id,
            detail={"validation": validation.dict()}
        )
        db.add(validate_audit)
    
    db.commit()
    db.refresh(ruleset)
    
    return RulesetUploadResponse(
        ruleset=RulesetResponse.model_validate(ruleset),
        validation=validation
    )


@router.post("/{ruleset_id}/publish", response_model=RulesetResponse)
async def publish_ruleset(
    ruleset_id: UUID,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Publish a ruleset (set status to active).
    
    Enforces single active ruleset per (domain, jurisdiction).
    Archives any previously active ruleset.
    """
    ruleset = db.query(Ruleset).filter(Ruleset.id == ruleset_id).first()
    if not ruleset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ruleset not found"
        )
    
    if ruleset.status == RulesetStatus.ACTIVE.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ruleset is already active"
        )
    
    # Find and archive any existing active ruleset for same domain/jurisdiction
    existing_active = db.query(Ruleset).filter(
        and_(
            Ruleset.domain == ruleset.domain,
            Ruleset.jurisdiction == ruleset.jurisdiction,
            Ruleset.status == RulesetStatus.ACTIVE.value,
            Ruleset.id != ruleset_id
        )
    ).first()
    
    if existing_active:
        existing_active.status = RulesetStatus.ARCHIVED.value
        # Create audit log for archiving
        archive_audit = RulesetAudit(
            ruleset_id=existing_active.id,
            action=RulesetAuditAction.ARCHIVE.value,
            actor_id=current_user.id,
            detail={"replaced_by": str(ruleset_id)}
        )
        db.add(archive_audit)
    
    # Update ruleset to active
    from datetime import datetime, timezone
    ruleset.status = RulesetStatus.ACTIVE.value
    ruleset.published_by = current_user.id
    ruleset.published_at = datetime.now(timezone.utc)
    
    # Create audit log
    publish_audit = RulesetAudit(
        ruleset_id=ruleset.id,
        action=RulesetAuditAction.PUBLISH.value,
        actor_id=current_user.id,
        detail={"replaced_ruleset_id": str(existing_active.id) if existing_active else None}
    )
    db.add(publish_audit)
    
    db.commit()
    db.refresh(ruleset)
    
    return RulesetResponse.model_validate(ruleset)


@router.post("/{ruleset_id}/rollback", response_model=RulesetResponse)
async def rollback_ruleset(
    ruleset_id: UUID,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Rollback to a previous ruleset (activate it and archive current active).
    """
    target_ruleset = db.query(Ruleset).filter(Ruleset.id == ruleset_id).first()
    if not target_ruleset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ruleset not found"
        )
    
    # Find current active for same domain/jurisdiction
    current_active = db.query(Ruleset).filter(
        and_(
            Ruleset.domain == target_ruleset.domain,
            Ruleset.jurisdiction == target_ruleset.jurisdiction,
            Ruleset.status == RulesetStatus.ACTIVE.value
        )
    ).first()
    
    if current_active and current_active.id == target_ruleset.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ruleset is already active"
        )
    
    # Archive current active
    if current_active:
        current_active.status = RulesetStatus.ARCHIVED.value
        archive_audit = RulesetAudit(
            ruleset_id=current_active.id,
            action=RulesetAuditAction.ARCHIVE.value,
            actor_id=current_user.id,
            detail={"rolled_back_to": str(target_ruleset.id)}
        )
        db.add(archive_audit)
    
    # Activate target ruleset
    from datetime import datetime, timezone
    target_ruleset.status = RulesetStatus.ACTIVE.value
    target_ruleset.published_by = current_user.id
    target_ruleset.published_at = datetime.now(timezone.utc)
    
    # Create audit log
    rollback_audit = RulesetAudit(
        ruleset_id=target_ruleset.id,
        action=RulesetAuditAction.ROLLBACK.value,
        actor_id=current_user.id,
        detail={"replaced_ruleset_id": str(current_active.id) if current_active else None}
    )
    db.add(rollback_audit)
    
    db.commit()
    db.refresh(target_ruleset)
    
    return RulesetResponse.model_validate(target_ruleset)


@router.get("", response_model=RulesetListResponse)
async def list_rulesets(
    domain: Optional[str] = Query(None),
    jurisdiction: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """List rulesets with filtering and pagination."""
    query = db.query(Ruleset)
    
    # Apply filters
    if domain:
        query = query.filter(Ruleset.domain == domain)
    if jurisdiction:
        query = query.filter(Ruleset.jurisdiction == jurisdiction)
    if status:
        query = query.filter(Ruleset.status == status)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * page_size
    rulesets = query.order_by(Ruleset.created_at.desc()).offset(offset).limit(page_size).all()
    
    return RulesetListResponse(
        items=[RulesetResponse.model_validate(r) for r in rulesets],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/active", response_model=ActiveRulesetResponse)
async def get_active_ruleset(
    domain: str = Query(..., description="Rule domain"),
    jurisdiction: str = Query(default="global", description="Jurisdiction"),
    include_content: bool = Query(default=False, description="Include full JSON content"),
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the active ruleset for a domain/jurisdiction.
    
    Public endpoint (no admin required) for validation engine to fetch active rules.
    """
    ruleset = db.query(Ruleset).filter(
        and_(
            Ruleset.domain == domain,
            Ruleset.jurisdiction == jurisdiction,
            Ruleset.status == RulesetStatus.ACTIVE.value
        )
    ).first()
    
    if not ruleset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active ruleset found for domain={domain}, jurisdiction={jurisdiction}"
        )
    
    signed_url = None
    content = None
    
    if include_content:
        storage_service = RulesStorageService()
        try:
            file_data = storage_service.get_ruleset_file(ruleset.file_path)
            content = file_data["content"]
        except Exception as e:
            # If file fetch fails, still return metadata but log error
            pass
    
    # Generate signed URL for download (1 hour expiry)
    try:
        storage_service = RulesStorageService()
        signed_url = storage_service.get_signed_url(ruleset.file_path, expires_in=3600)
    except Exception:
        pass  # Signed URL generation is optional
    
    return ActiveRulesetResponse(
        ruleset=RulesetResponse.model_validate(ruleset),
        signed_url=signed_url,
        content=content
    )


@router.get("/{ruleset_id}/audit", response_model=List[RulesetAuditResponse])
async def get_ruleset_audit(
    ruleset_id: UUID,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get audit log for a specific ruleset."""
    ruleset = db.query(Ruleset).filter(Ruleset.id == ruleset_id).first()
    if not ruleset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ruleset not found"
        )
    
    audit_logs = db.query(RulesetAudit).filter(
        RulesetAudit.ruleset_id == ruleset_id
    ).order_by(RulesetAudit.created_at.desc()).all()
    
    return [RulesetAuditResponse.model_validate(log) for log in audit_logs]
