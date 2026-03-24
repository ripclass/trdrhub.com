from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

from app.services.facts.document_facts import (  # noqa: E402
    apply_packing_list_fact_graph_to_validation_inputs,
    project_packing_list_validation_context,
)


def test_project_packing_list_validation_context_only_keeps_resolved_facts() -> None:
    projected = project_packing_list_validation_context(
        {
            "date": "stale-date",
            "gross_weight": "stale gross",
            "packing_size_breakdown": "stale size breakdown",
            "other_field": "kept",
        },
        fact_graph={
            "version": "fact_graph_v1",
            "facts": [
                {
                    "field_name": "document_date",
                    "value": "20 Apr 2026",
                    "normalized_value": "2026-04-20",
                    "verification_state": "confirmed",
                },
                {
                    "field_name": "gross_weight",
                    "value": "20,400 KGS",
                    "normalized_value": "20,400 KGS",
                    "verification_state": "operator_confirmed",
                },
                {
                    "field_name": "net_weight",
                    "value": "18,950 KGS",
                    "normalized_value": "18,950 KGS",
                    "verification_state": "candidate",
                },
            ],
        },
    )

    assert projected["date"] == "2026-04-20"
    assert projected["document_date"] == "2026-04-20"
    assert projected["gross_weight"] == "20,400 KGS"
    assert "net_weight" not in projected
    assert "packing_size_breakdown" not in projected
    assert projected["other_field"] == "kept"


def test_apply_packing_list_fact_graph_to_validation_inputs_mutates_payload_and_context() -> None:
    payload = {
        "documents": [
            {
                "document_id": "doc-packing",
                "document_type": "packing_list",
                "extracted_fields": {
                    "packing_list_number": "PL-026",
                    "date": "20 Apr 2026",
                    "gross_weight": "20,400 KGS",
                    "net_weight": "18,950 KGS",
                },
                "fact_graph_v1": {
                    "version": "fact_graph_v1",
                    "facts": [
                        {
                            "field_name": "packing_list_number",
                            "value": "PL-026",
                            "normalized_value": "PL-026",
                            "verification_state": "confirmed",
                        },
                        {
                            "field_name": "document_date",
                            "value": "20 Apr 2026",
                            "normalized_value": "2026-04-20",
                            "verification_state": "confirmed",
                        },
                        {
                            "field_name": "total_packages",
                            "value": "1850",
                            "normalized_value": "1850",
                            "verification_state": "confirmed",
                        },
                        {
                            "field_name": "gross_weight",
                            "value": "20,400 KGS",
                            "normalized_value": "20,400 KGS",
                            "verification_state": "operator_confirmed",
                        },
                        {
                            "field_name": "net_weight",
                            "value": "18,950 KGS",
                            "normalized_value": "18,950 KGS",
                            "verification_state": "candidate",
                        },
                    ],
                },
            }
        ],
        "packing_list": {
            "date": "stale-date",
            "gross_weight": "stale-gross",
            "net_weight": "stale-net",
        },
    }
    extracted_context = {
        "documents": payload["documents"],
        "packing_list": {
            "packing_list_number": "old-number",
            "gross_weight": "old-gross",
        },
    }

    projected = apply_packing_list_fact_graph_to_validation_inputs(payload, extracted_context)

    assert projected["packing_list_number"] == "PL-026"
    assert projected["date"] == "2026-04-20"
    assert projected["document_date"] == "2026-04-20"
    assert projected["total_packages"] == "1850"
    assert projected["gross_weight"] == "20,400 KGS"
    assert "net_weight" not in projected
    assert payload["packing_list"] == projected
    assert extracted_context["packing_list"] == projected
