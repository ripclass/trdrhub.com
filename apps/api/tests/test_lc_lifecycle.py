"""Tests for the LC lifecycle state machine — Phase A1 of Path A.

Covers the pure helpers + the transition() function with an in-memory
SQLite session so we exercise real SQLAlchemy bindings without
needing Postgres.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import legacy models module first so ValidationSession is registered
# on the shared Base before we touch the lc_lifecycle module.
from app import models as legacy_models  # noqa: F401  (side effects)
from app.models import ValidationSession
from app.models.base import Base
from app.models.lc_lifecycle import (
    LC_LIFECYCLE_DEFAULT_STATE,
    LC_LIFECYCLE_TERMINAL_STATES,
    LCLifecycleEvent,
    LCLifecycleState,
    allowed_next_states,
    is_terminal_state,
)
from app.services.lc_lifecycle import (
    InvalidLifecycleTransition,
    current_state,
    history,
    transition,
)


# ---------------------------------------------------------------------------
# Pure-helper tests (no DB)
# ---------------------------------------------------------------------------


class TestAllowedNextStates:
    def test_docs_in_preparation_can_advance_or_terminate(self):
        allowed = allowed_next_states(LCLifecycleState.DOCS_IN_PREPARATION)
        assert LCLifecycleState.DOCS_PRESENTED in allowed
        assert LCLifecycleState.EXPIRED in allowed
        assert LCLifecycleState.CLOSED in allowed
        assert LCLifecycleState.PAID not in allowed  # cannot skip review

    def test_under_bank_review_can_pay_or_raise_discrepancies(self):
        allowed = allowed_next_states(LCLifecycleState.UNDER_BANK_REVIEW)
        assert LCLifecycleState.PAID in allowed
        assert LCLifecycleState.DISCREPANCIES_RAISED in allowed
        assert LCLifecycleState.DOCS_IN_PREPARATION not in allowed

    def test_discrepancies_raised_can_resolve_or_re_paper(self):
        allowed = allowed_next_states(LCLifecycleState.DISCREPANCIES_RAISED)
        assert LCLifecycleState.DISCREPANCIES_RESOLVED in allowed
        assert LCLifecycleState.DOCS_IN_PREPARATION in allowed  # re-paper

    def test_closed_is_terminal(self):
        allowed = allowed_next_states(LCLifecycleState.CLOSED)
        assert allowed == frozenset()

    def test_unknown_state_returns_empty(self):
        assert allowed_next_states("totally-bogus-state") == frozenset()

    def test_string_input_works(self):
        # Pass a raw string the way the router would
        allowed = allowed_next_states("docs_in_preparation")
        assert LCLifecycleState.DOCS_PRESENTED in allowed


class TestIsTerminalState:
    def test_paid_is_terminal(self):
        assert is_terminal_state(LCLifecycleState.PAID)

    def test_closed_is_terminal(self):
        assert is_terminal_state("closed")

    def test_expired_is_terminal(self):
        assert is_terminal_state("expired")

    def test_under_review_is_not_terminal(self):
        assert not is_terminal_state(LCLifecycleState.UNDER_BANK_REVIEW)

    def test_terminals_match_table(self):
        for state in LCLifecycleState:
            assert is_terminal_state(state) == (state in LC_LIFECYCLE_TERMINAL_STATES)

    def test_unknown_string_is_not_terminal(self):
        assert not is_terminal_state("not-a-real-state")


# ---------------------------------------------------------------------------
# Transition tests (in-memory SQLite session)
# ---------------------------------------------------------------------------


@pytest.fixture()
def db():
    """Fresh in-memory SQLite per test, schema bootstrapped for ONLY
    the tables this test exercises.

    Whole-metadata create_all() blows up against SQLite because some
    other tables in the legacy schema use Postgres-only types like
    ARRAY and JSONB. Filtering to the tables we actually touch keeps
    the test isolated to lifecycle behavior.
    """
    engine = create_engine("sqlite:///:memory:")
    tables = [
        ValidationSession.__table__,
        LCLifecycleEvent.__table__,
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
    """Factory for ValidationSession rows with sensible defaults.

    Skips the User/Company FK requirement by leaving user_id as a
    fresh UUID (no relationship traversal in these tests).
    """

    def _build(state: str | None = None) -> ValidationSession:
        session = ValidationSession(
            user_id=uuid.uuid4(),
            status="created",
            workflow_type="exporter_presentation",
        )
        if state is not None:
            session.lifecycle_state = state
        db.add(session)
        db.commit()
        db.refresh(session)
        return session

    return _build


class TestCurrentState:
    def test_default_state_for_new_session(self, make_session):
        session = make_session()
        # SQLite doesn't honor server_default the way Postgres does,
        # so a brand-new row may have lifecycle_state as None even
        # though Postgres would have backfilled it. The helper must
        # gracefully fall back to the canonical default.
        assert current_state(session) == LC_LIFECYCLE_DEFAULT_STATE

    def test_explicit_state_round_trip(self, make_session):
        session = make_session(state="under_bank_review")
        assert current_state(session) == LCLifecycleState.UNDER_BANK_REVIEW

    def test_stale_value_falls_back_to_default(self, make_session):
        session = make_session(state="legacy_unknown_state_value")
        assert current_state(session) == LC_LIFECYCLE_DEFAULT_STATE


class TestTransition:
    def test_allowed_transition_succeeds(self, db, make_session):
        session = make_session(state="docs_in_preparation")
        actor_id = uuid.uuid4()

        event = transition(
            db,
            session,
            to_state=LCLifecycleState.DOCS_PRESENTED,
            actor_user_id=actor_id,
            reason="exporter submitted to negotiating bank",
        )
        db.commit()
        db.refresh(session)

        assert session.lifecycle_state == LCLifecycleState.DOCS_PRESENTED.value
        assert session.lifecycle_state_changed_at is not None
        assert event.from_state == "docs_in_preparation"
        assert event.to_state == "docs_presented"
        assert event.actor_user_id == actor_id
        assert event.reason == "exporter submitted to negotiating bank"

    def test_event_row_is_persisted(self, db, make_session):
        session = make_session(state="docs_in_preparation")
        transition(
            db,
            session,
            to_state="docs_presented",
            actor_user_id=uuid.uuid4(),
        )
        db.commit()

        rows = (
            db.query(LCLifecycleEvent)
            .filter(LCLifecycleEvent.validation_session_id == session.id)
            .all()
        )
        assert len(rows) == 1
        assert rows[0].to_state == "docs_presented"

    def test_disallowed_transition_raises(self, db, make_session):
        session = make_session(state="docs_in_preparation")
        with pytest.raises(InvalidLifecycleTransition) as exc_info:
            transition(
                db,
                session,
                to_state=LCLifecycleState.PAID,  # cannot skip from prep to paid
                actor_user_id=uuid.uuid4(),
            )

        err = exc_info.value
        assert err.from_state == "docs_in_preparation"
        assert err.to_state == "paid"
        assert LCLifecycleState.DOCS_PRESENTED in err.allowed
        assert LCLifecycleState.PAID not in err.allowed

    def test_force_bypasses_table(self, db, make_session):
        session = make_session(state="docs_in_preparation")
        transition(
            db,
            session,
            to_state=LCLifecycleState.PAID,
            actor_user_id=uuid.uuid4(),
            reason="admin override after manual reconciliation",
            force=True,
        )
        db.commit()
        db.refresh(session)
        assert session.lifecycle_state == "paid"

    def test_no_op_transition_logs_audit_marker(self, db, make_session):
        session = make_session(state="docs_in_preparation")
        transition(
            db,
            session,
            to_state="docs_in_preparation",
            actor_user_id=uuid.uuid4(),
        )
        db.commit()

        rows = (
            db.query(LCLifecycleEvent)
            .filter(LCLifecycleEvent.validation_session_id == session.id)
            .all()
        )
        assert len(rows) == 1
        assert rows[0].reason == "noop"
        assert rows[0].from_state == rows[0].to_state == "docs_in_preparation"

    def test_terminal_state_blocks_further_transitions(self, db, make_session):
        session = make_session(state="closed")
        with pytest.raises(InvalidLifecycleTransition):
            transition(
                db,
                session,
                to_state=LCLifecycleState.PAID,
                actor_user_id=uuid.uuid4(),
            )

    def test_terminal_state_allows_force(self, db, make_session):
        session = make_session(state="closed")
        # Re-opening a closed LC happens occasionally (admin
        # correction). Force should let it through.
        transition(
            db,
            session,
            to_state=LCLifecycleState.UNDER_BANK_REVIEW,
            actor_user_id=uuid.uuid4(),
            reason="admin reopened after counterparty correction",
            force=True,
        )
        db.commit()
        db.refresh(session)
        assert session.lifecycle_state == "under_bank_review"

    def test_re_papering_path_works(self, db, make_session):
        """End-to-end: bank raises discrepancy, exporter re-papers,
        new presentation goes back through review and clears."""
        session = make_session(state="docs_presented")
        actor = uuid.uuid4()

        # Bank reviews
        transition(db, session, "under_bank_review", actor_user_id=actor)
        # Bank raises discrepancies
        transition(db, session, "discrepancies_raised", actor_user_id=actor)
        # Exporter re-papers
        transition(db, session, "docs_in_preparation", actor_user_id=actor)
        # Present again
        transition(db, session, "docs_presented", actor_user_id=actor)
        transition(db, session, "under_bank_review", actor_user_id=actor)
        transition(db, session, "paid", actor_user_id=actor)
        db.commit()

        events = history(db, session)
        # Newest first; we made 6 transitions
        assert len(events) == 6
        assert events[0].to_state == "paid"
        assert events[-1].to_state == "under_bank_review"

    def test_unknown_target_state_raises(self, db, make_session):
        session = make_session(state="docs_in_preparation")
        with pytest.raises(InvalidLifecycleTransition):
            transition(
                db,
                session,
                to_state="not-a-state",
                actor_user_id=uuid.uuid4(),
            )


class TestHistory:
    def test_returns_events_newest_first(self, db, make_session):
        session = make_session(state="docs_in_preparation")
        actor = uuid.uuid4()
        transition(db, session, "docs_presented", actor_user_id=actor)
        transition(db, session, "under_bank_review", actor_user_id=actor)
        transition(db, session, "paid", actor_user_id=actor)
        db.commit()

        events = history(db, session)
        assert len(events) == 3
        assert events[0].to_state == "paid"
        assert events[2].to_state == "docs_presented"

    def test_limit_caps_results(self, db, make_session):
        session = make_session(state="docs_in_preparation")
        actor = uuid.uuid4()
        for to in ["docs_presented", "under_bank_review", "paid"]:
            transition(db, session, to, actor_user_id=actor)
        db.commit()

        events = history(db, session, limit=2)
        assert len(events) == 2
        assert events[0].to_state == "paid"
