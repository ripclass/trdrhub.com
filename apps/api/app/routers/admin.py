"""
Admin router hub - includes all admin sub-routers.
"""
import logging
import importlib
from fastapi import APIRouter

logger = logging.getLogger(__name__)

# Import sub-routers using importlib to avoid circular imports
# (Python's built-in 'secrets' module conflicts with admin/secrets.py)
dashboard = importlib.import_module('app.routers.admin.dashboard')
ops = importlib.import_module('app.routers.admin.ops')
audit = importlib.import_module('app.routers.admin.audit')
governance = importlib.import_module('app.routers.admin.governance')
jobs = importlib.import_module('app.routers.admin.jobs')
dr = importlib.import_module('app.routers.admin.dr')
secrets_router = importlib.import_module('app.routers.admin.secrets')
db_audit = importlib.import_module('app.routers.admin.db_audit')

router = APIRouter(prefix="/admin", tags=["Admin"])

# Include all admin sub-routers
router.include_router(dashboard.router)
router.include_router(ops.router)
router.include_router(audit.router)
router.include_router(governance.router)
router.include_router(jobs.router)
router.include_router(dr.router)
router.include_router(secrets_router.router)
router.include_router(db_audit.router)
