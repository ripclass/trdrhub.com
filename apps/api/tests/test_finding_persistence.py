"""Tests for finding_persistence — Phase A2 option B.

Verifies that the validation pipeline can hand off a list of finding
dicts and get back stable Discrepancy UUIDs tagged on each one. Same
SQLite-in-memory pattern as test_discrepancy_workflow.py.
"""

from __future__ import annotations

import uuid

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
from app.models.base import Base
from app.models.bulk_jobs import BulkItem, BulkJob  # noqa: F401  — FK targets
from app.models.discrepancy_workflow import (  # noqa: F401  — share metadata
    DiscrepancyComment,
    RepaperingRequest,
)
from app.models.user_notifications import Notification
from app.services.crossdoc import build_issue_cards
from app.services.finding_persistence import persist_findings_as_discrepancies


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
        Notification.__table__,
    ]
    Base.metadata.create_all(engine, tables=tables)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def session_row(db) -> ValidationSession:
    s = ValidationSession(
        user_id=uuid.uuid4(),
        status="running",
        workflow_type="exporter_presentation",
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def _findings(*items):
    return list(items)


class TestPersistFindings:
    def test_empty_list_is_noop(self, db, session_row):
        count = persist_findings_as_discrepancies(db, session_row, [])
        db.commit()
        assert count == 0
        assert db.query(Discrepancy).count() == 0

    def test_none_session_is_noop(self, db):
        count = persist_findings_as_discrepancies(
            db, None, [{"rule": "X", "title": "Y"}]
        )
        assert count == 0
        assert db.query(Discrepancy).count() == 0

    def test_single_finding_creates_row_and_tags_uuid(self, db, session_row):
        finding = {
            "rule": "UCP600-18A",
            "title": "Invoice arithmetic mismatch",
            "message": "Sum of line items does not match stated total",
            "severity": "major",
            "field": "total_amount",
            "expected": "USD 100,000",
            "actual": "USD 99,800",
            "documents": ["Commercial Invoice"],
        }
        count = persist_findings_as_discrepancies(db, session_row, [finding])
        db.commit()

        assert count == 1
        rows = db.query(Discrepancy).all()
        assert len(rows) == 1
        row = rows[0]
        assert row.validation_session_id == session_row.id
        assert row.rule_name == "UCP600-18A"
        assert row.field_name == "total_amount"
        assert row.severity == "major"
        # description prefers `message` over `title` — the longer narrative
        assert "sum of line items" in row.description.lower()
        assert row.expected_value == "USD 100,000"
        assert row.actual_value == "USD 99,800"
        # source_document_types is JSON; sqlite returns the python list back
        assert row.source_document_types == ["Commercial Invoice"]

        # Finding dict was tagged in-place with the persisted UUID
        assert finding.get("__discrepancy_uuid") == str(row.id)

    def test_multiple_findings_create_distinct_rows(self, db, session_row):
        findings = _findings(
            {"rule": "BL-MISSING-CLEAN-ON-BOARD", "title": "BL not clean", "severity": "critical"},
            {"rule": "INSURANCE-COVERAGE-LOW", "title": "Insurance < 110%", "severity": "major"},
            {"rule": "PORT-OF-LOADING-MISMATCH", "title": "POL differs", "severity": "major"},
        )
        count = persist_findings_as_discrepancies(db, session_row, findings)
        db.commit()

        assert count == 3
        assert db.query(Discrepancy).count() == 3
        uuids = {f["__discrepancy_uuid"] for f in findings}
        assert len(uuids) == 3

    def test_idempotent_second_run_updates_in_place(self, db, session_row):
        run1 = [
            {
                "rule": "UCP600-18A",
                "title": "Invoice arithmetic",
                "severity": "major",
                "field": "total_amount",
                "expected": "USD 100,000",
                "actual": "USD 99,800",
            }
        ]
        persist_findings_as_discrepancies(db, session_row, run1)
        db.commit()
        first_uuid = run1[0]["__discrepancy_uuid"]
        assert db.query(Discrepancy).count() == 1

        # Second run with same rule + field but mutated values
        run2 = [
            {
                "rule": "UCP600-18A",
                "title": "Invoice arithmetic (revised)",
                "severity": "critical",
                "field": "total_amount",
                "expected": "USD 100,000",
                "actual": "USD 90,000",
            }
        ]
        persist_findings_as_discrepancies(db, session_row, run2)
        db.commit()

        # Same UUID — row was updated, not duplicated
        assert run2[0]["__discrepancy_uuid"] == first_uuid
        assert db.query(Discrepancy).count() == 1

        row = db.query(Discrepancy).first()
        assert row.severity == "critical"
        assert "revised" in row.description.lower()
        assert row.actual_value == "USD 90,000"

    def test_idempotent_preserves_user_resolution_state(self, db, session_row):
        """If a user has already moved a discrepancy to ACKNOWLEDGED,
        a re-run of the pipeline must NOT reset it to raised.
        """
        run1 = [{"rule": "UCP600-18A", "title": "x", "severity": "major", "field": "f"}]
        persist_findings_as_discrepancies(db, session_row, run1)
        db.commit()

        row = db.query(Discrepancy).first()
        row.state = "acknowledged"
        row.owner_user_id = uuid.uuid4()
        db.commit()
        owner_before = row.owner_user_id

        # Re-run
        persist_findings_as_discrepancies(db, session_row, run1)
        db.commit()

        db.refresh(row)
        assert row.state == "acknowledged"
        assert row.owner_user_id == owner_before

    def test_finding_without_rule_synthesizes_one(self, db, session_row):
        finding = {
            "title": "BL signature is missing",
            "severity": "major",
        }
        persist_findings_as_discrepancies(db, session_row, [finding])
        db.commit()

        row = db.query(Discrepancy).first()
        assert row is not None
        assert row.rule_name  # non-empty
        assert "BL" in row.rule_name.upper() or "SIG" in row.rule_name.upper()
        assert finding["__discrepancy_uuid"] == str(row.id)

    def test_long_rule_and_field_truncation(self, db, session_row):
        long_rule = "X" * 250
        long_field = "y" * 250
        finding = {"rule": long_rule, "field": long_field, "title": "z", "severity": "minor"}
        persist_findings_as_discrepancies(db, session_row, [finding])
        db.commit()

        row = db.query(Discrepancy).first()
        assert len(row.rule_name) == 100
        assert len(row.field_name) == 100

    def test_severity_normalization(self, db, session_row):
        findings = _findings(
            {"rule": "A", "title": "a", "severity": "high"},
            {"rule": "B", "title": "b", "severity": "warning"},
            {"rule": "C", "title": "c", "severity": "info"},
            {"rule": "D", "title": "d", "severity": "garbage"},
        )
        persist_findings_as_discrepancies(db, session_row, findings)
        db.commit()
        sevs = {r.rule_name: r.severity for r in db.query(Discrepancy).all()}
        assert sevs["A"] == "critical"
        assert sevs["B"] == "major"
        assert sevs["C"] == "minor"
        assert sevs["D"] == "major"  # default


class TestIssueCardIntegration:
    """End-to-end: persist findings, then build_issue_cards reads the
    injected UUIDs and emits them as the card id (instead of rule name).
    """

    def test_issue_card_uses_persisted_uuid(self, db, session_row):
        findings = _findings(
            {
                "rule": "UCP600-18A",
                "title": "Invoice arithmetic",
                "severity": "major",
                "ruleset_domain": "icc.lcopilot.crossdoc",
            }
        )
        persist_findings_as_discrepancies(db, session_row, findings)
        db.commit()

        issue_cards, _ = build_issue_cards(findings)
        assert len(issue_cards) == 1
        card_id = issue_cards[0]["id"]
        # Should be a UUID string, not the rule name
        assert card_id != "UCP600-18A"
        # And it should round-trip — UUID format
        assert uuid.UUID(card_id) is not None

    def test_issue_card_falls_back_to_rule_when_no_uuid(self, db):
        # Persistence skipped (no validation_session) → no UUID tag
        finding = {
            "rule": "FALLBACK-RULE",
            "title": "x",
            "severity": "major",
            "ruleset_domain": "icc.lcopilot.crossdoc",
        }
        issue_cards, _ = build_issue_cards([finding])
        assert issue_cards[0]["id"] == "FALLBACK-RULE"
