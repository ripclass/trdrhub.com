"""Role-based access control helper — Phase A10.

Sits on top of the existing CompanyMember + MemberRole shape. Adds a
permission layer so endpoints can declare what *capability* they
need rather than re-implementing role checks ad-hoc:

    >>> require_permission(current_user, db, Permission.RESOLVE_DISCREPANCY)

Plain MEMBER users can validate + comment but can't resolve. ADMIN
or OWNER can resolve, waive, send re-paper, generate invoices,
change settings. VIEWER is read-only — every mutation permission
denied.

This is deliberately a small step toward the four-role model the
plan calls for (viewer / validator / approver / admin). The
existing OWNER/ADMIN/MEMBER/VIEWER enum is preserved; no migration
needed for v1. A later iteration can split MEMBER into
"validator" + "approver" if the binary distinction becomes too
coarse for customers.
"""

from __future__ import annotations

import enum
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..models import User
from ..models.rbac import CompanyMember, MemberRole, MemberStatus


class Permission(str, enum.Enum):
    """Capabilities the RBAC layer recognises. Every gated endpoint
    declares the permission it needs; the role→permission map below
    is the only thing that decides who can do what."""

    # Validation surface
    RUN_VALIDATION = "run_validation"
    RUN_BULK = "run_bulk"

    # Discrepancy workflow
    COMMENT_DISCREPANCY = "comment_discrepancy"
    RESOLVE_DISCREPANCY = "resolve_discrepancy"
    SEND_REPAPER = "send_repaper"

    # Services / billing
    GENERATE_INVOICE = "generate_invoice"

    # Settings / membership
    MANAGE_MEMBERS = "manage_members"
    CHANGE_SETTINGS = "change_settings"

    # Cross-cutting
    VIEW_AUDIT_LOG = "view_audit_log"


_ROLE_PERMISSIONS: dict[str, frozenset[Permission]] = {
    MemberRole.OWNER.value: frozenset(Permission),  # everything
    MemberRole.ADMIN.value: frozenset(
        {
            Permission.RUN_VALIDATION,
            Permission.RUN_BULK,
            Permission.COMMENT_DISCREPANCY,
            Permission.RESOLVE_DISCREPANCY,
            Permission.SEND_REPAPER,
            Permission.GENERATE_INVOICE,
            Permission.MANAGE_MEMBERS,
            Permission.CHANGE_SETTINGS,
            Permission.VIEW_AUDIT_LOG,
        }
    ),
    MemberRole.MEMBER.value: frozenset(
        {
            Permission.RUN_VALIDATION,
            Permission.RUN_BULK,
            Permission.COMMENT_DISCREPANCY,
            Permission.SEND_REPAPER,  # member can ask supplier to fix; admin/owner approves
        }
    ),
    MemberRole.VIEWER.value: frozenset(),
}


def _user_role(db: Session, user: User) -> Optional[str]:
    """Look up the user's effective role on their company. Falls back
    to ``user.role`` (legacy User.role string) if no CompanyMember
    row exists, then to None."""
    if user is None:
        return None
    if getattr(user, "company_id", None):
        member = (
            db.query(CompanyMember)
            .filter(CompanyMember.user_id == user.id)
            .filter(CompanyMember.company_id == user.company_id)
            .filter(CompanyMember.status == MemberStatus.ACTIVE.value)
            .first()
        )
        if member is not None:
            return (member.role or "").lower()
    legacy = (getattr(user, "role", None) or "").lower()
    return legacy or None


def has_permission(db: Session, user: User, permission: Permission) -> bool:
    role = _user_role(db, user)
    if role is None:
        return False
    perms = _ROLE_PERMISSIONS.get(role, frozenset())
    return permission in perms


def require_permission(db: Session, user: User, permission: Permission) -> None:
    """Raise 403 if the user lacks ``permission`` on their company.
    Endpoints call this in the request body."""
    if not has_permission(db, user, permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "permission_denied",
                "message": f"This action requires the '{permission.value}' permission.",
                "required_permission": permission.value,
            },
        )


def get_user_role(db: Session, user: User) -> Optional[str]:
    """Public version of ``_user_role`` for endpoints that want to
    surface the role to the frontend (e.g. /me payload)."""
    return _user_role(db, user)


__all__ = [
    "Permission",
    "get_user_role",
    "has_permission",
    "require_permission",
]
