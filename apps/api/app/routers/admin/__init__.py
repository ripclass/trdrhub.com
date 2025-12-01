# Admin routers package
# Export all sub-routers for easy importing

from . import dashboard
from . import ops
from . import audit
from . import governance
from . import jobs
from . import dr
from . import secrets
from . import db_audit

__all__ = [
    "dashboard",
    "ops", 
    "audit",
    "governance",
    "jobs",
    "dr",
    "secrets",
    "db_audit",
]
