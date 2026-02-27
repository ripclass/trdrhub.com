#!/usr/bin/env python3
import argparse
import os
from day3_pipeline_core import MANIFEST_DIR, bootstrap_dirs, compute_metrics, read_csv, run_batch

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Day3 batch validation")
    parser.add_argument("--limit", type=int, default=None, help="Run first N manifest rows")
    parser.add_argument("--smoke20", action="store_true", help="Shortcut for safe 20-case smoke run")
    parser.add_argument("--dry-run", action="store_true", help="Skip API calls and emit command stubs")
    parser.add_argument("--no-resume", action="store_true", help="Disable resume-safe mode")
    parser.add_argument("--min-interval", type=float, default=1.2, help="Minimum seconds between requests")
    parser.add_argument("--retries-429", type=int, default=5, help="Max retries for HTTP 429")
    args = parser.parse_args()

    bootstrap_dirs()
    rows = read_csv(MANIFEST_DIR / "final_manifest.csv")
    api_url = os.getenv("DAY3_API_URL", "http://localhost:8000/api/validate/")
    token = os.getenv("DAY3_API_TOKEN", "")
    dry_run = args.dry_run or (os.getenv("DAY3_DRY_RUN", "0") == "1")
    run_limit = 20 if args.smoke20 else args.limit
    out = run_batch(
        rows,
        api_url=api_url,
        api_token=token,
        dry_run=dry_run,
        limit=run_limit,
        resume_safe=not args.no_resume,
        max_retries_429=args.retries_429,
        min_interval_seconds=args.min_interval,
    )
    summary = compute_metrics(out)

    print(f"batch_results={len(out)}")
    print(f"comparable_records={summary['comparable_records']}")
    print(f"accuracy={summary['accuracy']}")
    print(f"status_counts={summary['status_counts']}")
    if args.smoke20:
        print("smoke20_expected=success_rate>=90%,_429<=5%,_pass_blocked<=20%")
