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
from app.services import validator_rule_executor as executor_module
from app.services.validator import validate_document_async
from app.services.validator_rules_loader import load_rules_with_provenance
from app.services.validator_supplement_router import resolve_domain_sequence
from app.services.validator_verdict_builder import build_validation_provenance, build_validation_results
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


class _FakeRulesServiceSemantic:
    async def get_active_ruleset(self, domain, jurisdiction, document_type=None):
        if domain != "icc.ucp600":
            return None
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
                    "rule_id": "SEM-TEST-1",
                    "title": "Semantic goods consistency",
                    "document_type": document_type,
                    "severity": "major",
                    "documents": ["commercial_invoice"],
                    "conditions": [
                        {
                            "field": "invoice.goods_description",
                            "value_ref": "bill_of_lading.goods_description",
                            "operator": "semantic_check",
                            "message": "Goods description mismatch",
                            "semantic": {
                                "context": "goods consistency",
                                "documents": ["invoice", "bill_of_lading"],
                                "threshold": 0.8,
                                "enable_ai": False,
                            },
                        }
                    ],
                }
            ],
        }


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
    monkeypatch.setattr(executor_module, "RuleEvaluator", lambda: _FakeEvaluator())

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
    monkeypatch.setattr(executor_module, "RuleEvaluator", lambda: _FakeEvaluator())

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
    monkeypatch.setattr(executor_module, "RuleEvaluator", lambda: _FakeEvaluator())

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


@pytest.mark.asyncio
async def test_phaseb_semantic_execution_snapshot(monkeypatch):
    async def _fake_semantic_compare(*_args, **_kwargs):
        return {
            "match": False,
            "score": 0.32,
            "expected": "LC says cotton shirts",
            "found": "B/L says polyester shirts",
            "documents": ["invoice", "bill_of_lading"],
            "suggested_fix": "Align BL goods description with invoice and LC",
        }

    monkeypatch.setattr(rules_service_module, "get_rules_service", lambda: _FakeRulesServiceSemantic())
    monkeypatch.setattr(executor_module, "run_semantic_comparison", _fake_semantic_compare)

    payload = {
        "domain": "icc.ucp600",
        "jurisdiction": "global",
        "lc": {"goods_description": "cotton shirts"},
        "invoice": {"goods_description": "cotton shirts"},
        "bill_of_lading": {"goods_description": "polyester shirts"},
    }

    issues, provenance = await validate_document_async(payload, "commercial_invoice", return_provenance=True)

    snapshot = {
        "rule": issues[0]["rule"],
        "passed": issues[0]["passed"],
        "severity": issues[0]["severity"],
        "message": issues[0]["message"],
        "expected": issues[0].get("expected"),
        "actual": issues[0].get("actual"),
        "suggestion": issues[0].get("suggestion"),
        "documents": issues[0].get("documents"),
        "semantic_match": issues[0].get("semantic_differences", [{}])[0].get("match"),
        "provenance_rule_count": provenance.get("rule_count_used"),
    }

    assert json.dumps(snapshot, sort_keys=True, indent=2) == json.dumps(
        {
            "rule": "SEM-TEST-1",
            "passed": False,
            "severity": "major",
            "message": "Goods description mismatch",
            "expected": "LC says cotton shirts",
            "actual": "B/L says polyester shirts",
            "suggestion": "Align BL goods description with invoice and LC",
            "documents": ["commercial_invoice"],
            "semantic_match": False,
            "provenance_rule_count": 1,
        },
        sort_keys=True,
        indent=2,
    )


def test_phasec_router_snapshot_detected_plus_explicit_supplements():
    payload = {
        "jurisdiction": "global",
        "lc_text": "This credit is subject to UCP 600 and eUCP Version 2.1. Reimbursement under URR 725.",
        "supplement_domains": ["regulations.bd"],
    }

    sequence = resolve_domain_sequence(payload)
    assert json.dumps(sequence, sort_keys=True, indent=2) == json.dumps(
        ["icc.ucp600", "icc.eucp2.1", "icc.urr725", "regulations.bd", "icc.lcopilot.crossdoc"],
        sort_keys=True,
        indent=2,
    )


def test_phasec_verdict_builder_snapshot():
    outcomes = [{"rule_id": "UCP-TEST-1", "passed": False, "severity": "warning", "message": "failed"}]
    rule_envelopes = [{
        "rule": {
            "rule_id": "UCP-TEST-1",
            "title": "Primary Test Rule",
            "document_type": "commercial_invoice",
            "severity": "warning",
            "documents": ["commercial_invoice"],
        },
        "meta": {
            "ruleset_id": "11111111-1111-1111-1111-111111111111",
            "domain": "icc.ucp600",
            "jurisdiction": "global",
            "ruleset_version": "1.2.3",
            "rulebook_version": "UCP600:2007",
            "rule_count_used": 1,
        },
    }]
    document_data = {}

    results = build_validation_results(
        outcomes=outcomes,
        rule_envelopes=rule_envelopes,
        document_data=document_data,
        semantic_registry={},
        base_metadata=rule_envelopes[0]["meta"],
    )
    provenance = build_validation_provenance(
        base_metadata=rule_envelopes[0]["meta"],
        jurisdiction="global",
        prepared_rule_count=1,
        provenance_rulesets=[{
            "ruleset_id": "11111111-1111-1111-1111-111111111111",
            "ruleset_version": "1.2.3",
            "domain": "icc.ucp600",
            "jurisdiction": "global",
            "rule_count_used": 1,
        }],
    )

    snapshot = {"result": results[0], "provenance": provenance}
    assert json.dumps(snapshot, sort_keys=True, indent=2) == json.dumps(
        {
            "result": {
                "rule": "UCP-TEST-1",
                "title": "Primary Test Rule",
                "description": None,
                "article": None,
                "tags": None,
                "documents": ["commercial_invoice"],
                "display_card": None,
                "expected_outcome": None,
                "passed": False,
                "severity": "warning",
                "message": "failed",
                "ruleset_id": "11111111-1111-1111-1111-111111111111",
                "ruleset_version": "1.2.3",
                "rulebook_version": "UCP600:2007",
                "ruleset_domain": "icc.ucp600",
                "jurisdiction": "global",
                "rule_count_used": 1,
            },
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
        },
        sort_keys=True,
        indent=2,
    )
