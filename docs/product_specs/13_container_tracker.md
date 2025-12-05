# 🚢 Container & Vessel Tracker - Product Spec

## Overview
**Product Name:** TRDR Shipment Tracker  
**Tagline:** "Track your cargo across the world"  
**Priority:** ⭐ HIGH (Direct bank request!)  
**Estimated Dev Time:** 3-4 weeks  

---

## Problem Statement
Traders struggle to track shipments:
- Multiple carriers, multiple portals
- Manual status checks
- No proactive alerts
- Delay visibility comes too late
- Customers ask "where's my order?"

## Solution
A unified tracking dashboard:
- Multi-carrier tracking
- Real-time vessel positions
- ETA predictions
- Delay alerts
- Share tracking with customers

---

## User Interface

### Dashboard
```
┌───────────────────────────────────────────────────────────┐
│  🚢 SHIPMENT TRACKER                                      │
│                                                           │
│  Active Shipments: 12  |  In Transit: 8  |  Delayed: 2   │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │                   🌍 WORLD MAP                       │ │
│  │                                                     │ │
│  │     🚢 MAERSK INFINITY                              │ │
│  │         ↘                                          │ │
│  │           🚢 MSC ANNA        🚢 EVER GOLDEN        │ │
│  │              ↓                    ↗               │ │
│  │  [Bangladesh]        [Singapore]      [China]     │ │
│  │                                                     │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  📦 SHIPMENTS                          [+ Track New]     │
│  ┌─────────────────────────────────────────────────────┐ │
│  │Container      │Vessel        │Route     │ETA    │St │ │
│  ├───────────────┼──────────────┼──────────┼───────┼───┤ │
│  │MSKU7788990   │MAERSK INFINITY│CTG→SHA   │Dec 18│🟢 │ │
│  │OOLU1234567   │MSC ANNA      │SHA→SIN   │Dec 20│🟢 │ │
│  │CMAU9876543   │EVER GOLDEN   │SIN→FEL   │Dec 25│🟡 │ │
│  │TRIU5551234   │CMA CGM MARCO │CTG→RTM   │Dec 28│🔴 │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  🔴 = Delayed  🟡 = Minor delay  🟢 = On time            │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

### Shipment Detail
```
┌───────────────────────────────────────────────────────────┐
│  🚢 SHIPMENT DETAIL                                       │
│                                                           │
│  Container: MSKU7788990                                   │
│  B/L Number: MSKU7788990123                              │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ 🌊 CURRENT STATUS                                   │ │
│  │                                                     │ │
│  │ Status: AT SEA                                      │ │
│  │ Vessel: MAERSK INFINITY                            │ │
│  │ Position: 15.2°N, 93.5°E (Bay of Bengal)           │ │
│  │ Speed: 18.5 knots                                  │ │
│  │ Last Update: 5 minutes ago                         │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  📍 JOURNEY                                              │
│  ┌─────────────────────────────────────────────────────┐ │
│  │                                                     │ │
│  │  ● Chittagong, BD        Loaded: 10 Dec 2024      │ │
│  │  │                       Departed: 11 Dec 2024    │ │
│  │  │                                                 │ │
│  │  │  ~~~~~ At Sea ~~~~~                            │ │
│  │  │  Current Position 🚢                           │ │
│  │  │  Distance: 1,234 nm remaining                  │ │
│  │  │                                                 │ │
│  │  │                                                 │ │
│  │  ○ Singapore (Transship) ETA: 15 Dec 2024        │ │
│  │  │                                                 │ │
│  │  │                                                 │ │
│  │  ○ Shanghai, CN          ETA: 18 Dec 2024        │ │
│  │                           Original: 18 Dec 2024  │ │
│  │                           Status: ON TIME ✅      │ │
│  │                                                     │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  📋 SHIPMENT DETAILS                                     │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ Shipper:     Dhaka Knitwear Ltd                    │ │
│  │ Consignee:   Shanghai Fashion Co                   │ │
│  │ Goods:       Cotton Garments                       │ │
│  │ Weight:      20,400 kg                             │ │
│  │ LC Number:   EXP2024112900001                     │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  [🔗 Share Tracking]  [🔔 Set Alerts]  [📄 Documents]    │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

### Delay Alert
```
┌───────────────────────────────────────────────────────────┐
│  🔔 DELAY ALERT                                           │
│                                                           │
│  Container: TRIU5551234                                   │
│  Status: DELAYED                                          │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ ⚠️ SIGNIFICANT DELAY DETECTED                       │ │
│  │                                                     │ │
│  │ Original ETA: 25 Dec 2024                          │ │
│  │ New ETA:      28 Dec 2024                          │ │
│  │ Delay:        3 days                               │ │
│  │                                                     │ │
│  │ Reason: Port congestion at Rotterdam               │ │
│  │         (Source: PortCall data)                    │ │
│  │                                                     │ │
│  │ Impact Assessment:                                 │ │
│  │ • LC Expiry: 30 Dec 2024                          │ │
│  │ • Buffer: 2 days (TIGHT ⚠️)                       │ │
│  │ • Presentation deadline at risk                   │ │
│  │                                                     │ │
│  │ Recommended Actions:                               │ │
│  │ 1. Contact shipping line for priority unloading   │ │
│  │ 2. Prepare LC amendment request (if needed)       │ │
│  │ 3. Notify buyer of potential delay                │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  [📧 Notify Buyer]  [📝 Draft Amendment]  [✓ Acknowledge]│
│                                                           │
└───────────────────────────────────────────────────────────┘
```

---

## Data Sources

### Carrier APIs
| Carrier | API Type | Coverage |
|---------|----------|----------|
| Maersk | REST API | 🟢 Full |
| MSC | REST API | 🟢 Full |
| CMA CGM | REST API | 🟢 Full |
| COSCO | REST API | 🟡 Partial |
| Hapag-Lloyd | REST API | 🟢 Full |
| ONE | REST API | 🟢 Full |
| Evergreen | Web scrape | 🟡 Basic |
| Yang Ming | Web scrape | 🟡 Basic |

### AIS Data (Vessel Positions)
- MarineTraffic API
- VesselFinder API
- Spire Maritime

### Port Data
- Port community systems
- Terminal operating systems
- Congestion indices

---

## Technical Architecture

```typescript
interface Shipment {
  id: string;
  containers: Container[];
  blNumber: string;
  
  // Route
  origin: Port;
  destination: Port;
  transshipments: Port[];
  
  // Parties
  shipper: Party;
  consignee: Party;
  carrier: Carrier;
  
  // Status
  currentStatus: ShipmentStatus;
  currentPosition?: GeoPosition;
  vessel?: Vessel;
  
  // Timing
  etd: Date;
  eta: Date;
  originalEta: Date;
  actualArrival?: Date;
  
  // LC Link
  lcNumber?: string;
  lcExpiry?: Date;
}

interface ShipmentStatus {
  code: "booked" | "loaded" | "departed" | "at_sea" | 
        "arrived" | "discharged" | "delivered";
  timestamp: Date;
  location: Port;
  remarks?: string;
}
```

---

## Pricing Model

| Tier | Containers/Month | Price | Features |
|------|-----------------|-------|----------|
| Free | 5 | $0 | Basic tracking |
| Starter | 25 | $29/mo | + Alerts, history |
| Professional | 100 | $79/mo | + ETA predictions, sharing |
| Business | 500 | $199/mo | + API, multi-user |
| Enterprise | Unlimited | Custom | + All carriers, integrations |

---

## Integration Points

### With LCopilot
```
LCopilot → Shipment Tracker:
1. LC has shipment deadline
2. User adds B/L number in LCopilot
3. Auto-create tracking
4. Alert if shipment delay risks LC validity
```

### With CustomsMate
```
Shipment Tracker → CustomsMate:
1. Shipment approaching destination
2. Alert: "Prepare customs declaration"
3. Pre-fill declaration with shipment data
```

---

## MVP Features (Week 1-2) ✅ COMPLETED

- [x] Container number tracking
- [x] Multi-carrier support (mock data with API fallback)
- [x] Basic status display
- [x] Manual tracking add
- [x] Dashboard with sidebar navigation
- [x] Search by container/vessel/B/L

## V2 Features (Week 3-4) 🔄 IN PROGRESS

- [x] Vessel tracking (IMO/MMSI/Name)
- [x] ETA display
- [x] Email/SMS alert creation
- [ ] Real carrier API integration (Searates, Portcast)
- [ ] Live vessel position map
- [ ] Shareable tracking links

## V3 Features (Future) 📅 PLANNED

- [ ] AI delay prediction
- [ ] Port congestion data
- [ ] Bulk tracking upload
- [ ] API for ERP integration
- [ ] Historical analytics
- [ ] Vessel sanctions screening (for banks)

---

## Competitive Landscape

| Competitor | Price | Carriers | Real-time | Alerts |
|------------|-------|----------|-----------|--------|
| Project44 | $$$$ | Many | ✅ | ✅ |
| FourKites | $$$$ | Many | ✅ | ✅ |
| Searates | Free-$$ | Basic | ⚠️ | ⚠️ |
| Freightos | Free | Many | ⚠️ | ⚠️ |
| **TRDR Tracker** | $-$$ | Many | ✅ | ✅ |

**Differentiation:** LC integration + Trade finance context

---

## 🏦 BANK-SPECIFIC FEATURES (Added based on bank feedback)

Banks need more than just tracking - they need **compliance visibility**:

### Vessel Risk Screening
```
┌───────────────────────────────────────────────────────────────┐
│  🚢 VESSEL COMPLIANCE CHECK                                   │
│                                                               │
│  Vessel: MAERSK INFINITY                                      │
│  IMO: 9778791                                                 │
│                                                               │
│  ✅ SANCTIONS STATUS                                          │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ OFAC SDN List:        ✅ CLEAR                          │ │
│  │ EU Sanctions:         ✅ CLEAR                          │ │
│  │ UN Sanctions:         ✅ CLEAR                          │ │
│  │ UK OFSI:              ✅ CLEAR                          │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  📋 VESSEL DETAILS                                           │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ Flag State:           🇩🇰 Denmark ✅ (Low risk)         │ │
│  │ Owner:                A.P. Moller-Maersk ✅             │ │
│  │ Operator:             Maersk Line ✅                    │ │
│  │ Built:                2019                              │ │
│  │ Classification:       Lloyd's Register                  │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  🌍 PORT CALL HISTORY (Last 12 months)                       │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ ✅ No calls to sanctioned ports                         │ │
│  │ ✅ No AIS gaps detected (>48 hours)                     │ │
│  │                                                         │ │
│  │ Recent Ports: Shanghai, Singapore, Rotterdam, Chittagong│ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  [ 📄 Download Compliance Report ]                           │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

### Bank Alert: Vessel Risk Detected
```
┌───────────────────────────────────────────────────────────────┐
│  🚨 VESSEL RISK ALERT                                         │
│                                                               │
│  Vessel: GLORY STAR                                           │
│  IMO: 9234567                                                 │
│  Container: TRIU5551234 (LC# IMP-2024-0089)                  │
│                                                               │
│  ⚠️ RISK INDICATORS DETECTED                                 │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                                                         │ │
│  │  ❌ FLAG STATE: 🇨🇲 Cameroon (High-risk registry)       │ │
│  │                                                         │ │
│  │  ⚠️ AIS GAP: 72 hours dark period detected            │ │
│  │     Location: Persian Gulf (Oct 15-18, 2024)          │ │
│  │                                                         │ │
│  │  ⚠️ PORT CALL: Bandar Abbas, Iran (Sep 2024)          │ │
│  │     Note: Iranian port - sanctions risk                │ │
│  │                                                         │ │
│  │  ⚠️ OWNERSHIP: Complex ownership structure             │ │
│  │     Ultimate beneficial owner unclear                  │ │
│  │                                                         │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  📋 RECOMMENDED ACTIONS FOR BANK                             │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ 1. Request alternative vessel from shipper             │ │
│  │ 2. Conduct enhanced due diligence on shipment          │ │
│  │ 3. Document risk assessment if proceeding              │ │
│  │ 4. Consider rejecting documents if high risk           │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  [ 🚨 Escalate to Compliance ]  [ 📄 Risk Report ]          │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

### Bank Dashboard View
```
┌───────────────────────────────────────────────────────────────┐
│  🏦 BANK TRADE FINANCE MONITORING                             │
│                                                               │
│  Active LCs with Shipments: 45                               │
│  Vessels Monitored: 38                                        │
│  Risk Alerts: 3                                              │
│                                                               │
│  📊 SHIPMENT STATUS BY LC                                    │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ LC Number    │Beneficiary    │Vessel      │Status │Risk │ │
│  ├──────────────┼───────────────┼────────────┼───────┼─────┤ │
│  │IMP-2024-0087│Dhaka Textiles │MAERSK INF. │At Sea │🟢   │ │
│  │IMP-2024-0088│BD Garments    │MSC ANNA    │Loaded │🟢   │ │
│  │IMP-2024-0089│XYZ Trading    │GLORY STAR  │At Sea │🔴   │ │
│  │IMP-2024-0090│Cotton Mills   │EVER GOLDEN │ETA 2d │🟡   │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  ⏰ LC EXPIRY WARNINGS                                       │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ ⚠️ IMP-2024-0090: ETA Dec 25, LC expires Dec 27        │ │
│  │    Buffer: 2 days - MONITOR CLOSELY                    │ │
│  │                                                         │ │
│  │ ⚠️ IMP-2024-0092: ETA Jan 2, LC expires Jan 3         │ │
│  │    Buffer: 1 day - HIGH RISK OF LATE PRESENTATION     │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  [ Export Report ]  [ Configure Alerts ]  [ Add LC ]         │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

### Key Bank Features
| Feature | Why Banks Need It |
|---------|-------------------|
| **Vessel Sanctions Check** | OFAC/EU compliance on vessels carrying LC goods |
| **Flag State Risk** | Flags of convenience indicate higher risk |
| **AIS Gap Detection** | Dark periods = potential sanctions evasion |
| **Port Call History** | Detect calls to sanctioned ports |
| **Ownership Screening** | Identify sanctioned beneficial owners |
| **LC Expiry Alerts** | Prevent late document presentation |
| **Compliance Reports** | Audit trail for regulators |

### Data Sources for Bank Features
| Data | Source | Update Frequency |
|------|--------|------------------|
| Vessel Sanctions | OFAC, EU, UN lists | Daily |
| AIS Positions | MarineTraffic, Spire | Real-time |
| Port Calls | AIS history | Daily |
| Flag State Risk | Industry databases | Monthly |
| Ownership | Equasis, Lloyd's | Weekly |

---

## Success Metrics

| Metric | Target (Month 3) |
|--------|------------------|
| Containers tracked | 2,000 |
| Active users | 500 |
| Delay alerts sent | 200 |
| Paid subscribers | 50 |

