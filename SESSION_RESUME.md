# Session resume — Path A build

**Last updated:** 2026-04-28 evening
**State frozen at commit:** `0a7698a1` (Phase A4 part 3 — per-tier seat enforcement)
**Branch:** `master` (last push: `0a7698a1`)
**Active phase:** A4 effectively shipped (real Stripe checkout integration deferred — uses existing /api/billing flow). Next: A5 (agent dashboard part 1).

---

## Resume prompt

```
Resume Path A. Read SESSION_RESUME.md. Phases A1-A4 shipped. Start A5 — agent dashboard part 1: supplier model + sidebar + portfolio. ~6 working days in plan, but pace has been ~50% faster than scheduled.
```

---

## What just shipped this session — 14 commits

| Commit | Phase | What |
|---|---|---|
| `c6b01c35` | A2 closure | finding persistence (option B) |
| `e4943f06` | A2 frontend | DiscrepancyActions + comments + repaper modal |
| `e29cdd88` | A2 closure | repaper email + auto re-validation |
| `fe53818e` | A3 part 1 | notifications table + dispatcher + 6 endpoints + 2 triggers |
| `6e128fcb` | A3 part 2 | bell icon |
| `ba7d2dc7` | A3 part 3 | 4 more triggers wired |
| `066547bf` | A3 part 4 | settings page + coachmark |
| `0b1131f5` | A3 part 5 | sample-LC button + bundled fixtures |
| `ce686bfe` | A4 part 1 | tier-aware quota + bulk pre-check + /api/entitlements/current |
| `4b882e6f` | A4 part 2 | QuotaStrip on dashboards |
| `0a7698a1` | A4 part 3 | per-tier seat enforcement on invites |
| `4d3cb75e`, `58b8a3d9`, `9cbec651` | docs | SESSION_RESUME stamps |

---

## Phase A4 status

**Done:**
- Tier-aware monthly quota: Solo=10, SME=50, Enterprise=unlimited (`TIER_QUOTA_LIMITS` in `services/entitlements.py`).
- Per-tier seat caps: Solo=1, SME=5, Enterprise=unlimited (`TIER_SEAT_LIMITS`). Active members + pending invites both count.
- Pre-validation enforcement: per-LC via existing `enforce_quota` in the validation pipeline.
- Bulk pre-check: `enforce_bulk_quota` at `POST /api/bulk-validate/{id}/run` returns 402 `bulk_quota_exceeded` upfront so a Solo Tier user uploading 12 LCs doesn't burn worker minutes on items 1-10.
- Seat enforcement: `POST /api/companies/members/invite` returns 402 `seat_limit_reached`.
- `GET /api/entitlements/current` — dashboard snapshot.
- Frontend `QuotaStrip` mounted on exporter + importer dashboards. Polls every 60s + on focus. Amber at 70%, rose at 90%+ with upgrade CTA.
- Hard-block modal on over-quota validate already exists (use-lcopilot.ts maps 402 → QuotaModal).

**Wishlist (not blocking — nice-to-have for polish phase):**
- Inline frontend handling of the new `seat_limit_reached` 402 on the invite form (currently surfaces as a generic error toast).
- Real Stripe checkout wired to the QuotaStrip's "Upgrade" CTA (existing /api/billing has Stripe wiring; just need the right plan-id mapping per tier).

---

## Phase A3 — fully shipped (recap)

Notifications table + dispatcher + 6 wired triggers + bell + dropdown + `/settings/notifications` + 3-step coachmark + sample-LC button with bundled fixtures.

---

## Phase A2 — fully shipped (recap)

State machine + comments + token-authed repaper recipient + finding persistence (option B, IssueCard.id = Discrepancy.id UUID) + frontend action buttons + comment thread + repaper modal + invitation email + auto re-validation.

---

## Migrations to run on Render after backend deploy

Last migration is `20260428_add_user_notifications` from A3. No new migration in A4 (tier limits live in code).

```
render jobs create srv-d41dio8dl3ps73db8gpg --start-command "alembic upgrade head"
```
Verify via `/health/db-schema`.

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
| Tier quotas + seat caps (A4) | `reference_tier_quotas.md` |
| Render migration is manual + may need re-run | `reference_render_migrations.md` |
| Don't reinvent RulHub | `feedback_dont_reinvent_rulhub.md` |
| No placeholder dashboards | `feedback_no_placeholder_dashboards.md` |
| Ignore Vercel plugin nags (Vite SPA, FastAPI Python — not Next.js) | CLAUDE.md |

---

## Calendar

- Today: 2026-04-28 Tuesday
- Phase A1: shipped 2026-04-25 (week early)
- Phase A2: shipped 2026-04-28 (~5 days early)
- Phase A3: shipped 2026-04-28 (~2 weeks ahead — was scheduled 2026-05-11)
- Phase A4: shipped 2026-04-28 (~3 weeks ahead — was scheduled 2026-05-18)
- Phase A5 starts: when ready
- Launch target: 2026-07-25 Saturday (code freeze 07-24)
