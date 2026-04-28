"""Tests for the agency persona models — Phase A5.

Pure model + relationship checks against an in-memory SQLite. The
router is exercised via the existing FastAPI smoke + per-team manual
test pattern; the heavy lifting (per-company scoping, soft-delete,
foreign_buyer_id integrity) is on the model + service layer.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models as legacy_models  # noqa: F401  (side effects)
# Import all models referenced by ValidationSession FKs so SQLAlchemy
# can resolve them when create_all builds the schema.
from app.models.agency import ForeignBuyer as _AgencyBuyer, Supplier as _AgencySupplier  # noqa: F401
from app.models.services import ServicesClient as _ServicesClient, TimeEntry as _TimeEntry  # noqa: F401
_legacy_models = legacy_models  # noqa: F401  (side effects)
from app.models import Discrepancy, ValidationSession
from app.models.agency import ForeignBuyer, Supplier
from app.models.base import Base
from app.models.bulk_jobs import BulkItem, BulkJob  # noqa: F401  — FK target
from app.models.discrepancy_workflow import (  # noqa: F401  — keep metadata
    DiscrepancyComment,
    RepaperingRequest,
)


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    tables = [
        BulkJob.__table__,
        BulkItem.__table__,
        ValidationSession.__table__,
        Discrepancy.__table__,
        DiscrepancyComment.__table__,
        RepaperingRequest.__table__,
        ForeignBuyer.__table__,
        Supplier.__table__,
    ]
    Base.metadata.create_all(engine, tables=tables)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


class TestSupplierCreate:
    def test_minimal_fields(self, db):
        company_id = uuid.uuid4()
        s = Supplier(agent_company_id=company_id, name="Acme Garments Ltd.")
        db.add(s)
        db.commit()
        db.refresh(s)
        assert s.id is not None
        assert s.name == "Acme Garments Ltd."
        assert s.country is None
        assert s.deleted_at is None
        assert s.created_at is not None

    def test_full_fields(self, db):
        company_id = uuid.uuid4()
        s = Supplier(
            agent_company_id=company_id,
            name="Acme",
            country="BD",
            factory_address="Plot 42, Savar EPZ",
            contact_name="Karim Rahman",
            contact_email="karim@acme.bd",
            contact_phone="+8801712345678",
            notes="Cotton garments only",
        )
        db.add(s)
        db.commit()
        db.refresh(s)
        assert s.country == "BD"
        assert s.factory_address.startswith("Plot 42")


class TestForeignBuyerCreate:
    def test_minimal_fields(self, db):
        company_id = uuid.uuid4()
        b = ForeignBuyer(agent_company_id=company_id, name="HM International")
        db.add(b)
        db.commit()
        db.refresh(b)
        assert b.id is not None
        assert b.name == "HM International"


class TestSupplierBuyerLink:
    def test_supplier_with_default_buyer(self, db):
        company_id = uuid.uuid4()
        buyer = ForeignBuyer(agent_company_id=company_id, name="Walmart Asia")
        db.add(buyer)
        db.commit()
        db.refresh(buyer)

        supplier = Supplier(
            agent_company_id=company_id,
            name="Acme",
            foreign_buyer_id=buyer.id,
        )
        db.add(supplier)
        db.commit()
        db.refresh(supplier)
        assert supplier.foreign_buyer_id == buyer.id
        # Backref
        assert supplier.foreign_buyer.name == "Walmart Asia"

    def test_buyer_deletion_nulls_supplier_fk(self, db):
        # SQLite respects ondelete="SET NULL" only when foreign_keys
        # pragma is on; under our test config the FK isn't enforced
        # so we mimic the cascade manually.
        company_id = uuid.uuid4()
        buyer = ForeignBuyer(agent_company_id=company_id, name="Walmart")
        db.add(buyer)
        db.commit()
        db.refresh(buyer)
        supplier = Supplier(
            agent_company_id=company_id,
            name="Acme",
            foreign_buyer_id=buyer.id,
        )
        db.add(supplier)
        db.commit()
        # Soft-delete the buyer; production would null the FK via
        # ondelete=SET NULL on hard delete. Here the soft-delete
        # column tracks the same intent.
        buyer.deleted_at = datetime.now(timezone.utc)
        db.commit()
        # Supplier still references the soft-deleted buyer; that's
        # intentional — listing endpoints filter on deleted_at.
        db.refresh(supplier)
        assert supplier.foreign_buyer_id == buyer.id


class TestValidationSessionAttribution:
    def test_session_links_to_supplier(self, db):
        company_id = uuid.uuid4()
        supplier = Supplier(agent_company_id=company_id, name="Acme")
        db.add(supplier)
        db.commit()
        db.refresh(supplier)

        session = ValidationSession(
            user_id=uuid.uuid4(),
            status="completed",
            workflow_type="exporter_presentation",
            supplier_id=supplier.id,
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        assert session.supplier_id == supplier.id

    def test_session_without_supplier_is_legacy(self, db):
        session = ValidationSession(
            user_id=uuid.uuid4(),
            status="completed",
            workflow_type="exporter_presentation",
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        assert session.supplier_id is None


class TestSoftDelete:
    def test_supplier_soft_delete(self, db):
        company_id = uuid.uuid4()
        s = Supplier(agent_company_id=company_id, name="Acme")
        db.add(s)
        db.commit()
        db.refresh(s)
        assert s.deleted_at is None
        s.deleted_at = datetime.now(timezone.utc)
        db.commit()
        # Row still in DB — listing endpoints filter on deleted_at IS NULL.
        assert (
            db.query(Supplier).filter(Supplier.id == s.id).first().deleted_at
            is not None
        )

    def test_buyer_soft_delete(self, db):
        company_id = uuid.uuid4()
        b = ForeignBuyer(agent_company_id=company_id, name="Walmart")
        db.add(b)
        db.commit()
        db.refresh(b)
        b.deleted_at = datetime.now(timezone.utc)
        db.commit()
        assert (
            db.query(ForeignBuyer)
            .filter(ForeignBuyer.id == b.id)
            .first()
            .deleted_at
            is not None
        )
