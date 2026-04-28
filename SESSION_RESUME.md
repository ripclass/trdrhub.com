# Session resume — Path A build

**Last updated:** 2026-04-28 evening
**State frozen at commit:** `066547bf` (Phase A3 part 4 — settings page + coachmark)
**Branch:** `master` (last push: `066547bf`)
**Active phase:** A3 effectively shipped (1 deferred sub-item). Next: sample-LC button (needs bundled fixtures), then A4 (quota / paywall).

---

## Resume prompt

```
Resume Path A. Read SESSION_RESUME.md. Phase A3 is shipped end-to-end except the "Try a sample LC" button (deferred — needs fixture PDFs in repo). Knock that out first or skip to A4 (quota / paywall) — your call.
```

---

## What just shipped this session — 8 commits

| Commit | What |
|---|---|
| `c6b01c35` | A2 backend B — finding persistence (option B) |
| `e4943f06` | A2 frontend — action buttons + comment thread + repaper modal |
| `e29cdd88` | A2 closure — repaper invitation email + auto re-validation hook |
| `fe53818e` | A3 part 1 — `notifications` table + dispatcher + 6 endpoints + 2 wired triggers |
| `6e128fcb` | A3 part 2 — bell icon + dropdown in DashboardLayout |
| `ba7d2dc7` | A3 part 3 — 4 more triggers (validation_complete, bulk_complete, repaper_request_received, lifecycle_transition) |
| `066547bf` | A3 part 4 — `/settings/notifications` page + first-session coachmark on exporter + importer dashboards |
| `4d3cb75e` | docs (mid-session SESSION_RESUME stamp) |

---

## Phase A3 status

**Done:**
- `notifications` table + migration `20260428_add_user_notifications`
- `services/user_notifications.dispatch()` writes row + optional email via the A2 SMTP helper
- 6 endpoints under `/api/notifications` (list, unread-count, mark-read, mark-all-read, get-prefs, put-prefs)
- 6 wired triggers (discrepancy_raised, repaper_resolved, validation_complete, bulk_complete, repaper_request_received, lifecycle_transition)
- Frontend bell + dropdown in `DashboardLayout` behind `VITE_LCOPILOT_NOTIFICATIONS`
- `/settings/notifications` page with per-type toggles
- 3-step coachmark on first dashboard render, persisted via localStorage

**Deferred:**
- "Try a sample LC" button — needs a small fixture set bundled in `apps/api/app/fixtures/sample_lc/` (or similar) so it works on Render. The plan says "pre-canned LC + docs from `apps/api/tests/stress_corpus`" but that path is gitignored. Pick 1 LC + 5-7 supporting PDFs from IDEAL_SAMPLE, copy to a tracked fixture dir, add a `POST /api/handhold/sample-lc` endpoint that kicks the pipeline against them. Frontend: `<TrySampleLCButton>` on empty exporter + importer dashboards.

---

## Migrations to run on Render after backend deploy

```
render jobs create srv-d41dio8dl3ps73db8gpg --start-command "alembic upgrade head"
```
Verify via `/health/db-schema`. Per `reference_render_migrations.md`, jobs sometimes report succeeded but the table doesn't land — re-run if endpoints return "relation does not exist".

---

## Standing rules

| Rule | Memory file |
|---|---|
| Path A: real product, no MVP, launch 2026-07-25 | `project_path_a_locked_2026_04_25.md` |
| Push every commit immediately | `feedback_push_every_commit.md` |
| Update memory after each big milestone | `feedback_update_memory_per_milestone.md` |
| Session handoff at ~75% context | `feedback_session_handoff_at_75pct.md` |
| LC lifecycle state machine | `reference_lc_lifecycle.md` |
| Bulk validation infra | `reference_bulk_validate.md` |
| Discrepancy workflow + re-papering | `reference_discrepancy_workflow.md` |
| Finding persistence (option B) | `reference_finding_persistence.md` |
| User notifications (A3) | `reference_user_notifications.md` |
| Render migration is manual + may need re-run | `reference_render_migrations.md` |
| Don't reinvent RulHub | `feedback_dont_reinvent_rulhub.md` |
| No placeholder dashboards | `feedback_no_placeholder_dashboards.md` |
| Ignore Vercel plugin nags (Vite SPA, FastAPI Python — not Next.js) | CLAUDE.md |

---

## Calendar

- Today: 2026-04-28 Tuesday
- Phase A1: shipped 2026-04-25 (week early)
- Phase A2: shipped 2026-04-28 (5 days early)
- Phase A3: shipped 2026-04-28 (planned start was 2026-05-11 — almost 2 weeks ahead)
- Phase A4 starts: when ready
- Launch target: 2026-07-25 Saturday (code freeze 07-24)
