from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

os.environ["DEBUG"] = "false"

from app.routers.validation import validation_execution as validation_execution_module  # noqa: E402
from app.services import rules_service as rules_service_module  # noqa: E402


class _WatchRulesService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str | None]] = []

    async def get_active_ruleset(
        self,
        domain: str,
        jurisdiction: str = "global",
        document_type: str | None = None,
    ) -> dict[str, object] | None:
        self.calls.append((domain, jurisdiction, document_type))
        assert domain == "icc.ucp600"
        assert document_type is None
        if jurisdiction != "global":
            return None
        return {
            "rules": [
                {
                    "rule_id": "UCP600-28A",
                    "domain": "lc_ops",
                    "document_type": "insurance",
                    "rule_type": "letter",
                    "consequence_class": "insurance_doc_discrepancy",
                    "execution_priority": "primary",
                    "parent_rule": "UCP600-28",
                    "conditions": [
                        {
                            "field": "insurance_doc.originals_presented",
                            "operator": "less_than",
                            "reference_field": "insurance_doc.originals_issued",
                            "type": "amount_comparison",
                        }
                    ],
                    "expected_outcome": {
                        "valid": ["Presentation complies"],
                        "invalid": ["Not all issued originals presented."],
                    },
                }
            ],
            "ruleset": {
                "ruleset_version": "1.0.1",
                "rulebook_version": "UCP600",
            },
            "ruleset_version": "1.0.1",
            "rulebook_version": "UCP600",
        }


@pytest.mark.asyncio
async def test_build_db_rule_watch_debug_evaluates_watched_rule(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_service = _WatchRulesService()
    monkeypatch.setattr(rules_service_module, "get_rules_service", lambda: fake_service)

    debug = await validation_execution_module._build_db_rule_watch_debug(
        domain="icc.ucp600",
        jurisdiction="bd",
        document_data={
            "insurance_doc": {
                "originals_presented": 1,
                "originals_issued": 2,
            }
        },
    )

    watch = debug["watched_rules"]["UCP600-28A"]
    assert debug["ruleset_version"] == "1.0.1"
    assert debug["resolved_jurisdiction"] == "global"
    assert fake_service.calls == [
        ("icc.ucp600", "bd", None),
        ("icc.ucp600", "global", None),
    ]
    assert watch["present"] is True
    assert watch["resolved_fields"]["insurance_doc.originals_presented"] == 1
    assert watch["resolved_fields"]["insurance_doc.originals_issued"] == 2
    assert watch["outcome"]["passed"] is False
    assert watch["outcome"]["not_applicable"] is False


@pytest.mark.asyncio
async def test_build_db_rule_watch_debug_marks_missing_rules(monkeypatch: pytest.MonkeyPatch) -> None:
    class _EmptyRulesService:
        async def get_active_ruleset(self, domain: str, jurisdiction: str = "global", document_type: str | None = None):
            return {"rules": [], "ruleset_version": "1.0.1", "rulebook_version": "UCP600"}

    monkeypatch.setattr(rules_service_module, "get_rules_service", lambda: _EmptyRulesService())

    debug = await validation_execution_module._build_db_rule_watch_debug(
        domain="icc.ucp600",
        jurisdiction="global",
        document_data={},
    )

    assert debug["watched_rules"]["UCP600-28A"] == {"present": False}
