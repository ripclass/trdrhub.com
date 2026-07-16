"""Production Proofline adapter registry."""

from __future__ import annotations

from app.services.ein_client import is_ein_configured

from .buyer_requirements import BuyerRequirementsAdapter
from .document_review import DocumentReviewAdapter
from .ein import EINVerificationAdapter
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
        # EIN remains API-only. Without live server credentials, run_check
        # persists pending-review rather than presenting mock verification.
        "ein": EINVerificationAdapter() if is_ein_configured() else None,
        "buyer_requirements": BuyerRequirementsAdapter(),
    }


__all__ = ["build_adapter_registry"]
