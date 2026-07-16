"""Persisted, idempotent Proofline module orchestration."""

from __future__ import annotations

import asyncio
import uuid
from types import SimpleNamespace

from app.models import ProoflineFinding, TradeCaseCheckRun
from app.services.proofline.applicability import ModuleApplicability
from app.services.proofline.orchestrator import (
    AdapterResult,
    canonical_input_hash,
    run_check,
)


class _Query:
    def __init__(self, rows):
        self.rows = list(rows)

    def filter(self, *criteria):
        for criterion in criteria:
            column = getattr(getattr(criterion, "left", None), "name", None)
            operator = getattr(getattr(criterion, "operator", None), "__name__", "")
            expected = getattr(getattr(criterion, "right", None), "value", None)
            if column and operator == "eq":
                self.rows = [
                    row for row in self.rows if getattr(row, column, None) == expected
                ]
        return self

    def first(self):
        return self.rows[0] if self.rows else None


class _Db:
    def __init__(self):
        self.rows = {TradeCaseCheckRun: [], ProoflineFinding: []}
        self.flushes = 0

    def query(self, model):
        return _Query(self.rows.get(model, []))

    def add(self, row):
        self.rows.setdefault(type(row), []).append(row)

    def flush(self):
        self.flushes += 1


class _Adapter:
    module = "open_account_review"
    version = "open-account-1"

    def __init__(self):
        self.calls = 0

    async def run(self, context):
        self.calls += 1
        return AdapterResult(
            state="issue_found",
            summary="One payment evidence gap was found.",
            source_record_type="proofline_open_account",
            source_record_id="OA-RUN-1",
            findings=[
                {
                    "source_finding_id": "OA-PAYMENT-TRIGGER-1",
                    "category": "payment_terms",
                    "severity": "high",
                    "title": "Payment trigger is not evidenced",
                    "explanation": "No approval trigger was found.",
                    "expected": "An identifiable approval trigger",
                    "observed": "No trigger in submitted evidence",
                    "suggested_correction": "Upload the agreed payment terms.",
                    "rule_reference": None,
                    "evidence_references": [],
                }
            ],
        )


class _FailingAdapter:
    module = "rulhub"
    version = "rulhub-client-1"

    async def run(self, context):
        raise TimeoutError("request contained private transaction details")


def _case():
    return SimpleNamespace(id=uuid.uuid4(), company_id=uuid.uuid4())


def _applicability(module="open_account_review", applicable=True):
    return ModuleApplicability(
        module=module,
        category="payment",
        applicable=applicable,
        required=applicable,
        reason="Applicable to this payment arrangement" if applicable else "Not used",
        state="pending" if applicable else "not_applicable",
    )


def test_input_hash_is_stable_across_mapping_order():
    assert canonical_input_hash({"a": 1, "b": {"x": 2, "y": 3}}) == canonical_input_hash(
        {"b": {"y": 3, "x": 2}, "a": 1}
    )


def test_not_applicable_module_is_persisted_without_calling_adapter():
    db = _Db()
    adapter = _Adapter()
    check = asyncio.run(
        run_check(
            db,
            trade_case=_case(),
            applicability=_applicability(applicable=False),
            context={},
            adapter=adapter,
            idempotency_key="not-applicable-1",
        )
    )

    assert check.state == "not_applicable"
    assert check.applicable is False
    assert adapter.calls == 0


def test_successful_check_persists_source_reference_and_normalized_finding_once():
    db = _Db()
    trade_case = _case()
    adapter = _Adapter()
    kwargs = dict(
        trade_case=trade_case,
        applicability=_applicability(),
        context={"payment_terms": {"due_days": 60}},
        adapter=adapter,
        idempotency_key="open-account-input-1",
    )

    first = asyncio.run(run_check(db, **kwargs))
    replay = asyncio.run(run_check(db, **kwargs))

    assert first.state == "issue_found"
    assert first.source_record_type == "proofline_open_account"
    assert first.source_record_id == "OA-RUN-1"
    assert replay is first
    assert adapter.calls == 1
    findings = db.rows[ProoflineFinding]
    assert len(findings) == 1
    assert findings[0].expected == "An identifiable approval trigger"
    assert findings[0].observed == "No trigger in submitted evidence"
    assert findings[0].suggested_correction.startswith("Upload")


def test_adapter_timeout_fails_closed_without_persisting_sensitive_exception_text():
    db = _Db()
    check = asyncio.run(
        run_check(
            db,
            trade_case=_case(),
            applicability=_applicability(module="rulhub"),
            context={"private": "do not log"},
            adapter=_FailingAdapter(),
            idempotency_key="rulhub-timeout-1",
        )
    )

    assert check.state == "unable_to_assess"
    assert check.error_code == "adapter_timeout"
    assert check.safe_error_message == "The required check timed out. Analyst review is required."
    assert "private transaction" not in check.safe_error_message

