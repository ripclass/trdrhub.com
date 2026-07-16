"""Cross-document adapter over TRDRHub's deterministic comparison engine."""

from __future__ import annotations

from typing import Any, Mapping

from app.services.crossdoc import run_cross_document_checks

from .base import AdapterResult


class DocumentReviewAdapter:
    module = "document_review"
    version = "icc.lcopilot.crossdoc"

    async def run(self, context: Mapping[str, Any]) -> AdapterResult:
        documents = [
            {
                "id": item.get("document_id"),
                "name": item.get("filename"),
                "type": item.get("type"),
                "document_type": item.get("type"),
            }
            for item in context.get("document_records", [])
        ]
        raw = run_cross_document_checks({
            "lc": context.get("lc") or {},
            "invoice": context.get("invoice") or {},
            "bill_of_lading": context.get("bill_of_lading") or {},
            "documents_presence": context.get("documents_presence") or {},
            "documents": documents,
        })
        findings: list[dict[str, Any]] = []
        for issue in raw:
            rule = str(issue.get("rule") or "CROSSDOC-FINDING")
            findings.append({
                "source_finding_id": rule,
                "category": issue.get("category") or "cross_document",
                "severity": issue.get("severity") or "major",
                "title": issue.get("title") or "Cross-document discrepancy",
                "explanation": issue.get("message") or "Submitted document fields are inconsistent.",
                "expected": issue.get("expected") or "Consistent values across the submitted documents",
                "observed": issue.get("actual") or issue.get("found") or "Inconsistent values were found",
                "suggested_correction": issue.get("suggestion") or "Correct the affected document or provide approved supporting evidence.",
                "rule_reference": {
                    "id": rule,
                    "source": "TRDRHub deterministic cross-document engine",
                    "domain": issue.get("ruleset_domain") or "icc.lcopilot.crossdoc",
                },
                "evidence_references": [
                    {"document_id": str(value)} for value in (issue.get("document_ids") or [])
                ],
            })
        return AdapterResult(
            state="issue_found" if findings else "clear",
            summary=f"Cross-document review produced {len(findings)} finding(s).",
            findings=findings,
            source_record_type="cross_document_review",
        )


__all__ = ["DocumentReviewAdapter"]
