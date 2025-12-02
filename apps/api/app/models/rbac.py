"""
RBAC Models - Role-Based Access Control for company members and invitations

This module defines:
- MemberRole: Enum for member roles (owner, admin, member, viewer)
- MemberStatus: Enum for member status (active, pending, suspended, removed)
- InvitationStatus: Enum for invitation status
- CompanyMember: Links users to companies with roles
- CompanyInvitation: Tracks pending invitations
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional
from uuid import UUID
import secrets

from sqlalchemy import (
    Column, String, DateTime, ForeignKey, Text, CheckConstraint, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class MemberRole(str, Enum):
    """Roles for company members"""
    OWNER = "owner"      # Full access, can delete company, transfer ownership
    ADMIN = "admin"      # Can manage members, access all tools, view billing
    MEMBER = "member"    # Can use assigned tools, view own usage
    VIEWER = "viewer"    # Read-only access to results/reports


class MemberStatus(str, Enum):
    """Status for company members"""
    ACTIVE = "active"
    PENDING = "pending"
    SUSPENDED = "suspended"
    REMOVED = "removed"


class InvitationStatus(str, Enum):
    """Status for company invitations"""
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


# Default tool access by role
DEFAULT_TOOL_ACCESS = {
    MemberRole.OWNER: ["lcopilot", "price_verify", "hscode", "sanctions", "container_track"],
    MemberRole.ADMIN: ["lcopilot", "price_verify", "hscode", "sanctions", "container_track"],
    MemberRole.MEMBER: ["lcopilot", "price_verify"],  # Can be customized
    MemberRole.VIEWER: [],  # View-only, no tool execution
}


class CompanyMember(Base):
    """
    Links users to companies with specific roles and tool access.
    
    Each user can belong to one company with one role.
    Tool access can be customized per member.
    """
    __tablename__ = "company_members"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    company_id = Column(PGUUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False, default=MemberRole.MEMBER.value)
    tool_access = Column(JSONB, nullable=False, default=list)
    invited_by = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    invited_at = Column(DateTime(timezone=True), nullable=True)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String(20), nullable=False, default=MemberStatus.ACTIVE.value)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    company = relationship("Company", back_populates="members", foreign_keys=[company_id])
    user = relationship("User", back_populates="company_membership", foreign_keys=[user_id])
    inviter = relationship("User", foreign_keys=[invited_by])
    
    __table_args__ = (
        CheckConstraint("role IN ('owner', 'admin', 'member', 'viewer')", name="valid_member_role"),
        CheckConstraint("status IN ('active', 'pending', 'suspended', 'removed')", name="valid_member_status"),
        UniqueConstraint("company_id", "user_id", name="unique_company_user"),
    )
    
    @property
    def is_owner(self) -> bool:
        return self.role == MemberRole.OWNER.value
    
    @property
    def is_admin(self) -> bool:
        return self.role in [MemberRole.OWNER.value, MemberRole.ADMIN.value]
    
    @property
    def can_manage_team(self) -> bool:
        """Can invite/remove members"""
        return self.role in [MemberRole.OWNER.value, MemberRole.ADMIN.value]
    
    @property
    def can_view_billing(self) -> bool:
        """Can view billing information"""
        return self.role in [MemberRole.OWNER.value, MemberRole.ADMIN.value]
    
    @property
    def can_manage_billing(self) -> bool:
        """Can change billing/payment settings"""
        return self.role == MemberRole.OWNER.value
    
    def can_access_tool(self, tool_id: str) -> bool:
        """Check if member can access a specific tool"""
        if self.role == MemberRole.OWNER.value:
            return True  # Owner has access to all tools
        return tool_id in (self.tool_access or [])
    
    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "company_id": str(self.company_id),
            "user_id": str(self.user_id),
            "role": self.role,
            "tool_access": self.tool_access or [],
            "invited_by": str(self.invited_by) if self.invited_by else None,
            "invited_at": self.invited_at.isoformat() if self.invited_at else None,
            "joined_at": self.joined_at.isoformat() if self.joined_at else None,
            "status": self.status,
            "is_owner": self.is_owner,
            "is_admin": self.is_admin,
            "can_manage_team": self.can_manage_team,
            "can_view_billing": self.can_view_billing,
            "can_manage_billing": self.can_manage_billing,
        }


class CompanyInvitation(Base):
    """
    Tracks pending invitations to join a company.
    
    Invitations expire after a set period and can be cancelled.
    When accepted, a CompanyMember record is created.
    """
    __tablename__ = "company_invitations"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    company_id = Column(PGUUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    email = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default=MemberRole.MEMBER.value)
    tool_access = Column(JSONB, nullable=False, default=list)
    invited_by = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    token = Column(String(255), nullable=False, unique=True)
    message = Column(Text, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), nullable=False, default=InvitationStatus.PENDING.value)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    company = relationship("Company", back_populates="invitations")
    inviter = relationship("User", foreign_keys=[invited_by])
    
    __table_args__ = (
        CheckConstraint("role IN ('admin', 'member', 'viewer')", name="valid_invitation_role"),
        CheckConstraint("status IN ('pending', 'accepted', 'expired', 'cancelled')", name="valid_invitation_status"),
    )
    
    @property
    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at if self.expires_at else False
    
    @property
    def is_valid(self) -> bool:
        return self.status == InvitationStatus.PENDING.value and not self.is_expired
    
    @classmethod
    def generate_token(cls) -> str:
        """Generate a secure random token for invitation links"""
        return secrets.token_urlsafe(32)
    
    @classmethod
    def default_expiry(cls, days: int = 7) -> datetime:
        """Get default expiry date (7 days from now)"""
        return datetime.utcnow() + timedelta(days=days)
    
    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "company_id": str(self.company_id),
            "email": self.email,
            "role": self.role,
            "tool_access": self.tool_access or [],
            "invited_by": str(self.invited_by) if self.invited_by else None,
            "message": self.message,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "accepted_at": self.accepted_at.isoformat() if self.accepted_at else None,
            "status": self.status,
            "is_expired": self.is_expired,
            "is_valid": self.is_valid,
        }


# Permission helper functions
def get_role_permissions(role: str) -> dict:
    """Get all permissions for a given role"""
    permissions = {
        MemberRole.OWNER.value: {
            "manage_team": True,
            "remove_members": True,
            "transfer_ownership": True,
            "view_billing": True,
            "manage_billing": True,
            "view_usage": True,
            "view_org_usage": True,
            "access_all_tools": True,
            "admin_panels": True,
            "api_access": True,
        },
        MemberRole.ADMIN.value: {
            "manage_team": True,
            "remove_members": True,  # Except owner
            "transfer_ownership": False,
            "view_billing": True,
            "manage_billing": False,
            "view_usage": True,
            "view_org_usage": True,
            "access_all_tools": True,
            "admin_panels": True,
            "api_access": True,
        },
        MemberRole.MEMBER.value: {
            "manage_team": False,
            "remove_members": False,
            "transfer_ownership": False,
            "view_billing": False,
            "manage_billing": False,
            "view_usage": True,  # Own usage only
            "view_org_usage": False,
            "access_all_tools": False,  # Only assigned tools
            "admin_panels": False,
            "api_access": False,
        },
        MemberRole.VIEWER.value: {
            "manage_team": False,
            "remove_members": False,
            "transfer_ownership": False,
            "view_billing": False,
            "manage_billing": False,
            "view_usage": True,  # View reports only
            "view_org_usage": False,
            "access_all_tools": False,
            "admin_panels": False,
            "api_access": False,
        },
    }
    return permissions.get(role, permissions[MemberRole.VIEWER.value])

