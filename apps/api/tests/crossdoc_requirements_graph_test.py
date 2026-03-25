from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

from app.services.crossdoc import run_cross_document_checks  # noqa: E402


def test_run_cross_document_checks_prefers_requirements_graph_for_missing_insurance() -> None:
    issues = run_cross_document_checks(
        {
            "lc": {
                "requirements_graph_v1": {
                    "version": "requirements_graph_v1",
                    "required_document_types": ["commercial_invoice", "insurance_policy"],
                }
            },
            "documents_presence": {
                "insurance_certificate": {"present": False},
            },
            "documents": [],
            "lc_text": "",
        }
    )

    rule_ids = {issue["rule"] for issue in issues}
    assert "CROSSDOC-DOC-1" in rule_ids


def test_run_cross_document_checks_does_not_raise_missing_insurance_without_graph_or_lc_text() -> None:
    issues = run_cross_document_checks(
        {
            "lc": {},
            "documents_presence": {
                "insurance_certificate": {"present": False},
            },
            "documents": [],
            "lc_text": "",
        }
    )

    rule_ids = {issue["rule"] for issue in issues}
    assert "CROSSDOC-DOC-1" not in rule_ids
