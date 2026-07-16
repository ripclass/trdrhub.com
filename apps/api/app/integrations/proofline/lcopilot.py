"""Proofline adapter over LCopilot's existing deterministic services."""

from __future__ import annotations

from typing import Any, Mapping

from app.services.validator import validate_document_async

from .base import AdapterResult


def _source_issues(result: Mapping[str, Any]) -> list[dict[str, Any]]:
    for key in ("issues", "issue_cards", "discrepancies"):
        values = result.get(key)
        if isinstance(values, list):
            return [item for item in values if isinstance(item, dict)]
    return []


def _finding(issue: Mapping[str, Any]) -> dict[str, Any]:
    rule = str(issue.get("rule") or issue.get("rule_id") or "LCOPILOT-FINDING")
    return {
        "source_finding_id": rule,
        "category": issue.get("category") or "letter_of_credit",
        "severity": issue.get("severity") or "major",
        "title": issue.get("title") or issue.get("rule_name") or "LCopilot finding",
        "explanation": issue.get("message") or issue.get("description") or "LCopilot identified a discrepancy.",
        "affected_document_id": issue.get("document_id"),
        "affected_field": issue.get("field") or issue.get("field_name"),
        "expected": issue.get("expected") or issue.get("expected_value") or "Compliant LC or presentation data",
        "observed": issue.get("actual") or issue.get("found") or issue.get("actual_value") or "A discrepancy was identified",
        "suggested_correction": issue.get("suggestion") or issue.get("suggested_fix") or "Review and correct the cited LC discrepancy.",
        "rule_reference": {
            "id": rule,
            "source": "LCopilot",
            "domain": issue.get("ruleset_domain") or "icc.lcopilot",
        },
        "evidence_references": [
            {"document_id": str(value)} for value in (issue.get("document_ids") or [])
        ],
    }


class LCopilotAdapter:
    module = "lcopilot"
    version = "lcopilot-shared-services-1"

    async def run(self, context: Mapping[str, Any]) -> AdapterResult:
        source = context.get("source_lcopilot_result")
        if isinstance(source, dict):
            issues = [_finding(item) for item in _source_issues(source)]
            return AdapterResult(
                state="issue_found" if issues else "clear",
                summary=f"Reused completed LCopilot review with {len(issues)} finding(s).",
                findings=issues,
                source_record_type="validation_session",
                source_record_id=context.get("source_lcopilot_session_id"),
                metadata={"reused_existing_work": True},
            )

        lc_records = [
            item
            for item in context.get("document_records", [])
            if item.get("canonical_type") == "letter_of_credit"
        ]
        if not lc_records:
            return AdapterResult(
                state="evidence_incomplete",
                summary="A letter of credit is required for this payment arrangement.",
                findings=[{
                    "source_finding_id": "LCOPILOT-LC-MISSING",
                    "category": "document_presence",
                    "severity": "high",
                    "title": "Letter of credit is missing",
                    "explanation": "LCopilot cannot evaluate the instrument until the LC is linked to the case.",
                    "expected": "A readable current letter of credit",
                    "observed": "No LC was submitted",
                    "suggested_correction": "Upload the LC or upgrade a completed LCopilot review.",
                }],
            )
        raw: list[dict[str, Any]] = []
        for record in lc_records:
            results = await validate_document_async(record.get("fields") or {}, "letter_of_credit")
            raw.extend(
                item for item in results
                if isinstance(item, dict)
                and not item.get("passed", False)
                and not item.get("not_applicable", False)
            )
        issues = [_finding(item) for item in raw]
        return AdapterResult(
            state="issue_found" if issues else "clear",
            summary=f"LCopilot evaluated the submitted LC and produced {len(issues)} finding(s).",
            findings=issues,
            source_record_type="proofline_document_set",
            source_record_id=str(lc_records[0].get("document_id")),
            metadata={"reused_existing_work": False},
        )


__all__ = ["LCopilotAdapter"]
