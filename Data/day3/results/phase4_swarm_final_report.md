# Phase 4 SWARM FINAL REPORT (Subagent)

## Execution sequence completed
- Targeted mismatch sample: `--limit 10` using `Data/day3/manifest/phase4_targeted10_manifest.csv`
- 45-case rehearsal: `--limit 45` using `Data/day3/manifest/final_manifest.csv`
- 90-case rehearsal: `--limit 90` using `Data/day3/manifest/final_manifest.csv`

## Root causes
1. **API service contract hard-stop to 503 (database connectivity)**
   - `apps/api/app/routers/validate.py`, `run_validate_document` exception path (around `line 2282`)
   - `is_database_unavailable_error(e)` branch maps DB/connectivity failures to:
     - HTTP 503
     - `{ error: "database_unavailable", message: ... }`
   - Observed in all failed records: `HTTP Error 503: Service Unavailable | body={"error":"database_unavailable"...}`
2. **Runner crash on large/error response reads after non-2xx responses**
   - `tools/day3_pipeline/day3_pipeline_core.py`, `run_batch()` handler for `urllib_error.HTTPError` (around `line 648`)
   - Existing code read from `exc` unguarded: `exc.read()` could raise `ConnectionResetError`, aborting the 90-case run before full report write.

## Files changed
- `tools/day3_pipeline/day3_pipeline_core.py`
  - In `run_batch(...)` error handler, wrapped `HTTPError.read()` with defensive `try/except` fallback to empty body.
  - This stabilizes batch execution and allows 90-case completion even on repeated 503s.

## Before/after metrics
| Phase | total_records | comparable_records | accuracy | status_counts | critical_false_pass |
|---|---:|---:|---:|---|---:|
| Targeted (10 mismatch sample) | 10 | 0 | 0.0 | `{\"error\": 10}` | 0 |
| 45-case | 45 | 0 | 0.0 | `{\"error\": 45}` | 0 |
| 90-case | 90 | 0 | 0.0 | `{\"error\": 90}` | 0 |

### Confusion matrix snapshots (unknown-only drift)
- **Targeted (10):** pass→unknown 3, warn→unknown 2, reject→unknown 3, blocked→unknown 2
- **45-case:** pass→unknown 20, warn→unknown 20, reject→unknown 5, blocked→unknown 0
- **90-case:** pass→unknown 20, warn→unknown 20, reject→unknown 35, blocked→unknown 15
- **Confusion delta:** 10→45 added additional non-run samples to pass/warn/reject buckets; 45→90 added 30 more reject/blocked unknowns, but still no comparable predictions.

## Exact command for official Phase 4 rerun
```powershell
$env:DAY3_API_URL='http://localhost:8000/api/validate/'
python tools/day3_pipeline/run_batch_day3.py --rate-profile phase4_eval --limit 90 --no-resume
```

## Blockers still present (post-run)
1. **Phase 4 validation API is returning 503 database_unavailable for every case**
   - Next patch: provision a healthy DB (or switch backend to a supported local stub profile) before rerun.
2. **Manifest/endpoint environment in runner environment is not fully parity with production validation service**
   - Next patch: run against the canonical evaluation endpoint used by phase4_eval and avoid local ad-hoc stubs.
3. **No successful comparable predictions -> no verdict quality signals to validate phase4 quality gates**
   - Next patch: once API reaches 200 path, rerun pipeline and recompute all three checkpoints.

## Final official rerun decision
PHASE 4 OFFICIAL RERUN UNBLOCKED: NO

