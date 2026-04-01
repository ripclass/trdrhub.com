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

from app.routers.rules_admin import _assert_ruleset_import_integrity  # noqa: E402
from app.schemas.ruleset import RulesImportSummaryModel  # noqa: E402
from app.services.rules_importer import RulesImporter  # noqa: E402


class _QueryStub:
    def filter(self, *args, **kwargs):
        return self

    def all(self):
        return []

    def update(self, *args, **kwargs):
        return 0


class _DBStub:
    def __init__(self) -> None:
        self.added = []
        self.flush_called = False
        self.commit_called = False

    def query(self, *args, **kwargs):
        return _QueryStub()

    def add(self, value):
        self.added.append(value)

    def flush(self):
        self.flush_called = True

    def commit(self):
        self.commit_called = True
        raise AssertionError("RulesImporter.import_ruleset should not commit directly")


def _build_summary(**overrides) -> RulesImportSummaryModel:
    payload = {
        "total_rules": 2,
        "inserted": 2,
        "updated": 0,
        "skipped_existing": 0,
        "skipped": 0,
        "errors": [],
        "warnings": [],
    }
    payload.update(overrides)
    return RulesImportSummaryModel.model_validate(payload)


def test_assert_ruleset_import_integrity_rejects_import_errors() -> None:
    with pytest.raises(ValueError, match="import produced errors"):
        _assert_ruleset_import_integrity(
            ruleset=SimpleNamespace(id="ruleset-1"),
            rules_payload=[{"rule_id": "UCP600-28A"}],
            import_summary=_build_summary(total_rules=1, inserted=0, errors=["UCP600-28A: bad row"]),
            active_rule_count=0,
        )


def test_assert_ruleset_import_integrity_rejects_active_count_mismatch() -> None:
    with pytest.raises(ValueError, match="expected 2, got 1"):
        _assert_ruleset_import_integrity(
            ruleset=SimpleNamespace(id="ruleset-2"),
            rules_payload=[{"rule_id": "UCP600-28"}, {"rule_id": "UCP600-28A"}],
            import_summary=_build_summary(),
            active_rule_count=1,
        )


def test_import_ruleset_flushes_but_does_not_commit() -> None:
    importer = RulesImporter(db=_DBStub())
    ruleset = SimpleNamespace(
        id="00000000-0000-0000-0000-000000000000",
        domain="icc.ucp600",
        jurisdiction="global",
        ruleset_version="1.0.1",
        rulebook_version="UCP600",
    )

    importer.import_ruleset(
        ruleset=ruleset,
        rules_payload=[{"rule_id": "UCP600-28A", "title": "Insurance Originals", "conditions": []}],
        activate=False,
        actor_id=None,
    )

    assert importer.db.flush_called is True
    assert importer.db.commit_called is False
