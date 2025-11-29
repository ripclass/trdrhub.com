# 🔒 Sanctions Screener - Product Spec

## Overview
**Product Name:** TRDR Sanctions Screener  
**Tagline:** "Screen parties, vessels, and goods in seconds"  
**Priority:** HIGH (Quick Win - you already have the rules!)  
**Estimated Dev Time:** 2-3 weeks  

---

## Problem Statement
SME exporters/importers don't have access to enterprise sanctions screening tools (Dow Jones, World-Check cost $10K+/year). They either:
- Skip screening (risky)
- Manually Google names (incomplete)
- Pay expensive consultants

## Solution
A simple, affordable sanctions screening tool that checks:
- **Parties** (buyers, sellers, banks, agents)
- **Vessels** (flag, owner, operator)
- **Ports** (loading, discharge, transshipment)
- **Goods** (dual-use, controlled items)

---

## User Flow

```
┌─────────────────────────────────────────────────────────────┐
│                   SANCTIONS SCREENER                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  🔍 What do you want to screen?                            │
│                                                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │ 👤 Party │ │ 🚢 Vessel│ │ ⚓ Port  │ │ 📦 Goods │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Enter name, IMO number, or HS code...               │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ☑️ OFAC SDN     ☑️ EU Consolidated    ☑️ UN Sanctions     │
│  ☑️ UK OFSI     ☑️ Dual-Use (EAR)     ☑️ Vessel Lists     │
│                                                             │
│                    [ 🔍 Screen Now ]                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Results Screen

### ✅ CLEAR Result
```
┌─────────────────────────────────────────────────────────────┐
│  ✅ NO MATCHES FOUND                                        │
│                                                             │
│  Party: "Acme Trading Co Ltd"                              │
│  Screened against: 6 lists                                  │
│  Date: 2025-11-29 14:32 UTC                                │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ OFAC SDN          ✅ Clear                          │   │
│  │ EU Consolidated   ✅ Clear                          │   │
│  │ UN Sanctions      ✅ Clear                          │   │
│  │ UK OFSI           ✅ Clear                          │   │
│  │ EAR Entity List   ✅ Clear                          │   │
│  │ Vessel Sanctions  ✅ N/A (not a vessel)             │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  [ 📄 Download Certificate ]  [ 🔄 Screen Another ]        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### ⚠️ POTENTIAL MATCH Result
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
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ⚠️ DO NOT PROCEED without compliance review               │
│                                                             │
│  [ 📞 Contact Compliance ]  [ 📄 Download Report ]         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Technical Architecture

### Data Sources (Your Existing Rules!)
```
Data/sanctions/
├── sanctions_screening.json      → API config & general rules
├── sanctions_ofac_detailed.json  → OFAC SDN, 50% Rule, SSI
├── sanctions_eu_detailed.json    → EU Consolidated, Russia packages
├── sanctions_un_uk.json          → UN 1718/1267, UK OFSI
└── sanctions_vessel_shipping.json → Vessel flags, dark activity
```

### API Endpoints
```
POST /api/sanctions/screen
{
  "type": "party" | "vessel" | "port" | "goods",
  "query": "string",
  "lists": ["OFAC", "EU", "UN", "UK", "EAR"],
  "fuzzy_threshold": 0.85
}

Response:
{
  "status": "clear" | "potential_match" | "match",
  "matches": [...],
  "screened_at": "ISO timestamp",
  "certificate_id": "uuid"
}
```

### Matching Algorithm
```python
def screen_party(name: str, lists: List[str]) -> ScreeningResult:
    # 1. Normalize name (remove Ltd, Inc, Co, etc.)
    normalized = normalize_party_name(name)
    
    # 2. Check exact match
    exact_matches = check_exact_match(normalized, lists)
    
    # 3. Check fuzzy match (Levenshtein, Jaro-Winkler)
    fuzzy_matches = check_fuzzy_match(normalized, lists, threshold=0.85)
    
    # 4. Check alias matches
    alias_matches = check_aliases(normalized, lists)
    
    # 5. Check 50% rule (for OFAC)
    ownership_matches = check_ownership_rule(normalized)
    
    return consolidate_results(exact_matches, fuzzy_matches, alias_matches)
```

---

## Pricing Model

| Tier | Screens/Month | Price | Target User |
|------|---------------|-------|-------------|
| Free | 10 | $0 | Try before buy |
| Starter | 100 | $29/mo | Small exporter |
| Professional | 500 | $99/mo | Active trader |
| Enterprise | Unlimited | $299/mo | Banks, freight forwarders |

**Upsell:** Bulk screening API for ERP integration

---

## MVP Features (Week 1-2)

- [ ] Party name screening
- [ ] OFAC SDN list
- [ ] EU Consolidated list  
- [ ] Fuzzy matching
- [ ] PDF certificate generation
- [ ] Basic UI

## V2 Features (Week 3-4)

- [ ] Vessel screening (IMO lookup)
- [ ] Port screening
- [ ] UK OFSI, UN lists
- [ ] Batch upload (CSV)
- [ ] API access
- [ ] Audit trail

## V3 Features (Future)

- [ ] Real-time list updates
- [ ] Dual-use goods screening
- [ ] Integration with LCopilot
- [ ] Watchlist monitoring (alert when list updates)

---

## Integration with LCopilot

```
LCopilot Validation Flow:
┌──────────────────────────────────────────────────────────┐
│ 1. Extract parties from LC (beneficiary, applicant,     │
│    advising bank, confirming bank)                      │
│                                                         │
│ 2. AUTO-SCREEN all parties via Sanctions Screener       │
│                                                         │
│ 3. If match found → Flag as CRITICAL issue              │
│    "⚠️ Beneficiary matches OFAC SDN list"              │
│                                                         │
│ 4. Block submission until resolved                      │
└──────────────────────────────────────────────────────────┘
```

---

## Competitive Analysis

| Competitor | Price | Coverage | SME Friendly? |
|------------|-------|----------|---------------|
| Dow Jones Risk & Compliance | $10K+/yr | Excellent | ❌ Enterprise only |
| World-Check (Refinitiv) | $8K+/yr | Excellent | ❌ Enterprise only |
| ComplyAdvantage | $5K+/yr | Good | ⚠️ Expensive |
| Sanction Scanner | $200/mo | Good | ✅ Yes |
| **TRDR Sanctions Screener** | $29-299/mo | Good | ✅ **Built for SMEs** |

---

## Success Metrics

| Metric | Target (Month 1) | Target (Month 6) |
|--------|------------------|------------------|
| Signups | 100 | 1,000 |
| Paid conversions | 10% | 15% |
| Screens/day | 500 | 10,000 |
| API customers | 5 | 50 |

---

## Marketing Hooks

1. **SEO:** "Free sanctions screening tool", "OFAC check online"
2. **Content:** "How to screen your trade partners" guide
3. **Integration:** "Screen while you validate your LC" with LCopilot
4. **Trust:** "Used by 500+ exporters" badge

---

## Risk & Compliance Notes

⚠️ **Disclaimer Required:**
> "TRDR Sanctions Screener is a screening aid, not legal advice. 
> Results should be verified with your compliance team. 
> We update lists regularly but cannot guarantee real-time accuracy."

⚠️ **Data Sources:**
- OFAC: Public domain, updated daily
- EU: Public domain, updated weekly
- UN: Public domain, updated as published
- UK: Public domain, updated weekly

No license required for public sanctions data.

