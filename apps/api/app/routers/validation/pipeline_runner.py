"""Validation pipeline runner extracted from validate_run.py."""

from __future__ import annotations

from typing import Any

from app.routers.validation.result_finalization import bind_shared as bind_result_finalization_shared
from app.routers.validation.result_finalization import finalize_validation_result
from app.routers.validation.session_setup import bind_shared as bind_session_setup_shared
from app.routers.validation.session_setup import prepare_validation_session
from app.routers.validation.validation_execution import bind_shared as bind_validation_execution_shared
from app.routers.validation.validation_execution import execute_validation_pipeline


_SHARED_NAMES: list[str] = []


def _shared_get(shared: Any, name: str) -> Any:
    if isinstance(shared, dict):
        return shared[name]
    return getattr(shared, name)


def bind_shared(shared: Any) -> None:
    namespace = globals()
    for name in _SHARED_NAMES:
        if name in namespace:
            continue
        try:
            namespace[name] = _shared_get(shared, name)
        except (KeyError, AttributeError):
            continue
    bind_stage_modules(shared)


def _checkpoint_trace(timings: Any) -> list[str]:
    if isinstance(timings, dict):
        return [str(name) for name in timings.keys()]
    return []


def _set_pipeline_stage(runtime_context: Any, stage: str, timings: Any) -> None:
    if not isinstance(runtime_context, dict):
        return
    runtime_context["pipeline_stage"] = stage
    runtime_context["pipeline_checkpoints"] = _checkpoint_trace(timings)
    stage_trace = runtime_context.setdefault("pipeline_stage_trace", [])
    if isinstance(stage_trace, list):
        stage_trace.append(stage)


def _annotate_pipeline_failure(exc: Exception, stage: str, timings: Any, runtime_context: Any) -> Exception:
    checkpoint_trace = _checkpoint_trace(timings)
    if isinstance(runtime_context, dict):
        runtime_context["pipeline_failure_stage"] = stage
        runtime_context["pipeline_checkpoints"] = checkpoint_trace
    try:
        setattr(exc, "_validation_pipeline_stage", stage)
        setattr(exc, "_validation_pipeline_checkpoints", checkpoint_trace)
        if (
            isinstance(runtime_context, dict)
            and runtime_context.get("job_id") is not None
            and runtime_context.get("job_id_resolvable")
        ):
            setattr(exc, "_validation_job_id", runtime_context.get("job_id"))
    except Exception:
        pass
    return exc


async def run_validate_pipeline(
    *,
    request,
    current_user,
    db,
    payload,
    files_list,
    doc_type,
    intake_only,
    start_time,
    timings,
    checkpoint,
    audit_service,
    audit_context,
    runtime_context,
):
    _set_pipeline_stage(runtime_context, "session_setup", timings)
    try:
        setup_state = await prepare_validation_session(
            request=request,
            current_user=current_user,
            db=db,
            payload=payload,
            files_list=files_list,
            intake_only=intake_only,
            checkpoint=checkpoint,
            start_time=start_time,
            runtime_context=runtime_context,
        )
    except Exception as exc:
        raise _annotate_pipeline_failure(exc, "session_setup", timings, runtime_context)
    if isinstance(setup_state, dict) and ("status" in setup_state or "structured_result" in setup_state):
        _set_pipeline_stage(runtime_context, "completed", timings)
        return setup_state

    _set_pipeline_stage(runtime_context, "validation_execution", timings)
    try:
        execution_state = await execute_validation_pipeline(
            request=request,
            current_user=current_user,
            db=db,
            payload=payload,
            files_list=files_list,
            doc_type=doc_type,
            checkpoint=checkpoint,
            start_time=start_time,
            setup_state=setup_state,
        )
    except Exception as exc:
        raise _annotate_pipeline_failure(exc, "validation_execution", timings, runtime_context)
    if isinstance(execution_state, dict) and "structured_result" in execution_state and "telemetry" in execution_state:
        _set_pipeline_stage(runtime_context, "completed", timings)
        return execution_state

    _set_pipeline_stage(runtime_context, "result_finalization", timings)
    try:
        final_result = await finalize_validation_result(
            request=request,
            current_user=current_user,
            db=db,
            payload=payload,
            files_list=files_list,
            start_time=start_time,
            timings=timings,
            checkpoint=checkpoint,
            audit_service=audit_service,
            audit_context=audit_context,
            setup_state=setup_state,
            execution_state=execution_state,
        )
    except Exception as exc:
        raise _annotate_pipeline_failure(exc, "result_finalization", timings, runtime_context)

    _set_pipeline_stage(runtime_context, "completed", timings)
    return final_result


def bind_stage_modules(shared: Any) -> None:
    bind_session_setup_shared(shared)
    bind_validation_execution_shared(shared)
    bind_result_finalization_shared(shared)


__all__ = ["bind_shared", "bind_stage_modules", "run_validate_pipeline"]
