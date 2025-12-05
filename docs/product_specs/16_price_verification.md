# 💰 Price Verification Tool - Product Spec

## Overview
**Product Name:** TRDR Price Verify  
**Tagline:** "Catch price anomalies before they become problems"  
**Priority:** HIGH (Direct bank request - competitive differentiator)  
**Estimated Dev Time:** 4-6 weeks  

---

## Problem Statement

Banks and traders face critical price verification challenges:

### For Banks (LC Issuing/Advising)
- **Trade-Based Money Laundering (TBML)**: Over/under invoicing is the #1 method
- **Manual price checks**: Google searches, outdated databases
- **Regulatory pressure**: FATF guidelines require price verification
- **Risk exposure**: Financing goods at inflated prices = collateral risk

### For Traders
- **Supplier fraud**: Being overcharged vs market rates
- **Negotiation blind spots**: Don't know fair market price
- **Currency confusion**: USD vs local currency conversions
- **No historical context**: Is this price normal for this season?

---

## The Opportunity

| Current State | With TRDR Price Verify |
|---------------|------------------------|
| Manual Google searches | Instant commodity price lookup |
| Outdated price databases | Real-time market data |
| No documentation | Auditable verification reports |
| Subjective judgment | Objective variance scoring |
| 30-60 minutes per check | < 30 seconds |

---

## Solution

An intelligent price verification system that:
1. **Extracts** prices from uploaded documents (invoices, LCs)
2. **Identifies** the commodity/goods being traded
3. **Looks up** current market prices from multiple sources
4. **Calculates** variance and flags anomalies
5. **Generates** compliance-ready verification reports

---

## User Interface

### Main Screen - Price Check
```
┌─────────────────────────────────────────────────────────────────┐
│  💰 PRICE VERIFICATION                                          │
│                                                                 │
│  Verify trade prices against global market rates               │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 📄 UPLOAD DOCUMENT                                      │   │
│  │                                                         │   │
│  │     Drop Invoice, LC, or Contract here                 │   │
│  │     or click to browse                                  │   │
│  │                                                         │   │
│  │     We'll extract prices automatically                 │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ─────────────────── OR ───────────────────                    │
│                                                                 │
│  🔍 MANUAL LOOKUP                                              │
│                                                                 │
│  Commodity:  [ Cotton (raw) ▼ ]  or  [ Search... ]            │
│                                                                 │
│  HS Code:    [ 5201.00.00 ]     (auto-filled from commodity)   │
│                                                                 │
│  Quantity:   [ 100 ]  [ MT ▼ ]  (Metric Tons)                  │
│                                                                 │
│  Unit Price: [ 1,850 ]  [ USD ▼ ]  per [ MT ▼ ]               │
│                                                                 │
│  Origin:     [ Bangladesh 🇧🇩 ▼ ]                              │
│  Destination:[ China 🇨🇳 ▼ ]                                   │
│                                                                 │
│  Incoterm:   [ FOB ▼ ]  (affects price comparison)            │
│                                                                 │
│                    [ 🔍 Verify Price ]                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Results Screen - Price Verified ✅
```
┌─────────────────────────────────────────────────────────────────┐
│  ✅ PRICE VERIFICATION RESULT                                   │
│                                                                 │
│  Overall: WITHIN NORMAL RANGE                                  │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  📦 ITEM DETAILS                                               │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Commodity:     Raw Cotton (Middling Grade)              │   │
│  │ HS Code:       5201.00.00                               │   │
│  │ Quantity:      100 MT                                   │   │
│  │ Document Price: USD 1,850 / MT (FOB Chittagong)        │   │
│  │ Total Value:   USD 185,000                              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  📊 MARKET COMPARISON                                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                                                         │   │
│  │  Your Price          Market Range         Variance     │   │
│  │  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │   │
│  │                                                         │   │
│  │     $1,850              $1,720 ─────────── $1,920      │   │
│  │        │                   │       ▲          │        │   │
│  │        │                   │       │          │        │   │
│  │        └───────────────────┼───────┘          │        │   │
│  │                            │    +3.2%         │        │   │
│  │                         $1,792               │        │   │
│  │                        (Avg Price)            │        │   │
│  │                                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  📈 PRICE SOURCES                                              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Source              │ Price      │ Date       │ Grade  │   │
│  ├─────────────────────┼────────────┼────────────┼────────┤   │
│  │ ICE Cotton Futures  │ $1,792/MT  │ Today      │ Mid    │   │
│  │ Cotlook A Index     │ $1,810/MT  │ Yesterday  │ Mid    │   │
│  │ USDA Weekly         │ $1,785/MT  │ Nov 25     │ Avg    │   │
│  │ BD Export Stats     │ $1,720/MT  │ Q3 2024    │ FOB    │   │
│  │ China Import CIF    │ $1,920/MT  │ Nov 2024   │ CIF    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ✅ VERDICT: Price is +3.2% above average - ACCEPTABLE         │
│     Tolerance range: ±15% for this commodity                   │
│                                                                 │
│  [ 📄 Download Report ]  [ 🔄 New Check ]  [ 📧 Email Report ] │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Results Screen - Price Alert ⚠️
```
┌─────────────────────────────────────────────────────────────────┐
│  ⚠️ PRICE VERIFICATION ALERT                                    │
│                                                                 │
│  Overall: SIGNIFICANT VARIANCE DETECTED                        │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  📦 ITEM DETAILS                                               │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Commodity:     Stainless Steel Coils (Grade 304)        │   │
│  │ HS Code:       7219.32.00                               │   │
│  │ Quantity:      50 MT                                    │   │
│  │ Document Price: USD 4,500 / MT (CIF Shanghai)          │   │
│  │ Total Value:   USD 225,000                              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  🚨 VARIANCE ANALYSIS                                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                                                         │   │
│  │  Your Price          Market Range         Variance     │   │
│  │  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  │   │
│  │                                                         │   │
│  │     $4,500                                             │   │
│  │        │                                               │   │
│  │        │              ⚠️ +38.5%                        │   │
│  │        │                                               │   │
│  │        │                   $2,980 ──────── $3,450      │   │
│  │        │                      │      ▲        │        │   │
│  │        │                      │   $3,250      │        │   │
│  │        │                      │  (Avg Price)  │        │   │
│  │                                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  🚨 RED FLAGS                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                                                         │   │
│  │  ❌ Price 38.5% ABOVE market average                   │   │
│  │     Normal variance for steel: ±10%                    │   │
│  │                                                         │   │
│  │  ❌ Price exceeds 52-week high ($3,680)                │   │
│  │                                                         │   │
│  │  ⚠️ TBML Risk Indicator: Potential over-invoicing      │   │
│  │     Consider enhanced due diligence                    │   │
│  │                                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  📋 RECOMMENDED ACTIONS                                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                                                         │   │
│  │  1. Request supplier to justify the premium pricing    │   │
│  │  2. Verify if special grade/specification applies      │   │
│  │  3. Check for recent price spikes in this commodity    │   │
│  │  4. Document rationale if proceeding with transaction  │   │
│  │                                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  [ 📄 Download Report ]  [ 🔄 New Check ]  [ 🚨 Flag for Review ]│
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Commodity Categories Supported

### Phase 1 (MVP) - Top Bangladesh Trade Commodities
| Category | Examples | Data Sources |
|----------|----------|--------------|
| **Textiles** | Raw Cotton, Cotton Yarn, Fabric | ICE Futures, Cotlook Index, USDA |
| **Metals** | Steel Coils, Aluminum, Copper | LME, Shanghai Futures, Platts |
| **Garments** | RMG, Knitwear | Industry benchmarks, export data |
| **Food/Agri** | Rice, Wheat, Sugar, Edible Oil | FAO, USDA, local exchanges |
| **Energy** | Fuel Oil, LNG | Platts, Argus |
| **Chemicals** | Dyes, Polymers | ICIS, industry reports |

### Phase 2 - Expanded Coverage
- Electronics & Machinery
- Pharmaceuticals (API pricing)
- Leather & Leather goods
- Jute & Jute products
- Seafood (shrimp, fish)
- Ceramics & Glassware

---

## Technical Architecture

### Data Sources
```
┌─────────────────────────────────────────────────────────────────┐
│                      PRICE DATA AGGREGATOR                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  COMMODITIES EXCHANGES          INDUSTRY INDICES                │
│  ┌─────────────────┐           ┌─────────────────┐             │
│  │ • ICE (Cotton)  │           │ • Cotlook Index │             │
│  │ • LME (Metals)  │           │ • ICIS Chemical │             │
│  │ • CBOT (Grains) │           │ • Platts Energy │             │
│  │ • Shanghai FE   │           │ • Argus Media   │             │
│  └─────────────────┘           └─────────────────┘             │
│                                                                 │
│  GOVERNMENT SOURCES             ALTERNATIVE DATA                │
│  ┌─────────────────┐           ┌─────────────────┐             │
│  │ • USDA Reports  │           │ • Import/Export │             │
│  │ • FAO GIEWS     │           │   customs data  │             │
│  │ • BD Export     │           │ • Trade finance │             │
│  │   Promotion     │           │   databases     │             │
│  │ • China Customs │           │ • Industry APIs │             │
│  └─────────────────┘           └─────────────────┘             │
│                                                                 │
│                         ↓                                       │
│              ┌─────────────────────┐                           │
│              │  PRICE NORMALIZER   │                           │
│              │  - Unit conversion  │                           │
│              │  - Currency FX      │                           │
│              │  - Incoterm adjust  │                           │
│              │  - Grade mapping    │                           │
│              └─────────────────────┘                           │
│                         ↓                                       │
│              ┌─────────────────────┐                           │
│              │  VARIANCE ENGINE    │                           │
│              │  - % deviation      │                           │
│              │  - Historical range │                           │
│              │  - Seasonal adjust  │                           │
│              │  - Risk scoring     │                           │
│              └─────────────────────┘                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### API Design
```
POST /api/price-verify
{
  "commodity": "cotton_raw",
  "hs_code": "5201.00.00",
  "quantity": 100,
  "quantity_unit": "MT",
  "unit_price": 1850,
  "currency": "USD",
  "price_unit": "MT",
  "origin_country": "BD",
  "destination_country": "CN",
  "incoterm": "FOB",
  "document_date": "2024-11-29"
}

Response:
{
  "status": "verified",
  "risk_level": "low",
  "variance_percent": 3.2,
  "variance_direction": "above",
  "market_price": {
    "average": 1792,
    "low": 1720,
    "high": 1920,
    "currency": "USD",
    "unit": "MT",
    "as_of": "2024-11-29"
  },
  "tolerance": {
    "normal_range_percent": 15,
    "alert_threshold_percent": 25
  },
  "sources": [...],
  "recommendations": [],
  "report_id": "PV-2024-001234"
}
```

---

## Pricing Model

### Tiered Pricing
| Tier | Price Checks/Month | Price | Per Check |
|------|-------------------|-------|-----------|
| **Free** | 10 | $0 | - |
| **Starter** | 100 | $49/mo | $0.49 |
| **Professional** | 500 | $149/mo | $0.30 |
| **Business** | 2,000 | $399/mo | $0.20 |
| **Enterprise** | Unlimited | Custom | Volume discount |

### Add-ons
- **API Access**: +$99/mo
- **Historical Data (5 years)**: +$49/mo
- **Custom Commodity Coverage**: +$199/mo
- **White-label Reports**: +$99/mo

---

## Integration Points

### With LCopilot
```
LC Document Uploaded
        ↓
Extract goods description, quantity, amount
        ↓
Auto-trigger Price Verification
        ↓
Include in LC Validation Report:
"Price Check: ✅ Cotton at $1,850/MT is within market range (+3.2%)"
```

### With Sanctions Screener
```
Price anomaly detected
        ↓
Flag potential TBML risk
        ↓
Auto-trigger enhanced screening on parties
        ↓
Combined risk assessment
```

### With HS Code Finder
```
User enters commodity description
        ↓
HS Code Finder suggests codes
        ↓
Price Verify uses HS code for accurate lookup
        ↓
Seamless workflow
```

---

## Compliance Features

### TBML Risk Indicators (Auto-detected)
| Indicator | Description | Action |
|-----------|-------------|--------|
| **Over-invoicing** | Price >25% above market | Alert + EDD flag |
| **Under-invoicing** | Price >25% below market | Alert + EDD flag |
| **Price at exact round number** | e.g., exactly $5,000/MT | Note in report |
| **Multiple shipments, identical prices** | Same price across shipments | Pattern flag |
| **High-risk origin/destination** | Price check + sanctions | Combined alert |

### Audit Trail
- Every price check logged with timestamp
- User attribution
- Source data preserved
- Report versioning
- Exportable for regulators

---

## MVP Features (Phase 1) ✅ COMPLETED

### Must Have ✅
- [x] Manual price lookup (commodity + price input)
- [x] Top 50+ commodities (Bangladesh focus)
- [x] Multiple price sources per commodity
- [x] Variance calculation + verdict
- [x] PDF report generation
- [x] Historical price charts

### Should Have ✅
- [x] HS code to commodity mapping
- [x] Currency conversion (live FX rates)
- [x] Dashboard with sidebar navigation
- [x] Batch verification (CSV upload)
- [x] TBML risk flagging

### Nice to Have 🔄
- [ ] LCopilot integration (auto-verify LC prices)
- [ ] API access for external systems
- [ ] Custom commodity requests
- [ ] White-label reports

---

## Success Metrics

| Metric | Target (6 months) |
|--------|-------------------|
| Monthly Active Users | 200+ |
| Price Checks/Month | 5,000+ |
| Accuracy (vs actual market) | >90% |
| Time to verify | <30 seconds |
| User satisfaction | >4.5/5 |
| Conversion (free→paid) | >8% |

---

## Competitive Analysis

| Feature | TRDR Price Verify | ICC Price Check | Manual Process |
|---------|-------------------|-----------------|----------------|
| **Price** | $49-399/mo | $500+/mo | Staff time |
| **Speed** | <30 seconds | Minutes | 30-60 mins |
| **Commodities** | 50+ | 100+ | Varies |
| **Document extraction** | ✅ AI-powered | ❌ Manual | ❌ Manual |
| **TBML flagging** | ✅ Auto | ⚠️ Basic | ❌ None |
| **Integration** | ✅ Full suite | ❌ Standalone | ❌ N/A |
| **Bangladesh focus** | ✅ Optimized | ⚠️ Generic | Varies |

---

## Risk & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Data source reliability** | High | Multi-source averaging, manual override |
| **Commodity misidentification** | Medium | HS code validation, user confirmation |
| **Price volatility** | Medium | Wider tolerance bands, date stamping |
| **FX rate fluctuations** | Low | Real-time rates, clear timestamps |
| **Regulatory changes** | Low | Modular compliance rules |

---

## Go-to-Market

### Target Segments
1. **Banks** (LC departments) - Primary based on your meeting feedback
2. **Large Exporters** (RMG, Textiles)
3. **Trading Companies**
4. **Freight Forwarders** (value-add service)

### Launch Channels
- Direct sales to banks (leverage your contact!)
- Integration with LCopilot (upsell)
- Trade association partnerships
- LinkedIn content marketing

### Messaging
> "Stop Googling prices. Get verified market rates in seconds."
> "Catch over-invoicing before it becomes a compliance headache."
> "The price verification tool banks actually use."

---

## Timeline

| Week | Milestone |
|------|-----------|
| 1-2 | Data source integration (5 commodities) |
| 3-4 | Core variance engine + UI |
| 5 | Document extraction integration |
| 6 | Testing + report generation |
| 7 | Beta with 3 banks |
| 8 | Public launch |

---

## Open Questions

1. **Which 20 commodities should be in MVP?** (Need Bangladesh trade data)
2. **Free tier limitations?** (10/month vs time-limited)
3. **Should banks get different UI than traders?**
4. **Integration: Should every LC auto-verify prices?**

---

## Next Steps

1. ✅ Product spec (this document)
2. ⬜ Validate commodity list with bank contact
3. ⬜ Research data source APIs and costs
4. ⬜ Create landing page
5. ⬜ Build MVP

---

*Last Updated: November 30, 2024*
*Author: TRDR Hub Product Team*

