from __future__ import annotations

from pathlib import Path


def test_python_shared_schema_includes_condition_requirements() -> None:
    source = Path("packages/shared-types/python/schemas.py").read_text(encoding="utf-8")

    assert "class RequirementsGraphConditionRequirement" in source
    assert "condition_requirements: List[RequirementsGraphConditionRequirement]" in source


def test_typescript_shared_schema_includes_condition_requirements() -> None:
    source = Path("packages/shared-types/src/api.ts").read_text(encoding="utf-8")

    assert "RequirementsGraphConditionRequirementSchema" in source
    assert "condition_requirements: z.array(RequirementsGraphConditionRequirementSchema).default([])" in source
