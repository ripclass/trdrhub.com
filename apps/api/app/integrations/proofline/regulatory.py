"""Proofline adapters over existing CBAM and EUDR applicability services."""

from __future__ import annotations

from typing import Any, Callable, Mapping

from app.services.readiness import cbam_scope_verdict, eudr_scope_verdict

from .base import AdapterResult


class _ScopeAdapter:
    module: str
    version = "trdrhub-readiness-scope-1"
    verdict: Callable[[dict[str, Any]], dict[str, Any]]

    async def run(self, context: Mapping[str, Any]) -> AdapterResult:
        answers = context.get(f"{self.module}_answers") or {}
        if not isinstance(answers, dict) or not answers:
            return AdapterResult(
                state="evidence_incomplete",
                summary=f"{self.module.upper()} was requested but the scope evidence is incomplete.",
                findings=[{
                    "source_finding_id": f"{self.module.upper()}-SCOPE-EVIDENCE",
                    "category": "regulatory_evidence",
                    "severity": "medium",
                    "title": f"{self.module.upper()} scope evidence is incomplete",
                    "explanation": f"The existing {self.module.upper()} Check cannot resolve scope without its required transaction answers.",
                    "expected": f"Completed {self.module.upper()} applicability answers and supporting evidence",
                    "observed": "The module was requested without complete scope inputs",
                    "suggested_correction": f"Complete the {self.module.upper()} Check intake or ask the analyst to resolve applicability.",
                }],
            )
        result = self.verdict(answers)
        verdict = str(result.get("verdict") or "borderline")
        if verdict == "likely_out_of_scope":
            state = "clear"
        elif verdict == "borderline":
            state = "pending_review"
        else:
            state = "evidence_incomplete"
        return AdapterResult(
            state=state,
            summary=" ".join(str(item) for item in (result.get("reasons") or [])),
            metadata={"scope_verdict": verdict, "deadline_note": result.get("deadline_note")},
        )


class CBAMAdapter(_ScopeAdapter):
    module = "cbam"
    verdict = staticmethod(cbam_scope_verdict)


class EUDRAdapter(_ScopeAdapter):
    module = "eudr"
    verdict = staticmethod(eudr_scope_verdict)


__all__ = ["CBAMAdapter", "EUDRAdapter"]
