import asyncio
import json
from pathlib import Path
import sys

import pytest

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.services import validator as validator_module
from app.services import rules_service as rules_service_module
from app.services.validator import validate_document_async
from app.services.validator_rules_loader import load_rules_with_provenance
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


class _FakeRulesServicePrimaryOnly:
    async def get_active_ruleset(self, domain, jurisdiction, document_type=None):
        if domain == "icc.ucp600":
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
                        "title": "Primary Test Rule",
                        "document_type": document_type,
                        "severity": "warning",
                        "conditions": [],
                    }
                ],
            }
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


@pytest.mark.asyncio
async def test_validate_document_async_skips_missing_supplement_rulesets(monkeypatch):
    monkeypatch.setattr(rules_service_module, "get_rules_service", lambda: _FakeRulesServicePrimaryOnly())
    monkeypatch.setattr(validator_module, "RuleEvaluator", lambda: _FakeEvaluator())

    issues = await validate_document_async(
        {
            "domain": "icc.ucp600",
            "jurisdiction": "global",
            "supplement_domains": ["regulations.bd", "sanctions.screening"],
            "lc": {},
        },
        "commercial_invoice",
    )

    assert issues
    assert issues[0]["ruleset_domain"] == "icc.ucp600"


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


@pytest.mark.asyncio
async def test_phasea_loader_snapshot_primary_plus_supplements():
    service = _FakeRulesServicePrimaryOnly()
    aggregated, base_meta, provenance = await load_rules_with_provenance(
        rules_service=service,
        domain_sequence=["icc.ucp600", "icc.urr725"],
        jurisdiction="global",
        document_type="commercial_invoice",
    )

    snapshot = {
        "rule_ids": [r.get("rule_id") for r, _ in aggregated],
        "base_meta": base_meta,
        "provenance": provenance,
    }
    assert json.dumps(snapshot, sort_keys=True, indent=2) == json.dumps(
        {
            "rule_ids": ["UCP-TEST-1"],
            "base_meta": {
                "ruleset_id": "11111111-1111-1111-1111-111111111111",
                "domain": "icc.ucp600",
                "jurisdiction": "global",
                "ruleset_version": "1.2.3",
                "rulebook_version": "UCP600:2007",
                "rule_count_used": 1,
            },
            "provenance": [
                {
                    "ruleset_id": "11111111-1111-1111-1111-111111111111",
                    "ruleset_version": "1.2.3",
                    "domain": "icc.ucp600",
                    "jurisdiction": "global",
                    "rule_count_used": 1,
                }
            ],
        },
        sort_keys=True,
        indent=2,
    )


@pytest.mark.asyncio
async def test_phasea_validate_document_snapshot_with_supplement_tolerance(monkeypatch):
    monkeypatch.setattr(rules_service_module, "get_rules_service", lambda: _FakeRulesServicePrimaryOnly())
    monkeypatch.setattr(validator_module, "RuleEvaluator", lambda: _FakeEvaluator())

    payload = {
        "domain": "icc.ucp600",
        "jurisdiction": "global",
        "supplement_domains": ["regulations.bd"],
        "lc": {},
    }
    issues, provenance = await validate_document_async(
        payload,
        "commercial_invoice",
        return_provenance=True,
    )

    snapshot = {
        "rules": [
            {
                "rule": i.get("rule"),
                "ruleset_domain": i.get("ruleset_domain"),
                "ruleset_version": i.get("ruleset_version"),
                "jurisdiction": i.get("jurisdiction"),
            }
            for i in issues
        ],
        "provenance": provenance,
        "execution": payload.get("_db_rules_execution"),
    }

    assert json.dumps(snapshot, sort_keys=True, indent=2) == json.dumps(
        {
            "rules": [
                {
                    "rule": "UCP-TEST-1",
                    "ruleset_domain": "icc.ucp600",
                    "ruleset_version": "1.2.3",
                    "jurisdiction": "global",
                }
            ],
            "provenance": {
                "success": True,
                "domain": "icc.ucp600",
                "jurisdiction": "global",
                "ruleset_id": "11111111-1111-1111-1111-111111111111",
                "ruleset_version": "1.2.3",
                "rule_count_used": 1,
                "rulesets": [
                    {
                        "ruleset_id": "11111111-1111-1111-1111-111111111111",
                        "ruleset_version": "1.2.3",
                        "domain": "icc.ucp600",
                        "jurisdiction": "global",
                        "rule_count_used": 1,
                    }
                ],
            },
            "execution": {
                "success": True,
                "domain": "icc.ucp600",
                "jurisdiction": "global",
                "ruleset_id": "11111111-1111-1111-1111-111111111111",
                "ruleset_version": "1.2.3",
                "rule_count_used": 1,
                "rulesets": [
                    {
                        "ruleset_id": "11111111-1111-1111-1111-111111111111",
                        "ruleset_version": "1.2.3",
                        "domain": "icc.ucp600",
                        "jurisdiction": "global",
                        "rule_count_used": 1,
                    }
                ],
            },
        },
        sort_keys=True,
        indent=2,
    )
