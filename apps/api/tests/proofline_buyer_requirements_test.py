"""Buyer policies are deterministic, versioned evidence checks."""

from __future__ import annotations

import asyncio

from app.integrations.proofline.buyer_requirements import BuyerRequirementsAdapter


def _policy(**overrides):
    values = {
        "id": "policy-1",
        "buyer_reference": "BUYER-US-1",
        "title": "Current environmental clearance",
        "description": "Tier 1 dyeing facilities require current clearance.",
        "applicable_party_type": "facility",
        "product_scope": {},
        "jurisdiction": "US",
        "required_document_type": "environmental_clearance",
        "required_credential_type": None,
        "approved_issuer_type": None,
        "validity_period_days": None,
        "severity": "high",
        "effective_date": "2026-01-01",
        "version": 2,
        "rulhub_mapping": None,
    }
    values.update(overrides)
    return values


def test_buyer_requirements_combine_current_documents_and_verified_ein_results():
    context = {
        "trade_case_id": "case-1",
        "origin_country": "BD",
        "destination_country": "US",
        "parties": [{"role": "facility", "name": "Dye House"}],
        "documents": {"environmental_clearance": {"document_id": "doc-1", "version": 2}},
        "buyer_requirements": [
            _policy(),
            _policy(
                id="policy-2",
                title="Current social audit credential",
                required_document_type=None,
                required_credential_type="SocialComplianceAudit",
                approved_issuer_type="approved_auditor",
            ),
        ],
        "ein_verification_results": [{
            "presentation_reference": "vp-2",
            "credential_type": "SocialComplianceAudit",
            "issuer_type": "approved_auditor",
            "status": "Expired",
        }],
    }

    result = asyncio.run(BuyerRequirementsAdapter().run(context))

    assert result.state == "issue_found"
    assert result.metadata["satisfied"] == 1
    assert result.metadata["total"] == 2
    assert result.findings[0]["observed"] == "Expired"
    assert result.findings[0]["rule_reference"]["version"] == "2"


def test_descriptive_policy_without_machine_evidence_requires_human_review():
    context = {
        "trade_case_id": "case-2",
        "origin_country": "BD",
        "destination_country": "US",
        "parties": [{"role": "seller", "name": "Supplier"}],
        "documents": {},
        "buyer_requirements": [_policy(
            applicable_party_type=None,
            required_document_type=None,
            required_credential_type=None,
        )],
    }

    result = asyncio.run(BuyerRequirementsAdapter().run(context))

    assert result.state == "pending_review"
    assert result.findings[0]["observed"] == "Manual evidence assessment required"
