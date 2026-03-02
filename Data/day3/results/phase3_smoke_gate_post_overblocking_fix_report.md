# Phase 3 Smoke20×2 Gate Report (Post Over-blocking Fix)

**Generated (local):** 2026-03-01 15:02:49 (Asia/Dhaka)
**Environment:** `DAY3_API_URL=http://localhost:8000/api/validate/`
**Endpoint:** http://localhost:8000/api/validate/

## Command Log
- `docker compose build api`
- `docker compose up -d --force-recreate api`
- `Invoke-WebRequest -Uri 'http://localhost:8000/health' -UseBasicParsing` (poll loop; 1 attempt -> 200)
- `python .\tools\day3_pipeline\run_batch_day3.py --smoke20 --min-interval 3.0 --retries-429 8`
  - output artifact snapshot: `run1_20260301_150015_*`
- `python .\tools\day3_pipeline\run_batch_day3.py --smoke20 --min-interval 3.0 --retries-429 8 --no-resume`
  - output artifact snapshot: `run2_20260301_150249_*`
- `copy-Item` to snapshot run artifacts (unique names)

## Run 1 Metrics (tag: `run1_20260301_150015`)
- `comparable_records`: 5
- `accuracy`: 0.0000
- `critical_false_pass`: 0
- `total_records`: 20
- `status_counts`: `error: 15, ok: 5`
- `rerun_consistency`: 1.0000
- `429 exhaustion cases`: 0 / 20 = 0.00
- `HTTP 422 errors`: 0
- `blocked_count`: 5
- `pass_blocked` (blocked/total): 0.25
- `pass_blocked` (blocked/comparable): 1.00 (for reference)

Artifacts:
- `run1_20260301_150015_day3_results.jsonl`
- `run1_20260301_150015_metrics_summary.json`
- `run1_20260301_150015_confusion_matrix.csv`
- `run1_20260301_150015_failed_cases.csv`
- `run1_20260301_150015_rate_limit_stats.json`

## Run 2 Metrics (tag: `run2_20260301_150249`)
- `comparable_records`: 5
- `accuracy`: 0.0000
- `critical_false_pass`: 0
- `total_records`: 20
- `status_counts`: `error: 15, ok: 5`
- `rerun_consistency`: 1.0000
- `429 exhaustion cases`: 0 / 20 = 0.00
- `HTTP 422 errors`: 0
- `blocked_count`: 5
- `pass_blocked` (blocked/total): 0.25
- `pass_blocked` (blocked/comparable): 1.00 (for reference)

Artifacts:
- `run2_20260301_150249_day3_results.jsonl`
- `run2_20260301_150249_metrics_summary.json`
- `run2_20260301_150249_confusion_matrix.csv`
- `run2_20260301_150249_failed_cases.csv`
- `run2_20260301_150249_rate_limit_stats.json`

## Hard Gates

### Run 1
- comparable >= 18/20: **FAIL** (5/20)
- accuracy >= 0.70: **FAIL** (0.00)
- critical_false_pass == 0: **PASS** (0)
- HTTP 422 == 0: **PASS** (0)
- 429 exhaustion <= 5%: **PASS** (0.00, based on cases_exhausted_after_429)
- pass_blocked < 0.30: **PASS** if defined as blocked/total (0.25), **FAIL** if defined as blocked/comparable (1.00)
- rerun_consistency >= 0.95: **PASS** (1.00)

### Run 2
- comparable >= 18/20: **FAIL** (5/20)
- accuracy >= 0.70: **FAIL** (0.00)
- critical_false_pass == 0: **PASS** (0)
- HTTP 422 == 0: **PASS** (0)
- 429 exhaustion <= 5%: **PASS** (0.00, based on cases_exhausted_after_429)
- pass_blocked < 0.30: **PASS** if defined as blocked/total (0.25), **FAIL** if defined as blocked/comparable (1.00)
- rerun_consistency >= 0.95: **PASS** (1.00)

## Blocker Classification
- **Blocker: PHASE3_SMOKE_METRIC_FAIL**
- Evidence: both runs miss hard gates for `comparable_records` (5/20) and `accuracy` (0.00), which are decisive for smoke approval.
- Secondary evidence: 15/20 cases are API `error` with repeated HTTP 500 `quota_error` and intermittent backend validation failures, indicating service stability/dependency issues independent of run-to-run consistency.

## Decision
**FAIL BLOCKED** — Do not proceed beyond this smoke gate.

## One-line Next Action
Stabilize backend API for deterministic `smoke20` behavior (fix quota/dependency/database errors causing 500s), then rerun this exact two-run sequence until `comparable>=18` and `accuracy>=0.70` are satisfied.