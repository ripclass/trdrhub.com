# 🚢 Container Tracker - Implementation Plan

> **Created:** December 5, 2024  
> **Total Effort:** 4-5 weeks  
> **Goal:** Transform demo into bank-grade, production-ready tracking solution

---

## Phase 1: Make It Real (Week 1)
**Goal:** Turn demo into functional MVP with real data and persistence

---

### Task 1.1: Database Models
**Priority:** 🔴 CRITICAL  
**Effort:** 1 day  
**Owner:** Senior Developer

#### Create New Models

**File:** `apps/api/app/models/tracking.py`

```python
# Models to create:

class TrackedShipment(Base):
    """User's shipment portfolio"""
    __tablename__ = "tracked_shipments"
    
    id = Column(UUID, primary_key=True)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    company_id = Column(UUID, ForeignKey("companies.id"))
    
    # Shipment info
    reference = Column(String(50), nullable=False)  # Container/Vessel number
    tracking_type = Column(String(20))  # "container" or "vessel"
    carrier = Column(String(100))
    carrier_code = Column(String(10))
    
    # Route
    origin_port = Column(String(100))
    origin_code = Column(String(10))
    destination_port = Column(String(100))
    destination_code = Column(String(10))
    
    # Status
    status = Column(String(50))
    eta = Column(DateTime)
    eta_confidence = Column(Integer)
    current_location = Column(String(200))
    progress = Column(Integer, default=0)
    
    # Vessel info
    vessel_name = Column(String(200))
    vessel_imo = Column(String(20))
    voyage = Column(String(50))
    
    # LC linkage
    lc_number = Column(String(100))
    lc_expiry = Column(DateTime)
    
    # Metadata
    nickname = Column(String(100))  # User-friendly name
    notes = Column(Text)
    is_active = Column(Boolean, default=True)
    last_checked = Column(DateTime)
    data_source = Column(String(50))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)


class TrackingAlert(Base):
    """Alert configurations"""
    __tablename__ = "tracking_alerts"
    
    id = Column(UUID, primary_key=True)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    shipment_id = Column(UUID, ForeignKey("tracked_shipments.id"))
    
    # Alert config
    reference = Column(String(50), nullable=False)
    tracking_type = Column(String(20))
    alert_type = Column(String(50))  # arrival, departure, delay, eta_change
    threshold_hours = Column(Integer)  # For delay alerts
    
    # Notification preferences
    notify_email = Column(Boolean, default=True)
    notify_sms = Column(Boolean, default=False)
    phone_number = Column(String(20))
    
    # Status
    is_active = Column(Boolean, default=True)
    last_triggered = Column(DateTime)
    trigger_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class TrackingEvent(Base):
    """Historical tracking events"""
    __tablename__ = "tracking_events"
    
    id = Column(UUID, primary_key=True)
    shipment_id = Column(UUID, ForeignKey("tracked_shipments.id"), nullable=False)
    
    # Event data
    event_type = Column(String(100))
    event_time = Column(DateTime)
    location = Column(String(200))
    description = Column(Text)
    
    # Position (optional)
    latitude = Column(Float)
    longitude = Column(Float)
    
    # Source
    data_source = Column(String(50))
    raw_data = Column(JSON)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class TrackingNotification(Base):
    """Sent notification log"""
    __tablename__ = "tracking_notifications"
    
    id = Column(UUID, primary_key=True)
    alert_id = Column(UUID, ForeignKey("tracking_alerts.id"), nullable=False)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    
    # Notification details
    notification_type = Column(String(20))  # email, sms
    recipient = Column(String(200))
    subject = Column(String(500))
    body = Column(Text)
    
    # Status
    status = Column(String(20))  # pending, sent, failed
    sent_at = Column(DateTime)
    error_message = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
```

#### Deliverables:
- [ ] Create `apps/api/app/models/tracking.py`
- [ ] Add to `apps/api/app/models/__init__.py`
- [ ] Create Alembic migration

---

### Task 1.2: Database Migration
**Priority:** 🔴 CRITICAL  
**Effort:** 0.5 day  
**Owner:** Senior Developer

#### Create Migration

```bash
cd apps/api
alembic revision --autogenerate -m "add_tracking_tables"
alembic upgrade head
```

#### Deliverables:
- [ ] Migration file created
- [ ] Migration tested locally
- [ ] Migration applied to production

---

### Task 1.3: Refactor Alerts to Database
**Priority:** 🔴 CRITICAL  
**Effort:** 1 day  
**Owner:** Senior Developer

#### Modify File: `apps/api/app/routers/tracking.py`

**Changes:**
1. Remove `_alerts_store: Dict` (in-memory storage)
2. Add database session dependency
3. Create CRUD functions for alerts
4. Update all alert endpoints

```python
# Replace this:
_alerts_store: Dict[str, TrackingAlert] = {}

# With database operations:
from app.models.tracking import TrackingAlert as TrackingAlertModel

@router.post("/alerts")
async def create_alert(
    request: CreateAlertRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    alert = TrackingAlertModel(
        id=uuid.uuid4(),
        user_id=current_user.id,
        reference=request.reference.upper(),
        tracking_type=request.tracking_type,
        alert_type=request.alert_type,
        # ... other fields
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert
```

#### Deliverables:
- [ ] Remove in-memory store
- [ ] Implement `create_alert` with DB
- [ ] Implement `list_alerts` with DB
- [ ] Implement `delete_alert` with DB
- [ ] Implement `toggle_alert` with DB
- [ ] Test all CRUD operations

---

### Task 1.4: Portfolio Persistence
**Priority:** 🔴 CRITICAL  
**Effort:** 1 day  
**Owner:** Senior Developer

#### Add New Endpoints

```python
# Add to apps/api/app/routers/tracking.py

@router.post("/portfolio/add")
async def add_to_portfolio(
    reference: str,
    tracking_type: str = "container",
    nickname: str = None,
    lc_number: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a shipment to user's portfolio"""
    # Track the shipment first to get current data
    if tracking_type == "container":
        tracking_data = await _track_container_internal(reference)
    else:
        tracking_data = await _track_vessel_internal(reference)
    
    # Create portfolio entry
    shipment = TrackedShipment(
        id=uuid.uuid4(),
        user_id=current_user.id,
        reference=reference.upper(),
        tracking_type=tracking_type,
        nickname=nickname,
        lc_number=lc_number,
        # ... populate from tracking_data
    )
    db.add(shipment)
    db.commit()
    return shipment


@router.delete("/portfolio/{shipment_id}")
async def remove_from_portfolio(shipment_id: str, ...):
    """Remove shipment from portfolio"""


@router.get("/portfolio")
async def get_portfolio(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get user's shipment portfolio"""
    shipments = db.query(TrackedShipment).filter(
        TrackedShipment.user_id == current_user.id,
        TrackedShipment.is_active == True
    ).all()
    
    # Optionally refresh tracking data for each
    return {
        "total": len(shipments),
        "shipments": shipments,
        "stats": calculate_portfolio_stats(shipments)
    }
```

#### Deliverables:
- [ ] `POST /portfolio/add` endpoint
- [ ] `DELETE /portfolio/{id}` endpoint
- [ ] `GET /portfolio` returns real data
- [ ] Frontend: Add "Save to Portfolio" button
- [ ] Frontend: Remove from portfolio

---

### Task 1.5: Configure Real API
**Priority:** 🔴 CRITICAL  
**Effort:** 0.5 day  
**Owner:** DevOps / Senior Developer

#### Action Items:

1. **Register for Searates API**
   - URL: https://www.searates.com/services/tracking-api/
   - Cost: Free tier (100 requests) or $29/mo (1000 requests)
   
2. **Add Environment Variables**
   ```bash
   # Render environment
   SEARATES_API_KEY=your_key_here
   
   # Optional additional providers
   DATALASTIC_API_KEY=your_key_here  # Free AIS data
   ```

3. **Test with Real Container**
   ```bash
   curl https://trdrhub-api.onrender.com/tracking/container/MSCU1234567
   # Should return data_source: "searates" instead of "mock"
   ```

#### Deliverables:
- [ ] Searates account created
- [ ] API key configured in Render
- [ ] Real tracking verified with test container

---

### Task 1.6: Background Alert Processing
**Priority:** 🔴 CRITICAL  
**Effort:** 1 day  
**Owner:** Senior Developer

#### Option A: Simple Scheduler (Recommended for MVP)

**File:** `apps/api/app/scheduler.py`

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.routers.tracking import check_and_send_alerts

scheduler = AsyncIOScheduler()

def start_scheduler():
    # Check alerts every 15 minutes
    scheduler.add_job(
        check_and_send_alerts,
        'interval',
        minutes=15,
        id='tracking_alerts_checker'
    )
    scheduler.start()
```

**Modify:** `apps/api/main.py`

```python
from app.scheduler import start_scheduler

@app.on_event("startup")
async def startup():
    start_scheduler()
```

**Add dependency:** `requirements.txt`
```
apscheduler==3.10.4
```

#### Deliverables:
- [ ] Install APScheduler
- [ ] Create scheduler module
- [ ] Wire up to FastAPI startup
- [ ] Test alert checking runs every 15 min
- [ ] Verify on Render logs

---

### Task 1.7: Email Notifications
**Priority:** 🔴 CRITICAL  
**Effort:** 1 day  
**Owner:** Senior Developer

#### Verify Resend Configuration

**Check:** `apps/api/app/services/notifications.py`

```python
# Ensure this is properly configured
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
```

#### Create Tracking Email Templates

**File:** `apps/api/app/templates/emails/tracking_arrival.html`

```html
<!DOCTYPE html>
<html>
<head>
    <title>Shipment Arrival Alert</title>
</head>
<body>
    <h1>🚢 Arrival Alert</h1>
    <p>Your shipment <strong>{{ container_number }}</strong> is arriving soon!</p>
    
    <table>
        <tr><td>Vessel:</td><td>{{ vessel_name }}</td></tr>
        <tr><td>ETA:</td><td>{{ eta }}</td></tr>
        <tr><td>Destination:</td><td>{{ destination }}</td></tr>
    </table>
    
    <p><a href="https://trdrhub.com/tracking/dashboard/container/{{ container_number }}">
        View Tracking Details
    </a></p>
</body>
</html>
```

#### Implement Send Function

```python
# In apps/api/app/services/notifications.py

async def send_tracking_alert_email(
    to_email: str,
    alert_type: str,
    shipment_data: dict
):
    """Send tracking alert email via Resend"""
    
    template = load_template(f"tracking_{alert_type}.html")
    html = template.render(**shipment_data)
    
    await resend.Emails.send({
        "from": "alerts@trdrhub.com",
        "to": to_email,
        "subject": f"🚢 {alert_type.title()} Alert: {shipment_data['reference']}",
        "html": html
    })
```

#### Deliverables:
- [ ] Verify RESEND_API_KEY configured
- [ ] Create arrival email template
- [ ] Create delay email template
- [ ] Create ETA change email template
- [ ] Test email sending
- [ ] Verify emails delivered (check spam)

---

## Phase 1 Completion Checklist

| Task | Status | Owner | ETA |
|------|--------|-------|-----|
| 1.1 Database Models | ⬜ | Dev | Day 1 |
| 1.2 Migration | ⬜ | Dev | Day 1 |
| 1.3 Refactor Alerts | ⬜ | Dev | Day 2 |
| 1.4 Portfolio Persistence | ⬜ | Dev | Day 3 |
| 1.5 Real API Config | ⬜ | DevOps | Day 3 |
| 1.6 Background Jobs | ⬜ | Dev | Day 4 |
| 1.7 Email Notifications | ⬜ | Dev | Day 5 |

**Phase 1 Done When:**
- ✅ Tracking returns real data (not mock)
- ✅ Alerts persist across server restarts
- ✅ Users can save shipments to portfolio
- ✅ Email notifications actually send
- ✅ Background job runs every 15 minutes

---

## Phase 2: Production Polish (Week 2)
**Goal:** Professional features and reliability

---

### Task 2.1: Map Visualization
**Effort:** 2-3 days

#### Frontend Changes

**Install:**
```bash
cd apps/web
npm install react-map-gl mapbox-gl
```

**Create Component:** `apps/web/src/components/tracking/TrackingMap.tsx`

```tsx
import Map, { Marker, Source, Layer } from 'react-map-gl';
import 'mapbox-gl/dist/mapbox-gl.css';

export function TrackingMap({ shipments, selectedShipment }) {
  return (
    <Map
      mapboxAccessToken={import.meta.env.VITE_MAPBOX_TOKEN}
      initialViewState={{
        longitude: 0,
        latitude: 20,
        zoom: 1.5
      }}
      style={{ width: '100%', height: 400 }}
      mapStyle="mapbox://styles/mapbox/dark-v11"
    >
      {shipments.map(ship => (
        <Marker
          key={ship.id}
          longitude={ship.position?.lon}
          latitude={ship.position?.lat}
        >
          <ShipIcon status={ship.status} />
        </Marker>
      ))}
    </Map>
  );
}
```

#### Deliverables:
- [ ] Mapbox account + token
- [ ] Map component created
- [ ] Vessel markers displayed
- [ ] Route lines shown
- [ ] Port markers added

---

### Task 2.2: LC Integration
**Effort:** 2 days

#### Backend: Link Shipments to LCs

```python
# Add to TrackedShipment model
lc_number = Column(String(100))
lc_expiry = Column(DateTime)
lc_id = Column(UUID, ForeignKey("lc_validations.id"))

# Add alert type
"lc_risk"  # When shipment ETA approaches LC expiry
```

#### Frontend: LC Expiry Warning

```tsx
// In ContainerTrackPage.tsx
{shipment.lc_expiry && (
  <LCExpiryWarning 
    eta={shipment.eta}
    lcExpiry={shipment.lc_expiry}
  />
)}
```

#### Deliverables:
- [ ] Add LC fields to shipment model
- [ ] LC expiry warning component
- [ ] Auto-populate from LCopilot
- [ ] LC risk alert type

---

### Task 2.3: Usage Tracking
**Effort:** 1 day

#### Backend: Log API Usage

```python
# Add to each tracking endpoint
await log_usage(
    user_id=current_user.id,
    tool="container_tracker",
    action="track_container",
    reference=container_number
)
```

#### Enforce Limits

```python
# Check user's plan limits
usage_count = await get_monthly_usage(current_user.id, "container_tracker")
plan_limit = get_plan_limit(current_user.plan, "tracking_calls")

if usage_count >= plan_limit:
    raise HTTPException(402, "Tracking limit reached. Upgrade plan.")
```

#### Deliverables:
- [ ] Usage logging implemented
- [ ] Plan limits enforced
- [ ] Usage displayed in Hub

---

### Task 2.4: Bulk Import
**Effort:** 1 day

#### Backend Endpoint

```python
@router.post("/portfolio/import")
async def bulk_import(
    file: UploadFile,
    current_user: User = Depends(get_current_user),
):
    """Import multiple shipments from CSV"""
    # Parse CSV: container_number, nickname, lc_number
    # Add each to portfolio
```

#### Frontend: CSV Upload

```tsx
<Button onClick={() => /* upload CSV */}>
  <Upload className="w-4 h-4 mr-2" />
  Import from CSV
</Button>
```

#### Deliverables:
- [ ] CSV upload endpoint
- [ ] Template CSV download
- [ ] Frontend upload UI
- [ ] Error handling for bad data

---

## Phase 2 Completion Checklist

| Task | Status | Owner | ETA |
|------|--------|-------|-----|
| 2.1 Map Visualization | ⬜ | Frontend | Day 1-2 |
| 2.2 LC Integration | ⬜ | Full-stack | Day 3-4 |
| 2.3 Usage Tracking | ⬜ | Backend | Day 5 |
| 2.4 Bulk Import | ⬜ | Full-stack | Day 5 |

---

## Phase 3: Bank Features (Week 3-5)
**Goal:** B2B ready with compliance features

---

### Task 3.1: Vessel Sanctions Screening
**Effort:** 1 week

#### Data Sources
- OFAC SDN List (free, updated daily)
- EU Consolidated Sanctions (free)
- UN Sanctions List (free)

#### Implementation

```python
# New service: apps/api/app/services/vessel_sanctions.py

class VesselSanctionsService:
    async def screen_vessel(self, imo: str, vessel_name: str) -> SanctionsResult:
        results = {
            "ofac": await self.check_ofac(imo, vessel_name),
            "eu": await self.check_eu_sanctions(imo),
            "un": await self.check_un_sanctions(imo),
            "flag_risk": self.assess_flag_risk(flag_state),
        }
        return SanctionsResult(**results)
```

#### Deliverables:
- [ ] OFAC SDN integration
- [ ] EU sanctions check
- [ ] UN sanctions check
- [ ] Flag state risk scoring
- [ ] Sanctions result in UI
- [ ] PDF compliance report

---

### Task 3.2: AIS Gap Detection
**Effort:** 4-5 days

#### Implementation

```python
# Track AIS history and detect gaps
class AISGapDetector:
    async def analyze_vessel_history(self, imo: str, days: int = 90):
        # Fetch historical AIS positions
        positions = await fetch_ais_history(imo, days)
        
        # Find gaps > 24 hours
        gaps = []
        for i in range(1, len(positions)):
            time_diff = positions[i].timestamp - positions[i-1].timestamp
            if time_diff.total_seconds() > 24 * 3600:
                gaps.append({
                    "start": positions[i-1].timestamp,
                    "end": positions[i].timestamp,
                    "duration_hours": time_diff.total_seconds() / 3600,
                    "last_known_position": positions[i-1].position
                })
        
        return AISAnalysis(gaps=gaps, risk_score=calculate_risk(gaps))
```

#### Deliverables:
- [ ] AIS history fetching
- [ ] Gap detection algorithm
- [ ] Risk scoring
- [ ] UI display of gaps
- [ ] Alerts for suspicious gaps

---

### Task 3.3: Compliance Reports
**Effort:** 3-4 days

#### PDF Report Contents

```
VESSEL DUE DILIGENCE REPORT
===========================
Vessel: MSC OSCAR (IMO: 9703318)
Report Date: December 5, 2024
Report ID: VDD-2024-001234

SANCTIONS SCREENING
- OFAC SDN: ✅ CLEAR
- EU Sanctions: ✅ CLEAR  
- UN Sanctions: ✅ CLEAR

FLAG STATE ASSESSMENT
- Flag: Panama 🇵🇦
- Risk Level: LOW
- Paris MoU Status: White List

AIS ANALYSIS (90 Days)
- Total Gaps Detected: 0
- Suspicious Patterns: None

PORT CALL HISTORY
- Last 10 Ports: [list]
- Sanctioned Port Calls: None

OWNERSHIP
- Registered Owner: [name]
- Beneficial Owner: [name]
- Risk Assessment: LOW

CONCLUSION
This vessel presents LOW risk for trade finance purposes.

[Digital Signature]
```

#### Deliverables:
- [ ] PDF generation (ReportLab/WeasyPrint)
- [ ] Report template
- [ ] Download endpoint
- [ ] Audit trail logging

---

## Phase 3 Completion Checklist

| Task | Status | Owner | ETA |
|------|--------|-------|-----|
| 3.1 Vessel Sanctions | ⬜ | Backend | Week 3 |
| 3.2 AIS Gap Detection | ⬜ | Backend | Week 4 |
| 3.3 Compliance Reports | ⬜ | Full-stack | Week 4-5 |

---

## Environment Variables Required

```bash
# Tracking APIs (Phase 1)
SEARATES_API_KEY=           # $29/mo - Container tracking
DATALASTIC_API_KEY=         # Free tier - AIS data

# Notifications (Phase 1)
RESEND_API_KEY=             # Already configured?
TWILIO_ACCOUNT_SID=         # For SMS
TWILIO_AUTH_TOKEN=
TWILIO_PHONE_NUMBER=

# Map (Phase 2)
VITE_MAPBOX_TOKEN=          # Free tier available

# Sanctions (Phase 3)
# No API keys - public data sources
```

---

## Success Criteria

### Phase 1 Complete When:
- [ ] Search returns real tracking data
- [ ] Alerts persist in database
- [ ] Portfolio saves across sessions
- [ ] Email notifications send successfully
- [ ] Background jobs run on schedule

### Phase 2 Complete When:
- [ ] Map shows vessel positions
- [ ] LCs linked to shipments
- [ ] Usage tracked and limited
- [ ] Bulk import works

### Phase 3 Complete When:
- [ ] Vessel sanctions screening works
- [ ] AIS gaps detected and flagged
- [ ] PDF compliance reports downloadable
- [ ] Bank demo-ready

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Searates API unreliable | Add Portcast as fallback |
| Email delivery issues | Use verified domain, monitor bounce rates |
| Map costs escalate | Implement caching, limit refreshes |
| Sanctions data outdated | Daily refresh from official sources |

---

*This plan is ready for sprint planning. Break into tickets as needed.*

