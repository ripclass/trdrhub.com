"""
Container & Vessel Tracking API

Endpoints for tracking containers and vessels with real-time data
from multiple sources (carrier APIs, AIS providers).
"""

import os
import re
import httpx
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.routers.auth import get_current_user
from app.services.notifications import notification_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tracking", tags=["tracking"])


# ============== Pydantic Models ==============

class Position(BaseModel):
    lat: float
    lon: float
    heading: Optional[float] = None
    course: Optional[float] = None
    speed: Optional[float] = None
    timestamp: Optional[str] = None


class Port(BaseModel):
    name: str
    code: str
    country: str


class VesselInfo(BaseModel):
    name: str
    imo: Optional[str] = None
    mmsi: Optional[str] = None
    voyage: Optional[str] = None
    flag: Optional[str] = None


class TrackingEvent(BaseModel):
    timestamp: str
    event: str
    location: str
    description: str
    status: str  # completed, current, upcoming


class ContainerTrackingResult(BaseModel):
    container_number: str
    carrier: Optional[str] = None
    carrier_code: Optional[str] = None
    status: str
    origin: Port
    destination: Port
    vessel: Optional[VesselInfo] = None
    eta: Optional[str] = None
    eta_confidence: Optional[int] = None
    current_location: Optional[str] = None
    position: Optional[Position] = None
    progress: int = 0
    events: List[TrackingEvent] = []
    last_update: str
    data_source: str


class VesselTrackingResult(BaseModel):
    name: str
    imo: Optional[str] = None
    mmsi: Optional[str] = None
    call_sign: Optional[str] = None
    flag: Optional[str] = None
    vessel_type: str
    status: str
    position: Position
    dimensions: Optional[Dict[str, float]] = None
    destination: Optional[str] = None
    eta: Optional[str] = None
    speed: Optional[float] = None
    heading: Optional[float] = None
    course: Optional[float] = None
    last_update: str
    data_source: str


class TrackingAlert(BaseModel):
    id: str
    user_id: str
    tracking_type: str  # container or vessel
    reference: str
    alert_type: str  # arrival, departure, delay, eta_change
    threshold: Optional[int] = None  # e.g., delay threshold in hours
    notify_email: bool = True
    notify_sms: bool = False
    phone_number: Optional[str] = None
    active: bool = True
    created_at: str


class CreateAlertRequest(BaseModel):
    tracking_type: str
    reference: str
    alert_type: str
    threshold: Optional[int] = None
    notify_email: bool = True
    notify_sms: bool = False
    phone_number: Optional[str] = None


# ============== Carrier API Integrations ==============

# Carrier SCAC codes for identification
CARRIER_CODES = {
    "MAEU": "Maersk",
    "MSCU": "MSC",
    "CMDU": "CMA CGM",
    "HLCU": "Hapag-Lloyd",
    "ONEY": "ONE",
    "EGLV": "Evergreen",
    "COSU": "COSCO",
    "YMLU": "Yang Ming",
    "HDMU": "HMM",
    "ZIMU": "ZIM",
    "OOLU": "OOCL",
}


def detect_carrier(container_number: str) -> tuple[str, str]:
    """Detect carrier from container number prefix."""
    prefix = container_number[:4].upper()
    carrier_name = CARRIER_CODES.get(prefix, "Unknown")
    return prefix, carrier_name


async def fetch_searates_tracking(container_number: str) -> Optional[Dict]:
    """
    Fetch container tracking from Searates/Container-Tracking.org
    Free tier available with rate limits.
    """
    api_key = os.getenv("SEARATES_API_KEY")
    if not api_key:
        logger.warning("SEARATES_API_KEY not configured")
        return None
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://api.searates.com/v1/tracking",
                params={
                    "container": container_number,
                    "api_key": api_key,
                }
            )
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        logger.error(f"Searates API error: {e}")
    return None


async def fetch_portcast_tracking(container_number: str) -> Optional[Dict]:
    """
    Fetch from Portcast API for advanced tracking.
    """
    api_key = os.getenv("PORTCAST_API_KEY")
    if not api_key:
        return None
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://api.portcast.io/api/v1/tracking/container",
                params={"container_number": container_number},
                headers={"Authorization": f"Bearer {api_key}"}
            )
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        logger.error(f"Portcast API error: {e}")
    return None


async def fetch_vessel_ais(identifier: str, search_type: str = "name") -> Optional[Dict]:
    """
    Fetch vessel AIS data from VesselFinder or MarineTraffic.
    """
    # Try Datalastic (has free tier)
    api_key = os.getenv("DATALASTIC_API_KEY")
    if api_key:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if search_type == "imo":
                    url = f"https://api.datalastic.com/api/v0/vessel?api-key={api_key}&imo={identifier}"
                elif search_type == "mmsi":
                    url = f"https://api.datalastic.com/api/v0/vessel?api-key={api_key}&mmsi={identifier}"
                else:
                    url = f"https://api.datalastic.com/api/v0/vessel?api-key={api_key}&name={identifier}"
                
                response = await client.get(url)
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.error(f"Datalastic API error: {e}")
    
    # Fallback to MarineTraffic if configured
    mt_api_key = os.getenv("MARINETRAFFIC_API_KEY")
    if mt_api_key:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"https://services.marinetraffic.com/api/vesselmaster/{mt_api_key}",
                    params={"imo": identifier} if search_type == "imo" else {"mmsi": identifier}
                )
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.error(f"MarineTraffic API error: {e}")
    
    return None


# ============== Mock Data for Development ==============

def generate_mock_container_tracking(container_number: str) -> ContainerTrackingResult:
    """Generate realistic mock tracking data for development."""
    carrier_code, carrier_name = detect_carrier(container_number)
    
    # Generate mock events based on current date
    now = datetime.utcnow()
    events = [
        TrackingEvent(
            timestamp=(now - timedelta(days=15)).isoformat() + "Z",
            event="Gate In",
            location="Shanghai Yangshan Terminal",
            description="Container arrived at origin terminal",
            status="completed"
        ),
        TrackingEvent(
            timestamp=(now - timedelta(days=13)).isoformat() + "Z",
            event="Loaded on Vessel",
            location="Shanghai Port",
            description=f"Container loaded onto vessel",
            status="completed"
        ),
        TrackingEvent(
            timestamp=(now - timedelta(days=12)).isoformat() + "Z",
            event="Vessel Departed",
            location="Shanghai Port",
            description="Vessel departed for destination",
            status="completed"
        ),
        TrackingEvent(
            timestamp=(now - timedelta(days=5)).isoformat() + "Z",
            event="In Transit",
            location="Indian Ocean",
            description="Vessel in transit",
            status="current"
        ),
        TrackingEvent(
            timestamp=(now + timedelta(days=3)).isoformat() + "Z",
            event="Arrival at Destination",
            location="Rotterdam Europoort",
            description="Expected arrival",
            status="upcoming"
        ),
    ]
    
    return ContainerTrackingResult(
        container_number=container_number,
        carrier=carrier_name,
        carrier_code=carrier_code,
        status="in_transit",
        origin=Port(name="Shanghai", code="CNSHA", country="China"),
        destination=Port(name="Rotterdam", code="NLRTM", country="Netherlands"),
        vessel=VesselInfo(
            name=f"{carrier_name.upper()} ATLANTIC",
            imo="9703318",
            mmsi="353136000",
            voyage="FA234E",
            flag="Panama"
        ),
        eta=(now + timedelta(days=3)).isoformat() + "Z",
        eta_confidence=92,
        current_location="Indian Ocean (Near Sri Lanka)",
        position=Position(
            lat=6.9271,
            lon=79.8612,
            heading=270,
            course=268,
            speed=18.5,
            timestamp=now.isoformat() + "Z"
        ),
        progress=68,
        events=events,
        last_update=now.isoformat() + "Z",
        data_source="mock"
    )


def generate_mock_vessel_tracking(identifier: str) -> VesselTrackingResult:
    """Generate realistic mock vessel data for development."""
    now = datetime.utcnow()
    
    # Clean up vessel name
    vessel_name = identifier.upper().replace("-", " ")
    
    return VesselTrackingResult(
        name=vessel_name,
        imo="9703318",
        mmsi="353136000",
        call_sign="3FQM9",
        flag="Panama",
        vessel_type="Container Ship",
        status="underway",
        position=Position(
            lat=28.9167,
            lon=33.0667,
            heading=315,
            course=312,
            speed=18.5,
            timestamp=now.isoformat() + "Z"
        ),
        dimensions={
            "length": 395.4,
            "beam": 59.0,
            "draught": 16.0
        },
        destination="NLRTM (Rotterdam)",
        eta=(now + timedelta(days=5)).isoformat() + "Z",
        speed=18.5,
        heading=315,
        course=312,
        last_update=now.isoformat() + "Z",
        data_source="mock"
    )


# ============== Internal Helper Functions ==============

async def _track_container_internal(container_number: str) -> ContainerTrackingResult:
    """
    Internal function to track a container (without auth dependency).
    Used by both endpoints and background tasks.
    """
    # Normalize container number
    container_number = re.sub(r'[^A-Z0-9]', '', container_number.upper())
    
    if len(container_number) < 10 or len(container_number) > 12:
        raise HTTPException(
            status_code=400,
            detail="Invalid container number format. Expected format: MSCU1234567"
        )
    
    # Try real APIs first
    result = None
    
    # Try Searates
    searates_data = await fetch_searates_tracking(container_number)
    if searates_data and searates_data.get("data"):
        # Parse Searates response
        data = searates_data["data"]
        result = ContainerTrackingResult(
            container_number=container_number,
            carrier=data.get("carrier", {}).get("name"),
            carrier_code=data.get("carrier", {}).get("code"),
            status=data.get("status", "unknown"),
            origin=Port(
                name=data.get("origin", {}).get("name", "Unknown"),
                code=data.get("origin", {}).get("code", ""),
                country=data.get("origin", {}).get("country", "")
            ),
            destination=Port(
                name=data.get("destination", {}).get("name", "Unknown"),
                code=data.get("destination", {}).get("code", ""),
                country=data.get("destination", {}).get("country", "")
            ),
            eta=data.get("eta"),
            current_location=data.get("location", {}).get("name"),
            events=[
                TrackingEvent(
                    timestamp=e.get("date", ""),
                    event=e.get("event", ""),
                    location=e.get("location", ""),
                    description=e.get("description", ""),
                    status="completed"
                )
                for e in data.get("events", [])
            ],
            last_update=datetime.utcnow().isoformat() + "Z",
            data_source="searates"
        )
    
    # Try Portcast as fallback
    if not result:
        portcast_data = await fetch_portcast_tracking(container_number)
        if portcast_data:
            # Parse Portcast response (structure may vary)
            result = ContainerTrackingResult(
                container_number=container_number,
                status=portcast_data.get("status", "unknown"),
                origin=Port(
                    name=portcast_data.get("pod", {}).get("name", "Unknown"),
                    code=portcast_data.get("pod", {}).get("locode", ""),
                    country=""
                ),
                destination=Port(
                    name=portcast_data.get("poa", {}).get("name", "Unknown"),
                    code=portcast_data.get("poa", {}).get("locode", ""),
                    country=""
                ),
                eta=portcast_data.get("eta"),
                last_update=datetime.utcnow().isoformat() + "Z",
                data_source="portcast"
            )
    
    # Fall back to mock data if no API available
    if not result:
        logger.info(f"Using mock data for container {container_number}")
        result = generate_mock_container_tracking(container_number)
    
    return result


async def _track_vessel_internal(identifier: str, search_type: str = "name") -> VesselTrackingResult:
    """
    Internal function to track a vessel (without auth dependency).
    Used by both endpoints and background tasks.
    """
    # Try real AIS data first
    ais_data = await fetch_vessel_ais(identifier, search_type)
    
    if ais_data and ais_data.get("data"):
        vessel = ais_data["data"]
        return VesselTrackingResult(
            name=vessel.get("name", identifier),
            imo=vessel.get("imo", ""),
            mmsi=vessel.get("mmsi", ""),
            call_sign=vessel.get("callsign", ""),
            flag=vessel.get("flag", "Unknown"),
            vessel_type=vessel.get("type", "Container Ship"),
            status=vessel.get("navigational_status", "underway"),
            position=Position(
                lat=vessel.get("lat", 0),
                lon=vessel.get("lon", 0),
                heading=vessel.get("heading", 0),
                course=vessel.get("course", 0),
                speed=vessel.get("speed", 0),
                timestamp=vessel.get("timestamp", datetime.utcnow().isoformat() + "Z")
            ),
            destination=vessel.get("destination", "Unknown"),
            eta=vessel.get("eta"),
            speed=vessel.get("speed", 0),
            heading=vessel.get("heading", 0),
            course=vessel.get("course", 0),
            last_update=datetime.utcnow().isoformat() + "Z",
            data_source="ais"
        )
    
    # Fall back to mock data if no API available
    logger.info(f"Using mock data for vessel {identifier}")
    return generate_mock_vessel_tracking(identifier)


# ============== API Endpoints ==============

@router.get("/container/{container_number}", response_model=ContainerTrackingResult)
async def track_container(
    container_number: str,
    current_user: User = Depends(get_current_user),
):
    """
    Track a container by container number.
    
    Supports formats:
    - Standard: MSCU1234567 (4 letters + 7 digits)
    - With check digit: MSCU123456-7
    """
    result = await _track_container_internal(container_number)
    
    # TODO: Log usage for billing
    # await log_tracking_usage(current_user.id, "container", container_number)
    
    return result


@router.get("/vessel/{identifier}", response_model=VesselTrackingResult)
async def track_vessel(
    identifier: str,
    search_type: str = Query("name", regex="^(name|imo|mmsi)$"),
    current_user: User = Depends(get_current_user),
):
    """
    Track a vessel by name, IMO, or MMSI number.
    
    Query params:
    - search_type: "name", "imo", or "mmsi"
    """
    result = await _track_vessel_internal(identifier, search_type)
    
    # TODO: Log usage for billing
    # await log_tracking_usage(current_user.id, "vessel", identifier)
    
    return result


@router.get("/search")
async def search_tracking(
    q: str = Query(..., min_length=3),
    type: str = Query("container", regex="^(container|vessel|bl)$"),
    current_user: User = Depends(get_current_user),
):
    """
    Search for containers, vessels, or B/L numbers.
    """
    q = q.strip().upper()
    
    if type == "container":
        result = await track_container(q, current_user)
        return {"type": "container", "result": result}
    elif type == "vessel":
        result = await track_vessel(q, "name", current_user)
        return {"type": "vessel", "result": result}
    elif type == "bl":
        # B/L search - try to find associated container
        # For now, treat it like a container search
        result = await track_container(q, current_user)
        return {"type": "container", "result": result}
    
    raise HTTPException(status_code=400, detail="Invalid search type")


# ============== Alerts Management ==============

# In-memory storage for alerts (replace with database in production)
_alerts_store: Dict[str, TrackingAlert] = {}


@router.post("/alerts", response_model=TrackingAlert)
async def create_alert(
    request: CreateAlertRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Create a tracking alert for a container or vessel.
    """
    import uuid
    
    alert_id = str(uuid.uuid4())
    alert = TrackingAlert(
        id=alert_id,
        user_id=str(current_user.id),
        tracking_type=request.tracking_type,
        reference=request.reference.upper(),
        alert_type=request.alert_type,
        threshold=request.threshold,
        notify_email=request.notify_email,
        notify_sms=request.notify_sms,
        phone_number=request.phone_number,
        active=True,
        created_at=datetime.utcnow().isoformat() + "Z"
    )
    
    _alerts_store[alert_id] = alert
    
    # TODO: Store in database
    # TODO: Set up background job to check alerts
    
    return alert


@router.get("/alerts", response_model=List[TrackingAlert])
async def list_alerts(
    current_user: User = Depends(get_current_user),
):
    """
    List all tracking alerts for the current user.
    """
    user_alerts = [
        alert for alert in _alerts_store.values()
        if alert.user_id == str(current_user.id)
    ]
    return user_alerts


@router.delete("/alerts/{alert_id}")
async def delete_alert(
    alert_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Delete a tracking alert.
    """
    if alert_id not in _alerts_store:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert = _alerts_store[alert_id]
    if alert.user_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    del _alerts_store[alert_id]
    return {"message": "Alert deleted"}


@router.post("/alerts/{alert_id}/toggle")
async def toggle_alert(
    alert_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Toggle an alert's active status.
    """
    if alert_id not in _alerts_store:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert = _alerts_store[alert_id]
    if alert.user_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    alert.active = not alert.active
    return alert


# ============== Shipment Portfolio ==============

@router.get("/portfolio")
async def get_portfolio(
    current_user: User = Depends(get_current_user),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """
    Get all tracked shipments for the current user.
    """
    # TODO: Fetch from database
    # For now, return mock data
    return {
        "total": 4,
        "shipments": [
            {
                "id": "1",
                "reference": "MSCU1234567",
                "type": "container",
                "status": "in_transit",
                "origin": "Shanghai, CN",
                "destination": "Rotterdam, NL",
                "eta": (datetime.utcnow() + timedelta(days=3)).isoformat() + "Z",
                "progress": 68,
                "alerts": 0,
            },
            {
                "id": "2",
                "reference": "MAEU987654321",
                "type": "container",
                "status": "delayed",
                "origin": "Chittagong, BD",
                "destination": "Hamburg, DE",
                "eta": (datetime.utcnow() + timedelta(days=7)).isoformat() + "Z",
                "progress": 55,
                "alerts": 2,
            },
            {
                "id": "3",
                "reference": "HLCU5678901",
                "type": "container",
                "status": "at_port",
                "origin": "Mumbai, IN",
                "destination": "Los Angeles, US",
                "eta": (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z",
                "progress": 42,
                "alerts": 1,
            },
        ],
        "stats": {
            "active": 3,
            "delivered_30d": 12,
            "delayed": 1,
            "on_time_rate": 92,
        }
    }


# ============== Background Alert Processing ==============

async def check_and_send_alerts():
    """
    Background task to check alerts and send notifications.
    Should be run periodically (e.g., every 15 minutes).
    """
    from app.database import SessionLocal
    from app.models.user import User
    
    db = SessionLocal()
    try:
        for alert in _alerts_store.values():
            if not alert.active:
                continue
            
            try:
                # Get user info for notifications
                user = db.query(User).filter(User.id == alert.user_id).first()
                if not user:
                    logger.warning(f"User {alert.user_id} not found for alert {alert.id}")
                    continue
                
                user_email = user.email if alert.notify_email else None
                user_phone = alert.phone_number if alert.notify_sms else None
                
                if alert.tracking_type == "container":
                    # Fetch current tracking data
                    container_data = await _track_container_internal(alert.reference)
                    
                    # Check for arrival alert
                    if alert.alert_type == "arrival":
                        if container_data.eta:
                            eta_date = datetime.fromisoformat(container_data.eta.replace("Z", "+00:00"))
                            now = datetime.now(eta_date.tzinfo)
                            hours_until_arrival = (eta_date - now).total_seconds() / 3600
                            
                            # Alert if within 24 hours of arrival
                            if 0 <= hours_until_arrival <= 24:
                                await notification_service.send_container_arrival_alert(
                                    container_number=container_data.container_number,
                                    vessel=container_data.vessel.name if container_data.vessel else "Unknown",
                                    port=container_data.destination.name,
                                    eta=container_data.eta,
                                    user_email=user_email,
                                    user_phone=user_phone,
                                    user_name=user.email.split("@")[0] if user.email else "User",
                                )
                                logger.info(f"Sent arrival alert for container {alert.reference}")
                    
                    # Check for delay alert
                    elif alert.alert_type == "delay" and alert.threshold:
                        # Compare current ETA with previous ETA (would need to store previous ETA)
                        # For now, just log
                        logger.info(f"Delay check for container {alert.reference}")
                
                elif alert.tracking_type == "vessel":
                    # Determine search type from reference
                    search_type = "imo" if alert.reference.startswith("IMO") else "mmsi" if alert.reference.isdigit() and len(alert.reference) == 9 else "name"
                    # Fetch current vessel data
                    vessel_data = await _track_vessel_internal(alert.reference, search_type)
                    
                    # Similar logic for vessel alerts
                    if alert.alert_type == "arrival" and vessel_data.eta:
                        eta_date = datetime.fromisoformat(vessel_data.eta.replace("Z", "+00:00"))
                        now = datetime.now(eta_date.tzinfo)
                        hours_until_arrival = (eta_date - now).total_seconds() / 3600
                        
                        if 0 <= hours_until_arrival <= 24:
                            await notification_service.send_container_arrival_alert(
                                container_number=vessel_data.name,  # Using vessel name as reference
                                vessel=vessel_data.name,
                                port=vessel_data.destination or "Unknown",
                                eta=vessel_data.eta,
                                user_email=user_email,
                                user_phone=user_phone,
                                user_name=user.email.split("@")[0] if user.email else "User",
                            )
                            logger.info(f"Sent arrival alert for vessel {alert.reference}")
            
            except Exception as e:
                logger.error(f"Error processing alert {alert.id}: {e}")
    finally:
        db.close()


# ============== Health Check ==============

@router.post("/alerts/check")
async def trigger_alert_check(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
):
    """
    Manually trigger alert checking (admin/testing endpoint).
    In production, this should be run via a cron job or scheduled task.
    """
    # Only allow admins or system users
    if current_user.role not in ["system_admin", "admin"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    background_tasks.add_task(check_and_send_alerts)
    return {"message": "Alert check triggered", "timestamp": datetime.utcnow().isoformat() + "Z"}


@router.get("/health")
async def tracking_health():
    """Check tracking API health and data source availability."""
    sources = {
        "searates": bool(os.getenv("SEARATES_API_KEY")),
        "portcast": bool(os.getenv("PORTCAST_API_KEY")),
        "datalastic": bool(os.getenv("DATALASTIC_API_KEY")),
        "marinetraffic": bool(os.getenv("MARINETRAFFIC_API_KEY")),
    }
    
    notification_status = notification_service.status()
    
    return {
        "status": "healthy",
        "data_sources": sources,
        "notifications": notification_status,
        "fallback": "mock",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

