from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN_PATH = ROOT / "main.py"


def test_global_exception_handler_includes_validation_breadcrumbs() -> None:
    source = MAIN_PATH.read_text(encoding="utf-8")

    assert "def _validation_breadcrumbs_from_request" in source
    assert 'getattr(request.state, "validation_runtime_context", None)' in source
    assert 'error_dict.update(_validation_breadcrumbs_from_request(request))' in source
    assert '"failure_stage"' in source
    assert '"checkpoint_trace"' in source
    assert '"pipeline_stage_trace"' in source
    assert '"job_id"' in source
