"""Typed internal buyer-policy requests enforce bounded manual configuration."""

from __future__ import annotations

import uuid
from datetime import date

import pytest
from pydantic import ValidationError

from app.schemas.proofline_review import BuyerRequirementCreate


def test_buyer_requirement_schema_captures_versioned_policy_scope():
    policy = BuyerRequirementCreate(
        company_id=uuid.uuid4(),
        buyer_reference="BUYER-US-1",
        title="Current environmental clearance",
        description="All Tier 1 dyeing facilities require a current clearance.",
        applicable_party_type="facility",
        product_scope={"hs_codes": ["6109"]},
        jurisdiction="US",
        required_credential_type="EnvironmentalClearance",
        approved_issuer_type="environmental_authority",
        validity_period_days=365,
        severity="high",
        effective_date=date(2026, 7, 1),
        version=3,
        rulhub_mapping={"requirement_id": "rh-12", "article": "Part D"},
    )

    assert policy.version == 3
    assert policy.product_scope["hs_codes"] == ["6109"]
    assert policy.is_active is True


def test_buyer_requirement_schema_rejects_unbounded_or_unknown_fields():
    with pytest.raises(ValidationError):
        BuyerRequirementCreate.model_validate({
            "company_id": str(uuid.uuid4()),
            "buyer_reference": "BUYER-1",
            "title": "Policy",
            "description": "Evidence is required",
            "effective_date": "2026-07-01",
            "severity": "guaranteed",
            "no_code_rule": "not supported",
        })
