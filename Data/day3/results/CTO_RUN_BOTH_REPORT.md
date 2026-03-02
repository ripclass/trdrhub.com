# CTO Run-BOTH Consolidated Report

Generated: 2026-02-27 (Asia/Dhaka)

## Track A — Day3 input quality fix + smoke rerun

### What was fixed
1. **Unsupported-only cases addressed**
   - Added deterministic API-compatible PDF stubs for non-uploadable text-only inputs (`.txt`) under:
     - `data/day3/generated/stubs/*.pdf`
   - Smoke and Forge-X manifests now contain only API-compatible payload paths.

2. **Weak LC scans quarantined from PASS**
   - PASS candidates from weak/real scan pools (e.g., `data/real/2025`, flagged/tbml/pacs-like docs) are reclassified away from PASS.

3. **Scenario/expected label repair**
   - Re-mapped scenarios with explicit oracle expectations:
     - pass -> pass
     - warn -> warn
     - reject -> reject
     - ocr_noise -> blocked
     - sanctions_tbml_shell -> reject

4. **Smoke-ready manifest regenerated (10 cases)**
   - `data/day3/manifest/smoke_ready_manifest.csv`
   - Balanced split: 2 each for pass/warn/reject/ocr_noise/sanctions_tbml_shell.

### Smoke execution result (10 cases)
- Run attempted live against default API: `http://localhost:8000/api/validate/`
- Output summary: `data/day3/results/smoke10_summary_from_smoke_ready.json`

Metrics:
- total_records: **10**
- comparable_records: **0**
- accuracy: **0.0**
- status_counts: **{ error: 10 }**

Top errors:
1. `<urlopen error [WinError 10061] No connection could be made because the target machine actively refused it>` (10/10)

Interpretation:
- Data-quality contract is improved (no missing files, no non-API extensions in smoke manifest), but live smoke quality is **not assessable** because the validation API was offline.

## Track B — Forge-X API-only synthetic generation batch (90 cases)

### Batch generated
- Manifest: `data/day3/manifest/forge_x_api_only_90_manifest.csv`
- Distribution:
  - 20 PASS
  - 20 WARN
  - 20 REJECT
  - 15 OCR-noise
  - 15 sanctions/TBML/shell

### Contract checks
- Total rows: **90**
- Missing payload files: **0**
- Non-API-compatible payloads in manifest: **0**
- Oracle labels included: **yes** (`scenario` + `expected_verdict`)

### Feasibility smoke on generated batch
- Live smoke against generated batch is currently blocked by API unavailability (same `WinError 10061`).
- Dry contract validation (file/path/type) passes locally.

## Files changed/added
- `tools/day3_pipeline/forge_x_manifest_tools.py` (new utility)
- `data/day3/manifest/smoke_ready_manifest.csv`
- `data/day3/manifest/forge_x_api_only_90_manifest.csv`
- `data/day3/generated/stubs/*.pdf` (deterministic API stubs)
- `data/day3/results/smoke10_summary_from_smoke_ready.json`
- `data/day3/results/day3_results.jsonl` (latest smoke attempt)
- `data/day3/results/failed_cases.csv` (latest smoke attempt)

## Exact commands

### Rebuild manifests + run smoke-ready attempt
```powershell
python .\tools\day3_pipeline\forge_x_manifest_tools.py
```

### Run full 90-case Forge-X batch (after API is up)
```powershell
Copy-Item .\data\day3\manifest\forge_x_api_only_90_manifest.csv .\data\day3\manifest\final_manifest.csv -Force
$env:DAY3_API_URL="http://localhost:8000/api/validate/"
python .\tools\day3_pipeline\run_batch_day3.py
```

### Optional: smoke only first 10 from full manifest
```powershell
$env:DAY3_API_URL="http://localhost:8000/api/validate/"
python .\tools\day3_pipeline\run_batch_day3.py --limit 10
```

## Expected API cost notes
- Request volume for full batch: **90 validation calls**.
- Cost depends on backend provider billing (not exposed in this repo).
- Practical estimate model:
  - Total cost = `90 x avg_cost_per_validation_call`
  - If avg call cost is C (USD), total ~= `90C`.
- Runtime impact is material for OCR-heavy/weak-scan cases; budget should include retries for transient API failures.

## Readiness status for full Day3 run
- **Manifest readiness:** READY (API-compatible payload coverage complete)
- **Infrastructure readiness:** BLOCKED (local validation API not reachable)
- **Go/No-Go now:** **NO-GO** until API endpoint is online
