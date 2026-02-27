#!/usr/bin/env python3
import argparse
import json
import os

from day3_pipeline_core import (
    MANIFEST_DIR,
    TARGET_COUNTS,
    bootstrap_dirs,
    clean_and_redact,
    compute_metrics,
    discover_inputs,
    run_batch,
    synthesize_manifest,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Day-3 local automation pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Skip live API calls and emit command stubs")
    parser.add_argument("--api-url", default=os.getenv("DAY3_API_URL", "http://localhost:8000/api/validate/"))
    parser.add_argument("--api-token", default=os.getenv("DAY3_API_TOKEN", ""))
    args = parser.parse_args()

    bootstrap_dirs()
    discovered = discover_inputs()
    cleaned = clean_and_redact(discovered)
    final_manifest = synthesize_manifest(cleaned)
    results = run_batch(final_manifest, api_url=args.api_url, api_token=args.api_token, dry_run=args.dry_run)
    summary = compute_metrics(results)

    print("Day-3 pipeline complete")
    print(f"Discovered: {len(discovered)}")
    print(f"Final synthetic manifest: {len(final_manifest)} (targets={json.dumps(TARGET_COUNTS)})")
    print(f"Results: {len(results)}")
    print(f"Accuracy: {summary['accuracy']}")
    print(f"Signoff: data/day3/results/DAY3_SIGNOFF.md")
    print(f"Manifest: {MANIFEST_DIR / 'final_manifest.csv'}")


if __name__ == "__main__":
    main()
