from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Numeric, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
import enum
from decimal import Decimal

from .base import Base


class UsageAction(str, enum.Enum):
    VALIDATE = "validate"           # Standard LC validation
    RECHECK = "recheck"            # Re-validation of existing LC
    EXPORT = "export"              # Export/download results
    BULK_UPLOAD = "bulk_upload"    # Bulk document processing
    DRAFT_IMPORT = "draft_import"  # Import draft LC
    IMPORT_BUNDLE = "import_bundle" # Import document bundle


class UsageRecord(Base):
    """
    Usage tracking model for billing calculations.
    Records every billable action with cost calculation at event time.
    """
    __tablename__ = "usage_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("validation_sessions.id"), nullable=True, index=True)  # Null for non-session actions

    # Usage details
    action = Column(String(50), nullable=False, index=True)  # Using String instead of Enum for flexibility
    units = Column(Integer, nullable=False, default=1)  # Usually 1, but could be bulk operations
    cost = Column(Numeric(10, 2), nullable=False)  # Cost calculated at event time in BDT

    # Context information
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    description = Column(String(500), nullable=True)  # Human-readable description

    # Metadata for detailed tracking
    event_metadata = Column(UUID, nullable=True)  # Additional context (document types, etc.)

    # Billing cycle tracking
    billed = Column(String(50), nullable=False, default=False)  # Whether this usage was included in an invoice
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=True, index=True)

    # Timestamps
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    company = relationship("Company", back_populates="usage_records")
    session = relationship("ValidationSession", back_populates="usage_records")
    user = relationship("User")
    invoice = relationship("Invoice")

    # Indexes for efficient querying
    __table_args__ = (
        Index("ix_usage_company_timestamp", "company_id", "timestamp"),
        Index("ix_usage_company_action", "company_id", "action"),
        Index("ix_usage_billing_cycle", "company_id", "billed", "timestamp"),
    )

    def __repr__(self):
        return f"<UsageRecord(id={self.id}, action={self.action}, cost={self.cost}, company_id={self.company_id})>"

    @property
    def cost_formatted(self) -> str:
        """Get formatted cost in BDT"""
        return f"{self.cost:,.2f} BDT"

    @property
    def is_billed(self) -> bool:
        """Check if this usage record has been billed"""
        return self.billed == True

    @property
    def is_recheckable(self) -> bool:
        """Check if this action can be rechecked (only validate actions)"""
        return self.action == UsageAction.VALIDATE.value

    def get_action_display(self) -> str:
        """Get human-readable action name"""
        action_names = {
            "validate": "LC Validation",
            "recheck": "LC Re-validation",
            "export": "Export Results",
            "bulk_upload": "Bulk Upload",
            "draft_import": "Draft Import",
            "import_bundle": "Import Bundle"
        }
        return action_names.get(self.action, self.action.title())

    def mark_as_billed(self, invoice_id: uuid.UUID):
        """Mark this usage record as billed"""
        self.billed = True
        self.invoice_id = invoice_id

    @staticmethod
    def create_usage_record(
        company_id: uuid.UUID,
        action: str,
        cost: Decimal,
        user_id: uuid.UUID = None,
        session_id: uuid.UUID = None,
        units: int = 1,
        description: str = None,
        metadata: dict = None
    ) -> 'UsageRecord':
        """Factory method to create a usage record"""
        return UsageRecord(
            company_id=company_id,
            session_id=session_id,
            action=action,
            units=units,
            cost=cost,
            user_id=user_id,
            description=description,
            metadata=metadata
        )