from __future__ import annotations

import json
from pathlib import Path

from day1_smoke_gate import run_smoke

ROOT = Path(r"H:\.openclaw\workspace\synthetic_exporter_mixed_batch_01")
OUT = Path(r"H:\.openclaw\workspace\trdrhub.com\mixed_batch_01_validation_report_render_after_truth_patch.json")
PROGRESS = Path(r"H:\.openclaw\workspace\trdrhub.com\mixed_batch_01_validation_progress_render_after_truth_patch.json")
BASE_URL = "https://trdrhub-api.onrender.com"

set_dirs = sorted([p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("mix_")])
results = []

for idx, set_dir in enumerate(set_dirs, start=1):
    item = {"index": idx, "set": set_dir.name}
    try:
        report = run_smoke(
            BASE_URL,
            set_dir,
            limit=1,
            api_key="dummy",
            bundle_by_dir=True,
            request_timeout=180,
        )
        set_result = (report.get("results") or [{}])[0]
        item.update({
            "ok": bool(set_result.get("ok")),
            "contract_status": set_result.get("contract_status"),
            "files": set_result.get("files", []),
            "unresolved_critical_fields": set_result.get("unresolved_critical_fields", []),
            "violation_reason_codes": set_result.get("violation_reason_codes", []),
            "field_level_status": set_result.get("field_level_status", {}),
            "critical_field_source_doc_hints": set_result.get("critical_field_source_doc_hints", {}),
            "total_violations": report.get("total_violations", 0),
            "ret_no_hit_total": report.get("ret_no_hit_total", 0),
            "ret_low_relevance_total": report.get("ret_low_relevance_total", 0),
        })
    except Exception as exc:
        item.update({
            "ok": False,
            "contract_status": "unknown",
            "error": str(exc),
            "files": [],
            "unresolved_critical_fields": [],
            "violation_reason_codes": [],
            "field_level_status": {},
            "critical_field_source_doc_hints": {},
            "total_violations": 0,
            "ret_no_hit_total": 0,
            "ret_low_relevance_total": 0,
        })

    results.append(item)
    progress = {
        "processed": len(results),
        "pass": sum(1 for r in results if r.get("contract_status") == "pass"),
        "review": sum(1 for r in results if r.get("contract_status") == "review"),
        "unknown": sum(1 for r in results if r.get("contract_status") == "unknown"),
        "results": results,
    }
    PROGRESS.write_text(json.dumps(progress, indent=2), encoding="utf-8")
    print(json.dumps({"processed": len(results), "latest": set_dir.name, "status": item.get("contract_status"), "ok": item.get("ok")}, ensure_ascii=False), flush=True)

final = {
    "processed": len(results),
    "pass": sum(1 for r in results if r.get("contract_status") == "pass"),
    "review": sum(1 for r in results if r.get("contract_status") == "review"),
    "unknown": sum(1 for r in results if r.get("contract_status") == "unknown"),
    "results": results,
}
OUT.write_text(json.dumps(final, indent=2), encoding="utf-8")
print(json.dumps(final, ensure_ascii=False), flush=True)
