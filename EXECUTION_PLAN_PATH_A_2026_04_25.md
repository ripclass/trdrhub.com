# Execution plan — Path A (real product, slipped launch)

Companion to `PRODUCT_BUILD_PLAN_2026_04_25.md` (the strategic doc).
Ripon picked Path A on 2026-04-25: slip launch from May 15 to ~July
25, 2026. Ship the real product across all 4 personas + enterprise
tier + cross-cutting capabilities. No half-built shells, no "v1.1
will fix it" promises.

This document is the *how*. Phase-by-phase execution. Each phase
ships to master behind feature flags so existing exporter + importer
users keep working while the new surface is built.

---

## Working principles

1. **Ship to master continuously, gated by feature flags.** No
   long-lived branches. Each phase lands in mainline within its
   2-week window. Existing exporter/importer users see no change
   until the flag flips.

2. **Backend before frontend within each phase.** Models +
   migrations + endpoints first. Test with curl. Then frontend
   binds to a stable API.

3. **Real data, not stubs, from day one.** Use the existing
   stress_corpus + IDEAL SAMPLE for every flow we build. If a
   feature can't survive real LC docs, it's not done.

4. **Smoke after every phase.** End of each 2-week phase: full
   smoke matrix run on the surfaces touched. No phase declares
   "done" without a green matrix.

5. **Daily commits, weekly tag.** Tag the master HEAD every Friday
   with `v0-week-N` so we have rollback points.

6. **Render preDeployCommand handles migrations** (already wired
   per `reference_render_migrations.md`). Verify after every deploy
   via `/health/db-schema`.

7. **Don't reinvent RulHub, don't touch ICC Rule Engine.** If a
   validation gap surfaces, surface it to Ripon to relay to the
   RulHub workspace.

---

## Calendar

Today: **2026-04-25** (Saturday).
Week 1 starts: **2026-04-27** (Monday).
Launch target: **2026-07-25** (Saturday) — Friday 24th = code
freeze, weekend = final smoke + Monday public launch.

13 weeks = 13 phases. 1 week = 1 phase = roughly 5-6 working days.

Buffer baked in: weeks 12-13 are largely buffer/polish/UAT, not new
features. If an earlier phase slips by a week, we eat it in the
buffer and still launch on July 25. If two phases slip, we slip
launch by 1 week to August 1.

---

## Phase index

| # | Week of | Phase | Output |
|---|---|---|---|
| A1 | 04-27 | Bulk validation infra + LC lifecycle state machine | Backend job model, worker, SSE, lifecycle states; flagged off |
| A2 | 05-04 | Discrepancy resolution workflow + re-papering loop | Discrepancy state, comments, owner, resolution actions; flagged off |
| A3 | 05-11 | Notifications (email + in-app) + first-session handhold | Notification model, dispatcher, demo mode, sample data |
| A4 | 05-18 | Quota / paywall + tier enforcement | Pre-validation quota check, upgrade UI, tier wiring |
| A5 | 05-25 | Agent dashboard part 1 — supplier model + sidebar + portfolio | Supplier CRUD, agent layout, KPI strip; flagged off |
| A6 | 06-01 | Agent dashboard part 2 — single + bulk validation flows | Per-supplier validation, bulk inbox, results table |
| A7 | 06-08 | Agent dashboard part 3 — re-papering coordination + foreign buyer profiles + reports | Repaper UI integration, buyer model, per-supplier report PDF |
| A8 | 06-15 | Services dashboard part 1 — client model + sidebar + portfolio + time tracking | Client CRUD, services layout, time entry model + UI |
| A9 | 06-22 | Services dashboard part 2 — single + bulk + invoicing | Per-client validation, bulk, invoice generation |
| A10 | 06-29 | Enterprise tier — group overview + RBAC + audit log UI | Aggregation endpoint, role model, permission gates, audit log surface |
| A11 | 07-06 | Exporter + importer polish — wire bulk + workflow + notifications + handhold integration | Bulk on exporter/importer, repaper hooks, notification triggers |
| A12 | 07-13 | Failure-mode degradation + support surface + search + settings completeness | Job queue, status page, in-app help, indexed search, prefs |
| A13 | 07-20 | Smoke matrix + bug bash + UAT | Every persona × tier × country combo, real LCs, bug list to zero |
| Launch | 07-25 | All flags ON in production | Public launch |

---

## Phase A1 — Bulk validation infra + LC lifecycle state machine

Week of 2026-04-27. ~6 working days.

**Why first:** Both are foundational. Every persona dashboard depends
on bulk. Every workflow depends on lifecycle state. Building these
last would mean retrofitting everything.

### Backend

**Bulk validation:**
- New model `BulkValidationJob` (id, owner_company_id FK,
  owner_user_id FK, persona, status, total_count, completed_count,
  failed_count, started_at, completed_at).
- New model `BulkValidationItem` (id, bulk_job_id FK,
  validation_session_id FK nullable, source_filename, supplier_id
  nullable FK, services_client_id nullable FK, status, error).
- Alembic migration for both + indexes.
- New endpoint `POST /api/bulk-validate/start` — accepts manifest
  (array of `{filename, supplier_id?, services_client_id?,
  files: []}`), returns bulk_job_id + per-item upload URLs.
- New endpoint `POST /api/bulk-validate/{job_id}/items/{item_id}/upload`
  — uploads files for a specific item.
- New endpoint `POST /api/bulk-validate/{job_id}/run` — kicks off
  validation for all uploaded items.
- New endpoint `GET /api/bulk-validate/{job_id}` — current state.
- New endpoint `GET /api/bulk-validate/{job_id}/stream` — SSE,
  pushes progress events.
- New endpoint `POST /api/bulk-validate/{job_id}/cancel`.
- Background worker — uses existing async pipeline if present, OR
  introduces a Celery/RQ worker. Audit `apps/api` for what's there.
  Concurrency cap on parallel validations (configurable, default
  4 — protects LLM rate limits + RulHub).

**LC lifecycle state machine:**
- New column on `validation_session`: `lifecycle_state` (text,
  default 'docs_in_preparation') + `lifecycle_state_changed_at`.
- New model `LCLifecycleEvent` (id, validation_session_id FK,
  from_state, to_state, actor_user_id FK, reason, created_at) —
  append-only event log.
- New helper `app/services/lc_lifecycle.py` with allowed
  transitions table + `transition(session, to_state, actor)` that
  enforces rules + writes event.
- States: `issued`, `advised`, `docs_in_preparation`,
  `docs_presented`, `under_bank_review`, `discrepancies_raised`,
  `discrepancies_resolved`, `paid`, `closed`, `expired`.
- New endpoint `POST /api/sessions/{id}/lifecycle/transition`.
- New endpoint `GET /api/sessions/{id}/lifecycle/history`.
- Existing validation completion automatically transitions
  `docs_in_preparation` → `under_bank_review` (or whichever applies).

### Frontend

- Feature flag `LCOPILOT_BULK_VALIDATION` in
  `apps/web/src/lib/lcopilot/featureFlags.ts`. Off by default.
- Feature flag `LCOPILOT_LIFECYCLE_UI`. Off by default.
- Behind the bulk flag, a hidden route `/lcopilot/_bulk-test` with
  a basic drag-drop file picker → calls the new endpoints, shows
  raw progress. For dev/QA testing only this phase.
- Behind the lifecycle flag, the existing exporter/importer results
  page shows a small lifecycle-state badge.

### Tests

- Backend unit: state machine transitions (allowed + rejected).
- Backend integration: bulk job create → upload → run → SSE
  progress → completion.
- Frontend: feature-flag wiring (off → no UI change).

### Done criteria

- Curl through full bulk flow with 5 sample LCs, all complete.
- SSE stream emits per-item progress.
- Cancel mid-flight stops further items.
- Lifecycle transitions write events; invalid transitions return
  400.

---

## Phase A2 — Discrepancy resolution workflow + re-papering loop

Week of 2026-05-04. ~6 working days.

**Why next:** Discrepancies are useless without resolution. Bulk +
lifecycle don't do anything for the user without an action layer.

### Backend

**Discrepancy resolution:**
- Audit existing `Discrepancy` model. Extend with: `state` (raised,
  acknowledged, responded, accepted, rejected, waived, repaper),
  `owner_user_id` FK, `resolved_at`, `resolution_action`,
  `resolution_evidence_session_id` FK (link to re-validation that
  cleared it).
- New model `DiscrepancyComment` (id, discrepancy_id FK, author_id
  FK, body, created_at).
- Migration.
- New endpoints:
  - `POST /api/discrepancies/{id}/comment`
  - `GET /api/discrepancies/{id}/comments`
  - `POST /api/discrepancies/{id}/resolve` (action + optional
    evidence session id)
  - `POST /api/discrepancies/{id}/assign` (owner_user_id)

**Re-papering loop:**
- New model `RepaperingRequest` (id, discrepancy_id FK, requester_id
  FK, recipient_email, recipient_user_id FK nullable, message,
  state: requested/in_progress/corrected/resolved, created_at,
  resolved_at, replacement_session_id FK nullable).
- Migration.
- New endpoints:
  - `POST /api/discrepancies/{id}/repaper` — creates request, fires
    email
  - `POST /api/repaper/{token}/upload` — recipient uploads
    corrected docs (token-authed for non-platform recipients)
  - `GET /api/repaper/{id}` — status
- Re-validation hook: when corrected docs uploaded, kick off
  validation, on completion link back to original discrepancy +
  transition state.

### Frontend

- Feature flag `LCOPILOT_DISCREPANCY_WORKFLOW`. Off by default.
- Behind flag: results page discrepancy cards get
  Accept/Reject/Waive/Re-paper buttons + comment thread (collapsed
  by default).
- Behind flag: a focused re-papering recipient page at
  `/repaper/{token}` for upload + comment.

### Tests

- State transitions for discrepancies.
- Comment thread chronology.
- Re-papering full loop: create → email sent → upload → re-validate
  → discrepancy resolved.

### Done criteria

- Five-discrepancy LC: each gets a different action, all reflect in
  state + audit trail.
- Re-papering email lands, recipient uploads, original discrepancy
  flips to `resolved` after re-validation.

---

## Phase A3 — Notifications + first-session handhold

Week of 2026-05-11. ~5 working days.

### Backend

- New model `Notification` (id, user_id FK, type, title, body,
  link_url, read_at, created_at).
- New service `app/services/notifications.py` with `dispatch(user,
  type, ...)` — writes in-app row + fires email if user prefs
  allow.
- Email integration: audit existing infra. If none, integrate SES
  or SendGrid (env-configurable).
- Notification triggers wired to events:
  - Validation complete
  - Discrepancy raised on user's LC
  - Re-papering request received (recipient)
  - Re-papering request resolved (requester)
  - Lifecycle state transition (configurable)
  - Bulk job complete
- New endpoints:
  - `GET /api/notifications` — list
  - `POST /api/notifications/{id}/read`
  - `GET /api/notifications/preferences`
  - `PUT /api/notifications/preferences`

### Frontend

- Feature flag `LCOPILOT_NOTIFICATIONS`. Off by default.
- Behind flag: bell icon in header with unread count, dropdown
  with last 10 notifications, "mark all read", link to settings.
- Behind flag: settings page section for notification preferences.

### First-session handhold (no flag — improves existing dashboards
right away)

- "Try a sample LC" button on empty exporter + importer dashboards.
  Pre-canned LC + docs from `apps/api/tests/stress_corpus`. One
  click runs full validation, lands on results.
- 3-step coachmark on first dashboard render. Stored in user prefs
  ("seen_tutorial").
- Optional sample data — checkbox at signup ("populate my account
  with 2 sample LCs"). Flagged off by default; manual enable for
  demos.

### Tests

- Notification dispatcher fires on every trigger.
- Email + in-app row both created.
- Preferences gate email delivery.
- Sample-LC flow runs end-to-end.

### Done criteria

- New signup → completes wizard → lands on dashboard → "Try a
  sample LC" works → results page renders.
- Discrepancy raised → email lands within 60s + bell icon shows
  unread.
- Toggle email pref off → only in-app row fires on next event.

---

## Phase A4 — Quota / paywall + tier enforcement

Week of 2026-05-18. ~4 working days.

### Backend

- Audit existing `entitlements` service. Extend with tier-aware
  quota.
- Tier definitions in code:
  - Solo: 10 LCs/month, 1 user, no SSO, no audit log, no group
    overview.
  - SME: 50 LCs/month, 5 users, basic invites, no SSO.
  - Enterprise: unlimited LCs, unlimited users, SSO, RBAC, audit
    log, group overview.
- Pre-validation hook in `/api/validate` + `/api/bulk-validate/run`
  — counts month's validations for the company, blocks if over
  quota with structured error code `quota_exceeded`.
- Per-tier seat enforcement on member invites.
- New endpoint `GET /api/entitlements/current` — returns tier,
  quota, used, remaining, upgrade options.

### Frontend

- Quota strip on dashboard: "12 of 50 LCs this month" with
  progress bar.
- Soft block at 90% quota: warning toast.
- Hard block at 100%: modal with upgrade CTA + Stripe checkout
  link.
- Settings → Billing already exists; add the "current plan" card
  with upgrade button.

### Tests

- Solo user hits 10 → 11th validation blocked with proper error.
- Upgrade flow → quota refreshes.
- Bulk job containing 12 LCs for a Solo tier returns
  `quota_exceeded` before starting.

### Done criteria

- All three tiers have working quota gates.
- Upgrade CTA hits real Stripe checkout (test mode).
- Quota strip visible on every dashboard.

---

## Phase A5 — Agent dashboard part 1 (supplier model + sidebar +
portfolio)

Week of 2026-05-25. ~6 working days.

### Backend

- New model `Supplier` (id, agent_company_id FK, name, country,
  factory_address, contact_name, contact_email, contact_phone,
  foreign_buyer_id nullable FK, created_at).
- New model `ForeignBuyer` (id, agent_company_id FK, name, country,
  contact_name, contact_email).
- Add `supplier_id` nullable FK on `validation_session`.
- Migrations.
- New endpoints:
  - `GET/POST /api/agency/suppliers`
  - `GET/PATCH/DELETE /api/agency/suppliers/{id}`
  - `GET/POST /api/agency/buyers`
  - `GET/PATCH/DELETE /api/agency/buyers/{id}`
  - `GET /api/agency/portfolio` — KPIs + recent activity across all
    suppliers.

### Frontend

- Feature flag `LCOPILOT_AGENCY_REAL`. Off by default.
- Behind flag: rebuild `/lcopilot/agency-dashboard` from scratch
  (delete the placeholder version's content; we already deleted +
  re-added the file in Phase 2 / revert).
  - Sidebar: Dashboard / Suppliers / Foreign Buyers / Active LCs /
    Bulk Inbox / Discrepancies / Reports / Billing / Settings.
  - Dashboard view: KPI strip (active LCs across N suppliers,
    discrepancies open, $ throughput this month) + recent activity
    table.
  - Suppliers page: list with CRUD, click → supplier detail.
  - Supplier detail: name + contact + LC list (this supplier's
    sessions).

### Tests

- Supplier CRUD round trip.
- Validation session attribution (when bulk or single validation
  runs with `supplier_id`, it appears under that supplier).
- Portfolio aggregation correctness.

### Done criteria

- Agent test user creates 5 suppliers, 1 foreign buyer, manually
  uploads an LC for a supplier (using existing exporter validation
  endpoint with supplier_id), portfolio shows 5 suppliers + 1
  active LC.

---

## Phase A6 — Agent dashboard part 2 (single + bulk validation
flows)

Week of 2026-06-01. ~6 working days.

### Frontend

- Behind `LCOPILOT_AGENCY_REAL`:
  - "Validate LC" CTA on supplier detail page → reuses the
    existing exporter upload component scoped with `supplier_id`.
  - Bulk Inbox page: drag-drop folder OR ZIP upload, parses
    structure (top-level dir = supplier name, contents = LC +
    docs), matches to existing supplier records (or prompts to
    create new), kicks off bulk job.
  - Bulk progress page: live (SSE) per-item progress.
  - Bulk results table: per-item verdict, sortable, click into
    full results page.
  - Bulk actions bar: "approve all clean" / "send re-papering for
    all with discrepancies" / "download per-supplier PDFs".

### Tests

- Bulk drag-drop with realistic folder of 5 supplier
  presentations.
- Each bulk item attributes to correct supplier.
- Bulk actions correctly trigger downstream flows.

### Done criteria

- Agent uploads a folder of 10 supplier presentations, all
  validate, bulk results page is accurate, bulk-action "send
  re-papering for all with discrepancies" creates N repaper
  requests.

---

## Phase A7 — Agent dashboard part 3 (re-papering coordination +
foreign buyer + reports)

Week of 2026-06-08. ~5 working days.

### Frontend

- Re-papering coordination view: list of open re-paper requests,
  status badges, ability to send a follow-up email or cancel.
- Foreign Buyers section: list, detail, link to suppliers
  shipping to that buyer.
- Reports section: per-supplier PDF (discrepancy rate, throughput,
  monthly summary). Per-buyer PDF. Monthly aggregate PDF.

### Backend

- New endpoint `POST /api/agency/reports/supplier/{id}` — generate
  PDF.
- New endpoint `POST /api/agency/reports/buyer/{id}` — generate
  PDF.
- Reuse the customs-pack PDF generation infra if applicable.

### Tests

- PDF generation with real data.
- Re-papering coordination view stays in sync as recipients act.

### Done criteria

- Agent can run their full month's workflow without falling out of
  the dashboard. Sample agency demo flows cleanly start to finish.
- Flag flips ON for a small set of test agent users in
  staging/production for UAT.

---

## Phase A8 — Services dashboard part 1 (client model + sidebar +
portfolio + time tracking)

Week of 2026-06-15. ~6 working days.

### Backend

- New model `ServicesClient` (id, services_company_id FK, name,
  contact_name, contact_email, billing_rate, retainer_active,
  retainer_hours_per_month, created_at).
- Add `services_client_id` nullable FK on `validation_session`.
- New model `TimeEntry` (id, services_company_id FK, services_client_id
  FK, validation_session_id nullable FK, user_id FK, hours,
  description, billable, billed, created_at).
- Migrations.
- Endpoints:
  - `GET/POST/PATCH/DELETE /api/services/clients`
  - `GET/POST/PATCH/DELETE /api/services/time`
  - `GET /api/services/portfolio`

### Frontend

- Feature flag `LCOPILOT_SERVICES_REAL`. Off by default.
- Rebuild services dashboard surface (no placeholder existed; this
  is greenfield).
  - Sidebar: Dashboard / Clients / Active LCs / Bulk Inbox / Time /
    Billing / Settings.
  - Dashboard: KPI strip + recent activity.
  - Clients page: CRUD list.
  - Client detail: contact + LCs + time entries.
  - Time page: log hours quickly, filter by client.

### Done criteria

- Services test user creates 3 clients, logs hours against an LC
  validation, portfolio shows correctly.

---

## Phase A9 — Services dashboard part 2 (single + bulk +
invoicing)

Week of 2026-06-22. ~5 working days.

### Frontend

- Behind `LCOPILOT_SERVICES_REAL`:
  - "Validate LC" CTA on client detail → exporter upload component
    scoped with `services_client_id`.
  - Bulk inbox same pattern as agent.
  - Per-client invoice generator: pulls LCs + time entries for the
    period, generates PDF invoice.

### Backend

- `POST /api/services/invoices/generate` — period + client_id →
  PDF + Invoice record.
- Optional Stripe Invoice integration for full billing automation
  (defer if too risky for v1; manual-PDF is fine).

### Tests

- Bulk validation flow.
- Invoice generation across mixed billable/non-billable hours.

### Done criteria

- Services flow: create client → log time → validate LC → generate
  invoice → invoice matches expected hours + LCs.
- Flag flips ON for test services users for UAT.

---

## Phase A10 — Enterprise tier (group overview + RBAC + audit log)

Week of 2026-06-29. ~6 working days.

### Backend

- New endpoint `GET /api/enterprise/group-overview` — aggregates
  across user's company's activities (single-entity for v1; multi-
  entity hierarchy deferred to v1.1).
- Extend existing CompanyMember with explicit roles: viewer,
  validator, approver, admin.
- Permission helper `app/services/rbac.py` with `require_role(user,
  permission)`.
- Gate sensitive endpoints (discrepancy resolve, repaper send,
  bulk run, invoice generate, settings change) on roles.
- Audit log surface: `GET /api/enterprise/audit-log` (already-
  written `audit_log` table).

### Frontend

- Feature flag `LCOPILOT_ENTERPRISE_TIER`. Off by default.
- Group Overview page: real KPI tiles (activity-by-activity
  rollup), drilldown links to source dashboards.
- Audit Log page: table with filters (user, date, action type).
- Settings: members page with role assignment for enterprise tier.

### Done criteria

- Enterprise test company with 3 members across 3 roles. Junior
  validator can extract+validate but cannot resolve discrepancies.
  Senior approver can resolve. Admin sees audit log of every action.
- Group Overview shows accurate KPIs across enabled activities.

---

## Phase A11 — Exporter + importer polish (wire bulk + workflow +
notifications + handhold)

Week of 2026-07-06. ~5 working days.

### Frontend

- Bulk inbox added to exporter dashboard sidebar (gated by
  feature flag, on by default for exporters now).
- Bulk inbox added to importer dashboard.
- Discrepancy workflow buttons + comments live on existing
  exporter results page + importer M1/M2 review pages.
- Notification triggers fire on existing exporter + importer flows.
- Handhold (sample LC button + tutorial) integrated on existing
  dashboards.

### Done criteria

- Existing exporter + importer dashboards now have bulk + workflow
  + notifications, all real, no breaking changes.

---

## Phase A12 — Failure-mode + support + search + settings

Week of 2026-07-13. ~5 working days.

### Backend

- Failure-mode degradation: when LLM (OpenRouter) returns 429/5xx
  or RulHub fails, queue the validation, return 202 + job_id, fire
  notification on completion.
- Status page: simple `/api/status` endpoint reporting health of
  upstream services. Public.
- Search: indexed search across LCs by number, supplier, client,
  status, date range. Use Postgres full-text or trigram. Endpoint
  `GET /api/search?q=...`.
- Settings completeness: notification prefs (already in A3),
  default issuing bank (per company), default supplier (per agent),
  email signature for outbound, branding for outbound PDFs (logo
  upload).

### Frontend

- Failure UI: queued-job status badge on dashboard, polling or
  SSE for completion.
- Status page UI: plain page at `/status`.
- Search bar in header on every dashboard.
- Settings sections built out.
- In-app help button → ticket creation (extend existing support
  router).

### Done criteria

- LLM kill-switch test: validation queued, user notified on
  recovery.
- Search returns LCs from any persona dashboard.
- Settings has every section real.

---

## Phase A13 — Smoke matrix + bug bash + UAT

Week of 2026-07-20. ~5 working days. Code freeze on 2026-07-24.

### Smoke matrix

For every (activity-set × tier × country) combination:
- Fresh signup → wizard → land on correct dashboard
- Run a single validation
- Run a bulk validation
- Verify notifications fire
- Verify quota enforces (where applicable)
- Verify lifecycle state transitions
- Verify discrepancy workflow + repapering
- Verify enterprise tier features render only for enterprise users

Activity subsets: 15 (every non-empty subset of {exp, imp, agent,
svc}).
Tiers: 3.
Countries: at minimum BD + IN + VN + UAE + US + GB.
= **270 combinations**. Sample 30-40 representative ones,
exhaustively test the rest by automated script.

### Bug bash

- Internal team runs through every flow, logs bugs to a tracker.
- Triage daily: must-fix vs nice-to-fix.
- Hold launch on any critical bug.

### UAT

- 3-5 friendly customers (1 BD exporter, 1 BD importer, 1 BD agent,
  1 services consultant, 1 enterprise) try the full product.
- Capture feedback. Fix what's critical, log the rest for v1.1.

### Done criteria

- Zero critical bugs.
- 30/30 sampled smoke matrix combos green.
- All UAT customers reach first-success in under 10 minutes.
- Code freeze 2026-07-24.

---

## Launch — 2026-07-25 / 2026-07-28

- 07-24 Friday: code freeze, final smoke run on staging.
- 07-25 Saturday: weekend final QA, all feature flags reviewed.
- 07-26 Sunday: production deploy with all flags ON, monitor.
- 07-27 Monday: public launch announcement.
- 07-28 onwards: support + monitor + log v1.1 backlog.

---

## Cross-cutting infrastructure work (interleaved with phases)

These don't get their own phase — they're baked into the schedule
where most relevant.

- **Feature flag system** — a real flag service in
  `apps/web/src/lib/lcopilot/featureFlags.ts` + backend equivalent.
  Gates per-user, per-company, or globally. Set up Phase A1.
- **Email infrastructure** — pick provider (SES vs SendGrid vs
  Postmark), wire up. Phase A3.
- **Background worker** — audit existing async/queue infra. If
  Celery/RQ exists, use it; if not, add it. Phase A1.
- **Telemetry** — every new endpoint gets request logging + error
  tracking. Sentry or equivalent should already be wired; verify.
- **Database migrations** — every phase has new migrations. Render
  preDeployCommand runs them automatically per
  `reference_render_migrations.md`. Verify after every deploy via
  `/health/db-schema`.

---

## Risks + mitigations

| Risk | Mitigation |
|---|---|
| Bulk validation hits LLM rate limits | Concurrency cap + queue; surface as user-visible "queued, ETA X min" |
| Postgres migration on prod fails | Test every migration locally first; backup before prod deploy; rollback plan |
| Feature flag bugs leak unfinished UI to users | Strict CI check that no flag is hardcoded ON in master commits |
| Cross-persona data bleed (one company sees another's) | Every endpoint enforces company scoping; row-level security on Supplier/Client/etc. |
| Customer support overload at launch | Pre-launch: triage process + canned responses + on-call rotation |
| RulHub side gaps surface during build | Surface to Ripon for relay; do not patch RulHub from this workspace |
| Stripe billing + quota interaction edge cases | Manual test every tier transition + downgrade scenario |
| Re-papering token security (unauth recipient access) | Time-limited tokens, single-LC scope, rate limits |
| Notifications spam users | Default email prefs to "important only"; frequency caps; unsubscribe links |
| Audit log bloats DB | Partition by month + retention policy (12 months default; configurable for enterprise) |

---

## What I need from Ripon to start Phase A1

1. **Confirm phase ordering.** I picked: foundation (bulk + lifecycle)
   first, then workflow, then cross-cutting, then per-persona, then
   enterprise, then polish, then UAT. Push back if you'd reorder.

2. **Confirm "ship to master with feature flags" approach.** Not
   long-lived branches. Existing exporter/importer keep working
   throughout.

3. **Confirm launch target.** 2026-07-25 weekend, 07-27 Monday public
   announcement. If there's a market reason for an earlier or later
   date, tell me now.

4. **Confirm authority to commit `PRODUCT_BUILD_PLAN_2026_04_25.md`
   and this file** as load-bearing reference docs (so future sessions
   read them on resume).

5. **Greenlight to start Phase A1 Monday 04-27** OR a date you'd
   prefer to start.

Once you say go on these five, I commit both planning docs + start
Phase A1 backend work.
