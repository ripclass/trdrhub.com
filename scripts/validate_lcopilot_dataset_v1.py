#!/usr/bin/env python3
import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path("datasets/lcopilot_v1")
MANIFEST = ROOT / "manifests" / "master_manifest.csv"


def fail(msg: str) -> None:
    raise SystemExit(f"VALIDATION_FAIL: {msg}")


def main() -> None:
    if not MANIFEST.exists():
        fail("Manifest CSV not found")

    rows = []
    with open(MANIFEST, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if len(rows) != 200:
        fail(f"Expected 200 cases, got {len(rows)}")

    verdict_counter = Counter(r["expected_verdict"] for r in rows)
    if verdict_counter != Counter({"pass": 80, "warn": 80, "reject": 40}):
        fail(f"Verdict mix mismatch: {dict(verdict_counter)}")

    split_counter = Counter(r["split"] for r in rows)
    if split_counter != Counter({"train": 140, "val": 30, "test": 30}):
        fail(f"Split mismatch: {dict(split_counter)}")

    role_counter = Counter(r["role"] for r in rows)
    if role_counter != Counter({"exporter": 100, "importer": 100}):
        fail(f"Role mismatch: {dict(role_counter)}")

    for r in rows:
        pdf = Path(r["pdf_path"])
        truth = Path(r["truth_json_path"])
        if not pdf.exists():
            fail(f"Missing PDF: {pdf}")
        if not truth.exists():
            fail(f"Missing truth JSON: {truth}")
        with open(truth, encoding="utf-8") as jf:
            record = json.load(jf)
        if record["case_id"] != r["case_id"]:
            fail(f"Case ID mismatch for {r['case_id']}")

    print("VALIDATION_PASS")
    print(f"verdicts={dict(verdict_counter)}")
    print(f"splits={dict(split_counter)}")
    print(f"roles={dict(role_counter)}")


if __name__ == "__main__":
    main()
