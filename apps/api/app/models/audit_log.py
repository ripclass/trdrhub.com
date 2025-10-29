"""
Audit Log model for compliance traceability.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional

from sqlalchemy import Column, String, DateTime, Text, JSON, UUID, ForeignKey, Integer
from sqlalchemy.orm import relationship

from ..database import Base


class AuditAction(str, Enum):
    """Audit action types."""
    UPLOAD = "upload"
    VALIDATE = "validate"
    DOWNLOAD = "download"
    CREATE_VERSION = "create_version"
    UPDATE_VERSION = "update_version"
    COMPARE_VERSIONS = "compare_versions"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    ACCESS_DENIED = "access_denied"
    # User management actions
    CREATE_USER = "create_user"
    ROLE_CHANGE = "role_change"
    DEACTIVATE_USER = "deactivate_user"
    REACTIVATE_USER = "reactivate_user"
    # Analytics actions
    ANALYTICS_VIEW = "analytics_view"
    ANALYTICS_EXPORT = "analytics_export"


class AuditResult(str, Enum):
    """Audit result types."""
    SUCCESS = "success"
    FAILURE = "failure"
    ERROR = "error"
    PARTIAL = "partial"


class AuditLog(Base):
    """
    Comprehensive audit log for compliance traceability.

    Tracks all user actions with who/what/when/result/version for compliance.
    """
    __tablename__ = "audit_log"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Correlation and tracking
    correlation_id = Column(String(100), nullable=False, index=True, doc="Request correlation ID")
    session_id = Column(String(100), nullable=True, index=True, doc="User session ID")

    # WHO: User information
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    user_email = Column(String(255), nullable=True, index=True)
    user_role = Column(String(50), nullable=True)

    # WHAT: Action details
    action = Column(String(50), nullable=False, index=True, doc="Action performed")
    resource_type = Column(String(50), nullable=True, index=True, doc="Type of resource (LC, document, etc.)")
    resource_id = Column(String(255), nullable=True, index=True, doc="Resource identifier")

    # LC-specific fields
    lc_number = Column(String(100), nullable=True, index=True, doc="LC number if applicable")
    lc_version = Column(String(10), nullable=True, doc="LC version (V1, V2, etc.)")

    # WHEN: Timing information
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    duration_ms = Column(Integer, nullable=True, doc="Action duration in milliseconds")

    # WHERE: Request information
    ip_address = Column(String(45), nullable=True, index=True, doc="Client IP address")
    user_agent = Column(Text, nullable=True, doc="Client user agent")
    endpoint = Column(String(255), nullable=True, doc="API endpoint accessed")
    http_method = Column(String(10), nullable=True, doc="HTTP method")

    # RESULT: Outcome information
    result = Column(String(20), nullable=False, index=True, doc="Action result")
    status_code = Column(Integer, nullable=True, doc="HTTP status code")
    error_message = Column(Text, nullable=True, doc="Error message if failed")

    # Evidence and integrity
    file_hash = Column(String(64), nullable=True, doc="SHA-256 hash of files involved")
    file_size = Column(Integer, nullable=True, doc="Total size of files in bytes")
    file_count = Column(Integer, nullable=True, doc="Number of files involved")

    # Metadata and context
    request_data = Column(JSON, nullable=True, doc="Request payload (sanitized)")
    response_data = Column(JSON, nullable=True, doc="Response data (sanitized)")
    audit_metadata = Column(JSON, nullable=True, doc="Additional context and metadata")

    # Compliance fields
    retention_until = Column(DateTime, nullable=True, doc="Log retention deadline")
    archived = Column(String(20), default="active", doc="Archive status")

    # Relationships
    user = relationship("User", backref="audit_logs")

    def __repr__(self):
        return f"<AuditLog(id={self.id}, action={self.action}, user={self.user_email}, timestamp={self.timestamp})>"

    @property
    def formatted_timestamp(self) -> str:
        """Return formatted timestamp for display."""
        return self.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")

    @property
    def is_success(self) -> bool:
        """Check if the action was successful."""
        return self.result == AuditResult.SUCCESS

    @property
    def is_file_operation(self) -> bool:
        """Check if this was a file-related operation."""
        return self.action in [AuditAction.UPLOAD, AuditAction.DOWNLOAD] and self.file_hash is not None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": str(self.id),
            "correlation_id": self.correlation_id,
            "user_email": self.user_email,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "lc_number": self.lc_number,
            "lc_version": self.lc_version,
            "timestamp": self.formatted_timestamp,
            "result": self.result,
            "status_code": self.status_code,
            "ip_address": self.ip_address,
            "endpoint": self.endpoint,
            "duration_ms": self.duration_ms,
            "file_hash": self.file_hash,
            "file_size": self.file_size,
            "error_message": self.error_message
        }