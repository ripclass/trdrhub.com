from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

from app.services.facts.supporting_facts import build_supporting_fact_set  # noqa: E402


def _fact_by_name(payload: dict, field_name: str) -> dict:
    facts = payload.get("facts") or []
    for fact in facts:
        if fact.get("field_name") == field_name:
            return fact
    raise AssertionError(f"Missing fact {field_name}")


def test_build_supporting_fact_set_preserves_generic_supporting_document_type() -> None:
    payload = build_supporting_fact_set(
        {
            "document_type": "shipment_advice",
            "extraction_lane": "document_ai",
            "extracted_fields": {
                "advice_number": "SA-2026-01",
                "date": "21 Apr 2026",
                "issuer": "Oceanic Carrier Ltd.",
                "lc_reference": "EXP2026BD019",
            },
            "field_details": {
                "advice_number": {
                    "value": "SA-2026-01",
                    "verification": "confirmed",
                    "source": "multimodal:pdf_pages",
                }
            },
        }
    )

    reference_fact = _fact_by_name(payload, "document_reference")
    issue_date_fact = _fact_by_name(payload, "issue_date")
    issuer_fact = _fact_by_name(payload, "issuer_name")

    assert payload["document_type"] == "shipment_advice"
    assert reference_fact["normalized_value"] == "SA-2026-01"
    assert issue_date_fact["normalized_value"] == "2026-04-21"
    assert issuer_fact["normalized_value"] == "Oceanic Carrier Ltd."
