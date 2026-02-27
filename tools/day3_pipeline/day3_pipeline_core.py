#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import os
import random
import re
import shutil
import sys
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Tuple
from urllib import request as urllib_request

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
REAL = DATA / "real"
SYN_SEED = DATA / "synthetic_seed"
DAY3 = DATA / "day3"
MANIFEST_DIR = DAY3 / "manifest"
GENERATED = DAY3 / "generated"
CLEANED = GENERATED / "cleaned"
RESULTS = DAY3 / "results"

TARGET_COUNTS = {
    "pass": 20,
    "warn": 20,
    "reject": 20,
    "ocr_noise": 15,
    "sanctions_tbml_shell": 15,
}

TEXT_EXTS = {".txt", ".csv", ".json", ".xml", ".md", ".log"}
FILE_EXT_ALLOWLIST = {".txt", ".csv", ".json", ".xml", ".md", ".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff"}

MANIFEST_FIELDS = [
    "case_id",
    "source_type",
    "source_path",
    "bundle_id",
    "scenario",
    "expected_verdict",
    "sensitivity_tag",
    "contains_pii",
    "language",
    "notes",
    "cleaned_path",
    "synthetic_parent_id",
    "run_enabled",
]


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9._-]+", "_", name.lower()).strip("_") or "item"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def bootstrap_dirs() -> List[Path]:
    dirs = [REAL, SYN_SEED, MANIFEST_DIR, GENERATED, RESULTS, CLEANED]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
    return dirs


def detect_sensitivity(path: Path) -> str:
    t = path.as_posix().lower()
    if any(k in t for k in ["passport", "nid", "national_id", "account", "swift", "sanction"]):
        return "restricted"
    return "internal"


def discover_inputs() -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for source_type, base in (("real", REAL), ("synthetic_seed", SYN_SEED)):
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if p.is_dir():
                continue
            if p.suffix.lower() not in FILE_EXT_ALLOWLIST:
                continue
            rel = p.relative_to(ROOT).as_posix()
            bundle = p.parent.name
            digest = hashlib.sha1(rel.encode("utf-8")).hexdigest()[:10]
            case_id = f"{source_type[:1]}_{bundle[:12]}_{digest}"
            rows.append(
                {
                    "case_id": case_id,
                    "source_type": source_type,
                    "source_path": rel,
                    "bundle_id": bundle,
                    "scenario": "pass",
                    "expected_verdict": "pass",
                    "sensitivity_tag": detect_sensitivity(p),
                    "contains_pii": "unknown",
                    "language": "unknown",
                    "notes": "auto-discovered; review scenario/expected_verdict",
                    "cleaned_path": "",
                    "synthetic_parent_id": "",
                    "run_enabled": "1",
                }
            )
    rows.sort(key=lambda r: r["source_path"])
    out = MANIFEST_DIR / "discovered_manifest.csv"
    write_csv(out, rows, MANIFEST_FIELDS)
    return rows


def redact_text(content: str) -> Tuple[str, bool]:
    original = content
    rules = [
        (r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", "[REDACTED_EMAIL]"),
        (r"\b(?:\+?\d{1,3}[\s-]?)?(?:\d[\s-]?){8,14}\b", "[REDACTED_PHONE]"),
        (r"\b\d{10,18}\b", "[REDACTED_ID]"),
        (r"\b[A-Z]{2}\d{2}[A-Z0-9]{4,30}\b", "[REDACTED_IBAN]"),
    ]
    redacted = content
    for pat, repl in rules:
        redacted = re.sub(pat, repl, redacted, flags=re.IGNORECASE)
    return redacted, redacted != original


def clean_and_redact(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    out_rows: List[Dict[str, str]] = []
    for row in rows:
        src = ROOT / row["source_path"]
        if not src.exists():
            row2 = dict(row)
            row2["notes"] += " | source_missing"
            row2["run_enabled"] = "0"
            out_rows.append(row2)
            continue

        case_dir = CLEANED / _slug(row["case_id"])
        case_dir.mkdir(parents=True, exist_ok=True)
        new_name = f"{_slug(src.stem)}{src.suffix.lower()}"
        dst = case_dir / new_name

        pii_found = False
        if src.suffix.lower() in TEXT_EXTS:
            text = src.read_text(encoding="utf-8", errors="ignore")
            redacted, changed = redact_text(text)
            pii_found = changed
            dst.write_text(redacted, encoding="utf-8")
        else:
            shutil.copy2(src, dst)

        row2 = dict(row)
        row2["cleaned_path"] = dst.relative_to(ROOT).as_posix()
        if pii_found:
            row2["contains_pii"] = "redacted"
            row2["sensitivity_tag"] = "restricted"
            row2["notes"] += " | pii_redacted"
        out_rows.append(row2)

    write_csv(MANIFEST_DIR / "cleaned_manifest.csv", out_rows, MANIFEST_FIELDS)
    return out_rows


def synthesize_manifest(rows: List[Dict[str, str]], seed: int = 42) -> List[Dict[str, str]]:
    random.seed(seed)
    base = [r for r in rows if r.get("cleaned_path")]
    if not base:
        base = rows
    if not base:
        base = [{
            "case_id": "seed_placeholder",
            "source_type": "synthetic_seed",
            "source_path": "",
            "bundle_id": "placeholder",
            "scenario": "pass",
            "expected_verdict": "pass",
            "sensitivity_tag": "internal",
            "contains_pii": "unknown",
            "language": "unknown",
            "notes": "placeholder when no source files are present",
            "cleaned_path": "",
            "synthetic_parent_id": "",
            "run_enabled": "1",
        }]
    synthetic_rows: List[Dict[str, str]] = []
    scenario_verdict = {
        "pass": "pass",
        "warn": "warn",
        "reject": "reject",
        "ocr_noise": "warn",
        "sanctions_tbml_shell": "reject",
    }
    for scenario, count in TARGET_COUNTS.items():
        for i in range(count):
            parent = random.choice(base)
            case_id = f"syn_{scenario}_{i+1:03d}"
            row = dict(parent)
            row.update(
                {
                    "case_id": case_id,
                    "source_type": "synthetic",
                    "scenario": scenario,
                    "expected_verdict": scenario_verdict[scenario],
                    "synthetic_parent_id": parent["case_id"],
                    "notes": f"synthetic generated from {parent['case_id']} | forge_x_style_metadata_only",
                    "run_enabled": "1",
                }
            )
            synthetic_rows.append(row)

    final_rows = synthetic_rows
    write_csv(MANIFEST_DIR / "final_manifest.csv", final_rows, MANIFEST_FIELDS)
    return final_rows


def _multipart_post(url: str, fields: Dict[str, str], files: List[Path], token: str = "") -> Dict:
    boundary = f"----Day3{uuid.uuid4().hex}"
    chunks: List[bytes] = []

    for k, v in fields.items():
        chunks += [
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode(),
            str(v).encode("utf-8"),
            b"\r\n",
        ]

    for fp in files:
        content = fp.read_bytes()
        chunks += [
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="files"; filename="{fp.name}"\r\n'.encode(),
            b"Content-Type: application/octet-stream\r\n\r\n",
            content,
            b"\r\n",
        ]

    chunks.append(f"--{boundary}--\r\n".encode())
    body = b"".join(chunks)

    req = urllib_request.Request(url, method="POST", data=body)
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    req.add_header("Accept", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")

    with urllib_request.urlopen(req, timeout=120) as r:
        txt = r.read().decode("utf-8", errors="ignore")
    return json.loads(txt) if txt.strip() else {}


def extract_actual_verdict(resp: Dict) -> str:
    for key in ["verdict", "final_verdict", "status"]:
        if isinstance(resp.get(key), str):
            return resp[key].lower()
    for path in [("structured_result", "verdict"), ("result", "verdict")]:
        node = resp
        ok = True
        for k in path:
            if isinstance(node, dict) and k in node:
                node = node[k]
            else:
                ok = False
                break
        if ok and isinstance(node, str):
            return node.lower()
    return "unknown"


def run_batch(rows: List[Dict[str, str]], api_url: str, api_token: str = "", dry_run: bool = False) -> List[Dict]:
    results = []
    command_stubs = []
    jsonl_path = RESULTS / "day3_results.jsonl"

    for row in rows:
        if row.get("run_enabled", "1") != "1":
            continue
        cleaned = row.get("cleaned_path", "")
        files = [ROOT / cleaned] if cleaned else []
        files = [f for f in files if f.exists() and f.is_file()]

        record = {
            "timestamp": _now(),
            "case_id": row["case_id"],
            "scenario": row["scenario"],
            "expected_verdict": row["expected_verdict"],
            "jobId": None,
            "actual_verdict": "not_run",
            "severities": [],
            "key_issues": [],
            "status": "stub",
            "error": None,
        }

        if dry_run or not files:
            cmd = f"curl -X POST \"{api_url}\" -F \"files=@{cleaned}\""
            command_stubs.append(cmd)
            record["status"] = "stub_command"
        else:
            try:
                resp = _multipart_post(
                    api_url,
                    fields={"scenario": row["scenario"], "case_id": row["case_id"]},
                    files=files,
                    token=api_token,
                )
                issues = resp.get("issues") or resp.get("structured_result", {}).get("issues") or []
                record.update(
                    {
                        "jobId": resp.get("jobId") or resp.get("job_id"),
                        "actual_verdict": extract_actual_verdict(resp),
                        "severities": sorted({str(x.get('severity', 'unknown')).lower() for x in issues if isinstance(x, dict)}),
                        "key_issues": [x.get("code") or x.get("rule_id") or x.get("message") for x in issues[:5] if isinstance(x, dict)],
                        "status": "ok",
                    }
                )
            except Exception as exc:
                record["status"] = "error"
                record["error"] = str(exc)

        results.append(record)

    with jsonl_path.open("w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    (RESULTS / "validation_commands.ps1").write_text("\n".join(command_stubs) + "\n", encoding="utf-8")
    return results


def compute_metrics(results: List[Dict]) -> Dict:
    comparable = [r for r in results if r.get("actual_verdict") not in {"not_run", "unknown"}]
    total = len(comparable)
    correct = sum(1 for r in comparable if r.get("actual_verdict") == r.get("expected_verdict"))
    accuracy = (correct / total) if total else 0.0

    critical_false_pass = 0
    for r in comparable:
        if r.get("expected_verdict") == "reject" and r.get("actual_verdict") == "pass":
            critical_false_pass += 1

    by_case: Dict[str, List[str]] = defaultdict(list)
    for r in comparable:
        by_case[r["case_id"]].append(r.get("actual_verdict", "unknown"))
    consistency_scores = []
    for verdicts in by_case.values():
        if len(verdicts) > 1:
            consistency_scores.append(1.0 if len(set(verdicts)) == 1 else 0.0)
    rerun_consistency = sum(consistency_scores) / len(consistency_scores) if consistency_scores else 1.0

    labels = ["pass", "warn", "reject", "unknown"]
    matrix = {e: {a: 0 for a in labels} for e in labels}
    for r in results:
        e = r.get("expected_verdict", "unknown")
        a = r.get("actual_verdict", "unknown")
        if e not in matrix:
            e = "unknown"
        if a not in labels:
            a = "unknown"
        matrix[e][a] += 1

    failed = [r for r in comparable if r.get("expected_verdict") != r.get("actual_verdict")]

    summary = {
        "generated_at": _now(),
        "total_records": len(results),
        "comparable_records": total,
        "accuracy": round(accuracy, 4),
        "critical_false_pass": critical_false_pass,
        "rerun_consistency": round(rerun_consistency, 4),
        "status_counts": dict(Counter(r.get("status", "unknown") for r in results)),
        "confusion_matrix": matrix,
    }

    (RESULTS / "metrics_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    _write_confusion_csv(matrix)
    _write_failed_csv(failed)
    _write_signoff(summary)
    return summary


def _write_confusion_csv(matrix: Dict[str, Dict[str, int]]) -> None:
    labels = ["pass", "warn", "reject", "unknown"]
    path = RESULTS / "confusion_matrix.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["expected\\actual", *labels])
        for e in labels:
            w.writerow([e] + [matrix[e][a] for a in labels])


def _write_failed_csv(rows: List[Dict]) -> None:
    path = RESULTS / "failed_cases.csv"
    fields = ["case_id", "scenario", "expected_verdict", "actual_verdict", "jobId", "status", "error"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in fields})


def _write_signoff(summary: Dict) -> None:
    md = f"""# DAY3_SIGNOFF

Generated: {summary['generated_at']}

## Metrics Snapshot
- Total records: {summary['total_records']}
- Comparable records: {summary['comparable_records']}
- Accuracy: {summary['accuracy']}
- Critical false-pass: {summary['critical_false_pass']}
- Rerun consistency: {summary['rerun_consistency']}

## Evidence Files
- metrics_summary.json
- confusion_matrix.csv
- failed_cases.csv
- day3_results.jsonl
- validation_commands.ps1

## Signoff Checklist
- [ ] Data stayed local (no external upload)
- [ ] Manifest reviewed for scenario correctness
- [ ] Failed cases triaged
- [ ] Critical false-pass == 0 (or accepted exception documented)
- [ ] Re-run consistency acceptable

## Decision
- [ ] APPROVED
- [ ] NEEDS FIXES

Owner: ____________________
Date: _____________________
"""
    (RESULTS / "DAY3_SIGNOFF.md").write_text(md, encoding="utf-8")


def write_csv(path: Path, rows: List[Dict[str, str]], fields: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})


def read_csv(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))
