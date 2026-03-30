from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
VALIDATION_EXECUTION_PATH = ROOT / "app" / "routers" / "validation" / "validation_execution.py"
RESULT_FINALIZATION_PATH = ROOT / "app" / "routers" / "validation" / "result_finalization.py"


def _load_symbols(path: Path, function_names: set[str]) -> Dict[str, Any]:
    source = path.read_text(encoding="utf-8")
    parsed = ast.parse(source)
    selected_nodes: list[ast.AST] = []

    for node in parsed.body:
        if isinstance(node, ast.FunctionDef) and node.name in function_names:
            selected_nodes.append(node)

    module_ast = ast.Module(body=selected_nodes, type_ignores=[])
    ast.fix_missing_locations(module_ast)
    namespace: Dict[str, Any] = {
        "Any": Any,
        "Dict": Dict,
        "List": List,
    }
    exec(compile(module_ast, str(path), "exec"), namespace)
    return namespace


def test_validation_execution_builds_timeout_events_with_stable_shape() -> None:
    symbols = _load_symbols(
        VALIDATION_EXECUTION_PATH,
        {"_build_timeout_event"},
    )

    event = symbols["_build_timeout_event"](
        stage="db_rules_execution",
        label="DB rules execution",
        timeout_seconds=60,
        fallback="issues_skipped",
    )

    assert event == {
        "stage": "db_rules_execution",
        "label": "DB rules execution",
        "timeout_seconds": 60.0,
        "fallback": "issues_skipped",
        "source": "validation_execution",
    }


def test_result_finalization_builds_degraded_execution_summary_from_timeout_events() -> None:
    symbols = _load_symbols(
        RESULT_FINALIZATION_PATH,
        {"_build_degraded_execution_summary"},
    )

    summary = symbols["_build_degraded_execution_summary"](
        [
            {
                "stage": "db_rules_execution",
                "label": "DB rules execution",
                "timeout_seconds": 60,
                "fallback": "issues_skipped",
                "source": "validation_execution",
            },
            {
                "stage": "usage_recording",
                "label": "Usage recording",
                "timeout_seconds": 10,
                "fallback": "usage_record_skipped",
                "source": "result_finalization",
            },
        ]
    )

    assert summary["degraded"] is True
    assert summary["timeout_event_count"] == 2
    assert summary["stage_count"] == 2
    assert summary["timeout_events"][0]["stage"] == "db_rules_execution"
    assert summary["timeout_events"][1]["stage"] == "usage_recording"


def test_result_finalization_reports_clean_execution_without_timeout_events() -> None:
    symbols = _load_symbols(
        RESULT_FINALIZATION_PATH,
        {"_build_degraded_execution_summary"},
    )

    summary = symbols["_build_degraded_execution_summary"]([])

    assert summary == {
        "degraded": False,
        "timeout_event_count": 0,
        "stage_count": 0,
        "timeout_events": [],
    }
