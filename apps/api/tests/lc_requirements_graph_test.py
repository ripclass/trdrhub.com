from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

from app.services.requirements import build_lc_requirements_graph_v1  # noqa: E402


def test_build_lc_requirements_graph_v1_compiles_required_docs_and_core_terms() -> None:
    graph = build_lc_requirements_graph_v1(
        {
            "document_id": "doc-lc",
            "document_type": "letter_of_credit",
            "extraction_lane": "document_ai",
            "lc_classification": {
                "workflow_orientation": "export",
                "applicable_rules": "UCP LATEST VERSION",
                "required_documents": [
                    {"code": "commercial_invoice", "display_name": "Commercial Invoice"},
                    {"code": "bill_of_lading", "display_name": "Bill Of Lading"},
                ],
                "requirement_conditions": ["Invoice must mention LC number"],
                "unmapped_requirements": ["Third-party docs clause needs interpretation"],
            },
            "fact_graph_v1": {
                "version": "fact_graph_v1",
                "document_type": "letter_of_credit",
                "facts": [
                    {
                        "field_name": "lc_number",
                        "value": "EXP2026BD001",
                        "normalized_value": "EXP2026BD001",
                    },
                    {
                        "field_name": "amount",
                        "value": "455750",
                        "normalized_value": "455750",
                    },
                    {
                        "field_name": "currency",
                        "value": "USD",
                        "normalized_value": "USD",
                    },
                    {
                        "field_name": "port_of_loading",
                        "value": "Chittagong",
                        "normalized_value": "Chittagong",
                    },
                ],
            },
        }
    )

    assert graph is not None
    assert graph["version"] == "requirements_graph_v1"
    assert graph["required_document_types"] == ["commercial_invoice", "bill_of_lading"]
    assert graph["core_terms"]["lc_number"] == "EXP2026BD001"
    assert "port_of_loading" in graph["required_fact_fields"]
    assert graph["documentary_conditions"] == ["Invoice must mention LC number"]
    assert graph["ambiguous_conditions"] == ["Third-party docs clause needs interpretation"]
