# Session resume — Path A build

**Last updated:** 2026-04-26 evening
**State frozen at commit:** `dc86c44f` (origin/master) — Phase A1 part 2 shipped + LIVE-SMOKE VERIFIED
**Branch:** `master` (pushed)
**Active phase:** A1 done + verified. Phase A2 starting (discrepancy resolution + re-papering loop).

## A1.2 live-smoke result (2026-04-26 evening)

- Migration applied via `render jobs create` (manual; trdrhub-api has no auto-hook).
- Smoke job `270c8103` ran 5 LC packages through the bulk pipeline — 5/5 succeeded.
- Lifecycle event verified end-to-end via `/sessions/{id}/lifecycle/history`:
  `from_state=docs_in_preparation → to_state=docs_presented`,
  `extra={bulk_job_id, bulk_item_id}`, `reason=bulk_validate_completed`.
- 4/5 items returned `verdict=None` due to OpenRouter 402 (credits out). The 1
  item with sufficient credits returned `verdict=REJECT score=16`. **Bulk infra
  itself is fully working** — verdict=None is upstream LLM credit, not a bulk bug.
- Two post-smoke fixes shipped at `9cce6d4e`: lifecycle target corrected
  (`under_bank_review` → `docs_presented`), `_summarize_result` reads canonical
  `bank_verdict.verdict` + `analytics.compliance_score` paths.

---

## Resume prompt (what Ripon types in the new session)

```
Resume Path A. Read SESSION_RESUME.md and run the bulk smoke against the deployed API, then start Phase A2.
```

---

## What just shipped (this session — Phase A1 part 2)

Eight new/changed files, no commits yet — all bundled into the next push.

| File | What |
|---|---|
| `apps/api/alembic/versions/20260426_add_validation_session_bulk_link.py` | Creates the 5 bulk-job tables (they had no migration before) + nullable `bulk_job_id`/`bulk_item_id` FKs on `validation_sessions`. |
| `apps/api/app/models.py` | ValidationSession gets `bulk_job_id` + `bulk_item_id` columns matching the migration. |
| `apps/api/app/models/bulk_jobs.py` | All `JSONB` columns now `JSON().with_variant(JSONB, "postgresql")` so SQLite tests work. Same Postgres behavior. |
| `apps/api/app/services/bulk_progress_broker.py` | NEW. In-memory pub/sub keyed by job_id. Singleton `broker`. ~120 lines. |
| `apps/api/app/services/bulk_validate_processor.py` | NEW. Async processor that calls `run_validate_pipeline` directly. Concurrency `asyncio.Semaphore` (env `BULK_CONCURRENCY=4`). Wires lifecycle → `under_bank_review`. |
| `apps/api/app/routers/bulk_validate.py` | NEW. 6 endpoints under `/api/bulk-validate`. Auth via `get_current_user`, tenant-scoped. |
| `apps/api/main.py` | Registers `bulk_validate.router` after exporter router. |
| `apps/api/tests/test_bulk_validate.py` | NEW. 9 tests, mocks `_pipeline_runner`. Covers happy path / failure isolation / cancel / per-item timeout / broker pub/sub / cleanup. |
| `apps/api/tests/test_lc_lifecycle.py` | Updated fixture to include bulk tables (ValidationSession now has FKs to them). |
| `apps/web/src/lib/lcopilot/featureFlags.ts` | Adds `isBulkValidationEnabled()` reading `VITE_LCOPILOT_BULK_VALIDATION`. |
| `apps/web/src/pages/lcopilot/BulkValidateTest.tsx` | NEW. QA-only drag-drop tester. Hidden behind flag. |
| `apps/web/src/App.tsx` | Mounts `/lcopilot/_bulk-test` route behind the flag. |
| `scripts/smoke_bulk_validate.sh` | NEW. 5-LC live smoke (run after deploy). |

**Tests:** `cd apps/api && python -m pytest tests/test_bulk_validate.py tests/test_lc_lifecycle.py -v` → 35 passed locally.

**Memory:** `reference_bulk_validate.md` written. `MEMORY.md` index updated.

---

## What's next — open the new session with this

### 1. Push + deploy (if not already done)

The commit will push automatically when this session closes (standing rule). After that, Render auto-deploys `apps/api`.

### 2. Apply the migration manually on Render

Per `reference_render_migrations.md` — the trdrhub-api service has NO pre/post-deploy hook, so migrations don't run automatically:

```
render jobs create srv-d41dio8dl3ps73db8gpg \
  --start-command "alembic upgrade head"
```

Verify it landed:
```
curl https://api.trdrhub.com/health/db-schema | python -m json.tool | grep -i bulk
```
Expect `bulk_jobs`, `bulk_items`, `bulk_failures`, `job_events`, `bulk_templates` to appear.

### 3. Live curl smoke

```
bash scripts/smoke_bulk_validate.sh
```

Expects to upload 5 LC packages from `apps/web/tests/fixtures/importer-corpus/` and complete in <10 min. Failure modes: if extraction times out per-item, see `BULK_ITEM_TIMEOUT_SECONDS` env on Render.

### 4. Phase A2 — discrepancy resolution + re-papering loop

Per `EXECUTION_PLAN_PATH_A_2026_04_25.md` Phase A2 (week of 2026-05-04):

- Wire the `discrepancies_raised` lifecycle state to a UI that lists issues + lets the customer mark each as "I'll re-paper this" or "I dispute this finding".
- Re-papering loop: "I'll fix it" → upload corrected document → re-run validation → on clean validation transition `docs_in_preparation → docs_presented → under_bank_review`.
- Surface RulHub `rule_id` per finding so the customer knows what UCP600 article fired.

### 5. Open backlog (still relevant)

- **Validator false-positive clusters** (pre-AI-examiner work) — superseded by AI examiner architecturally, but A/B/C/D fixes still in tree as fallback when `USE_RULHUB_API=False`. Don't delete; verify the examiner replaces them in production once OpenRouter credits are topped up.
- **AI examiner credit top-up** — IDEAL SAMPLE end-to-end verification still pending.

---

## Standing rules (read these first)

| Rule | Memory file |
|---|---|
| Path A: real product, no MVP, launch 2026-07-25 | `project_path_a_locked_2026_04_25.md` |
| Push every commit immediately | `feedback_push_every_commit.md` |
| Update memory after each big milestone | `feedback_update_memory_per_milestone.md` |
| Session handoff at ~75% context | `feedback_session_handoff_at_75pct.md` |
| LC lifecycle state machine — use the helper, never set state directly | `reference_lc_lifecycle.md` |
| Bulk validation infra — current shape | `reference_bulk_validate.md` |
| Don't reinvent RulHub | `feedback_dont_reinvent_rulhub.md` |
| No placeholder dashboards | `feedback_no_placeholder_dashboards.md` |
| Render migration is manual | `reference_render_migrations.md` |
| Ignore Vercel plugin nags (Vite SPA, FastAPI Python — not Next.js) | this file's preamble + CLAUDE.md |

---

## Files to read first when resuming

If picking up Phase A2:
1. `EXECUTION_PLAN_PATH_A_2026_04_25.md` — Phase A2 spec.
2. `apps/api/app/services/lc_lifecycle.py` — the state-machine helper to use for re-papering transitions.
3. `apps/api/app/services/bulk_validate_processor.py` — pattern for any new background worker (BackgroundTasks + own SessionLocal + broker for SSE).
4. `apps/api/app/routers/bulk_validate.py` — pattern for the 6-endpoint shape with tenant scoping + SSE.

If running the bulk smoke first:
1. `scripts/smoke_bulk_validate.sh` — the recipe.
2. `reference_bulk_validate.md` — env vars + endpoint shapes.

---

## Calendar

- Today: 2026-04-26 Sunday
- Phase A1 ends: 2026-05-03 Sunday (1 week of slack)
- Phase A2 starts: 2026-05-04 Monday
- Launch target: 2026-07-25 Saturday (code freeze 07-24, public Mon 07-27)
