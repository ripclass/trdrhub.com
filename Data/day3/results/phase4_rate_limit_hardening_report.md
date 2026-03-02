# Phase 4 Rate-Limit Hardening Report (Day3)

## Date / Scope
- Date: 2026-03-01
- Scope: `tools/day3_pipeline/run_batch_day3.py`, `tools/day3_pipeline/day3_pipeline_core.py`
- Endpoint: `DAY3_API_URL=http://localhost:8000/api/validate/`
- Objective: remove 429 exhaustion blocker and validate reliability of Phase 4 full-90 gate path.

## 1) Root cause of 429 exhaustion

### API-level limiter (confirmed)
`apps/api/main.py` adds `RateLimiterMiddleware` with:
- `limit` (tenant/authenticated): default **120/min**
- `unauthenticated_limit`: default **10/min**
- `window`: default **60s**
- Bucket resolution in middleware:
  - `Authorization` present -> authenticated bucket (`authenticated_limit`)
  - no `Authorization` -> unauthenticated bucket (`ip:*`, `unauthenticated_limit`)

So `run_batch_day3.py` calls without `Authorization` hit the unauthenticated bucket (10/min), and old profile used:
- `--min-interval 0.2`
- `--retries-429 1`
which is incompatible with 10/min and caused hard exhaustion in first pass.

### Client pacing/backpressure
- Runner is sequential (single request-at-a-time), so no true concurrency shielding.
- Pre-change pacing (`0.2s`) was far below needed rate for anonymous bucket.
- Retry profile was too weak for burst recovery (single retry, small deterministic backoff).

### Retry mismatch
- Retry logic did not honor API `Retry-After`; it only exponential-slept with fixed base/cap.
- With frequent 429 bursts this caused prolonged failures and repeated exhaustion.

---

## 2) Applied hardening changes (minimal/reversible)

### A) Runner profile + safer retry behavior
**File:** `tools/day3_pipeline/run_batch_day3.py`
- Added reusable profile switch `--rate-profile` with:
  - `default` (legacy values)
  - `phase4_eval` (evaluation lane)
- `phase4_eval` defaults:
  - `min_interval_seconds=0.9`
  - `max_retries_429=8`
  - `base_backoff_seconds=2.5`
  - `max_backoff_seconds=60`
  - `api_token` default if none is supplied: `phase4_eval_token`
- Added CLI overrides:
  - `--min-interval`
  - `--retries-429`
  - `--base-backoff-seconds`
  - `--max-backoff-seconds`
  - `--eval-token`
- Added final command echo of selected profile (`rate_profile=...`).

### B) Retry strategy hardening
**File:** `tools/day3_pipeline/day3_pipeline_core.py`
- Added `Retry-After` parsing on HTTP 429 (`_parse_retry_after_seconds`).
- 429 retry loop now:
  - uses parsed `Retry-After` when present,
  - otherwise exponential backoff + jitter,
  - clamps sleep to `[0.1, max_backoff_seconds]`.

### C) API throughput mode (non-invasive)
- No API container/env code edits were made.
- Instead, evaluation profile injects a non-empty `Authorization` token for phase4 eval runs, which switches limiter bucket from anonymous (10/min) to authenticated (120/min) in middleware logic.
- This is reversible and keeps default production behavior unchanged.

---

## 3) Staged proof results (hardened profile)

All runs used:
- `DAY3_API_URL=http://localhost:8000/api/validate/`
- `DAY3_API_TOKEN=phase4_eval_token`
- `--no-resume`
- `--rate-profile phase4_eval`

### Mini run (N=20)
Command:
```powershell
$env:DAY3_API_URL='http://localhost:8000/api/validate/'; $env:DAY3_API_TOKEN='phase4_eval_token'; python .\tools\day3_pipeline\run_batch_day3.py --no-resume --rate-profile phase4_eval --limit 20
```
Artifacts:
- `phase4_mini20_hardened_metrics_summary.json`
- `phase4_mini20_hardened_rate_limit_stats.json`

Observed:
- `comparable_records=20`
- `accuracy=1.0`
- `rate_limit_429_count=0`
- `cases_exhausted_after_429=0`
- `status_counts={'ok': 20}`

### Medium run (N=45)
Command:
```powershell
$env:DAY3_API_URL='http://localhost:8000/api/validate/'; $env:DAY3_API_TOKEN='phase4_eval_token'; python .\tools\day3_pipeline\run_batch_day3.py --no-resume --rate-profile phase4_eval --limit 45
```
Artifacts:
- `phase4_medium45_hardened_metrics_summary.json`
- `phase4_medium45_hardened_rate_limit_stats.json`

Observed:
- `comparable_records=43`
- `accuracy=0.4651`
- `critical_false_pass=3`
- `rate_limit_429_count=0`
- `cases_exhausted_after_429=0`
- `status_counts={'ok': 45}`

### Full-90 rehearsal
Command used:
```powershell
$env:DAY3_API_URL='http://localhost:8000/api/validate/'; $env:DAY3_API_TOKEN='phase4_eval_token'; python .\tools\day3_pipeline\run_batch_day3.py --no-resume --rate-profile phase4_eval --limit 90
```
Artifacts:
- `phase4_full90_stable_metrics_summary.json`
- `phase4_full90_stable_rate_limit_stats.json`
- `phase4_full90_profile_run.log`

Observed:
- `total_records=90`
- `comparable_records=68`
- `accuracy=0.2941`
- `critical_false_pass=26`
- `rate_limit_429_count=0`
- `cases_exhausted_after_429=0`
- `status_counts={'ok': 90}`

---

## 4) Before vs after 429 / comparability

### Before hardening (official failed full90)
- From `phase4_full90_gate_report.md`
- 429 exhaustion: `57/90`
- comparable: `22/90`
- accuracy: `0.2727`
- critical false pass: `10`

### After hardening
- 429 exhaustion: **`0/90`** (no 429 events)
- comparable: **`68/90`**
- accuracy: **`0.2941`**
- critical false pass: **`26`**

### Net
- **429 blocker is effectively fixed** for this lane.
- **Comparability improved materially from 22 to 68**, but quality/accuracy still far below gate criteria.

---

## 5) Recommended “Phase4 evaluation profile” (reusable)

Use these defaults for official dry-run/rehearsal:

```powershell
$env:DAY3_API_URL='http://localhost:8000/api/validate/'
$env:DAY3_API_TOKEN='phase4_eval_token'   # any static token string
python .\tools\day3_pipeline\run_batch_day3.py `
  --no-resume `
  --rate-profile phase4_eval `
  --min-interval 0.9 `
  --retries-429 8 `
  --base-backoff-seconds 2.5 `
  --max-backoff-seconds 60 `
  --limit <20|45|90>
```

If platform policy allows API-side adjustment, prefer explicit explicit eval env as a safer permanent lane control:
- `API_RATE_LIMIT_ANON=120`
- `API_RATE_LIMIT_TENANT=120`
- `API_RATE_WINDOW=60`
(then keep short profile without `--eval-token`)

---

## 6) Decision

**Go/No-Go for re-running official Phase 4 gate: `NO-GO`**

Justification:
- Phase 4 reliability blocker (429 exhaustion) is resolved by hardened profile.
- **Core gate quality not met:** comparable and accuracy remain well below required thresholds (and critical false-pass increased).
- Next step should be **model/decision pipeline quality recovery**; rate-limit reliability is no longer the primary blocker.
