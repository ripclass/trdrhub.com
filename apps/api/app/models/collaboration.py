"""
Collaboration Models
Threaded comments, mentions, attachments, and resolutions for LC processing
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Index, DECIMAL
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum
import uuid

from app.database import Base


class ThreadStatus(str, Enum):
    OPEN = "open"
    RESOLVED = "resolved"
    CLOSED = "closed"


class CommentVisibility(str, Enum):
    TENANT = "tenant"
    BANK = "bank"
    INTERNAL = "internal"


class ResolutionStatus(str, Enum):
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    CLOSED = "closed"


class CommentThread(Base):
    """Comment thread for LC jobs or discrepancies"""

    __tablename__ = "comment_threads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(64), nullable=False, index=True)
    bank_alias = Column(String(32), nullable=True, index=True)

    # Link to LC job or specific discrepancy
    job_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    discrepancy_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    title = Column(String(256), nullable=False)
    description = Column(Text)
    status = Column(String(16), nullable=False, default=ThreadStatus.OPEN)
    priority = Column(String(16), default="normal")  # low, normal, high, urgent

    created_by = Column(UUID(as_uuid=True), nullable=False)
    assigned_to = Column(UUID(as_uuid=True), nullable=True)

    watchers_count = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)

    last_activity_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    comments = relationship("Comment", back_populates="thread", cascade="all, delete-orphan")
    resolutions = relationship("Resolution", back_populates="thread", cascade="all, delete-orphan")
    watches = relationship("Watch", back_populates="thread", cascade="all, delete-orphan")

    __table_args__ = (
        Index('ix_threads_tenant_status', 'tenant_id', 'status'),
        Index('ix_threads_job_id', 'job_id'),
        Index('ix_threads_activity', 'last_activity_at'),
    )


class Comment(Base):
    """Individual comment in a thread"""

    __tablename__ = "comments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thread_id = Column(UUID(as_uuid=True), ForeignKey("comment_threads.id", ondelete="CASCADE"), nullable=False)

    author_id = Column(UUID(as_uuid=True), nullable=False)
    author_role = Column(String(32), nullable=False)  # exporter, importer, bank_officer, admin

    body_md = Column(Text, nullable=False)  # Markdown source
    body_html = Column(Text, nullable=False)  # Rendered HTML

    visibility = Column(String(16), nullable=False, default=CommentVisibility.TENANT)

    # Reply threading
    parent_id = Column(UUID(as_uuid=True), ForeignKey("comments.id"), nullable=True)

    # Edit tracking
    edited_at = Column(DateTime(timezone=True), nullable=True)
    edit_count = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    thread = relationship("CommentThread", back_populates="comments")
    parent = relationship("Comment", remote_side=[id])
    mentions = relationship("Mention", back_populates="comment", cascade="all, delete-orphan")
    attachments = relationship("Attachment", back_populates="comment", cascade="all, delete-orphan")

    __table_args__ = (
        Index('ix_comments_thread_created', 'thread_id', 'created_at'),
        Index('ix_comments_author', 'author_id'),
    )


class Mention(Base):
    """User mention in a comment"""

    __tablename__ = "mentions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    comment_id = Column(UUID(as_uuid=True), ForeignKey("comments.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)

    # Notification tracking
    notified_at = Column(DateTime(timezone=True), nullable=True)
    read_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    comment = relationship("Comment", back_populates="mentions")

    __table_args__ = (
        Index('ix_mentions_user', 'user_id'),
        Index('ix_mentions_comment', 'comment_id'),
    )


class Attachment(Base):
    """File attachment on a comment"""

    __tablename__ = "attachments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    comment_id = Column(UUID(as_uuid=True), ForeignKey("comments.id", ondelete="CASCADE"), nullable=False)

    filename = Column(String(256), nullable=False)
    mime_type = Column(String(128), nullable=False)
    file_size = Column(Integer, nullable=False)

    # S3 storage
    s3_bucket = Column(String(128), nullable=False)
    s3_key = Column(String(512), nullable=False)
    s3_version_id = Column(String(128), nullable=True)

    # Security
    sha256_hash = Column(String(64), nullable=False)
    virus_scan_status = Column(String(16), default="pending")  # pending, clean, infected, error
    virus_scan_result = Column(JSONB, nullable=True)

    # Metadata
    upload_ip = Column(String(45), nullable=True)
    retention_until = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    comment = relationship("Comment", back_populates="attachments")

    __table_args__ = (
        Index('ix_attachments_comment', 'comment_id'),
        Index('ix_attachments_hash', 'sha256_hash'),
    )


class Resolution(Base):
    """Thread resolution tracking"""

    __tablename__ = "resolutions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thread_id = Column(UUID(as_uuid=True), ForeignKey("comment_threads.id", ondelete="CASCADE"), nullable=False)

    status = Column(String(16), nullable=False)
    reason = Column(Text, nullable=True)

    resolved_by = Column(UUID(as_uuid=True), nullable=False)
    approved_by = Column(UUID(as_uuid=True), nullable=True)  # For 4-eyes approval

    # Governance
    requires_approval = Column(Boolean, default=False)
    approval_requested_at = Column(DateTime(timezone=True), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    thread = relationship("CommentThread", back_populates="resolutions")

    __table_args__ = (
        Index('ix_resolutions_thread', 'thread_id'),
        Index('ix_resolutions_status', 'status'),
    )


class Watch(Base):
    """User watching a thread for notifications"""

    __tablename__ = "watches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thread_id = Column(UUID(as_uuid=True), ForeignKey("comment_threads.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)

    # Watch preferences
    notify_comments = Column(Boolean, default=True)
    notify_resolutions = Column(Boolean, default=True)
    notify_mentions = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    thread = relationship("CommentThread", back_populates="watches")

    __table_args__ = (
        Index('ix_watches_thread', 'thread_id'),
        Index('ix_watches_user', 'user_id'),
        # Unique constraint: one watch per user per thread
        Index('ix_watches_unique', 'thread_id', 'user_id', unique=True),
    )