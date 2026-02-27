import asyncio
from pathlib import Path
import sys

import pytest

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.services import validator as validator_module
from app.services import rules_service as rules_service_module
from app.services.validator import validate_document_async
from app.routers.validate import _build_db_rules_blocked_structured_result


class _FakeRulesServiceSuccess:
    async def get_active_ruleset(self, domain, jurisdiction, document_type=None):
        return {
            "ruleset": {
                "id": "11111111-1111-1111-1111-111111111111",
                "domain": domain,
                "jurisdiction": jurisdiction,
                "ruleset_version": "1.2.3",
                "rulebook_version": "UCP600:2007",
            },
            "ruleset_version": "1.2.3",
            "rulebook_version": "UCP600:2007",
            "rules": [
                {
                    "rule_id": "UCP-TEST-1",
                    "title": "Test Rule",
                    "document_type": document_type,
                    "severity": "warning",
                    "conditions": [],
                }
            ],
        }


class _FakeRulesServiceNone:
    async def get_active_ruleset(self, domain, jurisdiction, document_type=None):
        return None


class _FakeEvaluator:
    async def evaluate_rules(self, rules, document_data):
        return {
            "outcomes": [
                {
                    "rule_id": "UCP-TEST-1",
                    "passed": False,
                    "severity": "warning",
                    "message": "failed",
                }
            ]
        }

    def resolve_field_path(self, *_args, **_kwargs):
        return None


@pytest.mark.asyncio
async def test_validate_document_async_returns_provenance_fields(monkeypatch):
    monkeypatch.setattr(rules_service_module, "get_rules_service", lambda: _FakeRulesServiceSuccess())
    monkeypatch.setattr(validator_module, "RuleEvaluator", lambda: _FakeEvaluator())

    issues, provenance = await validate_document_async(
        {
            "domain": "icc.ucp600",
            "jurisdiction": "global",
            "supplement_domains": [],
            "lc": {},
        },
        "commercial_invoice",
        return_provenance=True,
    )

    assert issues
    first = issues[0]
    assert first["ruleset_id"] == "11111111-1111-1111-1111-111111111111"
    assert first["ruleset_version"] == "1.2.3"
    assert first["ruleset_domain"] == "icc.ucp600"
    assert first["jurisdiction"] == "global"
    assert first["rule_count_used"] >= 1

    assert provenance["ruleset_id"] == "11111111-1111-1111-1111-111111111111"
    assert provenance["ruleset_version"] == "1.2.3"
    assert provenance["domain"] == "icc.ucp600"
    assert provenance["jurisdiction"] == "global"
    assert provenance["rule_count_used"] >= 1


@pytest.mark.asyncio
async def test_validate_document_async_fail_closed_when_no_active_ruleset(monkeypatch):
    monkeypatch.setattr(rules_service_module, "get_rules_service", lambda: _FakeRulesServiceNone())

    with pytest.raises(RuntimeError, match="Ruleset fetch failed"):
        await validate_document_async(
            {
                "domain": "icc.ucp600",
                "jurisdiction": "global",
                "supplement_domains": [],
                "lc": {},
            },
            "commercial_invoice",
        )


def test_db_blocked_result_has_blocked_verdict_and_provenance():
    result = _build_db_rules_blocked_structured_result(
        reason="timeout",
        processing_duration=0.5,
        documents=[],
        provenance={
            "ruleset_id": None,
            "ruleset_version": None,
            "domain": "icc.ucp600",
            "jurisdiction": "global",
            "rule_count_used": 0,
        },
    )

    assert result["validation_blocked"] is True
    assert result["bank_verdict"]["verdict"] == "BLOCKED"
    assert result["validation_provenance"]["domain"] == "icc.ucp600"
    assert result["validation_provenance"]["jurisdiction"] == "global"
    assert result["validation_provenance"]["rule_count_used"] == 0
