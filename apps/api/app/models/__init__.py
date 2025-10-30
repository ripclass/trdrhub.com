"""
Lightweight models package initializer.

Avoid importing every submodule here to prevent circular imports during
application startup. Only expose the core ORM classes needed by modules that
do `from app.models import User`, etc.
"""

# Re-export core ORM classes defined in app/models.py
from ..models import (  # noqa: F401
    User,
    ValidationSession,
    Document,
    Discrepancy,
    Report,
)

__all__ = [
    "User",
    "ValidationSession",
    "Document",
    "Discrepancy",
    "Report",
]