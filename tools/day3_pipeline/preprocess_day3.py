#!/usr/bin/env python3
from day3_pipeline_core import MANIFEST_DIR, bootstrap_dirs, clean_and_redact, read_csv

if __name__ == "__main__":
    bootstrap_dirs()
    rows = read_csv(MANIFEST_DIR / "discovered_manifest.csv")
    cleaned = clean_and_redact(rows)
    print(f"cleaned={len(cleaned)}")
