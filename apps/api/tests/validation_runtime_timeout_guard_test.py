from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATION_EXECUTION_PATH = ROOT / "app" / "routers" / "validation" / "validation_execution.py"
RESULT_FINALIZATION_PATH = ROOT / "app" / "routers" / "validation" / "result_finalization.py"


def test_validation_execution_guards_optional_async_stages_with_timeouts() -> None:
    source = VALIDATION_EXECUTION_PATH.read_text(encoding="utf-8")

    assert "async def _await_with_timeout(" in source
    assert "asyncio.wait_for(" in source
    assert "\"DB rules execution\"" in source
    assert "\"Price verification\"" in source
    assert "\"AI validation\"" in source
    assert "\"Bank policy application\"" in source
    assert "ai_validation_summary" in source
    assert "structured_result[\"ai_validation\"]" not in source


def test_result_finalization_guards_optional_async_stages_with_timeouts() -> None:
    source = RESULT_FINALIZATION_PATH.read_text(encoding="utf-8")

    assert "async def _await_with_timeout(" in source
    assert "asyncio.wait_for(" in source
    assert "\"Sanctions screening\"" in source
    assert "\"Validation arbitration escalation\"" in source
    assert "\"Usage recording\"" in source
    assert "structured_result[\"ai_validation\"] = ai_validation_summary" in source
