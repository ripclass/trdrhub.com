# QA Smoke Gate Checklist (Smoke20 × 2) — Run-Validation Protocol

**Scope:** Day3 smoke gate after backend-schema fix
**Primary runner:** `python .\tools\day3_pipeline\run_batch_day3.py`
**Artifact root:** `H:\.openclaw\workspace\trdrhub.com\Data\day3\results`  (repo scripts also write under `data\day3\results`, same path on Windows)

## 1) Runner command/path validation

### Correct smoke command (must run twice, independent rerun)
- **Run 1 (fresh):**
  - `$env:DAY3_API_URL = "http://localhost:8000/api/validate/"`
  - `python .\tools\day3_pipeline\run_batch_day3.py --smoke20 --min-interval 3.0 --retries-429 8`
- **Run 2 (no resume):**
  - `python .\tools\day3_pipeline\run_batch_day3.py --smoke20 --min-interval 3.0 --retries-429 8 --no-resume`
  - `--no-resume` is **required** because default mode is resume-safe and would skip prior successful `case_id`s, making the second run non-independent.

### Required per-run artifact capture (since script writes a single `day3_results.jsonl`/`metrics_summary.json` set)
After each run, snapshot files with run labels:
- `day3_results.jsonl` -> `smoke20_run1_day3_results.jsonl` / `smoke20_run2_day3_results.jsonl`
- `metrics_summary.json` -> `smoke20_run1_metrics_summary.json` / `smoke20_run2_metrics_summary.json`
- `confusion_matrix.csv` -> `smoke20_run1_confusion_matrix.csv` / `smoke20_run2_confusion_matrix.csv`
- `failed_cases.csv` -> `smoke20_run1_failed_cases.csv` / `smoke20_run2_failed_cases.csv`
- `rate_limit_stats.json` -> `smoke20_run1_rate_limit_stats.json` / `smoke20_run2_rate_limit_stats.json`

### Command/path issues found in current docs/scripts
- `tools/day3_pipeline/smoke20_day3.ps1` and `README_DAY3_AUTOPILOT.md` still advertise old smoke criteria (`success_rate>=90%`, `blocked in PASS<=20%`) and should be updated to the gate formulas below.
- Current scripts print/assume smoke completion but do **not** automatically persist per-run artifacts; manual snapshot step above is required for x2 evidence.

---

## 2) One exact smoke gate checklist (both runs must satisfy)
For each run, evaluate:
- **Comparable sufficiency:** `comparable_records >= 18`
- **Accuracy:** `accuracy >= 0.70`
- **Critical false pass:** `critical_false_pass == 0`
- **422 stability:** `err_422 == 0`
  - `err_422` = count of rows with error containing `HTTP Error 422` in run output (or equivalent 422 field in response logs)
- **429 exhaustion:** `(cases_exhausted_after_429 / comparable_records_or_processed_cases) <= 0.05`
  - recommended: use `cases_exhausted_after_429 / 20`
- **Pass-blocked anomaly:** `(pass_actual_blocked / pass_expected) < 0.30`
  - `pass_actual_blocked` = count(expected=`pass` and actual=`blocked`)
- **Rerun consistency (between run1 and run2):** `rerun_consistency >= 0.95`
  - compare same case_id actual verdict vectors across the two 20-case runs; require repeatability score `>=0.95`

---

## 3) Current artifact validation (as of now)

### Latest canonical files found
- `DAY3_SIGNOFF.md` — 2026-03-01
- `metrics_summary.json` — 2026-03-01
- `rate_limit_stats.json` — 2026-03-01
- `day3_results.jsonl` — 2026-03-01
- `failed_cases.csv` — 2026-03-01
- `confusion_matrix.csv` — 2026-03-01
- `validation_commands.ps1` — 2026-03-01 (empty, because no dry-run run was requested)

### Status vs required smoke20×2 schema
- `day3_results.jsonl` (latest): all 20 records are `status=error` with DB error (`HTTP Error 500 ... type column does not exist`), so run is **not smoke-comparable** (`comparable_records=0`).
- No paired second smoke run exists in the current artifact set.
- No file currently carries an explicit per-run label (`smoke20_run1_*`, `smoke20_run2_*`), so rerun consistency cannot be derived directly from current baseline artifacts.

### Secondary smoke files already present
- `smoke20_liveapi_20260227.jsonl` and `smoke20_liveapi_confusion_matrix.csv` are present (20 records), but they are **single-run historical artifacts**, not a paired x2 set and not tagged for run indexing.
- `smoke10_summary_from_smoke_ready.json` is for 10-case runs and is **schema-inapplicable** to the current smoke20 gate.

---

## 4) Stale/invalid artifact list (blocked for current smoke20×2 pass/fail scoring)
- **`Data\day3\results\day3_results.jsonl` + dependent artifacts** (latest):
  - invalid for smoke gate because backend-schema/runtime failures yielded 0 comparable records (all status error).
- **`Data\day3\results\iteration_2_*` and `iteration_3_*`** under `autonomous_loop\`:
  - generated during prior autonomous loop with older run context; no current `smoke20×2` paired evidence.
- **`Data\day3\results\smoke10_summary_from_smoke_ready.json`**:
  - wrong run size/name for smoke20 protocol (10-case summary).
- **`Data\day3\results\smoke20_liveapi_20260227.jsonl` + `smoke20_liveapi_confusion_matrix.csv`:**
  - historical single-run set only; cannot satisfy rerun-consistency requirement.
- **Docs/scripts needing update (protocol/schema alignment):**
  - `tools/day3_pipeline/smoke20_day3.ps1`
  - `tools/day3_pipeline/README_DAY3_AUTOPILOT.md`
  - both still state legacy pass criteria that conflict with the target formulas.

## 5) Evidence-backed derived metrics from available single valid smoke-style run
(For `smoke20_liveapi_20260227.jsonl` only; not x2)
- `comparable_records=20`
- `accuracy=0.05`
- `critical_false_pass=0`
- `err_422=0`
- `pass_actual_blocked=6`, `pass_expected=6`, ratio=1.0 (fails `<0.30`)
- `rate_limit_stats`: `cases_exhausted_after_429=0` (passes `<=5%`)
- rerun consistency: **N/A** (no run pair)

---

## 6) Action to make artifacts valid for next smoke20×2 gate
1. Run **exactly** the two commands in section 1.
2. Snapshot artifacts to run-specific filenames after each run.
3. Recompute all seven formulas above from the paired run artifacts.
4. Only then produce final GO/NOGO decision.
