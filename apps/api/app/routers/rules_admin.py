"""
Admin API endpoints for ruleset management (upload, validate, publish, rollback).
"""
import json
import hashlib
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from ..database import get_db
from ..models import User
from ..models.ruleset import Ruleset, RulesetStatus, RulesetAudit, RulesetAuditAction
from ..models.rule_record import RuleRecord
from ..core.security import require_admin, get_current_user
from ..schemas.ruleset import (
    RulesetCreate,
    RulesetResponse,
    RulesetListQuery,
    RulesetListResponse,
    ValidationReport,
    RulesetUploadResponse,
    ActiveRulesetResponse,
    RulesetAuditResponse,
    RulesImportSummaryModel,
)
from ..schemas.rules import (
    RuleListResponse,
    RuleRecordResponse,
    RuleUpdateRequest,
    RuleDeleteResponse,
    BulkSyncRequest,
    BulkSyncResponse,
    BulkSyncResponseItem,
)
from ..services.rules_storage import RulesStorageService
from ..services.rules_importer import RulesImporter
from ..services.rules_audit import record_rule_audit
from ..services.rules_service import get_rules_service
from ..metrics.rules_metrics import rules_update_total

try:
    import jsonschema  # type: ignore[reportMissingModuleSource]
    from jsonschema import validate, ValidationError  # type: ignore[reportMissingModuleSource]
except ImportError:
    # Fallback if jsonschema not installed
    jsonschema = None
    validate = None
    ValidationError = Exception


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/rulesets", tags=["admin-rules"])

# Filename patterns for auto-detection
FILENAME_PATTERNS = [
    re.compile(r"icc\.?(?P<rulebook>ucp600)-(?P<version>2007)-v(?P<ruleset>[\d\.]+)\.json"),
    re.compile(r"icc\.?(?P<rulebook>eucp2\.1)-v(?P<ruleset>[\d\.]+)\.json"),
    re.compile(r"icc\.?(?P<rulebook>urdg758)-v(?P<ruleset>[\d\.]+)\.json"),
    re.compile(r"icc\.?(?P<rulebook>lcopilot\.crossdoc)-v(?P<ruleset>[\d\.]+)\.json"),
]


def autodetect_metadata(filename: str) -> Optional[Dict[str, str]]:
    """
    Auto-detect metadata from filename.
    
    Returns dict with 'rulebook' and 'ruleset' keys if match found, None otherwise.
    """
    for pattern in FILENAME_PATTERNS:
        match = pattern.match(filename)
        if match:
            return match.groupdict()
    return None


def _load_ruleset_rules(ruleset: Ruleset) -> List[Dict[str, Any]]:
    if not ruleset.file_path:
        raise ValueError("Ruleset file reference missing")

    storage_service = RulesStorageService()
    file_data = storage_service.get_ruleset_file(ruleset.file_path)
    content = file_data.get("content")
    if not isinstance(content, list):
        raise ValueError("Ruleset file does not contain a list of rules")
    return content


def _set_rules_activation(db: Session, ruleset_id: Optional[UUID], *, is_active: bool) -> None:
    if not ruleset_id:
        return
    update_payload = {"is_active": is_active}
    update_payload["archived_at"] = None if is_active else func.now()
    db.query(RuleRecord).filter(RuleRecord.ruleset_id == ruleset_id).update(
        update_payload,
        synchronize_session=False,
    )


rules_router = APIRouter(prefix="/admin/rules", tags=["admin-rules"])


def _clear_rules_cache(domain: Optional[str], jurisdiction: Optional[str]) -> None:
    try:
        rules_service = get_rules_service()
        if domain and jurisdiction:
            rules_service.clear_cache(domain=domain, jurisdiction=jurisdiction)
        else:
            rules_service.clear_cache()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to clear rules cache: %s", exc)


def _get_rule_or_404(db: Session, rule_id: str) -> RuleRecord:
    rule = db.query(RuleRecord).filter(RuleRecord.rule_id == rule_id).first()
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule {rule_id} not found",
        )
    return rule


def _serialize_rule_record(rule: RuleRecord) -> RuleRecordResponse:
    return RuleRecordResponse(
        rule_id=rule.rule_id,
        rule_version=rule.rule_version,
        article=rule.article,
        version=rule.version,
        domain=rule.domain,
        jurisdiction=rule.jurisdiction,
        document_type=rule.document_type,
        rule_type=rule.rule_type,
        severity=rule.severity,
        deterministic=bool(rule.deterministic),
        requires_llm=bool(rule.requires_llm),
        title=rule.title,
        reference=rule.reference,
        description=rule.description,
        conditions=rule.conditions or [],
        expected_outcome=rule.expected_outcome or {},
        tags=rule.tags or [],
        metadata=rule.rule_metadata,
        checksum=rule.checksum,
        ruleset_id=rule.ruleset_id,
        ruleset_version=rule.ruleset_version,
        is_active=bool(rule.is_active),
        archived_at=rule.archived_at,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


def _load_ruleset_schema() -> dict:
    """Load the ruleset JSON schema."""
    schema_path = Path(__file__).parent.parent / "schemas" / "rules" / "ruleset.schema.json"
    if not schema_path.exists():
        raise FileNotFoundError(f"Ruleset schema not found at {schema_path}")
    with open(schema_path, 'r') as f:
        return json.load(f)


def _normalize_rule(rule: dict, domain: str, jurisdiction: str) -> dict:
    """
    Auto-fix common rule format issues:
    - Add missing domain/jurisdiction from upload params
    - Rename 'condition' to 'conditions' (plural)
    - Rename 'text' to 'description'
    - Map severity values to standard (high→fail, critical→fail, medium→warn, major→warn)
    - Add default metadata if missing
    """
    SEVERITY_MAP = {
        "critical": "fail",
        "high": "fail", 
        "major": "warn",
        "medium": "warn",
        "warning": "warn",
        "low": "info",
        "minor": "info"
    }
    
    fixed = rule.copy()
    
    # Add missing domain/jurisdiction
    if not fixed.get("domain"):
        fixed["domain"] = domain
    if not fixed.get("jurisdiction"):
        fixed["jurisdiction"] = jurisdiction
    
    # Rename 'condition' to 'conditions' (singular to plural)
    if "condition" in fixed and "conditions" not in fixed:
        fixed["conditions"] = fixed.pop("condition")
    elif "condition" in fixed and "conditions" in fixed:
        # Both exist - prefer conditions, remove condition
        del fixed["condition"]
    
    # Ensure conditions is a list
    if "conditions" in fixed and not isinstance(fixed["conditions"], list):
        fixed["conditions"] = [fixed["conditions"]] if fixed["conditions"] else []
    elif "conditions" not in fixed:
        fixed["conditions"] = []
    
    # Rename 'text' to 'description'
    if "text" in fixed and not fixed.get("description"):
        fixed["description"] = fixed.pop("text")
    elif "text" in fixed:
        del fixed["text"]  # Remove duplicate
    
    # Normalize severity
    old_severity = str(fixed.get("severity", "warn")).lower()
    fixed["severity"] = SEVERITY_MAP.get(old_severity, old_severity)
    
    # Add document_type if missing
    if not fixed.get("document_type"):
        fixed["document_type"] = "lc"
    
    # Add rule_version if missing
    if not fixed.get("rule_version"):
        fixed["rule_version"] = fixed.get("version", "1.0")
    
    # Add metadata if missing
    if not fixed.get("metadata"):
        fixed["metadata"] = {
            "ruleset_source": "RuleEngine Core",
            "ruleset_version": "v1.0",
            "effective_from": "2025-01-01",
            "effective_to": None
        }
    
    # Ensure deterministic has a value
    if "deterministic" not in fixed:
        fixed["deterministic"] = True
    
    # Ensure requires_llm has a value  
    if "requires_llm" not in fixed:
        fixed["requires_llm"] = False
    
    return fixed


def _normalize_ruleset(rules_json: list, domain: str = "icc", jurisdiction: str = "global") -> list:
    """Normalize all rules in a ruleset."""
    return [_normalize_rule(r, domain, jurisdiction) for r in rules_json if isinstance(r, dict)]


def _validate_ruleset_json(rules_json: list, domain: str = "icc", jurisdiction: str = "global") -> ValidationReport:
    """
    Validate ruleset JSON against schema.
    Auto-normalizes rules before validation.
    
    Returns ValidationReport with validation results.
    """
    errors = []
    warnings = []
    
    # Auto-normalize rules first
    rules_json = _normalize_ruleset(rules_json, domain, jurisdiction)
    
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
    # Auto-detect metadata from filename (optional)
    auto = autodetect_metadata(file.filename)
    if auto:
        # Only override fields user left empty
        if not rulebook_version:
            rulebook_version = f"{auto['rulebook']}-{auto['version']}" if 'version' in auto else auto['rulebook']
        if not ruleset_version:
            ruleset_version = auto.get("ruleset", ruleset_version)
    
    # Read and parse JSON file
    # Use utf-8-sig to automatically handle UTF-8 BOM if present
    try:
        content = await file.read()
        # Try utf-8-sig first (handles BOM), fallback to utf-8
        try:
            text_content = content.decode('utf-8-sig')
        except UnicodeDecodeError:
            # Fallback to regular utf-8 if utf-8-sig fails
            text_content = content.decode('utf-8')
        rules_json = json.loads(text_content)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON: {str(e)}"
        )
    except UnicodeDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file encoding: {str(e)}. File must be UTF-8 encoded."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read file: {str(e)}"
        )
    
    # Auto-normalize and validate JSON schema
    rules_json = _normalize_ruleset(rules_json, domain, jurisdiction)
    validation = _validate_ruleset_json(rules_json, domain, jurisdiction)
    
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
    try:
        storage_service = RulesStorageService()
    except ValueError as e:
        logger.error(f"Failed to initialize RulesStorageService: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Storage service initialization failed: {str(e)}"
        )
    except Exception as e:
        logger.exception("Unexpected error initializing RulesStorageService")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Storage service initialization failed: {str(e)}"
        )
    
    try:
        upload_result = storage_service.upload_ruleset(
            rules_json=rules_json,
            domain=domain,
            jurisdiction=jurisdiction,
            ruleset_version=ruleset_version,
            rulebook_version=rulebook_version
        )
    except ValueError as e:
        logger.error(f"Ruleset upload failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        logger.exception("Unexpected error during ruleset upload")
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

    import_summary = None
    if isinstance(rules_json, list):
        try:
            importer = RulesImporter(db)
            import_summary = importer.import_ruleset(
                ruleset=ruleset,
                rules_payload=rules_json,
                activate=False,
                actor_id=current_user.id,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Rules import failed for ruleset %s", ruleset.id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to import rules: {exc}",
            )
    
    # Create audit log
    audit = RulesetAudit(
        ruleset_id=ruleset.id,
        action=RulesetAuditAction.UPLOAD.value,
        actor_id=current_user.id,
        detail={
            "validation": validation.model_dump() if hasattr(validation, 'model_dump') else validation.dict(),
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
            detail={"validation": validation.model_dump() if hasattr(validation, 'model_dump') else validation.dict()}
        )
        db.add(validate_audit)
    
    try:
        db.commit()
        db.refresh(ruleset)
        logger.info(f"Successfully uploaded ruleset {ruleset.id} (domain={domain}, jurisdiction={jurisdiction}, status={ruleset.status})")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to commit ruleset upload: {e}", exc_info=True)
        # Clean up storage file if database commit failed
        try:
            storage_service.delete_ruleset_file(upload_result["file_path"])
        except:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save ruleset: {str(e)}"
        )
    
    summary_payload = (
        RulesImportSummaryModel.model_validate(import_summary.as_dict())
        if import_summary
        else None
    )
    
    # Clear cache so dashboard refreshes instantly
    try:
        rules_service = get_rules_service()
        rules_service.clear_cache()
    except Exception:
        pass  # Don't fail upload if cache clear fails

    return RulesetUploadResponse(
        ruleset=RulesetResponse.model_validate(ruleset),
        validation=validation,
        import_summary=summary_payload,
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
        _set_rules_activation(db, existing_active.id, is_active=False)
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
    
    # Import normalized rules and activate them
    try:
        rules_payload = _load_ruleset_rules(ruleset)
    except (FileNotFoundError, ValueError) as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load ruleset file: {exc}"
        )

    try:
        importer = RulesImporter(db)
        import_summary = importer.import_ruleset(
            ruleset=ruleset,
            rules_payload=rules_payload,
            activate=True,
            actor_id=current_user.id,
        )
        logger.info(
            "Ruleset %s import summary: %s",
            ruleset.id,
            import_summary.as_dict(),
        )
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to import rules for publish: {exc}",
        )

    # Create audit log
    publish_audit = RulesetAudit(
        ruleset_id=ruleset.id,
        action=RulesetAuditAction.PUBLISH.value,
        actor_id=current_user.id,
        detail={"replaced_ruleset_id": str(existing_active.id) if existing_active else None}
    )
    db.add(publish_audit)
    
    try:
        db.commit()
        db.refresh(ruleset)
        logger.info(f"Successfully published ruleset {ruleset.id} (domain={ruleset.domain}, jurisdiction={ruleset.jurisdiction})")
        if existing_active:
            logger.info(f"Archived previous active ruleset {existing_active.id}")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to commit ruleset publish: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to publish ruleset: {str(e)}"
        )
    
    # Invalidate cache for this domain/jurisdiction
    _clear_rules_cache(ruleset.domain, ruleset.jurisdiction)
    
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
        _set_rules_activation(db, current_active.id, is_active=False)
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
    try:
        rules_payload = _load_ruleset_rules(target_ruleset)
    except (FileNotFoundError, ValueError) as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load ruleset file: {exc}"
        )

    try:
        importer = RulesImporter(db)
        importer.import_ruleset(
            ruleset=target_ruleset,
            rules_payload=rules_payload,
            activate=True,
            actor_id=current_user.id,
        )
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to import rules for rollback: {exc}",
        )
    
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

    _clear_rules_cache(target_ruleset.domain, target_ruleset.jurisdiction)
    
    return RulesetResponse.model_validate(target_ruleset)


@router.post("/{ruleset_id}/archive", response_model=RulesetResponse)
async def archive_ruleset(
    ruleset_id: UUID,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Archive a ruleset (set status to archived and deactivate its rules).
    """
    ruleset = db.query(Ruleset).filter(Ruleset.id == ruleset_id).first()
    if not ruleset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ruleset not found"
        )
    
    if ruleset.status == RulesetStatus.ARCHIVED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ruleset is already archived"
        )
    
    # Archive the ruleset
    ruleset.status = RulesetStatus.ARCHIVED.value
    _set_rules_activation(db, ruleset.id, is_active=False)
    
    # Create audit log
    archive_audit = RulesetAudit(
        ruleset_id=ruleset.id,
        action=RulesetAuditAction.ARCHIVE.value,
        actor_id=current_user.id,
        detail={"reason": "Manual archive via admin"}
    )
    db.add(archive_audit)
    
    db.commit()
    db.refresh(ruleset)
    
    _clear_rules_cache(ruleset.domain, ruleset.jurisdiction)
    logger.info(f"Archived ruleset {ruleset_id} by user {current_user.id}")
    
    return RulesetResponse.model_validate(ruleset)


@router.delete("/{ruleset_id}")
async def delete_ruleset(
    ruleset_id: UUID,
    hard: bool = Query(default=False, description="If true, permanently delete; otherwise soft-delete (archive)"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Delete a ruleset.
    
    - soft delete (default): Archives the ruleset and deactivates its rules
    - hard delete: Permanently removes the ruleset and all associated rules
    """
    ruleset = db.query(Ruleset).filter(Ruleset.id == ruleset_id).first()
    if not ruleset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ruleset not found"
        )
    
    if hard:
        # Delete all associated rules first
        deleted_rules = db.query(RuleRecord).filter(RuleRecord.ruleset_id == ruleset_id).delete(synchronize_session=False)
        
        # Delete all audit logs
        db.query(RulesetAudit).filter(RulesetAudit.ruleset_id == ruleset_id).delete(synchronize_session=False)
        
        # Try to delete the file from storage
        try:
            if ruleset.file_path:
                storage_service = RulesStorageService()
                storage_service.delete_ruleset_file(ruleset.file_path)
        except Exception as exc:
            logger.warning(f"Failed to delete ruleset file: {exc}")
        
        # Delete the ruleset record
        db.delete(ruleset)
        db.commit()
        
        _clear_rules_cache(ruleset.domain, ruleset.jurisdiction)
        logger.info(f"Hard deleted ruleset {ruleset_id} ({deleted_rules} rules) by user {current_user.id}")
        
        return {"success": True, "message": f"Ruleset permanently deleted ({deleted_rules} rules removed)"}
    else:
        # Soft delete = archive
        if ruleset.status == RulesetStatus.ARCHIVED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ruleset is already archived"
            )
        
        ruleset.status = RulesetStatus.ARCHIVED.value
        _set_rules_activation(db, ruleset.id, is_active=False)
        
        archive_audit = RulesetAudit(
            ruleset_id=ruleset.id,
            action=RulesetAuditAction.ARCHIVE.value,
            actor_id=current_user.id,
            detail={"reason": "Soft delete via admin"}
        )
        db.add(archive_audit)
        
        db.commit()
        
        _clear_rules_cache(ruleset.domain, ruleset.jurisdiction)
        logger.info(f"Soft deleted (archived) ruleset {ruleset_id} by user {current_user.id}")
        
        return {"success": True, "message": "Ruleset archived"}


@router.get("", response_model=RulesetListResponse)
async def list_rulesets(
    domain: Optional[str] = Query(None),
    jurisdiction: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=2000),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    List rulesets from the new DB-backed system.

    Removes legacy rules_registry entirely.

    Supports domain/jurisdiction/status filtering + pagination.

    """

    query = db.query(Ruleset)

    if domain:
        query = query.filter(Ruleset.domain == domain)

    if jurisdiction:
        query = query.filter(Ruleset.jurisdiction == jurisdiction)

    if status:
        query = query.filter(Ruleset.status == status)

    total = query.count()

    rulesets = (
        query.order_by(Ruleset.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = [RulesetResponse.model_validate(r) for r in rulesets]

    return RulesetListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=items,
    )


@router.get("/active/all", response_model=List[ActiveRulesetResponse])
async def get_all_active_rulesets(
    include_content: bool = Query(default=False, description="Include full JSON content"),
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all active rulesets at once.
    
    This is more efficient than querying individual domain/jurisdiction combinations.
    Public endpoint (no admin required).
    """
    import time
    start_time = time.time()
    
    try:
        # Query all active rulesets (should be fast with index)
        rulesets = db.query(Ruleset).filter(
            Ruleset.status == RulesetStatus.ACTIVE.value
        ).all()
        
        query_time = time.time() - start_time
        if query_time > 1.0:
            logger.warning(f"Slow database query for all active rulesets: {query_time:.2f}s")
        
        results = []
        storage_service = None
        
        # Only initialize storage service once if needed
        if include_content or any(r.file_path for r in rulesets):
            try:
                storage_service = RulesStorageService()
            except Exception as e:
                logger.warning(f"Failed to initialize RulesStorageService: {e}")
        
        for ruleset in rulesets:
            signed_url = None
            content = None
            
            if storage_service and ruleset.file_path:
                try:
                    signed_url = storage_service.get_signed_url(ruleset.file_path, expires_in=3600)
                except Exception as e:
                    logger.warning(f"Failed to generate signed URL for {ruleset.file_path}: {e}")
                
                if include_content:
                    try:
                        file_data = storage_service.get_ruleset_file(ruleset.file_path)
                        content = file_data["content"]
                    except Exception as e:
                        logger.warning(f"Failed to fetch content for {ruleset.file_path}: {e}")
            
            results.append(ActiveRulesetResponse(
                ruleset=RulesetResponse.model_validate(ruleset),
                signed_url=signed_url,
                content=content
            ))
        
        total_time = time.time() - start_time
        if total_time > 2.0:
            logger.warning(f"Slow /admin/rulesets/active/all response: {total_time:.2f}s")
        
        return results
    except Exception as e:
        logger.exception(f"Unexpected error in get_all_active_rulesets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
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
    import time
    start_time = time.time()
    
    try:
        # Query for active ruleset (should be fast with index)
        # Use the partial unique index for optimal performance
        ruleset = db.query(Ruleset).filter(
            and_(
                Ruleset.domain == domain,
                Ruleset.jurisdiction == jurisdiction,
                Ruleset.status == RulesetStatus.ACTIVE.value
            )
        ).first()
        
        query_time = time.time() - start_time
        if query_time > 1.0:
            logger.warning(f"Slow database query for active ruleset: {query_time:.2f}s (domain={domain}, jurisdiction={jurisdiction})")
        
        if not ruleset:
            # Return 404 immediately without any storage initialization
            logger.debug(f"No active ruleset found for domain={domain}, jurisdiction={jurisdiction}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No active ruleset found for domain={domain}, jurisdiction={jurisdiction}"
            )
        
        signed_url = None
        content = None
        
        # Only initialize storage service if we actually need it (for signed URL or content)
        # This avoids slow Supabase client initialization when not needed
        if include_content or ruleset.file_path:
            storage_init_start = time.time()
            try:
                storage_service = RulesStorageService()
                storage_init_time = time.time() - storage_init_start
                if storage_init_time > 2.0:
                    logger.warning(f"Slow Supabase Storage initialization: {storage_init_time:.2f}s")
                
                # Generate signed URL for download (1 hour expiry) - only if file_path exists
                if ruleset.file_path:
                    try:
                        signed_url_start = time.time()
                        signed_url = storage_service.get_signed_url(ruleset.file_path, expires_in=3600)
                        signed_url_time = time.time() - signed_url_start
                        if signed_url_time > 1.0:
                            logger.warning(f"Slow signed URL generation: {signed_url_time:.2f}s")
                    except Exception as e:
                        logger.warning(f"Failed to generate signed URL for {ruleset.file_path}: {e}")
                
                # Only fetch content if explicitly requested (this can be slow for large files)
                if include_content and ruleset.file_path:
                    try:
                        content_start = time.time()
                        file_data = storage_service.get_ruleset_file(ruleset.file_path)
                        content = file_data["content"]
                        content_time = time.time() - content_start
                        if content_time > 2.0:
                            logger.warning(f"Slow content fetch: {content_time:.2f}s")
                    except Exception as e:
                        logger.error(f"Failed to fetch ruleset file content: {e}", exc_info=True)
                        # Continue without content
            except Exception as e:
                logger.error(f"Failed to initialize RulesStorageService: {e}", exc_info=True)
                # Continue without storage features - endpoint still works with just metadata
        
        total_time = time.time() - start_time
        if total_time > 2.0:
            logger.warning(f"Slow /admin/rulesets/active response: {total_time:.2f}s")
        
        return ActiveRulesetResponse(
            ruleset=RulesetResponse.model_validate(ruleset),
            signed_url=signed_url,
            content=content
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in get_active_ruleset: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
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


@rules_router.get("", response_model=RuleListResponse)
async def list_rules(
    domain: Optional[str] = Query(None),
    document_type: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    requires_llm: Optional[bool] = Query(None),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = db.query(RuleRecord)

    if domain:
        query = query.filter(RuleRecord.domain == domain)
    if document_type:
        query = query.filter(RuleRecord.document_type == document_type)
    if severity:
        query = query.filter(RuleRecord.severity == severity)
    if requires_llm is not None:
        query = query.filter(RuleRecord.requires_llm.is_(requires_llm))
    if is_active is not None:
        query = query.filter(RuleRecord.is_active.is_(is_active))
    if search:
        like_value = f"%{search.lower()}%"
        query = query.filter(
            or_(
                RuleRecord.rule_id.ilike(like_value),
                RuleRecord.title.ilike(like_value),
                RuleRecord.reference.ilike(like_value),
            )
        )

    total = query.count()
    rules = (
        query.order_by(RuleRecord.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = [_serialize_rule_record(rule) for rule in rules]
    return RuleListResponse(items=items, total=total, page=page, page_size=page_size)


@rules_router.get("/{rule_id}", response_model=RuleRecordResponse)
async def get_rule(
    rule_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    rule = _get_rule_or_404(db, rule_id)
    return _serialize_rule_record(rule)


@rules_router.patch("/{rule_id}", response_model=RuleRecordResponse)
async def update_rule(
    rule_id: str,
    payload: RuleUpdateRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    rule = _get_rule_or_404(db, rule_id)
    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No update fields provided",
        )

    if payload.rule_json:
        if not rule.ruleset_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rule is not linked to a ruleset",
            )
        target_ruleset = (
            db.query(Ruleset).filter(Ruleset.id == rule.ruleset_id).first()
        )
        if not target_ruleset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Linked ruleset not found",
            )
        importer = RulesImporter(db)
        importer.import_ruleset(
            ruleset=target_ruleset,
            rules_payload=[payload.rule_json],
            activate=payload.is_active if payload.is_active is not None else rule.is_active,
            actor_id=current_user.id,
        )
        record_rule_audit(
            db,
            action="edit_json",
            rule_id=rule.rule_id,
            ruleset_id=rule.ruleset_id,
            actor_id=current_user.id,
            detail={"updated_fields": list(payload.rule_json.keys())},
        )
        rules_update_total.labels(action="edit_json").inc()
    else:
        detail_payload: Dict[str, Any] = {}
        if payload.is_active is not None:
            rule.is_active = payload.is_active
            rule.archived_at = None if payload.is_active else datetime.now(timezone.utc)
            detail_payload["is_active"] = payload.is_active
        if payload.severity is not None:
            rule.severity = payload.severity
            detail_payload["severity"] = payload.severity
        if payload.tags is not None:
            rule.tags = payload.tags
            detail_payload["tags"] = payload.tags
        if payload.metadata is not None:
            rule.rule_metadata = payload.metadata
            detail_payload["metadata"] = payload.metadata

        if detail_payload:
            record_rule_audit(
                db,
                action="update",
                rule_id=rule.rule_id,
                ruleset_id=rule.ruleset_id,
                actor_id=current_user.id,
                detail=detail_payload,
            )
            rules_update_total.labels(action="update").inc()

    db.commit()
    db.refresh(rule)
    _clear_rules_cache(rule.domain, rule.jurisdiction)
    return _serialize_rule_record(rule)


@rules_router.delete("/{rule_id}", response_model=RuleDeleteResponse)
async def delete_rule(
    rule_id: str,
    hard: bool = Query(False, description="Permanently delete the rule"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    rule = _get_rule_or_404(db, rule_id)
    if hard:
        db.delete(rule)
        record_rule_audit(
            db,
            action="delete",
            rule_id=rule_id,
            ruleset_id=rule.ruleset_id,
            actor_id=current_user.id,
            detail=None,
        )
        rules_update_total.labels(action="delete").inc()
        db.commit()
        _clear_rules_cache(rule.domain, rule.jurisdiction)
        return RuleDeleteResponse(rule_id=rule_id, archived=False)

    rule.is_active = False
    rule.archived_at = datetime.now(timezone.utc)
    record_rule_audit(
        db,
        action="archive",
        rule_id=rule_id,
        ruleset_id=rule.ruleset_id,
        actor_id=current_user.id,
        detail=None,
    )
    rules_update_total.labels(action="archive").inc()
    db.commit()
    _clear_rules_cache(rule.domain, rule.jurisdiction)
    return RuleDeleteResponse(rule_id=rule_id, archived=True)


@rules_router.post("/bulk-sync", response_model=BulkSyncResponse)
async def bulk_sync_rules(
    request: Optional[BulkSyncRequest] = Body(default=None),
    ruleset_id: Optional[UUID] = Query(None),
    include_inactive: bool = Query(False),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    effective_ruleset_id = ruleset_id or (request.ruleset_id if request else None)
    effective_include_inactive = include_inactive or (
        request.include_inactive if request else False
    )

    query = db.query(Ruleset)
    if effective_ruleset_id:
        query = query.filter(Ruleset.id == effective_ruleset_id)
    elif not effective_include_inactive:
        query = query.filter(Ruleset.status == RulesetStatus.ACTIVE.value)

    rulesets = query.all()
    if not rulesets:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No matching rulesets found",
        )

    importer = RulesImporter(db)
    response_items: List[BulkSyncResponseItem] = []
    cache_keys: Set[Tuple[Optional[str], Optional[str]]] = set()

    for target in rulesets:
        try:
            payload = _load_ruleset_rules(target)
        except (FileNotFoundError, ValueError) as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to load ruleset {target.id}: {exc}",
            )

        try:
            summary = importer.import_ruleset(
                ruleset=target,
                rules_payload=payload,
                activate=target.status == RulesetStatus.ACTIVE.value,
                actor_id=current_user.id,
            )
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to import rules for ruleset {target.id}: {exc}",
            )

        if target.status != RulesetStatus.ACTIVE.value:
            _set_rules_activation(db, target.id, is_active=False)
        else:
            cache_keys.add((target.domain, target.jurisdiction))

        response_items.append(
            BulkSyncResponseItem(
                ruleset_id=target.id,
                status=target.status,
                domain=target.domain,
                jurisdiction=target.jurisdiction,
                summary=summary.as_dict(),
            )
        )
        logger.info(
            "Rules bulk sync complete",
            extra={
                "ruleset_id": str(target.id),
                "domain": target.domain,
                "jurisdiction": target.jurisdiction,
                "inserted": summary.inserted,
                "updated": summary.updated,
                "skipped": summary.skipped,
            },
        )

    db.commit()
    for domain, jurisdiction in cache_keys:
        _clear_rules_cache(domain, jurisdiction)
    return BulkSyncResponse(items=response_items)
