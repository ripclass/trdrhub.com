# TRDR Sanctions Screener - Gap Analysis

## Current State Assessment

### ✅ What Already Exists

#### 1. Sanctions Data Files
| File | Contents | Ready? |
|------|----------|--------|
| `sanctions_ofac_detailed.json` | 20+ OFAC rules (SDN, SSI, CAPTA, 50% rule, country programs) | ✅ |
| `sanctions_eu_detailed.json` | 15+ EU rules (Russia packages, Belarus, Iran, Syria) | ✅ |
| `sanctions_un_uk.json` | UN Security Council + UK OFSI rules | ✅ |
| `sanctions_screening.json` | API config + screening workflow rules | ✅ |
| `sanctions_vessel_shipping.json` | Vessel-specific + dark activity rules | ✅ |

**Total: 50+ sanctions rules already built!**

#### 2. Vessel Sanctions Service
`apps/api/app/services/vessel_sanctions.py` - **300+ lines, production-ready:**
- ✅ OFAC SDN list fetching (live from Treasury)
- ✅ EU Consolidated list fetching
- ✅ Fuzzy name matching with scoring
- ✅ Flag risk assessment (Paris MoU, Tokyo MoU)
- ✅ Flags of convenience detection
- ✅ Comprehensive result model
- ✅ Caching for performance

#### 3. Landing Page
`apps/web/src/pages/tools/SanctionsScreenerLanding.tsx` - **420+ lines, beautiful:**
- ✅ Hero section with screening types
- ✅ Pricing tiers ($29-299/mo)
- ✅ Feature breakdown (50+ lists, <2s screening)
- ✅ FAQ section
- ✅ Call-to-action buttons

---

## Gap Analysis

### ❌ Missing: Party Screening Backend
**Priority: CRITICAL**

The vessel service exists but party/entity screening doesn't.

| Missing Component | Effort |
|-------------------|--------|
| Party name normalization | 4 hrs |
| OFAC SDN entity lookup | 8 hrs |
| EU entity list integration | 8 hrs |
| Fuzzy matching (Jaro-Winkler) | 4 hrs |
| Alias database | 4 hrs |
| 50% ownership rule check | 8 hrs |

### ❌ Missing: Goods/Dual-Use Screening
**Priority: HIGH**

Already have export controls in HS Code Finder (Phase 4). Need to integrate:
- ECCN to HS code mapping
- Dual-use goods check
- End-use screening

### ❌ Missing: Screening Dashboard
**Priority: CRITICAL**

The landing page exists but no actual screening interface.

| Missing Component | Effort |
|-------------------|--------|
| Party screening form | 4 hrs |
| Vessel screening form | 4 hrs |
| Goods screening form | 4 hrs |
| Results display | 8 hrs |
| PDF certificate export | 8 hrs |
| Screening history | 4 hrs |

### ❌ Missing: Database Models
**Priority: HIGH**

| Model | Purpose | Effort |
|-------|---------|--------|
| SanctionsList | Track list versions/updates | 4 hrs |
| SanctionedEntity | Cached SDN entries | 8 hrs |
| ScreeningHistory | User audit trail | 4 hrs |
| ScreeningCertificate | Compliance records | 4 hrs |

### ❌ Missing: Real-Time List Updates
**Priority: MEDIUM**

Currently fetches on-demand. Need:
- Scheduled list sync (daily OFAC, weekly EU)
- List version tracking
- Change detection alerts

### ❌ Missing: Batch Screening
**Priority: MEDIUM**

For users screening hundreds of parties from ERP/TMS.

---

## Implementation Plan

### Phase 1: Core Screening (Priority: CRITICAL) - 40 hours
**Goal:** Working party + vessel + goods screening

**Database Models:**
```
SanctionsList        - List metadata and version tracking
SanctionedEntity     - Cached entities from lists
ScreeningResult      - Individual screening results
ScreeningHistory     - User audit trail
```

**API Endpoints:**
```
POST /sanctions/screen             - Single entity screening
POST /sanctions/batch-screen       - Batch screening (CSV)
GET  /sanctions/lists              - Available lists
GET  /sanctions/history            - User screening history
GET  /sanctions/certificate/{id}   - Download compliance cert
```

**Tasks:**
```
[Phase 1 Tasks - 40 hours]
[ ] Create database models for sanctions - 4 hrs
[ ] Party screening service (extend vessel service) - 12 hrs
[ ] Goods screening (integrate HS Code export controls) - 8 hrs
[ ] Screening API endpoints - 8 hrs
[ ] PDF certificate generation - 4 hrs
[ ] Run database migration - 4 hrs
```

### Phase 2: Screening Dashboard (Priority: HIGH) - 32 hours
**Goal:** Beautiful screening interface

**Frontend Pages:**
```
SanctionsLayout.tsx       - Sidebar layout
SanctionsOverview.tsx     - Dashboard home
SanctionsScreen.tsx       - Main screening interface
SanctionsHistory.tsx      - Past screenings
SanctionsCertificates.tsx - Download certs
SanctionsSettings.tsx     - Preferences
SanctionsHelp.tsx         - FAQ/Help
```

**Tasks:**
```
[Phase 2 Tasks - 32 hours]
[ ] Sanctions sidebar layout - 4 hrs
[ ] Party screening form + results - 8 hrs
[ ] Vessel screening form + results - 4 hrs (leverage existing)
[ ] Goods screening form + results - 4 hrs
[ ] Screening history page - 4 hrs
[ ] Certificate viewer + download - 4 hrs
[ ] Settings page - 2 hrs
[ ] Help/FAQ page - 2 hrs
```

### Phase 3: Production Polish (Priority: MEDIUM) - 24 hours
**Goal:** Features that differentiate from competitors

**Tasks:**
```
[Phase 3 Tasks - 24 hours]
[ ] Batch upload (CSV) with progress - 8 hrs
[ ] Real-time list sync job - 8 hrs
[ ] List update notifications - 4 hrs
[ ] API access for ERP integration - 4 hrs
```

### Phase 4: LCopilot Integration (Priority: HIGH) - 16 hours
**Goal:** Auto-screen parties in LCs

**Tasks:**
```
[Phase 4 Tasks - 16 hours]
[ ] Extract parties from LC documents - 4 hrs
[ ] Auto-screen during validation - 4 hrs
[ ] Display sanctions flags in Issues tab - 4 hrs
[ ] Block submission if match found - 4 hrs
```

---

## Data Sources (Free/Public)

| Source | URL | Format | Update Frequency |
|--------|-----|--------|------------------|
| OFAC SDN | treasury.gov/ofac/downloads | XML | Daily |
| OFAC Cons | treasury.gov/ofac/downloads/consolidated | XML | Daily |
| EU Consolidated | webgate.ec.europa.eu/fsd/fsf | XML | Weekly |
| UN UNSC | scsanctions.un.org | XML | As published |
| UK OFSI | gov.uk/government/publications | CSV | Weekly |

**No license required** - all public domain sanctions data.

---

## Matching Algorithm Design

### Name Normalization
```python
def normalize_name(name: str) -> str:
    # Remove legal suffixes: Ltd, Inc, Corp, LLC, GmbH, SA, AG
    # Remove punctuation and extra spaces
    # Transliterate non-ASCII characters
    # Convert to uppercase
```

### Fuzzy Matching
```python
def calculate_match_score(query: str, target: str) -> float:
    # 1. Exact match → 100%
    # 2. Jaro-Winkler similarity
    # 3. Token set ratio (handles word order)
    # 4. Phonetic matching (Soundex/Metaphone)
    # Return weighted average
```

### Match Thresholds
| Threshold | Classification |
|-----------|----------------|
| ≥95% | Exact Match - Block |
| 85-94% | High Match - Review Required |
| 70-84% | Potential Match - Flag |
| <70% | No Match |

---

## UI/UX Design

### Screening Flow
```
┌─────────────────────────────────────────────────────────────┐
│                  SANCTIONS SCREENER                         │
├─────────────────────────────────────────────────────────────┤
│  🔍 What do you want to screen?                            │
│                                                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │ 👤 Party │ │ 🚢 Vessel│ │ ⚓ Port  │ │ 📦 Goods │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
│                                                             │
│  Party Name:                                                │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Acme Trading Company Limited                        │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Country (optional): [United States ▼]                     │
│                                                             │
│  Lists to Screen:                                          │
│  ☑️ OFAC SDN     ☑️ EU Consolidated    ☑️ UN Sanctions     │
│  ☑️ UK OFSI     ☑️ BIS Entity List    ☑️ CAATSA           │
│                                                             │
│                    [ 🔍 Screen Now ]                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Results - Clear
```
┌─────────────────────────────────────────────────────────────┐
│  ✅ NO MATCHES FOUND                                        │
│                                                             │
│  Party: "Acme Trading Company Limited"                     │
│  Screened: 2025-12-06 18:45:32 UTC                        │
│  Lists Checked: 6                                          │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ ✅ OFAC SDN           Clear                         │   │
│  │ ✅ EU Consolidated    Clear                         │   │
│  │ ✅ UN Sanctions       Clear                         │   │
│  │ ✅ UK OFSI            Clear                         │   │
│  │ ✅ BIS Entity List    Clear                         │   │
│  │ ✅ CAATSA             Clear                         │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  [ 📄 Download Certificate ]  [ 🔄 Screen Another ]        │
│                                                             │
│  Certificate ID: TRDR-2025-12-06-A1B2C3                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Results - Match Found
```
┌─────────────────────────────────────────────────────────────┐
│  ⚠️ POTENTIAL MATCH - REVIEW REQUIRED                      │
│                                                             │
│  Party: "Iran Shipping Lines"                              │
│  Match Score: 95%                                          │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ ❌ OFAC SDN - MATCH                                 │   │
│  │    Listed Entity: "Islamic Republic of Iran         │   │
│  │                    Shipping Lines (IRISL)"          │   │
│  │    SDN ID: 10566                                    │   │
│  │    Program: IRAN-EO13382                            │   │
│  │    Listed: 2008-09-10                               │   │
│  │                                                     │   │
│  │ ❌ EU Consolidated - MATCH                          │   │
│  │    EU Ref: EU.1.42                                  │   │
│  │    Regulation: (EU) 267/2012                        │   │
│  │                                                     │   │
│  │ ✅ UK OFSI            Clear                         │   │
│  │ ✅ UN Sanctions       Clear                         │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ⚠️ DO NOT PROCEED without compliance review               │
│                                                             │
│  [ 📄 Download Report ]  [ 📞 Contact Compliance ]         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Pricing Tiers

| Tier | Screens/Month | Price | Target |
|------|---------------|-------|--------|
| Free | 10 | $0 | Trial |
| Starter | 100 | $29/mo | Small exporter |
| Professional | 500 | $99/mo | Active trader |
| Enterprise | Unlimited | $299/mo | Banks, freight |

**Upsell:** API access ($499/mo), batch upload, real-time alerts

---

## Competitive Positioning

| Feature | Dow Jones | World-Check | TRDR |
|---------|-----------|-------------|------|
| Price | $10K+/yr | $8K+/yr | $348-3,588/yr |
| SME Friendly | ❌ | ❌ | ✅ |
| Vessel Screening | Add-on | Add-on | ✅ Included |
| Goods/HS Code | ❌ | ❌ | ✅ Included |
| LC Integration | ❌ | ❌ | ✅ Included |
| API Access | $$$ | $$$ | ✅ Included |

---

## Success Metrics

| Metric | Month 1 | Month 6 |
|--------|---------|---------|
| Free signups | 100 | 1,000 |
| Paid conversions | 10% | 15% |
| Screens/day | 500 | 10,000 |
| API customers | 5 | 50 |

---

## Quick Wins (Ship This Week)

1. **Extend Vessel Service to Parties** (8 hrs)
   - Already have fuzzy matching
   - Just need party normalization

2. **Create Basic Screening UI** (8 hrs)
   - Reuse landing page design
   - Simple form + results

3. **Add Screening History** (4 hrs)
   - Store results in database
   - Display in dashboard

4. **PDF Certificate** (4 hrs)
   - Generate compliance certificate
   - Include screening timestamp

---

## Recommendation

**Start with Phase 1 + Phase 2 in parallel.**

Backend team: Build screening service
Frontend team: Build dashboard UI

The vessel service is a great foundation. Party screening is 80% the same code - just different entity normalization.

**Timeline:** 2 weeks for MVP, 4 weeks for full launch.

