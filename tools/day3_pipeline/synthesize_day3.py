#!/usr/bin/env python3
from day3_pipeline_core import MANIFEST_DIR, bootstrap_dirs, read_csv, synthesize_manifest

if __name__ == "__main__":
    bootstrap_dirs()
    rows = read_csv(MANIFEST_DIR / "cleaned_manifest.csv")
    final_rows = synthesize_manifest(rows)
    print(f"final_manifest_rows={len(final_rows)}")
