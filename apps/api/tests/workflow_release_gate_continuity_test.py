from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
RELEASE_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "release.yml"
GATE_COMMAND = "pytest tests/gold_corpus_matrix_baseline_test.py -q"


def test_ci_workflow_runs_gold_corpus_baseline_gate() -> None:
    source = CI_WORKFLOW.read_text(encoding="utf-8")

    assert "Run gold corpus baseline gate" in source
    assert GATE_COMMAND in source


def test_release_workflow_runs_gold_corpus_release_gate() -> None:
    source = RELEASE_WORKFLOW.read_text(encoding="utf-8")

    assert "Run gold corpus release gate" in source
    assert GATE_COMMAND in source
