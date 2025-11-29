# 📄 eBL Manager - Product Spec

## Overview
**Product Name:** TRDR eBL Manager  
**Tagline:** "Manage electronic Bills of Lading across all platforms"  
**Priority:** HIGH (Future-proofing - eBL adoption accelerating)  
**Estimated Dev Time:** 4-6 weeks  

---

## Market Context

### The eBL Revolution
- **2024:** DCSA reports 5% of global B/Ls are electronic
- **2025:** Target 50% by major carriers (Maersk, MSC, CMA CGM)
- **2028:** Target 100% (DCSA Digital Container Shipping roadmap)
- **Legal:** UK ETDA 2023, Singapore ETA 2021, US MLETR adoption pending

### The Problem
SME exporters are confused by multiple eBL platforms:
- Each carrier/bank uses different platforms
- No unified view of all eBLs
- Learning curve for each platform
- Difficult to track title transfers

---

## Solution

A **unified dashboard** to manage eBLs across all platforms:

```
┌─────────────────────────────────────────────────────────────┐
│                     eBL MANAGER                             │
│                                                             │
│  Connected Platforms:                                       │
│  ✅ DCSA  ✅ BOLERO  ✅ essDOCS  ✅ WaveBL  ⚪ CargoX       │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  📋 Your eBLs                                    [+ New eBL]│
│  ┌─────────────────────────────────────────────────────┐   │
│  │ B/L No.      │ Platform │ Status    │ Holder       │   │
│  ├──────────────┼──────────┼───────────┼──────────────┤   │
│  │ MSKU123456   │ DCSA     │ 🟢 Active │ HSBC HK      │   │
│  │ OOLU789012   │ WaveBL   │ 🟡 Pending│ You          │   │
│  │ EISU345678   │ BOLERO   │ ⚪ Draft  │ You          │   │
│  │ MSCU901234   │ essDOCS  │ 🔵 Surrendered│ -        │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Core Features

### 1. Multi-Platform Dashboard
```
┌───────────────────────────────────────────────────────────┐
│  eBL Overview                                             │
│                                                           │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐     │
│  │   12    │  │    5    │  │    3    │  │    2    │     │
│  │ Active  │  │ Pending │  │ Transfer│  │ Surrend │     │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘     │
│                                                           │
│  Platform Breakdown:                                      │
│  ████████████░░░░ DCSA (45%)                             │
│  ████████░░░░░░░░ WaveBL (30%)                           │
│  ████░░░░░░░░░░░░ BOLERO (15%)                           │
│  ██░░░░░░░░░░░░░░ essDOCS (10%)                          │
└───────────────────────────────────────────────────────────┘
```

### 2. Title Transfer Tracking
```
┌───────────────────────────────────────────────────────────┐
│  B/L: MSKU123456789                                       │
│  Platform: DCSA                                           │
│                                                           │
│  Title Transfer History:                                  │
│  ──────────────────────────────────────────────────────   │
│                                                           │
│  🏭 Shipper                    📅 2025-11-15 09:00       │
│  │  Dhaka Knitwear Exports                               │
│  │  Status: ISSUED                                       │
│  ▼                                                        │
│  🏦 Advising Bank              📅 2025-11-15 14:30       │
│  │  HSBC Bangladesh                                      │
│  │  Status: ENDORSED TO BANK                             │
│  ▼                                                        │
│  🏦 Issuing Bank               📅 2025-11-16 10:00       │
│  │  ICBC Shanghai                                        │
│  │  Status: TRANSFERRED                                  │
│  ▼                                                        │
│  🏭 Consignee                  📅 2025-11-18 16:00       │
│     Shanghai Fashion Import Co                           │
│     Status: SURRENDERED ✅                               │
│                                                           │
│  [ 📄 View Full Audit Trail ]                            │
└───────────────────────────────────────────────────────────┘
```

### 3. eBL Validation (Integration with LCopilot)
```
When eBL is uploaded to LCopilot:

┌───────────────────────────────────────────────────────────┐
│  eBL Validation Results                                   │
│                                                           │
│  ✅ Platform verified: DCSA                               │
│  ✅ Digital signature valid                               │
│  ✅ Hash integrity confirmed                              │
│  ✅ Current holder: HSBC HK (matches LC advising bank)   │
│                                                           │
│  ⚠️ Checks:                                               │
│  ├─ Shipper matches LC beneficiary: ✅                   │
│  ├─ Consignee matches LC terms: ✅                       │
│  ├─ Port of loading matches: ✅                          │
│  ├─ Port of discharge matches: ✅                        │
│  └─ On-board date within LC validity: ✅                 │
│                                                           │
│  🔒 eBL is VALID for LC presentation                     │
└───────────────────────────────────────────────────────────┘
```

### 4. Platform Connector Status
```
┌───────────────────────────────────────────────────────────┐
│  Platform Connections                                     │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ DCSA                                                │ │
│  │ Status: 🟢 Connected                                │ │
│  │ API Key: ****-****-****-1234                        │ │
│  │ Last Sync: 2 minutes ago                            │ │
│  │ [ Configure ] [ Disconnect ]                        │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ BOLERO                                              │ │
│  │ Status: 🟡 Pending Verification                     │ │
│  │ [ Complete Setup ]                                  │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ WaveBL                                              │ │
│  │ Status: ⚪ Not Connected                            │ │
│  │ [ Connect ]                                         │ │
│  └─────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────┘
```

---

## Technical Architecture

### Supported Platforms & APIs

| Platform | API Type | Status | Notes |
|----------|----------|--------|-------|
| **DCSA** | REST API | Ready | Open standard, carriers adopting |
| **BOLERO** | SWIFT + Web | Partner needed | Legacy but widely used |
| **essDOCS** | REST API | Ready | Common in commodities |
| **WaveBL** | Blockchain API | Ready | Growing fast |
| **CargoX** | Blockchain API | Future | Ethereum-based |
| **TradeLens** | Deprecated | ❌ | Shutting down |

### Data Model
```typescript
interface eBL {
  id: string;
  platform: "DCSA" | "BOLERO" | "essDOCS" | "WaveBL" | "CargoX";
  blNumber: string;
  status: "draft" | "issued" | "endorsed" | "transferred" | "surrendered";
  
  // Parties
  shipper: Party;
  consignee: Party;
  notifyParty: Party;
  currentHolder: Party;
  
  // Shipment
  portOfLoading: string;
  portOfDischarge: string;
  vesselName: string;
  voyageNumber: string;
  onBoardDate: Date;
  
  // Cargo
  goodsDescription: string;
  containerNumbers: string[];
  grossWeight: number;
  
  // Transfer history
  transferHistory: TransferEvent[];
  
  // Verification
  digitalSignature: string;
  hashIntegrity: string;
  platformVerified: boolean;
}

interface TransferEvent {
  timestamp: Date;
  fromParty: Party;
  toParty: Party;
  action: "issue" | "endorse" | "transfer" | "surrender";
  platformTxId: string;
}
```

### API Endpoints
```
GET  /api/ebl                    → List all eBLs
GET  /api/ebl/:id                → Get eBL details
POST /api/ebl/import             → Import eBL from platform
POST /api/ebl/:id/validate       → Validate against LC
GET  /api/ebl/:id/history        → Get transfer history
POST /api/ebl/platforms/connect  → Connect platform account
```

---

## User Flows

### Flow 1: Connect Platform
```
1. User clicks "Connect Platform"
2. Select platform (DCSA, WaveBL, etc.)
3. Enter API credentials / OAuth login
4. System verifies connection
5. Auto-import existing eBLs
```

### Flow 2: Track eBL
```
1. eBL appears in dashboard
2. User clicks to view details
3. See full transfer history
4. Get notified on status changes
```

### Flow 3: Validate for LC
```
1. User uploads eBL in LCopilot
2. System detects eBL format
3. Auto-fetch from connected platform
4. Validate against LC requirements
5. Show compliance status
```

---

## Pricing Model

| Tier | eBLs/Month | Price | Target User |
|------|------------|-------|-------------|
| Free | 5 | $0 | Try it out |
| Starter | 25 | $49/mo | Occasional shipper |
| Professional | 100 | $149/mo | Regular exporter |
| Enterprise | Unlimited | $399/mo | Freight forwarders, banks |

**Add-on:** LCopilot + eBL Bundle = 20% discount

---

## MVP Features (Week 1-3)

- [ ] Dashboard UI
- [ ] DCSA connector (most open)
- [ ] eBL import and display
- [ ] Transfer history view
- [ ] Basic validation

## V2 Features (Week 4-6)

- [ ] WaveBL connector
- [ ] essDOCS connector
- [ ] LCopilot integration
- [ ] Push notifications
- [ ] Export to PDF

## V3 Features (Future)

- [ ] BOLERO connector (requires partnership)
- [ ] Auto-title transfer initiation
- [ ] Bank integration
- [ ] Multi-party workflows

---

## Legal & Compliance

### Supported Jurisdictions
| Country | Legal Framework | Status |
|---------|-----------------|--------|
| UK | ETDA 2023 | ✅ eBL legally equivalent to paper |
| Singapore | ETA 2021 | ✅ eBL legally equivalent |
| USA | UCC Article 7 (pending MLETR) | ⚠️ Varies by state |
| UAE | ETTSL 2021 | ✅ eBL recognized |
| Germany | TDG (Transport Documents Act) | ✅ eBL recognized |
| China | Pending | ⚠️ Not yet recognized |

### Bank Acceptance
- HSBC: ✅ Accepts DCSA, BOLERO
- Standard Chartered: ✅ Accepts DCSA, essDOCS
- Citi: ✅ Accepts all major platforms
- ICBC: ⚠️ Limited acceptance
- Bank of China: ⚠️ Case-by-case

---

## Competitive Analysis

| Competitor | Multi-Platform? | Validation? | Price |
|------------|-----------------|-------------|-------|
| BOLERO | ❌ Own platform only | ❌ | $$$$ |
| essDOCS | ❌ Own platform only | ❌ | $$$ |
| WaveBL | ❌ Own platform only | ❌ | $$ |
| CargoX | ❌ Own platform only | ❌ | $$ |
| **TRDR eBL Manager** | ✅ **All platforms** | ✅ **LC validation** | $$ |

**Unique Value Prop:** Only tool that aggregates ALL eBL platforms + validates against LC!

---

## Success Metrics

| Metric | Target (Month 3) | Target (Year 1) |
|--------|------------------|-----------------|
| Connected accounts | 100 | 2,000 |
| eBLs managed | 500 | 25,000 |
| Platform connections | 2 | 5 |
| Bank partnerships | 1 | 5 |

---

## Marketing Hooks

1. **SEO:** "Electronic bill of lading management", "eBL tracker"
2. **Content:** "Paper B/L vs eBL comparison guide"
3. **Partnerships:** Approach carriers (Maersk, MSC) for co-marketing
4. **Events:** Sponsor DCSA/TradeTech conferences
5. **Timing:** "The future is now - 50% of B/Ls will be electronic by 2025"

