#!/usr/bin/env python3
from __future__ import annotations

import csv
import random
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

from day3_pipeline_core import (
    ROOT,
    MANIFEST_DIR,
    GENERATED,
    RESULTS,
    MANIFEST_FIELDS,
    TARGET_COUNTS,
    read_csv,
    write_csv,
    run_batch,
    compute_metrics,
)

API_EXT = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff"}
PASS_MUST_HAVE_TOKENS = ("lc", "letter_of_credit", "letter of credit")
PASS_BAD_TOKENS = ("packinglist", "packing_list", "insurance", "certificate", "invoice", "bill", "awb", "bl")


def _ext(path: str) -> str:
    return Path(path or "").suffix.lower()


def _is_api_compatible(path: str) -> bool:
    return _ext(path) in API_EXT


def _mk_stub_pdf(path: Path, label: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Deterministic tiny valid PDF payload.
    body = f"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 144]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n4 0 obj<</Length 68>>stream\nBT /F1 12 Tf 24 100 Td ({label}) Tj ET\nendstream endobj\n5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\nxref\n0 6\n0000000000 65535 f \ntrailer<</Size 6/Root 1 0 R>>\nstartxref\n9\n%%EOF\n"
    path.write_bytes(body.encode("latin-1", errors="ignore"))


def classify(row: Dict[str, str]) -> str:
    src = (row.get("source_path") or "").lower()
    if "flagged-tbml" in src or "pacs.009" in src or "pacs008" in src or "sanction" in src:
        return "sanctions_tbml_shell"
    if "import-minor d" in src:
        return "warn"
    if "import-major d" in src or "export-major d" in src:
        return "reject"
    if "real/2025" in src:
        return "ocr_noise"
    if "all correct" in src or "ideal sample" in src:
        return "pass"
    return "warn"


def expected_for(scenario: str) -> str:
    return {
        "pass": "pass",
        "warn": "warn",
        "reject": "reject",
        "ocr_noise": "blocked",
        "sanctions_tbml_shell": "reject",
    }[scenario]


def _pass_readiness(row: Dict[str, str]) -> tuple[bool, list[str]]:
    src = (row.get("source_path") or "").lower()
    cleaned = (row.get("cleaned_path") or "").lower()
    name = Path(cleaned or src).name.lower()
    reasons: list[str] = []

    if "all correct" not in src:
        reasons.append("not_from_all_correct_bucket")
    if not any(tok in src or tok in name for tok in PASS_MUST_HAVE_TOKENS):
        reasons.append("missing_lc_signal")
    if any(tok in name for tok in PASS_BAD_TOKENS):
        reasons.append("non_lc_doc_type")

    # lightweight text check for non-binary artifacts
    p = ROOT / row.get("cleaned_path", "")
    if p.exists() and p.suffix.lower() in {".txt", ".md", ".json", ".xml", ".csv"}:
        txt = p.read_text(encoding="utf-8", errors="ignore").lower()
        required = ["lc", "credit", "amount", "applicant", "beneficiary"]
        missing = [k for k in required if k not in txt]
        if missing:
            reasons.append("missing_core_lc_fields:" + ",".join(missing))

    return (len(reasons) == 0, reasons)


def _demote_pass_candidate(reasons: list[str]) -> tuple[str, str]:
    """Fail-closed demotion of weak PASS candidates into warn/blocked buckets."""
    hard_block_prefixes = ("missing_core_lc_fields:", "non_lc_doc_type")
    if any(r.startswith(hard_block_prefixes) for r in reasons):
        return "ocr_noise", "blocked"
    return "warn", "warn"


def build_parents(cleaned_rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    stubs_dir = GENERATED / "stubs"
    upload_ready_dir = GENERATED / "upload_ready"
    out = []
    for r in cleaned_rows:
        row = dict(r)
        scenario = classify(row)
        row["scenario"] = scenario
        row["expected_verdict"] = expected_for(scenario)

        cleaned = row.get("cleaned_path", "")
        if not _is_api_compatible(cleaned):
            # deterministic API-compatible stub for pipeline acceptance
            stub = stubs_dir / f"{row['case_id']}.pdf"
            if not stub.exists():
                _mk_stub_pdf(stub, f"STUB {row['case_id']} {scenario}")
            row["cleaned_path"] = stub.relative_to(ROOT).as_posix()
            row["notes"] = (row.get("notes", "") + " | deterministic_stub_pdf").strip()
        else:
            # normalize upload filename/path to avoid multipart filename edge-cases
            src_path = ROOT / cleaned
            normalized = upload_ready_dir / f"{row['case_id']}{src_path.suffix.lower()}"
            normalized.parent.mkdir(parents=True, exist_ok=True)
            if not normalized.exists() or normalized.stat().st_size != src_path.stat().st_size:
                shutil.copy2(src_path, normalized)
            row["cleaned_path"] = normalized.relative_to(ROOT).as_posix()

        # quarantine weak scans from PASS bucket + enforce readiness gate
        src = (row.get("source_path") or "").lower()
        if row["scenario"] == "pass" and ("real/2025" in src or "flagged" in src or "pacs" in src):
            row["scenario"] = "ocr_noise"
            row["expected_verdict"] = "blocked"
            row["notes"] = (row.get("notes", "") + " | quarantined_weak_lc_scan").strip()

        if row["scenario"] == "pass":
            ready, reasons = _pass_readiness(row)
            if not ready:
                demoted_scenario, demoted_verdict = _demote_pass_candidate(reasons)
                row["scenario"] = demoted_scenario
                row["expected_verdict"] = demoted_verdict
                row["notes"] = (
                    row.get("notes", "")
                    + f" | pass_quality_gate_failed:{';'.join(reasons)}"
                    + f" | moved_to_{demoted_scenario}_candidate_bucket"
                ).strip()

        row["run_enabled"] = "1"
        out.append(row)
    return out


def synthesize_90(parents: List[Dict[str, str]], seed: int = 99) -> List[Dict[str, str]]:
    random.seed(seed)
    by = defaultdict(list)
    for p in parents:
        by[p["scenario"]].append(p)

    counts = TARGET_COUNTS
    rows = []
    for scenario, count in counts.items():
        pool = by.get(scenario)
        if not pool:
            if scenario == "pass":
                continue
            pool = parents
        for i in range(1, count + 1):
            parent = random.choice(pool)
            row = dict(parent)
            row["case_id"] = f"forge_x_{scenario}_{i:03d}"
            row["source_type"] = "synthetic"
            row["synthetic_parent_id"] = parent["case_id"]
            row["scenario"] = scenario
            row["expected_verdict"] = expected_for(scenario)
            row["notes"] = f"forge_x_api_only synthetic from {parent['case_id']}"
            row["run_enabled"] = "1"
            rows.append(row)
    return rows


def smoke10(parents: List[Dict[str, str]], seed: int = 7) -> List[Dict[str, str]]:
    random.seed(seed)
    by = defaultdict(list)
    for p in parents:
        by[p["scenario"]].append(p)
    plan = [("pass", 2), ("warn", 2), ("reject", 2), ("ocr_noise", 2), ("sanctions_tbml_shell", 2)]
    rows = []
    for scenario, n in plan:
        pool = by.get(scenario) or parents
        picks = random.sample(pool, k=min(n, len(pool)))
        for i, parent in enumerate(picks, 1):
            row = dict(parent)
            row["case_id"] = f"smoke_{scenario}_{i:02d}"
            row["source_type"] = "synthetic"
            row["synthetic_parent_id"] = parent["case_id"]
            row["scenario"] = scenario
            row["expected_verdict"] = expected_for(scenario)
            row["notes"] = f"smoke-ready from {parent['case_id']}"
            row["run_enabled"] = "1"
            rows.append(row)
    return rows


def main() -> None:
    import argparse, os, json

    parser = argparse.ArgumentParser(description="Forge-X manifest utilities")
    parser.add_argument("--run-smoke", action="store_true", help="Also execute smoke manifest against API")
    parser.add_argument("--smoke-limit", type=int, default=20, help="Cases to run when --run-smoke is set")
    args = parser.parse_args()

    cleaned = read_csv(MANIFEST_DIR / "cleaned_manifest.csv")
    parents = build_parents(cleaned)

    smoke_rows = smoke10(parents)
    write_csv(MANIFEST_DIR / "smoke_ready_manifest.csv", smoke_rows, MANIFEST_FIELDS)

    forge_rows = synthesize_90(parents)
    write_csv(MANIFEST_DIR / "forge_x_api_only_90_manifest.csv", forge_rows, MANIFEST_FIELDS)
    write_csv(MANIFEST_DIR / "final_manifest.csv", forge_rows, MANIFEST_FIELDS)

    if args.run_smoke:
        api_url = os.getenv("DAY3_API_URL", "http://localhost:8000/api/validate/")
        token = os.getenv("DAY3_API_TOKEN", "")
        results = run_batch(
            smoke_rows,
            api_url=api_url,
            api_token=token,
            dry_run=False,
            limit=args.smoke_limit,
            resume_safe=True,
            min_interval_seconds=1.5,
            max_retries_429=6,
        )
        summary = compute_metrics(results)
        (RESULTS / "smoke10_summary_from_smoke_ready.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
