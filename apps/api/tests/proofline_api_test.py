"""Proofline customer case API behavior without application-wide bootstrapping."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import BackgroundTasks, HTTPException

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

    def create_party(self, *, company_id, case_id, values):
        self.calls.append(("create_party", company_id, case_id, values.copy()))
        return SimpleNamespace(id=uuid.uuid4(), company_id=company_id, trade_case_id=case_id, **values)

    def delete_party(self, *, company_id, case_id, party_id):
        self.calls.append(("delete_party", company_id, case_id, party_id))
        return True


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


def test_parties_are_created_and_deleted_inside_authenticated_company(monkeypatch):
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

    created = asyncio.run(router_module.create_trade_case_party(
        db.case.id,
        payload=router_module.TradeCasePartyCreate(
            role="buyer", name="US Buyer Inc", country_code="us",
            identifiers={"buyer_code": "B-1"},
        ),
        current_user=user,
        db=db,
    ))
    asyncio.run(router_module.delete_trade_case_party(
        db.case.id, created.id, current_user=user, db=db,
    ))

    assert created.country_code == "US"
    assert all(
        call[1] == company_id
        for repository in repositories
        for call in repository.calls
        if call[0] in {"get", "create_party", "delete_party"}
    )


def test_submit_validates_snapshot_transitions_and_enqueues_processing(monkeypatch):
    company_id = uuid.uuid4()
    user = SimpleNamespace(id=uuid.uuid4(), company_id=company_id, role="exporter")
    db = _Db(_case(company_id))
    background = BackgroundTasks()
    monkeypatch.setattr(router_module, "ProoflineRepository", _Repo)
    monkeypatch.setattr(router_module, "ensure_case_write_access", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(router_module, "_audit_action", lambda **_kwargs: None)
    monkeypatch.setattr(
        router_module,
        "load_case_context",
        lambda *_args, **_kwargs: {
            "parties": [{"name": "Buyer"}, {"name": "Seller"}],
            "documents": {"commercial_invoice": {"document_id": "doc-1"}},
            "payment_arrangement": "open_account",
        },
    )

    def transition(_db, trade_case, target, **_kwargs):
        trade_case.status = target.value

    monkeypatch.setattr(router_module, "transition_case", transition)

    response = asyncio.run(
        router_module.submit_trade_case(
            db.case.id,
            background_tasks=background,
            current_user=user,
            db=db,
        )
    )

    assert response.status.value == "submitted"
    assert db.commits == 1
    assert len(background.tasks) == 1


def test_submit_stops_at_payment_gate_when_proofline_checkout_is_live(monkeypatch):
    company_id = uuid.uuid4()
    user = SimpleNamespace(id=uuid.uuid4(), company_id=company_id, role="exporter")
    db = _Db(_case(company_id))
    background = BackgroundTasks()
    monkeypatch.setattr(router_module, "ProoflineRepository", _Repo)
    monkeypatch.setattr(router_module, "ensure_case_write_access", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(router_module, "_audit_action", lambda **_kwargs: None)
    monkeypatch.setattr(router_module, "is_proofline_checkout_enabled", lambda: True)
    monkeypatch.setattr(router_module, "quote_for_case", lambda *_args: (object(), object()))
    monkeypatch.setattr(
        router_module,
        "load_case_context",
        lambda *_args, **_kwargs: {
            "parties": [{"name": "Buyer"}, {"name": "Seller"}],
            "documents": {"commercial_invoice": {"document_id": "doc-1"}},
            "payment_arrangement": "open_account",
        },
    )

    def transition(_db, trade_case, target, **_kwargs):
        trade_case.status = target.value

    monkeypatch.setattr(router_module, "transition_case", transition)

    response = asyncio.run(
        router_module.submit_trade_case(
            db.case.id,
            background_tasks=background,
            current_user=user,
            db=db,
        )
    )

    assert response.status.value == "awaiting_payment"
    assert db.case.payment_status == "pending"
    assert not background.tasks


def test_submit_rejects_incomplete_case_without_enqueuing(monkeypatch):
    company_id = uuid.uuid4()
    user = SimpleNamespace(id=uuid.uuid4(), company_id=company_id, role="exporter")
    db = _Db(_case(company_id))
    background = BackgroundTasks()
    monkeypatch.setattr(router_module, "ProoflineRepository", _Repo)
    monkeypatch.setattr(router_module, "ensure_case_write_access", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        router_module,
        "load_case_context",
        lambda *_args, **_kwargs: {
            "parties": [{"name": "Buyer"}],
            "documents": {},
            "payment_arrangement": "open_account",
        },
    )

    with pytest.raises(HTTPException) as error:
        asyncio.run(
            router_module.submit_trade_case(
                db.case.id,
                background_tasks=background,
                current_user=user,
                db=db,
            )
        )

    assert error.value.status_code == 422
    assert not background.tasks
