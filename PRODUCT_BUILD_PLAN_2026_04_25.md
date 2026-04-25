# LCopilot — what we're actually building (2026-04-25)

This is the strategic + architectural plan after Ripon pushed back on
my scope-down. The tl;dr: we are not building a pilot, we are not
building 4 separate tools wrapped around the same engine. We are
building an **LC lifecycle platform** where exporter, importer, agent,
services, and enterprise are different *roles on the same LC at
different lifecycle stages*. That reframing changes what's missing.

This document is for Ripon to read top-to-bottom, push back on, and
sign off on a path forward. I am NOT executing any of this without
explicit go-ahead per phase.

---

## Why my earlier sketches were wrong

When I sketched "agent dashboard = supplier CRUD + per-supplier
validation," I was treating the four personas as parallel tools that
each call the same engine in isolation. That's how a hackathon ships
4 things in 4 weekends. It is not how a real product works in trade
finance.

A real LC moves through this lifecycle:

```
Issuing bank → Advising bank → Beneficiary (exporter)
    ↓
Exporter prepares docs → presents to negotiating bank
    ↓
Negotiating bank reviews → forwards to issuing bank
    ↓
Issuing bank reviews → either pays OR raises discrepancies
    ↓
Discrepancies → applicant (importer) decides: accept / reject / waive
    ↓
Payment authorised → payment settled → LC closed
```

Every one of our personas is somewhere on that timeline:

- **Exporter** owns the "prepare + present" stage.
- **Importer** owns the "issue + decide on discrepancies" stage at the
  start, and the "accept / reject / waive" stage at the end.
- **Agent / buying house** sits between *suppliers* (each of whom is
  effectively an exporter) and *foreign buyers* (each effectively an
  importer). They orchestrate the prepare+present stage on behalf of
  N suppliers and respond to discrepancies on behalf of those
  suppliers.
- **Services / freight forwarder / consultant** is hired help for the
  *prepare + present* stage. They do the work; their client owns
  the LC.
- **Enterprise** is a tier overlay on any of the above — the
  organisational shape (multi-SBU, RBAC, audit) wrapped around the
  same lifecycle.

Today, the platform treats every user as an isolated party validating
in a vacuum. There is no shared LC between exporter and importer even
if both are on the platform. Discrepancies raised by one don't flow
to the other. There's no notion of who's responsible for fixing what.
That gap is the difference between a validation tool and a trade
finance product.

---

## What I missed when sketching dashboards (the audit)

In rough priority order for "feels like a real product":

### Critical for v1 launch (non-negotiable)

1. **LC lifecycle state machine.** An LC is in one of: issued /
   advised / docs-being-prepared / docs-presented / under-review /
   discrepancies-raised / discrepancies-resolved / paid / closed /
   expired. Today: validation_session has a status field but it's
   not a real state machine. Without states, there's no shared
   understanding of "where is this LC right now?".

2. **Bulk validation.** A buying house with 80 factories cannot
   upload one LC at a time. Real flow: drag a folder of N
   per-supplier subfolders → system parses → runs N parallel
   validation jobs → live progress page → bulk results table → bulk
   actions ("approve clean", "send all with discrepancies for
   re-papering"). Same architecture serves importers ("5 supplier
   presentations came in this week") and services ("validate this
   batch for client X"). Today: zero bulk-validation infra on the
   exporter/importer side. Some bank-side bulk infra exists for
   reuse.

3. **Re-papering loop.** Exporter or agent finds a discrepancy →
   sends a request back to whoever owns the document (themselves, a
   supplier, a freight forwarder) → that party uploads a corrected
   doc → system re-validates → cycle continues until clean. Today:
   each validation is a one-shot. The frontend has no "request fix"
   action. There's no notion of a doc replacement that triggers
   re-validation.

4. **Discrepancy resolution workflow.** Today we surface a list of
   findings. Real product: each finding has a state (raised /
   acknowledged / responded / accepted / rejected / waived), an
   owner (who needs to act on it), a comment thread (so the parties
   can discuss before deciding), and an audit trail. Without this,
   you cannot run trade finance through the platform — you can only
   *check* compliance.

5. **Notifications.** At minimum email + in-app for: validation
   complete, discrepancy raised, action required, presentation
   accepted/rejected. Today: zero notification infra on the
   customer-facing side.

6. **Quota / paywall enforcement.** Solo / SME / Enterprise tiers
   exist as columns. They gate nothing. A free user can process
   infinity LCs. There's no upgrade prompt when limits hit. For a
   commercial launch, this is the difference between revenue and
   no revenue.

7. **First-session handhold.** Demo mode (validate a sample LC),
   tutorial overlay on first login, sample dataset. Today: zero.
   New user lands on an empty dashboard with no idea what to do.

### Critical per-persona (non-negotiable for the personas we ship)

8. **Per-persona dashboards** — exporter and importer exist; agent
   and services need to be built real (sidebar + validation flow +
   bulk + portfolio + actions + persona-appropriate scoping).

9. **Persona-appropriate scoping records.** Agent needs a Supplier
   model + per-supplier LC attribution. Services needs a Client
   model + per-client LC attribution + time tracking. Without these,
   N LCs across N suppliers/clients pile up in one undifferentiated
   list and the persona dashboard provides no portfolio visibility.

10. **Group Overview (enterprise tier).** Aggregated KPIs across
    activities (or sub-entities, if we ship multi-entity). Today:
    placeholder with em-dashes.

### Important but defer-able to v1.1

11. **Multi-party LC sharing.** If exporter + importer are both on
    platform, link them on the same LC so both see live status.
    Major architectural lift; defer if launching with mostly-solo
    customers.

12. **Bank API integrations.** Most banks don't support API anyway.
    For v1: pre-formatted PDF + email submission with a tracked
    status field. Real bank API integration is a per-bank
    engagement; defer.

13. **Sub-account / multi-tenant identity.** Agent's suppliers can
    log in as their own exporter accounts under the agent's
    umbrella. Big multi-tenant lift; v1.1 once we know the
    relationship pattern.

14. **Comments / collaboration on findings.** Inline thread per
    discrepancy. Nice-to-have for v1, mandatory for v1.1.

15. **Real reporting + analytics.** Discrepancy rate by supplier,
    by bank, by month. Throughput trends. Today: there's an
    analytics page; I haven't audited its quality.

16. **Internationalization.** Bangla / Vietnamese / Hindi UI. v1 in
    English only is fine.

17. **Mobile.** Trade finance managers do work on phones; today's
    UI is desktop-first. v1 mobile-OK, mobile-great in v1.1.

### Premium / enterprise-only (build into the tier)

18. **RBAC on validation actions.** Junior validates, senior
    approves discrepancy resolutions. Real permission system, not
    just labels.

19. **Audit log UI.** `audit_log` table exists; surface it for
    enterprise customers.

20. **SSO + SAML.** Bank-side wired; need to expose to enterprise
    tenants.

21. **Multi-entity hierarchy.** Parent Company + N child Companies
    for groups like Meghna. Real DB schema work.

### Hygiene that we can't ship without

22. **Failure mode handling.** When LLM is down / RulHub is down /
    OCR is down, system queues the job and emails the user when
    done. Today: probably hard-fails (need to audit).

23. **Privacy + DPA.** GDPR for EU, basic privacy policy for
    everyone. Existing privacy page maybe, hasn't been audited.

24. **Customer support surface.** Support router exists; I haven't
    audited the in-app surface. At minimum: in-app help button →
    ticket creation.

25. **Search.** Find LC by number / supplier / client / status /
    date range. Today: assume basic; needs audit.

26. **Settings completeness.** Per-user notification prefs, default
    bank, default supplier, branding for outbound PDFs.

---

## What this means for "real product per persona"

### Exporter (mostly real today, polish needed)

Already has: extract + validate + results + customs pack + bank
submissions. Gaps:
- **Bulk validation** for the rare exporter who submits many LCs.
- **Re-papering loop** when a discrepancy needs internal fix.
- **Notifications** when bank acknowledges submission.
- **Quota enforcement** so the SME tier means something.
- **First-session demo** so a new exporter can see the value in 5
  minutes.

### Importer (mostly real today, polish needed)

Already has: M1 draft LC review + M2 supplier doc review. Gaps:
- **Bulk validation** for end-of-month presentation rush.
- **Discrepancy resolution workflow** with accept/reject/waive AND
  owner assignment AND comments.
- **Notifications** when supplier presents docs / when discrepancies
  raised by exporter.
- **Settlement tracking** beyond the validation step.
- **Quota enforcement.**

### Agent (NEW dashboard)

Sidebar: Dashboard / Suppliers / Active LCs / Bulk Inbox /
Discrepancies / Reports / Billing / Settings.

Core flows:
1. **Onboard a supplier** — name, country, factory contact, foreign
   buyer they ship to.
2. **Validate a single LC for a supplier** — pick supplier → upload
   LC + docs → same engine → results → action (return to supplier
   for re-papering, OR forward to foreign buyer with clean stamp).
3. **Bulk validate a batch** — drag a folder structured by supplier
   → live progress page → results table.
4. **Cross-supplier portfolio view** — KPI strip + recent activity
   table sortable by supplier / verdict / date.
5. **Cross-supplier discrepancy queue** — all open discrepancies
   across all suppliers, with severity + owner + age.
6. **Re-papering coordination** — request a fix from a supplier →
   tracked → re-validate when corrected docs come in.
7. **Foreign buyer profiles** — who the agent is shipping to (so
   re-export packages can be branded / addressed correctly).
8. **Reports** — per-supplier discrepancy rate, per-buyer
   throughput, monthly summary PDF.

Backend additions:
- `Supplier` model (id, agent_company_id FK, name, country, contact,
  foreign_buyer_id FK).
- `ForeignBuyer` model (id, agent_company_id, name, country,
  contact).
- `validation_session.supplier_id` nullable FK.
- `validation_session.bulk_job_id` nullable FK.
- `BulkValidationJob` model (parent of N validation_sessions, with
  status, progress, owner).
- `RepaperingRequest` model (linked to validation_session +
  supplier, with status + correspondence trail).
- `/api/agency/suppliers` CRUD endpoints.
- `/api/agency/buyers` CRUD endpoints.
- `/api/agency/bulk-validate` endpoint.
- `/api/agency/portfolio` aggregation endpoint.
- `/api/agency/repapering` endpoints.

### Services (NEW dashboard)

Sidebar: Dashboard / Clients / Active LCs / Bulk Inbox / Time /
Billing / Settings.

Core flows:
1. **Onboard a client** — name, contact, billing rate, retainer
   status.
2. **Validate an LC for a client** — pick client → upload → engine
   → results → invoice client + log billable hours.
3. **Bulk validate a batch for one or many clients.**
4. **Cross-client portfolio view** — KPI strip per client.
5. **Time tracking** — hours per client per LC, exportable for
   invoicing.
6. **Per-client billing** — generate per-client invoices with
   itemised LCs + hours.

Backend additions:
- `ServicesClient` model (id, services_company_id FK, name, contact,
  billing_rate, retainer_active).
- `validation_session.services_client_id` nullable FK.
- `TimeEntry` model (linked to client + LC + user + hours +
  description).
- `/api/services/clients` CRUD.
- `/api/services/time` CRUD.
- `/api/services/portfolio` aggregation.
- `/api/services/invoice/<client_id>` invoice generation.

### Enterprise (tier overlay, not separate dashboard)

- **Group Overview page** — cross-activity KPI rollup (total LCs,
  discrepancy rate, throughput) with drilldown to source dashboard.
- **RBAC on validation actions** — roles: viewer, validator,
  approver, admin. Discrepancy resolution gates on approver.
- **Audit log UI** — surface existing `audit_log` table with
  filters.
- **Multi-entity hierarchy (defer to v1.1)** — parent Company + N
  child Companies + cross-entity rollup.
- **SSO** — expose existing SAML to enterprise tenants.

Backend additions:
- `Role` and `UserRole` models (or extend existing CompanyMember).
- `/api/enterprise/group-overview` aggregation.
- `/api/enterprise/audit-log` queryable endpoint.
- Migration: add `parent_company_id` nullable FK on Company
  (multi-entity, deferred surfacing).

---

## Cross-cutting capabilities

### Bulk validation architecture

- Frontend: drag-and-drop folder OR ZIP upload OR multi-file picker.
  Per-file metadata: which supplier/client (auto-attributed from
  folder structure or set on upload).
- Backend: `BulkValidationJob` model with N child validation_sessions.
  Status: pending / in_progress / completed / failed / cancelled.
- Worker: background job runs N validations in parallel (with
  concurrency cap to avoid blowing LLM rate limits / RulHub
  concurrency).
- Streaming progress: SSE endpoint returning per-child progress.
- Results UI: sortable table of child verdicts, click into any one
  for the full results page.
- Bulk actions: approve all clean, send re-papering requests to all
  with discrepancies, export per-child PDF reports as a ZIP.

### LC lifecycle state machine

States: `issued` → `advised` → `docs_in_preparation` →
`docs_presented` → `under_bank_review` → `discrepancies_raised` →
`discrepancies_resolved` → `paid` → `closed` / `expired` (terminal).

Transitions are gated by who's allowed to push them (bank user pushes
`paid`; exporter pushes `docs_presented`; importer pushes
`discrepancies_resolved` after waiving; etc.).

Each transition fires an event; events drive notifications.

Backend: `lc_lifecycle_state` field on validation_session OR a
separate `LCLifecycle` model linked to validation_session. State
transitions in a state-machine helper that enforces allowed
transitions.

### Discrepancy resolution workflow

Each discrepancy has:
- `state`: raised / acknowledged / responded / accepted / rejected /
  waived
- `owner_user_id`: who needs to act
- `comments`: thread of party-to-party discussion
- `resolution_action`: accept / reject / waive / re-paper
- `resolution_evidence`: optional uploaded doc

Backend: extend existing `Discrepancy` model. Add `Comment` model.
Add `/api/discrepancies/{id}/comment` endpoint. Add
`/api/discrepancies/{id}/resolve` endpoint with action.

### Re-papering loop

A `RepaperingRequest` model that links a discrepancy to a target
party (supplier, freight forwarder, internal team). Lifecycle:
`requested` → `in_progress` → `corrected_doc_uploaded` →
`re_validated` → `resolved` / `still_discrepant`.

Frontend: "Request fix" button on each discrepancy card. Modal asks
who to send to + message. Triggers email + in-app notification to
recipient. Recipient gets a focused page for that one fix request.
Once they upload, system re-runs validation against the corrected doc
and links result back to original discrepancy.

### Notifications

Channels: email (via existing transactional email infra if any, or
add SES/SendGrid), in-app.

Events to notify on:
- Validation complete (success / failure)
- Discrepancy raised
- Action required (re-paper request, resolution decision)
- Bank acknowledged submission
- LC state transition (configurable)

Per-user preferences: which events to email, which to only show
in-app, quiet hours.

Backend: `Notification` model + `/api/notifications` (list + mark
read). Background dispatcher fires emails based on event triggers.

### Quota + paywall

- Solo: 10 LCs / month, 1 user.
- SME: 50 LCs / month, 5 users, basic team invites.
- Enterprise: Unlimited LCs, unlimited users, RBAC, audit log,
  SSO, group overview, multi-entity (when shipped), priority
  support.

Enforcement: pre-validation entitlement check. Soft-block at limit
with upgrade CTA.

Backend: extend existing `entitlements` service with tier-aware
quota check. Wire to `/api/validate` entry path.

### First-session handhold

- Demo mode: a "Try a sample LC" button on the empty dashboard runs
  through extraction + validation on a pre-canned LC + docs and
  shows the results page. No real upload.
- Tutorial overlay: 3-step coachmark on first dashboard render.
- Sample dataset: 1-3 sample LCs already loaded in the user's
  account, marked as samples (clear from dashboard with one click).
- Help button: persistent in header → opens chat / ticket.

---

## Honest timeline

This is the part I have to be brutal about. Each line is "real
product, not pilot, not MVP."

| Workstream | Days | Notes |
|---|---|---|
| Phase 1 — auth fixes | DONE | shipped 50380242 |
| Phase 3a — jurisdiction wiring | DONE | shipped 3e88aa12 |
| Bulk validation infra | 6 | Backend job model + worker + SSE + frontend folder upload + progress + results table + actions |
| LC lifecycle state machine | 4 | State model + transition helpers + UI badges + state-aware actions |
| Discrepancy workflow | 5 | State + comments + resolution actions + UI |
| Re-papering loop | 5 | Request model + recipient flow + re-validate trigger + tracking UI |
| Notifications (email + in-app) | 4 | Notification model + dispatcher + email integration + UI |
| Quota / paywall enforcement | 3 | Quota check + upgrade UI + tier wiring |
| First-session handhold | 3 | Demo mode + tutorial + sample data |
| Agent dashboard (full real) | 8 | Supplier + buyer models + sidebar + portfolio + bulk + actions + reports |
| Services dashboard (full real) | 7 | Client model + time tracking + sidebar + portfolio + bulk + invoicing |
| Group Overview (single-entity) | 3 | Aggregation endpoint + KPI page + drilldown |
| RBAC for enterprise tier | 4 | Role model + permission gates + UI for role assignment |
| Audit log UI (enterprise) | 2 | Surface existing table + filters |
| Exporter polish (bulk + repaper hooks) | 3 | Wire bulk infra + repaper button + notifications |
| Importer polish (bulk + workflow + settlement) | 4 | Wire bulk + discrepancy workflow + settlement tracker |
| Failure-mode degradation | 3 | Job queue when LLM/RulHub down + status page |
| Customer support in-app surface | 2 | Help button + ticket creation modal |
| Search across LCs | 3 | Indexed search + filter UI |
| Settings completeness | 3 | Notif prefs + defaults + branding fields |
| Smoke matrix (every combo) | 4 | All persona × tier × country combos validated end-to-end |
| Testing + bug bash + polish | 6 | Buffer for the inevitable |

**Total: 82 days for a true production-quality launch across all 4
personas with the cross-cutting capabilities done right.**

That is *not* 20 days. It's roughly 12-13 weeks of focused work for a
single full-stack engineer, less if parallelised. The 20-day
deadline is incompatible with everything-real-everywhere.

---

## The strategic choice

There are basically four honest paths. Pick one.

### Path A — Slip launch to ~3 months out, ship the real thing.

Launch in mid-July 2026 instead of mid-May. Build all the missing
cross-cutting capabilities + 4 real personas. Customers who sign up
get a product that doesn't surprise them with limits.

Pros: launch with credibility, no "v1.1 will fix it" promises.
Cons: 3 months of runway burn, competitors can move, market timing.

### Path B — Phase the launch by persona, keep the date.

Launch May 15 with **exporter + importer as full real product** (with
bulk + lifecycle + workflow + notifications + quotas + handhold all
built). Wizard at signup offers all 4 activities; agent and services
selectors land on a *real interim view* (basically the exporter
dashboard with a banner "your full agency workspace ships in 4
weeks"). Build agent for real to ship June 15. Build services for
real to ship July 15. Group Overview ships with services.

Pros: honest product on day one for the two personas that exist; no
broken pages; sets expectations for the rest.
Cons: still asking customers to wait; agency segment can't fully
trust us until June.

### Path C — Phase the launch by capability, keep the date.

Launch May 15 with all 4 personas but each is "single-LC validation +
basic dashboard + the existing engine." No bulk, no lifecycle, no
notifications, no re-papering, no quotas, no handhold. Ship all
those cross-cutting capabilities post-launch.

Pros: all 4 personas live on day one.
Cons: every persona is hollow on the depth that matters; bulk is
table stakes for agents and we don't have it; we'll get hit with
"this can't possibly handle 80 suppliers" critique on day one.

### Path D — Compress brutally, miss things.

Try to do everything in 20 days. Cut corners on quality, skip
testing, ship and pray. Pretty much guaranteed to ship bugs that
take you out at launch.

I won't do Path D voluntarily. Path C is the temptation but is the
worst credibility play. Path A and Path B are the honest options.

**My recommendation: Path B.** Exporter + importer get real polish
(bulk, lifecycle, workflow, notifications, quotas, handhold) before
May 15. Agent + services + enterprise group ship in disciplined
post-launch waves with real features each time. Customers signing
up as agents on day one see exporter UI with a banner that says
their dashboard is coming on a specific date — no broken page, clear
expectation.

---

## What I need from you (Ripon)

1. **Pick A / B / C** (or argue for a hybrid I'm not seeing).
2. **Confirm the missing-pieces list** — anything I missed? Anything
   you'd cut?
3. **Confirm the persona role model** — am I right that exporter +
   importer + agent + services are roles on the SAME LC lifecycle,
   not parallel tools?
4. **Confirm priorities for cross-cutting capabilities** — bulk first?
   Lifecycle first? Notifications first? They're not all equally
   urgent and we should sequence intentionally.

After you respond, I'll write a phase-by-phase execution plan and
start building. I am not coding anything more on the
agent/services/group surfaces today — Phase 2 revert is the right
state to be in until we agree on which path.

---

## What's already shipped today

| Commit | What |
|---|---|
| `50380242` | Auth: route /auth/register through axios + explicit CSRF prefetch (fixes silent-onboarding-loss bug from jk@ith.com) |
| `8ec0c097` | Phase 2 wizard scope-down + placeholder rip — REVERTED at c404fbe9 |
| `3e88aa12` | RulHub jurisdiction falls back to Company.country |
| `c404fbe9` | Revert of Phase 2 |

Net change in the repo today: auth bug fixed, jurisdiction wired to
country. Wizard is back to 4 activities + 3 tiers + 15 countries.
Placeholder dashboards (Agency, GroupOverview, EnterpriseGroupLink)
are restored. We're in a coherent pre-rebuild state.
