from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

from app.services.facts.document_facts import (  # noqa: E402
    apply_insurance_fact_graph_to_validation_inputs,
    project_insurance_validation_context,
)


def test_project_insurance_validation_context_only_keeps_resolved_facts() -> None:
    projected = project_insurance_validation_context(
        {
            "policy_number": "stale-policy",
            "insured_amount": "stale-amount",
            "coverage_type": "stale-coverage",
            "other_field": "kept",
        },
        fact_graph={
            "version": "fact_graph_v1",
            "facts": [
                {
                    "field_name": "policy_number",
                    "value": "POL-2026-001",
                    "normalized_value": "POL-2026-001",
                    "verification_state": "confirmed",
                },
                {
                    "field_name": "insured_amount",
                    "value": "USD 125,000.50",
                    "normalized_value": "125000.50",
                    "verification_state": "operator_confirmed",
                },
                {
                    "field_name": "coverage_type",
                    "value": "ALL RISKS",
                    "normalized_value": "ALL RISKS",
                    "verification_state": "candidate",
                },
            ],
        },
    )

    assert projected["policy_number"] == "POL-2026-001"
    assert projected["insured_amount"] == "125000.50"
    assert "coverage_type" not in projected
    assert projected["other_field"] == "kept"


def test_apply_insurance_fact_graph_to_validation_inputs_mutates_payload_and_context() -> None:
    payload = {
        "documents": [
            {
                "document_id": "doc-insurance",
                "document_type": "insurance_certificate",
                "extracted_fields": {
                    "policy_number": "POL-2026-001",
                    "insured_amount": "USD 125,000.50",
                    "currency": "USD",
                },
                "fact_graph_v1": {
                    "version": "fact_graph_v1",
                    "facts": [
                        {
                            "field_name": "policy_number",
                            "value": "POL-2026-001",
                            "normalized_value": "POL-2026-001",
                            "verification_state": "confirmed",
                        },
                        {
                            "field_name": "insured_amount",
                            "value": "USD 125,000.50",
                            "normalized_value": "125000.50",
                            "verification_state": "confirmed",
                        },
                        {
                            "field_name": "currency",
                            "value": "USD",
                            "normalized_value": "USD",
                            "verification_state": "operator_confirmed",
                        },
                        {
                            "field_name": "coverage_type",
                            "value": "ALL RISKS",
                            "normalized_value": "ALL RISKS",
                            "verification_state": "candidate",
                        },
                    ],
                },
            }
        ],
        "insurance_certificate": {
            "policy_number": "stale-policy",
            "coverage_type": "stale-coverage",
        },
    }
    extracted_context = {
        "documents": payload["documents"],
        "insurance_certificate": {
            "policy_number": "old-policy",
            "insured_amount": "old-amount",
        },
    }

    projected = apply_insurance_fact_graph_to_validation_inputs(payload, extracted_context)

    assert projected["policy_number"] == "POL-2026-001"
    assert projected["insured_amount"] == "125000.50"
    assert projected["currency"] == "USD"
    assert "coverage_type" not in projected
    assert payload["insurance_certificate"] == projected
    assert payload["insurance"] == projected
    assert extracted_context["insurance_certificate"] == projected
    assert extracted_context["insurance"] == projected


def test_apply_insurance_fact_graph_prefers_real_insurance_doc_over_beneficiary_certificate() -> None:
    payload = {
        "documents": [
            {
                "document_id": "doc-beneficiary",
                "document_type": "beneficiary_certificate",
                "fact_graph_v1": {
                    "version": "fact_graph_v1",
                    "facts": [
                        {
                            "field_name": "issuer_name",
                            "value": "Beneficiary Co.",
                            "normalized_value": "BENEFICIARY CO.",
                            "verification_state": "confirmed",
                        }
                    ],
                },
            },
            {
                "document_id": "doc-insurance",
                "document_type": "insurance_certificate",
                "fact_graph_v1": {
                    "version": "fact_graph_v1",
                    "facts": [
                        {
                            "field_name": "insured_amount",
                            "value": "USD 150,000.00",
                            "normalized_value": "150000.00",
                            "verification_state": "confirmed",
                        },
                        {
                            "field_name": "currency",
                            "value": "USD",
                            "normalized_value": "USD",
                            "verification_state": "confirmed",
                        },
                    ],
                },
            },
        ],
        "insurance_certificate": {},
    }
    extracted_context = {
        "documents": payload["documents"],
        "insurance_certificate": {},
    }

    projected = apply_insurance_fact_graph_to_validation_inputs(payload, extracted_context)

    assert projected["insured_amount"] == "150000.00"
    assert projected["currency"] == "USD"
    assert payload["insurance"] == projected
    assert extracted_context["insurance"] == projected


def test_project_insurance_validation_context_projects_originals_presented() -> None:
    projected = project_insurance_validation_context(
        {},
        fact_graph={
            "version": "fact_graph_v1",
            "facts": [
                {
                    "field_name": "originals_presented",
                    "value": 1,
                    "normalized_value": 1,
                    "verification_state": "confirmed",
                }
            ],
        },
    )

    assert projected["originals_presented"] == 1
    assert projected["number_of_originals"] == 1
