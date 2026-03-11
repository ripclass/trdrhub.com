import json
import subprocess
from pathlib import Path
from collections import Counter

ROOT = Path(r"F:/New Download/LC Copies/Exporter-Generated/all-v3-mixed-lc-40iso")
MANIFEST = ROOT / "_manifest.json"
OUT_DIR = Path(r"H:/.openclaw/workspace/trdrhub.com")
SMOKE = Path(r"H:/.openclaw/workspace/trdrhub.com/apps/api/scripts/day1_smoke_gate.py")
PY = Path(r"H:/.openclaw/workspace/trdrhub.com/apps/api/venv/Scripts/python.exe")
BASE_URL = "https://trdrhub-api.onrender.com"

manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
iso_sets = [m for m in manifest if m.get("lc_mode") == "iso20022"][:10]

rows = []
reason_counter = Counter()
status_counter = Counter()

progress_path = OUT_DIR / "iso10_diagnostic_progress.json"
final_path = OUT_DIR / "iso10_diagnostic_summary.json"

def save_progress(final=False):
    report = {
        "processed": len(rows),
        "target": len(iso_sets),
        "status_counts": dict(status_counter),
        "top_reasons": [{"reason": k, "count": v} for k, v in reason_counter.most_common(20)],
        "rows": rows,
        "final": final,
    }
    (final_path if final else progress_path).write_text(json.dumps(report, indent=2), encoding="utf-8")

for i, item in enumerate(iso_sets, start=1):
    set_name = item["set"]
    input_dir = ROOT / set_name
    out_file = OUT_DIR / f"iso10_diag_{i:02d}_{set_name}.json"
    cmd = [
        str(PY), str(SMOKE),
        "--base-url", BASE_URL,
        "--input-dir", str(input_dir),
        "--limit", "1",
        "--api-key", "dummy",
        "--timeout", "180",
        "--out", str(out_file),
    ]
    status = "unknown"
    reasons = []
    error = ""
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=260)
        if proc.returncode == 0 and out_file.exists():
            data = json.loads(out_file.read_text(encoding="utf-8"))
            cc = data.get("contract_counts", {})
            if cc.get("pass", 0) > 0:
                status = "pass"
            elif cc.get("review", 0) > 0:
                status = "review"
            else:
                status = "unknown"
            results = data.get("results") or []
            if results and isinstance(results[0], dict):
                reasons = list(results[0].get("violation_reason_codes") or [])
        else:
            error = (proc.stderr or proc.stdout or "process_failed")[:500]
    except Exception as ex:
        error = str(ex)[:500]

    for r in reasons:
        reason_counter[str(r)] += 1
    status_counter[status] += 1
    rows.append({"index": i, "set": set_name, "status": status, "reasons": reasons, "error": error})
    save_progress(final=False)

save_progress(final=True)
print(json.dumps({"processed": len(rows), "status_counts": dict(status_counter), "out": str(final_path)}))
