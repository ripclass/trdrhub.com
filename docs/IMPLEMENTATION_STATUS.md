# Implementation Status Report

## Bank Dashboard - P0 (Must-Have)

| Feature | Status | Notes |
|---------|--------|-------|
| **Roles & Approvals** | ✅ **IMPLEMENTED** | Analyst → Reviewer → Approver flow with stages, approve/reject/reopen actions |
| **Discrepancy Workflow** | ✅ **IMPLEMENTED** | Assign, status, due dates, comments, bulk resolve, audit logs |
| **Queue Operations** | ✅ **IMPLEMENTED** | UI + backend (`/bank/queue`) with tenant scoping and RBAC; actions: retry/cancel/requeue/bulk wired |
| **Client Portfolio View** | ⚠️ **PARTIAL** | `ClientManagement` component exists with basic stats, but missing: per-client KPIs, trends, recent issues, duplicates heatmap |
| **Audit Trail** | ✅ **IMPLEMENTED** | Per LC and per action (who/when/what changed), CSV exportable |
| **Notifications** | ✅ **IMPLEMENTED** | Actionable items (open item, approve, request fix), read/unread, badges |
| **RBAC** | ⚠️ **PARTIAL** | Basic roles exist (`require_bank_or_admin`), but granular bank roles (Admin, Approver, Reviewer, Analyst, Read-only) need verification |

## Bank Dashboard - P1 (Important)

| Feature | Status | Notes |
|---------|--------|-------|
| **Validation Policy Surface** | ✅ **IMPLEMENTED** | `PolicySurface` component shows ruleset domain/jurisdiction/version/effective window |
| **SLA Dashboards** | ⚠️ **PARTIAL** | UI exists (`SLADashboards.tsx`) with throughput, aging, time-to-first-review metrics. Backend integration needs verification |
| **Bulk Jobs** | ❌ **MISSING** | Need: templated runs, scheduling, throttling, resumable batches |
| **Duplicate Detection** | ⚠️ **PARTIAL** | LC number + client name check exists (`checkDuplicate` API), but missing: content similarity, merge history |
| **Evidence Packs** | ⚠️ **PARTIAL** | UI exists (`EvidencePacks.tsx`) with one-click PDF/ZIP generation. Backend API integration needs verification |
| **API Tokens & Webhooks** | ⚠️ **PARTIAL** | Exists in Admin Console (`partners-webhooks`), but NOT in Bank Dashboard. Need: bank-specific API tokens with limited scope |

## Bank Dashboard - P2 (Nice-to-Have)

| Feature | Status | Notes |
|---------|--------|-------|
| **Saved Searches & Shared Views** | ❌ **MISSING** | No saved views or subscriptions found |
| **Health/Latency Banner** | ❌ **MISSING** | No transparency banner (green/amber/red) |
| **In-app Tutorials** | ❌ **MISSING** | No tutorials or keyboard shortcuts |
| **Multi-org Switching** | ❌ **MISSING** | No bank groups/regions switching |

---

## SME Dashboard (Importer/Exporter) - P0 (Must-Have)

| Feature | Status | Notes |
|---------|--------|-------|
| **LC Workspace** | ✅ **IMPLEMENTED** | Checklist of required docs per LC, status per doc, missing items, re-upload loop |
| **Drafts & Amendments** | ✅ **IMPLEMENTED** | Explicit tabs, versioning, diff of amendments, link to prior results |
| **Discrepancy Guidance** | ✅ **IMPLEMENTED** | `DiscrepancyGuidance` component with actionable fixes, before/after examples, common mistakes, re-validate, and upload fixed documents. Used in `ExporterResults.tsx` and `ImportResults.tsx` |
| **Result Lifecycle** | ⚠️ **PARTIAL** | `ready_for_submission` status exists, but missing: "ready to submit" badge, bank submission confirmation, history per LC |
| **Notifications** | ✅ **IMPLEMENTED** | What to fix, by when; actionable notifications |

## SME Dashboard - P1 (Important)

| Feature | Status | Notes |
|---------|--------|-------|
| **Templates** | ❌ **MISSING** | Mentioned in pricing but NO actual feature. Need: LC and document templates, pre-fill common fields |
| **Company Profile** | ❌ **MISSING** | Need: compliance info (TIN/VAT/etc.), default consignee/shipper, address book |
| **Team Roles** | ❌ **MISSING** | Need: owner, editor, viewer; sharing LC workspace with auditors |
| **Duplicate Guardrails** | ⚠️ **PARTIAL** | Warn on re-use of LC number exists, but missing: suggest linking to existing |

## SME Dashboard - P2 (Nice-to-Have)

| Feature | Status | Notes |
|---------|--------|-------|
| **AI Assistance** | ❌ **MISSING** | No generate cover letters, infer fields, translate descriptions |
| **Content Library** | ❌ **MISSING** | No reuse of past descriptions, HS codes, ports |
| **Shipment Timeline** | ❌ **MISSING** | No milestones with reminders |

---

## Cross-Cutting Features - P0 (Must-Have)

| Feature | Status | Notes |
|---------|--------|-------|
| **Search & Filters** | ⚠️ **PARTIAL** | Filters exist (`AdvancedFilters`), but missing: saved views, deep links need verification, export CSV/PDF |
| **Mobile-Friendly** | ⚠️ **PARTIAL** | Responsive components exist (`useIsMobile`, `ResponsiveContainer`), but key flows need verification |
| **Security** | ✅ **IMPLEMENTED** | 2FA prompts in `BankLogin.tsx`, idle timeout in `BankAuthProvider`; backend endpoints (`/bank/auth/request-2fa`, `/verify-2fa`) feature-flagged |
| **Data Retention** | ✅ **IMPLEMENTED** | Bank compliance endpoints (`/bank/compliance/retention-policy`, `/export`, `/erase`) with tenant scoping; UI wired |

## Cross-Cutting Features - P1 (Important)

| Feature | Status | Notes |
|---------|--------|-------|
| **Environment Banner** | ❌ **MISSING** | No Sandbox/Production banner or sample data mode |
| **Support** | ⚠️ **PARTIAL** | Help panels exist with email links, but missing: in-app help, ticket handoff with prefilled context |

## Cross-Cutting Features - P2 (Nice-to-Have)

| Feature | Status | Notes |
|---------|--------|-------|
| **Personalization** | ❌ **MISSING** | No pin tabs, default landing per role |
| **Internationalization** | ⚠️ **PARTIAL** | i18n infrastructure exists (`i18n/index.ts`, `TranslationManager`), but hooks need verification |

---

## Summary

### ✅ Fully Implemented (P0)
- Bank: Roles & Approvals, Discrepancy Workflow, Audit Trail, Notifications, Policy Surface
- SME: LC Workspace, Drafts & Amendments, Notifications
- Cross-cutting: Basic search/filters, responsive components

### ⚠️ Partially Implemented (Needs Completion)
- **Bank**: Client Portfolio (needs KPIs/trends/heatmap), RBAC (needs granular roles), Duplicate Detection (needs merge history), API Tokens (needs bank-specific UI)
- **SME**: Result Lifecycle (needs bank submission confirmation/history), Duplicate Guardrails (needs linking suggestion)
- **Cross-cutting**: Search (needs saved views/deep links), Mobile (needs verification), Security (needs enforcement), Data Retention (needs UI), Support (needs ticket handoff), i18n (needs verification)

### ❌ Missing (Critical Gaps - Backend APIs)
- **Bank P1**: Bulk Jobs backend integration
- **SME P1**: Templates, Company Profile, Team Roles
- **Cross-cutting P0**: (none) – all P0 backend APIs delivered (Queue Operations, Security 2FA, Data Retention)
- **Cross-cutting P1**: Environment Banner, Support ticket handoff
- **Cross-cutting P2**: Personalization, i18n hooks verification

---

## Recommended Priority Order

### Next Focus (Now that P0 backend APIs are complete)
1. **Bank P0 enhancements**: Client Portfolio KPIs/trends/duplicates heatmap; verify granular RBAC roles (Admin/Approver/Reviewer/Analyst/Read-only)
2. **Bank P1**: SLA Dashboards backend verification; Evidence Packs backend integration; Duplicate detection merge history
3. **SME P1**: Templates, Company Profile, Team Roles
4. **Cross-cutting P1**: Environment Banner, Support ticket handoff

### Sprint 2 (Important P1)
1. **SLA Dashboards** (throughput, aging, time-to-first-review, breaches)
2. **Evidence Packs** (one-click PDF/ZIP)
3. **Templates** (LC and document templates with pre-fill)
4. **Company Profile** (compliance info, address book)

### Sprint 3 (Enhancements)
1. **Client Portfolio** enhancements (KPIs, trends, heatmap)
2. **Result Lifecycle** enhancements (bank submission confirmation, history)
3. **Saved Views** and deep links
4. **Environment Banner** and sample data mode

