from __future__ import annotations

import json
from pathlib import Path

from app.services.extraction.lc_baseline import create_lc_baseline_from_extraction
from app.services.validation.ai_validator import validate_bl_fields, validate_packing_list

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "phase_b_track_e"
OUT_PATH = ROOT / "docs" / "phase_b_track_e_completion_board.md"


def _load(name: str):
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def _classify_residual(field):
    if field.missing_reason:
        return field.missing_reason
    if field.error:
        return "parser_failed"
    return "missing_in_source"


def _run_case(case: dict):
    baseline = create_lc_baseline_from_extraction(case["lc"], raw_text=case["lc"].get("raw_text", ""))
    critical = baseline.get_critical_fields()
    recovered = [f for f in critical if f.is_present]
    evidence = [f for f in recovered if f.has_evidence]

    bl_issues = validate_bl_fields(case["bill_of_lading"]["required_fields"], case["bill_of_lading"]["data"])
    pl_issues = validate_packing_list(case["packing_list"]["lc_text"], case["packing_list"]["data"])

    residual = []
    for f in critical:
        if not f.is_present:
            residual.append({
                "doc_type": "letter_of_credit",
                "field": f.field_name,
                "reason_class": _classify_residual(f),
                "detail": f.error or "not recovered",
            })

    for issue in bl_issues:
        residual.append({
            "doc_type": "bill_of_lading",
            "field": "n/a",
            "reason_class": "missing_in_source",
            "detail": str(issue),
        })

    for issue in pl_issues:
        residual.append({
            "doc_type": "packing_list",
            "field": "n/a",
            "reason_class": "missing_in_source",
            "detail": str(issue),
        })

    return {
        "id": case["id"],
        "lc_pass": len(residual) == 0 or not any(r["doc_type"] == "letter_of_credit" for r in residual),
        "bl_pass": len(bl_issues) == 0,
        "pl_pass": len(pl_issues) == 0,
        "critical_total": len(critical),
        "critical_recovered": len(recovered),
        "evidence_covered": len(evidence),
        "residual": residual,
    }


def main():
    cases = [_run_case(_load("ideal_sample.json")), _run_case(_load("exp2026bd001_like_miss.json"))]

    critical_total = sum(c["critical_total"] for c in cases)
    critical_recovered = sum(c["critical_recovered"] for c in cases)
    evidence_covered = sum(c["evidence_covered"] for c in cases)

    def pct(n, d):
        return 0.0 if d == 0 else round((n / d) * 100, 1)

    lc_pass = all(c["lc_pass"] for c in cases)
    bl_pass = all(c["bl_pass"] for c in cases)
    pl_pass = all(c["pl_pass"] for c in cases)

    residual_all = []
    for c in cases:
        residual_all.extend({"case": c["id"], **r} for r in c["residual"])

    go = lc_pass and bl_pass and pl_pass and pct(critical_recovered, critical_total) >= 95 and pct(evidence_covered, critical_total) >= 95

    lines = [
        "# Phase B Track E — Targeted QA Completion Board",
        "",
        "## Scope",
        "- Targeted extraction QA only (no full platform suite)",
        "- Fixtures: IDEAL_SAMPLE + EXP2026BD001_LIKE_MISS",
        "- Verdict/scoring metrics intentionally excluded from gating",
        "",
        "## Pass/Fail by Doc Type",
        f"- letter_of_credit: {'PASS' if lc_pass else 'FAIL'}",
        f"- bill_of_lading: {'PASS' if bl_pass else 'FAIL'}",
        f"- packing_list: {'PASS' if pl_pass else 'FAIL'}",
        "",
        "## Critical-field Recovery",
        f"- recovered: {critical_recovered}/{critical_total} ({pct(critical_recovered, critical_total)}%)",
        "",
        "## Evidence Span Coverage (critical fields)",
        f"- covered: {evidence_covered}/{critical_total} ({pct(evidence_covered, critical_total)}%)",
        "",
        "## Residual Misses",
    ]

    if residual_all:
        for r in residual_all:
            lines.append(f"- [{r['case']}] {r['doc_type']}::{r['field']} -> {r['reason_class']} ({r['detail']})")
    else:
        lines.append("- None")

    lines.extend([
        "",
        "## Phase B Extraction Close Decision",
        f"- Decision: {'GO' if go else 'NO-GO'}",
        "- Basis: doc-type pass status + critical recovery + critical evidence coverage",
    ])

    OUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(str(OUT_PATH))


if __name__ == "__main__":
    main()
