"""EIN verification stays API-bound, consent-scoped, and fail-closed."""

from __future__ import annotations

import asyncio

from app.integrations.proofline.ein import EINVerificationAdapter


class _EINClient:
    async def verify_presentations(self, payload):
        assert payload == {
            "trade_case_reference": "case-1",
            "presentations": [{
                "presentation_reference": "vp-101",
                "consent_reference": "consent-9",
                "credential_type": "EnvironmentalClearance",
                "subject_reference": "facility-7",
                "requested_claims": ["credentialStatus", "expirationDate"],
            }],
        }
        return {
            "verification_id": "ein-verification-1",
            "verified_at": "2026-07-16T10:00:00Z",
            "results": [{
                "presentation_reference": "vp-101",
                "credential_type": "EnvironmentalClearance",
                "subject_reference": "facility-7",
                "issuer_reference": "issuer-3",
                "issuer_type": "environmental_authority",
                "status": "Expired",
                "expiration_date": "2026-06-30",
                "credential_hash": "sha256:abc",
                "disclosed_claims": {"credentialStatus": "expired"},
                "credential_payload": {"must": "not be persisted"},
                "signature": "must-not-be-persisted",
            }],
        }


def test_ein_adapter_persists_only_verification_metadata_and_disclosed_claims():
    adapter = EINVerificationAdapter(client=_EINClient())
    result = asyncio.run(adapter.run({
        "trade_case_id": "case-1",
        "ein_presentations": [{
            "presentation_reference": "vp-101",
            "consent_reference": "consent-9",
            "credential_type": "EnvironmentalClearance",
            "subject_reference": "facility-7",
            "requested_claims": ["credentialStatus", "expirationDate"],
            "raw_credential": "must-not-be-sent",
        }],
    }))

    assert result.state == "issue_found"
    assert result.source_record_id == "ein-verification-1"
    assert result.findings[0]["observed"] == "Expired"
    stored = result.metadata["verification_results"][0]
    assert stored["credential_hash"] == "sha256:abc"
    assert stored["disclosed_claims"] == {"credentialStatus": "expired"}
    assert "credential_payload" not in stored
    assert "signature" not in stored


def test_ein_adapter_marks_requested_but_unshared_presentation_as_incomplete():
    result = asyncio.run(EINVerificationAdapter(client=_EINClient()).run({
        "trade_case_id": "case-2",
        "ein_presentations": [],
    }))

    assert result.state == "evidence_incomplete"
    assert result.findings[0]["observed"] == "Not shared"
    assert "mock" not in result.summary.lower()
