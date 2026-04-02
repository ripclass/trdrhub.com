from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Dict


ROOT = Path(__file__).resolve().parents[1]
VALIDATION_EXECUTION_PATH = ROOT / "app" / "routers" / "validation" / "validation_execution.py"


def _load_validation_execution_symbols(target_names: set[str]) -> Dict[str, Any]:
    source = VALIDATION_EXECUTION_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)
    selected = [
        node
        for node in parsed.body
        if isinstance(node, ast.FunctionDef) and node.name in target_names
    ]
    module_ast = ast.Module(body=selected, type_ignores=[])
    ast.fix_missing_locations(module_ast)
    namespace: Dict[str, Any] = {"Any": Any}
    exec(compile(module_ast, str(VALIDATION_EXECUTION_PATH), "exec"), namespace)
    return namespace


class _DummyDB:
    def __init__(self) -> None:
        self.rollback_calls = 0

    def rollback(self) -> None:
        self.rollback_calls += 1


def test_recover_validation_db_session_rolls_back_failed_state() -> None:
    symbols = _load_validation_execution_symbols({"_recover_validation_db_session"})
    recover_validation_db_session = symbols["_recover_validation_db_session"]

    db = _DummyDB()
    recover_validation_db_session(db)

    assert db.rollback_calls == 1


def test_validation_execution_emits_post_validation_recovery_checkpoints() -> None:
    source = VALIDATION_EXECUTION_PATH.read_text(encoding="utf-8")

    assert 'checkpoint("post_validation_db_recovery")' in source
    assert 'checkpoint("company_context_ready")' in source
    assert 'checkpoint("quota_check_complete")' in source
    assert 'checkpoint("request_user_type_resolved")' in source
