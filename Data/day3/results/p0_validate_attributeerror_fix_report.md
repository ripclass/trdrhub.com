# P0 /api/validate AttributeError Fix Report

## Task
- Reproduce single failing case
- Identify root cause and exact code path
- Apply minimal safe patch
- Verify via single-case probe + Smoke20 rerun

## 1) Reproduction (pre-fix evidence)
Executed against the currently running production-like endpoint `http://127.0.0.1:8000/api/validate/`.

### Single-case failure
- `python tools/day3_pipeline/run_batch_day3.py --limit 1`
- Result: `status_counts={'error': 1}`
- First record now: 
  - `status: error`
  - HTTP error body: `{"detail":{"error_code":"validation_internal_error","message":"Validation processing failed. Please retry or contact support.","error_type":"AttributeError"}}`

### Smoke20 failure
- `DAY3_API_URL=http://127.0.0.1:8000/api/validate/ python tools/day3_pipeline/run_batch_day3.py --smoke20 --min-interval 0.1`
- Result: `status_counts={'error': 19, 'ok': 1}` (19/20 failing with 500, 1 success)
- All 19 failures are HTTP 500 with `error_type: AttributeError` in response payload.

## 2) Root cause identification
**File:** `apps/api/app/routers/validate.py`  
**Function:** `validate_doc` (main POST endpoint)

### Exact failure line
`has_lc_document` calculation used:
- `payload.get("lc", {}).get("raw_text")`
- This assumes `payload["lc"]` is always dict-like.
- In failing requests, `payload["lc"]` can be `None`/non-dict (e.g., provided as `null`/invalid payload shape). `NoneType` does not have `.get`, causing `AttributeError` and surfacing as `validation_internal_error`.

A related hardening issue was also present in detected-doc collection (`doc.get(...)` when entries could be non-dict), so it was hardened too for safety.

## 3) Minimal patch applied
**File changed:** `apps/api/app/routers/validate.py`

### Changes
- Added type-safe extraction for detected document entries:
  - `if isinstance(doc, dict)` in list comprehension for `detected_doc_types`.
- Replaced unsafe access with explicit payload normalization:
  - `lc_payload = payload.get("lc") if isinstance(payload.get("lc"), dict) else {}`
  - `bool(lc_payload.get("raw_text"))` for LC detection.

This is a minimal, reversible change limited to one endpoint function.

## 4) Why this fixes the issue
- Prevents calling `.get` on `None`/non-dict `payload['lc']`, removing the `AttributeError` path that triggers 500.
- Keeps original LC detection semantics when lc is proper dict.
- Keeps behavior stable for normal requests while making malformed/payload-variant shapes non-fatal.

## 5) Verification outputs
### A) Syntax check
- `python -m py_compile app/routers/validate.py` (from `apps/api`) passed.

### B) Single-case probe on patched local endpoint (`127.0.0.1:8001`)
Request with explicit `lc=null` form field + one file:
- Command: `curl -X POST http://127.0.0.1:8001/api/validate/ -F files=@... -F lc=null ...`
- Result: **HTTP 200** with full structured response (`validation_blocked`, non-500).
- Confirms guard works at the previously failing lc_raw_text access path.

### C) Smoke20 rerun (immediate proof)
- `DAY3_API_URL=http://127.0.0.1:8001/api/validate/ python tools/day3_pipeline/run_batch_day3.py --smoke20 --min-interval 0.1`
- Result summary: `batch_results=20`, `status_counts={'ok': 19, 'error': 1}` (1 pre-existing throttling/429 case in this local run, no AttributeError).
- No AttributeError-style HTTP 500 observed on this patched path.

## 6) Files changed
- `apps/api/app/routers/validate.py`
  - around lines ~500–515 in `validate_doc`

## 7) Phase 3 rerun status
- **No (for current running endpoint on 8000):** the environment currently pointed to by port 8000 is still serving previous code and still returns 500 on ~19/20 cases.
- **Yes, after code update deployment/restart:** patch is in place in workspace and targeted to the root cause path; next phase-3 run should be re-executed against updated service process (or 8001 with same build) to confirm full pass.