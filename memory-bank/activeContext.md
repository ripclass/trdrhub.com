# Active Context - July 17, 2026

## Current Focus

Proofline — Verified Trade Clearance has been implemented inside the existing
TRDR Hub monorepo. The implementation is complete locally and committed through
`2aecf6d0`. It has not been pushed or deployed.

Proofline is a `TradeCase` orchestration layer. It reuses existing TRDR Hub
authentication, company tenancy, documents/S3/OCR, LCopilot, sanctions, CBAM,
EUDR, Stripe, notifications, audit, review, and report infrastructure. RulHub
and EIN remain external service boundaries.

## Proofline Delivered

- Payment-arrangement-first intake with ten supported arrangements.
- LC cases reuse LCopilot structured results and deterministic validation.
- Open-account cases evaluate purchase order, contract, invoice approval,
  shipment, payment terms, risk coverage, deductions, and expected-payment evidence.
- Tenant-safe case, party, document, check, finding, remediation, decision,
  event, buyer-requirement, package, and voluntary-outcome models.
- Immutable document versions and correction rounds; originals are preserved.
- Applicable-only sanctions, CBAM, EUDR, RulHub, EIN, buyer-policy, document,
  cross-document, LCopilot, and open-account modules.
- Fail-closed external integrations: unavailable verification never becomes Clear.
- Unified Expected/Found/SuggestedFix-compatible findings with provenance.
- Customer case workspace, staged intake, Tools placement, analyst queue/detail,
  correction flow, reviewer overrides, and reviewer-approved reports.
- Database-backed packages, existing Stripe Checkout/webhook reuse, and configurable
  LCopilot credit period/percentage.
- Customer milestone notifications, privacy-bounded admin metrics, and optional
  post-report outcome feedback labelled as unvalidated customer reporting.
- Backend/frontend feature flags and setup/runbook documentation.

## Verification Record

- Proofline backend: 108 passed across 25 test files.
- Existing LCopilot/crossdoc/Stripe/sanctions/readiness regressions: 58 passed.
- Proofline frontend: 18 passed across 11 files.
- Existing LCopilot results mapper: 24 passed.
- Production Vite build: passed; 3,260 modules transformed.
- Python compile/import: passed.
- Alembic: one head, `20260716_add_proofline_outcomes`.
- New Proofline outcome revision offline render: passed.
- Full TypeScript baseline still fails elsewhere with 954 diagnostic lines;
  changed Proofline files have zero diagnostics.
- Legacy `ExporterResults.test.tsx` is stale against the current unchanged UI
  (47/49 failures). `ExporterResults.tsx` and that test were not modified.
- ESLint cannot start because the repository has no ESLint configuration.
- Full Alembic offline rendering is blocked by historical seed migration
  `20250916_170100_seed_default_companies.py`, which is not offline-safe.
- In-app browser smoke verification was blocked by a local browser-runtime kernel
  asset error; the temporary Vite server was stopped.
- `git diff --check` and secret-pattern scan passed.

## Deployment / Operations Next Steps

1. Review `docs/PROOFLINE_SETUP.md` and the repository audit before rollout.
2. Run `alembic upgrade head` against the target database.
3. Set `PROOFLINE_ENABLED` and `VITE_PROOFLINE_ENABLED` consistently.
4. Keep checkout disabled until Stripe keys/webhook and package records are verified.
5. Enable EIN/RulHub only with real production credentials and verified contracts.
6. Add a deployed durable worker before unattended high-volume case processing.
7. Vercel CLI is not installed; install with `npm i -g vercel` before Vercel env,
   deployment, or log operations.

## Key References

- Setup: `docs/PROOFLINE_SETUP.md`
- Audit/verification: `docs/audits/2026-07-16-proofline-repository-audit.md`
- Design: `docs/superpowers/specs/2026-07-16-proofline-design.md`
- Plan: `docs/superpowers/plans/2026-07-16-proofline-internal-alpha.md`
- Final local commit: `2aecf6d0`

---

## Historical Context (December 2024)

## Current Focus
LCopilot V1 Enhancement - All Phases Complete

## Recent Work

### Phase 2: V1 Tab Cleanup (COMPLETED)
Streamlined UI from 7 tabs to 4 tabs, merged related functionality.

**Tab Structure Changes:**
- **Overview** - Now includes Analytics progress bars (extraction, compliance, customs readiness)
- **Documents** - Now has "View Details" button opening DocumentDetailsDrawer
- **Issues** - Unchanged (working well)
- **Customs Pack** - Now includes Submission History card

**Removed Tabs:**
- Extracted Data - Merged into Documents via drawer
- Submission History - Merged into Customs Pack
- Analytics - Merged into Overview with progress bars

**Files Modified:**
- `apps/web/src/components/lcopilot/dashboardTabs.ts` - Reduced from 7 to 4 tabs
- `apps/web/src/components/lcopilot/DocumentDetailsDrawer.tsx` (NEW) - Drawer for extracted data
- `apps/web/src/pages/ExporterResults.tsx` - Updated TabsList, added drawer, enhanced Overview

### Phase 3: 47A Parser Debug (COMPLETED)
Fixed 47A Additional Conditions extraction issues across multiple extraction pipelines.

**Root Causes Found:**
1. AI extractors (primary path) didn't include `additional_conditions` in their prompts
2. Parser patterns were too restrictive for some LC formats
3. `structured_lc_builder.py` only looked for `clauses` key, not `additional_conditions`

**Files Modified:**
- `apps/api/app/services/extraction/clauses_47a_parser.py` - Added 7 patterns (up from 4), enhanced diagnostic logging
- `apps/api/app/services/extraction/ai_lc_extractor.py` - Added `additional_conditions` to extraction prompt
- `apps/api/app/services/extraction/ensemble_extractor.py` - Added `additional_conditions` to extraction prompt  
- `apps/api/app/services/extraction/structured_lc_builder.py` - Now checks `additional_conditions`, `clauses`, and `clauses_47a`
- `apps/api/app/routers/validate.py` - Enhanced 47A debug logging

### Phase 1: Contract Validation Layer (COMPLETED)
Implemented Output-First validation layer.

**Files Created/Modified:**
- `apps/api/app/services/validation/response_contract_validator.py` (NEW)
- `apps/api/app/services/validation/__init__.py` (updated exports)
- `apps/api/app/routers/validate.py` (added validation call)
- `apps/web/src/types/lcopilot.ts` (added ContractWarning types)
- `apps/web/src/lib/exporter/resultsMapper.ts` (extract warnings from response)
- `apps/web/src/pages/ExporterResults.tsx` (Alert component in Overview)

## Next Steps
All requested phases complete. Potential follow-ups:
- Test with real LC documents to verify 47A extraction
- Monitor contract warnings in production
- Consider adding more advanced analytics charts

## Architecture Notes

### V1 Tab Structure (Post-Cleanup)
```
┌──────────────────────────────────────────────────────────────┐
│ TABS: [ Overview ] [ Documents (N) ] [ Issues (N) ] [ Customs Pack ]
└──────────────────────────────────────────────────────────────┘

Overview:
├── Contract Warnings Alert (if any)
├── Verdict Card (Pass/Fail/Fix Required)
├── Quick Stats Row: [N docs] [N issues] [N critical] [time]
├── Export Document Statistics Card
└── Analytics Summary (2 cards with progress bars)

Documents:
├── Document cards with status badges
├── "View Details" button → Opens DocumentDetailsDrawer
└── LC extraction shown inline for letter_of_credit documents

Issues:
├── Severity tabs: All | Critical | Major | Minor
└── Issue cards with full detail

Customs Pack:
├── Status/Readiness/Actions
├── Manifest Card
└── Submission History Card (moved from separate tab)
```

### DocumentDetailsDrawer Features
- Status badges (source format, eBL, OCR confidence)
- Grouped fields: Identification, Dates, Parties, Locations, Other
- Raw JSON toggle with copy button
- Automatic field name humanization

### 47A Extraction Flow
```
OCR Text → AI Extractor → additional_conditions array
              ↓                    ↓
         Regex Parser → clauses_47a_parser.py
              ↓                    ↓
       structured_lc_builder → lc_structured.additional_conditions
              ↓
       _build_lc_baseline_from_context → baseline._conditions_list
              ↓
       Contract Validator → Warning if empty
```

### Contract Validation Flow
```
Backend Processing → Contract Validation → Response
                           ↓
                    _contract_warnings[]
                           ↓
                    Frontend mappers
                           ↓
                    Overview Alert UI
```
