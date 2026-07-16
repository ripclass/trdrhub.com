"""Tenant-scoped repository for Proofline customer case operations."""

from __future__ import annotations

import secrets
import uuid
from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import (
    Document,
    ProoflineFinding,
    RemediationAction,
    TradeCase,
    TradeCaseCheckRun,
    TradeCaseDecision,
    TradeCaseDocument,
    TradeCaseParty,
)


def new_case_reference() -> str:
    """Return a non-sequential, customer-safe case reference."""
    return f"PL-{secrets.token_hex(5).upper()}"


class ProoflineRepository:
    """Proofline queries whose public entry points always require a tenant ID."""

    def __init__(self, db: Session):
        self.db = db

    def create_case(
        self,
        *,
        company_id: uuid.UUID,
        customer_user_id: uuid.UUID,
        owner_user_id: uuid.UUID,
        values: dict[str, Any],
    ) -> TradeCase:
        trade_case = TradeCase(
            id=uuid.uuid4(),
            case_reference=new_case_reference(),
            company_id=company_id,
            customer_user_id=customer_user_id,
            owner_user_id=owner_user_id,
            **values,
        )
        self.db.add(trade_case)
        return trade_case

    def list_cases(
        self,
        *,
        company_id: uuid.UUID,
        status: Optional[str] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[TradeCase], int]:
        query = self.db.query(TradeCase).filter(
            TradeCase.company_id == company_id,
            TradeCase.deleted_at.is_(None),
        )
        if status is not None:
            query = query.filter(TradeCase.status == status)
        total = query.count()
        rows = (
            query.order_by(TradeCase.updated_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return rows, total

    def get_case(self, *, company_id: uuid.UUID, case_id: uuid.UUID) -> Optional[TradeCase]:
        return (
            self.db.query(TradeCase)
            .filter(
                TradeCase.id == case_id,
                TradeCase.company_id == company_id,
                TradeCase.deleted_at.is_(None),
            )
            .first()
        )

    def update_case(self, trade_case: TradeCase, *, values: dict[str, Any]) -> TradeCase:
        for field, value in values.items():
            setattr(trade_case, field, value)
        return trade_case

    def summary_counts(
        self, *, company_id: uuid.UUID, case_id: uuid.UUID
    ) -> tuple[int, dict[str, int]]:
        document_count = (
            self.db.query(func.count(TradeCaseDocument.id))
            .filter(
                TradeCaseDocument.company_id == company_id,
                TradeCaseDocument.trade_case_id == case_id,
                TradeCaseDocument.is_current.is_(True),
            )
            .scalar()
            or 0
        )
        rows = (
            self.db.query(ProoflineFinding.severity, func.count(ProoflineFinding.id))
            .filter(
                ProoflineFinding.company_id == company_id,
                ProoflineFinding.trade_case_id == case_id,
                ProoflineFinding.visibility == "customer",
            )
            .group_by(ProoflineFinding.severity)
            .all()
        )
        counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        for severity, count in rows:
            counts[str(severity)] = int(count)
        return int(document_count), counts

    def customer_snapshot(self, *, company_id: uuid.UUID, case_id: uuid.UUID) -> dict[str, list]:
        """Load only customer-visible, tenant-scoped case children."""
        scope = {"company_id": company_id, "trade_case_id": case_id}
        parties = (
            self.db.query(TradeCaseParty)
            .filter_by(**scope)
            .order_by(TradeCaseParty.created_at.asc())
            .all()
        )
        documents = (
            self.db.query(TradeCaseDocument, Document)
            .join(Document, Document.id == TradeCaseDocument.document_id)
            .filter(
                TradeCaseDocument.company_id == company_id,
                TradeCaseDocument.trade_case_id == case_id,
            )
            .order_by(TradeCaseDocument.logical_key.asc(), TradeCaseDocument.version_number.desc())
            .all()
        )
        checks = (
            self.db.query(TradeCaseCheckRun)
            .filter_by(**scope)
            .order_by(TradeCaseCheckRun.created_at.asc())
            .all()
        )
        findings = (
            self.db.query(ProoflineFinding)
            .filter(
                ProoflineFinding.company_id == company_id,
                ProoflineFinding.trade_case_id == case_id,
                ProoflineFinding.visibility == "customer",
            )
            .order_by(ProoflineFinding.created_at.asc())
            .all()
        )
        actions = (
            self.db.query(RemediationAction)
            .join(ProoflineFinding, ProoflineFinding.id == RemediationAction.finding_id)
            .filter(
                RemediationAction.company_id == company_id,
                RemediationAction.trade_case_id == case_id,
                ProoflineFinding.company_id == company_id,
                ProoflineFinding.visibility == "customer",
            )
            .order_by(RemediationAction.created_at.asc())
            .all()
        )
        decisions = (
            self.db.query(TradeCaseDecision)
            .filter_by(**scope)
            .order_by(TradeCaseDecision.version_number.desc())
            .all()
        )
        return {
            "parties": parties,
            "documents": documents,
            "checks": checks,
            "findings": findings,
            "actions": actions,
            "decisions": decisions,
        }


__all__ = ["ProoflineRepository", "new_case_reference"]
