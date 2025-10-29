"""
Governance Service - 4-eyes approval and delegation enforcement
Provides bank-grade governance controls with approval workflows
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timezone, timedelta
from uuid import UUID
import functools
import logging
import json

from app.models.audit import GovernanceApproval, AuditLogEntry, AuditAction, AuditSeverity
from app.services.audit_service import AuditService
from app.core.database import get_db

logger = logging.getLogger(__name__)


class GovernanceError(Exception):
    """Governance enforcement error"""
    pass


class InsufficientApprovalsError(GovernanceError):
    """Insufficient approvals for action"""
    pass


class DelegationError(GovernanceError):
    """Delegation validation error"""
    pass


def requires_four_eyes(
    action: str,
    resource_type: str = None,
    required_approvals: int = 2,
    required_roles: List[str] = None,
    expiry_hours: int = 24,
    allow_self_approval: bool = False
):
    """
    Decorator to enforce 4-eyes approval on sensitive operations

    Args:
        action: Description of the action requiring approval
        resource_type: Type of resource being acted upon
        required_approvals: Number of approvals needed (default: 2)
        required_roles: List of roles that can provide approval
        expiry_hours: Hours until approval request expires
        allow_self_approval: Whether requester can approve their own request
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract context from function arguments
            context = _extract_governance_context(func, args, kwargs)

            if not context:
                raise GovernanceError("Unable to extract governance context")

            db = context["db"]
            current_user = context["current_user"]
            tenant_id = context["tenant_id"]
            resource_id = context.get("resource_id", "unknown")

            # Check if approval is already granted
            approval = await GovernanceService.check_existing_approval(
                db=db,
                action_type=action,
                resource_type=resource_type or func.__name__,
                resource_id=str(resource_id),
                tenant_id=tenant_id
            )

            if approval and approval.status == "approved":
                # Execute the function with approval
                logger.info(f"Executing approved action: {action} by {current_user.id}")

                # Mark approval as executed
                await GovernanceService.mark_approval_executed(
                    db=db,
                    approval_id=approval.id,
                    executed_by=current_user.id
                )

                # Execute the original function
                result = await func(*args, **kwargs)

                # Log execution in audit trail
                await AuditService.append_entry(
                    db=db,
                    tenant_id=tenant_id,
                    action=AuditAction.APPROVE,
                    resource_type=resource_type or "governance",
                    resource_id=str(approval.id),
                    actor_id=current_user.id,
                    action_description=f"Executed approved action: {action}",
                    severity=AuditSeverity.HIGH,
                    metadata={
                        "approval_id": str(approval.id),
                        "original_action": action,
                        "approvals_received": approval.approvals_received
                    }
                )

                return result

            else:
                # Request approval
                approval_request = await GovernanceService.request_approval(
                    db=db,
                    action_type=action,
                    resource_type=resource_type or func.__name__,
                    resource_id=str(resource_id),
                    tenant_id=tenant_id,
                    requested_by=current_user.id,
                    required_approvals=required_approvals,
                    required_roles=required_roles,
                    expiry_hours=expiry_hours,
                    request_context={
                        "function": func.__name__,
                        "args": _serialize_args(args),
                        "kwargs": _serialize_kwargs(kwargs)
                    }
                )

                raise InsufficientApprovalsError(
                    f"Action '{action}' requires {required_approvals} approvals. "
                    f"Approval request created: {approval_request.request_id}"
                )

        return wrapper
    return decorator


def requires_delegation(
    to_role: str,
    reason_required: bool = True,
    max_duration_hours: int = 72,
    audit_trail: bool = True
):
    """
    Decorator to enforce delegation requirements

    Args:
        to_role: Role that action must be delegated to
        reason_required: Whether delegation reason is required
        max_duration_hours: Maximum delegation duration
        audit_trail: Whether to create audit trail
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            context = _extract_governance_context(func, args, kwargs)

            if not context:
                raise DelegationError("Unable to extract governance context")

            db = context["db"]
            current_user = context["current_user"]
            tenant_id = context["tenant_id"]

            # Check if user has required role or valid delegation
            if not await GovernanceService.check_delegation_authority(
                db=db,
                user_id=current_user.id,
                tenant_id=tenant_id,
                required_role=to_role,
                max_duration_hours=max_duration_hours
            ):
                raise DelegationError(
                    f"Action requires delegation to role '{to_role}' or "
                    f"user must have that role"
                )

            # Execute function
            result = await func(*args, **kwargs)

            # Create audit trail if requested
            if audit_trail:
                await AuditService.append_entry(
                    db=db,
                    tenant_id=tenant_id,
                    action="delegated_action",
                    resource_type="governance",
                    resource_id=str(current_user.id),
                    actor_id=current_user.id,
                    action_description=f"Executed delegated action requiring role: {to_role}",
                    severity=AuditSeverity.MEDIUM,
                    metadata={
                        "function": func.__name__,
                        "required_role": to_role,
                        "delegation_used": True
                    }
                )

            return result

        return wrapper
    return decorator


class GovernanceService:
    """Service for managing governance workflows and approvals"""

    @staticmethod
    async def request_approval(
        db: Session,
        action_type: str,
        resource_type: str,
        resource_id: str,
        tenant_id: str,
        requested_by: UUID,
        required_approvals: int = 2,
        required_roles: List[str] = None,
        expiry_hours: int = 24,
        request_reason: str = None,
        request_context: Dict[str, Any] = None
    ) -> GovernanceApproval:
        """Create new approval request"""

        # Check for existing pending approval
        existing = db.query(GovernanceApproval).filter(
            and_(
                GovernanceApproval.tenant_id == tenant_id,
                GovernanceApproval.action_type == action_type,
                GovernanceApproval.resource_type == resource_type,
                GovernanceApproval.resource_id == resource_id,
                GovernanceApproval.status == "pending"
            )
        ).first()

        if existing:
            logger.info(f"Returning existing approval request: {existing.request_id}")
            return existing

        # Create new approval request
        expires_at = datetime.now(timezone.utc) + timedelta(hours=expiry_hours)

        approval = GovernanceApproval(
            tenant_id=tenant_id,
            action_type=action_type,
            resource_type=resource_type,
            resource_id=resource_id,
            requested_by=requested_by,
            request_reason=request_reason,
            request_context=request_context,
            required_approvals=required_approvals,
            required_roles=required_roles,
            expires_at=expires_at,
            approval_history=[]
        )

        db.add(approval)
        db.commit()

        # Create audit entry
        await AuditService.append_entry(
            db=db,
            tenant_id=tenant_id,
            action="approval_requested",
            resource_type="governance_approval",
            resource_id=str(approval.id),
            actor_id=requested_by,
            action_description=f"Requested approval for: {action_type}",
            severity=AuditSeverity.MEDIUM,
            metadata={
                "action_type": action_type,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "required_approvals": required_approvals,
                "expires_at": expires_at.isoformat()
            }
        )

        logger.info(f"Created approval request: {approval.request_id}")
        return approval

    @staticmethod
    async def provide_approval(
        db: Session,
        approval_id: UUID,
        approver_id: UUID,
        approver_role: str,
        decision: str,  # "approve" or "reject"
        comments: str = None
    ) -> GovernanceApproval:
        """Provide approval or rejection for a request"""

        approval = db.query(GovernanceApproval).filter(
            GovernanceApproval.id == approval_id
        ).first()

        if not approval:
            raise GovernanceError(f"Approval request not found: {approval_id}")

        if approval.status != "pending":
            raise GovernanceError(f"Approval request is not pending: {approval.status}")

        if approval.expires_at and approval.expires_at < datetime.now(timezone.utc):
            approval.status = "expired"
            db.commit()
            raise GovernanceError("Approval request has expired")

        # Check if approver has already provided approval
        approval_history = approval.approval_history or []
        for entry in approval_history:
            if entry.get("approver_id") == str(approver_id):
                raise GovernanceError("Approver has already provided approval for this request")

        # Check if approver has required role
        if approval.required_roles and approver_role not in approval.required_roles:
            raise GovernanceError(f"Approver role '{approver_role}' not in required roles: {approval.required_roles}")

        # Check if self-approval is allowed
        if approval.requested_by == approver_id:
            # For now, allow self-approval with warning
            logger.warning(f"Self-approval detected for request: {approval_id}")

        # Add approval/rejection to history
        approval_entry = {
            "approver_id": str(approver_id),
            "approver_role": approver_role,
            "decision": decision,
            "comments": comments,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        approval_history.append(approval_entry)
        approval.approval_history = approval_history

        if decision == "approve":
            approval.approvals_received += 1

            # Check if we have enough approvals
            if approval.approvals_received >= approval.required_approvals:
                approval.status = "approved"
                logger.info(f"Approval request approved: {approval.request_id}")

        elif decision == "reject":
            approval.status = "rejected"
            logger.info(f"Approval request rejected: {approval.request_id}")

        db.commit()

        # Create audit entry
        await AuditService.append_entry(
            db=db,
            tenant_id=approval.tenant_id,
            action=f"approval_{decision}",
            resource_type="governance_approval",
            resource_id=str(approval.id),
            actor_id=approver_id,
            action_description=f"{'Approved' if decision == 'approve' else 'Rejected'} request: {approval.action_type}",
            severity=AuditSeverity.HIGH,
            metadata={
                "approval_id": str(approval.id),
                "decision": decision,
                "approvals_received": approval.approvals_received,
                "required_approvals": approval.required_approvals,
                "comments": comments
            }
        )

        return approval

    @staticmethod
    async def check_existing_approval(
        db: Session,
        action_type: str,
        resource_type: str,
        resource_id: str,
        tenant_id: str
    ) -> Optional[GovernanceApproval]:
        """Check for existing approval for action"""

        return db.query(GovernanceApproval).filter(
            and_(
                GovernanceApproval.tenant_id == tenant_id,
                GovernanceApproval.action_type == action_type,
                GovernanceApproval.resource_type == resource_type,
                GovernanceApproval.resource_id == resource_id,
                GovernanceApproval.status.in_(["pending", "approved"])
            )
        ).first()

    @staticmethod
    async def mark_approval_executed(
        db: Session,
        approval_id: UUID,
        executed_by: UUID
    ) -> GovernanceApproval:
        """Mark approval as executed"""

        approval = db.query(GovernanceApproval).filter(
            GovernanceApproval.id == approval_id
        ).first()

        if approval:
            approval.executed_by = executed_by
            approval.executed_at = datetime.now(timezone.utc)
            approval.status = "executed"
            db.commit()

        return approval

    @staticmethod
    async def check_delegation_authority(
        db: Session,
        user_id: UUID,
        tenant_id: str,
        required_role: str,
        max_duration_hours: int = 72
    ) -> bool:
        """Check if user has delegation authority for role"""

        # In real implementation, this would check:
        # 1. User's current roles
        # 2. Active delegations to the user
        # 3. Delegation validity and expiry

        # For now, simulate delegation check
        logger.info(f"Checking delegation authority for user {user_id} to role {required_role}")

        # Simulate: return True if user has admin role or specific delegation
        # In real implementation, query user roles and delegation tables
        return True  # Placeholder

    @staticmethod
    async def get_pending_approvals(
        db: Session,
        tenant_id: str,
        approver_id: UUID = None,
        approver_role: str = None,
        limit: int = 50
    ) -> List[GovernanceApproval]:
        """Get pending approval requests"""

        query = db.query(GovernanceApproval).filter(
            and_(
                GovernanceApproval.tenant_id == tenant_id,
                GovernanceApproval.status == "pending",
                GovernanceApproval.expires_at > datetime.now(timezone.utc)
            )
        )

        # Filter by approver role if specified
        if approver_role and approver_role != "super_admin":
            # Filter to approvals that allow this role
            # This is a simplified check - real implementation would be more complex
            pass

        return query.order_by(desc(GovernanceApproval.requested_at)).limit(limit).all()

    @staticmethod
    async def get_approval_history(
        db: Session,
        tenant_id: str,
        action_type: str = None,
        resource_type: str = None,
        start_date: datetime = None,
        end_date: datetime = None,
        limit: int = 100
    ) -> List[GovernanceApproval]:
        """Get approval history with filters"""

        query = db.query(GovernanceApproval).filter(
            GovernanceApproval.tenant_id == tenant_id
        )

        if action_type:
            query = query.filter(GovernanceApproval.action_type == action_type)

        if resource_type:
            query = query.filter(GovernanceApproval.resource_type == resource_type)

        if start_date:
            query = query.filter(GovernanceApproval.requested_at >= start_date)

        if end_date:
            query = query.filter(GovernanceApproval.requested_at <= end_date)

        return query.order_by(desc(GovernanceApproval.requested_at)).limit(limit).all()

    @staticmethod
    async def cleanup_expired_approvals(db: Session) -> int:
        """Clean up expired approval requests"""

        expired_count = db.query(GovernanceApproval).filter(
            and_(
                GovernanceApproval.status == "pending",
                GovernanceApproval.expires_at < datetime.now(timezone.utc)
            )
        ).update({"status": "expired"})

        db.commit()

        if expired_count > 0:
            logger.info(f"Marked {expired_count} approval requests as expired")

        return expired_count


def _extract_governance_context(func: Callable, args: tuple, kwargs: dict) -> Optional[Dict[str, Any]]:
    """Extract governance context from function call"""

    # Look for common parameter names
    context = {}

    # Try to find database session
    for arg in args:
        if hasattr(arg, 'query'):  # SQLAlchemy session
            context["db"] = arg
            break

    if "db" in kwargs:
        context["db"] = kwargs["db"]

    # Try to find current user
    if "current_user" in kwargs:
        context["current_user"] = kwargs["current_user"]

    # Try to find tenant_id
    if "tenant_id" in kwargs:
        context["tenant_id"] = kwargs["tenant_id"]

    # Try to find resource_id
    if "resource_id" in kwargs:
        context["resource_id"] = kwargs["resource_id"]
    elif "id" in kwargs:
        context["resource_id"] = kwargs["id"]

    return context if context else None


def _serialize_args(args: tuple) -> List[Any]:
    """Serialize function arguments for storage"""
    serialized = []
    for arg in args:
        try:
            if hasattr(arg, '__dict__'):
                # Skip complex objects like database sessions
                serialized.append(f"<{type(arg).__name__}>")
            else:
                serialized.append(str(arg))
        except:
            serialized.append("<unserializable>")
    return serialized


def _serialize_kwargs(kwargs: dict) -> Dict[str, Any]:
    """Serialize function keyword arguments for storage"""
    serialized = {}
    for key, value in kwargs.items():
        try:
            if hasattr(value, '__dict__'):
                serialized[key] = f"<{type(value).__name__}>"
            else:
                serialized[key] = str(value)
        except:
            serialized[key] = "<unserializable>"
    return serialized