#!/usr/bin/env python3
import csv
import json
import random
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

SEED = 20260302
TOTAL_CASES = 200
VERDICT_TARGET = {"pass": 80, "warn": 80, "reject": 40}
SPLIT_TARGET = {"train": 140, "val": 30, "test": 30}
ROOT = Path("datasets/lcopilot_v1")

ISSUE_CATALOG = {
    "WARN_OCR_NOISE": {
        "category": "ocr",
        "severity": "warn",
        "blocking_rules": [],
    },
    "WARN_TOLERANCE_MISMATCH": {
        "category": "mismatch",
        "severity": "warn",
        "blocking_rules": [],
    },
    "WARN_CLAUSE_AMBIGUITY": {
        "category": "clause_edge",
        "severity": "warn",
        "blocking_rules": [],
    },
    "WARN_PARTIAL_DOC_MISSING": {
        "category": "missing_doc",
        "severity": "warn",
        "blocking_rules": [],
    },
    "REJ_SANCTIONS_HIT": {
        "category": "sanctions_risk",
        "severity": "reject",
        "blocking_rules": ["SANCTIONS_SCREENING_FAIL"],
    },
    "REJ_CRITICAL_DOC_MISSING": {
        "category": "missing_doc",
        "severity": "reject",
        "blocking_rules": ["MANDATORY_DOC_ABSENT"],
    },
    "REJ_AMOUNT_MISMATCH": {
        "category": "mismatch",
        "severity": "reject",
        "blocking_rules": ["LC_AMOUNT_MISMATCH"],
    },
    "REJ_PROHIBITED_CLAUSE": {
        "category": "clause_edge",
        "severity": "reject",
        "blocking_rules": ["PROHIBITED_CLAUSE_DETECTED"],
    },
}

PUBLIC_TEMPLATE_REFERENCES = [
    "UCP600-public-sample-structure",
    "ISBP745-checklist-pattern",
    "ICC-model-document-layout",
]

EXPORTER_NAMES = [
    "Aster Trade Works",
    "Blue Delta Exports",
    "Crescent Agro Supply",
    "Dawn Marine Logistics",
    "Evergrain Commodities",
]
IMPORTER_NAMES = [
    "Northbridge Import Co",
    "Harborline Procurement",
    "Summit Retail Sourcing",
    "Orchid Manufacturing Ltd",
    "Metroline Distributors",
]

DOC_TYPES = [
    "commercial_invoice",
    "packing_list",
    "bill_of_lading",
    "certificate_of_origin",
    "insurance_certificate",
    "inspection_certificate",
]


@dataclass
class CaseRecord:
    case_id: str
    split: str
    role: str
    transport_mode: str
    scan_variant: str
    scenario_tags: list
    expected_verdict: str
    expected_issue_ids: list
    blocking_rules: list
    amount_usd: int
    currency: str
    exporter: str
    importer: str
    commodity: str
    lc_reference: str
    docs_expected: list
    docs_present: list
    pdf_path: str
    truth_json_path: str
    provenance: dict


def ensure_dirs() -> dict:
    paths = {
        "root": ROOT,
        "cases": ROOT / "cases",
        "pdf": ROOT / "pdf",
        "manifests": ROOT / "manifests",
        "reports": ROOT / "reports",
        "scripts": ROOT / "scripts",
    }
    for p in paths.values():
        p.mkdir(parents=True, exist_ok=True)
    return paths


def make_pdf(path: Path, case: CaseRecord) -> None:
    c = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4
    y = height - 50
    lines = [
        "LCopilot Dataset v1 - Synthetic Test Case",
        f"Case ID: {case.case_id}",
        f"Split: {case.split}",
        f"Role: {case.role}",
        f"Transport: {case.transport_mode}",
        f"Scan Variant: {case.scan_variant}",
        f"LC Reference: {case.lc_reference}",
        f"Exporter: {case.exporter}",
        f"Importer: {case.importer}",
        f"Amount: {case.amount_usd} {case.currency}",
        f"Expected Verdict: {case.expected_verdict}",
        f"Scenario Tags: {', '.join(case.scenario_tags)}",
        "",
        "Note: All identifiers are synthetic/anonymized for compliance testing.",
    ]
    for line in lines:
        c.drawString(50, y, line)
        y -= 18
    c.showPage()
    c.save()


def build_cases() -> list[CaseRecord]:
    random.seed(SEED)

    verdicts = ["pass"] * VERDICT_TARGET["pass"] + ["warn"] * VERDICT_TARGET["warn"] + ["reject"] * VERDICT_TARGET["reject"]
    random.shuffle(verdicts)

    splits = ["train"] * SPLIT_TARGET["train"] + ["val"] * SPLIT_TARGET["val"] + ["test"] * SPLIT_TARGET["test"]
    random.shuffle(splits)

    roles = ["exporter"] * (TOTAL_CASES // 2) + ["importer"] * (TOTAL_CASES // 2)
    random.shuffle(roles)

    modes = ["sea"] * 80 + ["air"] * 80 + ["multimodal"] * 40
    random.shuffle(modes)

    scans = ["clean"] * 100 + ["ocr_noisy"] * 100
    random.shuffle(scans)

    commodities = [
        "garments",
        "rice",
        "electronics",
        "tea",
        "frozen_food",
        "machine_parts",
        "ceramics",
        "pharma_packaging",
    ]

    warn_issues = [
        "WARN_OCR_NOISE",
        "WARN_TOLERANCE_MISMATCH",
        "WARN_CLAUSE_AMBIGUITY",
        "WARN_PARTIAL_DOC_MISSING",
    ]
    reject_issues = [
        "REJ_SANCTIONS_HIT",
        "REJ_CRITICAL_DOC_MISSING",
        "REJ_AMOUNT_MISMATCH",
        "REJ_PROHIBITED_CLAUSE",
    ]

    cases: list[CaseRecord] = []

    for idx in range(TOTAL_CASES):
        case_id = f"LCV1-{idx+1:04d}"
        verdict = verdicts[idx]
        split = splits[idx]
        role = roles[idx]
        mode = modes[idx]
        scan = scans[idx]

        exporter = random.choice(EXPORTER_NAMES) + f" {idx%7+1}"
        importer = random.choice(IMPORTER_NAMES) + f" {idx%9+1}"
        amount = random.randint(25_000, 450_000)
        currency = "USD"
        commodity = random.choice(commodities)
        lc_ref = f"LC-{2026}{idx+1:05d}"

        docs_expected = DOC_TYPES.copy()
        docs_present = DOC_TYPES.copy()

        scenario_tags = [role, mode, scan, commodity]
        expected_issue_ids = []
        blocking_rules = []

        if verdict == "warn":
            issue = warn_issues[idx % len(warn_issues)]
            expected_issue_ids = [issue]
            scenario_tags.append(ISSUE_CATALOG[issue]["category"])
            if issue == "WARN_PARTIAL_DOC_MISSING":
                missing = random.choice(["inspection_certificate", "insurance_certificate"])
                if missing in docs_present:
                    docs_present.remove(missing)
        elif verdict == "reject":
            issue = reject_issues[idx % len(reject_issues)]
            expected_issue_ids = [issue]
            blocking_rules = ISSUE_CATALOG[issue]["blocking_rules"]
            scenario_tags.append(ISSUE_CATALOG[issue]["category"])
            if issue == "REJ_CRITICAL_DOC_MISSING":
                missing = random.choice(["commercial_invoice", "bill_of_lading"])
                if missing in docs_present:
                    docs_present.remove(missing)
            if issue == "REJ_AMOUNT_MISMATCH":
                scenario_tags.append("invoice_lc_mismatch")
        else:
            scenario_tags.append("clean_compliant")

        # Guarantee explicit coverage for required dimensions in some pass cases
        if verdict == "pass" and scan == "ocr_noisy":
            scenario_tags.append("noise_tolerant_pass")

        scenario_tags = sorted(set(scenario_tags))

        case = CaseRecord(
            case_id=case_id,
            split=split,
            role=role,
            transport_mode=mode,
            scan_variant=scan,
            scenario_tags=scenario_tags,
            expected_verdict=verdict,
            expected_issue_ids=expected_issue_ids,
            blocking_rules=blocking_rules,
            amount_usd=amount,
            currency=currency,
            exporter=exporter,
            importer=importer,
            commodity=commodity,
            lc_reference=lc_ref,
            docs_expected=docs_expected,
            docs_present=docs_present,
            pdf_path=str((ROOT / "pdf" / f"{case_id}.pdf").as_posix()),
            truth_json_path=str((ROOT / "cases" / f"{case_id}.json").as_posix()),
            provenance={
                "source_type": "synthetic",
                "template_references": PUBLIC_TEMPLATE_REFERENCES,
                "contains_pii": False,
                "generation_seed": SEED,
            },
        )
        cases.append(case)

    return cases


def write_outputs(cases: list[CaseRecord], paths: dict) -> None:
    # per-case JSON + PDF
    for case in cases:
        json_path = paths["cases"] / f"{case.case_id}.json"
        pdf_path = paths["pdf"] / f"{case.case_id}.pdf"

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(asdict(case), f, indent=2)
        make_pdf(pdf_path, case)

    # JSONL export
    jsonl_path = paths["manifests"] / "master_manifest.jsonl"
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for case in cases:
            f.write(json.dumps(asdict(case), ensure_ascii=False) + "\n")

    # CSV manifest
    csv_path = paths["manifests"] / "master_manifest.csv"
    fields = [
        "case_id",
        "split",
        "role",
        "transport_mode",
        "scan_variant",
        "scenario_tags",
        "expected_verdict",
        "expected_issue_ids",
        "blocking_rules",
        "pdf_path",
        "truth_json_path",
    ]

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for case in cases:
            writer.writerow(
                {
                    "case_id": case.case_id,
                    "split": case.split,
                    "role": case.role,
                    "transport_mode": case.transport_mode,
                    "scan_variant": case.scan_variant,
                    "scenario_tags": "|".join(case.scenario_tags),
                    "expected_verdict": case.expected_verdict,
                    "expected_issue_ids": "|".join(case.expected_issue_ids),
                    "blocking_rules": "|".join(case.blocking_rules),
                    "pdf_path": case.pdf_path,
                    "truth_json_path": case.truth_json_path,
                }
            )


def build_quality_report(cases: list[CaseRecord], paths: dict) -> None:
    verdict_counter = Counter(c.expected_verdict for c in cases)
    split_counter = Counter(c.split for c in cases)
    role_counter = Counter(c.role for c in cases)
    mode_counter = Counter(c.transport_mode for c in cases)
    scan_counter = Counter(c.scan_variant for c in cases)

    category_counter = Counter()
    for c in cases:
        for iid in c.expected_issue_ids:
            category_counter[ISSUE_CATALOG[iid]["category"]] += 1

    # Coverage matrix: verdict x role x mode (flattened summary)
    matrix = defaultdict(int)
    for c in cases:
        matrix[(c.expected_verdict, c.role, c.transport_mode)] += 1

    report_lines = [
        "# LCopilot Dataset v1 - Quality Report",
        "",
        "## Distribution Summary",
        f"- Total cases: {len(cases)}",
        f"- Verdicts: pass={verdict_counter['pass']}, warn={verdict_counter['warn']}, reject={verdict_counter['reject']}",
        f"- Splits: train={split_counter['train']}, val={split_counter['val']}, test={split_counter['test']}",
        f"- Roles: exporter={role_counter['exporter']}, importer={role_counter['importer']}",
        f"- Modes: sea={mode_counter['sea']}, air={mode_counter['air']}, multimodal={mode_counter['multimodal']}",
        f"- Scan variants: clean={scan_counter['clean']}, ocr_noisy={scan_counter['ocr_noisy']}",
        "",
        "## Coverage Matrix (verdict x role x mode)",
        "",
    ]

    for verdict in ["pass", "warn", "reject"]:
        report_lines.append(f"### {verdict.upper()}")
        for role in ["exporter", "importer"]:
            row = [f"- {role}:"]
            for mode in ["sea", "air", "multimodal"]:
                row.append(f"{mode}={matrix[(verdict, role, mode)]}")
            report_lines.append(" ".join(row))
        report_lines.append("")

    report_lines += [
        "## Scenario Issue Coverage",
        f"- missing_doc: {category_counter['missing_doc']}",
        f"- mismatch: {category_counter['mismatch']}",
        f"- sanctions_risk: {category_counter['sanctions_risk']}",
        f"- clause_edge: {category_counter['clause_edge']}",
        f"- ocr-related: {category_counter['ocr']}",
        "",
        "## Known Limitations",
        "- Documents are synthetic and intentionally simplified one-page PDFs for deterministic testing.",
        "- No real customer/beneficiary entities are included (PII-safe).",
        "- Sanctions scenarios are rule-trigger simulations, not live sanctions list matches.",
        "",
        "## Quick Usage Commands",
        "```bash",
        "python scripts/build_lcopilot_dataset_v1.py",
        "python scripts/validate_lcopilot_dataset_v1.py",
        "```",
    ]

    report_path = paths["reports"] / "quality_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))


def write_schema(paths: dict) -> None:
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "LCopilot Dataset v1 Case Schema",
        "type": "object",
        "required": [
            "case_id",
            "split",
            "role",
            "transport_mode",
            "scan_variant",
            "expected_verdict",
            "expected_issue_ids",
            "blocking_rules",
            "pdf_path",
            "truth_json_path",
            "provenance",
        ],
        "properties": {
            "case_id": {"type": "string"},
            "split": {"type": "string", "enum": ["train", "val", "test"]},
            "role": {"type": "string", "enum": ["exporter", "importer"]},
            "transport_mode": {"type": "string", "enum": ["sea", "air", "multimodal"]},
            "scan_variant": {"type": "string", "enum": ["clean", "ocr_noisy"]},
            "scenario_tags": {"type": "array", "items": {"type": "string"}},
            "expected_verdict": {"type": "string", "enum": ["pass", "warn", "reject"]},
            "expected_issue_ids": {"type": "array", "items": {"type": "string"}},
            "blocking_rules": {"type": "array", "items": {"type": "string"}},
            "pdf_path": {"type": "string"},
            "truth_json_path": {"type": "string"},
            "provenance": {"type": "object"},
        },
    }
    with open(paths["root"] / "schema.json", "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)


def write_readme(paths: dict) -> None:
    content = """# LCopilot Dataset v1

Deterministic synthetic dataset for LC importer/exporter workflow testing.

## Structure
- `cases/`: 200 case-level truth JSON files
- `pdf/`: 200 synthetic PDF documents (one per case)
- `manifests/master_manifest.csv`: runner ingestion manifest
- `manifests/master_manifest.jsonl`: JSONL manifest
- `reports/quality_report.md`: distribution + coverage checks
- `schema.json`: JSON schema for truth records

## Rebuild
```bash
python scripts/build_lcopilot_dataset_v1.py
python scripts/validate_lcopilot_dataset_v1.py
```
"""
    with open(paths["root"] / "README.md", "w", encoding="utf-8") as f:
        f.write(content)


def main() -> None:
    paths = ensure_dirs()
    cases = build_cases()
    write_schema(paths)
    write_outputs(cases, paths)
    build_quality_report(cases, paths)
    write_readme(paths)
    print(f"Built {len(cases)} cases at {ROOT}")


if __name__ == "__main__":
    main()
