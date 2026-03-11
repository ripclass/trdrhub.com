import json
import subprocess
from pathlib import Path

ROOT = Path(r"F:/New Download/LC Copies/Exporter-Generated/all-v3-mixed-lc-40iso")
OUT_DIR = Path(r"H:/.openclaw/workspace/trdrhub.com")
SMOKE = Path(r"H:/.openclaw/workspace/trdrhub.com/apps/api/scripts/day1_smoke_gate.py")
PY = Path(r"H:/.openclaw/workspace/trdrhub.com/apps/api/venv/Scripts/python.exe")
BASE_URL = "https://trdrhub-api.onrender.com"

sets = sorted([p for p in ROOT.iterdir() if p.is_dir()])
results = []

for i, s in enumerate(sets, start=1):
    out_file = OUT_DIR / f"day2_v3_set_{i:03d}.json"
    cmd = [
        str(PY), str(SMOKE),
        "--base-url", BASE_URL,
        "--input-dir", str(s),
        "--limit", "1",
        "--api-key", "dummy",
        "--timeout", "300",
        "--out", str(out_file),
    ]
    status = "unknown"
    error = ""
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=420)
        if proc.returncode == 0 and out_file.exists():
            data = json.loads(out_file.read_text(encoding="utf-8"))
            cc = data.get("contract_counts", {})
            if cc.get("pass", 0) > 0:
                status = "pass"
            elif cc.get("review", 0) > 0:
                status = "review"
            else:
                status = "unknown"
        else:
            error = (proc.stderr or proc.stdout or "process_failed")[:500]
    except Exception as ex:
        error = str(ex)[:500]

    results.append({"index": i, "set": s.name, "status": status, "error": error})

    # rolling checkpoint
    summary = {
        "processed": len(results),
        "pass": sum(1 for r in results if r["status"] == "pass"),
        "review": sum(1 for r in results if r["status"] == "review"),
        "unknown": sum(1 for r in results if r["status"] == "unknown"),
        "results": results,
    }
    (OUT_DIR / "day2_v3_batch_progress.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

final = {
    "processed": len(results),
    "pass": sum(1 for r in results if r["status"] == "pass"),
    "review": sum(1 for r in results if r["status"] == "review"),
    "unknown": sum(1 for r in results if r["status"] == "unknown"),
    "results": results,
}
(OUT_DIR / "day2_v3_batch_final.json").write_text(json.dumps(final, indent=2), encoding="utf-8")
print(json.dumps({k: final[k] for k in ["processed", "pass", "review", "unknown"]}))
