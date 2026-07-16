"""Deterministic evaluation of tenant-owned, versioned buyer requirements."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from .base import AdapterResult


BAD_CREDENTIAL_STATES = {"Expired", "Revoked", "Untrusted issuer", "Invalid signature"}


def _applies(policy: Mapping[str, Any], context: Mapping[str, Any]) -> bool:
    jurisdiction = str(policy.get("jurisdiction") or "").upper()
    routes = {"GLOBAL", str(context.get("origin_country") or "").upper(), str(context.get("destination_country") or "").upper()}
    if jurisdiction and jurisdiction not in routes:
        return False
    party_type = policy.get("applicable_party_type")
    if party_type and not any(str(item.get("role")) == str(party_type) for item in context.get("parties", [])):
        return False
    scope = policy.get("product_scope") or {}
    if not isinstance(scope, Mapping) or not scope:
        return True
    case_values = {str(value).strip().lower() for value in (context.get("product"), context.get("commodity"), context.get("hs_code")) if value}
    allowed = {str(value).strip().lower() for raw in scope.values() for value in (raw if isinstance(raw, list) else [raw]) if value}
    return not allowed or bool(case_values & allowed)


def _rule_reference(policy: Mapping[str, Any]) -> dict[str, Any]:
    mapping = policy.get("rulhub_mapping") or {}
    return {
        "id": str(policy.get("id")), "version": str(policy.get("version")),
        "source": "buyer_policy",
        "article": mapping.get("article") if isinstance(mapping, Mapping) else None,
    }


def _finding(policy: Mapping[str, Any], *, observed: str, correction: str) -> dict[str, Any]:
    return {
        "source_finding_id": f"BUYER-POLICY-{policy.get('id')}-V{policy.get('version')}",
        "category": "buyer_requirement", "severity": policy.get("severity") or "medium",
        "title": str(policy.get("title") or "Buyer requirement not satisfied"),
        "explanation": str(policy.get("description") or policy.get("title") or "Buyer evidence is required."),
        "expected": str(policy.get("description") or policy.get("title")), "observed": observed,
        "suggested_correction": correction, "rule_reference": _rule_reference(policy),
    }


class BuyerRequirementsAdapter:
    module = "buyer_requirements"
    version = "proofline-buyer-policy-1"

    async def run(self, context: Mapping[str, Any]) -> AdapterResult:
        policies = [item for item in (context.get("buyer_requirements") or []) if isinstance(item, Mapping) and _applies(item, context)]
        documents = context.get("documents") or {}
        credentials = context.get("ein_verification_results") or []
        findings: list[dict[str, Any]] = []
        evaluations: list[dict[str, Any]] = []
        state_rank = 0
        satisfied = 0
        for policy in policies:
            policy_status = "satisfied"
            document_type = policy.get("required_document_type")
            credential_type = policy.get("required_credential_type")
            if document_type and document_type not in documents:
                policy_status = "evidence_incomplete"
                state_rank = max(state_rank, 2)
                findings.append(_finding(policy, observed=f"Missing required document: {document_type}", correction=f"Upload the current {str(document_type).replace('_', ' ')} requested by the buyer."))
            if credential_type:
                matches = [item for item in credentials if str(item.get("credential_type")) == str(credential_type)]
                credential = matches[0] if matches else None
                observed = str(credential.get("status")) if credential else "Not shared"
                required_issuer = policy.get("approved_issuer_type")
                if credential and observed == "Verified" and required_issuer and credential.get("issuer_type") != required_issuer:
                    observed = "Untrusted issuer"
                if observed != "Verified":
                    policy_status = "issue_found" if observed in BAD_CREDENTIAL_STATES else "evidence_incomplete"
                    state_rank = max(state_rank, 3 if policy_status == "issue_found" else 2)
                    findings.append(_finding(policy, observed=observed, correction="Share a current EIN credential from an approved issuer or provide alternate evidence for analyst review."))
            if not document_type and not credential_type:
                policy_status = "pending_review"
                state_rank = max(state_rank, 1)
                findings.append(_finding(policy, observed="Manual evidence assessment required", correction="Ask the analyst to identify and confirm the evidence that satisfies this buyer policy."))
            if policy_status == "satisfied":
                satisfied += 1
            evaluations.append({"requirement_id": str(policy.get("id")), "version": int(policy.get("version") or 1), "status": policy_status})
        state = {0: "clear", 1: "pending_review", 2: "evidence_incomplete", 3: "issue_found"}[state_rank]
        material = json.dumps([(item.get("requirement_id"), item.get("version")) for item in evaluations], sort_keys=True).encode("utf-8")
        return AdapterResult(
            state=state,
            summary=f"{satisfied} of {len(policies)} applicable buyer requirement(s) satisfied.",
            findings=findings, source_record_type="buyer_policy_evaluation",
            source_record_id=f"buyer-policy-{hashlib.sha256(material).hexdigest()[:16]}",
            metadata={"satisfied": satisfied, "total": len(policies), "requirements": evaluations},
        )


__all__ = ["BuyerRequirementsAdapter"]
