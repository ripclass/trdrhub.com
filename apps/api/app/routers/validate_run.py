"""Validation run routes split from validate.py."""

from __future__ import annotations

import asyncio
from typing import Any, Dict

from fastapi import APIRouter

from app.routers.validation.pipeline_runner import bind_shared as bind_pipeline_runner_shared
from app.routers.validation.pipeline_runner import run_resume_pipeline, run_validate_pipeline
from app.routers.validation.request_parsing import bind_shared as bind_request_parsing_shared
from app.routers.validation.request_parsing import parse_validate_request
from app.utils.validation_progress import publish_completion, publish_progress


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
            "Missing shared bindings for validate_run: "
            + ", ".join(sorted(missing_bindings))
        )


def _enrich_http_exception_detail(
    *,
    detail: Any,
    failure_stage: str | None,
    checkpoint_trace: list[str],
    request_id: str | None,
    job_id: Any,
    job_id_resolvable: bool = False,
) -> Dict[str, Any]:
    if isinstance(detail, dict):
        enriched = dict(detail)
    else:
        enriched = {"message": str(detail) if detail else "Validation failed."}

    if failure_stage and not enriched.get("failure_stage"):
        enriched["failure_stage"] = failure_stage
    if checkpoint_trace and not enriched.get("checkpoint_trace"):
        enriched["checkpoint_trace"] = list(checkpoint_trace)
    if request_id and not enriched.get("request_id"):
        enriched["request_id"] = request_id
    if job_id_resolvable and job_id is not None and not enriched.get("job_id"):
        enriched["job_id"] = job_id

    return enriched


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

        # Client-supplied request id lets the frontend subscribe to the SSE
        # progress stream BEFORE the backend has created a session row. This
        # avoids the chicken-and-egg problem of needing job_id to subscribe.
        client_request_id = request.headers.get("X-Client-Request-ID") or None

        runtime_context: Dict[str, Any] = {"validation_session": None}
        runtime_context["client_request_id"] = client_request_id

        def checkpoint(name: str) -> None:
            timings[name] = round(time.time() - start_time, 3)
            # Best-effort progress publish — never blocks or fails the pipeline
            job_id = runtime_context.get("job_id")
            if job_id or client_request_id:
                try:
                    asyncio.create_task(
                        publish_progress(
                            checkpoint_name=name,
                            job_id=str(job_id) if job_id else None,
                            client_request_id=client_request_id,
                        )
                    )
                except RuntimeError:
                    # No running event loop; skip silently
                    pass

        checkpoint("request_received")

        audit_service = AuditService(db)
        audit_context = create_audit_context(request)
        payload: Dict[str, Any] = {}
        if hasattr(request, "state"):
            request.state.validation_runtime_context = runtime_context

        try:
            parsed_request = await parse_validate_request(request)
            payload = parsed_request.payload
            checkpoint("form_parsed")
            result = await run_validate_pipeline(
                request=request,
                current_user=current_user,
                db=db,
                payload=payload,
                files_list=parsed_request.files_list,
                doc_type=parsed_request.doc_type,
                intake_only=parsed_request.intake_only,
                extract_only=parsed_request.extract_only,
                start_time=start_time,
                timings=timings,
                checkpoint=checkpoint,
                audit_service=audit_service,
                audit_context=audit_context,
                runtime_context=runtime_context,
            )
            # Publish terminal completion event for SSE consumers
            try:
                final_job_id = runtime_context.get("job_id")
                asyncio.create_task(
                    publish_completion(
                        job_id=str(final_job_id) if final_job_id else None,
                        client_request_id=client_request_id,
                        success=True,
                    )
                )
            except RuntimeError:
                pass
            return result
        except HTTPException as exc:
            failure_stage = (
                getattr(exc, "_validation_pipeline_stage", None)
                or runtime_context.get("pipeline_failure_stage")
                or runtime_context.get("pipeline_stage")
            )
            checkpoint_trace = list(timings.keys())
            if failure_stage or runtime_context.get("job_id") is not None:
                logger.error(
                    "Validation endpoint HTTPException at stage=%s status=%s request_id=%s job_id=%s",
                    failure_stage,
                    exc.status_code,
                    audit_context.get("correlation_id"),
                    runtime_context.get("job_id"),
                )
                raise HTTPException(
                    status_code=exc.status_code,
                    detail=_enrich_http_exception_detail(
                        detail=exc.detail,
                        failure_stage=failure_stage,
                        checkpoint_trace=checkpoint_trace,
                        request_id=audit_context.get("correlation_id"),
                        job_id=runtime_context.get("job_id"),
                        job_id_resolvable=bool(runtime_context.get("job_id_resolvable")),
                    ),
                    headers=exc.headers,
                ) from exc
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
            failure_stage = (
                getattr(e, "_validation_pipeline_stage", None)
                or runtime_context.get("pipeline_failure_stage")
                or runtime_context.get("pipeline_stage")
            )
            checkpoint_trace = list(timings.keys())
            # Notify SSE consumers that the pipeline failed
            try:
                final_job_id = runtime_context.get("job_id")
                asyncio.create_task(
                    publish_completion(
                        job_id=str(final_job_id) if final_job_id else None,
                        client_request_id=client_request_id,
                        success=False,
                        error_message=f"Validation failed during {failure_stage}" if failure_stage else "Validation failed",
                    )
                )
            except RuntimeError:
                pass
            logger.error(
                f"Validation endpoint exception: {type(e).__name__}: {str(e)}",
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "user_id": current_user.id if current_user else None,
                    "endpoint": "/api/validate",
                    "failure_stage": failure_stage,
                    "checkpoint_trace": checkpoint_trace,
                    "request_id": audit_context.get("correlation_id"),
                    "job_id": runtime_context.get("job_id"),
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
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error_code": "validation_pipeline_failed",
                    "message": (
                        f"Validation failed during {failure_stage}."
                        if failure_stage
                        else "Validation failed during processing."
                    ),
                    "failure_stage": failure_stage or "unknown",
                    "checkpoint_trace": checkpoint_trace,
                    "request_id": audit_context.get("correlation_id"),
                    **(
                        {"job_id": runtime_context.get("job_id")}
                        if runtime_context.get("job_id_resolvable") and runtime_context.get("job_id") is not None
                        else {}
                    ),
                },
            ) from e

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

    async def resume_validate_doc(
        job_id: str,
        request: Request,
        current_user: User = Depends(get_user_optional),
        db: Session = Depends(get_db),
    ):
        """Resume a previously-extracted session and run the validation pipeline.

        Expects `POST /api/validate/resume/{job_id}` with an optional JSON body:

            {
              "field_overrides": {
                "<filename or doc_id>": { "field_name": "user value", ... }
              },
              "payload": { ... }   // optional passthrough to validation
            }
        """
        from uuid import UUID as _UUID
        from app.models import ValidationSession as _ValidationSession, SessionStatus

        start_time = time.time()
        timings: Dict[str, float] = {}

        def checkpoint(name: str) -> None:
            timings[name] = round(time.time() - start_time, 3)

        checkpoint("resume_request_received")

        body: Dict[str, Any] = {}
        try:
            if request.headers.get("content-type", "").startswith("application/json"):
                body = await request.json()
        except Exception:
            body = {}

        field_overrides = body.get("field_overrides") or body.get("fieldOverrides") or {}
        payload = body.get("payload") or {}

        try:
            job_uuid = _UUID(str(job_id))
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Invalid job_id: {job_id}") from exc

        validation_session = db.query(_ValidationSession).filter(_ValidationSession.id == job_uuid).first()
        if validation_session is None:
            raise HTTPException(status_code=404, detail="Validation session not found")
        if current_user is not None and validation_session.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Session belongs to a different user")
        if str(validation_session.status or "").strip().lower() != SessionStatus.EXTRACTION_READY.value:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Session status is '{validation_session.status}', expected '{SessionStatus.EXTRACTION_READY.value}'. "
                    "Call POST /api/validate/ with extract_only=true first."
                ),
            )

        runtime_context: Dict[str, Any] = {"validation_session": validation_session, "job_id": str(validation_session.id)}
        audit_service = AuditService(db)
        audit_context = create_audit_context(request)

        try:
            result = await run_resume_pipeline(
                request=request,
                current_user=current_user,
                db=db,
                validation_session=validation_session,
                payload=payload,
                field_overrides=field_overrides,
                start_time=start_time,
                timings=timings,
                checkpoint=checkpoint,
                audit_service=audit_service,
                audit_context=audit_context,
                runtime_context=runtime_context,
            )
            return result
        except HTTPException:
            raise
        except Exception as exc:
            logger.error(
                f"Resume validation failed for job_id={job_id}: {type(exc).__name__}: {exc}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Resume validation failed: {exc}",
            )

    router.add_api_route("/", validate_doc, methods=["POST"])
    router.add_api_route("/v2", validate_doc_v2, methods=["POST"])
    router.add_api_route("/resume/{job_id}", resume_validate_doc, methods=["POST"])

    return router


__all__ = ["build_router"]
