from fastapi import APIRouter, Depends

from app.services.rulhub_client import sync_rules_from_rulhub
from app.core.security import require_admin


router = APIRouter(prefix="/rules", tags=["rules"])


@router.post("/sync", dependencies=[Depends(require_admin)])
async def manual_sync():
    sync_rules_from_rulhub()
    return {"status": "ok", "message": "Rules synced from RulHub."}


