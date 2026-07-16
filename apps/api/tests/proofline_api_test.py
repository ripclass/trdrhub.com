"""Proofline customer case API behavior without application-wide bootstrapping."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.routers import proofline as router_module
from app.schemas.proofline import TradeCaseCreate, TradeCaseUpdate


def _case(company_id, **overrides):
    values = dict(
        id=uuid.uuid4(),
        case_reference="PL-7QG4M2",
        company_id=company_id,
        customer_user_id=uuid.uuid4(),
        owner_user_id=uuid.uuid4(),
        reviewer_user_id=None,
        title="US buyer July shipment",
        status="draft",
        payment_arrangement="open_account",
        service_package_id="proofline_standard",
        recommended_decision=None,
        final_decision=None,
        currency="USD",
        amount=Decimal("125000.00"),
        origin_country="BD",
        destination_country="US",
        shipment_date=None,
        expected_payment_date=None,
        payment_terms="Net 60 after buyer invoice approval",
        transaction_details={"purchase_order_number": "PO-1007"},
        source_lcopilot_session_id=None,
        final_report_id=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    values.update(overrides)
    return SimpleNamespace(**values)


class _Repo:
    def __init__(self, db):
        self.db = db
        self.calls = []
        self.case = db.case

    def create_case(self, *, company_id, customer_user_id, owner_user_id, values):
        self.calls.append(("create", company_id, values.copy()))
        self.case.company_id = company_id
        self.case.customer_user_id = customer_user_id
        self.case.owner_user_id = owner_user_id
        for key, value in values.items():
            setattr(self.case, key, value)
        return self.case

    def list_cases(self, *, company_id, status=None, offset=0, limit=50):
        self.calls.append(("list", company_id, status, offset, limit))
        return [self.case], 1

    def get_case(self, *, company_id, case_id):
        self.calls.append(("get", company_id, case_id))
        if company_id != self.case.company_id or case_id != self.case.id:
            return None
        return self.case

    def update_case(self, trade_case, *, values):
        self.calls.append(("update", trade_case.id, values.copy()))
        for key, value in values.items():
            setattr(trade_case, key, value)
        return trade_case

    def summary_counts(self, *, company_id, case_id):
        assert company_id == self.case.company_id
        return 0, {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}

    def customer_snapshot(self, *, company_id, case_id):
        assert company_id == self.case.company_id
        assert case_id == self.case.id
        now = datetime.now(timezone.utc)
        return {
            "parties": [SimpleNamespace(
                id=uuid.uuid4(), role="buyer", name="US Buyer Inc", country_code="US",
                identifiers={"buyer_code": "B-1"},
            )],
            "checks": [SimpleNamespace(
                id=uuid.uuid4(), module="sanctions", state="clear", applicable=True,
                applicability_reason="Parties are present", source_record_type="screening",
                source_record_id="SCR-1", result_summary={"summary": "No matches found"},
                completed_at=now,
            )],
            "findings": [],
            "actions": [],
            "decisions": [],
        }


class _Db:
    def __init__(self, case):
        self.case = case
        self.commits = 0
        self.rollbacks = 0

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def refresh(self, _value):
        return None


def test_create_list_get_and_update_use_authenticated_company(monkeypatch):
    company_id = uuid.uuid4()
    user = SimpleNamespace(id=uuid.uuid4(), company_id=company_id, role="exporter")
    db = _Db(_case(company_id))
    repositories = []

    def repo_factory(bound_db):
        repo = _Repo(bound_db)
        repositories.append(repo)
        return repo

    monkeypatch.setattr(router_module, "ProoflineRepository", repo_factory)
    monkeypatch.setattr(router_module, "_audit_action", lambda **_kwargs: None)
    monkeypatch.setattr(router_module, "ensure_case_write_access", lambda *_args, **_kwargs: None)

    created = asyncio.run(
        router_module.create_trade_case(
            payload=TradeCaseCreate(
                title="Open account shipment",
                payment_arrangement="open_account",
                origin_country="BD",
                destination_country="US",
                currency="USD",
                amount=Decimal("125000.00"),
            ),
            current_user=user,
            db=db,
        )
    )
    listed = asyncio.run(
        router_module.list_trade_cases(
            status_filter=None, offset=0, limit=50, current_user=user, db=db
        )
    )
    fetched = asyncio.run(
        router_module.get_trade_case(created.id, current_user=user, db=db)
    )
    updated = asyncio.run(
        router_module.update_trade_case(
            created.id,
            payload=TradeCaseUpdate(payment_terms="Net 60 after approval"),
            current_user=user,
            db=db,
        )
    )

    assert created.payment_arrangement.value == "open_account"
    assert listed.total == 1
    assert fetched.id == created.id
    assert updated.payment_terms == "Net 60 after approval"
    assert all(
        call[1] == company_id
        for repo in repositories
        for call in repo.calls
        if call[0] in {"create", "list", "get"}
    )


def test_viewer_cannot_create_or_update(monkeypatch):
    company_id = uuid.uuid4()
    user = SimpleNamespace(id=uuid.uuid4(), company_id=company_id, role="viewer")
    db = _Db(_case(company_id))
    monkeypatch.setattr(router_module, "ProoflineRepository", _Repo)

    def deny(*_args, **_kwargs):
        raise HTTPException(status_code=403, detail="Read-only Proofline access")

    monkeypatch.setattr(router_module, "ensure_case_write_access", deny)

    with pytest.raises(HTTPException) as create_error:
        asyncio.run(
            router_module.create_trade_case(
                payload=TradeCaseCreate(
                    title="Not allowed",
                    payment_arrangement="letter_of_credit",
                ),
                current_user=user,
                db=db,
            )
        )
    assert create_error.value.status_code == 403


def test_case_payload_does_not_expose_internal_review_fields(monkeypatch):
    company_id = uuid.uuid4()
    user = SimpleNamespace(id=uuid.uuid4(), company_id=company_id, role="exporter")
    db = _Db(
        _case(
            company_id,
            internal_notes="Do not expose",
            sensitive_screening_payload={"matched_record": "restricted"},
        )
    )
    monkeypatch.setattr(router_module, "ProoflineRepository", _Repo)

    response = asyncio.run(
        router_module.get_trade_case(db.case.id, current_user=user, db=db)
    )
    serialized = response.model_dump()

    assert "internal_notes" not in serialized
    assert "sensitive_screening_payload" not in serialized


def test_case_detail_contains_tenant_scoped_customer_snapshot(monkeypatch):
    company_id = uuid.uuid4()
    user = SimpleNamespace(id=uuid.uuid4(), company_id=company_id, role="exporter")
    db = _Db(_case(company_id))
    monkeypatch.setattr(router_module, "ProoflineRepository", _Repo)
    monkeypatch.setattr(router_module, "list_case_documents", lambda *_args, **_kwargs: [])

    response = asyncio.run(
        router_module.get_trade_case(db.case.id, current_user=user, db=db)
    )

    assert response.parties[0].name == "US Buyer Inc"
    assert response.checks[0].module == "sanctions"
    assert response.checks[0].state == "clear"
    assert response.findings == []
    assert response.actions == []
    assert response.decision_history == []
    assert response.documents == []
