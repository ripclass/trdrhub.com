# Session resume — Path A build

**Last updated:** 2026-04-28 evening
**State frozen at commit:** Phase A13 — `ea1b1750` + smoke matrix + launch checklist
**Branch:** `master`
**Active phase:** All 13 build phases shipped end-to-end. Pre-launch tasks remaining: Render migration runs + smoke verification + bug bash + UAT week.

---

## Resume prompt

```
Resume Path A. Read SESSION_RESUME.md and docs/LAUNCH_CHECKLIST_2026_07_25.md. All 13 phases shipped. Next is launch prep — run the migration on Render, set env vars + Vercel feature flags, exercise scripts/smoke_matrix.py, then the manual sample-matrix pass + UAT week.
```

---

## Phase scorecard — A1 through A13 all shipped

| | Phase | Plan slot | Done date | Pace |
|---|---|---|---|---|
| ✅ | A1 — Bulk + lifecycle | 2026-04-27 | 2026-04-25 | 2 days early |
| ✅ | A2 — Discrepancy + repaper | 2026-05-04 | 2026-04-28 | 5 days early |
| ✅ | A3 — Notifications + handhold | 2026-05-11 | 2026-04-28 | ~2 weeks early |
| ✅ | A4 — Quota + tier enforcement | 2026-05-18 | 2026-04-28 | ~3 weeks early |
| ✅ | A5 — Agency persona pt 1 | 2026-05-25 | 2026-04-28 | ~4 weeks early |
| ✅ | A6 — Agency pt 2 (bulk inbox) | 2026-06-01 | 2026-04-28 | ~5 weeks early |
| ✅ | A7 — Agency pt 3 (repaper coord + reports) | 2026-06-08 | 2026-04-28 | ~6 weeks early |
| ✅ | A8 — Services pt 1 (clients + time) | 2026-06-15 | 2026-04-28 | ~7 weeks early |
| ✅ | A9 — Services pt 2 (invoices) | 2026-06-22 | 2026-04-28 | ~8 weeks early |
| ✅ | A10 — Enterprise tier (RBAC + group overview + audit log) | 2026-06-29 | 2026-04-28 | ~9 weeks early |
| ✅ | A11 — Exporter+importer polish | 2026-07-06 | 2026-04-28 | ~10 weeks early |
| ✅ | A12 — Failure/support/search | 2026-07-13 | 2026-04-28 | ~11 weeks early |
| ✅ | A13 — Smoke matrix + checklist | 2026-07-20 | 2026-04-28 | ~12 weeks early |

**Code freeze target: 2026-07-24. Public launch: 2026-07-27.**
~13 weeks of slack for the launch-prep cycle.

---

## All shipped commits (this session window)

| Commit | Phase |
|---|---|
| `c6b01c35` `e4943f06` `e29cdd88` | A2 closure (option-B persistence + frontend wiring + email/auto-revalidate) |
| `fe53818e` `6e128fcb` `ba7d2dc7` `066547bf` `0b1131f5` | A3 (notifications backend + bell + 4 more triggers + settings page + sample-LC button) |
| `ce686bfe` `4b882e6f` `0a7698a1` | A4 (tier-aware quota + bulk pre-check + entitlements endpoint + QuotaStrip + seat enforcement) |
| `7b487a4d` `f2556084` | A5 (Supplier+ForeignBuyer models + 11 endpoints + agency dashboard) |
| `d833a030` `1c6cd925` `ea4a84a2` | A6 (single-validate scoping + bulk inbox folder upload + recent jobs panel) |
| `c1970ac4` `2f8823f0` `3b6546bb` | A7 (repaper coordination + buyer detail + supplier/buyer reports + PDFs) |
| `a987b6e2` | A8+A9 (services persona — clients + time + portfolio + invoice generator) |
| `58206070` | A10 (RBAC helper + enterprise group overview + audit log) |
| `ea1b1750` | A11+A12 (bulk-inbox sidebar links + status endpoint + global search bar) |
| (this commit) | A13 (smoke matrix script + launch checklist) |

---

## Pre-launch tasks (NOT yet done)

Per `docs/LAUNCH_CHECKLIST_2026_07_25.md`:

1. **Run migrations on Render** (3 pending: `20260428_add_user_notifications`, `20260429_add_agency_suppliers_buyers`, `20260430_add_services_clients_time`).
2. **Set env vars** on Render (SMTP_*, FRONTEND_URL prod value, etc.).
3. **Flip Vercel feature flags** for production (per checklist).
4. **Run `scripts/smoke_matrix.py`** against staging then prod.
5. **Manual 30-combo sample matrix** (persona × tier × country).
6. **Bug bash week** with internal team.
7. **UAT week** with 3-5 friendly customers.
8. **Launch weekend** monitoring + on-call rotation.

---

## v1.1 backlog (deferred from launch)

- Action bar on agency Bulk Inbox (approve-all-clean / repaper-all-discrepancies / per-supplier PDFs) — A6 deferral
- Failure-mode degradation queue + auto-retry on LLM 429 — A12 deferral
- Real Stripe checkout on QuotaStrip Upgrade CTA — A4 deferral
- Monthly aggregate PDF in agency reports — A7 deferral
- Settings UX completeness (default issuing bank, email signature, branding logo) — A12 deferral
- Multi-entity enterprise hierarchy — A10 v1.1 note
- Cross-device persistence for first-session coachmark (currently localStorage)
- Inline frontend handling of seat_limit_reached 402 (currently generic toast)

---

## Standing rules

| Rule | Memory file |
|---|---|
| Path A: real product, no MVP, launch 2026-07-25 | `project_path_a_locked_2026_04_25.md` |
| Push every commit immediately | `feedback_push_every_commit.md` |
| Update memory after each big milestone | `feedback_update_memory_per_milestone.md` |
| Session handoff at ~75% context | `feedback_session_handoff_at_75pct.md` |
| Render migration is manual + may need re-run | `reference_render_migrations.md` |
| Don't reinvent RulHub | `feedback_dont_reinvent_rulhub.md` |
| No placeholder dashboards | `feedback_no_placeholder_dashboards.md` |
| Ignore Vercel plugin nags (Vite SPA, FastAPI Python — not Next.js) | CLAUDE.md |
