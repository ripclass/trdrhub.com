from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

from app.services.facts.document_facts import (  # noqa: E402
    apply_inspection_fact_graph_to_validation_inputs,
    project_inspection_validation_context,
)


def test_project_inspection_validation_context_only_keeps_resolved_facts() -> None:
    projected = project_inspection_validation_context(
        {
            "inspection_result": "stale-result",
            "gross_weight": "stale-gross",
            "analysis_result": "stale-analysis",
            "other_field": "kept",
        },
        fact_graph={
            "version": "fact_graph_v1",
            "facts": [
                {
                    "field_name": "inspection_result",
                    "value": "PASSED",
                    "normalized_value": "PASSED",
                    "verification_state": "confirmed",
                },
                {
                    "field_name": "gross_weight",
                    "value": "20,400 KGS",
                    "normalized_value": "20,400 KGS",
                    "verification_state": "operator_confirmed",
                },
                {
                    "field_name": "analysis_result",
                    "value": "Moisture within tolerance",
                    "normalized_value": "Moisture within tolerance",
                    "verification_state": "candidate",
                },
            ],
        },
    )

    assert projected["inspection_result"] == "PASSED"
    assert projected["gross_weight"] == "20,400 KGS"
    assert "analysis_result" not in projected
    assert projected["other_field"] == "kept"


def test_apply_inspection_fact_graph_to_validation_inputs_mutates_payload_and_context() -> None:
    payload = {
        "documents": [
            {
                "document_id": "doc-inspection",
                "document_type": "inspection_certificate",
                "extracted_fields": {
                    "inspection_result": "PASSED",
                    "gross_weight": "20,400 KGS",
                    "net_weight": "18,950 KGS",
                },
                "fact_graph_v1": {
                    "version": "fact_graph_v1",
                    "facts": [
                        {
                            "field_name": "inspection_result",
                            "value": "PASSED",
                            "normalized_value": "PASSED",
                            "verification_state": "confirmed",
                        },
                        {
                            "field_name": "gross_weight",
                            "value": "20,400 KGS",
                            "normalized_value": "20,400 KGS",
                            "verification_state": "operator_confirmed",
                        },
                        {
                            "field_name": "analysis_result",
                            "value": "Moisture within tolerance",
                            "normalized_value": "Moisture within tolerance",
                            "verification_state": "candidate",
                        },
                    ],
                },
            }
        ],
        "inspection_certificate": {
            "inspection_result": "stale-result",
            "analysis_result": "stale-analysis",
        },
    }
    extracted_context = {
        "documents": payload["documents"],
        "inspection_certificate": {
            "inspection_result": "old-result",
            "gross_weight": "old-gross",
        },
    }

    projected = apply_inspection_fact_graph_to_validation_inputs(payload, extracted_context)

    assert projected["inspection_result"] == "PASSED"
    assert projected["gross_weight"] == "20,400 KGS"
    assert "analysis_result" not in projected
    assert payload["inspection_certificate"] == projected
    assert extracted_context["inspection_certificate"] == projected
