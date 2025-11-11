"""
Bank Organization Models
Hierarchical org units (group → region → branch) within a bank for multi-org switching
"""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, List

from sqlalchemy import (
    Column,
    String,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models import Base


class OrgKind(str, Enum):
    """Organization unit kind"""
    GROUP = "group"
    REGION = "region"
    BRANCH = "branch"


class OrgAccessRole(str, Enum):
    """User role within an org unit"""
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class BankOrg(Base):
    """Hierarchical organization unit within a bank"""
    __tablename__ = "bank_orgs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bank_company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("bank_orgs.id", ondelete="CASCADE"), nullable=True, index=True)
    
    # Org metadata
    kind = Column(String(50), nullable=False, index=True)  # 'group', 'region', 'branch'
    name = Column(String(255), nullable=False)
    code = Column(String(50), nullable=True)  # Short code like 'APAC', 'NYC-001'
    path = Column(String(500), nullable=False, index=True)  # Materialized path like '/1/2/3'
    
    # Hierarchy metadata
    level = Column(Integer, nullable=False, default=0)  # Depth in tree
    sort_order = Column(Integer, nullable=False, default=0)
    
    # Status
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    bank_company = relationship("Company", foreign_keys=[bank_company_id])
    parent = relationship("BankOrg", remote_side=[id], backref="children")
    user_access = relationship("UserOrgAccess", back_populates="org", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('ix_bank_orgs_bank_company_id', 'bank_company_id'),
        UniqueConstraint('bank_company_id', 'code', name='uq_bank_orgs_bank_code'),
    )


class UserOrgAccess(Base):
    """User access to organization units"""
    __tablename__ = "user_org_access"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    org_id = Column(UUID(as_uuid=True), ForeignKey("bank_orgs.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Access role within this org
    role = Column(String(50), nullable=False, default=OrgAccessRole.MEMBER.value)  # 'admin', 'member', 'viewer'
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    granted_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    org = relationship("BankOrg", back_populates="user_access")
    granter = relationship("User", foreign_keys=[granted_by])
    
    __table_args__ = (
        Index('ix_user_org_access_user_id', 'user_id'),
        Index('ix_user_org_access_org_id', 'org_id'),
        UniqueConstraint('user_id', 'org_id', name='uq_user_org_access_user_org'),
    )

