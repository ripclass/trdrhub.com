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

Task #8 in the task tracker has the abbreviated plan. **The integration audit
below is the load-bearing piece — it changes the original "extend existing
infra" framing significantly.**

### Audit findings (done 2026-04-25, don't re-audit)

The existing bulk infra at `apps/api/app/models/bulk_jobs.py`,
`apps/api/app/services/bulk_processor.py`, and
`apps/api/app/routers/bank_bulk_jobs.py` is partially reusable but
has bigger gaps than the original plan assumed:

1. **Models are reusable.** `BulkJob`, `BulkItem`, `BulkFailure`, `JobEvent`,
   `BulkTemplate` work as-is. `tenant_id` is `String(64)` — accepts a
   company_id UUID string fine. `BulkItem.item_data` is JSONB so we can
   stuff `supplier_id` / `services_client_id` / file refs in there.

2. **`app.core.queue` is a STUB.** Read it: literally `logger.info("Queue
   stub: Would enqueue {job_type}...")` and a no-op pass. Nothing
   actually queues, nothing dequeues. The existing `BulkProcessor._queue_job()`
   call doesn't do anything. Means: **there is no real background worker
   in this repo today.**

3. **`BulkProcessor._process_lc_validation()` is a SIMULATION.** It
   `await asyncio.sleep(0.1)` and returns hardcoded mock results
   (`{"validation_status": "passed", "compliance_score": 95.5, ...}`).
   NOT wired to the real `/api/validate/` pipeline at all. The
   `lc_validation` job_type is theatre.

4. **`BulkProcessor.start_job()` runs items synchronously** via
   `_process_job_items` → `asyncio.gather` over batches of 10. So if
   you call `start_job` directly from a request handler, the request
   blocks until every item finishes. Acceptable for tiny batches,
   broken at the 80-supplier scale we need.

5. **`_validate_job_config` REQUIRES `validation_rules` +
   `compliance_standards` config fields** for `lc_validation`. These
   are bank-internal concepts. Customer-side bulk needs to either
   relax this OR use a fresh job_type (preferred — cleaner separation).

6. **No SSE infra anywhere.** Bank-side bulk uses GET-poll for progress.
   We need to add SSE from scratch for the customer-facing experience.

### Revised A1 part 2 plan (build accordingly)

**Decision: new job_type `customer_lc_validation`, not extending
`lc_validation`.** Avoids touching bank-side validate config rules,
keeps customer + bank bulk behavior independently evolvable.

**Decision: in-process async via FastAPI BackgroundTasks for v1.** The
real worker queue (Celery/RQ/whatever) is a separate cross-cutting
infrastructure piece that touches deploy + ops. For Phase A1, run the
bulk job in a `BackgroundTasks` task off the request. Caps:
- Per-job concurrency: 4 items in parallel via `asyncio.Semaphore(4)`
  (protects LLM rate limits + RulHub).
- Job lifetime: cap at 30 min total. Exceeding = mark FAILED with
  reason `"timeout"`.
- Single-instance assumption. If we move to multi-instance Render
  later, we'll need a real queue. Document this as a v1.1 follow-up.

**Decision: SSE endpoint via FastAPI's `StreamingResponse` +
in-memory pub/sub per-job.** No Redis required. Pattern: `BulkProgressBroker`
class with `subscribe(job_id) -> async iterator` and `publish(job_id,
event)`. The background task `publish()`es per-item events; the SSE
endpoint `subscribe()`s + yields. When the request handler exits
(client disconnect), the subscription auto-cleans up. Lives entirely
in process memory. Multi-instance friendly = no, but we're single-
instance for v1.

### Files to create

1. **`apps/api/app/services/bulk_validate_processor.py`** — NEW. Don't
   extend `BulkProcessor`; subclass-or-compose so we can have our own
   `_execute_item_processing` that calls the real `/api/validate/`
   pipeline. Wire the lifecycle hook (transition to `under_bank_review`
   on success per `reference_lc_lifecycle.md`).

2. **`apps/api/app/services/bulk_progress_broker.py`** — NEW. In-memory
   pub/sub for SSE. ~50 lines.

3. **`apps/api/app/routers/bulk_validate.py`** — NEW router with
   the 6 endpoints from the original plan (start / upload / run /
   get / stream / cancel). Pydantic schemas inline.

4. **`apps/api/alembic/versions/20260426_add_validation_session_bulk_link.py`**
   — NEW migration. Add nullable `bulk_job_id` FK + `bulk_item_id` FK on
   `validation_sessions` so we can reverse-lookup which sessions
   belong to a bulk job.

5. **`apps/api/tests/test_bulk_validate.py`** — full flow tests, in-memory
   SQLite same pattern as `test_lc_lifecycle.py`. Mock the validation
   pipeline so tests don't actually call the LLM.

6. **`apps/web/src/lib/lcopilot/featureFlags.ts`** — add
   `LCOPILOT_BULK_VALIDATION` flag, off by default.

7. **`apps/web/src/pages/lcopilot/_bulk-test.tsx`** (or wherever the
   QA test routes live) — hidden behind feature flag. Drag-drop folder,
   show SSE progress, list results. Throwaway QA tool, NOT shipped UI.

### Files to read FIRST when resuming (in order)

1. `apps/api/app/routers/validate.py` — find the entry function for
   single-LC validation. We need to call it from inside the bulk
   processor.
2. `apps/api/app/services/lc_lifecycle.py` (already read in this
   session — recap in `reference_lc_lifecycle.md`).
3. `apps/api/app/models/bulk_jobs.py` (already read — see audit above).
4. **Skip** re-reading `bulk_processor.py` and `bank_bulk_jobs.py`
   unless something looks off — the audit above is current.

### Done criteria (unchanged)

- Curl through full bulk flow with 5 sample LCs from
  `apps/api/tests/stress_corpus`, all complete.
- SSE stream emits per-item progress.
- Cancel mid-flight stops further items.
- Each completed bulk child writes a lifecycle event transitioning
  to `under_bank_review` (using the helper from `50efc37a`).

### Risk callouts

- **`/api/validate/` is HTTP-handler-shaped, not service-shaped.** May
  need to extract a service function the bulk processor can call
  directly without going through the request layer. Audit before
  building.
- **Render is single-instance for trdrhub-api today.** Confirm before
  shipping; if multi-instance, the in-memory broker breaks for clients
  that hit the wrong instance. Fix = sticky-session OR Redis pubsub.
- **Concurrency cap of 4 might still hit LLM rate limits at 80
  suppliers.** Make the cap env-configurable (`BULK_CONCURRENCY` env
  var, default 4).

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
