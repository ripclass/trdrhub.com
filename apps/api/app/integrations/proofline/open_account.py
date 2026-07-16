"""Adapter for Proofline's deterministic open-account evidence checks."""

from __future__ import annotations

from typing import Any, Mapping

from app.services.proofline.open_account import run_open_account_checks

from .base import AdapterResult


class OpenAccountAdapter:
    module = "open_account_review"
    version = "proofline-open-account-1"

    async def run(self, context: Mapping[str, Any]) -> AdapterResult:
        result = run_open_account_checks(context)
        return AdapterResult(
            state=result.state,
            summary=(
                "Open-account evidence is complete and internally consistent."
                if not result.findings
                else f"Open-account review produced {len(result.findings)} finding(s)."
            ),
            findings=result.findings,
            source_record_type="proofline_open_account",
            metadata={
                "expected_payment_date": (
                    result.expected_payment_date.isoformat()
                    if result.expected_payment_date
                    else None
                ),
                "rule_references": result.rule_references,
            },
        )


__all__ = ["OpenAccountAdapter"]

