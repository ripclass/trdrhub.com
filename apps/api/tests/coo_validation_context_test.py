from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

from app.services.facts.document_facts import (  # noqa: E402
    apply_coo_fact_graph_to_validation_inputs,
    project_coo_validation_context,
)


def test_project_coo_validation_context_only_keeps_resolved_facts() -> None:
    projected = project_coo_validation_context(
        {
            "country_of_origin": "stale-origin",
            "goods_description": "stale goods",
            "issue_date": "stale-date",
            "other_field": "kept",
        },
        fact_graph={
            "version": "fact_graph_v1",
            "facts": [
                {
                    "field_name": "country_of_origin",
                    "value": "Bangladesh",
                    "normalized_value": "Bangladesh",
                    "verification_state": "confirmed",
                },
                {
                    "field_name": "goods_description",
                    "value": "100% cotton knit shirts",
                    "normalized_value": "100% cotton knit shirts",
                    "verification_state": "operator_confirmed",
                },
                {
                    "field_name": "exporter_name",
                    "value": "Dhaka Knitwear",
                    "normalized_value": "Dhaka Knitwear",
                    "verification_state": "candidate",
                },
            ],
        },
    )

    assert projected["country_of_origin"] == "Bangladesh"
    assert projected["goods_description"] == "100% cotton knit shirts"
    assert "exporter_name" not in projected
    assert "issue_date" not in projected
    assert projected["other_field"] == "kept"


def test_apply_coo_fact_graph_to_validation_inputs_mutates_payload_and_context() -> None:
    payload = {
        "documents": [
            {
                "document_id": "doc-coo",
                "document_type": "certificate_of_origin",
                "extracted_fields": {
                    "certificate_number": "COO-26",
                    "country_of_origin": "Bangladesh",
                    "goods_description": "100% cotton knit shirts",
                    "issue_date": "20 Apr 2026",
                },
                "fact_graph_v1": {
                    "version": "fact_graph_v1",
                    "facts": [
                        {
                            "field_name": "certificate_number",
                            "value": "COO-26",
                            "normalized_value": "COO-26",
                            "verification_state": "confirmed",
                        },
                        {
                            "field_name": "country_of_origin",
                            "value": "Bangladesh",
                            "normalized_value": "Bangladesh",
                            "verification_state": "confirmed",
                        },
                        {
                            "field_name": "goods_description",
                            "value": "100% cotton knit shirts",
                            "normalized_value": "100% cotton knit shirts",
                            "verification_state": "operator_confirmed",
                        },
                        {
                            "field_name": "issue_date",
                            "value": "20 Apr 2026",
                            "normalized_value": "2026-04-20",
                            "verification_state": "candidate",
                        },
                    ],
                },
            }
        ],
        "certificate_of_origin": {
            "country_of_origin": "stale-origin",
            "issue_date": "stale-date",
        },
    }
    extracted_context = {
        "documents": payload["documents"],
        "certificate_of_origin": {
            "certificate_number": "old-number",
            "country_of_origin": "old-origin",
        },
    }

    projected = apply_coo_fact_graph_to_validation_inputs(payload, extracted_context)

    assert projected["certificate_number"] == "COO-26"
    assert projected["country_of_origin"] == "Bangladesh"
    assert projected["goods_description"] == "100% cotton knit shirts"
    assert "issue_date" not in projected
    assert payload["certificate_of_origin"] == projected
    assert extracted_context["certificate_of_origin"] == projected
