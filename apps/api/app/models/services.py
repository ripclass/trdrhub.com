"""Services persona models — Phase A8.

Mirrors the agency persona shape (commit 7b487a4d) but for the
services consultant: a freight forwarder / customs broker / LC
consultant who runs LCs on behalf of clients and bills time.

Two new tables:
  * ``services_clients`` — the consultant's roster of clients.
  * ``time_entries`` — billable + non-billable time logged by the
    consultant against a client (and optionally a specific LC).

Plus a nullable ``services_client_id`` FK on ``validation_session``
so an LC can be attributed to a client (parallel to ``supplier_id``
for the agency persona).
"""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class ServicesClient(Base):
    """A consultant's client — the company whose LCs they manage."""

    __tablename__ = "services_clients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    services_company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name = Column(String(255), nullable=False)
    country = Column(String(2), nullable=True)
    contact_name = Column(String(255), nullable=True)
    contact_email = Column(String(320), nullable=True)
    contact_phone = Column(String(64), nullable=True)
    notes = Column(Text, nullable=True)

    # Billing terms — used by the invoice generator in Phase A9.
    # Hourly rate is in the company's reporting currency (no separate
    # currency column for v1; consultants typically settle in USD).
    billing_rate = Column(Numeric(10, 2), nullable=True)
    retainer_active = Column(Boolean, nullable=False, default=False, server_default="false")
    retainer_hours_per_month = Column(Numeric(6, 2), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    time_entries = relationship(
        "TimeEntry",
        back_populates="client",
        foreign_keys="TimeEntry.services_client_id",
    )

    __table_args__ = (
        Index(
            "ix_services_clients_company_name",
            "services_company_id",
            "name",
        ),
    )


class TimeEntry(Base):
    """One unit of logged time. Optionally attributed to a specific LC."""

    __tablename__ = "time_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    services_company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    services_client_id = Column(
        UUID(as_uuid=True),
        ForeignKey("services_clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    validation_session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("validation_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    hours = Column(Numeric(6, 2), nullable=False)
    description = Column(Text, nullable=True)
    billable = Column(Boolean, nullable=False, default=True, server_default="true")
    billed = Column(Boolean, nullable=False, default=False, server_default="false")

    # When the work was actually performed (not when the row was written).
    # Defaults to created_at via the service layer when not supplied.
    performed_on = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    client = relationship(
        "ServicesClient",
        back_populates="time_entries",
        foreign_keys=[services_client_id],
    )

    __table_args__ = (
        Index(
            "ix_time_entries_client_performed",
            "services_client_id",
            "performed_on",
        ),
    )


__all__ = ["ServicesClient", "TimeEntry"]
