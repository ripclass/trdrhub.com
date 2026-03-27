from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATE_PATH = ROOT / "app" / "routers" / "validate.py"


def test_validate_router_exposes_contract_helpers_to_split_modules() -> None:
    source = VALIDATE_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)

    imported_names: set[str] = set()
    for node in parsed.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != "app.routers.validation":
            continue
        imported_names.update(alias.name for alias in node.names)

    assert "_apply_validation_contract_decision_surfaces" in imported_names
    assert "_apply_workflow_stage_contract_overrides" in imported_names
    assert "_partition_workflow_stage_issues" in imported_names
