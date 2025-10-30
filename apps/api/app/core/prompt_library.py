"""
Minimal prompt library used for testing AI assistance flows.
"""

from __future__ import annotations

from typing import Dict

from .validation_engine import ValidationEngine


class PromptLibrary:
    """Provide deterministic prompt templates for unit tests."""

    def __init__(self):
        self.validation_engine = ValidationEngine()

    def get_bank_template(self, language):
        """Return a simple bank discrepancy notification template."""
        if str(language).lower().startswith("bn"):
            return "ব্যাংক অবহিতকরণ:\n{discrepancies}\nতারিখ: {date}"
        return "Bank Notice:\n{discrepancies}\nDate: {date}"

    def get_amendment_template(self, amendment_type: str, language):
        """Return a formatted amendment template."""
        if str(language).lower().startswith("bn"):
            return "অ্যামেন্ডমেন্ট ({amendment_type}): {details}"
        return "Amendment ({amendment_type}): {details}"

    def get_chat_help_prompts(self) -> Dict[str, str]:
        """Return canned chat helper prompts."""
        return {
            "en": "How can I help you with your LC validation?",
            "bn": "আমি কীভাবে আপনার এলসি যাচাইকরণে সাহায্য করতে পারি?",
        }
