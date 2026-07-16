"""Proofline evidence association, tenant ownership, and immutable versions."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from app.models import Document, TradeCaseDocument, ValidationSession
from app.services.proofline.documents import (
    DuplicateCaseDocument,
    ProoflineDocumentAccessError,
    associate_document,
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
            elif column == "deleted_at" and operator == "is_":
                self.rows = [row for row in self.rows if getattr(row, "deleted_at", None) is None]
        return self

    def order_by(self, *_args):
        self.rows.sort(key=lambda row: getattr(row, "version_number", 0), reverse=True)
        return self

    def first(self):
        return self.rows[0] if self.rows else None

    def all(self):
        return list(self.rows)


class _Db:
    def __init__(self, documents, sessions, associations=None):
        self.rows = {
            Document: list(documents),
            ValidationSession: list(sessions),
            TradeCaseDocument: list(associations or []),
        }
        self.added = []

    def query(self, model):
        return _Query(self.rows.get(model, []))

    def add(self, row):
        self.added.append(row)
        self.rows.setdefault(type(row), []).append(row)


def _source(company_id, user_id):
    session_id = uuid.uuid4()
    document_id = uuid.uuid4()
    session = SimpleNamespace(
        id=session_id,
        company_id=company_id,
        user_id=user_id,
        deleted_at=None,
    )
    document = SimpleNamespace(
        id=document_id,
        validation_session_id=session_id,
        document_type="commercial_invoice",
        original_filename="invoice.pdf",
        deleted_at=None,
    )
    return session, document


def _case(company_id):
    return SimpleNamespace(id=uuid.uuid4(), company_id=company_id)


def test_associates_existing_owned_document_without_changing_document_id():
    company_id = uuid.uuid4()
    user_id = uuid.uuid4()
    session, document = _source(company_id, user_id)
    db = _Db([document], [session])

    association = associate_document(
        db,
        trade_case=_case(company_id),
        company_id=company_id,
        actor_user_id=user_id,
        document_id=document.id,
        logical_key="commercial_invoice",
        document_type="commercial_invoice",
        content_hash="a" * 64,
    )

    assert association.document_id == document.id
    assert association.version_number == 1
    assert association.is_current is True
    assert association.evidence_metadata["sha256"] == "a" * 64


def test_cross_tenant_source_document_is_rejected():
    owner_company = uuid.uuid4()
    attacker_company = uuid.uuid4()
    user_id = uuid.uuid4()
    session, document = _source(owner_company, uuid.uuid4())
    db = _Db([document], [session])

    with pytest.raises(ProoflineDocumentAccessError):
        associate_document(
            db,
            trade_case=_case(attacker_company),
            company_id=attacker_company,
            actor_user_id=user_id,
            document_id=document.id,
            logical_key="commercial_invoice",
            document_type="commercial_invoice",
            content_hash="b" * 64,
        )

    assert db.added == []


def test_correction_creates_next_version_and_preserves_original():
    company_id = uuid.uuid4()
    user_id = uuid.uuid4()
    first_session, first_document = _source(company_id, user_id)
    second_session, second_document = _source(company_id, user_id)
    trade_case = _case(company_id)
    original = TradeCaseDocument(
        id=uuid.uuid4(),
        company_id=company_id,
        trade_case_id=trade_case.id,
        document_id=first_document.id,
        logical_key="commercial_invoice",
        document_type="commercial_invoice",
        version_number=1,
        correction_round=0,
        is_current=True,
        evidence_metadata={"sha256": "a" * 64},
    )
    db = _Db(
        [first_document, second_document],
        [first_session, second_session],
        [original],
    )

    corrected = associate_document(
        db,
        trade_case=trade_case,
        company_id=company_id,
        actor_user_id=user_id,
        document_id=second_document.id,
        logical_key="commercial_invoice",
        document_type="commercial_invoice",
        content_hash="b" * 64,
        supersedes_id=original.id,
        correction_round=1,
    )

    assert original.is_current is False
    assert original.document_id == first_document.id
    assert corrected.version_number == 2
    assert corrected.supersedes_id == original.id
    assert corrected.correction_round == 1


def test_duplicate_hash_is_rejected_before_adding_another_case_document():
    company_id = uuid.uuid4()
    user_id = uuid.uuid4()
    session, document = _source(company_id, user_id)
    trade_case = _case(company_id)
    existing = TradeCaseDocument(
        id=uuid.uuid4(),
        company_id=company_id,
        trade_case_id=trade_case.id,
        document_id=uuid.uuid4(),
        logical_key="purchase_order",
        document_type="purchase_order",
        version_number=1,
        correction_round=0,
        is_current=True,
        evidence_metadata={"sha256": "c" * 64},
    )
    db = _Db([document], [session], [existing])

    with pytest.raises(DuplicateCaseDocument):
        associate_document(
            db,
            trade_case=trade_case,
            company_id=company_id,
            actor_user_id=user_id,
            document_id=document.id,
            logical_key="commercial_invoice",
            document_type="commercial_invoice",
            content_hash="c" * 64,
        )

    assert db.added == []

