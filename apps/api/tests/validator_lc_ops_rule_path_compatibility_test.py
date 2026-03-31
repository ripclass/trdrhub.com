from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

os.environ["DEBUG"] = "false"

from app.services import validator as validator_module  # noqa: E402


def test_extract_rule_field_paths_includes_reference_and_computed_fields() -> None:
    rule = {
        "conditions": [
            {
                "field": "insurance_doc.originals_presented",
                "reference_field": "insurance_doc.originals_issued",
                "computed_field": "presentation.date + 5 banking_days",
                "type": "amount_comparison",
            }
        ]
    }

    paths = validator_module._extract_rule_field_paths(rule)

    assert "insurance_doc.originals_presented" in paths
    assert "insurance_doc.originals_issued" in paths
    assert "presentation.date + 5 banking_days" in paths


def test_rule_targets_documents_understands_insurance_doc_alias() -> None:
    rule = {
        "conditions": [
            {
                "field": "insurance_doc.originals_presented",
                "reference_field": "insurance_doc.originals_issued",
                "type": "amount_comparison",
            }
        ]
    }

    targets = validator_module._rule_targets_documents(rule)

    assert targets == {"insurance_certificate"}


def test_rule_targets_documents_infers_generic_document_type_selectors() -> None:
    courier_rule = {
        "conditions": [
            {
                "type": "field_equals_any",
                "field": "transport_document.type",
                "allowed_values": [
                    "courier_receipt",
                    "post_receipt",
                    "certificate_of_posting",
                ],
            }
        ]
    }
    coo_rule = {
        "conditions": [
            {
                "type": "field_match",
                "field": "document.type",
                "operator": "equals",
                "value": "certificate_of_origin",
            }
        ]
    }

    courier_targets = validator_module._rule_targets_documents(courier_rule)
    coo_targets = validator_module._rule_targets_documents(coo_rule)

    assert courier_targets == {"courier_receipt", "post_receipt", "certificate_of_posting"}
    assert coo_targets == {"certificate_of_origin"}


def test_rule_matches_doc_requirements_rejects_unsupported_special_targets() -> None:
    courier_rule = {
        "conditions": [
            {
                "type": "field_equals_any",
                "field": "transport_document.type",
                "allowed_values": ["courier_receipt"],
            }
        ]
    }

    matches = validator_module._rule_matches_doc_requirements(
        courier_rule,
        requirements={"bill_of_lading": True},
        doc_ready_map={
            "lc": True,
            "commercial_invoice": True,
            "bill_of_lading": True,
            "packing_list": True,
            "certificate_of_origin": True,
            "insurance_certificate": True,
            "inspection_certificate": False,
            "beneficiary_certificate": False,
        },
    )

    assert matches is False
