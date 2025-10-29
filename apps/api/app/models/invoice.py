from sqlalchemy import Column, String, Integer, Date, DateTime, Enum, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
import enum
from decimal import Decimal

from .base import Base


class InvoiceStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class Currency(str, enum.Enum):
    BDT = "BDT"
    USD = "USD"


class Invoice(Base):
    """
    Invoice model for tracking billing cycles and payments.
    Generated monthly for subscriptions or per-check for pay-per-use.
    """
    __tablename__ = "invoices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)

    # Invoice details
    invoice_number = Column(String(50), unique=True, nullable=False, index=True)
    amount = Column(Numeric(10, 2), nullable=False)  # Total amount
    currency = Column(Enum(Currency), nullable=False, default=Currency.BDT)

    # Billing period (null for pay-per-check)
    period_start = Column(Date, nullable=True)
    period_end = Column(Date, nullable=True)

    # Payment tracking
    status = Column(Enum(InvoiceStatus), nullable=False, default=InvoiceStatus.PENDING)
    payment_txn_id = Column(String(255), nullable=True, index=True)  # External payment provider transaction ID
    payment_method = Column(String(100), nullable=True)  # credit_card, bank_transfer, etc.

    # Invoice metadata
    event_metadata = Column(JSONB, nullable=True)  # Line items, notes, tax details
    description = Column(String(500), nullable=True)

    # Due date and payment tracking
    due_date = Column(Date, nullable=True)
    paid_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    company = relationship("Company", back_populates="invoices")

    def __repr__(self):
        return f"<Invoice(id={self.id}, number={self.invoice_number}, amount={self.amount} {self.currency}, status={self.status})>"

    @property
    def is_paid(self) -> bool:
        """Check if invoice is paid"""
        return self.status == InvoiceStatus.PAID

    @property
    def is_overdue(self) -> bool:
        """Check if invoice is overdue"""
        if not self.due_date or self.is_paid:
            return False
        return datetime.utcnow().date() > self.due_date

    @property
    def amount_formatted(self) -> str:
        """Get formatted amount with currency"""
        return f"{self.amount:,.2f} {self.currency}"

    def get_line_items(self) -> list:
        """Get invoice line items from metadata"""
        if not self.metadata:
            return []
        return self.metadata.get("line_items", [])

    def add_line_item(self, description: str, quantity: int, unit_price: Decimal, total: Decimal):
        """Add a line item to the invoice"""
        if not self.metadata:
            self.metadata = {}
        if "line_items" not in self.metadata:
            self.metadata["line_items"] = []

        line_item = {
            "description": description,
            "quantity": quantity,
            "unit_price": float(unit_price),
            "total": float(total)
        }
        self.metadata["line_items"].append(line_item)

    def calculate_subtotal(self) -> Decimal:
        """Calculate subtotal from line items"""
        line_items = self.get_line_items()
        return sum(Decimal(str(item["total"])) for item in line_items)

    def get_tax_amount(self) -> Decimal:
        """Get tax amount from metadata"""
        if not self.metadata:
            return Decimal("0")
        return Decimal(str(self.metadata.get("tax_amount", "0")))

    def set_tax_amount(self, tax_amount: Decimal):
        """Set tax amount in metadata"""
        if not self.metadata:
            self.metadata = {}
        self.metadata["tax_amount"] = float(tax_amount)

    def mark_as_paid(self, transaction_id: str, payment_method: str = None):
        """Mark invoice as paid with transaction details"""
        self.status = InvoiceStatus.PAID
        self.payment_txn_id = transaction_id
        if payment_method:
            self.payment_method = payment_method
        self.paid_at = datetime.utcnow()

    def mark_as_failed(self, reason: str = None):
        """Mark invoice as failed with optional reason"""
        self.status = InvoiceStatus.FAILED
        if reason:
            if not self.metadata:
                self.metadata = {}
            self.metadata["failure_reason"] = reason

    @staticmethod
    def generate_invoice_number(company_id: str) -> str:
        """Generate unique invoice number"""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        company_short = str(company_id)[:8].upper()
        return f"INV-{company_short}-{timestamp}"