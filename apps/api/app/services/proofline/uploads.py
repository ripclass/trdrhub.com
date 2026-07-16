"""Proofline document intake built on TRDRHub storage, OCR, and Document models."""

from __future__ import annotations

import hashlib
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.models import (
    Document,
    DocumentType,
    SessionStatus,
    TradeCase,
    TradeCaseDocument,
    User,
    ValidationSession,
    WorkflowType,
)
from app.services import DocumentAIService, S3Service
from app.services.document_intelligence import get_doc_type_classifier
from app.services.proofline.documents import associate_document
from app.utils.file_validation import detect_file_type_from_content, validate_upload_file


DEFAULT_MAX_UPLOAD_BYTES = int(os.getenv("PROOFLINE_MAX_UPLOAD_BYTES", str(25 * 1024 * 1024)))


class ProoflineUploadError(ValueError):
    """A customer-safe document intake failure."""


def validate_case_upload(
    content: bytes,
    *,
    filename: str,
    content_type: Optional[str],
    max_bytes: int = DEFAULT_MAX_UPLOAD_BYTES,
) -> None:
    if not content:
        raise ProoflineUploadError("The uploaded file is empty")
    if len(content) > max_bytes:
        raise ProoflineUploadError(
            f"The file exceeds the maximum upload size of {max_bytes // (1024 * 1024)} MB"
        )
    header = content[:16]
    valid, message = validate_upload_file(
        header, filename=filename, content_type=content_type
    )
    detected = detect_file_type_from_content(header)
    if not valid or detected is None:
        raise ProoflineUploadError(
            message or "The file content does not match a supported PDF or image format"
        )
    if content_type and detected != content_type:
        raise ProoflineUploadError(
            f"The file content does not match the declared type {content_type}"
        )


def choose_case_document_type(
    *,
    ocr_text: str,
    filename: str,
    declared_type: Optional[str],
    classifier=None,
) -> tuple[str, dict[str, Any]]:
    classifier = classifier or get_doc_type_classifier()
    try:
        fallback = DocumentType(declared_type) if declared_type else DocumentType.SUPPORTING_DOCUMENT
    except ValueError:
        fallback = DocumentType.SUPPORTING_DOCUMENT
    result = classifier.classify(text=ocr_text, filename=filename, fallback_type=fallback)
    suggested_type = result.document_type.value
    chosen_type = suggested_type if result.is_reliable else (declared_type or suggested_type)
    return chosen_type, {
        "suggested_type": suggested_type,
        "declared_type": declared_type,
        "confidence": float(result.confidence),
        "confidence_level": result.confidence_level.value,
        "is_reliable": bool(result.is_reliable),
        "reasoning": result.reasoning,
        "matched_patterns": list(result.matched_patterns),
    }


def _document_session(db: Session, *, trade_case: TradeCase, user: User) -> ValidationSession:
    if trade_case.document_session_id is not None:
        existing = (
            db.query(ValidationSession)
            .filter(
                ValidationSession.id == trade_case.document_session_id,
                ValidationSession.company_id == trade_case.company_id,
                ValidationSession.deleted_at.is_(None),
            )
            .first()
        )
        if existing is None:
            raise ProoflineUploadError("The case document workspace is unavailable")
        return existing

    session = ValidationSession(
        id=uuid.uuid4(),
        user_id=user.id,
        company_id=trade_case.company_id,
        status=SessionStatus.PROCESSING.value,
        workflow_type=WorkflowType.PROOFLINE.value,
        ocr_provider="google_documentai",
        processing_started_at=datetime.now(timezone.utc),
    )
    db.add(session)
    db.flush()
    trade_case.document_session_id = session.id
    return session


async def ingest_case_document(
    db: Session,
    *,
    trade_case: TradeCase,
    user: User,
    file: UploadFile,
    logical_key: str,
    declared_document_type: Optional[str] = None,
    supersedes_id: Optional[uuid.UUID] = None,
    correction_round: int = 0,
    s3_service=None,
    ocr_service=None,
) -> TradeCaseDocument:
    """Store, extract, classify, and version one Proofline document.

    The caller owns the database transaction. S3 and OCR implementations are
    the same services used by LCopilot.
    """
    filename = (file.filename or "document").strip()
    content = await file.read()
    validate_case_upload(
        content,
        filename=filename,
        content_type=file.content_type,
    )
    content_hash = hashlib.sha256(content).hexdigest()
    session = _document_session(db, trade_case=trade_case, user=user)
    storage = s3_service or S3Service()
    ocr = ocr_service or DocumentAIService()

    initial_type = declared_document_type or DocumentType.SUPPORTING_DOCUMENT.value
    await file.seek(0)
    upload = await storage.upload_file(file, session.id, initial_type)
    result = await ocr.process_file(
        content,
        file.content_type or "application/octet-stream",
        document_hash=content_hash,
    )
    if not result.get("success"):
        raise ProoflineUploadError("Document extraction is temporarily unavailable")

    ocr_text = result.get("extracted_text") or ""
    document_type, classification = choose_case_document_type(
        ocr_text=ocr_text,
        filename=filename,
        declared_type=declared_document_type,
    )
    extracted_fields = result.get("extracted_fields") or {}
    if not isinstance(extracted_fields, dict):
        extracted_fields = {}
    extracted_fields = {
        **extracted_fields,
        "extraction_status": "completed",
        "proofline_classification": classification,
    }
    document = Document(
        id=uuid.uuid4(),
        validation_session_id=session.id,
        document_type=document_type,
        original_filename=upload["original_filename"],
        s3_key=upload["s3_key"],
        file_size=upload["file_size"],
        content_type=upload["content_type"],
        ocr_text=ocr_text,
        ocr_confidence=result.get("overall_confidence"),
        ocr_processed_at=datetime.now(timezone.utc),
        extracted_fields=extracted_fields,
    )
    db.add(document)
    db.flush()
    return associate_document(
        db,
        trade_case=trade_case,
        company_id=trade_case.company_id,
        actor_user_id=user.id,
        document_id=document.id,
        logical_key=logical_key,
        document_type=document_type,
        content_hash=content_hash,
        supersedes_id=supersedes_id,
        correction_round=correction_round,
    )


__all__ = [
    "DEFAULT_MAX_UPLOAD_BYTES",
    "ProoflineUploadError",
    "choose_case_document_type",
    "ingest_case_document",
    "validate_case_upload",
]
