"""Proofline release controls independent from established TRDRHub tools."""

from __future__ import annotations

from fastapi import HTTPException

from app.config import settings


def is_proofline_enabled() -> bool:
    return bool(getattr(settings, "PROOFLINE_ENABLED", True))


def require_proofline_enabled() -> None:
    if not is_proofline_enabled():
        raise HTTPException(status_code=404, detail="Proofline is not enabled")


__all__ = ["is_proofline_enabled", "require_proofline_enabled"]
