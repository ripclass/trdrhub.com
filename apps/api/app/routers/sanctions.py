"""
Sanctions Screening API Router — Phase 2 launch (2026-07).

All screening runs through RulHub's deterministic engine
(POST /v1/screen/sanctions via ``services/sanctions_rulhub.py``): tiered
name/IMO matching against OFAC SDN / OFAC consolidated / UN / UK OFSI
designated-party lists plus the sanctions programme-rules corpus. The
previous local sample-list screener is no longer consulted — it screened
against ~60 hardcoded entries and could false-"clear" real names.

FAIL-CLOSED: any screening failure returns 503 with
``error_code=screening_unavailable`` — never an empty "no hits" response.
The frontend must render that as "do not treat as clear".

Surfaces that had no real backing (fake API keys, webhooks, CSV batch jobs,
fabricated list-sync stats, sample notifications) now answer honestly
(501 / empty) instead of returning invented data.
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, Query, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.database import get_db
from app.models.user import User
from app.core.security import get_current_user, get_optional_user
from app.services.sanctions_rulhub import (
    COVERED_LISTS,
    FAIL_CLOSED_MESSAGE,
    OFAC_50_CAVEAT,
    ScreeningUnavailable,
    screen_via_rulhub,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sanctions", tags=["sanctions-screener"])


# ============================================================================
# Pydantic Models
# ============================================================================

class PartyScreenRequest(BaseModel):
    """Request to screen a party/entity."""
    name: str = Field(..., min_length=2, max_length=500, description="Party name to screen")
    country: Optional[str] = Field(default=None, max_length=2, description="Country code (ISO 2-letter)")
    lists: List[str] = Field(default=[], description="Retained for API compat — the engine screens all covered lists")


class VesselScreenRequest(BaseModel):
    """Request to screen a vessel."""
    name: str = Field(..., min_length=2, max_length=200, description="Vessel name")
    imo: Optional[str] = Field(default=None, description="IMO number")
    mmsi: Optional[str] = Field(default=None, description="MMSI number")
    flag_state: Optional[str] = Field(default=None, description="Flag state name")
    flag_code: Optional[str] = Field(default=None, max_length=2, description="Flag state ISO code")
    lists: List[str] = Field(default=[], description="Retained for API compat — the engine screens all covered lists")


class GoodsScreenRequest(BaseModel):
    """Request to screen goods."""
    description: str = Field(..., min_length=3, max_length=2000, description="Goods description")
    hs_code: Optional[str] = Field(default=None, description="HS code if known")
    destination_country: Optional[str] = Field(default=None, max_length=2, description="Destination country code")


class BatchScreenRequest(BaseModel):
    """Request for batch screening."""
    items: List[Dict[str, Any]] = Field(..., max_length=100, description="Items to screen")
    screening_type: str = Field(default="party", description="Type: party, vessel, goods")
    lists: List[str] = Field(default=[], description="Retained for API compat")


class ScreeningMatch(BaseModel):
    """Individual match in results."""
    list_code: str
    list_name: str
    matched_name: str
    matched_type: str = "entity"
    match_type: str = "possible_match"  # hit | possible_match
    match_score: float = 0.0
    match_method: str = ""  # exact | match_key | fuzzy | imo | id_document
    programs: List[str] = []
    country: Optional[str] = None
    source_id: Optional[str] = None
    listed_date: Optional[str] = None
    remarks: Optional[str] = None
    # RulHub deterministic decision per hit
    action: str = "review"  # block | review
    recommendation: str = ""
    caveats: List[str] = []
    programme_context: List[Dict[str, Any]] = []


class ScreeningResponse(BaseModel):
    """Screening result response."""
    query: str
    screening_type: str
    screened_at: str
    status: str  # clear | potential_match | match | unavailable
    risk_level: str
    lists_screened: List[str]
    matches: List[ScreeningMatch]
    total_matches: int
    highest_score: float
    flags: List[str]
    recommendation: str
    certificate_id: str  # screening reference id (scr_*)
    processing_time_ms: int
    # Engine transparency (audit anchors)
    rules_checked: int = 0
    screening_scope: List[str] = []
    coverage_warning: Optional[str] = None
    list_versions: Optional[Dict[str, Optional[str]]] = None
    engine: str = "rulhub"


def _to_response(mapped: Dict[str, Any]) -> ScreeningResponse:
    return ScreeningResponse(
        query=mapped["query"],
        screening_type=mapped["screening_type"],
        screened_at=mapped["screened_at"],
        status=mapped["status"],
        risk_level=mapped["risk_level"],
        lists_screened=mapped["lists_screened"],
        matches=[ScreeningMatch(**m) for m in mapped["matches"]],
        total_matches=mapped["total_matches"],
        highest_score=mapped["highest_score"],
        flags=mapped["flags"],
        recommendation=mapped["recommendation"],
        certificate_id=mapped["screening_id"],
        processing_time_ms=mapped["processing_time_ms"],
        rules_checked=mapped.get("rules_checked", 0),
        screening_scope=mapped.get("screening_scope") or [],
        coverage_warning=mapped.get("coverage_warning"),
        list_versions=mapped.get("list_versions"),
        engine=mapped.get("engine", "rulhub"),
    )


def _unavailable_503(exc: Exception) -> HTTPException:
    return HTTPException(
        status_code=503,
        detail={
            "error_code": "screening_unavailable",
            "message": str(exc) or FAIL_CLOSED_MESSAGE,
        },
    )


# Anonymous visitors get a small daily allowance (lead magnet); a free
# account lifts it during launch. Signed-in users are bounded by the global
# rate limiter only. Redis-unreachable fails OPEN here — the global limiter
# still bounds abuse, and a cache hiccup must not take the tool down.
ANON_DAILY_SCREENS = 5


async def _enforce_anon_limit(request: Request, current_user: Optional[User]) -> None:
    if current_user is not None:
        return
    from app.utils.anon_rate_limit import reserve_anon_run

    try:
        retry_in = await reserve_anon_run(
            request=request, scope="sanctions_screen", limit=ANON_DAILY_SCREENS,
        )
    except Exception:
        logger.warning("anon screening limiter unavailable — failing open", exc_info=True)
        return
    if retry_in is not None:
        hours = max(1, round(retry_in / 3600))
        raise HTTPException(
            status_code=429,
            detail={
                "error_code": "free_limit_reached",
                "message": (
                    f"You've used today's {ANON_DAILY_SCREENS} free checks. "
                    f"Create a free account for unlimited screening during launch, "
                    f"or come back in about {hours}h."
                ),
            },
        )


# ============================================================================
# Screening endpoints (all RulHub-backed, all fail-closed)
# ============================================================================

@router.get("/lists")
async def get_available_lists():
    """Designated-party lists the engine screens against."""
    return {
        "lists": COVERED_LISTS,
        "default_lists": [l["code"] for l in COVERED_LISTS if l["status"] == "active"],
        "caveat": OFAC_50_CAVEAT,
    }


@router.post("/screen/party", response_model=ScreeningResponse)
async def screen_party(
    request: PartyScreenRequest,
    http_request: Request,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Screen a party/entity name against designated-party lists + programme rules.

    Fail-closed: 503 screening_unavailable on any engine failure.
    """
    await _enforce_anon_limit(http_request, current_user)
    try:
        mapped = await screen_via_rulhub(
            query=request.name,
            screening_type="party",
            entity=request.name,
            country=request.country,
        )
    except ScreeningUnavailable as exc:
        raise _unavailable_503(exc)
    return _to_response(mapped)


@router.post("/screen/vessel", response_model=ScreeningResponse)
async def screen_vessel(
    request: VesselScreenRequest,
    http_request: Request,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Screen a vessel (name or IMO) against designated-party lists + programme rules."""
    await _enforce_anon_limit(http_request, current_user)
    # IMO gives the matcher an exact identifier tier; fall back to the name.
    vessel_key = (request.imo or "").strip() or request.name
    transaction: Dict[str, Any] = {}
    if request.imo:
        transaction["imo"] = request.imo
    if request.mmsi:
        transaction["mmsi"] = request.mmsi
    if request.flag_state:
        transaction["flag_state"] = request.flag_state
    try:
        mapped = await screen_via_rulhub(
            query=request.name,
            screening_type="vessel",
            vessel=vessel_key,
            country=request.flag_code,
            transaction=transaction or None,
        )
    except ScreeningUnavailable as exc:
        raise _unavailable_503(exc)
    return _to_response(mapped)


@router.post("/screen/goods", response_model=ScreeningResponse)
async def screen_goods(
    request: GoodsScreenRequest,
    http_request: Request,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Screen goods + destination against the sanctions programme-rules corpus.

    Goods screening evaluates sectoral restrictions and destination-country
    programmes; it is not a designated-party name match.
    """
    await _enforce_anon_limit(http_request, current_user)
    try:
        mapped = await screen_via_rulhub(
            query=request.description,
            screening_type="goods",
            country=request.destination_country,
            transaction={
                "goods_description": request.description,
                "goods": request.description,
                **({"hs_code": request.hs_code} if request.hs_code else {}),
            },
        )
    except ScreeningUnavailable as exc:
        raise _unavailable_503(exc)
    return _to_response(mapped)


@router.post("/screen/batch")
async def batch_screen(
    request: BatchScreenRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Batch screening (max 100 items). Requires authentication.

    Fail-closed per row: a row that could not be screened is reported as
    ``unavailable`` — it is never counted as clear.
    """
    results = []
    for item in request.items:
        query = item.get("name") or item.get("query") or item.get("description")
        if not query:
            results.append({"error": "Missing name/query field", "item": item, "status": "unavailable"})
            continue

        try:
            if request.screening_type == "vessel":
                mapped = await screen_via_rulhub(
                    query=query,
                    screening_type="vessel",
                    vessel=(item.get("imo") or "").strip() or query,
                    country=item.get("flag_code") or item.get("country"),
                )
            elif request.screening_type == "goods":
                mapped = await screen_via_rulhub(
                    query=query,
                    screening_type="goods",
                    country=item.get("destination_country") or item.get("country"),
                    transaction={"goods_description": query, "goods": query,
                                 **({"hs_code": item["hs_code"]} if item.get("hs_code") else {})},
                )
            else:
                mapped = await screen_via_rulhub(
                    query=query,
                    screening_type="party",
                    entity=query,
                    country=item.get("country"),
                )
            results.append({
                "query": mapped["query"],
                "status": mapped["status"],
                "risk_level": mapped["risk_level"],
                "total_matches": mapped["total_matches"],
                "highest_score": mapped["highest_score"],
                "action": next((m["action"] for m in mapped["matches"] if m["action"] == "block"),
                               "review" if mapped["matches"] else None),
                "certificate_id": mapped["screening_id"],
            })
        except ScreeningUnavailable:
            results.append({
                "query": query,
                "status": "unavailable",
                "error": FAIL_CLOSED_MESSAGE,
            })
        except Exception as e:
            logger.error(f"Error screening {query}: {e}")
            results.append({"query": query, "status": "unavailable", "error": FAIL_CLOSED_MESSAGE})

    clear_count = sum(1 for r in results if r.get("status") == "clear")
    match_count = sum(1 for r in results if r.get("status") == "match")
    potential_count = sum(1 for r in results if r.get("status") == "potential_match")
    unavailable_count = sum(1 for r in results if r.get("status") == "unavailable")

    return {
        "total": len(results),
        "clear": clear_count,
        "potential_match": potential_count,
        "match": match_count,
        "unavailable": unavailable_count,
        "errors": unavailable_count,
        "fail_closed_note": (
            f"{unavailable_count} item(s) could not be screened — treat them as "
            "unscreened, not clear."
        ) if unavailable_count else None,
        "results": results,
    }


@router.post("/quick-screen")
async def quick_screen(
    http_request: Request,
    query: str = Query(..., min_length=2, description="Name to screen"),
    type: str = Query(default="party", regex="^(party|vessel|goods)$"),
    country: Optional[str] = Query(default=None, max_length=2),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """Quick screening endpoint for simple lookups. Fail-closed like the rest."""
    await _enforce_anon_limit(http_request, current_user)
    try:
        if type == "vessel":
            mapped = await screen_via_rulhub(query=query, screening_type="vessel",
                                             vessel=query, country=country)
        elif type == "goods":
            mapped = await screen_via_rulhub(query=query, screening_type="goods",
                                             country=country,
                                             transaction={"goods_description": query, "goods": query})
        else:
            mapped = await screen_via_rulhub(query=query, screening_type="party",
                                             entity=query, country=country)
    except ScreeningUnavailable as exc:
        raise _unavailable_503(exc)

    return {
        "query": query,
        "status": mapped["status"],
        "risk_level": mapped["risk_level"],
        "total_matches": mapped["total_matches"],
        "highest_score": mapped["highest_score"],
        "recommendation": mapped["recommendation"],
        "certificate_id": mapped["screening_id"],
    }


@router.get("/countries/sanctioned")
async def get_sanctioned_countries():
    """Reference list of comprehensively sanctioned countries."""
    from app.services.sanctions_screening import SANCTIONED_COUNTRIES

    return {
        "countries": [
            {
                "code": code,
                "name": info["name"],
                "type": info["type"],
                "programs": info["programs"],
            }
            for code, info in SANCTIONED_COUNTRIES.items()
        ],
    }


# ============================================================================
# History / stats — honest empties until persistence lands
# ============================================================================

@router.get("/history")
async def get_screening_history(
    limit: int = Query(default=20, le=100),
    screening_type: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Screening history. Results are not persisted yet — always empty."""
    return {
        "total": 0,
        "screenings": [],
        "note": "Screening results are not persisted yet. Keep the screening reference id (scr_*) from each result for your records.",
    }


@router.get("/stats")
async def get_screening_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Screening statistics. Not available until history persistence lands."""
    return {
        "total_screenings": None,
        "this_month": None,
        "clear_rate": None,
        "match_rate": None,
        "most_common_lists": [],
        "note": "Statistics not available yet — screening results are not persisted.",
    }


@router.get("/certificate/{certificate_id}")
async def get_certificate(
    certificate_id: str,
    format: str = Query(default="json", regex="^(json|pdf)$"),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """Screening certificates are not issued yet."""
    raise HTTPException(
        status_code=404,
        detail=(
            "Screening certificates are not issued yet. The screening reference "
            "id on each result identifies the screen; certificate documents are "
            "on the roadmap."
        ),
    )


# ============================================================================
# List status — the engine owns list ingestion; no fabricated sync stats
# ============================================================================

@router.get("/lists/sync-status")
async def get_list_sync_status(
    current_user: Optional[User] = Depends(get_optional_user),
):
    """List coverage status.

    Designated-party lists are ingested and versioned inside the screening
    engine. Per-source as-of dates arrive with each screening result
    (``list_versions``) — that response field is the audit anchor for a given
    screen, not this registry.
    """
    return {
        "lists": COVERED_LISTS,
        "managed_by": "screening engine (api.rulhub.com)",
        "note": (
            "List ingestion and versioning happen inside the screening engine. "
            "Each screening response carries the per-source list as-of dates it "
            "was screened against (list_versions)."
        ),
    }


@router.post("/lists/trigger-sync")
async def trigger_list_sync(
    list_code: str = Query(..., description="List code to sync"),
    current_user: User = Depends(get_current_user),
):
    """List synchronization is owned by the screening engine — not triggerable here."""
    raise HTTPException(
        status_code=501,
        detail="List ingestion runs inside the screening engine on its own schedule; it cannot be triggered from here.",
    )


# ============================================================================
# Notifications / API keys / webhooks — not built yet; answer honestly
# ============================================================================

@router.get("/notifications/preferences")
async def get_notification_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Notification preferences (defaults — persistence not built yet)."""
    return {
        "list_updates": False,
        "watchlist_alerts": False,
        "screening_summary": False,
        "email_enabled": False,
        "webhook_url": None,
        "note": "Sanctions notification preferences are not persisted yet.",
    }


@router.put("/notifications/preferences")
async def update_notification_preferences(
    current_user: User = Depends(get_current_user),
):
    raise HTTPException(status_code=501, detail="Sanctions notification preferences are not available yet.")


@router.get("/notifications/recent")
async def get_recent_notifications(
    limit: int = Query(default=20, le=100),
    current_user: User = Depends(get_current_user),
):
    """No sanctions notifications are generated yet."""
    return {"notifications": [], "unread_count": 0}


@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    current_user: User = Depends(get_current_user),
):
    raise HTTPException(status_code=404, detail="No sanctions notifications exist yet.")


@router.get("/api-keys")
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Programmatic API keys for the screener are not self-serve yet."""
    return {
        "keys": [],
        "max_keys": 0,
        "note": "Programmatic screening access is available via the RulHub API — contact support@trdrhub.com.",
    }


@router.post("/api-keys")
async def create_api_key(
    name: str = Query(..., min_length=1, max_length=100),
    current_user: User = Depends(get_current_user),
):
    raise HTTPException(
        status_code=501,
        detail="Self-serve API keys are not available yet — contact support@trdrhub.com for programmatic screening access.",
    )


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
):
    raise HTTPException(status_code=404, detail="No API keys exist for this account.")


@router.get("/api-keys/usage")
async def get_api_usage(
    current_user: User = Depends(get_current_user),
):
    raise HTTPException(status_code=501, detail="API usage metering is not available yet.")


@router.get("/webhooks")
async def list_webhooks(
    current_user: User = Depends(get_current_user),
):
    return {"webhooks": [], "max_webhooks": 0,
            "note": "Sanctions webhooks are not available yet."}


@router.post("/webhooks")
async def create_webhook(
    current_user: User = Depends(get_current_user),
):
    raise HTTPException(status_code=501, detail="Sanctions webhooks are not available yet.")


@router.delete("/webhooks/{webhook_id}")
async def delete_webhook(
    webhook_id: str,
    current_user: User = Depends(get_current_user),
):
    raise HTTPException(status_code=404, detail="No webhooks exist for this account.")


@router.post("/webhooks/{webhook_id}/test")
async def test_webhook(
    webhook_id: str,
    current_user: User = Depends(get_current_user),
):
    raise HTTPException(status_code=404, detail="No webhooks exist for this account.")


# ============================================================================
# CSV batch-job endpoints — superseded by POST /screen/batch (JSON, max 100)
# ============================================================================

@router.post("/batch/upload-csv")
async def upload_csv_for_batch_screening(
    current_user: User = Depends(get_current_user),
):
    raise HTTPException(
        status_code=501,
        detail="CSV batch jobs are not available yet — parse the CSV client-side and POST up to 100 rows to /api/sanctions/screen/batch.",
    )


@router.get("/batch/status/{job_id}")
async def get_batch_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
):
    raise HTTPException(status_code=404, detail="No batch jobs exist — use POST /api/sanctions/screen/batch (synchronous).")


@router.get("/batch/download/{job_id}")
async def download_batch_results(
    job_id: str,
    current_user: User = Depends(get_current_user),
):
    raise HTTPException(status_code=404, detail="No batch jobs exist — use POST /api/sanctions/screen/batch (synchronous).")
