# P0 Validate AttributeError Round2 Report

## Objective
- Eliminate remaining `/api/validate` `validation_internal_error` AttributeError (`'str' object has no attribute 'get'`) on local `:8000` endpoint.
- Reproduce, capture traceback, patch minimally, restart/rebuild, and run proof checks.

## 1) Reproduction on :8000 + full traceback capture
- Ran targeted request against `/api/validate` with the smoke manifest multipart case via `tmp_probe.py` (multipart upload from `Data/day3/manifest/final_manifest.csv`).
- Captured container logs (`docker logs trdrhub-api`) and confirmed traceback:
  - `app.routers._legacy_validate - ERROR - Validation endpoint exception`
  - `AttributeError: 'str' object has no attribute 'get'`
  - Source chain included:
    - `/app/app/routers/validate.py` (line around 587): `lc_type_guess = detect_lc_type(lc_context, shipment_context)`
    - `/app/app/services/lc_classifier.py` (line around 52): `.get(...)` on non-dict `ports_context`

## 2) Root cause (exact failing paths)
- The prior fix normalized top-level `payload["lc"]`, but did not guarantee downstream nested `ports` shape before `detect_lc_type`.
- In runtime payloads, `lc_context` itself was dict-like, but `lc_context["ports"]` was arriving as `str` in some legacy path cases.
- `detect_lc_type()` immediately did `ports_context.get(...)` and raised AttributeError, causing 500 `validation_internal_error`.

## 3) Applied patch(es)
### `trdrhub.com/apps/api/app/services/lc_classifier.py`
- In `detect_lc_type(...)`, added defensive normalization for nested `ports_context`:
  - `ports_context = lc_context.get("ports") or {}`
  - if not dict, coerce to `{}`.

### `trdrhub.com/apps/api/app/routers/validate.py`
- Hardened `lc`/`shipment` context normalization before type detection:
  - replace `payload.get("lc")` truthy checks with key-presence checks and normalize if present.
  - set `lc_context = _normalize_lc_payload_structures(...)` and fallback to `{}` when not dict.
  - validate `shipment_context` and fallback to `{}` when not dict.

### `trdrhub.com/apps/api/app/routers/validate_v1_backup.py`
- Mirrored the same defensive guards for legacy route path:
  - same `payload["lc"]` normalize + dict checks
  - `lc_context` and `shipment_context` fallback to `{}` when non-dict.

## 4) Restart / rebuild
- Restarted and rebuilt API after patches:
  - `docker compose -f trdrhub.com/docker-compose.yml down api`
  - `docker compose -f trdrhub.com/docker-compose.yml up -d --build api`

## 5) Verification
### Single-case probe
- `tmp` multipart probe (case from `final_manifest.csv`) on `/api/validate/` now returns non-500.

### Smoke20 one-run proof
- Executed:
  - `python tools/day3_pipeline/run_batch_day3.py --smoke20 --min-interval 0.05`
- Result summary (`Data/day3/results/metrics_summary.json`):
  - `total_records: 20`
  - `comparable_records: 19`
  - `status_counts: ok=19, error=1`
- `failed_cases.csv` now shows only:
  - one `error` case = `HTTP 429 Too Many Requests` (rate-limited), **no `validation_internal_error`**/AttributeError 500 entries.

## 6) Current status / next blocker
- **Root bug fixed** for remaining AttributeError path (ports shape not guaranteed as dict).
- **Phase 3 full rerun now unblocked for this specific P0 class of failures** (no longer getting 500 AttributeError). Remaining blocker is infra-side rate limiting causing one `429` in one-run smoke (`forge_x_pass_011`), not validation internal server errors.

## Files changed
- `apps/api/app/services/lc_classifier.py`
- `apps/api/app/routers/validate.py`
- `apps/api/app/routers/validate_v1_backup.py`