#!/usr/bin/env python3
import argparse
import os
from day3_pipeline_core import MANIFEST_DIR, bootstrap_dirs, compute_metrics, read_csv, run_batch

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Day3 batch validation")
    parser.add_argument("--limit", type=int, default=None, help="Run first N manifest rows (smoke mode)")
    parser.add_argument("--dry-run", action="store_true", help="Skip API calls and emit command stubs")
    args = parser.parse_args()

    bootstrap_dirs()
    rows = read_csv(MANIFEST_DIR / "final_manifest.csv")
    api_url = os.getenv("DAY3_API_URL", "http://localhost:8000/api/validate/")
    token = os.getenv("DAY3_API_TOKEN", "")
    dry_run = args.dry_run or (os.getenv("DAY3_DRY_RUN", "0") == "1")
    out = run_batch(rows, api_url=api_url, api_token=token, dry_run=dry_run, limit=args.limit)
    summary = compute_metrics(out)

    print(f"batch_results={len(out)}")
    print(f"comparable_records={summary['comparable_records']}")
    print(f"accuracy={summary['accuracy']}")
    print(f"status_counts={summary['status_counts']}")
