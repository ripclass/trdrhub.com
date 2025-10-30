"""
Compatibility shim for legacy imports like ``from app.orm import User``.

This package re-exports ORM models and enums from the canonical
``app.models`` module to preserve backward compatibility with
older code and deployment scripts. Converting this shim to a package
ensures environments that expect ``app.orm`` to be a package continue
to work without ModuleNotFoundError issues.
"""

from ..models import (
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

"""
Compatibility shim for legacy imports like ``from app.orm import User``.

This package re-exports ORM models and enums from the canonical
``app.models`` module to preserve backward compatibility with
older code and deployment scripts. Converting this shim to a package
ensures environments that expect ``app.orm`` to be a package continue
to work without ModuleNotFoundError issues.
"""

from ..models import (
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
