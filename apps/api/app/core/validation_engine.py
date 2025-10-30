"""
Lightweight validation engine facsimile for test environments.

The production system provides a comprehensive rule engine that can surface
explanations, regulatory references, and fix suggestions for discrepancies.
For documentation builds and unit tests we only need deterministic, side-effect
free helpers so higher level services (e.g. LLM assist) can run without the
full engine.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class ValidationEngine:
    """Minimal stub providing rule lookup utilities used in tests."""

    _DEFAULT_REFERENCE = {
        "regulation": "UCP 600",
        "article": "14.a",
        "description": "Documents must comply with the credit terms.",
    }

    def get_rule_explanation(self, rule_code: str, language: str = "en") -> str:
        """
        Return a human-friendly explanation for a rule.

        The stub returns templated text; in production this would pull from a
        knowledge base with multi-language support.
        """
        base = (
            f"Rule {rule_code or 'UNKNOWN'} requires all submitted documents "
            "to match the letter of credit conditions."
        )
        if language.lower().startswith("bn"):
            return "এই নিয়ম অনুযায়ী সব নথি এলসি শর্ত অনুসারে হতে হবে।"
        return base

    def get_rule_reference(self, rule_code: str) -> Optional[Dict[str, str]]:
        """
        Return the regulatory reference for a rule.

        The stub maps known codes to a generic UCP reference.
        """
        if not rule_code:
            return None
        reference = self._DEFAULT_REFERENCE.copy()
        reference["rule_code"] = rule_code
        return reference

    def get_fix_suggestion(
        self,
        rule_code: str,
        discrepancy: Dict[str, Any],
        language: str = "en",
    ) -> Optional[str]:
        """
        Provide a simple fix suggestion for a discrepancy.

        Production logic would inspect rule metadata; here we return a generic
        recommendation to review and amend the offending field.
        """
        field = discrepancy.get("field") or discrepancy.get("description", "document")
        suggestion = (
            f"Review the {field} for rule {rule_code or 'UNKNOWN'} and upload a corrected document."
        )
        if language.lower().startswith("bn"):
            return f"{field} পরীক্ষা করুন এবং সংশোধিত নথি জমা দিন।"
        return suggestion
