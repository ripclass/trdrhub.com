"""Consent-scoped EIN verification adapter; no wallet or credential duplication."""

from __future__ import annotations

from typing import Any, Mapping

from app.services.ein_client import EINClient, get_ein_client

from .base import AdapterResult


STATUS_LABELS = {
    "verified": "Verified", "expired": "Expired", "revoked": "Revoked",
    "missing": "Missing", "untrusted_issuer": "Untrusted issuer",
    "untrusted issuer": "Untrusted issuer", "invalid_signature": "Invalid signature",
    "invalid signature": "Invalid signature", "not_shared": "Not shared",
    "not shared": "Not shared", "unable_to_verify": "Unable to verify",
    "unable to verify": "Unable to verify",
}
ISSUE_STATUSES = {"Expired", "Revoked", "Untrusted issuer", "Invalid signature"}
INCOMPLETE_STATUSES = {"Missing", "Not shared"}


def _presentation_request(row: Mapping[str, Any]) -> dict[str, Any] | None:
    reference = row.get("presentation_reference")
    consent = row.get("consent_reference")
    if not reference or not consent:
        return None
    return {
        key: value for key, value in {
            "presentation_reference": str(reference),
            "consent_reference": str(consent),
            "credential_type": row.get("credential_type"),
            "subject_reference": row.get("subject_reference"),
            "requested_claims": list(row.get("requested_claims") or []),
        }.items() if value not in (None, "", [])
    }


def _safe_result(row: Mapping[str, Any]) -> dict[str, Any]:
    raw_status = str(row.get("status") or "Unable to verify")
    status = STATUS_LABELS.get(raw_status.strip().lower(), "Unable to verify")
    return {
        key: value for key, value in {
            "presentation_reference": row.get("presentation_reference"),
            "credential_type": row.get("credential_type"),
            "subject_reference": row.get("subject_reference"),
            "issuer_reference": row.get("issuer_reference"),
            "issuer_type": row.get("issuer_type"),
            "status": status,
            "issued_at": row.get("issued_at") or row.get("issuance_date"),
            "expiration_date": row.get("expiration_date") or row.get("expires_at"),
            "credential_hash": row.get("credential_hash") or row.get("hash"),
            "disclosed_claims": dict(row.get("disclosed_claims") or {}),
        }.items() if value not in (None, "", {})
    }


class EINVerificationAdapter:
    module = "ein"
    version = "ein-api-v1"

    def __init__(self, client: EINClient | None = None) -> None:
        self.client = client or get_ein_client()

    async def run(self, context: Mapping[str, Any]) -> AdapterResult:
        presentations = [
            request for row in (context.get("ein_presentations") or [])
            if isinstance(row, Mapping)
            if (request := _presentation_request(row)) is not None
        ]
        if not presentations:
            return AdapterResult(
                state="evidence_incomplete",
                summary="EIN verification was requested, but no consented credential presentation was shared.",
                findings=[{
                    "source_finding_id": "EIN-PRESENTATION-NOT-SHARED",
                    "category": "credential_evidence", "severity": "medium",
                    "title": "EIN credential presentation not shared",
                    "explanation": "Proofline cannot verify a credential without an EIN presentation and consent reference.",
                    "expected": "A consented EIN credential presentation", "observed": "Not shared",
                    "suggested_correction": "Share the requested presentation through EIN or ask the analyst to use other evidence.",
                }],
                source_record_type="ein_verification_request",
                metadata={"verification_results": []},
            )
        response = await self.client.verify_presentations({
            "trade_case_reference": str(context.get("trade_case_id")),
            "presentations": presentations,
        })
        safe_results = [_safe_result(row) for row in (response.get("results") or []) if isinstance(row, Mapping)]
        findings: list[dict[str, Any]] = []
        for index, item in enumerate(safe_results):
            status = item.get("status", "Unable to verify")
            if status == "Verified":
                continue
            severity = "high" if status in ISSUE_STATUSES else "medium"
            reference = item.get("presentation_reference") or f"presentation-{index + 1}"
            findings.append({
                "source_finding_id": f"EIN-{str(reference).upper()}-{str(status).upper().replace(' ', '-')}",
                "category": "credential_evidence", "severity": severity,
                "title": f"Credential status: {status}",
                "explanation": "EIN did not return a current, trusted verification for the requested credential.",
                "affected_entity": item.get("subject_reference"),
                "expected": "Verified", "observed": status,
                "suggested_correction": "Share a current credential from a trusted issuer or provide alternate evidence for analyst review.",
                "evidence_references": [{
                    "credential_reference": item.get("presentation_reference"),
                    "credential_hash": item.get("credential_hash"),
                    "issuer": item.get("issuer_reference"),
                }],
            })
        statuses = {str(item.get("status")) for item in safe_results}
        if statuses & ISSUE_STATUSES:
            state = "issue_found"
        elif statuses & INCOMPLETE_STATUSES:
            state = "evidence_incomplete"
        elif "Unable to verify" in statuses or not safe_results:
            state = "unable_to_assess"
        else:
            state = "clear"
        return AdapterResult(
            state=state,
            summary=f"EIN returned {len(safe_results)} credential verification result(s).",
            findings=findings,
            source_record_type="ein_verification",
            source_record_id=str(response.get("verification_id") or "") or None,
            metadata={
                "verification_id": response.get("verification_id"),
                "verified_at": response.get("verified_at"),
                "verification_results": safe_results,
            },
        )


__all__ = ["EINVerificationAdapter"]
