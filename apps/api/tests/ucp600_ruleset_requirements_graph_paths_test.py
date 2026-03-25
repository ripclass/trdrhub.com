from __future__ import annotations

import json
from pathlib import Path


RULESET_PATH = (
    Path(__file__).resolve().parents[1]
    / "rulesets"
    / "icc.ucp600"
    / "icc.ucp600-2007-v1.0.2.json"
)


def test_ucp600_non_negotiable_sea_waybill_rule_uses_structured_requirements_toggle() -> None:
    rules = json.loads(RULESET_PATH.read_text(encoding="utf-8"))

    rule = next(entry for entry in rules if entry.get("rule_id") == "UCP600-21")
    applies_if = rule.get("applies_if") or []

    assert {
        "field": "lc.requirements_structured_v1.toggles.non_negotiable_allowed",
        "operator": "equals",
        "value": True,
    } in applies_if
