from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PIPELINE_RUNNER_PATH = ROOT / "app" / "routers" / "validation" / "pipeline_runner.py"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.asyncio
async def test_pipeline_runner_tags_stage_and_checkpoints_on_execution_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEBUG", "false")
    pipeline_runner = _load_module(
        PIPELINE_RUNNER_PATH,
        "pipeline_runner_failure_breadcrumbs_test",
    )

    async def fake_prepare_validation_session(**kwargs):
        return {"validation_session": "ok"}

    async def fake_execute_validation_pipeline(**kwargs):
        raise RuntimeError("execution boom")

    async def fake_finalize_validation_result(**kwargs):
        raise AssertionError("finalization should not run")

    pipeline_runner.prepare_validation_session = fake_prepare_validation_session
    pipeline_runner.execute_validation_pipeline = fake_execute_validation_pipeline
    pipeline_runner.finalize_validation_result = fake_finalize_validation_result

    runtime_context: dict[str, object] = {}
    timings = {"request_received": 0.0, "form_parsed": 0.1}

    with pytest.raises(RuntimeError) as exc_info:
        await pipeline_runner.run_validate_pipeline(
            request=object(),
            current_user=None,
            db=None,
            payload={},
            files_list=[],
            doc_type=None,
            intake_only=False,
            start_time=0.0,
            timings=timings,
            checkpoint=lambda name: None,
            audit_service=None,
            audit_context={},
            runtime_context=runtime_context,
        )

    assert str(exc_info.value) == "execution boom"
    assert getattr(exc_info.value, "_validation_pipeline_stage") == "validation_execution"
    assert getattr(exc_info.value, "_validation_pipeline_checkpoints") == [
        "request_received",
        "form_parsed",
    ]
    assert runtime_context["pipeline_stage"] == "validation_execution"
    assert runtime_context["pipeline_failure_stage"] == "validation_execution"
    assert runtime_context["pipeline_checkpoints"] == ["request_received", "form_parsed"]
    assert runtime_context["pipeline_stage_trace"] == [
        "session_setup",
        "validation_execution",
    ]
