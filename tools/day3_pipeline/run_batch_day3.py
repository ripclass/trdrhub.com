#!/usr/bin/env python3
import os
from day3_pipeline_core import MANIFEST_DIR, bootstrap_dirs, read_csv, run_batch

if __name__ == "__main__":
    bootstrap_dirs()
    rows = read_csv(MANIFEST_DIR / "final_manifest.csv")
    api_url = os.getenv("DAY3_API_URL", "http://localhost:8000/api/validate/")
    token = os.getenv("DAY3_API_TOKEN", "")
    dry_run = os.getenv("DAY3_DRY_RUN", "0") == "1"
    out = run_batch(rows, api_url=api_url, api_token=token, dry_run=dry_run)
    print(f"batch_results={len(out)}")
