"""
Container & Vessel Tracking API

Endpoints for tracking containers and vessels with real-time data
from multiple sources (carrier APIs, AIS providers).
"""

import os
import re
import httpx
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.database import get_db
from app.models import User
from app.models.tracking import (
    TrackedShipment,
    TrackingAlert as TrackingAlertModel,
    TrackingEvent as TrackingEventModel,
    TrackingNotification as TrackingNotificationModel,
    TrackingType,
    ShipmentStatus,
    AlertType,
    NotificationStatus,
)
from app.routers.auth import get_current_user
from app.services.notifications import notification_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tracking", tags=["tracking"])


# ============== Pydantic Models (API) ==============

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


class TrackingEventResponse(BaseModel):
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
    events: List[TrackingEventResponse] = []
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


class TrackingAlertResponse(BaseModel):
    id: str
    user_id: str
    tracking_type: str
    reference: str
    alert_type: str
    threshold_hours: Optional[int] = None
    threshold_days: Optional[int] = None
    notify_email: bool = True
    notify_sms: bool = False
    email_address: Optional[str] = None
    phone_number: Optional[str] = None
    is_active: bool = True
    last_triggered: Optional[str] = None
    trigger_count: int = 0
    created_at: str


class CreateAlertRequest(BaseModel):
    tracking_type: str
    reference: str
    alert_type: str
    threshold_hours: Optional[int] = None
    threshold_days: Optional[int] = None
    notify_email: bool = True
    notify_sms: bool = False
    email_address: Optional[str] = None
    phone_number: Optional[str] = None


class AddToPortfolioRequest(BaseModel):
    reference: str
    tracking_type: str = "container"
    nickname: Optional[str] = None
    lc_number: Optional[str] = None
    lc_expiry: Optional[str] = None
    bl_number: Optional[str] = None
    notes: Optional[str] = None


class PortfolioShipmentResponse(BaseModel):
    id: str
    reference: str
    tracking_type: str
    nickname: Optional[str] = None
    status: Optional[str] = None
    carrier: Optional[str] = None
    origin_port: Optional[str] = None
    origin_code: Optional[str] = None
    destination_port: Optional[str] = None
    destination_code: Optional[str] = None
    eta: Optional[str] = None
    progress: int = 0
    vessel_name: Optional[str] = None
    lc_number: Optional[str] = None
    lc_expiry: Optional[str] = None
    is_active: bool = True
    alerts_count: int = 0
    last_checked: Optional[str] = None
    created_at: str


# ============== Carrier API Integrations ==============

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
    """Fetch container tracking from Searates."""
    api_key = os.getenv("SEARATES_API_KEY")
    if not api_key:
        logger.warning("SEARATES_API_KEY not configured")
        return None
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://api.searates.com/v1/tracking",
                params={"container": container_number, "api_key": api_key}
            )
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        logger.error(f"Searates API error: {e}")
    return None


async def fetch_portcast_tracking(container_number: str) -> Optional[Dict]:
    """Fetch from Portcast API."""
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
    """Fetch vessel AIS data from Datalastic or MarineTraffic."""
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
    """Generate realistic mock tracking data."""
    carrier_code, carrier_name = detect_carrier(container_number)
    now = datetime.utcnow()
    
    events = [
        TrackingEventResponse(
            timestamp=(now - timedelta(days=15)).isoformat() + "Z",
            event="Gate In",
            location="Shanghai Yangshan Terminal",
            description="Container arrived at origin terminal",
            status="completed"
        ),
        TrackingEventResponse(
            timestamp=(now - timedelta(days=13)).isoformat() + "Z",
            event="Loaded on Vessel",
            location="Shanghai Port",
            description="Container loaded onto vessel",
            status="completed"
        ),
        TrackingEventResponse(
            timestamp=(now - timedelta(days=12)).isoformat() + "Z",
            event="Vessel Departed",
            location="Shanghai Port",
            description="Vessel departed for destination",
            status="completed"
        ),
        TrackingEventResponse(
            timestamp=(now - timedelta(days=5)).isoformat() + "Z",
            event="In Transit",
            location="Indian Ocean",
            description="Vessel in transit",
            status="current"
        ),
        TrackingEventResponse(
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
            lat=6.9271, lon=79.8612, heading=270, course=268, speed=18.5,
            timestamp=now.isoformat() + "Z"
        ),
        progress=68,
        events=events,
        last_update=now.isoformat() + "Z",
        data_source="mock"
    )


def generate_mock_vessel_tracking(identifier: str) -> VesselTrackingResult:
    """Generate realistic mock vessel data."""
    now = datetime.utcnow()
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
            lat=28.9167, lon=33.0667, heading=315, course=312, speed=18.5,
            timestamp=now.isoformat() + "Z"
        ),
        dimensions={"length": 395.4, "beam": 59.0, "draught": 16.0},
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
    """Internal function to track a container (without auth dependency)."""
    container_number = re.sub(r'[^A-Z0-9]', '', container_number.upper())
    
    if len(container_number) < 10 or len(container_number) > 12:
        raise HTTPException(
            status_code=400,
            detail="Invalid container number format. Expected format: MSCU1234567"
        )
    
    result = None
    
    # Try Searates
    searates_data = await fetch_searates_tracking(container_number)
    if searates_data and searates_data.get("data"):
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
                TrackingEventResponse(
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
    
    # Fall back to mock data
    if not result:
        logger.info(f"Using mock data for container {container_number}")
        result = generate_mock_container_tracking(container_number)
    
    return result


async def _track_vessel_internal(identifier: str, search_type: str = "name") -> VesselTrackingResult:
    """Internal function to track a vessel (without auth dependency)."""
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
    
    logger.info(f"Using mock data for vessel {identifier}")
    return generate_mock_vessel_tracking(identifier)


# ============== API Endpoints ==============

@router.get("/container/{container_number}", response_model=ContainerTrackingResult)
async def track_container(
    container_number: str,
    current_user: User = Depends(get_current_user),
):
    """Track a container by container number."""
    result = await _track_container_internal(container_number)
    # TODO: Log usage for billing
    return result


@router.get("/vessel/{identifier}", response_model=VesselTrackingResult)
async def track_vessel(
    identifier: str,
    search_type: str = Query("name", regex="^(name|imo|mmsi)$"),
    current_user: User = Depends(get_current_user),
):
    """Track a vessel by name, IMO, or MMSI number."""
    result = await _track_vessel_internal(identifier, search_type)
    return result


@router.get("/search")
async def search_tracking(
    q: str = Query(..., min_length=3),
    type: str = Query("container", regex="^(container|vessel|bl)$"),
    current_user: User = Depends(get_current_user),
):
    """Search for containers, vessels, or B/L numbers."""
    q = q.strip().upper()
    
    if type == "container":
        result = await _track_container_internal(q)
        return {"type": "container", "result": result}
    elif type == "vessel":
        result = await _track_vessel_internal(q, "name")
        return {"type": "vessel", "result": result}
    elif type == "bl":
        result = await _track_container_internal(q)
        return {"type": "container", "result": result}
    
    raise HTTPException(status_code=400, detail="Invalid search type")


# ============== Alerts Management (Database-backed) ==============

def _alert_model_to_response(alert: TrackingAlertModel) -> TrackingAlertResponse:
    """Convert database model to API response."""
    return TrackingAlertResponse(
        id=str(alert.id),
        user_id=str(alert.user_id),
        tracking_type=alert.tracking_type,
        reference=alert.reference,
        alert_type=alert.alert_type,
        threshold_hours=alert.threshold_hours,
        threshold_days=alert.threshold_days,
        notify_email=alert.notify_email,
        notify_sms=alert.notify_sms,
        email_address=alert.email_address,
        phone_number=alert.phone_number,
        is_active=alert.is_active,
        last_triggered=alert.last_triggered.isoformat() + "Z" if alert.last_triggered else None,
        trigger_count=alert.trigger_count,
        created_at=alert.created_at.isoformat() + "Z" if alert.created_at else datetime.utcnow().isoformat() + "Z"
    )


@router.post("/alerts", response_model=TrackingAlertResponse)
async def create_alert(
    request: CreateAlertRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a tracking alert for a container or vessel."""
    # Validate alert_type
    valid_types = [t.value for t in AlertType]
    if request.alert_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid alert_type. Must be one of: {', '.join(valid_types)}"
        )
    
    # Create alert in database
    alert = TrackingAlertModel(
        id=uuid.uuid4(),
        user_id=current_user.id,
        tracking_type=request.tracking_type,
        reference=request.reference.upper(),
        alert_type=request.alert_type,
        threshold_hours=request.threshold_hours,
        threshold_days=request.threshold_days,
        notify_email=request.notify_email,
        notify_sms=request.notify_sms,
        email_address=request.email_address,
        phone_number=request.phone_number,
        is_active=True,
    )
    
    db.add(alert)
    db.commit()
    db.refresh(alert)
    
    logger.info(f"Created alert {alert.id} for {alert.reference} (user: {current_user.id})")
    
    return _alert_model_to_response(alert)


@router.get("/alerts", response_model=List[TrackingAlertResponse])
async def list_alerts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    active_only: bool = Query(False, description="Filter to active alerts only"),
):
    """List all tracking alerts for the current user."""
    query = db.query(TrackingAlertModel).filter(
        TrackingAlertModel.user_id == current_user.id
    )
    
    if active_only:
        query = query.filter(TrackingAlertModel.is_active == True)
    
    alerts = query.order_by(TrackingAlertModel.created_at.desc()).all()
    
    return [_alert_model_to_response(alert) for alert in alerts]


@router.delete("/alerts/{alert_id}")
async def delete_alert(
    alert_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a tracking alert."""
    try:
        alert_uuid = uuid.UUID(alert_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid alert ID format")
    
    alert = db.query(TrackingAlertModel).filter(
        TrackingAlertModel.id == alert_uuid
    ).first()
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    if alert.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    db.delete(alert)
    db.commit()
    
    logger.info(f"Deleted alert {alert_id} (user: {current_user.id})")
    
    return {"message": "Alert deleted", "id": alert_id}


@router.post("/alerts/{alert_id}/toggle", response_model=TrackingAlertResponse)
async def toggle_alert(
    alert_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Toggle an alert's active status."""
    try:
        alert_uuid = uuid.UUID(alert_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid alert ID format")
    
    alert = db.query(TrackingAlertModel).filter(
        TrackingAlertModel.id == alert_uuid
    ).first()
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    if alert.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    alert.is_active = not alert.is_active
    db.commit()
    db.refresh(alert)
    
    logger.info(f"Toggled alert {alert_id} to {'active' if alert.is_active else 'inactive'}")
    
    return _alert_model_to_response(alert)


# ============== Portfolio Management (Database-backed) ==============

def _shipment_model_to_response(shipment: TrackedShipment, alerts_count: int = 0) -> PortfolioShipmentResponse:
    """Convert database model to API response."""
    return PortfolioShipmentResponse(
        id=str(shipment.id),
        reference=shipment.reference,
        tracking_type=shipment.tracking_type,
        nickname=shipment.nickname,
        status=shipment.status,
        carrier=shipment.carrier,
        origin_port=shipment.origin_port,
        origin_code=shipment.origin_code,
        destination_port=shipment.destination_port,
        destination_code=shipment.destination_code,
        eta=shipment.eta.isoformat() + "Z" if shipment.eta else None,
        progress=shipment.progress or 0,
        vessel_name=shipment.vessel_name,
        lc_number=shipment.lc_number,
        lc_expiry=shipment.lc_expiry.isoformat() + "Z" if shipment.lc_expiry else None,
        is_active=shipment.is_active,
        alerts_count=alerts_count,
        last_checked=shipment.last_checked.isoformat() + "Z" if shipment.last_checked else None,
        created_at=shipment.created_at.isoformat() + "Z" if shipment.created_at else datetime.utcnow().isoformat() + "Z"
    )


@router.post("/portfolio/add", response_model=PortfolioShipmentResponse)
async def add_to_portfolio(
    request: AddToPortfolioRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a shipment to the user's portfolio."""
    reference = request.reference.upper().strip()
    
    # Check if already exists
    existing = db.query(TrackedShipment).filter(
        TrackedShipment.user_id == current_user.id,
        TrackedShipment.reference == reference,
        TrackedShipment.tracking_type == request.tracking_type,
    ).first()
    
    if existing:
        if existing.is_active:
            raise HTTPException(
                status_code=400,
                detail="Shipment already in portfolio"
            )
        else:
            # Re-activate the shipment
            existing.is_active = True
            existing.nickname = request.nickname or existing.nickname
            existing.lc_number = request.lc_number or existing.lc_number
            existing.notes = request.notes or existing.notes
            db.commit()
            db.refresh(existing)
            return _shipment_model_to_response(existing)
    
    # Fetch current tracking data
    try:
        if request.tracking_type == "container":
            tracking_data = await _track_container_internal(reference)
            shipment = TrackedShipment(
                id=uuid.uuid4(),
                user_id=current_user.id,
                company_id=current_user.company_id if hasattr(current_user, 'company_id') else None,
                reference=reference,
                tracking_type="container",
                nickname=request.nickname,
                carrier=tracking_data.carrier,
                carrier_code=tracking_data.carrier_code,
                origin_port=tracking_data.origin.name,
                origin_code=tracking_data.origin.code,
                origin_country=tracking_data.origin.country,
                destination_port=tracking_data.destination.name,
                destination_code=tracking_data.destination.code,
                destination_country=tracking_data.destination.country,
                status=tracking_data.status,
                current_location=tracking_data.current_location,
                latitude=tracking_data.position.lat if tracking_data.position else None,
                longitude=tracking_data.position.lon if tracking_data.position else None,
                progress=tracking_data.progress,
                eta=datetime.fromisoformat(tracking_data.eta.replace("Z", "+00:00")) if tracking_data.eta else None,
                eta_confidence=tracking_data.eta_confidence,
                vessel_name=tracking_data.vessel.name if tracking_data.vessel else None,
                vessel_imo=tracking_data.vessel.imo if tracking_data.vessel else None,
                vessel_mmsi=tracking_data.vessel.mmsi if tracking_data.vessel else None,
                voyage=tracking_data.vessel.voyage if tracking_data.vessel else None,
                vessel_flag=tracking_data.vessel.flag if tracking_data.vessel else None,
                lc_number=request.lc_number,
                lc_expiry=datetime.fromisoformat(request.lc_expiry.replace("Z", "+00:00")) if request.lc_expiry else None,
                bl_number=request.bl_number,
                notes=request.notes,
                data_source=tracking_data.data_source,
                last_checked=datetime.utcnow(),
            )
        else:
            tracking_data = await _track_vessel_internal(reference, "name")
            shipment = TrackedShipment(
                id=uuid.uuid4(),
                user_id=current_user.id,
                company_id=current_user.company_id if hasattr(current_user, 'company_id') else None,
                reference=reference,
                tracking_type="vessel",
                nickname=request.nickname,
                status=tracking_data.status,
                latitude=tracking_data.position.lat if tracking_data.position else None,
                longitude=tracking_data.position.lon if tracking_data.position else None,
                eta=datetime.fromisoformat(tracking_data.eta.replace("Z", "+00:00")) if tracking_data.eta else None,
                vessel_name=tracking_data.name,
                vessel_imo=tracking_data.imo,
                vessel_mmsi=tracking_data.mmsi,
                vessel_flag=tracking_data.flag,
                lc_number=request.lc_number,
                lc_expiry=datetime.fromisoformat(request.lc_expiry.replace("Z", "+00:00")) if request.lc_expiry else None,
                notes=request.notes,
                data_source=tracking_data.data_source,
                last_checked=datetime.utcnow(),
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching tracking data: {e}")
        # Create with minimal data
        shipment = TrackedShipment(
            id=uuid.uuid4(),
            user_id=current_user.id,
            reference=reference,
            tracking_type=request.tracking_type,
            nickname=request.nickname,
            lc_number=request.lc_number,
            lc_expiry=datetime.fromisoformat(request.lc_expiry.replace("Z", "+00:00")) if request.lc_expiry else None,
            bl_number=request.bl_number,
            notes=request.notes,
            status="unknown",
        )
    
    db.add(shipment)
    db.commit()
    db.refresh(shipment)
    
    logger.info(f"Added shipment {reference} to portfolio (user: {current_user.id})")
    
    return _shipment_model_to_response(shipment)


@router.delete("/portfolio/{shipment_id}")
async def remove_from_portfolio(
    shipment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    hard_delete: bool = Query(False, description="Permanently delete instead of soft delete"),
):
    """Remove a shipment from the portfolio."""
    try:
        shipment_uuid = uuid.UUID(shipment_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid shipment ID format")
    
    shipment = db.query(TrackedShipment).filter(
        TrackedShipment.id == shipment_uuid
    ).first()
    
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    
    if shipment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if hard_delete:
        db.delete(shipment)
    else:
        shipment.is_active = False
    
    db.commit()
    
    logger.info(f"Removed shipment {shipment_id} from portfolio (hard_delete: {hard_delete})")
    
    return {"message": "Shipment removed from portfolio", "id": shipment_id}


@router.get("/portfolio")
async def get_portfolio(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    active_only: bool = Query(True, description="Only show active shipments"),
):
    """Get all tracked shipments for the current user."""
    # Build query
    query = db.query(TrackedShipment).filter(
        TrackedShipment.user_id == current_user.id
    )
    
    if active_only:
        query = query.filter(TrackedShipment.is_active == True)
    
    # Get total count
    total = query.count()
    
    # Get shipments with pagination
    shipments = query.order_by(TrackedShipment.created_at.desc()).offset(offset).limit(limit).all()
    
    # Get alert counts for each shipment
    shipment_responses = []
    for shipment in shipments:
        alerts_count = db.query(TrackingAlertModel).filter(
            TrackingAlertModel.shipment_id == shipment.id,
            TrackingAlertModel.is_active == True
        ).count()
        shipment_responses.append(_shipment_model_to_response(shipment, alerts_count))
    
    # Calculate stats
    all_shipments = db.query(TrackedShipment).filter(
        TrackedShipment.user_id == current_user.id,
        TrackedShipment.is_active == True
    ).all()
    
    delayed_count = sum(1 for s in all_shipments if s.status == "delayed")
    delivered_30d = db.query(TrackedShipment).filter(
        TrackedShipment.user_id == current_user.id,
        TrackedShipment.status == "delivered",
        TrackedShipment.ata >= datetime.utcnow() - timedelta(days=30)
    ).count()
    
    on_time_rate = 100 - (delayed_count / max(len(all_shipments), 1) * 100) if all_shipments else 100
    
    return {
        "total": total,
        "shipments": shipment_responses,
        "stats": {
            "active": len(all_shipments),
            "delivered_30d": delivered_30d,
            "delayed": delayed_count,
            "on_time_rate": round(on_time_rate),
        }
    }


@router.post("/portfolio/{shipment_id}/refresh", response_model=PortfolioShipmentResponse)
async def refresh_shipment(
    shipment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Refresh tracking data for a portfolio shipment."""
    try:
        shipment_uuid = uuid.UUID(shipment_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid shipment ID format")
    
    shipment = db.query(TrackedShipment).filter(
        TrackedShipment.id == shipment_uuid
    ).first()
    
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    
    if shipment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Fetch fresh tracking data
    try:
        if shipment.tracking_type == "container":
            tracking_data = await _track_container_internal(shipment.reference)
            shipment.carrier = tracking_data.carrier
            shipment.carrier_code = tracking_data.carrier_code
            shipment.origin_port = tracking_data.origin.name
            shipment.origin_code = tracking_data.origin.code
            shipment.destination_port = tracking_data.destination.name
            shipment.destination_code = tracking_data.destination.code
            shipment.status = tracking_data.status
            shipment.current_location = tracking_data.current_location
            shipment.latitude = tracking_data.position.lat if tracking_data.position else None
            shipment.longitude = tracking_data.position.lon if tracking_data.position else None
            shipment.progress = tracking_data.progress
            shipment.eta = datetime.fromisoformat(tracking_data.eta.replace("Z", "+00:00")) if tracking_data.eta else None
            shipment.eta_confidence = tracking_data.eta_confidence
            if tracking_data.vessel:
                shipment.vessel_name = tracking_data.vessel.name
                shipment.vessel_imo = tracking_data.vessel.imo
                shipment.vessel_mmsi = tracking_data.vessel.mmsi
                shipment.voyage = tracking_data.vessel.voyage
                shipment.vessel_flag = tracking_data.vessel.flag
            shipment.data_source = tracking_data.data_source
        else:
            tracking_data = await _track_vessel_internal(shipment.reference, "name")
            shipment.status = tracking_data.status
            shipment.latitude = tracking_data.position.lat if tracking_data.position else None
            shipment.longitude = tracking_data.position.lon if tracking_data.position else None
            shipment.eta = datetime.fromisoformat(tracking_data.eta.replace("Z", "+00:00")) if tracking_data.eta else None
            shipment.vessel_name = tracking_data.name
            shipment.vessel_imo = tracking_data.imo
            shipment.vessel_mmsi = tracking_data.mmsi
            shipment.vessel_flag = tracking_data.flag
            shipment.data_source = tracking_data.data_source
        
        shipment.last_checked = datetime.utcnow()
        shipment.last_updated = datetime.utcnow()
        
        db.commit()
        db.refresh(shipment)
        
        logger.info(f"Refreshed shipment {shipment_id}")
        
    except Exception as e:
        logger.error(f"Error refreshing shipment {shipment_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to refresh tracking data")
    
    return _shipment_model_to_response(shipment)


# ============== Background Alert Processing ==============

async def check_and_send_alerts(db: Session):
    """
    Background task to check alerts and send notifications.
    Should be run periodically (e.g., every 15 minutes).
    """
    # Get all active alerts
    alerts = db.query(TrackingAlertModel).filter(
        TrackingAlertModel.is_active == True
    ).all()
    
    logger.info(f"Checking {len(alerts)} active alerts")
    
    for alert in alerts:
        try:
            # Get user info
            user = db.query(User).filter(User.id == alert.user_id).first()
            if not user:
                logger.warning(f"User {alert.user_id} not found for alert {alert.id}")
                continue
            
            user_email = alert.email_address or user.email if alert.notify_email else None
            user_phone = alert.phone_number if alert.notify_sms else None
            
            if alert.tracking_type == "container":
                tracking_data = await _track_container_internal(alert.reference)
                
                # Check for arrival alert
                if alert.alert_type == AlertType.ARRIVAL.value and tracking_data.eta:
                    try:
                        eta_date = datetime.fromisoformat(tracking_data.eta.replace("Z", "+00:00"))
                        now = datetime.now(eta_date.tzinfo)
                        hours_until_arrival = (eta_date - now).total_seconds() / 3600
                        
                        # Alert if within 24 hours
                        if 0 <= hours_until_arrival <= 24:
                            await notification_service.send_container_arrival_alert(
                                container_number=tracking_data.container_number,
                                vessel=tracking_data.vessel.name if tracking_data.vessel else "Unknown",
                                port=tracking_data.destination.name,
                                eta=tracking_data.eta,
                                user_email=user_email,
                                user_phone=user_phone,
                                user_name=user.email.split("@")[0] if user.email else "User",
                            )
                            
                            # Update alert
                            alert.last_triggered = datetime.utcnow()
                            alert.trigger_count += 1
                            
                            # Log notification
                            notification = TrackingNotificationModel(
                                id=uuid.uuid4(),
                                alert_id=alert.id,
                                user_id=user.id,
                                notification_type="email" if user_email else "sms",
                                recipient=user_email or user_phone or "unknown",
                                subject=f"Arrival Alert: {tracking_data.container_number}",
                                trigger_reason=f"ETA within {int(hours_until_arrival)} hours",
                                shipment_reference=alert.reference,
                                shipment_status=tracking_data.status,
                                status=NotificationStatus.SENT.value,
                                sent_at=datetime.utcnow(),
                            )
                            db.add(notification)
                            
                            logger.info(f"Sent arrival alert for container {alert.reference}")
                    except Exception as e:
                        logger.error(f"Error processing arrival alert: {e}")
                
                # Check for delay alert
                elif alert.alert_type == AlertType.DELAY.value:
                    if tracking_data.status == "delayed":
                        await notification_service.send_delay_alert(
                            container_number=tracking_data.container_number,
                            current_eta=tracking_data.eta,
                            delay_hours=alert.threshold_hours or 0,
                            user_email=user_email,
                            user_phone=user_phone,
                            user_name=user.email.split("@")[0] if user.email else "User",
                        )
                        alert.last_triggered = datetime.utcnow()
                        alert.trigger_count += 1
                        logger.info(f"Sent delay alert for container {alert.reference}")
            
            elif alert.tracking_type == "vessel":
                search_type = "imo" if alert.reference.startswith("IMO") else \
                             "mmsi" if alert.reference.isdigit() and len(alert.reference) == 9 else "name"
                tracking_data = await _track_vessel_internal(alert.reference, search_type)
                
                if alert.alert_type == AlertType.ARRIVAL.value and tracking_data.eta:
                    try:
                        eta_date = datetime.fromisoformat(tracking_data.eta.replace("Z", "+00:00"))
                        now = datetime.now(eta_date.tzinfo)
                        hours_until_arrival = (eta_date - now).total_seconds() / 3600
                        
                        if 0 <= hours_until_arrival <= 24:
                            await notification_service.send_container_arrival_alert(
                                container_number=tracking_data.name,
                                vessel=tracking_data.name,
                                port=tracking_data.destination or "Unknown",
                                eta=tracking_data.eta,
                                user_email=user_email,
                                user_phone=user_phone,
                                user_name=user.email.split("@")[0] if user.email else "User",
                            )
                            alert.last_triggered = datetime.utcnow()
                            alert.trigger_count += 1
                            logger.info(f"Sent arrival alert for vessel {alert.reference}")
                    except Exception as e:
                        logger.error(f"Error processing vessel arrival alert: {e}")
        
        except Exception as e:
            logger.error(f"Error processing alert {alert.id}: {e}")
    
    db.commit()


# ============== Admin/Health Endpoints ==============

@router.post("/alerts/check")
async def trigger_alert_check(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Manually trigger alert checking (admin endpoint)."""
    if not hasattr(current_user, 'role') or current_user.role not in ["system_admin", "admin"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    background_tasks.add_task(check_and_send_alerts, db)
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
    
    try:
        notification_status = notification_service.status()
    except:
        notification_status = {"email": False, "sms": False}
    
    # Get scheduler status
    try:
        from app.scheduler import get_scheduler_status
        scheduler_status = get_scheduler_status()
    except:
        scheduler_status = {"running": False, "jobs": []}
    
    return {
        "status": "healthy",
        "data_sources": sources,
        "notifications": notification_status,
        "scheduler": scheduler_status,
        "fallback": "mock",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
