from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import time as time_module
import types
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette import status


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

VALIDATE_RUN_PATH = ROOT / "app" / "routers" / "validate_run.py"


def _load_module(path: Path, name: str):
    routers_root = ROOT / "app" / "routers"
    validation_root = routers_root / "validation"

    routers_pkg = types.ModuleType("app.routers")
    routers_pkg.__path__ = [str(routers_root)]
    sys.modules["app.routers"] = routers_pkg

    validation_pkg = types.ModuleType("app.routers.validation")
    validation_pkg.__path__ = [str(validation_root)]
    sys.modules["app.routers.validation"] = validation_pkg

    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Logger:
    def error(self, *args, **kwargs) -> None:
        return None


class _AuditService:
    def __init__(self, db) -> None:
        self.db = db

    def log_action(self, **kwargs) -> None:
        return None


class _FakeRouter:
    def __init__(self, *args, **kwargs) -> None:
        self.routes = []

    def add_api_route(self, path, endpoint, methods=None):
        self.routes.append(SimpleNamespace(path=path, endpoint=endpoint, methods=methods or []))


def _shared_bindings() -> dict[str, object]:
    return {
        "AuditAction": SimpleNamespace(UPLOAD="UPLOAD"),
        "AuditResult": SimpleNamespace(ERROR="ERROR"),
        "AuditService": _AuditService,
        "Depends": lambda dependency=None: dependency,
        "HTTPException": HTTPException,
        "List": list,
        "Request": object,
        "Session": object,
        "SessionStatus": object,
        "User": object,
        "adapt_from_structured_result": lambda **kwargs: None,
        "create_audit_context": lambda request: {
            "correlation_id": "req-123",
            "ip_address": "127.0.0.1",
            "user_agent": "pytest",
            "endpoint": "/api/validate",
            "http_method": "POST",
        },
        "get_db": lambda: None,
        "get_user_optional": lambda: None,
        "logger": _Logger(),
        "status": status,
        "time": time_module,
    }


@pytest.mark.asyncio
async def test_validate_run_wraps_generic_pipeline_failures_with_breadcrumbs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEBUG", "false")
    validate_run = _load_module(
        VALIDATE_RUN_PATH,
        "validate_run_failure_breadcrumbs_test",
    )
    validate_run.APIRouter = _FakeRouter
    validate_run.bind_request_parsing_shared = lambda shared: None
    validate_run.bind_pipeline_runner_shared = lambda shared: None

    async def fake_parse_validate_request(request):
        return SimpleNamespace(
            payload={},
            files_list=[],
            doc_type=None,
            intake_only=False,
        )

    async def fake_run_validate_pipeline(**kwargs):
        kwargs["runtime_context"]["pipeline_stage"] = "validation_execution"
        kwargs["runtime_context"]["pipeline_failure_stage"] = "validation_execution"
        kwargs["runtime_context"]["job_id"] = "job-123"
        kwargs["runtime_context"]["job_id_resolvable"] = True
        raise RuntimeError("pipeline boom")

    validate_run.parse_validate_request = fake_parse_validate_request
    validate_run.run_validate_pipeline = fake_run_validate_pipeline

    router = validate_run.build_router(_shared_bindings())
    validate_doc = next(route.endpoint for route in router.routes if route.path == "/")

    with pytest.raises(HTTPException) as exc_info:
        await validate_doc(request=SimpleNamespace(headers={}), current_user=None, db=object())

    assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert exc_info.value.detail == {
        "error_code": "validation_pipeline_failed",
        "message": "Validation failed during validation_execution.",
        "failure_stage": "validation_execution",
        "checkpoint_trace": ["request_received", "form_parsed"],
        "request_id": "req-123",
        "job_id": "job-123",
    }


@pytest.mark.asyncio
async def test_validate_run_exposes_runtime_context_on_request_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEBUG", "false")
    validate_run = _load_module(
        VALIDATE_RUN_PATH,
        "validate_run_request_state_runtime_context_test",
    )
    validate_run.APIRouter = _FakeRouter
    validate_run.bind_request_parsing_shared = lambda shared: None
    validate_run.bind_pipeline_runner_shared = lambda shared: None

    seen: dict[str, object] = {}

    async def fake_parse_validate_request(request):
        seen["runtime_context"] = request.state.validation_runtime_context
        return SimpleNamespace(
            payload={},
            files_list=[],
            doc_type=None,
            intake_only=False,
        )

    async def fake_run_validate_pipeline(**kwargs):
        return {
            "job_id": "job-state-1",
            "structured_result": {},
            "telemetry": {},
        }

    validate_run.parse_validate_request = fake_parse_validate_request
    validate_run.run_validate_pipeline = fake_run_validate_pipeline

    router = validate_run.build_router(_shared_bindings())
    validate_doc = next(route.endpoint for route in router.routes if route.path == "/")

    request = SimpleNamespace(headers={}, state=SimpleNamespace())
    result = await validate_doc(request=request, current_user=None, db=object())

    assert isinstance(seen["runtime_context"], dict)
    assert request.state.validation_runtime_context is seen["runtime_context"]
    assert result["job_id"] == "job-state-1"


@pytest.mark.asyncio
async def test_validate_run_enriches_http_exceptions_with_stage_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEBUG", "false")
    validate_run = _load_module(
        VALIDATE_RUN_PATH,
        "validate_run_http_failure_breadcrumbs_test",
    )
    validate_run.APIRouter = _FakeRouter
    validate_run.bind_request_parsing_shared = lambda shared: None
    validate_run.bind_pipeline_runner_shared = lambda shared: None

    async def fake_parse_validate_request(request):
        return SimpleNamespace(
            payload={},
            files_list=[],
            doc_type=None,
            intake_only=False,
        )

    async def fake_run_validate_pipeline(**kwargs):
        kwargs["runtime_context"]["pipeline_stage"] = "result_finalization"
        kwargs["runtime_context"]["job_id"] = "job-http-1"
        kwargs["runtime_context"]["job_id_resolvable"] = True
        exc = HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"message": "Upstream unavailable"},
        )
        setattr(exc, "_validation_pipeline_stage", "result_finalization")
        raise exc

    validate_run.parse_validate_request = fake_parse_validate_request
    validate_run.run_validate_pipeline = fake_run_validate_pipeline

    router = validate_run.build_router(_shared_bindings())
    validate_doc = next(route.endpoint for route in router.routes if route.path == "/")

    with pytest.raises(HTTPException) as exc_info:
        await validate_doc(request=SimpleNamespace(headers={}), current_user=None, db=object())

    assert exc_info.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert exc_info.value.detail == {
        "message": "Upstream unavailable",
        "failure_stage": "result_finalization",
        "checkpoint_trace": ["request_received", "form_parsed"],
        "request_id": "req-123",
        "job_id": "job-http-1",
    }


@pytest.mark.asyncio
async def test_validate_run_omits_non_resolvable_job_ids_from_error_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEBUG", "false")
    validate_run = _load_module(
        VALIDATE_RUN_PATH,
        "validate_run_http_failure_without_resolvable_job_test",
    )
    validate_run.APIRouter = _FakeRouter
    validate_run.bind_request_parsing_shared = lambda shared: None
    validate_run.bind_pipeline_runner_shared = lambda shared: None

    async def fake_parse_validate_request(request):
        return SimpleNamespace(
            payload={},
            files_list=[],
            doc_type=None,
            intake_only=False,
        )

    async def fake_run_validate_pipeline(**kwargs):
        kwargs["runtime_context"]["pipeline_stage"] = "result_finalization"
        kwargs["runtime_context"]["job_id"] = "ephemeral-job-1"
        kwargs["runtime_context"]["job_id_resolvable"] = False
        exc = HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"message": "Upstream unavailable"},
        )
        setattr(exc, "_validation_pipeline_stage", "result_finalization")
        raise exc

    validate_run.parse_validate_request = fake_parse_validate_request
    validate_run.run_validate_pipeline = fake_run_validate_pipeline

    router = validate_run.build_router(_shared_bindings())
    validate_doc = next(route.endpoint for route in router.routes if route.path == "/")

    with pytest.raises(HTTPException) as exc_info:
        await validate_doc(request=SimpleNamespace(headers={}), current_user=None, db=object())

    assert exc_info.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert exc_info.value.detail == {
        "message": "Upstream unavailable",
        "failure_stage": "result_finalization",
        "checkpoint_trace": ["request_received", "form_parsed"],
        "request_id": "req-123",
    }
