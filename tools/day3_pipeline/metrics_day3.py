#!/usr/bin/env python3
import json
from day3_pipeline_core import RESULTS, compute_metrics

if __name__ == "__main__":
    jsonl = RESULTS / "day3_results.jsonl"
    rows = []
    if jsonl.exists():
        for line in jsonl.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    summary = compute_metrics(rows)
    print(json.dumps(summary, indent=2))
