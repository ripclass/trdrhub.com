"""Proofline adapter over the existing fail-closed sanctions service."""

from __future__ import annotations

from typing import Any, Mapping

from app.services.sanctions_rulhub import ScreeningUnavailable, screen_via_rulhub

from .base import AdapterResult


class SanctionsAdapter:
    module = "sanctions"
    version = "rulhub-sanctions-1"

    async def run(self, context: Mapping[str, Any]) -> AdapterResult:
        findings: list[dict[str, Any]] = []
        screening_ids: list[str] = []
        list_versions: dict[str, Any] = {}
        for party in context.get("parties", []):
            name = str(party.get("name") or "").strip()
            if not name:
                continue
            try:
                result = await screen_via_rulhub(
                    query=name,
                    screening_type="entity",
                    entity=name,
                    country=party.get("country_code"),
                )
            except ScreeningUnavailable as exc:
                raise TimeoutError("Sanctions screening unavailable") from exc
            if result.get("status") == "unavailable":
                raise TimeoutError("Sanctions coverage unavailable")
            if result.get("screening_id"):
                screening_ids.append(str(result["screening_id"]))
            list_versions.update(result.get("list_versions") or {})
            for index, match in enumerate(result.get("matches") or []):
                match_type = match.get("match_type")
                findings.append({
                    "source_finding_id": f"SANCTIONS-{party.get('id')}-{index}",
                    "category": "restricted_party",
                    "severity": "critical" if match_type == "hit" else "high",
                    "title": "Sanctions match requires review" if match_type == "hit" else "Possible sanctions match requires review",
                    "explanation": result.get("recommendation") or "A designated-party screening result requires analyst review.",
                    "affected_entity": name,
                    "expected": "No designated-party match on the screened lists",
                    "observed": f"{match.get('list_name')}: {match.get('matched_name')}",
                    "suggested_correction": "Do not proceed on this result alone. Compare identifiers and escalate to the qualified reviewer.",
                    "rule_reference": {
                        "id": match.get("source_id") or match.get("list_code"),
                        "source": match.get("list_name"),
                        "version": list_versions.get(match.get("list_code")),
                    },
                    "visibility": "internal",
                })
        return AdapterResult(
            state="issue_found" if findings else "clear",
            summary=(
                f"Party screening produced {len(findings)} match(es) requiring review."
                if findings else "No designated-party matches were returned by the screened lists."
            ),
            findings=findings,
            source_record_type="sanctions_screening",
            source_record_id=screening_ids[0] if screening_ids else None,
            metadata={"screening_ids": screening_ids, "list_versions": list_versions},
        )


__all__ = ["SanctionsAdapter"]
