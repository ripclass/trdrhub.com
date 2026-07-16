"""Proofline associations for existing TRDRHub Document records."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Document, TradeCase, TradeCaseDocument, ValidationSession


class ProoflineDocumentAccessError(PermissionError):
    """The source document is not owned by the case tenant/actor."""


class DuplicateCaseDocument(ValueError):
    """The evidence hash or logical document version already exists."""


def associate_document(
    db: Session,
    *,
    trade_case: TradeCase,
    company_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    document_id: uuid.UUID,
    logical_key: str,
    document_type: str,
    content_hash: Optional[str] = None,
    supersedes_id: Optional[uuid.UUID] = None,
    correction_round: int = 0,
) -> TradeCaseDocument:
    """Attach one owned Document, optionally as a successor version.

    The original Document is never changed.  The caller owns commit/rollback.
    Legacy upload sessions without a company remain associable only by their
    original user, whose authenticated company is the target case company.
    """
    if trade_case.company_id != company_id:
        raise ProoflineDocumentAccessError("Trade case does not belong to the company")
    if not logical_key.strip() or not document_type.strip():
        raise ValueError("Logical key and document type are required")
    if correction_round < 0:
        raise ValueError("Correction round cannot be negative")
    if content_hash is not None:
        normalized_hash = content_hash.strip().lower()
        if len(normalized_hash) != 64 or any(ch not in "0123456789abcdef" for ch in normalized_hash):
            raise ValueError("Content hash must be a SHA-256 hex digest")
    else:
        normalized_hash = None

    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.deleted_at.is_(None))
        .first()
    )
    if document is None:
        raise ProoflineDocumentAccessError("Document is not available")
    source_session = (
        db.query(ValidationSession)
        .filter(
            ValidationSession.id == document.validation_session_id,
            ValidationSession.deleted_at.is_(None),
        )
        .first()
    )
    owned = source_session is not None and (
        source_session.company_id == company_id
        or (source_session.company_id is None and source_session.user_id == actor_user_id)
    )
    if not owned:
        raise ProoflineDocumentAccessError("Document is not available")

    associations = (
        db.query(TradeCaseDocument)
        .filter(
            TradeCaseDocument.company_id == company_id,
            TradeCaseDocument.trade_case_id == trade_case.id,
        )
        .all()
    )
    for existing in associations:
        if existing.document_id == document_id:
            return existing
        existing_hash = (existing.evidence_metadata or {}).get("sha256")
        if normalized_hash and existing_hash == normalized_hash:
            raise DuplicateCaseDocument("This file is already attached to the trade case")

    previous = None
    if supersedes_id is not None:
        previous = next((item for item in associations if item.id == supersedes_id), None)
        if previous is None or not previous.is_current:
            raise ProoflineDocumentAccessError("The superseded document version is not available")
        if previous.logical_key != logical_key:
            raise ValueError("A correction must retain the original logical document key")
        if correction_round <= previous.correction_round:
            raise ValueError("A correction must advance the correction round")
        version_number = previous.version_number + 1
    else:
        current_same_key = next(
            (item for item in associations if item.logical_key == logical_key and item.is_current),
            None,
        )
        if current_same_key is not None:
            raise DuplicateCaseDocument(
                "This document slot already has a current version; identify the version being corrected"
            )
        version_number = 1

    if previous is not None:
        previous.is_current = False

    association = TradeCaseDocument(
        id=uuid.uuid4(),
        company_id=company_id,
        trade_case_id=trade_case.id,
        document_id=document.id,
        logical_key=logical_key.strip(),
        document_type=document_type.strip(),
        version_number=version_number,
        supersedes_id=previous.id if previous is not None else None,
        correction_round=correction_round,
        is_current=True,
        evidence_metadata={"sha256": normalized_hash} if normalized_hash else {},
        uploaded_by_user_id=actor_user_id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(association)
    return association


def list_case_documents(
    db: Session, *, company_id: uuid.UUID, trade_case_id: uuid.UUID
) -> list[TradeCaseDocument]:
    return (
        db.query(TradeCaseDocument)
        .filter(
            TradeCaseDocument.company_id == company_id,
            TradeCaseDocument.trade_case_id == trade_case_id,
        )
        .order_by(TradeCaseDocument.logical_key.asc(), TradeCaseDocument.version_number.desc())
        .all()
    )


__all__ = [
    "DuplicateCaseDocument",
    "ProoflineDocumentAccessError",
    "associate_document",
    "list_case_documents",
]

