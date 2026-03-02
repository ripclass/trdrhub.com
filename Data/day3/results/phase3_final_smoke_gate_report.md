# Phase 3 Smoke20×2 Final Gate Report

**Run date/time:** 2026-03-01 15:34–15:37 (Asia/Dhaka)
**Endpoint:** `DAY3_API_URL=http://localhost:8000/api/validate/`
**Service availability check:** API host reachable (`/health` 200, `/` 200, `/api/validate/` 405 expected method-restricted)

## Snapshots
- **Run 1 artifacts:**
  - `phase3_final_run1_20260301_153343_metrics_summary.json`
  - `phase3_final_run1_20260301_153343_confusion_matrix.csv`
  - `phase3_final_run1_20260301_153343_failed_cases.csv`
  - `phase3_final_run1_20260301_153343_rate_limit_stats.json`
  - `phase3_final_run1_20260301_153343_day3_results.jsonl`
- **Run 2 artifacts:**
  - `phase3_final_run2_20260301_153615_metrics_summary.json`
  - `phase3_final_run2_20260301_153615_confusion_matrix.csv`
  - `phase3_final_run2_20260301_153615_failed_cases.csv`
  - `phase3_final_run2_20260301_153615_rate_limit_stats.json`
  - `phase3_final_run2_20260301_153615_day3_results.jsonl`

## Run 1 / Run 2 metrics
| Metric | Run 1 | Run 2 |
|---|---:|---:|
| comparable_records | 20 | 20 |
| accuracy | 0.0 | 0.0 |
| critical_false_pass | 0 | 0 |
| HTTP 422 count | 0 | 0 |
| 429 exhaustion cases | 0 | 0 |
| 429 exhaustion % | 0.00% | 0.00% |
| pass_blocked ratio | 1.00 (20/20) | 1.00 (20/20) |
| rerun_consistency | 1.0 | 1.0 |
| status_counts | ok:20 | ok:20 |

## Gate evaluation (hard gates)
- comparable >= 18/20: **PASS**
- accuracy >= 0.70: **FAIL**
- critical_false_pass == 0: **PASS**
- HTTP 422 == 0: **PASS**
- 429 exhaustion <= 5%: **PASS**
- pass_blocked < 0.30: **FAIL**
- rerun_consistency >= 0.95: **PASS**

## Final Phase 3 decision
**FAIL (blocker)
Reason: two hard blockers (accuracy 0.0, pass_blocked 1.00 > 0.30).**

Evidence:
- Both runs returned `pass`-labeled expected cases as `blocked` (confusion matrix: `pass -> blocked` = 20) in 20/20 comparable records.

## One-line next action
Rollback/triage blocked-overclassification in validation pipeline + reopen API verdict mapping for pass-flow cases, then rerun this Phase 3 Smoke20×2 gate.