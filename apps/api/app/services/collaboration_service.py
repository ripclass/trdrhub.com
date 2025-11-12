"""
Collaboration Service
Handles threaded comments, mentions, attachments, and resolution workflows
"""

import re
import hashlib
import markdown
import bleach
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from uuid import UUID, uuid4
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.models.collaboration import (
    CommentThread, Comment, Mention, Attachment, Resolution, Watch,
    ThreadStatus, CommentVisibility, ResolutionStatus
)
from app.core.security import get_password_hash
from app.config import settings
from app.services.notification_service import notification_service
from app.services.audit_service import audit_service
from app.core.exceptions import ValidationError, PermissionError

import logging

logger = logging.getLogger(__name__)


class CollaborationService:
    """Service for managing collaboration features"""

    def __init__(self):
        self.allowed_html_tags = [
            'p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'ul', 'ol', 'li', 'blockquote', 'code', 'pre', 'a', 'img'
        ]
        self.allowed_attributes = {
            'a': ['href', 'title'],
            'img': ['src', 'alt', 'title', 'width', 'height'],
            'code': ['class'],
            'pre': ['class']
        }

    async def create_thread(
        self,
        db: Session,
        tenant_id: str,
        title: str,
        description: str,
        created_by: UUID,
        bank_alias: Optional[str] = None,
        job_id: Optional[UUID] = None,
        discrepancy_id: Optional[UUID] = None,
        priority: str = "normal",
        watchers: Optional[List[UUID]] = None
    ) -> CommentThread:
        """Create a new comment thread"""

        # Validate input
        if not job_id and not discrepancy_id:
            raise ValidationError("Thread must be linked to either a job or discrepancy")

        # Create thread
        thread = CommentThread(
            tenant_id=tenant_id,
            bank_alias=bank_alias,
            job_id=job_id,
            discrepancy_id=discrepancy_id,
            title=title,
            description=description,
            created_by=created_by,
            priority=priority,
            status=ThreadStatus.OPEN
        )

        db.add(thread)
        db.flush()  # Get the ID

        # Add creator as watcher
        await self._add_watcher(db, thread.id, created_by)

        # Add additional watchers
        if watchers:
            for user_id in watchers:
                await self._add_watcher(db, thread.id, user_id)

        db.commit()

        # Emit audit event
        await audit_service.log_event(
            tenant_id=tenant_id,
            event_type="collab.thread.created",
            actor_id=created_by,
            resource_type="comment_thread",
            resource_id=str(thread.id),
            details={
                "title": title,
                "job_id": str(job_id) if job_id else None,
                "discrepancy_id": str(discrepancy_id) if discrepancy_id else None,
                "priority": priority
            }
        )

        # Send notifications
        await notification_service.emit_event_simple(
            tenant_id=tenant_id,
            event_key="collab.thread.created",
            event_data={
                "thread_id": str(thread.id),
                "title": title,
                "created_by": str(created_by),
                "job_id": str(job_id) if job_id else None,
                "discrepancy_id": str(discrepancy_id) if discrepancy_id else None
            },
            db=db
        )

        return thread

    async def add_comment(
        self,
        db: Session,
        thread_id: UUID,
        author_id: UUID,
        author_role: str,
        body_md: str,
        visibility: str = CommentVisibility.TENANT,
        parent_id: Optional[UUID] = None
    ) -> Comment:
        """Add a comment to a thread"""

        # Get thread and validate access
        thread = db.query(CommentThread).filter(CommentThread.id == thread_id).first()
        if not thread:
            raise ValidationError("Thread not found")

        # Sanitize and render markdown
        body_html = self._render_markdown(body_md)

        # Extract mentions
        mentions = self._extract_mentions(body_md)

        # Create comment
        comment = Comment(
            thread_id=thread_id,
            author_id=author_id,
            author_role=author_role,
            body_md=body_md,
            body_html=body_html,
            visibility=visibility,
            parent_id=parent_id
        )

        db.add(comment)
        db.flush()

        # Create mention records
        for user_id in mentions:
            mention = Mention(
                comment_id=comment.id,
                user_id=user_id
            )
            db.add(mention)

        # Update thread activity
        thread.last_activity_at = datetime.utcnow()
        thread.comments_count = thread.comments_count + 1

        # Add author as watcher if not already
        await self._add_watcher(db, thread_id, author_id)

        db.commit()

        # Emit audit event
        await audit_service.log_event(
            tenant_id=thread.tenant_id,
            event_type="collab.comment.created",
            actor_id=author_id,
            resource_type="comment",
            resource_id=str(comment.id),
            details={
                "thread_id": str(thread_id),
                "visibility": visibility,
                "mentions_count": len(mentions),
                "parent_id": str(parent_id) if parent_id else None
            }
        )

        # Send notifications to watchers
        await self._notify_watchers(db, thread, comment, mentions)

        return comment

    async def add_attachment(
        self,
        db: Session,
        comment_id: UUID,
        filename: str,
        mime_type: str,
        file_size: int,
        s3_bucket: str,
        s3_key: str,
        sha256_hash: str,
        upload_ip: str,
        uploaded_by: UUID
    ) -> Attachment:
        """Add file attachment to a comment"""

        # Validate file type and size
        if not self._is_allowed_file_type(mime_type):
            raise ValidationError(f"File type not allowed: {mime_type}")

        if file_size > settings.MAX_ATTACHMENT_SIZE:
            raise ValidationError(f"File too large: {file_size} bytes")

        # Create attachment
        attachment = Attachment(
            comment_id=comment_id,
            filename=filename,
            mime_type=mime_type,
            file_size=file_size,
            s3_bucket=s3_bucket,
            s3_key=s3_key,
            sha256_hash=sha256_hash,
            upload_ip=upload_ip,
            virus_scan_status="pending"
        )

        db.add(attachment)
        db.commit()

        # Queue virus scan
        await self._queue_virus_scan(attachment.id)

        # Emit audit event
        comment = db.query(Comment).filter(Comment.id == comment_id).first()
        if comment:
            await audit_service.log_event(
                tenant_id=comment.thread.tenant_id,
                event_type="collab.attachment.uploaded",
                actor_id=uploaded_by,
                resource_type="attachment",
                resource_id=str(attachment.id),
                details={
                    "comment_id": str(comment_id),
                    "filename": filename,
                    "file_size": file_size,
                    "mime_type": mime_type
                }
            )

        return attachment

    async def resolve_thread(
        self,
        db: Session,
        thread_id: UUID,
        resolved_by: UUID,
        status: str,
        reason: Optional[str] = None,
        requires_approval: bool = False
    ) -> Resolution:
        """Resolve a thread with optional 4-eyes approval"""

        # Get thread and validate access
        thread = db.query(CommentThread).filter(CommentThread.id == thread_id).first()
        if not thread:
            raise ValidationError("Thread not found")

        # Check if user has permission to resolve
        if not await self._can_resolve_thread(db, thread, resolved_by):
            raise PermissionError("Insufficient permissions to resolve thread")

        # Create resolution
        resolution = Resolution(
            thread_id=thread_id,
            status=status,
            reason=reason,
            resolved_by=resolved_by,
            requires_approval=requires_approval
        )

        if requires_approval:
            resolution.approval_requested_at = datetime.utcnow()
            # Don't update thread status yet - wait for approval
        else:
            resolution.approved_at = datetime.utcnow()
            resolution.approved_by = resolved_by
            # Update thread status immediately
            thread.status = status

        db.add(resolution)
        db.commit()

        # Emit audit event
        await audit_service.log_event(
            tenant_id=thread.tenant_id,
            event_type="collab.thread.resolution_requested" if requires_approval else "collab.thread.resolved",
            actor_id=resolved_by,
            resource_type="resolution",
            resource_id=str(resolution.id),
            details={
                "thread_id": str(thread_id),
                "status": status,
                "requires_approval": requires_approval,
                "reason": reason
            }
        )

        # Send notifications
        event_key = "collab.thread.resolution_requested" if requires_approval else "collab.thread.resolved"
        await notification_service.emit_event_simple(
            tenant_id=thread.tenant_id,
            event_key=event_key,
            event_data={
                "thread_id": str(thread_id),
                "resolution_id": str(resolution.id),
                "status": status,
                "resolved_by": str(resolved_by),
                "requires_approval": requires_approval
            },
            db=db
        )

        return resolution

    async def approve_resolution(
        self,
        db: Session,
        resolution_id: UUID,
        approved_by: UUID
    ) -> Resolution:
        """Approve a pending thread resolution"""

        resolution = db.query(Resolution).filter(Resolution.id == resolution_id).first()
        if not resolution:
            raise ValidationError("Resolution not found")

        if not resolution.requires_approval:
            raise ValidationError("Resolution does not require approval")

        if resolution.approved_at:
            raise ValidationError("Resolution already approved")

        # Check approval permissions
        thread = resolution.thread
        if not await self._can_approve_resolution(db, thread, approved_by):
            raise PermissionError("Insufficient permissions to approve resolution")

        # Approve resolution
        resolution.approved_by = approved_by
        resolution.approved_at = datetime.utcnow()

        # Update thread status
        thread.status = resolution.status

        db.commit()

        # Emit audit event
        await audit_service.log_event(
            tenant_id=thread.tenant_id,
            event_type="collab.thread.resolution_approved",
            actor_id=approved_by,
            resource_type="resolution",
            resource_id=str(resolution_id),
            details={
                "thread_id": str(thread.id),
                "original_requester": str(resolution.resolved_by),
                "status": resolution.status
            }
        )

        # Send notifications
        await notification_service.emit_event_simple(
            tenant_id=thread.tenant_id,
            event_key="collab.thread.resolution_approved",
            event_data={
                "thread_id": str(thread.id),
                "resolution_id": str(resolution_id),
                "approved_by": str(approved_by),
                "status": resolution.status
            },
            db=db
        )

        return resolution

    async def add_watcher(
        self,
        db: Session,
        thread_id: UUID,
        user_id: UUID
    ) -> Watch:
        """Add a user as a watcher to a thread"""
        return await self._add_watcher(db, thread_id, user_id)

    async def remove_watcher(
        self,
        db: Session,
        thread_id: UUID,
        user_id: UUID
    ) -> bool:
        """Remove a user as a watcher from a thread"""

        watch = db.query(Watch).filter(
            and_(Watch.thread_id == thread_id, Watch.user_id == user_id)
        ).first()

        if watch:
            db.delete(watch)

            # Update watchers count
            thread = db.query(CommentThread).filter(CommentThread.id == thread_id).first()
            if thread:
                thread.watchers_count = thread.watchers_count - 1

            db.commit()
            return True

        return False

    def _render_markdown(self, markdown_text: str) -> str:
        """Render markdown to safe HTML"""

        # Render markdown
        html = markdown.markdown(
            markdown_text,
            extensions=['extra', 'codehilite', 'nl2br']
        )

        # Sanitize HTML
        clean_html = bleach.clean(
            html,
            tags=self.allowed_html_tags,
            attributes=self.allowed_attributes,
            strip=True
        )

        return clean_html

    def _extract_mentions(self, text: str) -> List[UUID]:
        """Extract @mentions from text and return user IDs"""

        # Pattern to match @username or @user-id
        mention_pattern = r'@([a-zA-Z0-9_-]+|\[([^\]]+)\])'
        mentions = []

        for match in re.finditer(mention_pattern, text):
            mention_text = match.group(1) or match.group(2)

            # Try to parse as UUID first (for @[user-id] format)
            try:
                user_id = UUID(mention_text)
                mentions.append(user_id)
            except ValueError:
                # Could be username - would need user lookup service
                # For now, skip username mentions
                pass

        return list(set(mentions))  # Remove duplicates

    async def _add_watcher(
        self,
        db: Session,
        thread_id: UUID,
        user_id: UUID
    ) -> Watch:
        """Internal method to add a watcher"""

        # Check if already watching
        existing = db.query(Watch).filter(
            and_(Watch.thread_id == thread_id, Watch.user_id == user_id)
        ).first()

        if existing:
            return existing

        # Create watch
        watch = Watch(
            thread_id=thread_id,
            user_id=user_id
        )

        db.add(watch)

        # Update watchers count
        thread = db.query(CommentThread).filter(CommentThread.id == thread_id).first()
        if thread:
            thread.watchers_count = thread.watchers_count + 1

        return watch

    async def _notify_watchers(
        self,
        db: Session,
        thread: CommentThread,
        comment: Comment,
        mentions: List[UUID]
    ):
        """Send notifications to thread watchers and mentioned users"""

        # Get all watchers
        watchers = db.query(Watch).filter(Watch.thread_id == thread.id).all()

        # Notify watchers
        for watch in watchers:
            if watch.user_id != comment.author_id and watch.notify_comments:
                await notification_service.emit_event_simple(
                    tenant_id=thread.tenant_id,
                    event_key="collab.comment.created",
                    event_data={
                        "thread_id": str(thread.id),
                        "comment_id": str(comment.id),
                        "author_id": str(comment.author_id),
                        "recipient_id": str(watch.user_id),
                        "thread_title": thread.title
                    },
                    db=db
                )

        # Notify mentioned users (higher priority)
        for user_id in mentions:
            await notification_service.emit_event_simple(
                tenant_id=thread.tenant_id,
                event_key="collab.mention.created",
                event_data={
                    "thread_id": str(thread.id),
                    "comment_id": str(comment.id),
                    "author_id": str(comment.author_id),
                    "mentioned_user_id": str(user_id),
                    "thread_title": thread.title
                },
                db=db,
                severity=EventSeverity.WARNING
            )

    def _is_allowed_file_type(self, mime_type: str) -> bool:
        """Check if file type is allowed for attachments"""

        allowed_types = [
            'image/jpeg', 'image/png', 'image/gif', 'image/webp',
            'application/pdf',
            'text/plain', 'text/csv',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        ]

        return mime_type in allowed_types

    async def _queue_virus_scan(self, attachment_id: UUID):
        """Queue attachment for virus scanning"""

        # In production, this would queue a background job
        # For now, just mark as clean (placeholder)
        logger.info(f"Queuing virus scan for attachment {attachment_id}")

    async def _can_resolve_thread(
        self,
        db: Session,
        thread: CommentThread,
        user_id: UUID
    ) -> bool:
        """Check if user can resolve thread"""

        # For now, allow thread creator and bank officers to resolve
        # In production, this would check RBAC
        return True

    async def _can_approve_resolution(
        self,
        db: Session,
        thread: CommentThread,
        user_id: UUID
    ) -> bool:
        """Check if user can approve resolution"""

        # For now, allow bank officers and admins to approve
        # In production, this would check RBAC for 4-eyes approval
        return True


# Global service instance
collaboration_service = CollaborationService()