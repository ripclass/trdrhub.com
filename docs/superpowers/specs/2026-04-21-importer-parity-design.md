# Importer parity with exporter — design

- **Date:** 2026-04-21
- **Status:** Approved, ready for implementation planning
- **Owner:** TRDR Hub / LCopilot
- **Supersedes:** N/A (first importer-parity design doc)

## Context

The LCopilot exporter flow has been heavily refactored over the past 3-4 months — AI-first extraction, inline ExtractionReview, LC intake card, sessionStorage persistence, Zod runtime validation, 4-tab results shell, `resultsMapper` normalization, and the new validation spine (AI Examiner → arithmetic backstop → RulHub → Opus veto).

The importer flow was wired before that refactor and has drifted. Audit findings:

- Backend is already unified — both sides hit the same `/api/validate` endpoint and the same extraction/validation pipelines. No legacy OCR-first code path exists in the backend.
- Frontend has diverged significantly. `ImportLCUpload.tsx` is ~40% the size of `ExportLCUpload.tsx` and is missing ExtractionReview, LC intake card, sessionStorage persistence, Zod validation, and modern results shaping. UI still references "OCR" language.
- `ImportResults.tsx` uses local `transformApiToSupplierFormat` / `transformApiToDraftFormat` transforms and mock data structures instead of the shared `resultsMapper`.
- `ImporterDashboardV2.tsx` has 14 sections, some stubbed (notifications is an empty array), sidebar is heavy.
- Three importer-specific backend endpoints exist but are partially implemented: `supplier-fix-pack` (S3 upload TODO), `notify-supplier` (stub), `bank-precheck` (stub).

Import LC and Export LC are genuinely different trade-finance workflows, but the **internal plumbing** (extraction, validation, review UI primitives, data normalization) should be identical. This design scopes the work to bring importer to parity on plumbing while respecting the workflow differences.

## Goals

1. Importer frontend uses the same modern plumbing as exporter (ExtractionReview, intake card, sessionStorage, Zod, `resultsMapper`, tab shell).
2. Importer supports two distinct workflows (Moment 1: Draft LC Risk Analysis, Moment 2: Supplier Document Review) as first-class entry points.
3. Importer-specific post-validation actions (amendment request, fix-pack, notify-supplier, bank-precheck) are implemented end-to-end, not stubbed.
4. Both importer and exporter dashboards have a slim, identical-skeleton sidebar and **actually update** when a new validation completes (verified by automated smoke, not just "the code calls the endpoint").
5. No regression to the live exporter golden path at any point during the refactor.

## Non-goals (explicitly deferred)

- Linking Moment 1 and Moment 2 sessions (decision: independent sessions — protects billing clarity and avoids stale-LC validation).
- Accept-with-waiver or formal rejection actions (bank-facing, wait for traction data).
- Customs pack for importer (exporter-only today; separate scoping later).
- Rulhub-side fixes (separate workspace).
- AI Examiner prompt tuning (unrelated).
- Importer analytics beyond the dashboard stats strip.

## Key decisions

| Decision | Choice | Rationale |
|---|---|---|
| Session state model | Independent — no cross-session linkage | Per-session billing clarity; LC amendments between Moment 1 and Moment 2 make linkage dangerous (stale-LC validation); matches exporter's model. |
| Two-moment separation | Two sidebar items + two routes | Names the intent, zero ambiguity, one click from anywhere. |
| Shared home | `apps/web/src/components/lcopilot/` | Single canonical location for LC-validation UI primitives used by both dashboards. |
| Execution order | Extract-first (exporter refactor → importer build) | Guarantees shared-component consolidation happens; avoids the drift trap that produced the current stale importer. |
| `workflow_type` on `ValidationSession` | Three enum values: `exporter_presentation`, `importer_draft_lc`, `importer_supplier_docs` | Single field disambiguates the three flows without proliferating endpoints. |
| Sidebar size | 4 items (exporter) / 5 items (importer) — identical skeleton | Matches the "destinations not escape hatches" principle. |
| Reviews page | Kept at `/reviews` but removed from sidebar | 95% of users want latest (on dashboard); 5% need old sessions — reached via "View all →" link. |

## Architecture

### The two workflows (importer)

**Moment 1 — Draft LC Risk Analysis.** Importer uploads a draft LC their bank has proposed. Engine runs full extraction + validation, producing a findings set framed as *risks and unusual terms* the importer should push back on. Typical action: generate an amendment request PDF to send to the issuing bank.

**Moment 2 — Supplier Document Review.** Importer uploads the issued LC + shipping documents received from the exporter. Engine runs the same extraction + validation, producing discrepancies between the supplier's documents and the LC terms. Typical actions: generate supplier fix-pack, email the supplier, run bank-precheck before authorizing payment.

### Unified backend, branched frontend

- Extraction pipeline: identical for all three `workflow_type` values (multimodal → SWIFT → ai_lc_extractor → ai_first_extractor).
- Validation pipeline: identical (AI Examiner → arithmetic → RulHub → Opus veto).
- The `workflow_type` value flows through to `structured_result.meta.workflow_type` and drives **UI copy + post-validation action palette only**.

### Sidebar after refactor (both identical skeleton)

| Exporter | Importer |
|---|---|
| Dashboard | Dashboard |
| Upload *(renamed from "New Validation")* | Draft LC Review |
| — | Supplier Doc Review |
| Billing | Billing |
| Settings | Settings |

Help → top-bar. Notifications → top-bar bell. Old sidebar item "Validations" (Clock icon, dead page) → deleted; reachable page stays at `/reviews`.

### Dashboard home (both identical)

```
Stats strip (reviews this month · avg verdict · attention needed)
Start New (1 CTA exporter / 2 CTAs importer)
Recent Activity (last 10 sessions with type badge) + View all → link
Quota banner (conditional)
```

## Phase 1 — Shared component extraction

Pure refactor of exporter into shared location. Zero behavior change.

**Home:** `apps/web/src/components/lcopilot/`

**Pieces to extract:**

| Piece | From | To |
|---|---|---|
| `ExtractionReview` | `pages/ExportLCUpload.tsx` co-located | `components/lcopilot/ExtractionReview/` |
| `LcIntakeCard` | inline in `ExportLCUpload.tsx` | `components/lcopilot/LcIntakeCard.tsx` |
| `useExtractionPayloadStore` (sessionStorage helper) | inline in `ExportLCUpload.tsx` | `hooks/use-extraction-payload-store.ts` |
| `parseExtractionResponse` (Zod validator) | `hooks/use-lcopilot.ts` | stays there, unchanged — already shared |
| `resultsMapper.ts` | `lib/exporter/resultsMapper.ts` | `lib/lcopilot/resultsMapper.ts` |
| Tab shell + `VerdictTab`, `DocumentsTab`, `FindingsTab`, `HistoryTab` | `pages/exporter/results/tabs/` | `components/lcopilot/results/tabs/` |
| `PreparationGuide` | exporter-only | `components/lcopilot/PreparationGuide.tsx` |
| `ReviewsTable` (if exists; else build fresh in Phase 4) | various | `components/lcopilot/ReviewsTable.tsx` |

**Rules:**
- One commit per piece. File move + import rewrites + rename of `Exporter*` → neutral names.
- No new props, no feature adds, no styling tweaks.
- Playwright regression on IDEAL SAMPLE before AND after each commit. DOM snapshot + network requests + structured_result shape must be byte-identical.
- Any diff → revert that commit, investigate.

**Exit criteria:**
- Exporter visually and functionally unchanged.
- `components/lcopilot/` populated with all extracted pieces.
- All imports across the codebase point to the new paths.
- IDEAL SAMPLE Playwright regression passes at 100% parity.

## Phase 2 — Importer flows on shared pieces

Built on top of Phase 1 outputs. No duplication.

### Routes & page components

| Sidebar label | Route | Component |
|---|---|---|
| Draft LC Review | `/lcopilot/importer-dashboard/draft-lc` | `<ImporterValidationPage moment="draft_lc" />` |
| Supplier Doc Review | `/lcopilot/importer-dashboard/supplier-docs` | `<ImporterValidationPage moment="supplier_docs" />` |

Single component, two URL entries. Component reads `moment` prop and conditionally renders moment-aware title, CTA label, and accepted doc types; everything else is shared (`ExtractionReview`, `LcIntakeCard`, tab shell).

### Moment-driven UI differences

| Aspect | Moment 1 (draft_lc) | Moment 2 (supplier_docs) |
|---|---|---|
| Accepted uploads | Draft LC, SWIFT message, LC application form, Proforma Invoice | LC + Invoice, BL, Packing List, CoO, Insurance, Inspection, Beneficiary cert |
| Page title | "Draft LC Risk Analysis" | "Supplier Document Review" |
| Primary CTA | "Analyze LC Risks" | "Review Supplier Documents" |
| Required-docs rendering | Informational — "LC demands these docs from your supplier" | Checklist — "your supplier must have provided these" |

### Backend data model

Alembic migration adds `workflow_type` enum to `ValidationSession`:

```python
class WorkflowType(str, Enum):
    EXPORTER_PRESENTATION = "exporter_presentation"
    IMPORTER_DRAFT_LC = "importer_draft_lc"
    IMPORTER_SUPPLIER_DOCS = "importer_supplier_docs"
```

Three-step zero-downtime migration:
1. Add column `workflow_type` (nullable)
2. Backfill existing rows to `exporter_presentation`
3. Set `NOT NULL`

### API wire

- `POST /api/validate/?workflow_type=importer_draft_lc` — new optional query param
- Absent param defaults to `exporter_presentation` (no exporter code breaks)
- Extraction + validation pipeline is untouched — `workflow_type` flows to `structured_result.meta.workflow_type` and the `ValidationSession` row only

### Results page

Rewrite `ImportResults.tsx` (currently 2060 lines with mock data + local transforms) as a thin wrapper around shared tab shell. Delete `mockDraftLCResults`, `mockSupplierResults`, `transformApiToSupplierFormat`, `transformApiToDraftFormat`. Replace with `resultsMapper` from `lib/lcopilot/` and a moment-aware action palette (action buttons are placeholders in Phase 2; Phase 3 fills them in).

### Exit criteria
- The two new importer routes (`/draft-lc`, `/supplier-docs`) are live and reachable via dashboard "Start New" CTAs and direct URL. Sidebar is not modified in Phase 2 — Phase 4 owns the sidebar rewrite.
- Clicking either CTA runs extract → review → validate → results using shared components.
- `ValidationSession.workflow_type` populated correctly in all three cases.
- Results page renders with moment-aware verdict copy (action buttons are placeholders).

## Phase 3 — Importer-specific post-validation actions

### Moment 1 actions

| Action | Backend | Frontend hook |
|---|---|---|
| Download Amendment Request | NEW: `POST /api/importer/amendment-request` — returns PDF stream. Template-driven generator walks risk findings and produces "Please amend clause X from Y to Z" entries. | `useAmendmentRequest(sessionId)` |

### Moment 2 actions

| Action | Backend | Frontend hook |
|---|---|---|
| Supplier Fix Pack | EXISTS stubbed. **Wire S3 upload** (remove TODO at `importer.py:193`), return signed URL with 24-hour expiry. | `useSupplierFixPack(sessionId)` |
| Notify Supplier | EXISTS stubbed. **Implement endpoint** — send via existing email service (Resend/SES), write audit log, return `{success, notification_id, sent_at}`. | `useNotifySupplier(sessionId, email, message)` |
| Bank Precheck | EXISTS stubbed. **Implement endpoint** — re-run validation with `precheck_mode=true`, tighter verdict threshold, return verdict memo. | `useBankPrecheck(sessionId)` |

### Both moments

| Action | Behavior |
|---|---|
| Export findings PDF | Shared `lcopilot` report renderer (build or extract if it already exists). |

### UI integration

Shared `VerdictTab` gains an `actionSlot` prop. `ImporterResultsPage` injects moment-aware palette:

```tsx
<VerdictTab actionSlot={
  workflowType === 'importer_draft_lc'
    ? <DraftLcActions sessionId={sessionId} />
    : <SupplierDocActions sessionId={sessionId} />
} />
```

Exporter passes its own `actionSlot` — no regression.

### Exit criteria
- All 4 action endpoints implemented with real side effects (real S3 upload, real email sent, real precheck memo).
- Audit log row written for every action.
- Moment 1 and Moment 2 results pages have working action buttons.
- Integration test per endpoint.

## Phase 4 — Sidebar + dashboard wire-up (both)

### Sidebar rewrite

**Exporter** (`ExporterSidebar.tsx`):
- Remove "Validations" (Clock icon) item
- Rename "New Validation" → "Upload"
- Net: 5 items → 4

**Importer** (`ImporterSidebar.tsx`):
- Rewrite to 5 items: Dashboard · Draft LC Review · Supplier Doc Review · Billing · Settings
- Help → top-bar. Notifications → top-bar bell.
- Net: 14 items → 5

### Routes

- `/lcopilot/importer-analytics` → 301 redirect to dashboard
- Old `?section=workspace|templates|ai-assistance|content-library|shipment-timeline|reviews|analytics|notifications|billing-usage` → redirect to dashboard (or billing for `billing-usage`)
- Keep redirects in place ≥ 90 days; audit deep-link traffic before removing

### Dashboard home (both)

Identical skeleton:
1. Stats strip (reviews this month · average verdict · attention needed)
2. Start New (1 CTA exporter / 2 CTAs importer)
3. Recent Activity — last 10 sessions with `[DRAFT LC]` / `[SHIPMENT]` / default badges; `View all →` link
4. Quota banner (conditional)

### Wire-up — concrete deliverable

Not "`getUserSessions` is called somewhere". The proof is:

1. User logs in → Dashboard loads → Recent Activity reflects last 10 rows for that user/tenant.
2. User runs a full upload → extract → review → validate.
3. User returns to Dashboard (sidebar click or logo).
4. **Within 5 seconds (no manual reload), the new session appears at the top of Recent Activity** with correct verdict and timestamp.
5. Stats strip increments appropriately.

Work items:
- `queryClient.invalidateQueries(['user-sessions'])` in the success handler of `useValidate` / `useResumeValidate`.
- Verify `getUserSessions()` returns freshly-committed rows (no backend cache).
- Confirm tenancy filter: session persists with correct `tenant_id` + `user_id`.
- Playwright e2e asserting the 5-second update.

### Files touched in Phase 4

| File | Change |
|---|---|
| `components/exporter/ExporterSidebar.tsx` | Remove Validations item, rename New Validation → Upload |
| `components/importer/ImporterSidebar.tsx` | Rewrite to 5-item set |
| `lib/exporter/exporterSections.ts` | Update `SidebarSection` enum (drop `'reviews'`), migrate callers |
| `pages/ExporterDashboard.tsx` | Add View all → link, audit query invalidation |
| `pages/ImporterDashboardV2.tsx` | Rewrite to shared skeleton, audit query invalidation |
| `pages/ImporterAnalytics.tsx` | Delete (folded into dashboard stats strip) |
| `hooks/use-lcopilot.ts` | Add invalidation on validation success |
| `App.tsx` | 301 redirects for removed routes |
| Playwright e2e | New test: upload → dashboard updates within 5s (both portals) |

### Exit criteria
- Both sidebars render the minimum item set.
- Both dashboards render real user data.
- **The 5-second dashboard-update smoke test passes on both portals.**
- Old deep links redirect cleanly.

## Testing strategy

| Phase | Test gate |
|---|---|
| 1 | Playwright regression on IDEAL SAMPLE before AND after each extraction commit. Byte-identical DOM, network, structured_result. Any diff → revert. |
| 2 | New importer Playwright specs for both moments (upload → extract-review → validate → results). Backend test that `workflow_type` persists correctly on `ValidationSession`. |
| 3 | Integration tests per action endpoint. supplier-fix-pack returns valid ZIP via signed S3 URL. notify-supplier actually calls email service. bank-precheck returns structured verdict memo. Audit log rows exist. |
| 4 | The 5-second dashboard-update smoke (Playwright) on both portals. |

## Risks & mitigations

| Risk | Mitigation |
|---|---|
| Phase 1 regresses exporter golden path | One commit per piece; smoke before merging each; easy bisect |
| `workflow_type` migration on existing `ValidationSession` rows | Three-step zero-downtime Alembic migration (add nullable → backfill → set NOT NULL) |
| Email sending triggers spam filters | Use existing verified-domain service; per-tenant rate limit; sandbox addresses first |
| S3 fix-pack bucket cost creep | 30-day lifecycle expiry; deny public writes; signed URLs only |
| Billing leakage — `workflow_type` accidentally affects per-session charging | Explicit test: one session each of the three workflow_types has identical billing + quota records |
| Dashboard "wire-up" is a bigger fire (persistence / tenancy / cache bugs) | 5-second smoke test exposes it immediately. If it fails, Phase 4 gains a root-cause sub-task. Don't ship Phase 4 until it passes. |
| Old importer deep links have live users bookmarked | 301 redirects on all removed routes; keep ≥ 90 days; audit traffic before full removal |

## Rollback per phase

- **Phase 1:** `git revert` the extraction commit. Old files stay in tree until the final Phase 1 cleanup commit.
- **Phase 2:** `workflow_type` defaults to `exporter_presentation` — reverting importer routes breaks nothing for exporter. Frontend importer routes guarded by `LCOPILOT_IMPORTER_V2` feature flag.
- **Phase 3:** No per-endpoint server flags. Client flag `VITE_LCOPILOT_IMPORTER_V2` already hides the action buttons, so no one calls the endpoints when the flag is off — blast radius is contained at the route layer. Rollback = git revert + redeploy (or hotfix). If we later need a granular kill switch, one env (`LCOPILOT_IMPORTER_ACTIONS_ENABLED`) gating all four endpoints together is the minimum addition worth making.
- **Phase 4:** Sidebar rewrite = single file revert. Redirects layer stays (harmless).

## Success criteria (whole project)

- Importer can complete both Moment 1 and Moment 2 flows using the exporter's modern plumbing (ExtractionReview, intake card, sessionStorage, Zod, shared tab shell, `resultsMapper`).
- All four importer-specific actions (amendment-request, fix-pack, notify-supplier, bank-precheck) work end-to-end with real side effects.
- Both portal sidebars are slim and identical-skeleton.
- Both dashboards update within 5 seconds of a new validation completing.
- Exporter golden path regresses zero times across all four phases.
- `/components/lcopilot/` is the authoritative home for LC-validation UI primitives; no duplicate components between exporter and importer.

## Out of scope (deferred explicitly)

- Moment 1 ↔ Moment 2 session linkage (independent sessions only).
- Accept-with-waiver and formal rejection actions.
- Importer-side customs pack.
- Rulhub engine fixes (separate workspace).
- AI Examiner prompt tuning.
- Combined / enterprise / bank dashboards.

## Rough timing (directional, not a commitment)

| Phase | Work-days |
|---|---|
| 1 — extract | ~2-3 |
| 2 — importer flows | ~3-4 |
| 3 — action endpoints | ~3-5 |
| 4 — shell + wire-up | ~2-3 |
| **Total** | **~10-15 focused days** |
