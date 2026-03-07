from __future__ import annotations

import argparse
import json
import mimetypes
from pathlib import Path
from typing import Any, Dict, List, Tuple

import requests


def _pick_files(input_dir: Path, limit: int) -> List[Path]:
    exts = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff"}
    files = [p for p in sorted(input_dir.rglob("*")) if p.is_file() and p.suffix.lower() in exts]
    return files[:limit]


def _post_validate(base_url: str, file_path: Path, timeout: int = 120, bearer: str = "", api_key: str = "") -> Dict[str, Any]:
    mime = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    url = base_url.rstrip("/") + "/api/validate/"
    headers: Dict[str, str] = {}
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    if api_key:
        headers["x-api-key"] = api_key
    with file_path.open("rb") as f:
        resp = requests.post(
            url,
            files={"file": (file_path.name, f, mime)},
            data={"userType": "exporter"},
            headers=headers,
            timeout=timeout,
        )
    resp.raise_for_status()
    return resp.json()


def _extract_gate_metrics(payload: Dict[str, Any]) -> Tuple[str, Dict[str, Any], Dict[str, Any]]:
    structured = payload.get("structured_result") if isinstance(payload.get("structured_result"), dict) else {}
    contract = structured.get("_day1_contract") if isinstance(structured.get("_day1_contract"), dict) else {}
    metrics = structured.get("_day1_metrics") if isinstance(structured.get("_day1_metrics"), dict) else {}
    status = str(contract.get("status") or "unknown")
    return status, contract, metrics


def run_smoke(base_url: str, input_dir: Path, limit: int, bearer: str = "", api_key: str = "") -> Dict[str, Any]:
    files = _pick_files(input_dir, limit)
    if not files:
        raise RuntimeError(f"No documents found in {input_dir}")

    results = []
    contract_counts = {"pass": 0, "review": 0, "unknown": 0}
    total_ret_no_hit = 0
    total_ret_low = 0
    total_violations = 0

    for fp in files:
        try:
            payload = _post_validate(base_url, fp, bearer=bearer, api_key=api_key)
            status, contract, metrics = _extract_gate_metrics(payload)
            contract_counts[status] = contract_counts.get(status, 0) + 1
            total_ret_no_hit += int(metrics.get("ret_no_hit") or 0)
            total_ret_low += int(metrics.get("ret_low_relevance") or 0)
            total_violations += len(contract.get("violations") or [])
            results.append({
                "file": fp.name,
                "ok": True,
                "contract_status": status,
                "violations": len(contract.get("violations") or []),
                "ret_no_hit": int(metrics.get("ret_no_hit") or 0),
                "ret_low_relevance": int(metrics.get("ret_low_relevance") or 0),
            })
        except Exception as e:
            results.append({"file": fp.name, "ok": False, "error": str(e), "contract_status": "unknown"})
            contract_counts["unknown"] = contract_counts.get("unknown", 0) + 1

    processed = len(results)
    hard_failures = sum(1 for r in results if not r.get("ok"))

    gate_pass = hard_failures == 0 and contract_counts.get("unknown", 0) == 0

    return {
        "base_url": base_url,
        "input_dir": str(input_dir),
        "processed": processed,
        "contract_counts": contract_counts,
        "total_violations": total_violations,
        "ret_no_hit_total": total_ret_no_hit,
        "ret_low_relevance_total": total_ret_low,
        "hard_failures": hard_failures,
        "gate_pass": gate_pass,
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Day-1 20-doc staging smoke gate")
    parser.add_argument("--base-url", required=True, help="API base url, e.g. http://localhost:8000")
    parser.add_argument("--input-dir", required=True, help="Directory with docs (.pdf/.png/...) for smoke")
    parser.add_argument("--limit", type=int, default=20, help="Number of docs to run (default: 20)")
    parser.add_argument("--bearer", default="", help="Bearer token for Authorization header")
    parser.add_argument("--api-key", default="", help="Optional x-api-key header")
    parser.add_argument("--out", default="day1_smoke_report.json", help="Output report file")
    args = parser.parse_args()

    report = run_smoke(args.base_url, Path(args.input_dir), args.limit, bearer=args.bearer, api_key=args.api_key)
    out_path = Path(args.out)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps({
        "processed": report["processed"],
        "gate_pass": report["gate_pass"],
        "contract_counts": report["contract_counts"],
        "total_violations": report["total_violations"],
        "ret_no_hit_total": report["ret_no_hit_total"],
        "ret_low_relevance_total": report["ret_low_relevance_total"],
        "out": str(out_path),
    }, indent=2))


if __name__ == "__main__":
    main()
