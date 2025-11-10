# Implementation Status Report

## Bank Dashboard - P0 (Must-Have)

| Feature | Status | Notes |
|---------|--------|-------|
| **Roles & Approvals** | ✅ **IMPLEMENTED** | Analyst → Reviewer → Approver flow with stages, approve/reject/reopen actions |
| **Discrepancy Workflow** | ✅ **IMPLEMENTED** | Assign, status, due dates, comments, bulk resolve, audit logs |
| **Queue Operations** | ✅ **IMPLEMENTED** | UI + backend (`/bank/queue`) with tenant scoping and RBAC; actions: retry/cancel/requeue/bulk wired |
| **Client Portfolio View** | ✅ **IMPLEMENTED** | `ClientManagement` component with expandable rows showing per-client KPIs, trends, recent issues, and duplicates heatmap via `ClientDetailView` |
| **Audit Trail** | ✅ **IMPLEMENTED** | Per LC and per action (who/when/what changed), CSV exportable |
| **Notifications** | ✅ **IMPLEMENTED** | Actionable items (open item, approve, request fix), read/unread, badges |
| **RBAC** | ✅ **IMPLEMENTED** | Granular bank workflow roles (`can_act_as_workflow_stage`, `require_workflow_stage_access`) with analyst, reviewer, approver stage checks; bank_admin/bank_officer permissions enforced |

## Bank Dashboard - P1 (Important)

| Feature | Status | Notes |
|---------|--------|-------|
| **Validation Policy Surface** | ✅ **IMPLEMENTED** | `PolicySurface` component shows ruleset domain/jurisdiction/version/effective window |
| **SLA Dashboards** | ✅ **IMPLEMENTED** | UI exists (`SLADashboards.tsx`) with throughput, aging, time-to-first-review metrics. Backend API endpoints (`/bank/sla/metrics`, `/bank/sla/breaches`) implemented and wired. Calculates metrics from JobQueue, BankApproval, and DiscrepancyWorkflow tables. |
| **Bulk Jobs** | ❌ **MISSING** | Need: templated runs, scheduling, throttling, resumable batches |
| **Duplicate Detection** | ⚠️ **PARTIAL** | LC number + client name check exists (`checkDuplicate` API), but missing: content similarity, merge history |
| **Evidence Packs** | ✅ **IMPLEMENTED** | UI exists (`EvidencePacks.tsx`) with one-click PDF/ZIP generation. Backend API endpoints (`/bank/evidence-packs/sessions`, `/bank/evidence-packs/generate`) implemented and wired. Lists validation sessions from bank's tenant companies via BankTenant relationship. |
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
| **Result Lifecycle** | ✅ **IMPLEMENTED** | "Ready to submit" badge, bank submission confirmation dialog, and submission history tab added to `ExporterResults.tsx` and `ImportResults.tsx` |
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
- Bank: Roles & Approvals, Discrepancy Workflow, Audit Trail, Notifications, Policy Surface, Queue Operations, Client Portfolio (with KPIs/trends/heatmap), RBAC (granular roles)
- SME: LC Workspace, Drafts & Amendments, Notifications, Result Lifecycle (ready to submit badge, bank submission confirmation, history per LC)
- Cross-cutting: Basic search/filters, responsive components, Security (2FA, idle timeout), Data Retention

### ⚠️ Partially Implemented (Needs Completion)
- **Bank**: Duplicate Detection (needs merge history), API Tokens (needs bank-specific UI)
- **SME**: Duplicate Guardrails (needs linking suggestion)
- **Cross-cutting**: Search (needs saved views/deep links), Mobile (needs verification), Support (needs ticket handoff), i18n (needs verification)

### ❌ Missing (Critical Gaps - Backend APIs)
- **Bank P1**: Bulk Jobs backend integration
- **SME P1**: Templates, Company Profile, Team Roles
- **Cross-cutting P0**: (none) – all P0 backend APIs delivered (Queue Operations, Security 2FA, Data Retention)
- **Cross-cutting P1**: Environment Banner, Support ticket handoff
- **Cross-cutting P2**: Personalization, i18n hooks verification

---

## Recommended Priority Order

### Next Focus (Now that P0 backend APIs are complete)
1. **Bank P1**: Duplicate detection merge history; Bulk Jobs backend integration
2. **SME P1**: Templates, Company Profile, Team Roles
3. **Cross-cutting P1**: Environment Banner, Support ticket handoff

### Sprint 2 (Important P1)
1. **SLA Dashboards** (throughput, aging, time-to-first-review, breaches)
2. **Evidence Packs** (one-click PDF/ZIP)
3. **Templates** (LC and document templates with pre-fill)
4. **Company Profile** (compliance info, address book)

### Sprint 3 (Enhancements)
1. **Saved Views** and deep links
2. **Environment Banner** and sample data mode
3. **Personalization** (pin tabs, default landing per role)
4. **Internationalization** hooks verification

