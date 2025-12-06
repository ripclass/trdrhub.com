# Sprint 1: Ship LCopilot Core
**Goal:** Complete end-to-end LC workflow for all user types. Bank demo ready.
**Duration:** 2 weeks
**Priority Order:** Exporter → Importer → Combined → Enterprise → Bank

---

## Current State Assessment

| Dashboard | Route | Status | Issues |
|-----------|-------|--------|--------|
| **Exporter** | `/lcopilot/exporter-dashboard` | 🟡 70% | Extraction ✅, Validation ✅, Doc Gen ❓, AI ❓ |
| **Importer** | `/lcopilot/importer-dashboard` | 🔴 30% | Uses mock data, extraction broken |
| **Combined** | `/lcopilot/combined-dashboard` | 🔴 20% | Mock data only, UI shell exists |
| **Enterprise** | `/lcopilot/enterprise-dashboard` | 🟡 50% | UI exists, links to Export/Import |
| **Bank** | `/lcopilot/bank-dashboard` | 🟡 60% | Complex UI exists, needs integration |

---

## Phase 1: Exporter Dashboard (Days 1-4)
**Priority:** P0 - This is revenue-critical

### 1.1 Core Flow (Must Work)
```
Upload LC Package → OCR/Extract → Validate → View Results → Generate Docs → Download
```

#### Tasks:
- [ ] **Verify extraction pipeline**
  - `POST /upload` → S3 → DocumentProcessingService → OCR
  - Check: MT700 fields extracted correctly
  - Check: Supporting docs (Invoice, B/L, Insurance) extracted
  
- [ ] **Verify validation pipeline**
  - `POST /validate` → UCP600 rules → Crossdoc checks → AI enrichment
  - Check: Issues display with Expected/Found/Suggested Fix
  - Check: Compliance score calculated correctly
  
- [ ] **Fix Document Generation** (if broken)
  - `GET /doc-generator/generate` → Template → PDF
  - Check: Documents pre-filled from LC data
  - Check: Download works (PDF, ZIP)

- [ ] **Fix Results Export**
  - Export validation report as PDF
  - Export discrepancy list as CSV
  - Share report via link

- [ ] **Session History**
  - `GET /sessions` → List user's past validations
  - Click to view past results
  - Delete old sessions

### 1.2 AI Features (Basic Version)
- [ ] **AI Insights on Issues**
  - Show AI explanation for each discrepancy
  - Suggested resolution from AI
  
- [ ] **AI Document Summary**
  - Quick summary of LC terms
  - Key dates highlighted

### 1.3 Polish
- [ ] Fix any UI bugs in results display
- [ ] Ensure Overview/Documents/Issues/Analytics tabs work
- [ ] Mobile responsiveness check

---

## Phase 2: Importer Dashboard (Days 5-7)
**Priority:** P1 - Second user segment

### 2.1 Fix Extraction
Currently using mock data. Need to wire up real API.

#### Tasks:
- [ ] **Wire up ImportLCUpload to real API**
  - Currently at `apps/web/src/pages/ImportLCUpload.tsx`
  - Should call same extraction pipeline as exporter
  - Importer uploads: LC copy from bank, supplier docs for review
  
- [ ] **Wire up ImportResults to real API**
  - Currently at `apps/web/src/pages/ImportResults.tsx`
  - Should display real validation results
  
- [ ] **Different validation focus for Importers:**
  - Supplier document compliance check
  - Bank discrepancy response preparation
  - Payment vs shipment timing

### 2.2 Importer-Specific Features
- [ ] Supplier document vetting workflow
- [ ] Bank discrepancy response templates
- [ ] Payment authorization workflow

---

## Phase 3: Combined Dashboard (Days 8-9)
**Priority:** P2 - Users who do both export/import

### 3.1 Fix Data Fetching
Currently uses mock data (`mockKPIData`, `mockSessions`).

#### Tasks:
- [ ] **Wire up real data**
  - Fetch both export and import sessions
  - Aggregate KPIs across both
  
- [ ] **View mode toggle**
  - Switch between Export/Import/Combined views
  - Already has `ViewModeToggle` component

### 3.2 Unified Experience
- [ ] Combined session list (export + import)
- [ ] Single upload flow with type selection
- [ ] Merged analytics

---

## Phase 4: Enterprise Dashboard (Days 10-11)
**Priority:** P3 - Large companies

### 4.1 Current State
UI exists with workspace concept. Links to Export/Import dashboards.

#### Tasks:
- [ ] **Multi-workspace support**
  - Export Operations workspace
  - Import Compliance workspace
  - Treasury workspace
  
- [ ] **Team features**
  - Member list per workspace
  - Role-based access
  - Activity feed

- [ ] **Governance features**
  - Approval workflows
  - Audit trail
  - Compliance reporting

---

## Phase 5: Bank Dashboard (Days 12-14)
**Priority:** P4 - Demo waiting

### 5.1 Current State
Most complex dashboard. Many components exist but need integration.

#### Key Components:
```
BankSidebar, BankQuickStats, BulkLCUpload, ProcessingQueue, 
ResultsTable, ClientManagement, BankAnalytics, ApprovalsView,
DiscrepanciesView, PolicySurface, QueueOperationsView, 
SLADashboardsView, EvidencePacksView
```

#### Tasks:
- [ ] **Core Bank Flow**
  ```
  Upload LC Package → Process → Review Discrepancies → 
  Approve/Reject → Client Notification → Evidence Pack
  ```

- [ ] **Client Management**
  - View client submissions
  - Track per-client metrics
  - Generate client reports

- [ ] **Queue Management**
  - SLA monitoring
  - Priority queue
  - Bulk operations

- [ ] **Policy Engine**
  - Bank-specific rules
  - Risk thresholds
  - Auto-approve criteria

- [ ] **Evidence Packs**
  - Generate compliance evidence
  - Audit-ready documentation

---

## Backend API Status Check

### Extraction APIs
| Endpoint | Status | Notes |
|----------|--------|-------|
| `POST /documents/upload` | ✅ | Multi-file upload |
| `POST /documents/process` | ✅ | OCR + extraction |
| `GET /documents/{session_id}` | ✅ | Get extracted data |

### Validation APIs
| Endpoint | Status | Notes |
|----------|--------|-------|
| `POST /validate/lc/{session_id}` | ✅ | Full validation |
| `GET /validate/results/{session_id}` | ✅ | Get results |
| `GET /validate/issues/{session_id}` | ✅ | Get issue list |

### Session APIs
| Endpoint | Status | Notes |
|----------|--------|-------|
| `GET /sessions` | ✅ | List user sessions |
| `GET /sessions/{id}` | ✅ | Get session detail |
| `DELETE /sessions/{id}` | ✅ | Delete session |

### Doc Generator APIs
| Endpoint | Status | Notes |
|----------|--------|-------|
| `POST /doc-generator/generate` | ❓ | Check if working |
| `GET /doc-generator/templates` | ❓ | List templates |
| `GET /doc-generator/download/{id}` | ❓ | Download PDF |

### Bank-Specific APIs
| Endpoint | Status | Notes |
|----------|--------|-------|
| `GET /bank/queue` | ❓ | Processing queue |
| `POST /bank/approve/{id}` | ❓ | Approve submission |
| `POST /bank/reject/{id}` | ❓ | Reject submission |
| `GET /bank/clients` | ❓ | Client list |
| `GET /bank/analytics` | ❓ | Bank analytics |

---

## Test Checklist Per Dashboard

### Exporter Test Flow
1. [ ] Sign up as exporter
2. [ ] Complete onboarding
3. [ ] Upload LC package (MT700 + 3 supporting docs)
4. [ ] Wait for processing
5. [ ] View extraction results
6. [ ] View validation results
7. [ ] Navigate all tabs (Overview, Documents, Issues, Analytics)
8. [ ] Generate compliance report
9. [ ] Download report
10. [ ] View session in history
11. [ ] Delete session

### Importer Test Flow
1. [ ] Sign up as importer
2. [ ] Complete onboarding
3. [ ] Upload received LC + supplier docs
4. [ ] View extraction
5. [ ] View validation (supplier compliance focus)
6. [ ] Generate bank response
7. [ ] View history

### Bank Test Flow
1. [ ] Login as bank user
2. [ ] View processing queue
3. [ ] Open client submission
4. [ ] Review discrepancies
5. [ ] Approve/Reject with comments
6. [ ] Generate evidence pack
7. [ ] View client analytics
8. [ ] Check SLA dashboard

---

## Daily Schedule

| Day | Focus | Deliverable |
|-----|-------|-------------|
| 1-2 | Exporter core flow | Upload → Extract → Validate works |
| 3-4 | Exporter polish | Doc Gen, Export, AI insights |
| 5-6 | Importer fix | Wire to real APIs, fix extraction |
| 7 | Importer polish | Import-specific features |
| 8-9 | Combined dashboard | Wire real data, view toggle |
| 10-11 | Enterprise dashboard | Multi-workspace, teams |
| 12-13 | Bank dashboard | Core flow, queue, approvals |
| 14 | Bank polish | Evidence packs, demo prep |

---

## Definition of Done

### Per Dashboard:
- [ ] Core flow works end-to-end
- [ ] No console errors
- [ ] Loading states work
- [ ] Error states handled
- [ ] Mobile responsive (basic)
- [ ] No mock data in production

### Sprint Complete:
- [ ] Any user type can sign up
- [ ] Onboarding routes to correct dashboard
- [ ] Each dashboard type works independently
- [ ] Bank demo ready
- [ ] No critical bugs

---

## Notes

### Quick Wins (Do First)
1. Verify exporter extraction/validation still works
2. Check if doc generator endpoints exist
3. Test session history

### Blockers to Watch
1. Importer extraction sharing same pipeline?
2. Bank auth separate from main auth?
3. Doc generator templates exist?

### Out of Scope (Sprint 2+)
- Multi-AI provider support
- Advanced bank features (bulk processing, SLA automation)
- White-label/custom branding
- API access for customers

