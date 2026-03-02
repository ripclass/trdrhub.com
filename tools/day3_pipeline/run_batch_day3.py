#!/usr/bin/env python3
import argparse
import os
from day3_pipeline_core import MANIFEST_DIR, bootstrap_dirs, compute_metrics, read_csv, run_batch


RATE_LIMIT_PROFILES = {
    "default": {
        "min_interval_seconds": 1.2,
        "max_retries_429": 5,
        "base_backoff_seconds": 1.5,
        "max_backoff_seconds": 30.0,
    },
    "phase4_eval": {
        "min_interval_seconds": 0.9,
        "max_retries_429": 8,
        "base_backoff_seconds": 2.5,
        "max_backoff_seconds": 60.0,
        "api_token": "phase4_eval_token",
    },
}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Day3 batch validation")
    parser.add_argument("--limit", type=int, default=None, help="Run first N manifest rows")
    parser.add_argument("--smoke20", action="store_true", help="Shortcut for safe 20-case smoke run")
    parser.add_argument("--dry-run", action="store_true", help="Skip API calls and emit command stubs")
    parser.add_argument("--no-resume", action="store_true", help="Disable resume-safe mode")
    parser.add_argument("--rate-profile", choices=RATE_LIMIT_PROFILES.keys(), default="default", help="Rate-limit/retry profile")
    parser.add_argument("--min-interval", type=float, default=None, help="Minimum seconds between requests")
    parser.add_argument("--retries-429", type=int, default=None, help="Max retries for HTTP 429")
    parser.add_argument("--base-backoff-seconds", type=float, default=None, help="Base backoff for retries")
    parser.add_argument("--max-backoff-seconds", type=float, default=None, help="Max backoff cap for retries")
    parser.add_argument("--eval-token", default=None, help="Optional override token for phase4 eval profile")
    args = parser.parse_args()

    bootstrap_dirs()
    rows = read_csv(MANIFEST_DIR / "final_manifest.csv")
    api_url = os.getenv("DAY3_API_URL", "http://localhost:8000/api/validate/")

    profile = RATE_LIMIT_PROFILES[args.rate_profile]

    token = os.getenv("DAY3_API_TOKEN", "")
    if not token and args.rate_profile == "phase4_eval":
        token = args.eval_token or profile.get("api_token", "")

    dry_run = args.dry_run or (os.getenv("DAY3_DRY_RUN", "0") == "1")
    run_limit = 20 if args.smoke20 else args.limit

    min_interval_seconds = args.min_interval if args.min_interval is not None else profile["min_interval_seconds"]
    max_retries_429 = args.retries_429 if args.retries_429 is not None else profile["max_retries_429"]
    base_backoff_seconds = args.base_backoff_seconds if args.base_backoff_seconds is not None else profile["base_backoff_seconds"]
    max_backoff_seconds = args.max_backoff_seconds if args.max_backoff_seconds is not None else profile["max_backoff_seconds"]

    evaluation_mode = (
        os.getenv("DAY3_EVALUATION_MODE", "").strip().lower() in {"1", "true", "yes"}
    ) or args.rate_profile == "phase4_eval"

    out = run_batch(
        rows,
        api_url=api_url,
        api_token=token,
        dry_run=dry_run,
        limit=run_limit,
        resume_safe=not args.no_resume,
        max_retries_429=max_retries_429,
        base_backoff_seconds=base_backoff_seconds,
        max_backoff_seconds=max_backoff_seconds,
        min_interval_seconds=min_interval_seconds,
        evaluation_mode=evaluation_mode,
    )
    summary = compute_metrics(out)

    print(f"batch_results={len(out)}")
    print(f"comparable_records={summary['comparable_records']}")
    print(f"accuracy={summary['accuracy']}")
    print(f"status_counts={summary['status_counts']}")
    if args.smoke20:
        print("smoke20_expected=success_rate>=90%,_429<=5%,_pass_blocked<=20%")
    print(f"rate_profile={args.rate_profile}")
    print(f"evaluation_mode={evaluation_mode}")
