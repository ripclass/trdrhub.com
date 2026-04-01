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


class _LcOpsCompatibilityRulesService:
    async def get_active_ruleset(
        self,
        domain: str,
        jurisdiction: str = "global",
        document_type: str | None = None,
    ) -> dict[str, object] | None:
        if domain == "icc.ucp600":
            return {
                "rules": [
                    {
                        "rule_id": "UCP600-28A",
                        "domain": "lc_ops",
                        "jurisdiction": "global",
                        "severity": "fail",
                        "deterministic": True,
                        "requires_llm": False,
                        "consequence_class": "insurance_doc_discrepancy",
                        "title": "Insurance Document: Originals Must Be Presented",
                        "conditions": [
                            {
                                "field": "insurance_doc.originals_presented",
                                "operator": "less_than",
                                "reference_field": "insurance_doc.originals_issued",
                                "type": "amount_comparison",
                            }
                        ],
                        "expected_outcome": {
                            "valid": ["Presentation complies"],
                            "invalid": [
                                "Not all issued originals of the insurance document presented.",
                                "Remediation: Require all originals.",
                            ],
                        },
                    }
                ],
                "ruleset_version": "1.0.2",
                "rulebook_version": "UCP600:2007",
            }
        if domain == "icc.isbp745":
            return {
                "rules": [
                    {
                        "rule_id": "ISBP745-A1",
                        "domain": "icc",
                        "jurisdiction": "global",
                        "severity": "info",
                        "deterministic": True,
                        "requires_llm": False,
                        "consequence_class": "domain_logic",
                        "title": "Abbreviations",
                        "conditions": [
                            {
                                "type": "document_content",
                                "rule": "Generally accepted abbreviations are acceptable in place of full words and vice versa.",
                            }
                        ],
                        "expected_outcome": {
                            "valid": ["Abbreviations acceptable"],
                            "invalid": ["Bank refuses document for using abbreviation."],
                        },
                    }
                ],
                "ruleset_version": "1.0.2",
                "rulebook_version": "ISBP745",
            }
        return {"rules": [], "ruleset_version": "1.0.2", "rulebook_version": domain}


@pytest.mark.asyncio
async def test_validate_document_async_surfaces_specific_lc_ops_discrepancy_without_narrative_singletons(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_service = _LcOpsCompatibilityRulesService()

    monkeypatch.setattr(rules_service_module, "get_rules_service", lambda: fake_service)

    async def _fake_inject_semantic_conditions(rules, document_data, evaluator):
        return rules, {}

    monkeypatch.setattr(
        validator_module,
        "_inject_semantic_conditions",
        _fake_inject_semantic_conditions,
    )

    results = await validator_module.validate_document_async(
        {
            "domain": "icc.ucp600",
            "jurisdiction": "global",
            "supplement_domains": ["icc.isbp745"],
            "lc": {
                "beneficiary_name": "Bangladesh Export Ltd",
                "requirements_graph_v1": {
                    "required_document_types": ["insurance_certificate"],
                    "requirements_structured_v1": {
                        "document_quantities": {
                            "insurance_certificate": {"originals_required": 2}
                        }
                    },
                },
            },
            "insurance": {
                "originals_presented": 1,
                "originals_issued": 2,
            },
            "insurance_doc": {
                "originals_presented": 1,
                "originals_issued": 2,
            },
        },
        document_type="commercial_invoice",
    )

    rule_ids = [result.get("rule") for result in results]

    assert "UCP600-28A" in rule_ids
    assert "ISBP745-A1" not in rule_ids


@pytest.mark.asyncio
async def test_validate_document_async_treats_lc_ops_letter_rules_as_discrepancies_without_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _MissingMetadataRulesService:
        async def get_active_ruleset(
            self,
            domain: str,
            jurisdiction: str = "global",
            document_type: str | None = None,
        ) -> dict[str, object] | None:
            if domain == "icc.ucp600":
                return {
                    "rules": [
                        {
                            "rule_id": "UCP600-28A",
                            "domain": "lc_ops",
                            "jurisdiction": "global",
                            "severity": "fail",
                            "deterministic": True,
                            "requires_llm": False,
                            "rule_type": "letter",
                            "title": "Insurance Document: Originals Must Be Presented",
                            "conditions": [
                                {
                                    "field": "insurance_doc.originals_presented",
                                    "operator": "less_than",
                                    "reference_field": "insurance_doc.originals_issued",
                                    "type": "amount_comparison",
                                }
                            ],
                            "expected_outcome": {
                                "valid": ["Presentation complies"],
                                "invalid": [
                                    "Not all issued originals of the insurance document presented."
                                ],
                            },
                        }
                    ],
                    "ruleset_version": "1.0.2",
                    "rulebook_version": "UCP600:2007",
                }
            return {"rules": [], "ruleset_version": "1.0.2", "rulebook_version": domain}

    fake_service = _MissingMetadataRulesService()
    monkeypatch.setattr(rules_service_module, "get_rules_service", lambda: fake_service)

    async def _fake_inject_semantic_conditions(rules, document_data, evaluator):
        return rules, {}

    monkeypatch.setattr(
        validator_module,
        "_inject_semantic_conditions",
        _fake_inject_semantic_conditions,
    )

    results = await validator_module.validate_document_async(
        {
            "domain": "icc.ucp600",
            "jurisdiction": "global",
            "lc": {
                "requirements_graph_v1": {
                    "required_document_types": ["insurance_certificate"],
                },
            },
            "insurance": {
                "originals_presented": 1,
                "originals_issued": 2,
            },
            "insurance_doc": {
                "originals_presented": 1,
                "originals_issued": 2,
            },
        },
        document_type="commercial_invoice",
    )

    rule_ids = [result.get("rule") for result in results]
    assert rule_ids == ["UCP600-28A"]
