"""
Bank Duplicate Detection Router
Endpoints for finding duplicates, merging sessions, and viewing merge history
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.routers.bank import require_bank_or_admin
from app.models import User, ValidationSession, SessionStatus
from app.models.duplicate_detection import LCFingerprint, LCMergeHistory, MergeType
from app.services.similarity_service import SimilarityService
from app.schemas.duplicate_detection import (
    DuplicateCandidatesResponse,
    DuplicateCandidate,
    MergeRequest,
    MergeResponse,
    MergeHistoryResponse,
    LCMergeHistoryRead,
)
from app.services.audit_service import AuditService
from app.middleware.audit_middleware import create_audit_context
from app.models import AuditAction, AuditResult
from fastapi import Request
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bank/duplicates", tags=["bank", "duplicates"])


@router.get("/candidates/{session_id}", response_model=DuplicateCandidatesResponse)
def get_duplicate_candidates(
    session_id: UUID,
    threshold: Optional[float] = Query(None, ge=0.0, le=1.0, description="Similarity threshold (0.0-1.0)"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of candidates"),
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """
    Get duplicate candidates for a validation session.
    Returns sessions that are similar to the given session based on fingerprint matching.
    """
    audit_service = AuditService(db)
    audit_context = create_audit_context(request)
    
    try:
        # Verify session exists and user has access
        session = db.query(ValidationSession).filter(
            ValidationSession.id == session_id,
            ValidationSession.deleted_at.is_(None),
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Validation session not found")
        
        # Org scope filter (if org_id is set in request state)
        org_id = getattr(request.state, "org_id", None) if request else None
        if org_id:
            # Verify session belongs to the selected org
            from sqlalchemy.dialects.postgresql import JSONB
            from sqlalchemy import cast
            session_org_id = cast(session.extracted_data, JSONB)[
                'bank_metadata'
            ]['org_id'].astext if session.extracted_data else None
            if session_org_id != org_id:
                raise HTTPException(status_code=403, detail="Session does not belong to selected org")
        
        # Check if session belongs to user's company (for bank users)
        if current_user.role == "bank" and session.company_id != current_user.company_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Ensure session is completed
        if session.status not in [SessionStatus.COMPLETED.value, SessionStatus.FAILED.value]:
            raise HTTPException(
                status_code=400,
                detail="Session must be completed to check for duplicates"
            )
        
        # Initialize similarity service and ensure fingerprint exists
        similarity_service = SimilarityService(db)
        
        # Create fingerprint if it doesn't exist
        fingerprint = db.query(LCFingerprint).filter(
            LCFingerprint.validation_session_id == session_id
        ).first()
        
        if not fingerprint:
            fingerprint = similarity_service.create_or_update_fingerprint(
                session,
                company_id=current_user.company_id if current_user.role == "bank" else None
            )
        
        # Find duplicate candidates (respect org scope)
        candidates_data = similarity_service.find_duplicate_candidates(
            session_id,
            threshold=threshold,
            limit=limit,
            org_id=org_id  # Pass org_id to filter candidates
        )
        
        # Convert to response format
        candidates = []
        for cand_data in candidates_data:
            # Get the session for additional details
            cand_session = db.query(ValidationSession).filter(
                ValidationSession.id == cand_data['session_id']
            ).first()
            
            if cand_session:
                candidates.append(DuplicateCandidate(
                    session_id=cand_data['session_id'],
                    lc_number=cand_data['lc_number'],
                    client_name=cand_data['client_name'],
                    similarity_score=cand_data['similarity_score'],
                    content_similarity=cand_data.get('content_similarity'),
                    metadata_similarity=cand_data.get('metadata_similarity'),
                    field_matches=cand_data.get('field_matches'),
                    detected_at=fingerprint.created_at,  # Use fingerprint creation time
                    completed_at=cand_session.processing_completed_at,
                ))
        
        # Log audit
        audit_service.log_action(
            action=AuditAction.READ,
            user=current_user,
            correlation_id=audit_context['correlation_id'],
            resource_type="duplicate_candidates",
            resource_id=str(session_id),
            ip_address=audit_context['ip_address'],
            user_agent=audit_context['user_agent'],
            endpoint=audit_context['endpoint'],
            http_method=audit_context['http_method'],
            result=AuditResult.SUCCESS,
            audit_metadata={
                "session_id": str(session_id),
                "candidates_count": len(candidates),
                "threshold": threshold,
            }
        )
        
        return DuplicateCandidatesResponse(
            session_id=session_id,
            candidates=candidates,
            total_count=len(candidates),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting duplicate candidates: {e}", exc_info=True)
        audit_service.log_action(
            action=AuditAction.READ,
            user=current_user,
            correlation_id=audit_context['correlation_id'],
            resource_type="duplicate_candidates",
            resource_id=str(session_id),
            ip_address=audit_context['ip_address'],
            user_agent=audit_context['user_agent'],
            endpoint=audit_context['endpoint'],
            http_method=audit_context['http_method'],
            result=AuditResult.FAILURE,
            audit_metadata={"error": str(e)}
        )
        raise HTTPException(status_code=500, detail="Failed to get duplicate candidates")


@router.post("/merge", response_model=MergeResponse)
def merge_sessions(
    merge_request: MergeRequest,
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """
    Merge two validation sessions.
    The source session will be marked as merged into the target session.
    """
    audit_service = AuditService(db)
    audit_context = create_audit_context(request)
    
    try:
        # Verify both sessions exist
        source_session = db.query(ValidationSession).filter(
            ValidationSession.id == merge_request.source_session_id,
            ValidationSession.deleted_at.is_(None),
        ).first()
        
        target_session = db.query(ValidationSession).filter(
            ValidationSession.id == merge_request.target_session_id,
            ValidationSession.deleted_at.is_(None),
        ).first()
        
        if not source_session or not target_session:
            raise HTTPException(status_code=404, detail="One or both sessions not found")
        
        # Check access
        if current_user.role == "bank":
            if source_session.company_id != current_user.company_id or \
               target_session.company_id != current_user.company_id:
                raise HTTPException(status_code=403, detail="Access denied")
        
        # Prevent merging session into itself
        if source_session.id == target_session.id:
            raise HTTPException(status_code=400, detail="Cannot merge session into itself")
        
        # Validate merge type
        try:
            merge_type_enum = MergeType(merge_request.merge_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid merge_type: {merge_request.merge_type}"
            )
        
        # Determine which fields to merge
        fields_to_merge = merge_request.fields_to_merge
        if fields_to_merge is None:
            # Merge all fields by default
            fields_to_merge = ['extracted_data', 'validation_results', 'documents']
        
        # Perform merge (for now, just record the merge history)
        # In a full implementation, you might want to:
        # - Copy data from source to target
        # - Update target session with merged data
        # - Mark source session as merged/deleted
        
        fields_merged = {}
        preserved_data = {}
        
        # Record what was merged
        if 'extracted_data' in fields_to_merge:
            fields_merged['extracted_data'] = True
            preserved_data['source_extracted_data'] = source_session.extracted_data
        
        if 'validation_results' in fields_to_merge:
            fields_merged['validation_results'] = True
            preserved_data['source_validation_results'] = source_session.validation_results
        
        # Create merge history record
        merge_history = LCMergeHistory(
            source_session_id=merge_request.source_session_id,
            target_session_id=merge_request.target_session_id,
            merge_type=merge_type_enum.value,
            merge_reason=merge_request.merge_reason,
            merged_by=current_user.id,
            fields_merged=fields_merged,
            preserved_data=preserved_data,
        )
        
        db.add(merge_history)
        db.commit()
        db.refresh(merge_history)
        
        # Log audit
        audit_service.log_action(
            action=AuditAction.UPDATE,
            user=current_user,
            correlation_id=audit_context['correlation_id'],
            resource_type="session_merge",
            resource_id=str(merge_request.target_session_id),
            ip_address=audit_context['ip_address'],
            user_agent=audit_context['user_agent'],
            endpoint=audit_context['endpoint'],
            http_method=audit_context['http_method'],
            result=AuditResult.SUCCESS,
            audit_metadata={
                "source_session_id": str(merge_request.source_session_id),
                "target_session_id": str(merge_request.target_session_id),
                "merge_type": merge_request.merge_type,
                "merge_id": str(merge_history.id),
            }
        )
        
        return MergeResponse(
            merge_id=merge_history.id,
            source_session_id=merge_request.source_session_id,
            target_session_id=merge_request.target_session_id,
            merge_type=merge_request.merge_type,
            merged_at=merge_history.merged_at,
            fields_merged=fields_merged,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error merging sessions: {e}", exc_info=True)
        db.rollback()
        audit_service.log_action(
            action=AuditAction.UPDATE,
            user=current_user,
            correlation_id=audit_context['correlation_id'],
            resource_type="session_merge",
            resource_id=str(merge_request.target_session_id) if merge_request else None,
            ip_address=audit_context['ip_address'],
            user_agent=audit_context['user_agent'],
            endpoint=audit_context['endpoint'],
            http_method=audit_context['http_method'],
            result=AuditResult.FAILURE,
            audit_metadata={"error": str(e)}
        )
        raise HTTPException(status_code=500, detail="Failed to merge sessions")


@router.get("/history/{session_id}", response_model=MergeHistoryResponse)
def get_merge_history(
    session_id: UUID,
    current_user: User = Depends(require_bank_or_admin),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """
    Get merge history for a validation session.
    Returns all merges where this session was either the source or target.
    """
    audit_service = AuditService(db)
    audit_context = create_audit_context(request)
    
    try:
        # Verify session exists
        session = db.query(ValidationSession).filter(
            ValidationSession.id == session_id,
            ValidationSession.deleted_at.is_(None),
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Validation session not found")
        
        # Check access
        if current_user.role == "bank" and session.company_id != current_user.company_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get merge history (both as source and target)
        merges = db.query(LCMergeHistory).filter(
            (LCMergeHistory.source_session_id == session_id) |
            (LCMergeHistory.target_session_id == session_id)
        ).order_by(LCMergeHistory.merged_at.desc()).all()
        
        merge_reads = [LCMergeHistoryRead.model_validate(m) for m in merges]
        
        # Log audit
        audit_service.log_action(
            action=AuditAction.READ,
            user=current_user,
            correlation_id=audit_context['correlation_id'],
            resource_type="merge_history",
            resource_id=str(session_id),
            ip_address=audit_context['ip_address'],
            user_agent=audit_context['user_agent'],
            endpoint=audit_context['endpoint'],
            http_method=audit_context['http_method'],
            result=AuditResult.SUCCESS,
            audit_metadata={
                "session_id": str(session_id),
                "merge_count": len(merge_reads),
            }
        )
        
        return MergeHistoryResponse(
            merges=merge_reads,
            total_count=len(merge_reads),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting merge history: {e}", exc_info=True)
        audit_service.log_action(
            action=AuditAction.READ,
            user=current_user,
            correlation_id=audit_context['correlation_id'],
            resource_type="merge_history",
            resource_id=str(session_id),
            ip_address=audit_context['ip_address'],
            user_agent=audit_context['user_agent'],
            endpoint=audit_context['endpoint'],
            http_method=audit_context['http_method'],
            result=AuditResult.FAILURE,
            audit_metadata={"error": str(e)}
        )
        raise HTTPException(status_code=500, detail="Failed to get merge history")

