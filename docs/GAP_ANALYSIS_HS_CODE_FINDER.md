# HS Code Finder - Gap Analysis & Implementation Plan

## Executive Summary

**Current State:** Demo/Prototype (15% complete)  
**Target State:** Bank-Grade Commercial Tool (100%)  
**Critical Gap:** Using ~10 sample HS codes instead of 500,000+ real codes

### Trade Specialist Verdict: Would I Pay for This?

**NO** - Not in current state. Here's why:

| What's Built | What a Trade Specialist Actually Needs |
|--------------|----------------------------------------|
| 10 sample HS codes | 500,000+ global HS codes with country extensions |
| Keyword matching | Real AI classification trained on binding rulings |
| 8 hardcoded duty rates | 18,000+ tariff lines per country, updated daily |
| Generic FTA text | Product-specific rules of origin (PSR) database |
| Single-page dashboard | Multi-page tool with history, bulk, reports |

**To get a trade specialist to pay $49/mo:**
1. Must have REAL HS code database (not 10 samples)
2. Must have ACCURATE duty rates (not hardcoded)
3. Must have FTA eligibility with actual rules
4. Must have binding ruling cross-reference
5. Must work for top 20 trade corridors minimum

---

## What's Currently Built

### Backend (apps/api/app/routers/hs_code.py)
- ✅ Database models: HSCode, DutyRate, FTAAgreement, FTARule, HSClassification, HSCodeSearch
- ✅ POST /classify - AI classification (DEMO: keyword matching only)
- ✅ GET /search - Search by code/description
- ✅ GET /code/{hs_code} - Get code details
- ✅ POST /calculate-duty - Calculate import duties
- ✅ GET /fta-check - FTA eligibility check
- ✅ GET /countries - List 10 supported countries
- ✅ GET /ftas - List 5 sample FTAs
- ✅ POST /save - Save classification to history
- ✅ GET /history - Get user's classification history
- ✅ DELETE /history/{id} - Delete classification
- ✅ Analytics logging for searches

### Frontend (apps/web/src/pages/tools/hs-code/HSCodeDashboard.tsx)
- ✅ Product description input with popular searches
- ✅ Import/export country selection (14 countries)
- ✅ Classification results with confidence score
- ✅ AI reasoning display
- ✅ Duty rates tab (MFN, GSP)
- ✅ FTA options tab
- ✅ Alternative codes tab
- ✅ Restrictions alerts
- ✅ Duty calculator with landed cost estimate
- ✅ Classification history sidebar
- ✅ Save/copy functionality
- ✅ Tips for better results

### Landing Page (apps/web/src/pages/tools/HSCodeFinderLanding.tsx)
- ✅ Feature cards (6 features)
- ✅ Process steps (3 steps)
- ✅ Stats display
- ✅ Pricing tiers
- ✅ FAQ section

---

## Critical Gaps (What's Missing)

### 1. ❌ REAL HS Code Database (CRITICAL)

**Current:** 10 hardcoded sample codes in SAMPLE_HS_CODES
**Required:** Complete tariff schedules

| Country | Schedule | Total Lines | Source |
|---------|----------|-------------|--------|
| USA | HTS | 18,000+ | USITC |
| EU | TARIC | 15,000+ | European Commission |
| UK | UK Tariff | 12,000+ | HMRC |
| China | CCTS | 20,000+ | China Customs |
| India | ITC-HS | 11,000+ | DGFT |

**Data Sources (Free):**
- US HTS: https://hts.usitc.gov/ (CSV download available)
- EU TARIC: https://ec.europa.eu/taxation_customs/dds2/taric/
- UN Comtrade: https://comtradeplus.un.org/

**Estimated Effort:** 40 hours (data import scripts + database population)

### 2. ❌ REAL AI Classification (CRITICAL)

**Current:** Simple keyword matching in `classify_with_ai()` function
```python
# Current (apps/api/app/routers/hs_code.py:186-262)
def classify_with_ai(description: str, import_country: str):
    # Just keyword matching - NOT real AI
    for kw in data["keywords"]:
        if kw in desc_lower:
            score += 1
```

**Required:**
- OpenAI/Claude integration with fine-tuned prompts
- Training context from:
  - WCO Explanatory Notes
  - US CBP binding rulings (CROSS database)
  - EU BTI (Binding Tariff Information)
  - Historical classification data
- Confidence calibration from real data
- Multi-language support (Chinese product names common)

**For System Architect:**
```
AI Classification Architecture:
1. Primary: GPT-4 with structured prompts
2. Context: Include HS chapter notes + GRIs (General Rules of Interpretation)
3. Fallback: Vector similarity search on HS descriptions
4. Validation: Cross-check against historical rulings
5. Learning: Store corrections for fine-tuning
```

**Estimated Effort:** 24 hours (prompt engineering + API integration)

### 3. ❌ REAL Duty Rates Database (CRITICAL)

**Current:** 8 hardcoded rates in SAMPLE_DUTY_RATES
```python
# Current (apps/api/app/routers/hs_code.py:158-174)
SAMPLE_DUTY_RATES = {
    "US": {
        "6109.10.00": {"mfn": 16.5, "gsp": 0, "fta_ca": 0, "fta_mx": 0},
        # Only 8 codes...
    }
}
```

**Required:**
- MFN (Most Favored Nation) rates for all codes
- Preferential rates by FTA
- GSP rates with country eligibility
- Section 301 additional duties (US-China)
- Section 232 duties (steel/aluminum)
- Anti-dumping duties (AD)
- Countervailing duties (CVD)
- Quota rates (in-quota vs out-quota)
- Specific rates ($/kg, $/unit)
- Compound rates (% + $/unit)

**Data Source:** US HTS General Notes contain all rate columns

**Estimated Effort:** 32 hours (parsing + database schema + import)

### 4. ❌ REAL FTA Rules of Origin (HIGH)

**Current:** Generic placeholder text
```python
# Current (apps/api/app/routers/hs_code.py:521-525)
"rules_of_origin": {
    "requirement": "Change in Tariff Classification (CTC) at 4-digit level",
    "rvc_threshold": "40% Regional Value Content",
    # Generic for all products - WRONG
}
```

**Required:**
- Product-Specific Rules (PSR) vary by HS code
- USMCA alone has 300+ pages of PSRs
- Different FTAs have different rules for same product
- De minimis exceptions
- Cumulation rules (bilateral, diagonal, full)

**Example Real PSR (USMCA Chapter 62 - Apparel):**
```
6109.10 (T-shirts): A change to headings 61.01 through 61.17 
from any heading outside that group, provided that the good 
is both cut (or knit to shape) and sewn or otherwise assembled 
in the territory of one or more of the Parties.
```

**Estimated Effort:** 40 hours (PSR database for major FTAs)

### 5. ❌ Missing Dashboard Features (MEDIUM)

| Feature | Priority | Effort |
|---------|----------|--------|
| Sidebar navigation (like other tools) | HIGH | 4 hrs |
| Bulk classification (CSV upload) | HIGH | 16 hrs |
| PDF export of classifications | MEDIUM | 8 hrs |
| Binding ruling search | HIGH | 24 hrs |
| Project/folder organization | MEDIUM | 8 hrs |
| Team sharing | LOW | 16 hrs |
| API access | LOW | 16 hrs |
| Classification comparison | MEDIUM | 8 hrs |

### 6. ❌ Missing Data Integrations (MEDIUM)

| Integration | Purpose | Effort |
|-------------|---------|--------|
| US CBP CROSS API | Binding rulings lookup | 16 hrs |
| EU TARIC API | Real-time EU rates | 8 hrs |
| WCO HS Updates | Annual code changes | 8 hrs |
| Section 301 list | China tariff exclusions | 8 hrs |
| AD/CVD database | Anti-dumping rates | 8 hrs |

### 7. ❌ Missing Compliance Features (LOW for MVP)

| Feature | Description |
|---------|-------------|
| Export controls | Check ITAR, EAR, CCL |
| Sanctions screening | OFAC, EU sanctions |
| Quota monitoring | Track quota fill rates |
| Audit trail | Track who classified what |
| Compliance reports | For customs audits |

---

## Implementation Plan

### Phase 1: Make It Real (Priority: CRITICAL)
**Goal:** Turn demo into working product with real data

**For System Architect:**
```
Data Architecture:
1. HS Code table - partitioned by country_code
2. Duty Rates table - with effective dates for historical queries  
3. FTA Rules table - keyed by fta_code + hs_code_prefix
4. Data versioning for tariff schedule updates
5. Cache layer for frequent code lookups
```

**For Senior Developer:**
```
Phase 1 Tasks (80 hours total):
[ ] Import US HTS data (18,000 codes) - 16 hrs
[ ] Import EU TARIC data (15,000 codes) - 16 hrs  
[ ] Integrate OpenAI for real AI classification - 16 hrs
[ ] Import duty rates with special programs - 16 hrs
[ ] Add sidebar navigation layout - 4 hrs
[ ] Run database migration on production - 4 hrs
[ ] Test with 100 real product descriptions - 8 hrs
```

### Phase 2: Production Polish (Priority: HIGH)
**Goal:** Features that differentiate from free tools

**For Senior Developer:**
```
Phase 2 Tasks (64 hours total):
[ ] Bulk classification (CSV upload/download) - 16 hrs
[ ] PDF export with professional formatting - 8 hrs
[ ] Binding ruling cross-reference - 24 hrs
[ ] Classification comparison tool - 8 hrs
[ ] Rate alerts (notify on changes) - 8 hrs
```

### Phase 3: Enterprise Features (Priority: MEDIUM)
**Goal:** Features for larger customers

**For Senior Developer:**
```
Phase 3 Tasks (56 hours total):
[ ] USMCA rules of origin engine - 24 hrs
[ ] RCEP rules of origin engine - 16 hrs
[ ] Team collaboration - 16 hrs
```

### Phase 4: Compliance Suite (Priority: LOW)
**Goal:** Full compliance toolkit

```
Phase 4 Tasks (40 hours):
[ ] Export controls screening (EAR/ITAR) - 16 hrs
[ ] Section 301 exclusion checker - 8 hrs
[ ] AD/CVD rate lookup - 8 hrs
[ ] Quota status monitoring - 8 hrs
```

---

## Data Sources Reference

### Free Data Sources
| Source | Data | Format | Update |
|--------|------|--------|--------|
| USITC | US HTS codes + rates | JSON/CSV | Annual + midyear |
| EC TARIC | EU codes + rates | XML/REST | Daily |
| UN Comtrade | HS concordance | CSV | Annual |
| WCO | HS nomenclature | PDF | Every 5 years |

### Commercial APIs (for real-time)
| Provider | Coverage | Cost |
|----------|----------|------|
| Avalara | 200+ countries | $$$ |
| Descartes | Global + compliance | $$$$ |
| Tarifftel | 100+ countries | $$ |

### Government APIs
| API | Data |
|-----|------|
| CBP ACE | US import data |
| CBP CROSS | Binding rulings |
| EU TARIC | European tariffs |

---

## Quick Wins (Can Ship This Week)

1. **Add Sidebar Layout** (4 hrs)
   - Match other tools (Container Tracker, LC Builder)
   - Add navigation for History, Settings, Help

2. **Import Free US HTS Data** (16 hrs)
   - Download from USITC
   - Parse and import 18,000+ codes
   - Include General Notes

3. **Integrate OpenAI** (8 hrs)
   - Replace keyword matching
   - Use GPT-4 with HS context
   - Return confidence + reasoning

4. **Fix Duty Calculator** (4 hrs)
   - Pull real MFN rates from imported data
   - Show Section 301 rates for China
   - Add GSP eligibility check

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| HS Codes in DB | 10 | 50,000+ |
| Countries with rates | 2 (demo) | 20+ |
| Classification accuracy | Unknown | 95%+ |
| FTAs with real rules | 0 | 10+ |
| Average response time | <1s | <2s |

---

## Recommendation

**Start with Phase 1 Data Import.** Without real HS codes and duty rates, this tool is just a demo. The AI classification can be improved incrementally, but the data is non-negotiable.

**Minimum for "Shippable":**
1. ✅ US HTS codes (all 18,000)
2. ✅ US MFN duty rates
3. ✅ Real AI classification (OpenAI)
4. ✅ USMCA basic eligibility
5. ✅ Save/history functionality

**Timeline:** 2-3 weeks for Phase 1 if prioritized.

---

## Appendix: Sample Real HS Code Entry

```json
{
  "hts_number": "6109.10.0012",
  "description": "T-shirts, singlets, tank tops and similar garments, knitted or crocheted: Of cotton: Men's or boys': Other",
  "unit_of_quantity": "DOZ",
  "general_rate": "16.5%",
  "special_rate": "Free (AU,BH,CA,CL,CO,IL,JO,KR,MA,MX,OM,P,PA,PE,SG)",
  "column_2_rate": "45%",
  "quota_quantity": null,
  "additional_duties": {
    "section_301": null,
    "section_232": null,
    "antidumping": null
  },
  "chapter_notes": "Note 2: The terms 'men's or boys'' or 'women's or girls'' in any heading in the tariff schedule includes garments that are identifiable as being for males or females, respectively...",
  "effective_date": "2024-01-01"
}
```

This is what each of the 18,000+ US HTS codes looks like. Currently, we have 10 simplified samples.

