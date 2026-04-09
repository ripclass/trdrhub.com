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


def _attach_pipeline_telemetry(
    result: Any,
    *,
    runtime_context: Any,
    timings: Any,
    request_id: str | None,
) -> Any:
    if not isinstance(result, dict):
        return result

    telemetry = result.get("telemetry")
    if not isinstance(telemetry, dict):
        telemetry = {}
        result["telemetry"] = telemetry

    stage_trace = []
    if isinstance(runtime_context, dict):
        raw_stage_trace = runtime_context.get("pipeline_stage_trace")
        if isinstance(raw_stage_trace, list):
            stage_trace = [str(stage) for stage in raw_stage_trace]

    telemetry.setdefault("pipeline_stage_trace", stage_trace)
    telemetry.setdefault("checkpoint_trace", _checkpoint_trace(timings))
    telemetry.setdefault(
        "pipeline_stage",
        runtime_context.get("pipeline_stage") if isinstance(runtime_context, dict) else None,
    )
    telemetry.setdefault(
        "job_id_resolvable",
        bool(runtime_context.get("job_id_resolvable")) if isinstance(runtime_context, dict) else False,
    )
    if isinstance(runtime_context, dict) and runtime_context.get("job_id_source") is not None:
        telemetry.setdefault("job_id_source", runtime_context.get("job_id_source"))
    if request_id:
        telemetry.setdefault("request_id", request_id)
    return result


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
    extract_only: bool = False,
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
        return _attach_pipeline_telemetry(
            setup_state,
            runtime_context=runtime_context,
            timings=timings,
            request_id=audit_context.get("correlation_id") if isinstance(audit_context, dict) else None,
        )

    # Extract-only mode: stop before validation. Persist the setup snapshot
    # so the resume endpoint can pick up where we left off, return a slim
    # response the extraction review screen can consume.
    if extract_only:
        _set_pipeline_stage(runtime_context, "extraction_ready", timings)
        try:
            extraction_response = _build_extraction_only_response(
                setup_state=setup_state,
                payload=payload,
                db=db,
            )
        except Exception as exc:
            raise _annotate_pipeline_failure(exc, "extraction_persist", timings, runtime_context)
        return _attach_pipeline_telemetry(
            extraction_response,
            runtime_context=runtime_context,
            timings=timings,
            request_id=audit_context.get("correlation_id") if isinstance(audit_context, dict) else None,
        )

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
        return _attach_pipeline_telemetry(
            execution_state,
            runtime_context=runtime_context,
            timings=timings,
            request_id=audit_context.get("correlation_id") if isinstance(audit_context, dict) else None,
        )

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
    return _attach_pipeline_telemetry(
        final_result,
        runtime_context=runtime_context,
        timings=timings,
        request_id=audit_context.get("correlation_id") if isinstance(audit_context, dict) else None,
    )


def bind_stage_modules(shared: Any) -> None:
    bind_session_setup_shared(shared)
    bind_validation_execution_shared(shared)
    bind_result_finalization_shared(shared)


# ---------------------------------------------------------------------------
# Extract-only / resume helpers
# ---------------------------------------------------------------------------


_SETUP_SNAPSHOT_KEY = "_setup_snapshot"


def _jsonable(value: Any) -> Any:
    """Coerce a value to something JSON-serializable; drop anything we can't."""
    if value is None:
        return None
    if isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, dict):
        out: dict = {}
        for k, v in value.items():
            if isinstance(k, (str, int, float, bool)):
                try:
                    out[str(k)] = _jsonable(v)
                except Exception:
                    continue
        return out
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(v) for v in value]
    try:
        return str(value)
    except Exception:
        return None


def _snapshot_setup_state(setup_state: dict) -> dict:
    """Build a JSON-serializable snapshot of setup_state (minus SQLAlchemy objects)."""
    snap: dict = {}
    for key, value in setup_state.items():
        if key == "validation_session":
            # re-attached on resume via DB lookup by job_id
            continue
        snap[key] = _jsonable(value)
    return snap


def _build_required_field_map(setup_state: dict) -> dict:
    """Derive the per-document required-field map from the parsed LC clauses.

    Delegates to required_fields_derivation.derive_required_fields(), which
    walks the LC context's already-extracted clause 46A documents-required
    list and clause 47A additional-conditions list and emits a per-doc
    required field map plus the MT700 mandatory list for the LC itself.
    """
    from app.services.extraction.required_fields_derivation import derive_required_fields

    lc_context = setup_state.get("lc_context") or {}
    documents = (setup_state.get("extracted_context") or {}).get("documents") or []

    document_types_present: list = []
    for doc in documents:
        if not isinstance(doc, dict):
            continue
        dtype = doc.get("document_type") or doc.get("documentType")
        if dtype:
            document_types_present.append(str(dtype))

    derived = derive_required_fields(
        lc_context=lc_context,
        document_types_present=document_types_present,
    )
    # Keep the legacy `baseline_required` key (cross-doc requirements) for
    # any existing consumers that grep for it.
    return {
        "baseline_required": derived.get("applies_to_all_supporting_docs") or [],
        "lc_self_required": derived.get("lc_self_required") or [],
        "lc_skeleton_required": derived.get("lc_skeleton_required") or [],
        "by_document_type": derived.get("by_document_type") or {},
        "applies_to_all_supporting_docs": derived.get("applies_to_all_supporting_docs") or [],
        "evidence": derived.get("evidence") or [],
    }


def _build_missing_required_documents(
    lc_context: dict,
    documents: list,
) -> list:
    """Compare LC-required document types against what was actually uploaded.

    Returns a list of missing docs in the shape the frontend expects:
        [{"type": <canonical_doc_type>, "display_name": <human>, "raw_text": <LC clause>, "reason_code": <code>}]

    Never errors — if we can't figure it out we just return [].
    """
    if not isinstance(lc_context, dict):
        return []

    try:
        from app.services.extraction.lc_taxonomy import normalize_required_documents
        from app.routers.validation.lc_intake import (
            infer_required_document_types_from_lc,
        )
    except ImportError:
        return []

    required_types = []
    try:
        required_types = infer_required_document_types_from_lc(lc_context) or []
    except Exception:
        required_types = []

    required_detailed = []
    try:
        required_detailed = normalize_required_documents(lc_context) or []
    except Exception:
        required_detailed = []

    if not required_types and not required_detailed:
        return []

    # Doc-type equivalence for the missing-docs check.
    #
    # Two different rules are in play:
    #
    # 1. Specialization -> parent (one-way).  A specialized transport doc
    #    like ocean_bill_of_lading satisfies a generic bill_of_lading
    #    requirement, but uploading a generic bill_of_lading does NOT
    #    satisfy an ocean_bill_of_lading requirement — the LC specifically
    #    asked for ocean and the user might have uploaded a short-form or
    #    non-marine BL.
    #
    # 2. Sibling equivalence (bidirectional).  UCP600 Art 28(d) explicitly
    #    treats an insurance policy and an insurance certificate as
    #    interchangeable presentation documents, and LC clauses commonly
    #    use "INSURANCE POLICY/CERTIFICATE" wording.  So uploading either
    #    satisfies a requirement for the other.
    _TRANSPORT_PARENTS: Dict[str, Tuple[str, ...]] = {
        "ocean_bill_of_lading": ("bill_of_lading",),
        "house_bill_of_lading": ("bill_of_lading",),
        "master_bill_of_lading": ("bill_of_lading",),
        "multimodal_transport_document": ("bill_of_lading",),
        "sea_waybill": ("bill_of_lading",),
    }
    _INSURANCE_SIBLINGS: Tuple[str, ...] = (
        "insurance_certificate",
        "insurance_policy",
        "marine_insurance_certificate",
        "marine_insurance_policy",
        "cargo_insurance",
        "cargo_insurance_certificate",
    )

    uploaded_types: set = set()
    for doc in documents or []:
        if not isinstance(doc, dict):
            continue
        doc_type = str(doc.get("document_type") or doc.get("documentType") or "").strip().lower()
        if not doc_type:
            continue
        uploaded_types.add(doc_type)
        # Specialization -> parent propagation
        for parent in _TRANSPORT_PARENTS.get(doc_type, ()):
            uploaded_types.add(parent)
        # Insurance siblings propagate both ways
        if doc_type in _INSURANCE_SIBLINGS:
            uploaded_types.update(_INSURANCE_SIBLINGS)

    # Build the missing list — prefer detailed entries (they carry the raw LC
    # clause text); fall back to plain types when detailed is empty.
    missing: list = []
    seen_types: set = set()

    if required_detailed:
        for entry in required_detailed:
            if not isinstance(entry, dict):
                continue
            type_ = str(entry.get("type") or entry.get("code") or "").strip().lower()
            if not type_ or type_ in seen_types:
                continue
            if type_ in uploaded_types:
                continue
            seen_types.add(type_)
            missing.append({
                "type": type_,
                "display_name": entry.get("display_name") or entry.get("label") or type_.replace("_", " ").title(),
                "raw_text": entry.get("raw_text") or entry.get("text") or "",
                "reason_code": "lc_required_missing_upload",
            })

    # Catch anything in required_types that wasn't in required_detailed
    for type_ in required_types:
        type_norm = str(type_ or "").strip().lower()
        if not type_norm or type_norm in seen_types:
            continue
        if type_norm in uploaded_types:
            continue
        seen_types.add(type_norm)
        missing.append({
            "type": type_norm,
            "display_name": type_norm.replace("_", " ").title(),
            "raw_text": "",
            "reason_code": "lc_required_missing_upload",
        })

    return missing


def _build_extraction_only_response(*, setup_state: dict, payload: dict, db: Any) -> dict:
    """Persist the setup snapshot on the DB session and build the extract-only response."""
    validation_session = setup_state.get("validation_session")
    job_id = setup_state.get("job_id")

    snapshot = _snapshot_setup_state(setup_state)
    required_fields = _build_required_field_map(setup_state)

    if validation_session is not None:
        extracted_data = dict(validation_session.extracted_data or {})
        extracted_data[_SETUP_SNAPSHOT_KEY] = snapshot
        extracted_data["_required_fields"] = required_fields
        extracted_data["_extraction_ready_at"] = __import__("datetime").datetime.utcnow().isoformat() + "Z"
        validation_session.extracted_data = extracted_data
        validation_session.status = "extraction_ready"
        try:
            db.commit()
            db.refresh(validation_session)
        except Exception:
            db.rollback()
            raise

    documents = (setup_state.get("extracted_context") or {}).get("documents") or []
    lc_context = setup_state.get("lc_context") or {}
    missing_required_documents = _build_missing_required_documents(lc_context, documents)

    return {
        "status": "extraction_ready",
        "job_id": str(job_id) if job_id else None,
        "jobId": str(job_id) if job_id else None,
        "documents": documents,
        "lc_context": lc_context,
        "lc_type": setup_state.get("lc_type"),
        "required_fields": required_fields,
        "missing_required_documents": missing_required_documents,
        "message": "Extraction complete. Review unresolved fields, then call /api/validate/resume/{job_id} to validate.",
    }


def _reconstruct_setup_state(validation_session: Any) -> dict:
    """Load a previously-persisted setup snapshot and reattach the live session row."""
    extracted_data = validation_session.extracted_data or {}
    snapshot = extracted_data.get(_SETUP_SNAPSHOT_KEY) or {}
    if not isinstance(snapshot, dict) or not snapshot:
        raise RuntimeError(
            "Session has no extraction snapshot — was it created via /api/validate?extract_only=true?"
        )
    state = dict(snapshot)
    state["validation_session"] = validation_session
    return state


def _apply_field_overrides(setup_state: dict, field_overrides: dict) -> None:
    """Apply user-confirmed field values into the extracted context in-place.

    Shape: {"<document_id or filename>": {"field_name": "new value", ...}, ...}

    This keeps the override path narrow: we merge user values into each
    matching document's `extracted_fields` dict. Anything the user didn't
    touch stays as the AI extractor produced it.
    """
    if not field_overrides or not isinstance(field_overrides, dict):
        return
    extracted_context = setup_state.get("extracted_context")
    if not isinstance(extracted_context, dict):
        return
    documents = extracted_context.get("documents") or []
    for doc in documents:
        if not isinstance(doc, dict):
            continue
        doc_key = str(doc.get("id") or doc.get("document_id") or doc.get("filename") or "")
        overrides = field_overrides.get(doc_key)
        if not isinstance(overrides, dict):
            continue
        target = doc.get("extracted_fields")
        if not isinstance(target, dict):
            target = {}
            doc["extracted_fields"] = target
        for field_name, value in overrides.items():
            target[str(field_name)] = value
        doc["_user_confirmed_fields"] = sorted(list(overrides.keys()))


async def run_resume_pipeline(
    *,
    request,
    current_user,
    db,
    validation_session,
    payload: dict,
    field_overrides: dict,
    start_time: float,
    timings: dict,
    checkpoint,
    audit_service,
    audit_context,
    runtime_context: dict,
):
    """Resume a previously-extracted session: apply overrides, run validation + finalization."""
    _set_pipeline_stage(runtime_context, "resume_reconstruct", timings)
    try:
        setup_state = _reconstruct_setup_state(validation_session)
    except Exception as exc:
        raise _annotate_pipeline_failure(exc, "resume_reconstruct", timings, runtime_context)

    _apply_field_overrides(setup_state, field_overrides or {})

    _set_pipeline_stage(runtime_context, "validation_execution", timings)
    try:
        execution_state = await execute_validation_pipeline(
            request=request,
            current_user=current_user,
            db=db,
            payload=payload or {},
            files_list=[],
            doc_type=(payload or {}).get("document_type") or "letter_of_credit",
            checkpoint=checkpoint,
            start_time=start_time,
            setup_state=setup_state,
        )
    except Exception as exc:
        raise _annotate_pipeline_failure(exc, "validation_execution", timings, runtime_context)

    if isinstance(execution_state, dict) and "structured_result" in execution_state and "telemetry" in execution_state:
        _set_pipeline_stage(runtime_context, "completed", timings)
        return _attach_pipeline_telemetry(
            execution_state,
            runtime_context=runtime_context,
            timings=timings,
            request_id=audit_context.get("correlation_id") if isinstance(audit_context, dict) else None,
        )

    _set_pipeline_stage(runtime_context, "result_finalization", timings)
    try:
        final_result = await finalize_validation_result(
            request=request,
            current_user=current_user,
            db=db,
            payload=payload or {},
            files_list=[],
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
    return _attach_pipeline_telemetry(
        final_result,
        runtime_context=runtime_context,
        timings=timings,
        request_id=audit_context.get("correlation_id") if isinstance(audit_context, dict) else None,
    )


__all__ = [
    "bind_shared",
    "bind_stage_modules",
    "run_validate_pipeline",
    "run_resume_pipeline",
]
