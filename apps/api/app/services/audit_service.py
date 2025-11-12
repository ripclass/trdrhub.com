"""
Audit service for compliance traceability.
"""

import hashlib
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union, Tuple
from uuid import UUID

from fastapi import Request, Response
from sqlalchemy.orm import Session

from app.models import AuditLog, AuditAction, AuditResult, BankAuditLog
from .. import models
from app.database import get_db


class AuditService:
    """Service for handling audit logging and compliance traceability."""

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _coerce_uuid(value: Optional[Union[str, UUID]]) -> Optional[UUID]:
        if value is None:
            return None
        if isinstance(value, UUID):
            return value
        try:
            return UUID(str(value))
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _coerce_datetime(value: Optional[Union[str, datetime]]) -> datetime:
        if value is None:
            return datetime.utcnow()
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return datetime.utcnow()

    @staticmethod
    def generate_correlation_id() -> str:
        """Generate a unique correlation ID for request tracking."""
        return str(uuid.uuid4())

    @staticmethod
    def calculate_file_hash(file_content: bytes) -> str:
        """
        Calculate SHA-256 hash of file content for integrity verification.

        Args:
            file_content: File content as bytes

        Returns:
            SHA-256 hash as hex string
        """
        return hashlib.sha256(file_content).hexdigest()

    @staticmethod
    def calculate_multiple_files_hash(files_data: List[bytes]) -> str:
        """
        Calculate combined hash for multiple files.

        Args:
            files_data: List of file contents as bytes

        Returns:
            Combined SHA-256 hash as hex string
        """
        hasher = hashlib.sha256()
        for file_content in sorted(files_data):  # Sort for consistent hashing
            hasher.update(file_content)
        return hasher.hexdigest()

    @staticmethod
    def sanitize_request_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize request data by removing sensitive information.

        Args:
            data: Request data dictionary

        Returns:
            Sanitized data dictionary
        """
        sensitive_fields = [
            'password', 'token', 'secret', 'key', 'authorization',
            'x-api-key', 'auth', 'credential', 'private'
        ]

        sanitized = {}
        for key, value in data.items():
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in sensitive_fields):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                sanitized[key] = AuditService.sanitize_request_data(value)
            elif isinstance(value, list) and value and isinstance(value[0], dict):
                sanitized[key] = [AuditService.sanitize_request_data(item) for item in value]
            else:
                sanitized[key] = value

        return sanitized

    def log_action(
        self,
        action: Union[str, AuditAction],
        user: Optional[models.User] = None,
        user_id: Optional[UUID] = None,
        user_email: Optional[str] = None,
        correlation_id: Optional[str] = None,
        session_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        lc_number: Optional[str] = None,
        lc_version: Optional[str] = None,
        result: Union[str, AuditResult] = AuditResult.SUCCESS,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        endpoint: Optional[str] = None,
        http_method: Optional[str] = None,
        status_code: Optional[int] = None,
        error_message: Optional[str] = None,
        file_content: Optional[bytes] = None,
        files_content: Optional[List[bytes]] = None,
        file_size: Optional[int] = None,
        file_count: Optional[int] = None,
        request_data: Optional[Dict[str, Any]] = None,
        response_data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        audit_metadata: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[int] = None,
        retention_days: int = 2555  # 7 years default
    ) -> AuditLog:
        """
        Log an audit event with comprehensive tracking.

        Args:
            action: Action performed
            user: User object (optional)
            user_id: User ID (optional, extracted from user if not provided)
            user_email: User email (optional, extracted from user if not provided)
            correlation_id: Request correlation ID
            session_id: User session ID
            resource_type: Type of resource affected
            resource_id: Resource identifier
            lc_number: LC number if applicable
            lc_version: LC version if applicable
            result: Action result
            ip_address: Client IP address
            user_agent: Client user agent
            endpoint: API endpoint
            http_method: HTTP method
            status_code: HTTP status code
            error_message: Error message if failed
            file_content: Single file content for hashing
            files_content: Multiple files content for hashing
            file_size: File size in bytes
            file_count: Number of files
            request_data: Request payload (will be sanitized)
            response_data: Response data (will be sanitized)
            metadata: Additional metadata (legacy alias)
            audit_metadata: Additional metadata for audit records
            duration_ms: Action duration in milliseconds
            retention_days: How long to retain this log (default 7 years)

        Returns:
            Created AuditLog instance
        """
        # Extract user info if user object provided
        if user:
            user_id = user_id or user.id
            user_email = user_email or user.email
            user_role = getattr(user, 'role', None)
        else:
            user_role = None

        # Generate correlation ID if not provided
        if not correlation_id:
            correlation_id = self.generate_correlation_id()

        # Calculate file hash if content provided
        file_hash = None
        if file_content:
            file_hash = self.calculate_file_hash(file_content)
            file_size = file_size or len(file_content)
            file_count = file_count or 1
        elif files_content:
            file_hash = self.calculate_multiple_files_hash(files_content)
            file_size = file_size or sum(len(content) for content in files_content)
            file_count = file_count or len(files_content)

        # Sanitize sensitive data
        sanitized_request_data = None
        if request_data:
            sanitized_request_data = self.sanitize_request_data(request_data)

        sanitized_response_data = None
        if response_data:
            sanitized_response_data = self.sanitize_request_data(response_data)

        # Merge legacy metadata alias
        if metadata:
            if audit_metadata:
                merged = metadata.copy()
                merged.update(audit_metadata)
                audit_metadata = merged
            else:
                audit_metadata = metadata

        # Calculate retention deadline
        retention_until = datetime.utcnow() + timedelta(days=retention_days)

        # Create audit log entry
        audit_log = AuditLog(
            correlation_id=correlation_id,
            session_id=session_id,
            user_id=user_id,
            user_email=user_email,
            user_role=user_role,
            action=str(action),
            resource_type=resource_type,
            resource_id=resource_id,
            lc_number=lc_number,
            lc_version=lc_version,
            timestamp=datetime.utcnow(),
            duration_ms=duration_ms,
            ip_address=ip_address,
            user_agent=user_agent,
            endpoint=endpoint,
            http_method=http_method,
            result=str(result),
            status_code=status_code,
            error_message=error_message,
            file_hash=file_hash,
            file_size=file_size,
            file_count=file_count,
            request_data=sanitized_request_data,
            response_data=sanitized_response_data,
            audit_metadata=audit_metadata,
            retention_until=retention_until,
            archived="active"
        )

        self.db.add(audit_log)
        self.db.commit()
        self.db.refresh(audit_log)

        return audit_log

    def log_upload(
        self,
        user: models.User,
        file_content: bytes,
        filename: str,
        lc_number: Optional[str] = None,
        validation_session_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        result: AuditResult = AuditResult.SUCCESS,
        error_message: Optional[str] = None
    ) -> AuditLog:
        """Log file upload action."""
        return self.log_action(
            action=AuditAction.UPLOAD,
            user=user,
            correlation_id=correlation_id,
            resource_type="document",
            resource_id=validation_session_id,
            lc_number=lc_number,
            result=result,
            ip_address=ip_address,
            user_agent=user_agent,
            endpoint="/upload",
            http_method="POST",
            error_message=error_message,
            file_content=file_content,
            metadata={
                "filename": filename,
                "validation_session_id": validation_session_id
            }
        )

    def log_validation(
        self,
        user: models.User,
        validation_session_id: str,
        lc_number: Optional[str] = None,
        discrepancy_count: Optional[int] = None,
        correlation_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        duration_ms: Optional[int] = None,
        result: AuditResult = AuditResult.SUCCESS,
        error_message: Optional[str] = None
    ) -> AuditLog:
        """Log validation action."""
        return self.log_action(
            action=AuditAction.VALIDATE,
            user=user,
            correlation_id=correlation_id,
            resource_type="validation_session",
            resource_id=validation_session_id,
            lc_number=lc_number,
            result=result,
            ip_address=ip_address,
            user_agent=user_agent,
            endpoint="/validate",
            http_method="POST",
            duration_ms=duration_ms,
            error_message=error_message,
            metadata={
                "validation_session_id": validation_session_id,
                "discrepancy_count": discrepancy_count
            }
        )

    def log_download(
        self,
        user: models.User,
        resource_id: str,
        resource_type: str = "report",
        lc_number: Optional[str] = None,
        lc_version: Optional[str] = None,
        file_content: Optional[bytes] = None,
        correlation_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        result: AuditResult = AuditResult.SUCCESS,
        error_message: Optional[str] = None
    ) -> AuditLog:
        """Log download action."""
        return self.log_action(
            action=AuditAction.DOWNLOAD,
            user=user,
            correlation_id=correlation_id,
            resource_type=resource_type,
            resource_id=resource_id,
            lc_number=lc_number,
            lc_version=lc_version,
            result=result,
            ip_address=ip_address,
            user_agent=user_agent,
            endpoint="/download",
            http_method="GET",
            error_message=error_message,
            file_content=file_content
        )

    def log_version_action(
        self,
        action: AuditAction,
        user: models.User,
        lc_number: str,
        lc_version: str,
        version_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        endpoint: Optional[str] = None,
        http_method: Optional[str] = None,
        audit_metadata: Optional[Dict[str, Any]] = None,
        result: AuditResult = AuditResult.SUCCESS,
        error_message: Optional[str] = None
    ) -> AuditLog:
        """Log LC version-related actions."""
        return self.log_action(
            action=action,
            user=user,
            correlation_id=correlation_id,
            resource_type="lc_version",
            resource_id=version_id,
            lc_number=lc_number,
            lc_version=lc_version,
            result=result,
            ip_address=ip_address,
            user_agent=user_agent,
            endpoint=endpoint,
            http_method=http_method,
            error_message=error_message,
            audit_metadata=audit_metadata
        )

    def get_user_activity(
        self,
        user_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        actions: Optional[List[str]] = None,
        limit: int = 100
    ) -> List[AuditLog]:
        """Get audit logs for a specific user."""
        query = self.db.query(AuditLog).filter(AuditLog.user_id == user_id)

        if start_date:
            query = query.filter(AuditLog.timestamp >= start_date)
        if end_date:
            query = query.filter(AuditLog.timestamp <= end_date)
        if actions:
            query = query.filter(AuditLog.action.in_(actions))

        return query.order_by(AuditLog.timestamp.desc()).limit(limit).all()

    def get_lc_activity(
        self,
        lc_number: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AuditLog]:
        """Get audit logs for a specific LC."""
        query = self.db.query(AuditLog).filter(AuditLog.lc_number == lc_number)

        if start_date:
            query = query.filter(AuditLog.timestamp >= start_date)
        if end_date:
            query = query.filter(AuditLog.timestamp <= end_date)

        return query.order_by(AuditLog.timestamp.desc()).limit(limit).all()

    def verify_file_integrity(self, file_content: bytes, expected_hash: str) -> bool:
        """
        Verify file integrity against stored hash.

        Args:
            file_content: Current file content
            expected_hash: Expected SHA-256 hash

        Returns:
            True if hashes match, False otherwise
        """
        current_hash = self.calculate_file_hash(file_content)
        return current_hash == expected_hash

    def get_compliance_report(
        self,
        start_date: datetime,
        end_date: datetime,
        user_id: Optional[UUID] = None,
        action: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate compliance report for audit purposes.

        Args:
            start_date: Report start date
            end_date: Report end date
            user_id: Optional user filter
            action: Optional action filter

        Returns:
            Compliance report dictionary
        """
        query = self.db.query(AuditLog).filter(
            AuditLog.timestamp >= start_date,
            AuditLog.timestamp <= end_date
        )

        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        if action:
            query = query.filter(AuditLog.action == action)

        logs = query.all()

        # Calculate statistics
        total_actions = len(logs)
        successful_actions = len([log for log in logs if log.result == AuditResult.SUCCESS])
        failed_actions = len([log for log in logs if log.result == AuditResult.FAILURE])
        error_actions = len([log for log in logs if log.result == AuditResult.ERROR])

        # Group by action type
        action_counts = {}
        for log in logs:
            action_counts[log.action] = action_counts.get(log.action, 0) + 1

        # Group by user
        user_activity = {}
        for log in logs:
            if log.user_email:
                user_activity[log.user_email] = user_activity.get(log.user_email, 0) + 1

        return {
            "report_period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "summary": {
                "total_actions": total_actions,
                "successful_actions": successful_actions,
                "failed_actions": failed_actions,
                "error_actions": error_actions,
                "success_rate": round(successful_actions / max(total_actions, 1) * 100, 2)
            },
            "action_breakdown": action_counts,
            "user_activity": user_activity,
            "logs": [log.to_dict() for log in logs[:1000]]  # Limit for performance
        }

    def get_recent_actions(self, action: AuditAction, days: int = 30) -> List[AuditLog]:
        """
        Get recent actions of a specific type.

        Args:
            action: The action type to filter by
            days: Number of days to look back

        Returns:
            List of matching audit logs
        """
        since = datetime.utcnow() - timedelta(days=days)

        return self.db.query(AuditLog).filter(
            AuditLog.action == action,
            AuditLog.timestamp >= since
        ).order_by(AuditLog.timestamp.desc()).all()

    @staticmethod
    async def append_entry(
        db: Session,
        event: Optional[Dict[str, Any]] = None,
        bank_id: Optional[Union[str, UUID]] = None,
        tenant_id: Optional[Union[str, UUID]] = None,
        lc_id: Optional[Union[str, UUID]] = None,
        **legacy_fields: Any,
    ):
        """
        Persist an audit event either to the bank-specific ledger or the
        general audit log when ``bank_id`` is absent.
        """
        normalized_event = event.copy() if isinstance(event, dict) else {}
        normalized_event.update(legacy_fields)
        timestamp = AuditService._coerce_datetime(normalized_event.get("timestamp"))

        if bank_id:
            record = BankAuditLog(
                bank_id=AuditService._coerce_uuid(bank_id),
                tenant_id=AuditService._coerce_uuid(tenant_id),
                lc_id=AuditService._coerce_uuid(lc_id),
                event=normalized_event,
                created_at=timestamp,
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            return record

        log_entry = AuditLog(
            correlation_id=normalized_event.get("correlation_id", str(uuid.uuid4())),
            session_id=normalized_event.get("session_id"),
            user_id=AuditService._coerce_uuid(normalized_event.get("user_id")),
            user_email=normalized_event.get("user_email"),
            user_role=normalized_event.get("user_role"),
            action=normalized_event.get("action", AuditAction.ANALYTICS_VIEW.value),
            resource_type=normalized_event.get("resource_type"),
            resource_id=normalized_event.get("resource_id"),
            lc_number=normalized_event.get("lc_number"),
            lc_version=normalized_event.get("lc_version"),
            timestamp=timestamp,
            duration_ms=normalized_event.get("duration_ms"),
            ip_address=normalized_event.get("ip_address"),
            user_agent=normalized_event.get("user_agent"),
            endpoint=normalized_event.get("endpoint"),
            http_method=normalized_event.get("http_method"),
            result=normalized_event.get("result", AuditResult.SUCCESS.value),
            status_code=normalized_event.get("status_code"),
            error_message=normalized_event.get("error_message"),
            file_hash=normalized_event.get("file_hash"),
            file_size=normalized_event.get("file_size"),
            file_count=normalized_event.get("file_count"),
            request_data=normalized_event.get("request_data"),
            response_data=normalized_event.get("response_data"),
            audit_metadata=normalized_event,
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        return log_entry

    @staticmethod
    async def search_entries(
        db: Session,
        tenant_id: Optional[Union[str, UUID]] = None,
        actor_id: Optional[Union[str, UUID]] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        action: Optional[str] = None,
        severity: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
        bank_id: Optional[Union[str, UUID]] = None,
    ) -> Tuple[List[Any], int]:
        """
        Search audit entries for admin/bank dashboards.
        """
        start = start_date or datetime.utcnow() - timedelta(days=30)
        end = end_date or datetime.utcnow()

        if bank_id:
            query = db.query(BankAuditLog).filter(BankAuditLog.bank_id == AuditService._coerce_uuid(bank_id))
            if tenant_id:
                query = query.filter(BankAuditLog.tenant_id == AuditService._coerce_uuid(tenant_id))
            if resource_id:
                query = query.filter(BankAuditLog.lc_id == AuditService._coerce_uuid(resource_id))
            query = query.filter(BankAuditLog.created_at.between(start, end))

            total = query.count()
            items = (
                query.order_by(BankAuditLog.created_at.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )
            return items, total

        query = db.query(models.AuditLogEntry).filter(
            models.AuditLogEntry.created_at.between(start, end)
        )

        if tenant_id:
            query = query.filter(models.AuditLogEntry.tenant_id == str(tenant_id))
        if actor_id:
            query = query.filter(models.AuditLogEntry.actor_id == AuditService._coerce_uuid(actor_id))
        if resource_type:
            query = query.filter(models.AuditLogEntry.resource_type == resource_type)
        if resource_id:
            query = query.filter(models.AuditLogEntry.resource_id == resource_id)
        if action:
            query = query.filter(models.AuditLogEntry.action == action)
        if severity:
            query = query.filter(models.AuditLogEntry.severity == severity)

        total = query.count()
        entries = (
            query.order_by(models.AuditLogEntry.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return entries, total


class AuditServiceSingleton:
    """
    Singleton wrapper for AuditService that provides convenience methods.
    Methods accept db as a parameter instead of requiring instance creation.
    """
    
    async def log_event(
        self,
        tenant_id: str,
        event_type: str,
        actor_id: Optional[UUID] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        db: Optional[Session] = None
    ):
        """
        Convenience method for logging audit events.
        Creates AuditService instance with db and calls log_action.
        """
        if not db:
            # Try to get db from context if available
            from app.database import get_db
            db_gen = get_db()
            db = next(db_gen)
        
        service = AuditService(db)
        return service.log_action(
            action=event_type,
            user_id=actor_id,
            resource_type=resource_type,
            resource_id=resource_id,
            audit_metadata=details or {}
        )


# Global singleton instance
audit_service = AuditServiceSingleton()