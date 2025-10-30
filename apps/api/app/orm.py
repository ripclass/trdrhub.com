"""
Compatibility shim for legacy imports like ``from app.orm import User``.

This module re-exports ORM models and enums from the canonical
``app.models`` module to preserve backward compatibility with
older code and deployment scripts.
"""

from .models import (
    User,
    UserRole,
    ValidationSession,
    Document,
    Discrepancy,
    DiscrepancySeverity,
    Report,
)

__all__ = [
    "User",
    "UserRole",
    "ValidationSession",
    "Document",
    "Discrepancy",
    "DiscrepancySeverity",
    "Report",
]


