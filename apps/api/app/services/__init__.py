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

from importlib.util import module_from_spec, spec_from_file_location
import sys
from pathlib import Path

_LEGACY_MODULE_NAME = "app._legacy_services"
_LEGACY_MODULE_PATH = Path(__file__).resolve().parent.parent / "services.py"
_REQUIRED_LEGACY_EXPORTS = (
    "S3Service",
    "ValidationSessionService",
    "DocumentProcessingService",
    "ReportService",
    "DocumentAIService",
)


def _load_legacy_services():
    """Load legacy services module and validate required exports."""
    spec = spec_from_file_location(_LEGACY_MODULE_NAME, _LEGACY_MODULE_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load legacy services from {_LEGACY_MODULE_PATH}")

    module = module_from_spec(spec)
    sys.modules[_LEGACY_MODULE_NAME] = module
    spec.loader.exec_module(module)

    missing = [name for name in _REQUIRED_LEGACY_EXPORTS if not hasattr(module, name)]
    if missing:
        raise ImportError(
            f"Legacy services module {_LEGACY_MODULE_PATH} missing required exports: {', '.join(missing)}"
        )
    return module

if _LEGACY_MODULE_NAME in sys.modules:
    _cached = sys.modules[_LEGACY_MODULE_NAME]
    if not all(hasattr(_cached, name) for name in _REQUIRED_LEGACY_EXPORTS):
        sys.modules.pop(_LEGACY_MODULE_NAME, None)
        _legacy = _load_legacy_services()
    else:
        _legacy = _cached
else:
    _legacy = _load_legacy_services()

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
