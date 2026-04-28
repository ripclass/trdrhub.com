"""Agency persona models — Phase A5.

A sourcing / buying agent runs LCs on behalf of foreign buyers
across N domestic suppliers. Two records track the actors at the
edges of that triangle:

  * ``Supplier`` — a domestic factory the agent sources from.
  * ``ForeignBuyer`` — the international counterparty the LC is
    issued for. One agent typically has many suppliers and many
    foreign buyers; an LC ties one of each together.

Both belong to a single ``Company`` (the agent's company) — agents
don't share supplier rosters. Phase A6 wires the agent's validation
flows; this phase just ships the rosters + portfolio aggregation.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class Supplier(Base):
    """A domestic factory / exporter the agent's company manages."""

    __tablename__ = "agency_suppliers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name = Column(String(255), nullable=False)
    country = Column(String(2), nullable=True)  # ISO 3166-1 alpha-2

    # Operational details surface on the supplier detail page.
    factory_address = Column(Text, nullable=True)
    contact_name = Column(String(255), nullable=True)
    contact_email = Column(String(320), nullable=True)
    contact_phone = Column(String(64), nullable=True)
    notes = Column(Text, nullable=True)

    # Optional default foreign buyer — most suppliers ship to one
    # primary international counterparty. The default flows into the
    # validation form pre-fill.
    foreign_buyer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agency_foreign_buyers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

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

    foreign_buyer = relationship(
        "ForeignBuyer",
        foreign_keys=[foreign_buyer_id],
        backref="default_for_suppliers",
    )

    __table_args__ = (
        Index(
            "ix_agency_suppliers_company_name",
            "agent_company_id",
            "name",
        ),
    )


class ForeignBuyer(Base):
    """An overseas counterparty the agent's LCs ship goods to."""

    __tablename__ = "agency_foreign_buyers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_company_id = Column(
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

    __table_args__ = (
        Index(
            "ix_agency_foreign_buyers_company_name",
            "agent_company_id",
            "name",
        ),
    )


__all__ = ["ForeignBuyer", "Supplier"]
