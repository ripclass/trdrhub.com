from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

VALIDATE_RUN_PATH = ROOT / "app" / "routers" / "validate_run.py"
REQUEST_PARSING_PATH = ROOT / "app" / "routers" / "validation" / "request_parsing.py"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_validate_run_build_router_fails_fast_when_required_shared_binding_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEBUG", "false")
    validate_run = _load_module(
        VALIDATE_RUN_PATH,
        "validate_run_fail_fast_bindings_test",
    )
    validate_run.bind_request_parsing_shared = lambda shared: None
    validate_run.bind_pipeline_runner_shared = lambda shared: None

    with pytest.raises(RuntimeError) as exc_info:
        validate_run.build_router(
            {
                "AuditAction": object(),
                "AuditResult": object(),
                "AuditService": object(),
                "Depends": lambda dependency=None: dependency,
                "HTTPException": Exception,
                "List": list,
                "Request": object,
                "Session": object,
                "SessionStatus": object(),
                "User": object,
                "adapt_from_structured_result": lambda **kwargs: None,
                "create_audit_context": lambda request: {},
                "get_db": lambda: None,
                "get_user_optional": lambda: None,
                "status": object(),
                "time": object(),
            }
        )

    message = str(exc_info.value)
    assert "validate_run" in message
    assert "logger" in message


def test_request_parsing_bind_shared_fails_fast_when_binding_is_missing() -> None:
    request_parsing = _load_module(
        REQUEST_PARSING_PATH,
        "request_parsing_fail_fast_bindings_test",
    )

    with pytest.raises(RuntimeError) as exc_info:
        request_parsing.bind_shared(
            {
                "Any": object,
                "HTTPException": Exception,
                "Request": object,
                "_extract_intake_only": lambda payload: False,
                "json": object(),
                "status": object(),
            }
        )

    message = str(exc_info.value)
    assert "validation.request_parsing" in message
    assert "validate_upload_file" in message
