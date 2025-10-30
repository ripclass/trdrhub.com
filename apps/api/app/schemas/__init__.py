"""
Compatibility shim exposing legacy schema classes through ``app.schemas``.

The canonical schema definitions live in ``app/schemas.py``.  Keep importing
logic centralized so both module-style and package-style imports succeed.
"""

from __future__ import annotations

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

_LEGACY_MODULE_NAME = "app._legacy_schemas"
_LEGACY_MODULE_PATH = Path(__file__).resolve().parent.parent / "schemas.py"

if _LEGACY_MODULE_NAME in sys.modules:
    _legacy = sys.modules[_LEGACY_MODULE_NAME]
else:
    _spec = spec_from_file_location(_LEGACY_MODULE_NAME, _LEGACY_MODULE_PATH)
    if _spec is None or _spec.loader is None:
        raise ImportError(f"Unable to load legacy schemas from {_LEGACY_MODULE_PATH}")
    _legacy = module_from_spec(_spec)
    sys.modules[_LEGACY_MODULE_NAME] = _legacy
    _spec.loader.exec_module(_legacy)

# Expose everything publicly to mirror ``from app.schemas import *`` behaviour.
_exported = {
    name: getattr(_legacy, name)
    for name in dir(_legacy)
    if not name.startswith("_")
}

globals().update(_exported)
__all__ = sorted(_exported.keys())
