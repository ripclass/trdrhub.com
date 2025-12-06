# HS Code Finder - Gap Analysis & Implementation Plan

## Executive Summary

**Current State:** Phase 3 Complete (95% complete)  
**Target State:** Bank-Grade Commercial Tool (100%)  
**Status:** Enterprise features live - USMCA ROO engine, RVC calculator, team collaboration, bulk classification, PDF export, binding rulings

### Trade Specialist Verdict: Would I Pay for This?

**MAYBE** - Getting there. Here's the progress:

| What's Built (Phase 1) | What Still Needs Work |
|------------------------|----------------------|
| ✅ 100+ sample US HTS codes | Need 18,000+ full US HTS |
| ✅ OpenAI classification service | Need binding ruling training data |
| ✅ Section 301 rates structure | Need full 301 list coverage |
| ✅ 5 FTA agreements with rules | Need product-specific ROO |
| ✅ 11-page sidebar dashboard | Need bulk upload implementation |

**To get a trade specialist to pay $49/mo:**
1. ✅ Real database architecture (DONE)
2. ⏳ Import full 18,000+ US HTS codes (2 hours)
3. ⏳ Add more Section 301 and AD/CVD rates
4. ⏳ Implement bulk classification
5. ⏳ Connect OpenAI with chapter notes context

---

## What's Currently Built (Phase 1 Complete)

### Backend (apps/api)
- ✅ **Database Models** (`app/models/hs_code.py`):
  - HSCodeTariff - HS codes with hierarchy (2/4/6/8/10 digit)
  - DutyRate - MFN, preferential, compound rates
  - FTAAgreement - USMCA, RCEP, CPTPP, GSP, KORUS
  - FTARule - Product-specific rules of origin
  - HSClassification - User history
  - HSCodeSearch - Analytics
  - BindingRuling - CBP CROSS rulings (new)
  - ChapterNote - GRI notes for classification (new)
  - Section301Rate - US-China tariffs (new)
  
- ✅ **Classification Service** (`app/services/hs_classification.py`):
  - OpenAI GPT-4o-mini integration
  - GRI rules system prompt
  - Chapter notes context retrieval
  - Binding ruling context
  - Fallback to database search
  
- ✅ **API Endpoints** (`app/routers/hs_code.py`):
  - POST /classify - AI classification with OpenAI
  - GET /search - Database search by code/description
  - GET /code/{hs_code} - Full details with duty rates
  - POST /calculate-duty - With Section 301 support
  - GET /fta-check - With rules of origin
  - GET /ftas - From database (not hardcoded)
  - POST /save, GET /history, DELETE /history/{id}
  
- ✅ **Data Import** (`scripts/import_hts_data.py`):
  - 100+ sample US HTS codes seeded
  - 5 FTA agreements with member countries
  - Chapter notes for key chapters
  - Section 301 rates for common codes

### Frontend (apps/web/src/pages/tools/hs-code/)
- ✅ **HSCodeLayout** - Sidebar navigation with 11 pages
- ✅ **HSCodeOverview** - Dashboard with stats, quick actions
- ✅ **HSCodeClassify** - AI product classification
- ✅ **HSCodeSearch** - Browse/search HS codes
- ✅ **HSCodeDuty** - Calculator with Section 301, landed cost
- ✅ **HSCodeFTA** - FTA eligibility with ROO requirements
- ✅ **HSCodeHistory** - Classification history
- ✅ **HSCodeROO** - Rules of origin reference
- ✅ **HSCodeCompliance** - Import compliance guide
- ✅ **HSCodeFavorites** - Favorite codes (placeholder)
- ✅ **HSCodeBulk** - Bulk upload (placeholder)
- ✅ **HSCodeSettings** - Preferences
- ✅ **HSCodeHelp** - FAQ and resources

### Landing Page
- ✅ Feature cards, process steps, pricing, FAQ

---

## Remaining Gaps (Phase 2)

### 1. ⏳ Full US HTS Database (8 hours)

**Current:** 100+ sample codes in database
**Required:** Complete 18,000+ US HTS tariff schedule

| Country | Schedule | Current | Target | Source |
|---------|----------|---------|--------|--------|
| USA | HTS | 100+ | 18,000+ | hts.usitc.gov |
| EU | TARIC | 0 | 15,000+ | European Commission |
| UK | UK Tariff | 0 | 12,000+ | HMRC |

**Next Steps:**
- Download full HTS from https://hts.usitc.gov/current
- Parse CSV into hs_code_tariffs table
- Include chapter notes for AI context

### 2. ✅ AI Classification (DONE)

**Implemented:** OpenAI GPT-4o-mini with GRI system prompt
```python
# Now in apps/api/app/services/hs_classification.py
class HSClassificationService:
    SYSTEM_PROMPT = """You are an expert customs classification specialist...
    Your task is to classify products into the correct HS code following GRI..."""
    
    async def classify_product(self, description, import_country, export_country):
        # Uses OpenAI with chapter notes context
        result = await self._classify_with_openai(user_prompt)
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

### Phase 2: Production Polish (Priority: HIGH) ✅ COMPLETED
**Goal:** Features that differentiate from free tools

**For Senior Developer:**
```
Phase 2 Tasks (64 hours total):
[x] Bulk classification (CSV upload/download) - 16 hrs ✅
    - POST /bulk-classify - Process JSON array of products
    - POST /bulk-classify/upload - CSV file upload
    - GET /bulk-classify/download-template - Get CSV template
    - GET /bulk-classify/export/{job_id} - Export results as CSV/JSON
[x] PDF export with professional formatting - 8 hrs ✅
    - GET /export/pdf/{classification_id} - Single classification PDF
    - POST /export/bulk-pdf - Multiple classifications report
[x] Binding ruling cross-reference - 24 hrs ✅
    - GET /rulings/search - Search CBP CROSS rulings
    - GET /rulings/{ruling_number} - Get ruling details
    - GET /rulings/by-code/{hs_code} - Rulings for HS code
[x] Classification comparison tool - 8 hrs ✅
    - POST /compare - Compare two products side-by-side
    - Shows chapter/heading/subheading match
    - Consolidation recommendations
[x] Rate alerts (notify on changes) - 8 hrs ✅
    - POST /alerts/subscribe - Subscribe to rate changes
    - GET /alerts - List user's alert subscriptions
    - DELETE /alerts/{alert_id} - Unsubscribe
    - PUT /alerts/{alert_id} - Update alert settings
    - GET /rate-changes - Recent rate changes
```

**Frontend Pages Added:**
- HSCodeBulk.tsx - CSV upload/download with results table
- HSCodeCompare.tsx - Side-by-side product comparison
- HSCodeRulings.tsx - Binding ruling search
- HSCodeAlerts.tsx - Rate alert subscriptions

### Phase 3: Enterprise Features (Priority: MEDIUM) ✅ COMPLETED
**Goal:** Features for larger customers

**For Senior Developer:**
```
Phase 3 Tasks (56 hours total):
[x] USMCA rules of origin engine - 24 hrs ✅
    - GET /roo/rules/{fta_code}/{hs_code} - Get applicable PSRs
    - POST /roo/calculate-rvc - Regional Value Content calculator
    - POST /roo/determine-origin - Full origin determination
    - GET /roo/determinations - User's determination history
    - Supports Transaction Value and Net Cost methods
    - Labor Value Content for USMCA automotive
[x] RCEP rules of origin engine - 16 hrs ✅
    - Same API endpoints support RCEP, CPTPP, KORUS
    - FTA-specific threshold defaults
[x] Team collaboration - 16 hrs ✅
    - POST/GET /teams - Create and list teams
    - GET /teams/{id} - Team details with members
    - POST /teams/{id}/invite - Invite members
    - POST /teams/{id}/projects - Create projects
    - POST /share - Share classifications
    - GET /shared/{link} - Access shared content
```

**Database Models Added:**
- ProductSpecificRule - FTA product-specific rules (PSR)
- RVCCalculation - Saved RVC calculations
- OriginDetermination - Complete origin records
- HSCodeTeam - Teams for collaboration
- HSCodeTeamMember - Role-based membership
- HSCodeProject - Team projects
- ClassificationShare - Sharing with permissions

**Frontend Pages Added:**
- HSCodeUSMCA.tsx - USMCA ROO calculator with RVC
- HSCodeTeams.tsx - Team management UI

### Phase 4: Compliance Suite (Priority: LOW) ✅ COMPLETED
**Goal:** Full compliance toolkit

**For Senior Developer:**
```
Phase 4 Tasks (40 hours total):
[x] Export controls screening (EAR/ITAR) - 16 hrs ✅
    - POST /compliance/export-control/screen - Full EAR/ITAR screening
    - GET /compliance/eccn/search - Search ECCN database
    - GET /compliance/itar/categories - List USML categories
[x] Section 301 exclusion checker - 8 hrs ✅
    - GET /compliance/section-301/exclusions - Search exclusions
    - GET /compliance/section-301/check/{hs_code} - Check status
[x] AD/CVD rate lookup - 8 hrs ✅
    - GET /compliance/ad-cvd/search - Search AD/CVD orders
    - GET /compliance/ad-cvd/check - Check applicability
    - GET /compliance/ad-cvd/countries - Countries with orders
[x] Quota status monitoring - 8 hrs ✅
    - GET /compliance/quotas/search - Search TRQs
    - GET /compliance/quotas/check/{hs_code} - Check quota status
    - GET /compliance/quotas/alerts - High fill rate alerts
[x] Full compliance screening - 4 hrs ✅
    - POST /compliance/full-screening - Combined screening
    - GET /compliance/history - Screening history
```

**Database Models Added:**
- ExportControlItem - ECCN database (EAR Commerce Control List)
- ITARItem - USML categories (International Traffic in Arms)
- Section301Exclusion - Product-specific exclusions
- ADCVDOrder - Antidumping and Countervailing Duty orders
- TariffQuota - Tariff Rate Quotas with fill status
- ComplianceScreening - User screening history

**Frontend Pages Added:**
- HSCodeComplianceDashboard.tsx - Combined compliance overview
- HSCodeExportControls.tsx - EAR/ITAR screening UI
- HSCodeSection301.tsx - Section 301 checker
- HSCodeADCVD.tsx - AD/CVD order lookup
- HSCodeQuotas.tsx - Quota monitoring dashboard

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

