"""Tests for the bulk-validation processor + broker — Phase A1 part 2.

Covers the broker pub/sub semantics + the full processor flow with the
real pipeline mocked out. Tests intentionally don't hit
``run_validate_pipeline`` for two reasons:

  * It would require a working LLM provider + RulHub creds, neither
    of which are available in CI.
  * The shape of the result + the side-effects on the spawned
    ``ValidationSession`` are stable (covered by other test suites).
    Bulk's job is to call the pipeline correctly, persist results,
    and emit progress events — that's what we verify here.

Mocking pattern: monkey-patch
``app.services.bulk_validate_processor._pipeline_runner`` per-test.
"""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import legacy models first so ValidationSession + the bulk_jobs
# foreign-key targets register on the shared Base.
from app import models as legacy_models  # noqa: F401  (side effects)
from app.models import ValidationSession
from app.models.base import Base
from app.models.bulk_jobs import (
    BulkFailure,
    BulkItem,
    BulkJob,
    ItemStatus,
    JobEvent,
    JobStatus,
)
from app.models.lc_lifecycle import LCLifecycleEvent, LCLifecycleState
from app.services import bulk_validate_processor as bvp
from app.services.bulk_progress_broker import BulkProgressBroker
from app.services.bulk_validate_processor import (
    CUSTOMER_LC_VALIDATION_JOB_TYPE,
    BulkValidateProcessor,
)


# ---------------------------------------------------------------------------
# Broker tests
# ---------------------------------------------------------------------------


class TestBulkProgressBroker:
    @pytest.mark.asyncio
    async def test_publish_then_subscribe_yields_event(self):
        b = BulkProgressBroker()
        job_id = uuid.uuid4()

        # Subscribe in a task, publish, then close so the iterator exits.
        events = []

        async def consume():
            async for ev in b.subscribe(job_id):
                events.append(ev)

        task = asyncio.create_task(consume())
        # Wait until the subscriber is registered before publishing.
        for _ in range(50):
            if await b.subscriber_count(job_id) >= 1:
                break
            await asyncio.sleep(0.01)
        await b.publish(job_id, {"event": "tick", "n": 1})
        await b.publish(job_id, {"event": "tick", "n": 2})
        await b.close(job_id)
        await asyncio.wait_for(task, timeout=2.0)

        assert events == [{"event": "tick", "n": 1}, {"event": "tick", "n": 2}]

    @pytest.mark.asyncio
    async def test_subscribe_auto_cleans_up_on_cancel(self):
        b = BulkProgressBroker()
        job_id = uuid.uuid4()

        async def consume():
            async for _ in b.subscribe(job_id):
                pass

        task = asyncio.create_task(consume())
        for _ in range(50):
            if await b.subscriber_count(job_id) >= 1:
                break
            await asyncio.sleep(0.01)
        assert await b.subscriber_count(job_id) == 1

        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        # Give the finally block a tick to run.
        await asyncio.sleep(0.05)
        assert await b.subscriber_count(job_id) == 0

    @pytest.mark.asyncio
    async def test_publish_with_no_subscribers_is_noop(self):
        b = BulkProgressBroker()
        # Should not raise.
        await b.publish(uuid.uuid4(), {"event": "lonely"})


# ---------------------------------------------------------------------------
# Processor tests — in-memory SQLite, mocked pipeline
# ---------------------------------------------------------------------------


@pytest.fixture()
def db():
    """Fresh in-memory SQLite per test, schema bootstrapped for ONLY
    the tables this test exercises.

    User isn't included — the legacy User table has columns (e.g.
    ``onboarding_data``) that use raw Postgres JSONB and don't compile
    on SQLite. The processor takes a ``current_user`` object directly
    so we never need to round-trip a User row through the DB.
    """
    engine = create_engine("sqlite:///:memory:")
    tables = [
        ValidationSession.__table__,
        LCLifecycleEvent.__table__,
        BulkJob.__table__,
        BulkItem.__table__,
        BulkFailure.__table__,
        JobEvent.__table__,
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
def make_user():
    """Build a SimpleNamespace user with the attributes the processor
    actually reads (``id``, optionally ``company_id``).
    """
    from types import SimpleNamespace

    def _build() -> Any:
        return SimpleNamespace(
            id=uuid.uuid4(),
            company_id=None,
            email="bulk-tester@test.local",
        )

    return _build


@pytest.fixture()
def make_job(db, make_user):
    def _build(*, total_items: int = 0, status: str = JobStatus.PENDING.value) -> BulkJob:
        user = make_user()
        job = BulkJob(
            id=uuid.uuid4(),
            tenant_id=str(user.id),
            name="bulk test",
            job_type=CUSTOMER_LC_VALIDATION_JOB_TYPE,
            config={},
            created_by=user.id,
            status=status,
            total_items=total_items,
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return job, user

    return _build


@pytest.fixture()
def make_item(db, tmp_path: Path):
    def _build(job: BulkJob, lc_identifier: str = "LC-X") -> BulkItem:
        # Drop a tiny placeholder file on disk so the processor's
        # path-resolution doesn't trip; the mocked pipeline never
        # actually reads it.
        file_path = tmp_path / f"{lc_identifier}.pdf"
        file_path.write_bytes(b"%PDF-1.4 stub")
        item = BulkItem(
            id=uuid.uuid4(),
            job_id=job.id,
            lc_identifier=lc_identifier,
            item_data={"file_paths": [str(file_path)]},
            status=ItemStatus.PENDING.value,
        )
        db.add(item)
        job.total_items = (job.total_items or 0) + 1
        db.commit()
        db.refresh(item)
        return item

    return _build


@pytest.fixture(autouse=True)
def _isolated_broker(monkeypatch):
    """Replace the module-level singleton with a fresh broker per test
    so events from different tests can't bleed into each other.
    """
    fresh = BulkProgressBroker()
    monkeypatch.setattr("app.services.bulk_validate_processor.broker", fresh)
    monkeypatch.setattr("app.services.bulk_progress_broker.broker", fresh)
    return fresh


@pytest.fixture(autouse=True)
def _override_session_local(monkeypatch, db):
    """Force the processor's ``SessionLocal()`` to hand back the same
    in-memory session the test uses, so test assertions see the writes.

    The processor closes its session in a finally — we patch ``close``
    to a no-op for the test session's lifetime so post-run assertions
    can still query. The fixture's ``finally`` block restores the real
    close so engine teardown works.
    """
    real_close = db.close
    db.close = lambda: None  # type: ignore[assignment]

    monkeypatch.setattr(
        "app.services.bulk_validate_processor.SessionLocal", lambda: db
    )
    try:
        yield
    finally:
        db.close = real_close  # type: ignore[assignment]


def _mock_pipeline_factory(*, validation_session_holder: dict, db):
    """Build a fake ``run_validate_pipeline`` that creates a real
    ValidationSession row + writes it into the runtime_context the way
    the real pipeline does.
    """

    async def _fake(**kwargs):
        rt = kwargs["runtime_context"]
        current_user = kwargs["current_user"]
        sess = ValidationSession(
            id=uuid.uuid4(),
            user_id=current_user.id,
            status="completed",
            workflow_type="exporter_presentation",
            lifecycle_state=LCLifecycleState.DOCS_IN_PREPARATION.value,
        )
        db.add(sess)
        db.commit()
        db.refresh(sess)
        rt["validation_session"] = sess
        validation_session_holder.setdefault("sessions", []).append(sess)
        return {
            "session_id": str(sess.id),
            "structured_result": {
                "verdict": "pass",
                "compliance_score": 95.0,
            },
            "provisional_issues": [],
        }

    return _fake


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestProcessorHappyPath:
    @pytest.mark.asyncio
    async def test_run_processes_all_items_and_emits_events(
        self, db, make_job, make_item, monkeypatch, _isolated_broker
    ):
        job, user = make_job()
        items = [make_item(job, lc_identifier=f"LC-{i}") for i in range(3)]

        spawned: dict = {}
        monkeypatch.setattr(
            bvp,
            "_pipeline_runner",
            _mock_pipeline_factory(validation_session_holder=spawned, db=db),
        )

        # Capture broker events.
        received: list = []

        async def consume():
            async for ev in _isolated_broker.subscribe(job.id):
                received.append(ev)

        consumer = asyncio.create_task(consume())
        # Wait until subscribed.
        for _ in range(50):
            if await _isolated_broker.subscriber_count(job.id) >= 1:
                break
            await asyncio.sleep(0.01)

        processor = BulkValidateProcessor(concurrency=2, per_item_timeout_seconds=30)
        await processor.run(job_id=job.id, current_user=user)
        await asyncio.wait_for(consumer, timeout=2.0)

        # Job state.
        db.expire_all()
        job_after = db.query(BulkJob).filter(BulkJob.id == job.id).first()
        assert job_after.status == JobStatus.SUCCEEDED.value
        assert job_after.succeeded_items == 3
        assert job_after.failed_items == 0
        assert job_after.finished_at is not None

        # All items SUCCEEDED.
        item_rows = db.query(BulkItem).filter(BulkItem.job_id == job.id).all()
        assert all(i.status == ItemStatus.SUCCEEDED.value for i in item_rows)
        # Each item carries its result summary.
        for i in item_rows:
            assert i.result_data is not None
            assert i.result_data.get("verdict") == "pass"
            assert i.result_data.get("compliance_score") == 95.0

        # Spawned ValidationSessions linked back to bulk job + item.
        assert len(spawned.get("sessions", [])) == 3
        for sess in spawned["sessions"]:
            db.refresh(sess)
            assert sess.bulk_job_id == job.id
            assert sess.bulk_item_id is not None

        # Lifecycle event written per spawned session.
        events = db.query(LCLifecycleEvent).all()
        assert len(events) == 3
        assert all(e.to_state == LCLifecycleState.DOCS_PRESENTED.value for e in events)
        assert all(e.reason == "bulk_validate_completed" for e in events)

        # Progress events: one job_started, three item_started + item_completed,
        # one job_completed.
        kinds = [e.get("event") for e in received]
        assert "job_started" in kinds
        assert kinds.count("item_started") == 3
        assert kinds.count("item_completed") == 3
        assert "job_completed" in kinds


class TestProcessorFailureIsolation:
    @pytest.mark.asyncio
    async def test_one_failed_item_does_not_block_others(
        self, db, make_job, make_item, monkeypatch, _isolated_broker
    ):
        job, user = make_job()
        items = [make_item(job, lc_identifier=f"LC-{i}") for i in range(3)]
        target_failure_id = items[1].id

        async def _flaky_pipeline(**kwargs):
            rt = kwargs["runtime_context"]
            bulk_item_id = rt.get("bulk_item_id")
            if bulk_item_id == str(target_failure_id):
                raise RuntimeError("simulated extraction failure")
            sess = ValidationSession(
                id=uuid.uuid4(),
                user_id=kwargs["current_user"].id,
                status="completed",
                workflow_type="exporter_presentation",
                lifecycle_state=LCLifecycleState.DOCS_IN_PREPARATION.value,
            )
            db.add(sess)
            db.commit()
            db.refresh(sess)
            rt["validation_session"] = sess
            return {"structured_result": {"verdict": "pass"}, "provisional_issues": []}

        monkeypatch.setattr(bvp, "_pipeline_runner", _flaky_pipeline)

        processor = BulkValidateProcessor(concurrency=1, per_item_timeout_seconds=30)
        await processor.run(job_id=job.id, current_user=user)

        db.expire_all()
        job_after = db.query(BulkJob).filter(BulkJob.id == job.id).first()
        assert job_after.status == JobStatus.PARTIAL.value
        assert job_after.succeeded_items == 2
        assert job_after.failed_items == 1

        failed_item = db.query(BulkItem).filter(BulkItem.id == target_failure_id).first()
        assert failed_item.status == ItemStatus.FAILED.value
        assert failed_item.error_code == "pipeline_error"
        assert failed_item.last_error
        # BulkFailure row created.
        failures = db.query(BulkFailure).filter(BulkFailure.item_id == target_failure_id).all()
        assert len(failures) == 1
        assert failures[0].error_code == "pipeline_error"


class TestProcessorCancel:
    @pytest.mark.asyncio
    async def test_cancel_skips_remaining_items(
        self, db, make_job, make_item, monkeypatch
    ):
        job, user = make_job()
        items = [make_item(job, lc_identifier=f"LC-{i}") for i in range(5)]

        processor = BulkValidateProcessor(concurrency=1, per_item_timeout_seconds=30)
        processed_count = 0

        async def _slow_pipeline(**kwargs):
            nonlocal processed_count
            processed_count += 1
            if processed_count == 2:
                # Mid-flight cancel after the second item starts.
                processor.cancel()
            sess = ValidationSession(
                id=uuid.uuid4(),
                user_id=kwargs["current_user"].id,
                status="completed",
                workflow_type="exporter_presentation",
                lifecycle_state=LCLifecycleState.DOCS_IN_PREPARATION.value,
            )
            db.add(sess)
            db.commit()
            db.refresh(sess)
            kwargs["runtime_context"]["validation_session"] = sess
            return {"structured_result": {"verdict": "pass"}, "provisional_issues": []}

        monkeypatch.setattr(bvp, "_pipeline_runner", _slow_pipeline)

        await processor.run(job_id=job.id, current_user=user)

        db.expire_all()
        item_rows = db.query(BulkItem).filter(BulkItem.job_id == job.id).all()
        statuses = [i.status for i in item_rows]
        # At least one SUCCEEDED before cancel, at least one SKIPPED after.
        assert ItemStatus.SUCCEEDED.value in statuses
        assert ItemStatus.SKIPPED.value in statuses
        # No item should remain PENDING.
        assert ItemStatus.PENDING.value not in statuses

        job_after = db.query(BulkJob).filter(BulkJob.id == job.id).first()
        # CANCELLED takes precedence in finalize when cancel_flag is set.
        assert job_after.status == JobStatus.CANCELLED.value


class TestProcessorTimeout:
    @pytest.mark.asyncio
    async def test_per_item_timeout_records_failure(
        self, db, make_job, make_item, monkeypatch
    ):
        job, user = make_job()
        make_item(job, lc_identifier="LC-slow")

        async def _hangs(**kwargs):
            await asyncio.sleep(5.0)  # longer than the timeout below
            return {"structured_result": {"verdict": "pass"}}

        monkeypatch.setattr(bvp, "_pipeline_runner", _hangs)

        processor = BulkValidateProcessor(
            concurrency=1, per_item_timeout_seconds=1, job_timeout_seconds=60
        )
        await processor.run(job_id=job.id, current_user=user)

        db.expire_all()
        item = db.query(BulkItem).filter(BulkItem.job_id == job.id).first()
        assert item.status == ItemStatus.FAILED.value
        assert item.error_code == "item_timeout"


class TestSummary:
    def test_summarize_pass_payload(self):
        summary = BulkValidateProcessor._summarize_result(
            {
                "structured_result": {
                    "verdict": "REJECT",
                    "compliance_score": 0.62,
                },
                "provisional_issues": [{"severity": "major"}, {"severity": "minor"}],
            }
        )
        assert summary["verdict"] == "REJECT"
        assert summary["compliance_score"] == 0.62
        assert summary["finding_count"] == 2

    def test_summarize_handles_non_dict(self):
        summary = BulkValidateProcessor._summarize_result("not-a-dict")
        assert summary == {"raw_type": "str"}
