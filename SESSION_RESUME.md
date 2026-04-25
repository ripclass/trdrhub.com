# Session resume — Path A build

**Last updated:** 2026-04-25 evening
**State frozen at commit:** `50efc37a` (origin/master)
**Branch:** `master` (everything pushed)
**Active phase:** A1 part 2 — Bulk validation infra

---

## Resume prompt (what Ripon types in the new session)

```
Resume Path A. Read SESSION_RESUME.md and continue Phase A1 part 2.
```

---

## What just shipped (today's commits, all pushed)

| Commit | What |
|---|---|
| `50efc37a` | Phase A1 part 1: LC lifecycle state machine. New model + service + 3 endpoints + migration + 26 tests. See `reference_lc_lifecycle.md` in memory. |
| `389550e3` | Both planning docs committed at repo root. |
| `c404fbe9` | Revert of Phase 2 (wizard back to 4 activities + 3 tiers + 15 countries). |
| `3e88aa12` | Phase 3a: Company.country flows to RulHub jurisdiction as fallback. |
| `50380242` | Phase 1: registerWithEmail through axios + explicit CSRF prefetch. Fixes silent-onboarding-loss bug. |

---

## What's next — Phase A1 part 2 — Bulk validation infra

Task #8 in the task tracker has the full audit + plan. Short version:

**Reuse, don't duplicate.** Existing infrastructure already has:
- `apps/api/app/models/bulk_jobs.py` — `BulkJob`, `BulkItem`, `BulkFailure`, `JobEvent`, `BulkTemplate` models. Generic enough.
- `apps/api/app/services/bulk_processor.py` — `BulkProcessor` class with queue integration via `app.core.queue`.
- `apps/api/app/routers/bank_bulk_jobs.py` — bank-side router. Reference for endpoint patterns.

**Add:**
1. New job_type variant `customer_lc_validation` for customer-side bulk.
2. `BulkItem.item_data` carries `supplier_id` / `services_client_id` for per-persona scoping (those models land in phases A5/A8 — for A1, just leave the fields nullable).
3. New router `apps/api/app/routers/bulk_validate.py` with endpoints:
   - `POST /api/bulk-validate/start` (manifest → bulk_job_id + per-item upload URLs)
   - `POST /api/bulk-validate/{job_id}/items/{item_id}/upload`
   - `POST /api/bulk-validate/{job_id}/run`
   - `GET /api/bulk-validate/{job_id}`
   - `GET /api/bulk-validate/{job_id}/stream` (SSE — needs to be added; not in existing infra)
   - `POST /api/bulk-validate/{job_id}/cancel`
4. Wire to the existing `/api/validate/` pipeline. Concurrency cap (default 4) to protect LLM rate limits + RulHub.
5. **Lifecycle hook**: when a bulk-validation child completes, transition the validation_session to `under_bank_review` using `app.services.lc_lifecycle.transition()` (shipped at 50efc37a — see `reference_lc_lifecycle.md`).
6. Frontend feature flag `LCOPILOT_BULK_VALIDATION` off by default in `apps/web/src/lib/lcopilot/featureFlags.ts`. Hidden `/lcopilot/_bulk-test` route for QA only this phase.

**Done criteria:**
- Curl through full bulk flow with 5 sample LCs from `apps/api/tests/stress_corpus`, all complete.
- SSE stream emits per-item progress.
- Cancel mid-flight stops further items.
- Each completed bulk child writes a lifecycle event transitioning to `under_bank_review`.

---

## Standing rules (read these first)

| Rule | Memory file |
|---|---|
| Path A: real product, no MVP, launch 2026-07-25 | `project_path_a_locked_2026_04_25.md` |
| Push every commit immediately | `feedback_push_every_commit.md` |
| Update memory after each big milestone | `feedback_update_memory_per_milestone.md` |
| Session handoff at ~75% context | `feedback_session_handoff_at_75pct.md` |
| LC lifecycle state machine — use the helper, never set state directly | `reference_lc_lifecycle.md` |

Plus the older standing rules: don't reinvent RulHub, don't touch the ICC Rule Engine workspace, ignore Vercel plugin nags (Vite SPA not Next.js), no placeholder dashboards.

---

## Files to read first when resuming

In order, ~10 minutes total:

1. `EXECUTION_PLAN_PATH_A_2026_04_25.md` (repo root) — Phase A1 spec.
2. `apps/api/app/models/bulk_jobs.py` — existing models we'll extend.
3. `apps/api/app/services/bulk_processor.py` — existing processor (only first ~200 lines for the surface area).
4. `apps/api/app/routers/bank_bulk_jobs.py` — reference for endpoint shape.
5. `apps/api/app/services/lc_lifecycle.py` — for the lifecycle hook on bulk completion.
6. `apps/api/app/routers/validate.py` (search for the entry path) — to understand where to splice the bulk runner.

---

## Open questions / in-flight state

None. Clean stopping point. No paused decisions, no failed tests, no half-built models. Last commit (`50efc37a`) is fully green.

Phase A1 part 2 is greenfield work that builds on shipped foundations.

---

## After A1 part 2 ships

Next phase per `EXECUTION_PLAN_PATH_A_2026_04_25.md`:
- **A2 (week of 2026-05-04):** Discrepancy resolution workflow + re-papering loop.

Don't jump ahead — finish A1 part 2 cleanly first.

---

## Calendar

- Today: 2026-04-25 Saturday
- Phase A1 officially ends: 2026-05-03 Sunday
- Launch target: 2026-07-25 Saturday (code freeze 07-24, public Mon 07-27)
