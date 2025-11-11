"""
Compatibility layer for ``app.models`` imports.

Historically the ORM models lived in ``app/models.py``. When the project grew
into a package-based layout, several modules – plus external deploy scripts –
continued to import classes via ``from app.models import User``.  Importing the
package while that legacy module still exists on disk can trigger circular
imports, so we load the original file explicitly under a private module name
and re-export the handful of symbols callers expect.
"""

from __future__ import annotations

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

_LEGACY_MODULE_NAME = "app._legacy_models"
_LEGACY_MODULE_PATH = Path(__file__).resolve().parent.parent / "models.py"

if _LEGACY_MODULE_NAME in sys.modules:
    _legacy = sys.modules[_LEGACY_MODULE_NAME]
else:
    _spec = spec_from_file_location(_LEGACY_MODULE_NAME, _LEGACY_MODULE_PATH)
    if _spec is None or _spec.loader is None:
        raise ImportError(f"Unable to load legacy models from {_LEGACY_MODULE_PATH}")
    _legacy = module_from_spec(_spec)
    sys.modules[_LEGACY_MODULE_NAME] = _legacy
    _spec.loader.exec_module(_legacy)

# Get UsageAction from legacy module (it's imported there from .models.usage_record)
UsageAction = _legacy.UsageAction  # type: ignore[attr-defined]

UserRole = _legacy.UserRole  # type: ignore[attr-defined]
SessionStatus = _legacy.SessionStatus  # type: ignore[attr-defined]
DocumentType = _legacy.DocumentType  # type: ignore[attr-defined]
DiscrepancyType = _legacy.DiscrepancyType  # type: ignore[attr-defined]
DiscrepancySeverity = _legacy.DiscrepancySeverity  # type: ignore[attr-defined]

User = _legacy.User  # type: ignore[attr-defined]
ValidationSession = _legacy.ValidationSession  # type: ignore[attr-defined]
Document = _legacy.Document  # type: ignore[attr-defined]
Discrepancy = _legacy.Discrepancy  # type: ignore[attr-defined]
Report = _legacy.Report  # type: ignore[attr-defined]
AuditLog = _legacy.AuditLog  # type: ignore[attr-defined]
AuditAction = _legacy.AuditAction  # type: ignore[attr-defined]
AuditResult = _legacy.AuditResult  # type: ignore[attr-defined]
Company = _legacy.Company  # type: ignore[attr-defined]
PlanType = _legacy.PlanType  # type: ignore[attr-defined]
CompanyStatus = _legacy.CompanyStatus  # type: ignore[attr-defined]
Invoice = _legacy.Invoice  # type: ignore[attr-defined]
InvoiceStatus = _legacy.InvoiceStatus  # type: ignore[attr-defined]
Currency = _legacy.Currency  # type: ignore[attr-defined]
UsageRecord = _legacy.UsageRecord  # type: ignore[attr-defined]
BankTenant = _legacy.BankTenant  # type: ignore[attr-defined]
BankReport = _legacy.BankReport  # type: ignore[attr-defined]
BankAuditLog = _legacy.BankAuditLog  # type: ignore[attr-defined]
UserRoleAssignment = _legacy.UserRoleAssignment  # type: ignore[attr-defined]

__all__ = [
    "User",
    "UserRole",
    "ValidationSession",
    "SessionStatus",
    "Document",
    "DocumentType",
    "Discrepancy",
    "DiscrepancyType",
    "DiscrepancySeverity",
    "Report",
    "AuditLog",
    "AuditAction",
    "AuditResult",
    "Company",
    "PlanType",
    "CompanyStatus",
    "Invoice",
    "InvoiceStatus",
    "Currency",
    "UsageRecord",
    "UsageAction",
    "BankTenant",
    "BankReport",
    "BankAuditLog",
    "UserRoleAssignment",
]
