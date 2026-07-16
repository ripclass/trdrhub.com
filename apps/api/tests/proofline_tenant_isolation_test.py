"""Proofline repository lookups must always include the authenticated tenant."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

from app.models import TradeCase
from app.repositories.proofline import ProoflineRepository


class _Query:
    def __init__(self, rows):
        self.rows = list(rows)
        self.criteria = []

    def filter(self, *criteria):
        self.criteria.extend(criteria)
        for criterion in criteria:
            column = getattr(getattr(criterion, "left", None), "name", None)
            operator = getattr(getattr(criterion, "operator", None), "__name__", "")
            expected = getattr(getattr(criterion, "right", None), "value", None)
            if column and operator == "eq":
                self.rows = [
                    row for row in self.rows if getattr(row, column, None) == expected
                ]
            elif column == "deleted_at" and operator == "is_":
                self.rows = [row for row in self.rows if row.deleted_at is None]
        return self

    def first(self):
        return self.rows[0] if self.rows else None


class _Db:
    def __init__(self, rows):
        self.rows = rows
        self.last_query = None

    def query(self, model):
        assert model is TradeCase
        self.last_query = _Query(self.rows)
        return self.last_query


def test_get_case_rejects_cross_tenant_id_even_when_case_uuid_is_known():
    owner_company = uuid.uuid4()
    attacker_company = uuid.uuid4()
    case_id = uuid.uuid4()
    row = SimpleNamespace(
        id=case_id,
        company_id=owner_company,
        deleted_at=None,
    )
    db = _Db([row])
    repository = ProoflineRepository(db)

    assert repository.get_case(company_id=attacker_company, case_id=case_id) is None
    criterion_columns = {
        getattr(getattr(item, "left", None), "name", None)
        for item in db.last_query.criteria
    }
    assert {"id", "company_id", "deleted_at"} <= criterion_columns


def test_get_case_returns_only_matching_tenant_case():
    company_id = uuid.uuid4()
    case_id = uuid.uuid4()
    row = SimpleNamespace(id=case_id, company_id=company_id, deleted_at=None)
    repository = ProoflineRepository(_Db([row]))

    assert repository.get_case(company_id=company_id, case_id=case_id) is row

