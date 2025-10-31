"""
Router aggregation helpers ensuring both legacy module files and new packages
can be imported consistently via ``from app.routers import <module>``.
"""

from __future__ import annotations

import sys
from importlib import import_module, util
from pathlib import Path

_BASE_PATH = Path(__file__).resolve().parent


def _load_router_module(name: str):
    """
    Load router module ``app/routers/<name>.py`` even if a package with the same
    name exists. Falls back to standard import when the file is missing.
    """
    module_path = _BASE_PATH / f"{name}.py"
    if module_path.exists():
        module_name = f"app.routers._legacy_{name}"
        if module_name in sys.modules:
            return sys.modules[module_name]
        spec = util.spec_from_file_location(module_name, module_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Unable to load router module for {name}")
        module = util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module

    return import_module(f"app.routers.{name}")


auth = _load_router_module("auth")
sessions = _load_router_module("sessions")
fake_s3 = _load_router_module("fake_s3")
documents = _load_router_module("documents")
lc_versions = _load_router_module("lc_versions")
audit = _load_router_module("audit")
admin = _load_router_module("admin")
analytics = _load_router_module("analytics")
billing = _load_router_module("billing")
bank = _load_router_module("bank")

__all__ = [
    "auth",
    "sessions",
    "fake_s3",
    "documents",
    "lc_versions",
    "audit",
    "admin",
    "analytics",
    "billing",
    "bank",
]
