"""
Document Audit Service

Tracks all document operations for compliance and history.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID

from sqlalchemy.orm import Session
from fastapi import Request

from app.models.doc_generator_catalog import DocumentAuditLog, AuditAction

logger = logging.getLogger(__name__)


class DocumentAuditService:
    """
    Service for logging and querying document audit trail.
    
    All document operations should be logged through this service
    for compliance and history tracking.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def log_action(
        self,
        document_set_id: UUID,
        user_id: UUID,
        action: AuditAction,
        request: Optional[Request] = None,
        detail: Optional[str] = None,
        field_changed: Optional[str] = None,
        old_value: Optional[str] = None,
        new_value: Optional[str] = None,
    ) -> DocumentAuditLog:
        """
        Log an audit action for a document set.
        
        Args:
            document_set_id: The document set being acted upon
            user_id: The user performing the action
            action: Type of action (AuditAction enum)
            request: FastAPI request object for IP/user-agent
            detail: Additional action detail
            field_changed: For updates, the field that changed
            old_value: Previous value (for updates)
            new_value: New value (for updates)
        
        Returns:
            The created audit log entry
        """
        # Extract request info
        ip_address = None
        user_agent = None
        session_id = None
        
        if request:
            ip_address = self._get_client_ip(request)
            user_agent = request.headers.get("user-agent", "")[:500]
            session_id = request.headers.get("x-session-id")
        
        # Create audit log
        audit_log = DocumentAuditLog(
            document_set_id=document_set_id,
            user_id=user_id,
            action=action,
            action_detail=detail,
            field_changed=field_changed,
            old_value=old_value,
            new_value=new_value,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id,
        )
        
        self.db.add(audit_log)
        self.db.commit()
        
        logger.info(f"Audit log: {action.value} on {document_set_id} by {user_id}")
        
        return audit_log
    
    def log_create(
        self,
        document_set_id: UUID,
        user_id: UUID,
        request: Optional[Request] = None,
        source: str = "manual"
    ) -> DocumentAuditLog:
        """Log document set creation"""
        return self.log_action(
            document_set_id=document_set_id,
            user_id=user_id,
            action=AuditAction.CREATED,
            request=request,
            detail=f"Created via {source}",
        )
    
    def log_update(
        self,
        document_set_id: UUID,
        user_id: UUID,
        field: str,
        old_value: Any,
        new_value: Any,
        request: Optional[Request] = None,
    ) -> DocumentAuditLog:
        """Log document set update"""
        return self.log_action(
            document_set_id=document_set_id,
            user_id=user_id,
            action=AuditAction.UPDATED,
            request=request,
            field_changed=field,
            old_value=str(old_value)[:1000] if old_value is not None else None,
            new_value=str(new_value)[:1000] if new_value is not None else None,
        )
    
    def log_generate(
        self,
        document_set_id: UUID,
        user_id: UUID,
        document_type: str,
        request: Optional[Request] = None,
    ) -> DocumentAuditLog:
        """Log document generation"""
        return self.log_action(
            document_set_id=document_set_id,
            user_id=user_id,
            action=AuditAction.GENERATED,
            request=request,
            detail=f"Generated {document_type}",
        )
    
    def log_download(
        self,
        document_set_id: UUID,
        user_id: UUID,
        document_type: Optional[str] = None,
        request: Optional[Request] = None,
    ) -> DocumentAuditLog:
        """Log document download"""
        detail = f"Downloaded {document_type}" if document_type else "Downloaded all documents"
        return self.log_action(
            document_set_id=document_set_id,
            user_id=user_id,
            action=AuditAction.DOWNLOADED,
            request=request,
            detail=detail,
        )
    
    def log_validate(
        self,
        document_set_id: UUID,
        user_id: UUID,
        result: str,
        request: Optional[Request] = None,
    ) -> DocumentAuditLog:
        """Log validation run"""
        return self.log_action(
            document_set_id=document_set_id,
            user_id=user_id,
            action=AuditAction.VALIDATED,
            request=request,
            detail=f"Validation result: {result}",
        )
    
    def log_duplicate(
        self,
        source_id: UUID,
        new_id: UUID,
        user_id: UUID,
        request: Optional[Request] = None,
    ) -> DocumentAuditLog:
        """Log document set duplication"""
        return self.log_action(
            document_set_id=new_id,
            user_id=user_id,
            action=AuditAction.DUPLICATED,
            request=request,
            detail=f"Duplicated from {source_id}",
        )
    
    def log_import(
        self,
        document_set_id: UUID,
        user_id: UUID,
        source: str,
        request: Optional[Request] = None,
    ) -> DocumentAuditLog:
        """Log import from external source (e.g., LCopilot)"""
        return self.log_action(
            document_set_id=document_set_id,
            user_id=user_id,
            action=AuditAction.IMPORTED,
            request=request,
            detail=f"Imported from {source}",
        )
    
    def log_delete(
        self,
        document_set_id: UUID,
        user_id: UUID,
        request: Optional[Request] = None,
    ) -> DocumentAuditLog:
        """Log document set deletion"""
        return self.log_action(
            document_set_id=document_set_id,
            user_id=user_id,
            action=AuditAction.DELETED,
            request=request,
        )
    
    def get_history(
        self,
        document_set_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Get audit history for a document set.
        
        Returns:
            List of audit entries ordered by time (newest first)
        """
        logs = self.db.query(DocumentAuditLog).filter(
            DocumentAuditLog.document_set_id == document_set_id
        ).order_by(
            DocumentAuditLog.created_at.desc()
        ).offset(offset).limit(limit).all()
        
        return [self._log_to_dict(log) for log in logs]
    
    def get_user_activity(
        self,
        user_id: UUID,
        days: int = 30,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get recent activity for a user"""
        since = datetime.utcnow() - timedelta(days=days)
        
        logs = self.db.query(DocumentAuditLog).filter(
            DocumentAuditLog.user_id == user_id,
            DocumentAuditLog.created_at >= since
        ).order_by(
            DocumentAuditLog.created_at.desc()
        ).limit(limit).all()
        
        return [self._log_to_dict(log) for log in logs]
    
    def get_company_activity(
        self,
        company_id: UUID,
        days: int = 30,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get recent activity for a company (requires join)"""
        # This would require joining with document_sets to filter by company
        # Implementation depends on your specific needs
        pass
    
    def _log_to_dict(self, log: DocumentAuditLog) -> Dict[str, Any]:
        """Convert audit log to dictionary"""
        return {
            "id": str(log.id),
            "document_set_id": str(log.document_set_id),
            "user_id": str(log.user_id),
            "action": log.action.value,
            "action_detail": log.action_detail,
            "field_changed": log.field_changed,
            "old_value": log.old_value,
            "new_value": log.new_value,
            "ip_address": log.ip_address,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
    
    def _get_client_ip(self, request: Request) -> Optional[str]:
        """Extract client IP from request"""
        # Check for forwarded IP (behind proxy/load balancer)
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        # Check for real IP header
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fall back to client host
        if request.client:
            return request.client.host
        
        return None


def get_audit_service(db: Session) -> DocumentAuditService:
    """Create audit service instance"""
    return DocumentAuditService(db)

