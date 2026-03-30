from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

RESULT_FINALIZATION_PATH = ROOT / "app" / "routers" / "validation" / "result_finalization.py"
SESSION_SETUP_PATH = ROOT / "app" / "routers" / "validation" / "session_setup.py"
VALIDATION_EXECUTION_PATH = ROOT / "app" / "routers" / "validation" / "validation_execution.py"


def _load_module(path: Path, name: str, package: str | None = None):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {path}")
    module = importlib.util.module_from_spec(spec)
    if package:
        module.__package__ = package
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _shared_map(module, missing: str) -> dict[str, object]:
    return {
        name: object()
        for name in module._SHARED_NAMES
        if name != missing
    }


def test_result_finalization_bind_shared_fails_fast_when_binding_is_missing() -> None:
    module = _load_module(
        RESULT_FINALIZATION_PATH,
        "result_finalization_fail_fast_bindings_test",
    )

    with pytest.raises(RuntimeError) as exc_info:
        module.bind_shared(_shared_map(module, "logger"))

    message = str(exc_info.value)
    assert "validation.result_finalization" in message
    assert "logger" in message


def test_session_setup_bind_shared_fails_fast_when_binding_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEBUG", "false")
    module = _load_module(
        SESSION_SETUP_PATH,
        "app.routers.validation.session_setup_fail_fast_bindings_test",
        package="app.routers.validation",
    )

    with pytest.raises(RuntimeError) as exc_info:
        module.bind_shared(_shared_map(module, "ValidationSessionService"))

    message = str(exc_info.value)
    assert "validation.session_setup" in message
    assert "ValidationSessionService" in message


def test_validation_execution_bind_shared_fails_fast_when_binding_is_missing() -> None:
    module = _load_module(
        VALIDATION_EXECUTION_PATH,
        "validation_execution_fail_fast_bindings_test",
    )

    with pytest.raises(RuntimeError) as exc_info:
        module.bind_shared(_shared_map(module, "logger"))

    message = str(exc_info.value)
    assert "validation.validation_execution" in message
    assert "logger" in message
