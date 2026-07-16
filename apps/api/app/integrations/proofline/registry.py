"""Production Proofline adapter registry."""

from __future__ import annotations

from .document_review import DocumentReviewAdapter
from .lcopilot import LCopilotAdapter
from .open_account import OpenAccountAdapter
from .regulatory import CBAMAdapter, EUDRAdapter
from .rulhub import RulHubRequirementsAdapter
from .sanctions import SanctionsAdapter


def build_adapter_registry() -> dict[str, object | None]:
    return {
        "lcopilot": LCopilotAdapter(),
        "open_account_review": OpenAccountAdapter(),
        "document_review": DocumentReviewAdapter(),
        "sanctions": SanctionsAdapter(),
        "rulhub": RulHubRequirementsAdapter(),
        "cbam": CBAMAdapter(),
        "eudr": EUDRAdapter(),
        # EIN remains API-only. Until production credentials are configured,
        # run_check persists a visible pending-review state rather than a mock.
        "ein": None,
        "buyer_requirements": None,
    }


__all__ = ["build_adapter_registry"]
