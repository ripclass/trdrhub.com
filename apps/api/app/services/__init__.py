"""
Expose service helpers under ``app.services`` while keeping legacy module APIs.

Historically the project defined key service classes in ``app/services.py``.
Later, feature-specific services were organised into the ``app/services/``
package (e.g. ``audit_service.py``).  Importers expect both styles to work:

    from app.services import S3Service
    from app.services.audit_service import AuditService

This initializer loads the legacy module once and re-exports the classes so the
module-style imports continue to function, while also letting Python resolve
subpackage imports for the newer layout.
"""

from __future__ import annotations

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

_LEGACY_MODULE_NAME = "app._legacy_services"
_LEGACY_MODULE_PATH = Path(__file__).resolve().parent.parent / "services.py"

if _LEGACY_MODULE_NAME in sys.modules:
    _legacy = sys.modules[_LEGACY_MODULE_NAME]
else:
    _spec = spec_from_file_location(_LEGACY_MODULE_NAME, _LEGACY_MODULE_PATH)
    if _spec is None or _spec.loader is None:
        raise ImportError(f"Unable to load legacy services from {_LEGACY_MODULE_PATH}")
    _legacy = module_from_spec(_spec)
    sys.modules[_LEGACY_MODULE_NAME] = _legacy
    _spec.loader.exec_module(_legacy)

S3Service = _legacy.S3Service  # type: ignore[attr-defined]
ValidationSessionService = _legacy.ValidationSessionService  # type: ignore[attr-defined]
DocumentProcessingService = _legacy.DocumentProcessingService  # type: ignore[attr-defined]
ReportService = _legacy.ReportService  # type: ignore[attr-defined]
DocumentAIService = _legacy.DocumentAIService  # type: ignore[attr-defined]

__all__ = [
    "S3Service",
    "ValidationSessionService",
    "DocumentProcessingService",
    "ReportService",
    "DocumentAIService",
]
