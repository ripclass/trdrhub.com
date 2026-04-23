"""Agency workspace stub — Day 4 deliverable.

Backs /lcopilot/agency-dashboard for sourcing/buying-agent users. Real
implementation (bulk per-supplier validation, per-supplier discrepancy
tracking, agent re-papering workflow) is deferred until the agency build
gets an explicit spec sign-off + AI credits.

For now ``GET /api/agency/suppliers`` returns ``[]`` so the frontend empty
state is driven by real data rather than hardcoded — same pattern Stream A
used for the importer analytics stub.
"""

from typing import List

from fastapi import APIRouter, Depends

from ..core.security import get_current_user
from ..models import User
from pydantic import BaseModel


router = APIRouter(prefix="/agency", tags=["agency"])


class Supplier(BaseModel):
    """Placeholder supplier shape.

    Full model lands when the agency build ships. Keeping the payload shape
    stable now lets the frontend wire against it without another round-trip.
    """

    id: str
    name: str
    country: str | None = None
    active_lcs: int = 0
    open_discrepancies: int = 0


@router.get("/suppliers", response_model=List[Supplier])
async def list_suppliers(_: User = Depends(get_current_user)) -> List[Supplier]:
    """Return the caller's supplier portfolio.

    Stub returns an empty list — Day 4 ships the placeholder UI behind it.
    Full implementation deferred. See ONBOARDING_REFACTOR_RESUME.md.
    """
    return []
