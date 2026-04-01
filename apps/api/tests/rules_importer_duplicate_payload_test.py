from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

os.environ["DEBUG"] = "false"

from app.services.rules_importer import RulesImporter  # noqa: E402


class _QueryStub:
    def filter(self, *args, **kwargs):
        return self

    def all(self):
        return []


class _DBStub:
    def query(self, *args, **kwargs):
        return _QueryStub()


def test_import_ruleset_rejects_duplicate_payload_rule_ids() -> None:
    importer = RulesImporter(db=_DBStub())
    ruleset = SimpleNamespace(
        id="00000000-0000-0000-0000-000000000000",
        domain="icc.isbp745",
        jurisdiction="global",
        ruleset_version="1.0.0",
        rulebook_version="821E",
    )

    payload = [
        {"rule_id": "ISBP821-A3", "title": "First", "conditions": []},
        {"rule_id": "ISBP821-A3", "title": "Second", "conditions": []},
    ]

    with pytest.raises(ValueError, match="Duplicate rule_ids in payload: ISBP821-A3"):
        importer.import_ruleset(
            ruleset=ruleset,
            rules_payload=payload,
            activate=False,
            actor_id=None,
        )
