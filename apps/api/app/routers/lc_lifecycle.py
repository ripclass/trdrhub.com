"""LC lifecycle state-machine endpoints — Phase A1 of Path A.

  POST /api/sessions/{id}/lifecycle/transition
  GET  /api/sessions/{id}/lifecycle/history
  GET  /api/sessions/{id}/lifecycle/state

Surfaces the state machine in app/services/lc_lifecycle.py over HTTP.
Permission model: only the session owner OR privileged roles
(admin/bank) can transition. Everyone with read access can fetch
history + state.
"""

from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..core.security import ensure_owner_or_privileged, get_current_user
from ..database import get_db
from ..models import User, ValidationSession
from ..models.lc_lifecycle import (
    LC_LIFECYCLE_STATE_VALUES,
    LCLifecycleEvent,
)
from ..services.lc_lifecycle import (
    InvalidLifecycleTransition,
    allowed_next_states,
    current_state,
    history,
    is_terminal_state,
    transition,
)


router = APIRouter(
    prefix="/sessions/{session_id}/lifecycle",
    tags=["lc-lifecycle"],
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class LifecycleTransitionRequest(BaseModel):
    """Request body for POST /sessions/{id}/lifecycle/transition."""

    to_state: str = Field(
        ...,
        description=(
            "Target lifecycle state. One of: "
            + ", ".join(LC_LIFECYCLE_STATE_VALUES)
        ),
    )
    reason: Optional[str] = Field(
        None,
        description="Human/system reason for the transition. Audit trail.",
    )
    extra: Optional[dict[str, Any]] = Field(
        None,
        description="Free-form structured context (e.g. linked event payload).",
    )
    force: bool = Field(
        False,
        description=(
            "Bypass the allowed-transitions table. Privileged actions "
            "only — admins or rare correction paths. Audit-logged."
        ),
    )


class LifecycleStateResponse(BaseModel):
    """Returned by GET /lifecycle/state and POST /lifecycle/transition."""

    session_id: str
    current_state: str
    is_terminal: bool
    allowed_next_states: list[str]
    state_changed_at: Optional[str] = None


class LifecycleEventResponse(BaseModel):
    id: str
    from_state: Optional[str]
    to_state: str
    actor_user_id: Optional[str]
    reason: Optional[str]
    extra: Optional[dict[str, Any]] = None
    created_at: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_session_or_404(
    db: Session, session_id: UUID, current_user: User
) -> ValidationSession:
    session = (
        db.query(ValidationSession)
        .filter(ValidationSession.id == session_id)
        .first()
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Validation session not found",
        )
    ensure_owner_or_privileged(current_user, session.user_id)
    return session


def _state_response(session: ValidationSession) -> LifecycleStateResponse:
    state_enum = current_state(session)
    return LifecycleStateResponse(
        session_id=str(session.id),
        current_state=state_enum.value,
        is_terminal=is_terminal_state(state_enum),
        allowed_next_states=sorted(s.value for s in allowed_next_states(state_enum)),
        state_changed_at=(
            session.lifecycle_state_changed_at.isoformat()
            if session.lifecycle_state_changed_at
            else None
        ),
    )


def _event_response(event: LCLifecycleEvent) -> LifecycleEventResponse:
    return LifecycleEventResponse(
        id=str(event.id),
        from_state=event.from_state,
        to_state=event.to_state,
        actor_user_id=str(event.actor_user_id) if event.actor_user_id else None,
        reason=event.reason,
        extra=event.extra,
        created_at=event.created_at.isoformat() if event.created_at else "",
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/state", response_model=LifecycleStateResponse)
async def get_lifecycle_state(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LifecycleStateResponse:
    """Return the session's current lifecycle state + allowed next states."""
    session = _load_session_or_404(db, session_id, current_user)
    return _state_response(session)


@router.post(
    "/transition",
    response_model=LifecycleStateResponse,
    status_code=status.HTTP_200_OK,
)
async def transition_lifecycle_state(
    session_id: UUID,
    payload: LifecycleTransitionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LifecycleStateResponse:
    """Transition the session to a new lifecycle state.

    Rejects with 400 + ``code: invalid_transition`` if the target state
    is not in the allowed-transitions table for the current state and
    ``force=false``. Response payload lists the allowed alternatives so
    the caller can correct + retry.
    """
    session = _load_session_or_404(db, session_id, current_user)

    try:
        transition(
            db,
            session,
            to_state=payload.to_state,
            actor_user_id=current_user.id,
            reason=payload.reason,
            extra=payload.extra,
            force=payload.force,
        )
    except InvalidLifecycleTransition as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "invalid_transition",
                "message": str(exc),
                "from_state": exc.from_state,
                "to_state": exc.to_state,
                "allowed_next_states": sorted(s.value for s in exc.allowed),
            },
        ) from exc

    db.commit()
    db.refresh(session)
    return _state_response(session)


@router.get("/history", response_model=list[LifecycleEventResponse])
async def get_lifecycle_history(
    session_id: UUID,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[LifecycleEventResponse]:
    """Return the session's lifecycle event log, newest first."""
    session = _load_session_or_404(db, session_id, current_user)
    capped = max(1, min(limit, 500))
    events = history(db, session, limit=capped)
    return [_event_response(e) for e in events]
