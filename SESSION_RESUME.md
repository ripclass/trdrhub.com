# Session resume — Path A build

**Last updated:** 2026-04-28 evening
**State frozen at commit:** `0b1131f5` (Phase A3 part 5 — sample-LC button + bundled fixtures)
**Branch:** `master` (last push: `0b1131f5`)
**Active phase:** A3 fully shipped end-to-end. Next: A4 (quota / paywall + tier enforcement).

---

## Resume prompt

```
Resume Path A. Read SESSION_RESUME.md. Phase A3 fully shipped (backend + bell + settings + coachmark + sample-LC). Start A4 — quota / paywall + tier enforcement (week of 2026-05-18 in the original plan, ~3 weeks ahead).
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
| `0b1131f5` | A3 part 5 — `Try a sample LC` button + bundled fixtures (`apps/api/app/fixtures/sample_lc/`) + `POST /api/handhold/sample-lc` endpoint. .gitignore unignores the bundled PDFs so they ship to Render. |
| `4d3cb75e`, `58b8a3d9` | docs (SESSION_RESUME stamps mid-session) |

---

## Phase A3 status

**Done end-to-end:**
- `notifications` table + migration `20260428_add_user_notifications`
- `services/user_notifications.dispatch()` writes row + optional email via the A2 SMTP helper
- 6 endpoints under `/api/notifications` (list, unread-count, mark-read, mark-all-read, get-prefs, put-prefs)
- 6 wired triggers (discrepancy_raised, repaper_resolved, validation_complete, bulk_complete, repaper_request_received, lifecycle_transition)
- Frontend bell + dropdown in `DashboardLayout` behind `VITE_LCOPILOT_NOTIFICATIONS`
- `/settings/notifications` page with per-type toggles
- 3-step coachmark on first dashboard render, persisted via localStorage
- Sample-LC button + 7 bundled fixture PDFs (BD-CN/SHIPMENT_CLEAN, ~27 KB total) + `POST /api/handhold/sample-lc` endpoint

**Remaining wishlist (not blocking — push to follow-up phases):**
- Cross-device persistence for the coachmark dismiss (currently localStorage). Move to `User.onboarding_data['seen_tutorial']` if it becomes a UX issue.
- More diverse sample-LC corridors (US-VN, UK-IN, DE-CN already exist in importer-corpus; could rotate or let users pick).

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
