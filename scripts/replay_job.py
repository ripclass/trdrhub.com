#!/usr/bin/env python3
import os
import sys
import time
import json
import requests
from typing import Any, Dict, List, Optional

BASE_URL = os.getenv("TRDRHUB_API_BASE", "https://trdrhub-api.onrender.com")
TOKEN = os.getenv("TRDRHUB_BEARER")  # paste a short-lived JWT or set env
POLL_INTERVAL = float(os.getenv("TRDRHUB_POLL_INTERVAL", "1.5"))
TIMEOUT_SEC = int(os.getenv("TRDRHUB_TIMEOUT_SEC", "90"))


def hdrs() -> Dict[str, str]:
    return {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}


def get_json(path: str) -> Dict[str, Any]:
    url = f"{BASE_URL}{path}"
    r = requests.get(url, headers=hdrs(), timeout=30)
    r.raise_for_status()
    return r.json()


def main(job_id: str) -> int:
    print(f"🔁 Polling /api/jobs/{job_id} ...")
    start = time.time()
    status: Optional[str] = None
    while time.time() - start < TIMEOUT_SEC:
        job = get_json(f"/api/jobs/{job_id}")
        status = job.get("status")
        print(f"  → status={status}")
        if status in {"completed", "failed", "cancelled"}:
            break
        time.sleep(POLL_INTERVAL)

    if status not in {"completed", "failed", "cancelled"}:
        print(f"❌ Job not terminal within {TIMEOUT_SEC}s (status={status})")
        return 2

    print(f"📥 Fetching /api/results/{job_id} ...")
    res = get_json(f"/api/results/{job_id}")

    # Write full payload for inspection
    out_path = f"./results_{job_id}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2, ensure_ascii=False)
    print(f"✅ Saved full payload → {out_path}")

    sr = res.get("structured_result", {})
    # Prefer nested lc_structured.documents_structured if present
    docs = (
        sr.get("lc_structured", {}).get("documents_structured")
        or sr.get("documents_structured")
        or []
    )

    print("\n🧾 Option-E Documents:")
    if not docs:
        print("  (empty)")
    else:
        for i, d in enumerate(docs, 1):
            print(f"  {i:02d}. {d.get('filename')}  —  type={d.get('document_type')}  status={d.get('extraction_status')}")

    # Minimal assertions as exit code signal
    if not sr or sr.get("version") != "structured_result_v1":
        print("❌ structured_result_v1 missing")
        return 3

    if len(docs) == 0:
        print("❌ documents_structured empty")
        return 4

    print("\n📊 Telemetry:", res.get("telemetry", {}))
    print("🎉 Done.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: replay_job.py <JOB_ID>")
        sys.exit(1)
    if not TOKEN:
        print("Warning: TRDRHUB_BEARER is not set; this request may fail if auth is required.", file=sys.stderr)
    sys.exit(main(sys.argv[1]))

