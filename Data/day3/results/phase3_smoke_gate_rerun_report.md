# TRDRHub Phase 3 Smoke20 ×2 Rerun Report

## Commands executed (exact)
1. `$env:DAY3_API_URL='http://localhost:8000/api/validate/'`
2. `python .\tools\day3_pipeline\run_batch_day3.py --smoke20 --min-interval 3.0 --retries-429 8`
3. Snapshot run1 artifacts:
   - `Data/day3/results/run1_20260301_143628_day3_results.jsonl`
   - `Data/day3/results/run1_20260301_143628_metrics_summary.json`
   - `Data/day3/results/run1_20260301_143628_confusion_matrix.csv`
   - `Data/day3/results/run1_20260301_143628_failed_cases.csv`
   - `Data/day3/results/run1_20260301_143628_rate_limit_stats.json`
4. `$env:DAY3_API_URL='http://localhost:8000/api/validate/'`
5. `python .\tools\day3_pipeline\run_batch_day3.py --smoke20 --min-interval 3.0 --retries-429 8 --no-resume`
6. Snapshot run2 artifacts:
   - `Data/day3/results/run2_20260301_143908_day3_results.jsonl`
   - `Data/day3/results/run2_20260301_143908_metrics_summary.json`
   - `Data/day3/results/run2_20260301_143908_confusion_matrix.csv`
   - `Data/day3/results/run2_20260301_143908_failed_cases.csv`
   - `Data/day3/results/run2_20260301_143908_rate_limit_stats.json`

## Run metrics table

| Gate input | Run #1 | Run #2 |
|---|---:|---:|
| `comparable_records` | 20 | 20 |
| `accuracy` | 0.0000 | 0.0000 |
| `critical_false_pass` | 0 | 0 |
| HTTP 422 count | 0 | 0 |
| `cases_exhausted_after_429` | 0 | 0 |
| `429_exhaustion` | 0.00% (`0/20`) | 0.00% (`0/20`) |
| `pass_blocked` | 1.0000 (`20/20`) | 1.0000 (`20/20`) |
| `rerun_consistency` | 1.0000 | 1.0000 |
| raw status counts (`status_counts`) | `{"ok": 20}` | `{"ok": 20}` |

## Hard gate evaluation

- Comparable >= 18/20: **FAIL** (20, but classification indicates effective quality failure; 0 accuracy)
- Accuracy >= 0.70: **FAIL** (0.0000)
- `critical_false_pass == 0`: **PASS** (0)
- HTTP 422 == 0: **PASS** (0)
- `429` exhaustion <= 5%: **PASS** (0.00%)
- `pass_blocked < 0.30`: **FAIL** (1.0000)
- `rerun_consistency >= 0.95`: **PASS** (1.0000)

## Blocker classification
- **BLOCKER: Validation quality collapse (functional blocker).**
  Evidence: both runs returned `actual_verdict=blocked` for all 20 smoke cases (all expected `pass`), yielding `accuracy=0.0` and `pass_blocked=1.0`.

## Final decision
**FAIL**

## One-line next action
Stop here and fix `/api/validate/` pass-case validation/extraction behavior (ensure pass scenarios can return `actual_verdict=pass`), then rerun this exact Phase 3 protocol.