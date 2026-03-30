"""Customs-pack route split from validate.py."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter


_SHARED_NAMES = ['CustomsPackBuilderFull', 'Depends', 'HTTPException', 'Session', 'UUID', 'User', 'UserRole', 'ValidationSession', 'get_current_user', 'get_db', 'logger', 'status']


def _shared_get(shared: Any, name: str) -> Any:
    if isinstance(shared, dict):
        return shared[name]
    return getattr(shared, name)


def _bind_shared(shared: Any) -> None:
    namespace = globals()
    missing_bindings: list[str] = []
    for name in _SHARED_NAMES:
        if name in namespace:
            continue
        try:
            namespace[name] = _shared_get(shared, name)
        except (KeyError, AttributeError):
            missing_bindings.append(name)
    if missing_bindings:
        raise RuntimeError(
            "Missing shared bindings for validate_customs: "
            + ", ".join(sorted(missing_bindings))
        )


def build_router(shared: Any) -> APIRouter:
    _bind_shared(shared)
    router = APIRouter()

    async def generate_customs_pack(
        session_id: str,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        """
        Build the customs pack ZIP, upload to S3, and return a signed URL.
        The FE should read .customs_pack.download_url and redirect the browser to it.
        """
        from uuid import UUID
    
        try:
            session_uuid = UUID(session_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid session ID format"
            )
    
        session = (
            db.query(ValidationSession)
            .filter(
                ValidationSession.id == session_uuid,
                ValidationSession.deleted_at.is_(None)
            )
            .first()
        )
    
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Validation session not found"
            )
    
        # Check access - user must own the session or be admin
        if session.user_id != current_user.id and current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
        # Validate session has been processed
        validation_results = session.validation_results or {}
        if not validation_results:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Session has no validation_results yet. Please run validation first."
            )
    
        # Build the customs pack
        try:
            builder = CustomsPackBuilderFull()
            result = builder.build_and_upload(db=db, session_id=session_id)
        except ValueError as e:
            # Session not found or invalid
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        except Exception as e:
            logger.error(f"Failed to build customs pack for session {session_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate customs pack: {str(e)}"
            )
    
        return {"customs_pack": result}

    router.add_api_route("/customs-pack/{session_id}", generate_customs_pack, methods=["GET"])

    return router


__all__ = ["build_router"]
