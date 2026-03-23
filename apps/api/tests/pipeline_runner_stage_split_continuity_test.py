from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PIPELINE_RUNNER_PATH = ROOT / "app" / "routers" / "validation" / "pipeline_runner.py"
SESSION_SETUP_PATH = ROOT / "app" / "routers" / "validation" / "session_setup.py"
VALIDATION_EXECUTION_PATH = ROOT / "app" / "routers" / "validation" / "validation_execution.py"
RESULT_FINALIZATION_PATH = ROOT / "app" / "routers" / "validation" / "result_finalization.py"


def test_pipeline_runner_delegates_to_three_stage_modules() -> None:
    source = PIPELINE_RUNNER_PATH.read_text(encoding="utf-8")

    assert "await prepare_validation_session(" in source
    assert "await execute_validation_pipeline(" in source
    assert "await finalize_validation_result(" in source
    assert "bind_stage_modules(shared)" in source

    assert "ValidationSessionService(db)" not in source
    assert "build_unified_structured_result(" not in source
    assert "run_sanctions_screening_for_validation(" not in source


def test_stage_modules_own_expected_stage_markers() -> None:
    session_source = SESSION_SETUP_PATH.read_text(encoding="utf-8")
    execution_source = VALIDATION_EXECUTION_PATH.read_text(encoding="utf-8")
    result_source = RESULT_FINALIZATION_PATH.read_text(encoding="utf-8")

    assert "No Letter of Credit Found" in session_source
    assert "LC type detection:" in session_source
    assert "Persisted %d documents to database" in session_source

    assert "V2 Validation Gate:" in execution_source
    assert "DB rules executed:" in execution_source
    assert "Batch lookup:" in execution_source

    assert "build_unified_structured_result(" in result_source
    assert "run_sanctions_screening_for_validation(" in result_source
    assert "validate_and_annotate_response(" in result_source
