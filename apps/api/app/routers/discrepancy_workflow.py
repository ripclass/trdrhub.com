"""Discrepancy resolution + re-papering API — Phase A2.

Two routers in one module. The discrepancy router handles
authenticated user actions; the re-papering router handles
token-authed recipient flows (no JWT required for the upload step).

Endpoints:

  /api/discrepancies/{id}/comment       POST  add a comment
  /api/discrepancies/{id}/comments      GET   thread
  /api/discrepancies/{id}/resolve       POST  apply terminal action
  /api/discrepancies/{id}/assign        POST  set owner
  /api/discrepancies/{id}/repaper       POST  create re-papering request

  /api/repaper/{token}                  GET   recipient view (no auth)
  /api/repaper/{token}/comment          POST  recipient adds a comment
  /api/repaper/{token}/upload           POST  recipient uploads corrected docs
  /api/repaper/{token}/cancel           POST  requester (auth) cancels

All ownership checks scope by the parent ``ValidationSession.user_id``
unless the caller has admin privileges.
"""

from __future__ import annotations

import logging
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from ..config import settings
from ..core.security import get_current_user
from ..database import get_db
from ..models import Discrepancy, User, ValidationSession
from ..models.discrepancy_workflow import (
    DiscrepancyComment,
    DiscrepancyState,
    RepaperingRequest,
    RepaperingState,
)
from ..services.discrepancy_workflow import (
    InvalidDiscrepancyTransition,
    InvalidRepaperingTransition,
    add_recipient_comment,
    add_user_comment,
    assign_discrepancy_owner,
    create_repapering_request,
    transition_discrepancy,
    transition_repapering,
)
from ..services.email import send_email
from ..services.repaper_revalidate import schedule_revalidation

logger = logging.getLogger(__name__)


discrepancy_router = APIRouter(prefix="/api/discrepancies", tags=["discrepancies"])
repaper_router = APIRouter(prefix="/api/repaper", tags=["re-papering"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class CommentCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=4000)


class CommentRead(BaseModel):
    id: UUID
    body: str
    source: str
    author_user_id: Optional[UUID]
    author_email: Optional[str]
    author_display_name: Optional[str]
    created_at: datetime


class DiscrepancyResolveRequest(BaseModel):
    action: str = Field(
        ...,
        description="One of accept / reject / waive / resolved",
    )
    evidence_session_id: Optional[UUID] = None
    note: Optional[str] = Field(None, max_length=2000)


class AssignRequest(BaseModel):
    owner_user_id: UUID


class DiscrepancyRead(BaseModel):
    id: UUID
    validation_session_id: UUID
    state: str
    severity: str
    description: str
    owner_user_id: Optional[UUID]
    acknowledged_at: Optional[datetime]
    resolved_at: Optional[datetime]
    resolution_action: Optional[str]
    resolution_evidence_session_id: Optional[UUID]


class RepaperCreateRequest(BaseModel):
    recipient_email: EmailStr
    recipient_display_name: Optional[str] = Field(None, max_length=128)
    message: Optional[str] = Field(None, max_length=2000)


class RepaperRead(BaseModel):
    id: UUID
    discrepancy_id: UUID
    recipient_email: str
    recipient_display_name: Optional[str]
    state: str
    message: Optional[str]
    access_token: Optional[str]  # only returned on create
    replacement_session_id: Optional[UUID]
    created_at: datetime
    opened_at: Optional[datetime]
    submitted_at: Optional[datetime]
    resolved_at: Optional[datetime]


class RepaperRecipientView(BaseModel):
    """Recipient-safe view (no token leakage, no internal IDs).

    The recipient sees: who asked, what's required, what state we're
    in. Does NOT see other discrepancies or session data.
    """

    discrepancy_description: str
    requester_email: Optional[str]
    message: Optional[str]
    state: str
    submitted_at: Optional[datetime]


class RepaperCommentRequest(BaseModel):
    body: str = Field(..., min_length=1, max_length=4000)
    author_email: EmailStr
    author_display_name: Optional[str] = Field(None, max_length=128)


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------


def _load_owned_discrepancy(
    db: Session, current_user: User, discrepancy_id: UUID
) -> Discrepancy:
    """Fetch a discrepancy that the caller owns via the parent session.

    404 (not 403) for foreign discrepancies — don't leak existence.
    """
    discrepancy = (
        db.query(Discrepancy)
        .filter(Discrepancy.id == discrepancy_id)
        .first()
    )
    if discrepancy is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Discrepancy not found")
    session = (
        db.query(ValidationSession)
        .filter(ValidationSession.id == discrepancy.validation_session_id)
        .first()
    )
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Discrepancy not found")
    is_owner = str(session.user_id) == str(current_user.id)
    is_admin = (current_user.role or "").lower() in ("admin", "bank_admin")
    if not (is_owner or is_admin):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Discrepancy not found")
    return discrepancy


def _load_repaper_by_token(db: Session, token: str) -> RepaperingRequest:
    request = (
        db.query(RepaperingRequest)
        .filter(RepaperingRequest.access_token == token)
        .first()
    )
    if request is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Re-papering request not found")
    if request.token_expires_at is not None:
        # Tokens may carry an expiry. Compare aware-vs-aware.
        if request.token_expires_at < datetime.now(timezone.utc):
            raise HTTPException(status.HTTP_410_GONE, "Re-papering link expired")
    return request


# ---------------------------------------------------------------------------
# Discrepancy endpoints (authenticated)
# ---------------------------------------------------------------------------


@discrepancy_router.post(
    "/{discrepancy_id}/comment",
    response_model=CommentRead,
    status_code=status.HTTP_201_CREATED,
)
async def post_discrepancy_comment(
    discrepancy_id: UUID,
    body: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    discrepancy = _load_owned_discrepancy(db, current_user, discrepancy_id)
    comment = add_user_comment(
        db, discrepancy, body=body.body, author_user_id=current_user.id
    )
    db.commit()
    db.refresh(comment)
    return CommentRead(
        id=comment.id,
        body=comment.body,
        source=comment.source,
        author_user_id=comment.author_user_id,
        author_email=comment.author_email,
        author_display_name=comment.author_display_name,
        created_at=comment.created_at,
    )


@discrepancy_router.get(
    "/{discrepancy_id}/comments",
    response_model=List[CommentRead],
)
async def list_discrepancy_comments(
    discrepancy_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    discrepancy = _load_owned_discrepancy(db, current_user, discrepancy_id)
    rows = (
        db.query(DiscrepancyComment)
        .filter(DiscrepancyComment.discrepancy_id == discrepancy.id)
        .order_by(DiscrepancyComment.created_at.asc())
        .all()
    )
    return [
        CommentRead(
            id=c.id,
            body=c.body,
            source=c.source,
            author_user_id=c.author_user_id,
            author_email=c.author_email,
            author_display_name=c.author_display_name,
            created_at=c.created_at,
        )
        for c in rows
    ]


_RESOLVE_ACTION_TO_STATE = {
    "accept": DiscrepancyState.ACCEPTED,
    "reject": DiscrepancyState.REJECTED,
    "waive": DiscrepancyState.WAIVED,
    "resolved": DiscrepancyState.RESOLVED,
}


@discrepancy_router.post(
    "/{discrepancy_id}/resolve",
    response_model=DiscrepancyRead,
)
async def resolve_discrepancy(
    discrepancy_id: UUID,
    body: DiscrepancyResolveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    target_state = _RESOLVE_ACTION_TO_STATE.get(body.action.lower())
    if target_state is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"action must be one of {sorted(_RESOLVE_ACTION_TO_STATE.keys())}",
        )
    discrepancy = _load_owned_discrepancy(db, current_user, discrepancy_id)
    try:
        transition_discrepancy(
            db,
            discrepancy,
            target_state,
            actor_user_id=current_user.id,
            resolution_action=body.action.lower(),
            resolution_evidence_session_id=body.evidence_session_id,
            system_comment=body.note or f"Resolution: {body.action.lower()}",
        )
    except InvalidDiscrepancyTransition as exc:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            {
                "code": "invalid_transition",
                "message": str(exc),
                "from_state": exc.from_state,
                "to_state": exc.to_state,
                "allowed_next_states": sorted(s.value for s in exc.allowed),
            },
        ) from exc
    db.commit()
    db.refresh(discrepancy)
    return _to_discrepancy_read(discrepancy)


@discrepancy_router.post(
    "/{discrepancy_id}/assign",
    response_model=DiscrepancyRead,
)
async def assign_discrepancy(
    discrepancy_id: UUID,
    body: AssignRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    discrepancy = _load_owned_discrepancy(db, current_user, discrepancy_id)
    assign_discrepancy_owner(
        db,
        discrepancy,
        owner_user_id=body.owner_user_id,
        actor_user_id=current_user.id,
    )
    db.commit()
    db.refresh(discrepancy)
    return _to_discrepancy_read(discrepancy)


@discrepancy_router.post(
    "/{discrepancy_id}/repaper",
    response_model=RepaperRead,
    status_code=status.HTTP_201_CREATED,
)
async def request_repapering(
    discrepancy_id: UUID,
    body: RepaperCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    discrepancy = _load_owned_discrepancy(db, current_user, discrepancy_id)
    request = create_repapering_request(
        db,
        discrepancy,
        requester_user_id=current_user.id,
        recipient_email=body.recipient_email,
        recipient_display_name=body.recipient_display_name,
        message=body.message,
    )
    db.commit()
    db.refresh(request)

    # Fire the recipient invitation email. Best-effort — return the
    # request either way so the caller can surface the share link
    # even if SMTP is unconfigured (dev) or the send transiently fails.
    _send_repaper_invitation_email(
        request=request,
        discrepancy=discrepancy,
        requester=current_user,
    )

    return _to_repaper_read(request, include_token=True)


def _send_repaper_invitation_email(
    *,
    request: RepaperingRequest,
    discrepancy: Discrepancy,
    requester: User,
) -> None:
    frontend = (settings.FRONTEND_URL or "").rstrip("/")
    recipient_link = f"{frontend}/repaper/{request.access_token}"
    requester_label = (
        getattr(requester, "full_name", None)
        or getattr(requester, "email", None)
        or "your counterparty"
    )
    short_desc = (discrepancy.description or "").strip()
    if len(short_desc) > 280:
        short_desc = short_desc[:277] + "..."
    custom_message = (request.message or "").strip()
    custom_block = (
        f"<blockquote style='margin:8px 0;padding:8px 12px;"
        f"border-left:3px solid #d4d4d8;color:#3f3f46;'>"
        f"{custom_message}</blockquote>"
        if custom_message
        else ""
    )
    html = f"""
    <p>Hello,</p>
    <p>{requester_label} has flagged a document that needs a correction
    and asked you to help fix it. The discrepancy:</p>
    <blockquote style='margin:8px 0;padding:8px 12px;
    border-left:3px solid #f59e0b;color:#1f2937;'>{short_desc or 'Re-papering request'}</blockquote>
    {custom_block}
    <p>Open the link below to review the issue and upload the corrected
    document(s). No account or login is required.</p>
    <p><a href='{recipient_link}' style='display:inline-block;padding:8px 14px;
    background:#0f172a;color:#fff;text-decoration:none;border-radius:6px;'>
    Open the request</a></p>
    <p style='color:#6b7280;font-size:12px;'>If the button does not work,
    paste this URL into your browser:<br/>{recipient_link}</p>
    <p style='color:#6b7280;font-size:12px;'>— TRDR Hub</p>
    """
    send_email(
        to=request.recipient_email,
        subject="Document correction request — TRDR Hub",
        html_body=html,
    )


# ---------------------------------------------------------------------------
# Re-papering endpoints (token-authed for recipient, JWT for requester)
# ---------------------------------------------------------------------------


@repaper_router.get(
    "/{token}",
    response_model=RepaperRecipientView,
)
async def view_repaper_request(
    token: str,
    db: Session = Depends(get_db),
):
    request = _load_repaper_by_token(db, token)
    discrepancy = (
        db.query(Discrepancy).filter(Discrepancy.id == request.discrepancy_id).first()
    )
    requester = (
        db.query(User).filter(User.id == request.requester_user_id).first()
        if request.requester_user_id
        else None
    )
    # Mark the request as opened on first GET if still pending.
    if request.state == RepaperingState.REQUESTED.value:
        try:
            transition_repapering(db, request, RepaperingState.IN_PROGRESS)
            db.commit()
        except InvalidRepaperingTransition:
            pass
    return RepaperRecipientView(
        discrepancy_description=(discrepancy.description if discrepancy else ""),
        requester_email=(requester.email if requester else None),
        message=request.message,
        state=request.state,
        submitted_at=request.submitted_at,
    )


@repaper_router.post(
    "/{token}/comment",
    response_model=CommentRead,
    status_code=status.HTTP_201_CREATED,
)
async def post_repaper_comment(
    token: str,
    body: RepaperCommentRequest,
    db: Session = Depends(get_db),
):
    request = _load_repaper_by_token(db, token)
    discrepancy = (
        db.query(Discrepancy).filter(Discrepancy.id == request.discrepancy_id).first()
    )
    if discrepancy is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Discrepancy not found")
    comment = add_recipient_comment(
        db,
        discrepancy,
        body=body.body,
        author_email=body.author_email,
        author_display_name=body.author_display_name,
    )
    db.commit()
    db.refresh(comment)
    return CommentRead(
        id=comment.id,
        body=comment.body,
        source=comment.source,
        author_user_id=None,
        author_email=comment.author_email,
        author_display_name=comment.author_display_name,
        created_at=comment.created_at,
    )


@repaper_router.post(
    "/{token}/upload",
    response_model=RepaperRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_repaper_files(
    token: str,
    background: BackgroundTasks,
    files: List[UploadFile] = File(..., description="Corrected document(s)"),
    db: Session = Depends(get_db),
):
    """Recipient uploads corrected docs.

    Persists files under
    ``<BULK_VALIDATE_STORAGE_DIR>/repaper/{request_id}/``, marks the
    request CORRECTED, and schedules a background re-validation. The
    revalidation runs the pipeline as the original requester, links
    the new ValidationSession via ``replacement_session_id``, and on a
    clean run (zero findings) auto-resolves the parent Discrepancy
    with the new session as evidence. See
    ``app/services/repaper_revalidate.py``.
    """
    if not files:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "At least one file required")
    request = _load_repaper_by_token(db, token)
    if request.state in (
        RepaperingState.RESOLVED.value,
        RepaperingState.CANCELLED.value,
    ):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Request already {request.state}; cannot accept uploads",
        )

    # Storage path mirrors the bulk processor convention.
    import os

    base = os.getenv("BULK_VALIDATE_STORAGE_DIR", "/tmp/lcopilot-bulk")
    target_dir = Path(base) / "repaper" / str(request.id)
    target_dir.mkdir(parents=True, exist_ok=True)

    saved: List[str] = []
    for upload in files:
        if not upload.filename:
            continue
        safe = upload.filename.replace("/", "_").replace("\\", "_")
        dest = target_dir / safe
        with dest.open("wb") as out:
            shutil.copyfileobj(upload.file, out)
        saved.append(str(dest))
    if not saved:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No usable files in upload")

    try:
        transition_repapering(db, request, RepaperingState.CORRECTED)
    except InvalidRepaperingTransition as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            {"code": "invalid_transition", "message": str(exc)},
        ) from exc
    db.commit()
    db.refresh(request)

    # Schedule auto re-validation. The task runs after the response is
    # returned, opens its own DB session, runs the pipeline, links the
    # new ValidationSession, and (on a clean run) resolves the parent
    # discrepancy. Failures inside the task are logged but never
    # surface to the recipient — they uploaded successfully.
    schedule_revalidation(background, request.id)

    return _to_repaper_read(request, include_token=False)


@repaper_router.post(
    "/{request_id}/cancel",
    response_model=RepaperRead,
)
async def cancel_repaper_request(
    request_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Requester cancels a pending re-papering request. Path uses
    the request UUID (not the access token) since it's an
    authenticated requester-side action."""
    request = (
        db.query(RepaperingRequest)
        .filter(RepaperingRequest.id == request_id)
        .first()
    )
    if request is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Re-papering request not found")
    if request.requester_user_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Re-papering request not found")
    try:
        transition_repapering(db, request, RepaperingState.CANCELLED)
    except InvalidRepaperingTransition as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            {"code": "invalid_transition", "message": str(exc)},
        ) from exc
    db.commit()
    db.refresh(request)
    return _to_repaper_read(request, include_token=False)


# ---------------------------------------------------------------------------
# Mappers
# ---------------------------------------------------------------------------


def _to_discrepancy_read(d: Discrepancy) -> DiscrepancyRead:
    return DiscrepancyRead(
        id=d.id,
        validation_session_id=d.validation_session_id,
        state=d.state,
        severity=d.severity,
        description=d.description,
        owner_user_id=d.owner_user_id,
        acknowledged_at=d.acknowledged_at,
        resolved_at=d.resolved_at,
        resolution_action=d.resolution_action,
        resolution_evidence_session_id=d.resolution_evidence_session_id,
    )


def _to_repaper_read(r: RepaperingRequest, *, include_token: bool) -> RepaperRead:
    return RepaperRead(
        id=r.id,
        discrepancy_id=r.discrepancy_id,
        recipient_email=r.recipient_email,
        recipient_display_name=r.recipient_display_name,
        state=r.state,
        message=r.message,
        access_token=r.access_token if include_token else None,
        replacement_session_id=r.replacement_session_id,
        created_at=r.created_at,
        opened_at=r.opened_at,
        submitted_at=r.submitted_at,
        resolved_at=r.resolved_at,
    )


__all__ = ["discrepancy_router", "repaper_router"]
