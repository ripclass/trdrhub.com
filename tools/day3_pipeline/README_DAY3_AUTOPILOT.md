# Day-3 Local Autopilot (Paste folders -> run 1 command -> get report)

This pipeline keeps all data local and automates Day-3 preparation + validation evidence.

## 0) Paste your folders

Put your files in:

- `data/real/` (real bundles)
- `data/synthetic_seed/` (seed docs for synthetic scenario expansion)

## 1) Run one command (PowerShell)

From repo root:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\day3_pipeline\run_day3.ps1
```

## What it does

1. Bootstraps required folders
2. Auto-discovers files and creates a draft manifest
3. Cleans + redacts text artifacts into `data/day3/generated/cleaned`
4. Builds a synthetic scenario manifest with target counts:
   - 20 pass
   - 20 warn
   - 20 reject
   - 15 ocr_noise
   - 15 sanctions_tbml_shell
5. Runs batch validation (real API call if file artifacts exist, otherwise command stubs)
6. Computes metrics/evidence and produces signoff draft

## Outputs

- `data/day3/manifest/discovered_manifest.csv`
- `data/day3/manifest/cleaned_manifest.csv`
- `data/day3/manifest/final_manifest.csv`
- `data/day3/results/day3_results.jsonl`
- `data/day3/results/validation_commands.ps1`
- `data/day3/results/confusion_matrix.csv`
- `data/day3/results/failed_cases.csv`
- `data/day3/results/metrics_summary.json`
- `data/day3/results/DAY3_SIGNOFF.md`

## API/Auth notes

Set only if needed by your local API:

- `DAY3_API_URL` (default: `http://localhost:8000/api/validate/`)
- `DAY3_API_TOKEN` (optional bearer token)

Example:

```powershell
$env:DAY3_API_URL="http://localhost:8000/api/validate/"
$env:DAY3_API_TOKEN="your-token-if-required"
```

If API call is not possible for a case, pipeline still emits runnable command stubs in `validation_commands.ps1`.

## Python direct runner

```powershell
python .\tools\day3_pipeline\run_day3_pipeline.py
```

## Smoke presets (safe pacing)

```powershell
# 20-case smoke, resume-safe, low-rate to avoid 429
python .\tools\day3_pipeline\run_batch_day3.py --smoke20 --min-interval 1.5 --retries-429 6

# Full rerun with resume-safe (skips already successful cases)
python .\tools\day3_pipeline\run_batch_day3.py --min-interval 1.2 --retries-429 5
```

Expected smoke criteria:
- success_rate >= 90%
- HTTP 429 <= 5%
- blocked in PASS <= 20%

Additional output:
- `data/day3/results/rate_limit_stats.json`