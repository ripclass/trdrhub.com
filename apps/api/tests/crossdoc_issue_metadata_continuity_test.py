from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

os.environ["DEBUG"] = "false"

from app.services.validation.crossdoc_validator import CrossDocIssue, DocumentType  # noqa: E402
from app.services.validation.issue_engine import IssueSeverity  # noqa: E402


def test_crossdoc_issue_to_dict_preserves_overlap_metadata() -> None:
    issue = CrossDocIssue(
        rule_id="CROSSDOC-INV-002",
        title="Invoice Issuer Does Not Match LC Beneficiary",
        severity=IssueSeverity.CRITICAL,
        message="Invoice issuer does not match LC beneficiary.",
        expected="Invoice issued by: BANGLADESH EXPORT",
        found="Invoice issued by: EASTERN APPAREL SOURCING",
        suggestion="Ensure invoice shows the LC beneficiary.",
        source_doc=DocumentType.INVOICE,
        target_doc=DocumentType.LC,
        source_field="issuer",
        target_field="beneficiary",
    )

    payload = issue.to_dict()

    assert payload["source_doc"] == "commercial_invoice"
    assert payload["target_doc"] == "letter_of_credit"
    assert payload["source_field"] == "issuer"
    assert payload["target_field"] == "beneficiary"
