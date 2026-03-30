"""Validation results routes split from validate.py."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter


_SHARED_NAMES = ['Depends', 'HTTPException', 'Session', 'User', 'ValidationSession', 'adapt_from_structured_result', 'get_db', 'get_user_optional', 'logger', 'status']


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
            "Missing shared bindings for validate_results: "
            + ", ".join(sorted(missing_bindings))
        )


def build_router(shared: Any) -> APIRouter:
    _bind_shared(shared)
    router = APIRouter()

    async def get_validation_result_v2(
        session_id: str,
        current_user: User = Depends(get_user_optional),
        db: Session = Depends(get_db),
    ):
        """
        Get validation results in V2 SME format for an existing session.
        Uses lenient auth to support sessions created anonymously.
        """
        from app.services.validation.sme_response_builder import adapt_from_structured_result
    
        # Get the session
        session = db.query(ValidationSession).filter(
            ValidationSession.id == session_id
        ).first()
    
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Validation session {session_id} not found"
            )
    
        # Lenient access check - allow if:
        # 1. User owns the session
        # 2. User is admin
        # 3. Session was created anonymously (demo user)
        # For now, we allow access since sessions may have been created before auth was enforced
        # TODO: Add stricter access control once session ownership is properly tracked
    
        # Get stored validation results
        raw_results = session.validation_results or {}
        if not raw_results:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Session has no validation results yet"
            )
    
        # Unwrap if stored in nested format: {"structured_result": {...}}
        if "structured_result" in raw_results:
            structured_result = raw_results["structured_result"]
        else:
            structured_result = raw_results
    
        # Debug: Log what keys are available in structured_result
        logger.info(f"V2 session {session_id} - stored keys: {list(structured_result.keys())}")
        logger.info(f"V2 session {session_id} - lc_data keys: {list(structured_result.get('lc_data', {}).keys()) if isinstance(structured_result.get('lc_data'), dict) else 'N/A'}")
        logger.info(f"V2 session {session_id} - documents count: {len(structured_result.get('documents_structured', []))}")
        logger.info(f"V2 session {session_id} - issues count: {len(structured_result.get('issues', []))}")
        logger.info(f"V2 session {session_id} - crossdoc count: {len(structured_result.get('crossdoc_issues', []))}")
    
        # Transform to SME format
        try:
            sme_response = adapt_from_structured_result(
                structured_result=structured_result,
                session_id=session_id,
            )
        
            return {
                "version": "2.0",
                "session_id": session_id,
                "data": sme_response.to_dict(),
            }
        except Exception as e:
            logger.error(f"V2 transformation failed for session {session_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to transform results: {str(e)}"
            )

    router.add_api_route("/v2/session/{session_id}", get_validation_result_v2, methods=["GET"])

    return router


__all__ = ["build_router"]
