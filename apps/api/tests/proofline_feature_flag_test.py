"""Proofline can be disabled without changing LCopilot configuration."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.config import settings
from app.services.proofline.feature_flags import require_proofline_enabled


def test_proofline_release_flag_fails_closed(monkeypatch):
    monkeypatch.setattr(settings, "PROOFLINE_ENABLED", False)
    with pytest.raises(HTTPException) as error:
        require_proofline_enabled()
    assert error.value.status_code == 404


def test_proofline_release_flag_does_not_depend_on_lcopilot_checkout(monkeypatch):
    monkeypatch.setattr(settings, "PROOFLINE_ENABLED", True)
    monkeypatch.setattr(settings, "STRIPE_CHECKOUT_ENABLED", False)
    assert require_proofline_enabled() is None
