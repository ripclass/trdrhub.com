"""
Admin router hub - includes all admin sub-routers.

Uses importlib with direct file paths to avoid namespace conflicts
since this file is loaded as 'app.routers._legacy_admin' by the
router aggregation system.
"""
import logging
import importlib.util
import sys
from pathlib import Path
from fastapi import APIRouter

logger = logging.getLogger(__name__)

# Get the admin package directory
_ADMIN_PKG_DIR = Path(__file__).parent / "admin"


def _import_submodule(name: str):
    """Import a submodule from the admin package directory."""
    module_path = _ADMIN_PKG_DIR / f"{name}.py"
    module_name = f"app.routers.admin.{name}"
    
    if module_name in sys.modules:
        return sys.modules[module_name]
    
    if not module_path.exists():
        raise ImportError(f"Admin submodule not found: {module_path}")
    
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load admin submodule: {name}")
    
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# Import all admin sub-routers using file-based loading
dashboard = _import_submodule("dashboard")
ops = _import_submodule("ops")
audit = _import_submodule("audit")
governance = _import_submodule("governance")
jobs = _import_submodule("jobs")
dr = _import_submodule("dr")
vault = _import_submodule("vault")
db_audit = _import_submodule("db_audit")

router = APIRouter(prefix="/admin", tags=["Admin"])

# Include all admin sub-routers
router.include_router(dashboard.router)
router.include_router(ops.router)
router.include_router(audit.router)
router.include_router(governance.router)
router.include_router(jobs.router)
router.include_router(dr.router)
router.include_router(vault.router)
router.include_router(db_audit.router)
