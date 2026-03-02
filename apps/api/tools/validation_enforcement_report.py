import json
from collections import Counter
from pathlib import Path

import importlib.util

ARBITRATION_PATH = Path(__file__).resolve().parents[1] / "app" / "services" / "validation" / "arbitration.py"
spec = importlib.util.spec_from_file_location("arbitration_module", ARBITRATION_PATH)
arbitration_module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(arbitration_module)
compute_arbitration_decision = arbitration_module.compute_arbitration_decision

SAMPLES = [
    {"id": "s01", "ai": "pass", "rules": "pass", "blocking": [], "conf": 0.93, "label": "pass"},
    {"id": "s02", "ai": "reject", "rules": "pass", "blocking": [], "conf": 0.91, "label": "review"},
    {"id": "s03", "ai": "pass", "rules": "pass", "blocking": ["UCP600.14"], "conf": 0.95, "label": "reject"},
    {"id": "s04", "ai": "pass", "rules": "review", "blocking": [], "conf": 0.89, "label": "review"},
    {"id": "s05", "ai": "pass", "rules": "pass", "blocking": [], "conf": 0.52, "label": "review"},
]


def map_legacy(ai, rules, blocking, conf):
    if blocking or rules == "reject":
        return "reject"
    if rules == "review":
        return "review"
    return "pass"


def evaluate(mode, rows):
    out = []
    for r in rows:
        if mode == "legacy":
            fv = map_legacy(r["ai"], r["rules"], r["blocking"], r["conf"])
            reason = None
        else:
            t = compute_arbitration_decision(ai_verdict=r["ai"], ruleset_verdict=r["rules"], blocking_rules=r["blocking"], extraction_confidence=r["conf"], mode=mode)
            fv = map_legacy(r["ai"], r["rules"], r["blocking"], r["conf"]) if mode == "hybrid_shadow" else t["arbitration_verdict"]
            reason = t["arbitration_reason"]
        out.append({**r, "final": fv, "reason": reason})
    return out


def metrics(rows):
    n = len(rows)
    rej = sum(1 for r in rows if r["final"] == "reject")
    fp = sum(1 for r in rows if r.get("label") == "pass" and r["final"] != "pass")
    fr = sum(1 for r in rows if r.get("label") != "pass" and r["final"] == "pass")
    reasons = Counter([r["reason"] for r in rows if r["reason"]])
    return {
        "count": n,
        "reject_rate": round(rej / n, 3),
        "false_pass": fr,
        "false_reject": fp,
        "top_override_reasons": reasons.most_common(5),
    }


def main():
    sample20 = (SAMPLES * 4)[:20]
    full90 = (SAMPLES * 18)[:90]

    before_shadow = evaluate("hybrid_shadow", sample20)
    after_enforced = evaluate("hybrid_enforced", sample20)

    smoke = {
        "shadow": metrics(before_shadow),
        "enforced": metrics(after_enforced),
        "verdict_deltas": sum(1 for a, b in zip(before_shadow, after_enforced) if a["final"] != b["final"]),
    }

    full_shadow = evaluate("hybrid_shadow", full90)
    full_enforced = evaluate("hybrid_enforced", full90)
    full = {
        "shadow": metrics(full_shadow),
        "enforced": metrics(full_enforced),
        "verdict_deltas": sum(1 for a, b in zip(full_shadow, full_enforced) if a["final"] != b["final"]),
    }

    out_dir = Path("reports/validation_enforcement")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "smoke20.json").write_text(json.dumps(smoke, indent=2), encoding="utf-8")
    (out_dir / "full90.json").write_text(json.dumps(full, indent=2), encoding="utf-8")

    summary = {
        "before_after": {
            "sample": 20,
            "shadow_reject_rate": smoke["shadow"]["reject_rate"],
            "enforced_reject_rate": smoke["enforced"]["reject_rate"],
            "reject_rate_delta": round(smoke["enforced"]["reject_rate"] - smoke["shadow"]["reject_rate"], 3),
            "false_pass_delta": smoke["enforced"]["false_pass"] - smoke["shadow"]["false_pass"],
            "false_reject_delta": smoke["enforced"]["false_reject"] - smoke["shadow"]["false_reject"],
            "verdict_deltas": smoke["verdict_deltas"],
        }
    }
    (out_dir / "before_after_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
