"""
Admin router hub - includes all admin sub-routers.
"""
import logging
from fastapi import APIRouter
from app.routers.admin import dashboard, ops, audit, governance, jobs, dr, secrets, db_audit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])

# Include all admin sub-routers
router.include_router(dashboard.router)
router.include_router(ops.router)
router.include_router(audit.router)
router.include_router(governance.router)
router.include_router(jobs.router)
router.include_router(dr.router)
router.include_router(secrets.router)
router.include_router(db_audit.router)
