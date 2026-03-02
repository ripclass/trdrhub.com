# TRDRHub Phase 3 Smoke20 x2 Gate Report

## Commands run (exact)
1. `$env:DAY3_API_URL='http://localhost:8000/api/validate/'`
2. `python .\tools\day3_pipeline\run_batch_day3.py --smoke20 --min-interval 3.0 --retries-429 8`
3. Snapshot artifacts to run1 labels:
   - `day3_run1_20260301_132400_day3_results.jsonl`
   - `day3_run1_20260301_132400_metrics_summary.json`
   - `day3_run1_20260301_132400_confusion_matrix.csv`
   - `day3_run1_20260301_132400_failed_cases.csv`
   - `day3_run1_20260301_132400_rate_limit_stats.json`
4. `$env:DAY3_API_URL='http://localhost:8000/api/validate/'`
5. `python .\tools\day3_pipeline\run_batch_day3.py --smoke20 --min-interval 3.0 --retries-429 8 --no-resume`
6. Snapshot artifacts to run2 labels:
   - `day3_run2_20260301_132627_day3_results.jsonl`
   - `day3_run2_20260301_132627_metrics_summary.json`
   - `day3_run2_20260301_132627_confusion_matrix.csv`
   - `day3_run2_20260301_132627_failed_cases.csv`
   - `day3_run2_20260301_132627_rate_limit_stats.json`

## Run metrics

| Gate input | Run1 | Run2 |
|---|---:|---:|
| comparable_records | 1 | 1 |
| accuracy | 0.0000 | 0.0000 |
| critical_false_pass | 0 | 0 |
| HTTP 422 | 0 | 0 |
| cases_exhausted_after_429 | 0 | 0 |
| 429 rate (`cases_exhausted_after_429 / 20`) | 0.00% | 0.00% |
| pass_blocked (`pass_actual_blocked / pass_expected`) | 1 / 20 = 0.05 | 1 / 20 = 0.05 |
| rerun_consistency (run1 vs run2 verdict vectors) | 1.00 | 1.00 |

## Gate results

- Comparable >= 18/20: **FAIL** (1)
- Accuracy >= 0.70: **FAIL** (0.00)
- Critical_false_pass == 0: **PASS** (0)
- HTTP 422 == 0: **PASS** (0)
- 429 exhaustion <= 5%: **PASS** (0.00%)
- Pass-blocked < 0.30: **PASS** (0.05)
- Rerun_consistency >= 0.95: **PASS** (1.00)

## Decision
**FAIL** (hard gate fail: comparable/accuracy are below threshold). 

### Blocker classification (runtime/schema)
**Runtime blocker in validator endpoint.** Both runs returned `HTTP Error 500 ... validation_internal_error ... AttributeError` on 19/20 cases each run; only one case returned `actual_verdict=blocked` and still failed comparability (`comparable_records=1`).

## Next action
Fix backend `POST /api/validate/` 500 AttributeError path (validation_internal_error) and rerun this exact Phase-3 protocol once resolved.