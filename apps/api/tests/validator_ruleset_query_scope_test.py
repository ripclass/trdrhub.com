from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

os.environ["DEBUG"] = "false"

from app.services import rules_service as rules_service_module  # noqa: E402
from app.services import validator as validator_module  # noqa: E402


class _FakeRulesService:
    def __init__(self) -> None:
        self.calls: list[dict[str, str | None]] = []

    async def get_active_ruleset(
        self,
        domain: str,
        jurisdiction: str = "global",
        document_type: str | None = None,
    ) -> dict[str, object]:
        self.calls.append(
            {
                "domain": domain,
                "jurisdiction": jurisdiction,
                "document_type": document_type,
            }
        )
        if domain == "icc.ucp600":
            return {
                "rules": [
                    {
                        "rule_id": "UCP600-28A",
                        "domain": "lc_ops",
                        "document_type": "insurance",
                        "title": "Insurance Originals Match LC Requirement",
                        "description": "Insurance originals must satisfy the LC quantity requirement.",
                    }
                ],
                "ruleset_version": "1.0",
                "rulebook_version": "UCP600:2007",
            }
        return {
            "rules": [],
            "ruleset_version": "1.0",
            "rulebook_version": "UCP600:2007",
        }


class _FallbackRulesService:
    def __init__(self) -> None:
        self.calls: list[dict[str, str | None]] = []

    async def get_active_ruleset(
        self,
        domain: str,
        jurisdiction: str = "global",
        document_type: str | None = None,
    ) -> dict[str, object] | None:
        self.calls.append(
            {
                "domain": domain,
                "jurisdiction": jurisdiction,
                "document_type": document_type,
            }
        )
        if domain == "icc.ucp600" and jurisdiction == "global":
            return {
                "rules": [
                    {
                        "rule_id": "UCP600-28A",
                        "domain": "lc_ops",
                        "document_type": "insurance",
                        "title": "Insurance Originals Match LC Requirement",
                        "description": "Insurance originals must satisfy the LC quantity requirement.",
                    }
                ],
                "ruleset_version": "1.0",
                "rulebook_version": "UCP600:2007",
            }
        return None


@pytest.mark.asyncio
async def test_validate_document_async_fetches_unfiltered_rulesets_for_lc_scoped_rules(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_service = _FakeRulesService()

    monkeypatch.setattr(rules_service_module, "get_rules_service", lambda: fake_service)

    async def _fake_inject_semantic_conditions(rules, document_data, evaluator):
        return rules, {}

    monkeypatch.setattr(
        validator_module,
        "_inject_semantic_conditions",
        _fake_inject_semantic_conditions,
    )
    monkeypatch.setattr(
        validator_module,
        "activate_rules_for_lc",
        lambda lc_context, filtered_rules_with_meta, document_data: filtered_rules_with_meta,
    )

    class _FakeRuleEvaluator:
        async def evaluate_rules(self, rules, input_context):
            return {
                "outcomes": [
                    {
                        "rule_id": "UCP600-28A",
                        "passed": False,
                        "severity": "major",
                        "message": "Insurance originals presented are below the LC requirement.",
                    }
                ]
            }

    monkeypatch.setattr(validator_module, "RuleEvaluator", _FakeRuleEvaluator)

    results = await validator_module.validate_document_async(
        {
            "domain": "icc.ucp600",
            "jurisdiction": "global",
            "lc": {
                "requirements_graph_v1": {
                    "required_document_types": ["insurance_certificate"],
                    "condition_requirements": [
                        {
                            "requirement_type": "document_quantity",
                            "document_type": "insurance_certificate",
                            "originals_required": 2,
                        }
                    ],
                }
            },
            "insurance": {"originals_presented": 1},
        },
        document_type="commercial_invoice",
    )

    icc_ucp600_calls = [
        call for call in fake_service.calls if call.get("domain") == "icc.ucp600"
    ]

    assert icc_ucp600_calls
    assert all(call.get("document_type") is None for call in icc_ucp600_calls)
    assert [result.get("rule") for result in results] == ["UCP600-28A"]


@pytest.mark.asyncio
async def test_validate_document_async_falls_back_to_global_for_icc_rulesets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_service = _FallbackRulesService()

    monkeypatch.setattr(rules_service_module, "get_rules_service", lambda: fake_service)

    async def _fake_inject_semantic_conditions(rules, document_data, evaluator):
        return rules, {}

    monkeypatch.setattr(
        validator_module,
        "_inject_semantic_conditions",
        _fake_inject_semantic_conditions,
    )
    monkeypatch.setattr(
        validator_module,
        "activate_rules_for_lc",
        lambda lc_context, filtered_rules_with_meta, document_data: filtered_rules_with_meta,
    )

    class _FakeRuleEvaluator:
        async def evaluate_rules(self, rules, input_context):
            return {
                "outcomes": [
                    {
                        "rule_id": "UCP600-28A",
                        "passed": False,
                        "severity": "major",
                        "message": "Insurance originals presented are below the LC requirement.",
                    }
                ]
            }

    monkeypatch.setattr(validator_module, "RuleEvaluator", _FakeRuleEvaluator)

    results = await validator_module.validate_document_async(
        {
            "domain": "icc.ucp600",
            "jurisdiction": "bd",
            "lc": {
                "requirements_graph_v1": {
                    "required_document_types": ["insurance_certificate"],
                }
            },
            "insurance": {"originals_presented": 1},
        },
        document_type="commercial_invoice",
    )

    assert [
        (call.get("domain"), call.get("jurisdiction"))
        for call in fake_service.calls
        if call.get("domain") == "icc.ucp600"
    ] == [
        ("icc.ucp600", "bd"),
        ("icc.ucp600", "global"),
    ]
    assert [result.get("rule") for result in results] == ["UCP600-28A"]
