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


def test_condition_requirements_contract_carries_transport_and_quantity_fields() -> None:
    py_source = Path("packages/shared-types/python/schemas.py").read_text(encoding="utf-8")
    ts_source = Path("packages/shared-types/src/api.ts").read_text(encoding="utf-8")

    for token in ("document_type", "field_name", "originals_required", "copies_required", "exact_wording"):
        assert token in py_source
        assert token in ts_source


def test_bank_verdict_action_items_promote_exact_wording_requirements_explicitly() -> None:
    source = Path("apps/api/app/routers/validation/response_shaping.py").read_text(encoding="utf-8")

    assert 'requirement_kind == "document_exact_wording"' in source
    assert 'title = f"Add LC-required statement to {doc_label}"' in source


def test_validation_contract_shared_schema_exposes_rules_evidence_and_summary() -> None:
    py_source = Path("packages/shared-types/python/schemas.py").read_text(encoding="utf-8")
    ts_source = Path("packages/shared-types/src/api.ts").read_text(encoding="utf-8")

    for token in ("rules_evidence", "evidence_summary", "review_required_reason", "escalation_triggers"):
        assert token in py_source
        assert token in ts_source
