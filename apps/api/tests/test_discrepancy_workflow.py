"""Tests for the discrepancy resolution workflow + re-papering loop —
Phase A2 of Path A.

Same SQLite-in-memory pattern as test_lc_lifecycle.py and
test_bulk_validate.py. Tests are pure model + service layer; the
router is exercised in a separate test that runs against the FastAPI
TestClient (covered in CI smoke).
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Legacy models registered first so Discrepancy / ValidationSession bind
# to the shared Base before we import the workflow extensions.
from app import models as legacy_models  # noqa: F401  (side effects)
from app.models import Discrepancy, ValidationSession
from app.models.base import Base
from app.models.bulk_jobs import BulkItem, BulkJob  # noqa: F401  — FK targets
from app.models.discrepancy_workflow import (
    DISCREPANCY_DEFAULT_STATE,
    DiscrepancyComment,
    DiscrepancyState,
    REPAPERING_TRANSITIONS,
    RepaperingRequest,
    RepaperingState,
    discrepancy_allowed_next_states,
    discrepancy_is_terminal,
    repapering_allowed_next_states,
)
from app.services.discrepancy_workflow import (
    InvalidDiscrepancyTransition,
    InvalidRepaperingTransition,
    add_recipient_comment,
    add_user_comment,
    assign_discrepancy_owner,
    create_repapering_request,
    discrepancy_current_state,
    transition_discrepancy,
    transition_repapering,
)


# ---------------------------------------------------------------------------
# Pure-helper tests
# ---------------------------------------------------------------------------


class TestDiscrepancyAllowedNext:
    def test_raised_can_engage_or_terminate(self):
        allowed = discrepancy_allowed_next_states(DiscrepancyState.RAISED)
        assert DiscrepancyState.ACKNOWLEDGED in allowed
        assert DiscrepancyState.ACCEPTED in allowed
        assert DiscrepancyState.WAIVED in allowed
        assert DiscrepancyState.REPAPER in allowed
        # Cannot skip straight to RESOLVED — must go through ACCEPTED/REPAPER
        # or come back from REPAPER once corrected.
        assert DiscrepancyState.RESOLVED not in allowed

    def test_repaper_can_resolve(self):
        allowed = discrepancy_allowed_next_states(DiscrepancyState.REPAPER)
        assert DiscrepancyState.RESOLVED in allowed
        assert DiscrepancyState.REJECTED in allowed

    def test_terminal_states_have_no_transitions(self):
        assert discrepancy_allowed_next_states(DiscrepancyState.WAIVED) == frozenset()
        assert discrepancy_allowed_next_states(DiscrepancyState.RESOLVED) == frozenset()

    def test_unknown_state(self):
        assert discrepancy_allowed_next_states("not-a-state") == frozenset()


class TestDiscrepancyIsTerminal:
    def test_terminals(self):
        assert discrepancy_is_terminal(DiscrepancyState.RESOLVED)
        assert discrepancy_is_terminal(DiscrepancyState.WAIVED)
        assert discrepancy_is_terminal("accepted")  # accepted carries audit-final but not in terminal set

    def test_non_terminals(self):
        assert not discrepancy_is_terminal(DiscrepancyState.RAISED)
        assert not discrepancy_is_terminal(DiscrepancyState.REPAPER)


class TestRepaperingAllowedNext:
    def test_requested_can_progress_or_cancel(self):
        allowed = repapering_allowed_next_states(RepaperingState.REQUESTED)
        assert RepaperingState.IN_PROGRESS in allowed
        assert RepaperingState.CANCELLED in allowed

    def test_corrected_can_resolve(self):
        allowed = repapering_allowed_next_states(RepaperingState.CORRECTED)
        assert RepaperingState.RESOLVED in allowed

    def test_terminal_states(self):
        assert repapering_allowed_next_states(RepaperingState.RESOLVED) == frozenset()
        assert repapering_allowed_next_states(RepaperingState.CANCELLED) == frozenset()


# ---------------------------------------------------------------------------
# DB-bound tests
# ---------------------------------------------------------------------------


@pytest.fixture()
def db():
    """Fresh in-memory SQLite per test, schema bootstrapped for the
    tables this test exercises.
    """
    engine = create_engine("sqlite:///:memory:")
    tables = [
        BulkJob.__table__,  # ValidationSession FK target
        BulkItem.__table__,
        ValidationSession.__table__,
        Discrepancy.__table__,
        DiscrepancyComment.__table__,
        RepaperingRequest.__table__,
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
def make_session(db):
    def _build() -> ValidationSession:
        s = ValidationSession(
            user_id=uuid.uuid4(),
            status="completed",
            workflow_type="exporter_presentation",
        )
        db.add(s)
        db.commit()
        db.refresh(s)
        return s

    return _build


@pytest.fixture()
def make_discrepancy(db, make_session):
    def _build(*, state: str | None = None) -> Discrepancy:
        s = make_session()
        d = Discrepancy(
            validation_session_id=s.id,
            discrepancy_type="ucp600",
            severity="major",
            rule_name="UCP600.18.c",
            description="Late presentation",
        )
        if state is not None:
            d.state = state
        db.add(d)
        db.commit()
        db.refresh(d)
        return d

    return _build


class TestDiscrepancyCurrentState:
    def test_default_state_when_unset(self, db, make_session):
        s = make_session()
        d = Discrepancy(
            validation_session_id=s.id,
            discrepancy_type="ucp600",
            severity="major",
            rule_name="UCP600.18.c",
            description="x",
        )
        assert discrepancy_current_state(d) == DISCREPANCY_DEFAULT_STATE

    def test_explicit_state_round_trip(self, make_discrepancy):
        d = make_discrepancy(state="repaper")
        assert discrepancy_current_state(d) == DiscrepancyState.REPAPER

    def test_stale_value_falls_back_to_default(self, make_discrepancy):
        d = make_discrepancy(state="legacy_unknown")
        assert discrepancy_current_state(d) == DISCREPANCY_DEFAULT_STATE


class TestTransitionDiscrepancy:
    def test_allowed_transition_succeeds(self, db, make_discrepancy):
        d = make_discrepancy()
        transition_discrepancy(
            db, d, DiscrepancyState.ACKNOWLEDGED, actor_user_id=uuid.uuid4()
        )
        db.commit()
        db.refresh(d)
        assert d.state == "acknowledged"
        assert d.acknowledged_at is not None
        assert d.state_changed_at is not None

    def test_disallowed_transition_raises(self, db, make_discrepancy):
        d = make_discrepancy()
        with pytest.raises(InvalidDiscrepancyTransition) as exc_info:
            transition_discrepancy(
                db, d, DiscrepancyState.RESOLVED, actor_user_id=uuid.uuid4()
            )
        err = exc_info.value
        assert err.from_state == "raised"
        assert err.to_state == "resolved"
        assert DiscrepancyState.ACKNOWLEDGED in err.allowed

    def test_terminal_resolution_sets_metadata(self, db, make_discrepancy):
        d = make_discrepancy()
        evidence = uuid.uuid4()
        transition_discrepancy(
            db,
            d,
            DiscrepancyState.WAIVED,
            actor_user_id=uuid.uuid4(),
            resolution_action="waive",
            resolution_evidence_session_id=evidence,
        )
        db.commit()
        db.refresh(d)
        assert d.state == "waived"
        assert d.resolved_at is not None
        assert d.resolution_action == "waive"
        assert d.resolution_evidence_session_id == evidence

    def test_force_bypasses_table(self, db, make_discrepancy):
        d = make_discrepancy()
        transition_discrepancy(
            db,
            d,
            DiscrepancyState.RESOLVED,
            actor_user_id=uuid.uuid4(),
            force=True,
        )
        db.commit()
        db.refresh(d)
        assert d.state == "resolved"

    def test_full_repaper_loop(self, db, make_discrepancy):
        """raised -> acknowledged -> repaper -> resolved (clean loop)."""
        d = make_discrepancy()
        actor = uuid.uuid4()
        transition_discrepancy(db, d, DiscrepancyState.ACKNOWLEDGED, actor_user_id=actor)
        transition_discrepancy(db, d, DiscrepancyState.REPAPER, actor_user_id=actor)
        transition_discrepancy(
            db,
            d,
            DiscrepancyState.RESOLVED,
            actor_user_id=actor,
            resolution_evidence_session_id=uuid.uuid4(),
        )
        db.commit()
        db.refresh(d)
        assert d.state == "resolved"
        assert d.resolved_at is not None
        # 3 system comments written for the 3 transitions.
        comments = (
            db.query(DiscrepancyComment)
            .filter(DiscrepancyComment.discrepancy_id == d.id)
            .all()
        )
        assert len(comments) == 3
        assert all(c.source == "system" for c in comments)


class TestUserComment:
    def test_user_comment_auto_advances_to_responded(self, db, make_discrepancy):
        d = make_discrepancy()  # state = raised
        author = uuid.uuid4()
        c = add_user_comment(db, d, body="will fix this", author_user_id=author)
        db.commit()
        db.refresh(d)
        assert d.state == "responded"
        assert c.body == "will fix this"
        assert c.source == "user"

    def test_user_comment_after_terminal_state_does_not_re_open(self, db, make_discrepancy):
        d = make_discrepancy(state="resolved")
        author = uuid.uuid4()
        add_user_comment(db, d, body="fyi", author_user_id=author)
        db.commit()
        db.refresh(d)
        # Comment lands but state stays resolved (no allowed transition out).
        assert d.state == "resolved"


class TestAssignOwner:
    def test_assign_writes_audit_comment(self, db, make_discrepancy):
        d = make_discrepancy()
        owner = uuid.uuid4()
        assign_discrepancy_owner(db, d, owner_user_id=owner, actor_user_id=uuid.uuid4())
        db.commit()
        db.refresh(d)
        assert d.owner_user_id == owner
        comments = (
            db.query(DiscrepancyComment)
            .filter(DiscrepancyComment.discrepancy_id == d.id)
            .all()
        )
        assert len(comments) == 1
        assert "Owner changed" in comments[0].body

    def test_idempotent_assign(self, db, make_discrepancy):
        d = make_discrepancy()
        owner = uuid.uuid4()
        assign_discrepancy_owner(db, d, owner_user_id=owner, actor_user_id=uuid.uuid4())
        db.commit()
        # Re-assign to same owner: no new comment.
        result = assign_discrepancy_owner(
            db, d, owner_user_id=owner, actor_user_id=uuid.uuid4()
        )
        db.commit()
        assert result is None
        comments = (
            db.query(DiscrepancyComment)
            .filter(DiscrepancyComment.discrepancy_id == d.id)
            .all()
        )
        assert len(comments) == 1


class TestRepapering:
    def test_create_request_transitions_discrepancy(self, db, make_discrepancy):
        d = make_discrepancy()
        request = create_repapering_request(
            db,
            d,
            requester_user_id=uuid.uuid4(),
            recipient_email="supplier@example.com",
            recipient_display_name="ACME Co.",
            message="please fix the late shipment date",
        )
        db.commit()
        db.refresh(request)
        db.refresh(d)
        assert d.state == "repaper"
        assert request.recipient_email == "supplier@example.com"
        assert request.access_token  # generated
        assert len(request.access_token) >= 32
        assert request.state == "requested"

    def test_repaper_full_loop(self, db, make_discrepancy):
        d = make_discrepancy()
        req = create_repapering_request(
            db,
            d,
            requester_user_id=uuid.uuid4(),
            recipient_email="supplier@example.com",
        )
        db.commit()

        # Recipient opens link.
        transition_repapering(db, req, RepaperingState.IN_PROGRESS)
        db.commit()
        db.refresh(req)
        assert req.opened_at is not None

        # Recipient uploads.
        transition_repapering(db, req, RepaperingState.CORRECTED)
        db.commit()
        db.refresh(req)
        assert req.submitted_at is not None

        # Re-validation comes back clean.
        replacement = uuid.uuid4()
        transition_repapering(
            db, req, RepaperingState.RESOLVED, replacement_session_id=replacement
        )
        db.commit()
        db.refresh(req)
        assert req.state == "resolved"
        assert req.resolved_at is not None
        assert req.replacement_session_id == replacement

    def test_invalid_repaper_transition_raises(self, db, make_discrepancy):
        d = make_discrepancy()
        req = create_repapering_request(
            db, d, requester_user_id=uuid.uuid4(), recipient_email="x@y.z"
        )
        db.commit()
        with pytest.raises(InvalidRepaperingTransition):
            # requested -> resolved is not allowed (must go through corrected)
            transition_repapering(db, req, RepaperingState.RESOLVED)

    def test_recipient_comment_carries_email_no_user(self, db, make_discrepancy):
        d = make_discrepancy()
        c = add_recipient_comment(
            db,
            d,
            body="here are the corrected docs",
            author_email="supplier@example.com",
            author_display_name="ACME",
        )
        db.commit()
        db.refresh(c)
        assert c.author_user_id is None
        assert c.author_email == "supplier@example.com"
        assert c.source == "recipient"
