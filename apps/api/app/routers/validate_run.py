"""Validation run routes split from validate.py."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter

from app.routers.validation.pipeline_runner import bind_shared as bind_pipeline_runner_shared
from app.routers.validation.pipeline_runner import run_validate_pipeline
from app.routers.validation.request_parsing import bind_shared as bind_request_parsing_shared
from app.routers.validation.request_parsing import parse_validate_request


_SHARED_NAMES = [
    'Any', 'AuditAction', 'AuditResult', 'AuditService', 'Depends', 'Dict', 'HTTPException', 'List',
    'Request', 'Session', 'SessionStatus', 'User', 'adapt_from_structured_result', 'create_audit_context',
    'get_db', 'get_user_optional', 'logger', 'status', 'time'
]


def _shared_get(shared: Any, name: str) -> Any:
    if isinstance(shared, dict):
        return shared[name]
    return getattr(shared, name)


def _bind_shared(shared: Any) -> None:
    namespace = globals()
    for name in _SHARED_NAMES:
        if name in namespace:
            continue
        try:
            namespace[name] = _shared_get(shared, name)
        except (KeyError, AttributeError):
            continue


def build_router(shared: Any) -> APIRouter:
    _bind_shared(shared)
    bind_request_parsing_shared(shared)
    bind_pipeline_runner_shared(shared)
    router = APIRouter()

    async def validate_doc(
        request: Request,
        current_user: User = Depends(get_user_optional),
        db: Session = Depends(get_db),
    ):
        """Validate LC documents."""
        start_time = time.time()

        timings: Dict[str, float] = {}

        def checkpoint(name: str) -> None:
            timings[name] = round(time.time() - start_time, 3)

        checkpoint("request_received")

        audit_service = AuditService(db)
        audit_context = create_audit_context(request)
        payload: Dict[str, Any] = {}
        runtime_context: Dict[str, Any] = {"validation_session": None}

        try:
            parsed_request = await parse_validate_request(request)
            payload = parsed_request.payload
            checkpoint("form_parsed")
            return await run_validate_pipeline(
                request=request,
                current_user=current_user,
                db=db,
                payload=payload,
                files_list=parsed_request.files_list,
                doc_type=parsed_request.doc_type,
                intake_only=parsed_request.intake_only,
                start_time=start_time,
                timings=timings,
                checkpoint=checkpoint,
                audit_service=audit_service,
                audit_context=audit_context,
                runtime_context=runtime_context,
            )
        except HTTPException:
            raise
        except UnicodeDecodeError as e:
            logger.error(f"Encoding error during file upload: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File encoding error: Unable to process uploaded file. Please ensure files are valid PDFs or images. Error: {str(e)}"
            )
        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            logger.error(
                f"Validation endpoint exception: {type(e).__name__}: {str(e)}",
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "user_id": current_user.id if current_user else None,
                    "endpoint": "/api/validate",
                    "traceback": error_traceback,
                },
                exc_info=True
            )

            user_type = payload.get("userType") or payload.get("user_type") if payload else None
            validation_session = runtime_context.get("validation_session")
            if user_type == "bank" and validation_session:
                duration_ms = int((time.time() - start_time) * 1000)
                audit_service.log_action(
                    action=AuditAction.UPLOAD,
                    user=current_user,
                    correlation_id=audit_context['correlation_id'],
                    resource_type="bank_validation",
                    resource_id=str(validation_session.id) if validation_session else "unknown",
                    ip_address=audit_context['ip_address'],
                    user_agent=audit_context['user_agent'],
                    endpoint=audit_context['endpoint'],
                    http_method=audit_context['http_method'],
                    result=AuditResult.ERROR,
                    duration_ms=duration_ms,
                    error_message=str(e),
                )
            raise

    async def validate_doc_v2(
        request: Request,
        current_user: User = Depends(get_user_optional),
        db: Session = Depends(get_db),
    ):
        """
        V2 Validation Endpoint - SME-focused response format.

        This endpoint runs the same validation logic but returns a cleaner,
        more focused response designed for SME/Corporation users.

        Response follows the SMEValidationResponse contract:
        - lc_summary: LC header info
        - verdict: The big answer (PASS/FIX_REQUIRED/LIKELY_REJECT)
        - issues: Grouped by must_fix and should_fix
        - documents: Grouped by good, has_issues, missing
        - processing: Metadata
        """
        try:
            v1_response = await validate_doc(request, current_user, db)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"V2 validation failed: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Validation failed: {str(e)}"
            )

        job_id = v1_response.get("job_id", "unknown")
        structured_result = v1_response.get("structured_result", {})

        try:
            sme_response = adapt_from_structured_result(
                structured_result=structured_result,
                session_id=job_id,
            )

            return {
                "version": "2.0",
                "job_id": job_id,
                "data": sme_response.to_dict(),
                "_v1_structured_result": structured_result if request.headers.get("X-Include-V1") else None,
            }
        except Exception as e:
            logger.error(f"V2 response transformation failed: {e}", exc_info=True)
            return {
                "version": "1.0",
                "job_id": job_id,
                "data": structured_result,
                "_transformation_error": str(e),
            }

    router.add_api_route("/", validate_doc, methods=["POST"])
    router.add_api_route("/v2", validate_doc_v2, methods=["POST"])

    return router


__all__ = ["build_router"]
