"""LCopilot-to-Proofline upgrade preserves source work and ownership."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.services.proofline import upgrade


class _Query:
    def __init__(self, result=None):
        self.result = result

    def filter(self, *_args):
        return self

    def first(self):
        return self.result


class _Db:
    def __init__(self, existing=None):
        self.existing = existing
        self.added = []

    def query(self, _model):
        return _Query(self.existing)

    def add(self, value):
        self.added.append(value)

    def flush(self):
        return None


class _Repo:
    def __init__(self, db):
        self.db = db
        self.parties = []

    def create_case(self, *, company_id, customer_user_id, owner_user_id, values):
        return SimpleNamespace(
            id=uuid.uuid4(),
            case_reference="PL-UPGRADE1",
            company_id=company_id,
            customer_user_id=customer_user_id,
            owner_user_id=owner_user_id,
            created_at=datetime.now(timezone.utc),
            **values,
        )

    def create_party(self, *, company_id, case_id, values):
        party = SimpleNamespace(
            id=uuid.uuid4(), company_id=company_id, trade_case_id=case_id, **values
        )
        self.parties.append(party)
        return party


@pytest.mark.asyncio
async def test_upgrade_references_completed_lcopilot_work_without_rerunning(monkeypatch):
    company_id = uuid.uuid4()
    user = SimpleNamespace(id=uuid.uuid4(), company_id=company_id)
    documents = [
        SimpleNamespace(id=uuid.uuid4(), document_type="letter_of_credit"),
        SimpleNamespace(id=uuid.uuid4(), document_type="commercial_invoice"),
    ]
    source = SimpleNamespace(
        id=uuid.uuid4(),
        company_id=company_id,
        user_id=user.id,
        status="completed",
        review_state="delivered",
        workflow_type="exporter_presentation",
        validation_results={
            "structured_result": {
                "lc_number": "EXP2026BD001",
                "amount": 125000,
                "currency": "USD",
                "applicant": "US Buyer Inc",
                "beneficiary": "Dhaka Exporter Ltd",
                "issues": [{"rule": "UCP600-14", "severity": "major"}],
            }
        },
        documents=documents,
        review_report_id=uuid.uuid4(),
    )
    repository = _Repo(_Db())
    associated = []
    checks = []

    def associate(_db, **kwargs):
        associated.append(kwargs)
        return SimpleNamespace(id=uuid.uuid4())

    async def reuse_check(_db, **kwargs):
        checks.append(kwargs)
        return SimpleNamespace(id=uuid.uuid4(), state="issue_found")

    monkeypatch.setattr(upgrade, "associate_document", associate)
    monkeypatch.setattr(upgrade, "run_check", reuse_check)

    trade_case, created = await upgrade.upgrade_lcopilot_session(
        repository.db,
        source_session=source,
        current_user=user,
        repository=repository,
    )

    assert created is True
    assert trade_case.source_lcopilot_session_id == source.id
    assert trade_case.document_session_id == source.id
    assert trade_case.service_package_id == "proofline_standard"
    assert trade_case.currency == "USD"
    assert str(trade_case.amount) == "125000"
    assert trade_case.transaction_details["source_lcopilot_result_reused"] is True
    assert trade_case.transaction_details["source_lcopilot_report_id"] == str(source.review_report_id)
    assert [item["logical_key"] for item in associated] == [
        "letter_of_credit",
        "commercial_invoice",
    ]
    assert {party.name for party in repository.parties} == {
        "US Buyer Inc",
        "Dhaka Exporter Ltd",
    }
    assert checks[0]["context"]["source_lcopilot_result"] is source.validation_results["structured_result"]


@pytest.mark.asyncio
async def test_upgrade_is_idempotent_for_same_tenant_and_source(monkeypatch):
    company_id = uuid.uuid4()
    existing = SimpleNamespace(id=uuid.uuid4(), company_id=company_id)
    source = SimpleNamespace(id=uuid.uuid4(), company_id=company_id)
    user = SimpleNamespace(id=uuid.uuid4(), company_id=company_id)
    monkeypatch.setattr(upgrade, "ProoflineRepository", lambda db: _Repo(db))

    trade_case, created = await upgrade.upgrade_lcopilot_session(
        _Db(existing), source_session=source, current_user=user
    )

    assert trade_case is existing
    assert created is False


@pytest.mark.asyncio
async def test_upgrade_rejects_incomplete_or_cross_tenant_source():
    user = SimpleNamespace(id=uuid.uuid4(), company_id=uuid.uuid4())
    cross_tenant = SimpleNamespace(
        id=uuid.uuid4(), company_id=uuid.uuid4(), status="completed", review_state="delivered"
    )
    with pytest.raises(upgrade.LCopilotUpgradeError):
        await upgrade.upgrade_lcopilot_session(
            _Db(), source_session=cross_tenant, current_user=user
        )

    incomplete = SimpleNamespace(
        id=uuid.uuid4(), company_id=user.company_id, status="processing", review_state="under_review"
    )
    with pytest.raises(upgrade.LCopilotUpgradeError):
        await upgrade.upgrade_lcopilot_session(
            _Db(), source_session=incomplete, current_user=user
        )
