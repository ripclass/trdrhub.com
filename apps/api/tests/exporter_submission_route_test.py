from __future__ import annotations

import os
import sys
import importlib.util
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
import types
from unittest.mock import MagicMock
from uuid import uuid4

import pytest


ROOT = Path(__file__).resolve().parents[1]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

os.environ["DEBUG"] = "false"

from app.models.exporter_submission import SubmissionEventType, SubmissionStatus  # noqa: E402


ROUTERS_ROOT = ROOT / "app" / "routers"
if "app.routers" not in sys.modules:
    routers_pkg = types.ModuleType("app.routers")
    routers_pkg.__path__ = [str(ROUTERS_ROOT)]
    sys.modules["app.routers"] = routers_pkg

_spec = importlib.util.spec_from_file_location("app.routers.exporter", ROUTERS_ROOT / "exporter.py")
if _spec is None or _spec.loader is None:
    raise RuntimeError("Unable to load exporter router module for tests")
exporter = importlib.util.module_from_spec(_spec)
sys.modules["app.routers.exporter"] = exporter
_spec.loader.exec_module(exporter)


class _FakeAuditService:
    def __init__(self, _db) -> None:
        self.calls: list[dict[str, object]] = []

    def log_action(self, **kwargs) -> None:
        self.calls.append(kwargs)


class _FakeExportSubmission:
    def __init__(self, **kwargs) -> None:
        self.id = uuid4()
        self.created_at = datetime.now(timezone.utc)
        self.receipt_url = None
        self.result_at = None
        for key, value in kwargs.items():
            setattr(self, key, value)


class _FakeSubmissionEvent:
    def __init__(self, **kwargs) -> None:
        self.id = uuid4()
        self.created_at = datetime.now(timezone.utc)
        for key, value in kwargs.items():
            setattr(self, key, value)


def _allow_submit_guardrails():
    return exporter.GuardrailCheckResponse(
        can_submit=True,
        blocking_issues=[],
        warnings=[],
        required_docs_present=True,
        high_severity_discrepancies=0,
        policy_checks_passed=True,
    )


@pytest.mark.asyncio
async def test_create_bank_submission_creates_pending_submission_and_initial_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(exporter, "AuditService", _FakeAuditService)
    monkeypatch.setattr(exporter, "ExportSubmission", _FakeExportSubmission)
    monkeypatch.setattr(exporter, "SubmissionEvent", _FakeSubmissionEvent)
    monkeypatch.setattr(exporter, "check_guardrails", lambda *_args, **_kwargs: _allow_submit_guardrails())

    session_id = uuid4()
    company_id = uuid4()
    user_id = uuid4()
    bank_id = uuid4()

    session_query = MagicMock()
    session_query.filter.return_value = session_query
    session_query.first.return_value = SimpleNamespace(
        id=session_id,
        company_id=company_id,
        validation_results={},
    )

    document_query = MagicMock()
    document_query.filter.return_value = document_query
    document_query.all.return_value = [
        SimpleNamespace(
            id=uuid4(),
            file_name="Invoice.pdf",
            original_filename="Invoice.pdf",
            document_type="invoice",
            sha256_hash="a" * 64,
        ),
        SimpleNamespace(
            id=uuid4(),
            file_name="Bill_of_Lading.pdf",
            original_filename="Bill_of_Lading.pdf",
            document_type="bill_of_lading",
            sha256_hash="b" * 64,
        ),
    ]

    db = MagicMock()
    db.query.side_effect = [session_query, document_query]

    request = exporter.BankSubmissionCreate(
        validation_session_id=session_id,
        lc_number="EXP2026BD001",
        bank_id=bank_id,
        bank_name="SABL Bank",
        note="Final exporter proof",
    )
    current_user = SimpleNamespace(
        id=user_id,
        company_id=company_id,
        full_name="Imran Ali",
        email="imran@iec.com",
    )

    response = await exporter.create_bank_submission(
        request=request,
        current_user=current_user,
        db=db,
        http_request=None,
    )

    assert response.company_id == company_id
    assert response.user_id == user_id
    assert response.validation_session_id == session_id
    assert response.bank_id == bank_id
    assert response.bank_name == "SABL Bank"
    assert response.status == SubmissionStatus.PENDING
    assert response.note == "Final exporter proof"

    assert db.add.call_count == 2
    submission = db.add.call_args_list[0].args[0]
    event = db.add.call_args_list[1].args[0]

    assert submission.manifest_data["lc_number"] == "EXP2026BD001"
    assert [doc["name"] for doc in submission.manifest_data["documents"]] == [
        "Invoice.pdf",
        "Bill_of_Lading.pdf",
    ]
    assert event.submission_id == submission.id
    assert event.event_type == SubmissionEventType.CREATED.value
    assert event.payload == {
        "lc_number": "EXP2026BD001",
        "bank_name": "SABL Bank",
    }
    db.flush.assert_called_once()
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(submission)


@pytest.mark.asyncio
async def test_create_bank_submission_returns_existing_submission_for_same_idempotency_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(exporter, "AuditService", _FakeAuditService)
    monkeypatch.setattr(exporter, "check_guardrails", lambda *_args, **_kwargs: _allow_submit_guardrails())

    company_id = uuid4()
    user_id = uuid4()
    session_id = uuid4()
    submission_id = uuid4()

    existing_submission = SimpleNamespace(
        id=submission_id,
        company_id=company_id,
        user_id=user_id,
        validation_session_id=session_id,
        lc_number="EXP2026BD001",
        bank_id=uuid4(),
        bank_name="SABL Bank",
        status=SubmissionStatus.PENDING.value,
        manifest_hash="abc123",
        note="Existing submission",
        receipt_url=None,
        created_at=datetime.now(timezone.utc),
        submitted_at=datetime.now(timezone.utc),
        result_at=None,
    )

    existing_query = MagicMock()
    existing_query.filter.return_value = existing_query
    existing_query.first.return_value = existing_submission

    db = MagicMock()
    db.query.return_value = existing_query

    request = exporter.BankSubmissionCreate(
        validation_session_id=session_id,
        lc_number="EXP2026BD001",
        bank_name="SABL Bank",
        idempotency_key="submit-once",
    )
    current_user = SimpleNamespace(
        id=user_id,
        company_id=company_id,
        full_name="Imran Ali",
        email="imran@iec.com",
    )

    response = await exporter.create_bank_submission(
        request=request,
        current_user=current_user,
        db=db,
        http_request=None,
    )

    assert response.id == submission_id
    assert response.status == SubmissionStatus.PENDING
    assert response.note == "Existing submission"
    db.add.assert_not_called()
    db.commit.assert_not_called()
    db.refresh.assert_not_called()
