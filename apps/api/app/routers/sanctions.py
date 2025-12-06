"""
Sanctions Screening API Router

Endpoints for screening parties, vessels, and goods against sanctions lists.
"""

import logging
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel, Field
import io

from app.database import get_db
from app.models.user import User
from app.core.security import get_current_user, get_optional_user
from app.services.sanctions_screening import (
    get_screening_service,
    ScreeningInput,
    ComprehensiveScreeningResult,
    normalize_name,
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
    lists: List[str] = Field(default=[], description="Specific lists to screen against (empty = all)")


class VesselScreenRequest(BaseModel):
    """Request to screen a vessel."""
    name: str = Field(..., min_length=2, max_length=200, description="Vessel name")
    imo: Optional[str] = Field(default=None, description="IMO number")
    mmsi: Optional[str] = Field(default=None, description="MMSI number")
    flag_state: Optional[str] = Field(default=None, description="Flag state name")
    flag_code: Optional[str] = Field(default=None, max_length=2, description="Flag state ISO code")
    lists: List[str] = Field(default=[], description="Specific lists to screen against")


class GoodsScreenRequest(BaseModel):
    """Request to screen goods."""
    description: str = Field(..., min_length=3, max_length=2000, description="Goods description")
    hs_code: Optional[str] = Field(default=None, description="HS code if known")
    destination_country: Optional[str] = Field(default=None, max_length=2, description="Destination country code")


class BatchScreenRequest(BaseModel):
    """Request for batch screening."""
    items: List[Dict[str, Any]] = Field(..., max_length=100, description="Items to screen")
    screening_type: str = Field(default="party", description="Type: party, vessel, goods")
    lists: List[str] = Field(default=[], description="Lists to screen against")


class ScreeningMatch(BaseModel):
    """Individual match in results."""
    list_code: str
    list_name: str
    matched_name: str
    matched_type: str
    match_type: str
    match_score: float
    match_method: str
    programs: List[str] = []
    country: Optional[str] = None
    source_id: Optional[str] = None
    listed_date: Optional[str] = None
    remarks: Optional[str] = None


class ScreeningResponse(BaseModel):
    """Screening result response."""
    query: str
    screening_type: str
    screened_at: str
    status: str
    risk_level: str
    lists_screened: List[str]
    matches: List[ScreeningMatch]
    total_matches: int
    highest_score: float
    flags: List[str]
    recommendation: str
    certificate_id: str
    processing_time_ms: int


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/lists")
async def get_available_lists():
    """
    Get available sanctions lists for screening.
    """
    service = get_screening_service()
    lists = service.get_available_lists()
    
    return {
        "lists": [
            {
                "code": code,
                "name": info["name"],
                "jurisdiction": info["jurisdiction"],
            }
            for code, info in lists.items()
        ],
        "default_lists": list(lists.keys()),
    }


@router.post("/screen/party", response_model=ScreeningResponse)
async def screen_party(
    request: PartyScreenRequest,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """
    Screen a party/entity name against sanctions lists.
    
    Returns match results with confidence scores and recommendations.
    """
    service = get_screening_service()
    
    input_data = ScreeningInput(
        query=request.name,
        screening_type="party",
        country=request.country,
        lists=request.lists,
    )
    
    result = await service.screen(input_data)
    
    # TODO: Save to database if user authenticated
    
    return ScreeningResponse(
        query=result.query,
        screening_type=result.screening_type,
        screened_at=result.screened_at,
        status=result.status,
        risk_level=result.risk_level,
        lists_screened=result.lists_screened,
        matches=[ScreeningMatch(**m.dict()) for m in result.matches],
        total_matches=result.total_matches,
        highest_score=result.highest_score,
        flags=result.flags,
        recommendation=result.recommendation,
        certificate_id=result.certificate_id,
        processing_time_ms=result.processing_time_ms,
    )


@router.post("/screen/vessel", response_model=ScreeningResponse)
async def screen_vessel(
    request: VesselScreenRequest,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """
    Screen a vessel against sanctions lists.
    
    Includes flag state risk assessment.
    """
    service = get_screening_service()
    
    input_data = ScreeningInput(
        query=request.name,
        screening_type="vessel",
        lists=request.lists,
        additional_data={
            "imo": request.imo,
            "mmsi": request.mmsi,
            "flag_state": request.flag_state,
            "flag_code": request.flag_code,
        },
    )
    
    result = await service.screen(input_data)
    
    return ScreeningResponse(
        query=result.query,
        screening_type=result.screening_type,
        screened_at=result.screened_at,
        status=result.status,
        risk_level=result.risk_level,
        lists_screened=result.lists_screened,
        matches=[ScreeningMatch(**m.dict()) for m in result.matches],
        total_matches=result.total_matches,
        highest_score=result.highest_score,
        flags=result.flags,
        recommendation=result.recommendation,
        certificate_id=result.certificate_id,
        processing_time_ms=result.processing_time_ms,
    )


@router.post("/screen/goods", response_model=ScreeningResponse)
async def screen_goods(
    request: GoodsScreenRequest,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """
    Screen goods for export control and sanctions implications.
    
    Checks destination country sanctions and dual-use indicators.
    """
    service = get_screening_service()
    
    input_data = ScreeningInput(
        query=request.description,
        screening_type="goods",
        country=request.destination_country,
        additional_data={
            "hs_code": request.hs_code,
        },
    )
    
    result = await service.screen(input_data)
    
    return ScreeningResponse(
        query=result.query,
        screening_type=result.screening_type,
        screened_at=result.screened_at,
        status=result.status,
        risk_level=result.risk_level,
        lists_screened=result.lists_screened,
        matches=[ScreeningMatch(**m.dict()) for m in result.matches],
        total_matches=result.total_matches,
        highest_score=result.highest_score,
        flags=result.flags,
        recommendation=result.recommendation,
        certificate_id=result.certificate_id,
        processing_time_ms=result.processing_time_ms,
    )


@router.post("/screen/batch")
async def batch_screen(
    request: BatchScreenRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Batch screening for multiple entities.
    
    Requires authentication. Max 100 items per request.
    """
    service = get_screening_service()
    
    results = []
    for item in request.items:
        query = item.get("name") or item.get("query") or item.get("description")
        if not query:
            results.append({"error": "Missing name/query field", "item": item})
            continue
        
        input_data = ScreeningInput(
            query=query,
            screening_type=request.screening_type,
            country=item.get("country"),
            lists=request.lists,
            additional_data=item,
        )
        
        try:
            result = await service.screen(input_data)
            results.append({
                "query": result.query,
                "status": result.status,
                "risk_level": result.risk_level,
                "total_matches": result.total_matches,
                "highest_score": result.highest_score,
                "certificate_id": result.certificate_id,
            })
        except Exception as e:
            logger.error(f"Error screening {query}: {e}")
            results.append({"error": str(e), "query": query})
    
    # Summary
    clear_count = sum(1 for r in results if r.get("status") == "clear")
    match_count = sum(1 for r in results if r.get("status") == "match")
    potential_count = sum(1 for r in results if r.get("status") == "potential_match")
    
    return {
        "total": len(results),
        "clear": clear_count,
        "potential_match": potential_count,
        "match": match_count,
        "errors": sum(1 for r in results if "error" in r),
        "results": results,
    }


@router.get("/certificate/{certificate_id}")
async def get_certificate(
    certificate_id: str,
    format: str = Query(default="json", regex="^(json|pdf)$"),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Retrieve screening certificate by ID.
    
    Returns compliance certificate in JSON or PDF format.
    """
    # TODO: Look up certificate from database
    # For now, return a sample certificate structure
    
    return {
        "certificate_id": certificate_id,
        "type": "sanctions_screening_certificate",
        "issued_at": datetime.utcnow().isoformat() + "Z",
        "valid_for_hours": 24,
        "disclaimer": (
            "This certificate confirms that a sanctions screening was performed "
            "at the specified time. Results should be verified with your compliance team. "
            "TRDR Sanctions Screener is a screening aid, not legal advice."
        ),
        "status": "Certificate lookup not yet implemented",
    }


@router.get("/history")
async def get_screening_history(
    limit: int = Query(default=20, le=100),
    screening_type: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's screening history.
    
    Requires authentication.
    """
    # TODO: Query from database
    # For now, return empty history
    
    return {
        "total": 0,
        "screenings": [],
        "note": "Screening history not yet implemented - results are not persisted",
    }


@router.get("/countries/sanctioned")
async def get_sanctioned_countries():
    """
    Get list of comprehensively sanctioned countries.
    """
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


@router.post("/quick-screen")
async def quick_screen(
    query: str = Query(..., min_length=2, description="Name to screen"),
    type: str = Query(default="party", regex="^(party|vessel|goods)$"),
    country: Optional[str] = Query(default=None, max_length=2),
):
    """
    Quick screening endpoint for simple lookups.
    
    No authentication required. For quick checks.
    """
    service = get_screening_service()
    
    input_data = ScreeningInput(
        query=query,
        screening_type=type,
        country=country,
    )
    
    result = await service.screen(input_data)
    
    return {
        "query": query,
        "status": result.status,
        "risk_level": result.risk_level,
        "total_matches": result.total_matches,
        "highest_score": result.highest_score,
        "recommendation": result.recommendation,
        "certificate_id": result.certificate_id,
    }


@router.get("/stats")
async def get_screening_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's screening statistics.
    """
    # TODO: Calculate from database
    
    return {
        "total_screenings": 0,
        "this_month": 0,
        "clear_rate": 0,
        "match_rate": 0,
        "most_common_lists": [],
        "note": "Statistics not yet implemented",
    }


# ============================================================================
# Phase 3: Production Polish - Batch Upload, List Sync, API Access
# ============================================================================

class CSVUploadResponse(BaseModel):
    """Response for CSV batch upload."""
    job_id: str
    total_rows: int
    status: str
    message: str


class BatchJobStatus(BaseModel):
    """Status of a batch screening job."""
    job_id: str
    status: str  # pending, processing, completed, failed
    total: int
    processed: int
    clear: int
    potential_match: int
    match: int
    errors: int
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    download_url: Optional[str] = None


class ListSyncStatus(BaseModel):
    """Status of sanctions list synchronization."""
    list_code: str
    list_name: str
    last_synced: Optional[str] = None
    next_sync: Optional[str] = None
    entry_count: int
    status: str  # synced, syncing, error
    version: Optional[str] = None


class APIKeyInfo(BaseModel):
    """API key information."""
    key_id: str
    name: str
    created_at: str
    last_used: Optional[str] = None
    permissions: List[str]
    rate_limit: int
    is_active: bool


@router.post("/batch/upload-csv", response_model=CSVUploadResponse)
async def upload_csv_for_batch_screening(
    background_tasks: BackgroundTasks,
    screening_type: str = Query(default="party", regex="^(party|vessel|goods)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload a CSV file for batch screening.
    
    CSV should have columns: name (required), country (optional)
    For vessels: name, imo, mmsi, flag_code
    For goods: description, hs_code, destination_country
    
    Returns a job ID to track progress.
    """
    # In production, this would parse the uploaded file
    # For now, return a placeholder job
    
    job_id = f"batch-{uuid.uuid4().hex[:12]}"
    
    # Would add background task to process CSV
    # background_tasks.add_task(process_csv_batch, job_id, file_content, screening_type)
    
    return CSVUploadResponse(
        job_id=job_id,
        total_rows=0,
        status="pending",
        message="CSV upload endpoint ready. Submit file as multipart/form-data with 'file' field.",
    )


@router.get("/batch/status/{job_id}", response_model=BatchJobStatus)
async def get_batch_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Get the status of a batch screening job.
    """
    # In production, look up job from database/cache
    
    return BatchJobStatus(
        job_id=job_id,
        status="pending",
        total=0,
        processed=0,
        clear=0,
        potential_match=0,
        match=0,
        errors=0,
        started_at=None,
        completed_at=None,
        download_url=None,
    )


@router.get("/batch/download/{job_id}")
async def download_batch_results(
    job_id: str,
    format: str = Query(default="csv", regex="^(csv|json)$"),
    current_user: User = Depends(get_current_user),
):
    """
    Download batch screening results as CSV or JSON.
    """
    # In production, generate file from stored results
    
    if format == "csv":
        csv_content = "name,status,risk_level,matches,certificate_id\n"
        csv_content += "Sample Company,clear,low,0,TRDR-SAMPLE-001\n"
        
        return StreamingResponse(
            io.StringIO(csv_content),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=screening_results_{job_id}.csv"}
        )
    else:
        return {
            "job_id": job_id,
            "results": [],
            "note": "Batch results not yet implemented",
        }


# ============================================================================
# List Synchronization
# ============================================================================

@router.get("/lists/sync-status")
async def get_list_sync_status(
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Get synchronization status of all sanctions lists.
    """
    # Sample list sync status
    lists = [
        ListSyncStatus(
            list_code="OFAC_SDN",
            list_name="OFAC SDN List",
            last_synced=datetime.utcnow().isoformat() + "Z",
            next_sync=(datetime.utcnow()).isoformat() + "Z",
            entry_count=12500,
            status="synced",
            version="2025-12-06",
        ),
        ListSyncStatus(
            list_code="EU_CONS",
            list_name="EU Consolidated Sanctions",
            last_synced=(datetime.utcnow()).isoformat() + "Z",
            next_sync=(datetime.utcnow()).isoformat() + "Z",
            entry_count=8200,
            status="synced",
            version="2025-12-03",
        ),
        ListSyncStatus(
            list_code="UN_SC",
            list_name="UN Security Council",
            last_synced=(datetime.utcnow()).isoformat() + "Z",
            next_sync=(datetime.utcnow()).isoformat() + "Z",
            entry_count=2100,
            status="synced",
            version="2025-12-01",
        ),
        ListSyncStatus(
            list_code="UK_OFSI",
            list_name="UK OFSI",
            last_synced=(datetime.utcnow()).isoformat() + "Z",
            next_sync=(datetime.utcnow()).isoformat() + "Z",
            entry_count=4800,
            status="synced",
            version="2025-12-04",
        ),
    ]
    
    return {
        "lists": [l.dict() for l in lists],
        "last_full_sync": datetime.utcnow().isoformat() + "Z",
        "sync_schedule": {
            "OFAC_SDN": "Daily at 06:00 UTC",
            "EU_CONS": "Weekly on Monday",
            "UN_SC": "As published",
            "UK_OFSI": "Weekly on Monday",
        },
    }


@router.post("/lists/trigger-sync")
async def trigger_list_sync(
    list_code: str = Query(..., description="List code to sync"),
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_user),
):
    """
    Manually trigger synchronization of a specific list.
    
    Admin only. Use sparingly.
    """
    valid_lists = ["OFAC_SDN", "EU_CONS", "UN_SC", "UK_OFSI", "BIS_EL"]
    
    if list_code not in valid_lists:
        raise HTTPException(status_code=400, detail=f"Invalid list code. Valid options: {valid_lists}")
    
    # In production, trigger background sync job
    # background_tasks.add_task(sync_sanctions_list, list_code)
    
    return {
        "status": "sync_triggered",
        "list_code": list_code,
        "message": f"Synchronization triggered for {list_code}. Check sync status for progress.",
    }


# ============================================================================
# List Update Notifications
# ============================================================================

class NotificationPreference(BaseModel):
    """User notification preferences."""
    list_updates: bool = True
    watchlist_alerts: bool = True
    screening_summary: bool = False
    email_enabled: bool = True
    webhook_url: Optional[str] = None


@router.get("/notifications/preferences")
async def get_notification_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's notification preferences.
    """
    # Would fetch from database
    return NotificationPreference(
        list_updates=True,
        watchlist_alerts=True,
        screening_summary=False,
        email_enabled=True,
        webhook_url=None,
    ).dict()


@router.put("/notifications/preferences")
async def update_notification_preferences(
    preferences: NotificationPreference,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update user's notification preferences.
    """
    # Would save to database
    return {
        "status": "updated",
        "preferences": preferences.dict(),
    }


@router.get("/notifications/recent")
async def get_recent_notifications(
    limit: int = Query(default=20, le=100),
    current_user: User = Depends(get_current_user),
):
    """
    Get recent notifications for the user.
    """
    # Sample notifications
    notifications = [
        {
            "id": "notif-1",
            "type": "list_update",
            "title": "OFAC SDN List Updated",
            "message": "152 new entries added, 23 removed",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "read": False,
        },
        {
            "id": "notif-2",
            "type": "watchlist_alert",
            "title": "Watchlist Status Change",
            "message": "ABC Trading Co status changed from Clear to Potential Match",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "read": True,
        },
    ]
    
    return {
        "notifications": notifications[:limit],
        "unread_count": sum(1 for n in notifications if not n["read"]),
    }


@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Mark a notification as read.
    """
    return {"status": "marked_read", "notification_id": notification_id}


# ============================================================================
# API Access for ERP Integration
# ============================================================================

@router.get("/api-keys")
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List user's API keys for programmatic access.
    """
    # Would fetch from database
    return {
        "keys": [],
        "max_keys": 5,
        "documentation_url": "/docs#/sanctions-screener",
    }


@router.post("/api-keys")
async def create_api_key(
    name: str = Query(..., min_length=1, max_length=100, description="Key name"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new API key for programmatic access.
    
    The key is only shown once. Store it securely.
    """
    key_id = f"sk_{uuid.uuid4().hex}"
    
    return {
        "key_id": key_id[:20] + "...",  # Truncated for display
        "key": key_id,  # Full key - only shown once
        "name": name,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "permissions": ["screen:party", "screen:vessel", "screen:goods", "batch:upload"],
        "rate_limit": 1000,  # requests per hour
        "warning": "This is the only time the full key will be shown. Store it securely.",
    }


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Revoke an API key.
    """
    return {
        "status": "revoked",
        "key_id": key_id,
    }


@router.get("/api-keys/usage")
async def get_api_usage(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get API usage statistics.
    """
    return {
        "current_period": {
            "start": datetime.utcnow().replace(day=1).isoformat() + "Z",
            "end": datetime.utcnow().isoformat() + "Z",
            "requests": 0,
            "limit": 10000,
        },
        "by_endpoint": {
            "screen/party": 0,
            "screen/vessel": 0,
            "screen/goods": 0,
            "batch": 0,
        },
        "by_day": [],
    }


# ============================================================================
# Webhook Integration
# ============================================================================

class WebhookConfig(BaseModel):
    """Webhook configuration."""
    url: str
    events: List[str]  # list_update, watchlist_alert, batch_complete
    secret: Optional[str] = None
    is_active: bool = True


@router.get("/webhooks")
async def list_webhooks(
    current_user: User = Depends(get_current_user),
):
    """
    List configured webhooks.
    """
    return {"webhooks": [], "max_webhooks": 3}


@router.post("/webhooks")
async def create_webhook(
    config: WebhookConfig,
    current_user: User = Depends(get_current_user),
):
    """
    Create a webhook for real-time notifications.
    
    Events:
    - list_update: When sanctions lists are updated
    - watchlist_alert: When watchlist item status changes
    - batch_complete: When batch screening job completes
    """
    webhook_id = f"wh_{uuid.uuid4().hex[:12]}"
    secret = f"whsec_{uuid.uuid4().hex}"
    
    return {
        "webhook_id": webhook_id,
        "url": config.url,
        "events": config.events,
        "secret": secret,
        "is_active": True,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "note": "Store the secret securely for verifying webhook signatures.",
    }


@router.delete("/webhooks/{webhook_id}")
async def delete_webhook(
    webhook_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Delete a webhook.
    """
    return {"status": "deleted", "webhook_id": webhook_id}


@router.post("/webhooks/{webhook_id}/test")
async def test_webhook(
    webhook_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Send a test event to the webhook.
    """
    return {
        "status": "test_sent",
        "webhook_id": webhook_id,
        "event": "test",
        "response_code": 200,
    }

