from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

os.environ["DEBUG"] = "false"

from app.routers.rules_admin import _validate_ruleset_json  # noqa: E402


def test_validate_ruleset_json_rejects_duplicate_rule_ids() -> None:
    report = _validate_ruleset_json(
        [
            {"rule_id": "ISBP821-A3", "title": "First", "conditions": []},
            {"rule_id": "ISBP821-A3", "title": "Second", "conditions": []},
        ],
        domain="icc.isbp745",
        jurisdiction="global",
    )

    assert report.valid is False
    assert any("Duplicate rule_ids found:" in error for error in report.errors)
    assert "ISBP821-A3" in report.metadata["duplicate_rule_ids"]
