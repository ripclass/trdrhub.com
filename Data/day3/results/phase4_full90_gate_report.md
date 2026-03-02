# Phase 4 Full-90 Gate Report

## Execution Summary
- Pipeline: `tools/day3_pipeline/run_batch_day3.py`
- Command used: `python .\\tools\\day3_pipeline\\run_batch_day3.py --limit 90 --no-resume --retries-429 1 --min-interval 0.2`
- Endpoint: `DAY3_API_URL=http://localhost:8000/api/validate/`
- Resume contamination: **disabled** (`--no-resume`) and `resume_skipped_cases=0`
- Snapshot artifacts written (requested names):
  - `day3_results.jsonl`
  - `metrics_summary.json`
  - `confusion_matrix.csv`
  - `failed_cases.csv`
  - `rate_limit_stats.json`

## Snapshot Metrics
| Metric | Value |
|---|---:|
| Total records | 90 |
| Comparable records | 22 |
| Accuracy | 0.2727 |
| Critical false pass | 10 |
| 5xx systemic failures | 0 |
| 429 exhaustion (cases_exhausted_after_429 / total) | 57 / 90 = 63.33% |
| Status counts | `error`: 58, `ok`: 32 |
| Rate-limit retries attempted | 77 |
| Max retry attempts used | 1 |

## Gate Evaluation
- `comparable >= 85/90`: **FAIL** (22)
- `accuracy >= 0.65`: **FAIL** (0.2727)
- `critical_false_pass == 0`: **FAIL** (10)
- `429 exhaustion <= 5%`: **FAIL** (63.33%)
- `no runtime blocker / no systemic 5xx class`: **FAIL (runtime blocker)**
  - Evidence: 58 error rows, including **57 cases exhausted after 429** and **1 timeout**; no 5xx observed

## Confidence Guardrail (Wilson-style)
- Using comparable records only: 6 correct / 22 comparable (accuracy 0.2727)
- 95% Wilson CI: **[0.1315, 0.4815]**
- Interpretation: performance estimate is below threshold with wide uncertainty and too few effective comparable outcomes.

## Final Decision
**PHASE 4 FAIL**

## One-line Next Action
- Unblock API quota/rate handling (increase capacity or adjust throttling strategy/backoff) and re-run full 90 with `--no-resume` before any Phase 4 approval consideration.
