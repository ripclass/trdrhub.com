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

from app.services import rules_service as rules_service_module  # noqa: E402
from app.services import validator as validator_module  # noqa: E402
from app.services.facts import (  # noqa: E402
    apply_bl_fact_graph_to_validation_inputs,
    apply_insurance_fact_graph_to_validation_inputs,
    apply_invoice_fact_graph_to_validation_inputs,
    apply_lc_fact_graph_to_validation_inputs,
)


class _LcOpsCompatibilityRulesService:
    async def get_active_ruleset(
        self,
        domain: str,
        jurisdiction: str = "global",
        document_type: str | None = None,
    ) -> dict[str, object] | None:
        if domain == "icc.ucp600":
            return {
                "rules": [
                    {
                        "rule_id": "UCP600-28A",
                        "domain": "lc_ops",
                        "jurisdiction": "global",
                        "document_type": "insurance",
                        "severity": "fail",
                        "deterministic": True,
                        "requires_llm": False,
                        "consequence_class": "insurance_doc_discrepancy",
                        "title": "Insurance Document: Originals Must Be Presented",
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
                            "invalid": [
                                "Not all issued originals of the insurance document presented.",
                                "Remediation: Require all originals.",
                            ],
                        },
                    }
                ],
                "ruleset_version": "1.0.2",
                "rulebook_version": "UCP600:2007",
            }
        if domain == "icc.isbp745":
            return {
                "rules": [
                    {
                        "rule_id": "ISBP745-A1",
                        "domain": "icc",
                        "jurisdiction": "global",
                        "severity": "info",
                        "deterministic": True,
                        "requires_llm": False,
                        "consequence_class": "domain_logic",
                        "title": "Abbreviations",
                        "conditions": [
                            {
                                "type": "document_content",
                                "rule": "Generally accepted abbreviations are acceptable in place of full words and vice versa.",
                            }
                        ],
                        "expected_outcome": {
                            "valid": ["Abbreviations acceptable"],
                            "invalid": ["Bank refuses document for using abbreviation."],
                        },
                    }
                ],
                "ruleset_version": "1.0.2",
                "rulebook_version": "ISBP745",
            }
        return {"rules": [], "ruleset_version": "1.0.2", "rulebook_version": domain}


@pytest.mark.asyncio
async def test_validate_document_async_surfaces_specific_lc_ops_discrepancy_without_narrative_singletons(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_service = _LcOpsCompatibilityRulesService()

    monkeypatch.setattr(rules_service_module, "get_rules_service", lambda: fake_service)

    async def _fake_inject_semantic_conditions(rules, document_data, evaluator):
        return rules, {}

    monkeypatch.setattr(
        validator_module,
        "_inject_semantic_conditions",
        _fake_inject_semantic_conditions,
    )

    results = await validator_module.validate_document_async(
        {
            "domain": "icc.ucp600",
            "jurisdiction": "global",
            "supplement_domains": ["icc.isbp745"],
            "lc": {
                "beneficiary_name": "Bangladesh Export Ltd",
                "requirements_graph_v1": {
                    "required_document_types": ["insurance_certificate"],
                    "requirements_structured_v1": {
                        "document_quantities": {
                            "insurance_certificate": {"originals_required": 2}
                        }
                    },
                },
            },
            "insurance": {
                "originals_presented": 1,
                "originals_issued": 2,
            },
            "insurance_doc": {
                "originals_presented": 1,
                "originals_issued": 2,
            },
        },
        document_type="commercial_invoice",
    )

    rule_ids = [result.get("rule") for result in results]

    assert "UCP600-28A" in rule_ids
    assert "ISBP745-A1" not in rule_ids


@pytest.mark.asyncio
async def test_validate_document_async_treats_lc_ops_letter_rules_as_discrepancies_without_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _MissingMetadataRulesService:
        async def get_active_ruleset(
            self,
            domain: str,
            jurisdiction: str = "global",
            document_type: str | None = None,
        ) -> dict[str, object] | None:
            if domain == "icc.ucp600":
                return {
                    "rules": [
                        {
                            "rule_id": "UCP600-28A",
                            "domain": "lc_ops",
                            "jurisdiction": "global",
                            "document_type": "insurance",
                            "severity": "fail",
                            "deterministic": True,
                            "requires_llm": False,
                            "rule_type": "letter",
                            "title": "Insurance Document: Originals Must Be Presented",
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
                                "invalid": [
                                    "Not all issued originals of the insurance document presented."
                                ],
                            },
                        }
                    ],
                    "ruleset_version": "1.0.2",
                    "rulebook_version": "UCP600:2007",
                }
            return {"rules": [], "ruleset_version": "1.0.2", "rulebook_version": domain}

    fake_service = _MissingMetadataRulesService()
    monkeypatch.setattr(rules_service_module, "get_rules_service", lambda: fake_service)

    async def _fake_inject_semantic_conditions(rules, document_data, evaluator):
        return rules, {}

    monkeypatch.setattr(
        validator_module,
        "_inject_semantic_conditions",
        _fake_inject_semantic_conditions,
    )

    results = await validator_module.validate_document_async(
        {
            "domain": "icc.ucp600",
            "jurisdiction": "global",
            "lc": {
                "requirements_graph_v1": {
                    "required_document_types": ["insurance_certificate"],
                },
            },
            "insurance": {
                "originals_presented": 1,
                "originals_issued": 2,
            },
            "insurance_doc": {
                "originals_presented": 1,
                "originals_issued": 2,
            },
        },
        document_type="commercial_invoice",
    )

    rule_ids = [result.get("rule") for result in results]
    assert rule_ids == ["UCP600-28A"]


@pytest.mark.asyncio
async def test_validate_document_async_suppresses_unrelated_transport_and_notice_rules_for_insurance_probe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _ScopedRulesService:
        async def get_active_ruleset(
            self,
            domain: str,
            jurisdiction: str = "global",
            document_type: str | None = None,
        ) -> dict[str, object] | None:
            if domain != "icc.ucp600":
                return {"rules": [], "ruleset_version": "1.0.2", "rulebook_version": domain}

            return {
                "rules": [
                    {
                        "rule_id": "UCP600-16",
                        "domain": "lc_ops",
                        "jurisdiction": "global",
                        "document_type": "lc",
                        "severity": "fail",
                        "deterministic": True,
                        "requires_llm": False,
                        "rule_type": "umbrella",
                        "title": "Discrepant Documents, Waiver and Notice",
                        "tags": ["notice", "waiver", "non_compliance", "time_limits"],
                        "conditions": [
                            {
                                "left_path": "presentation.status",
                                "right_path": "non_complying",
                                "type": "field_match",
                            },
                            {"field": "notice.content.refusal_statement", "type": "field_presence"},
                        ],
                    },
                    {
                        "rule_id": "UCP600-19",
                        "domain": "lc_ops",
                        "jurisdiction": "global",
                        "document_type": "transport",
                        "severity": "fail",
                        "deterministic": True,
                        "requires_llm": False,
                        "rule_type": "umbrella",
                        "title": "Transport Document Covering at Least Two Different Modes of Transport",
                        "tags": ["transport_document", "multimodal", "shipment", "carrier"],
                        "conditions": [
                            {"field": "transport_document.carrier_name", "type": "field_presence"},
                        ],
                    },
                    {
                        "rule_id": "UCP600-25",
                        "domain": "lc_ops",
                        "jurisdiction": "global",
                        "document_type": "certificate",
                        "severity": "warn",
                        "deterministic": True,
                        "requires_llm": False,
                        "rule_type": "umbrella",
                        "title": "Courier Receipt, Post Receipt or Certificate of Posting",
                        "tags": ["courier", "post_receipt", "certificate_of_posting"],
                        "conditions": [
                            {"field": "courier_doc.courier_name", "type": "field_presence"},
                            {"field": "post_doc.signature_or_stamp_and_date", "type": "field_presence"},
                        ],
                    },
                    {
                        "rule_id": "UCP600-28A",
                        "domain": "lc_ops",
                        "jurisdiction": "global",
                        "document_type": "insurance",
                        "severity": "fail",
                        "deterministic": True,
                        "requires_llm": False,
                        "rule_type": "letter",
                        "consequence_class": "insurance_doc_discrepancy",
                        "title": "Insurance Document: Originals Must Be Presented",
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
                            "invalid": ["Not all issued originals of the insurance document presented."],
                        },
                    },
                ],
                "ruleset_version": "1.0.2",
                "rulebook_version": "UCP600:2007",
            }

    monkeypatch.setattr(rules_service_module, "get_rules_service", lambda: _ScopedRulesService())

    async def _fake_inject_semantic_conditions(rules, document_data, evaluator):
        return rules, {}

    monkeypatch.setattr(
        validator_module,
        "_inject_semantic_conditions",
        _fake_inject_semantic_conditions,
    )

    results = await validator_module.validate_document_async(
        {
            "domain": "icc.ucp600",
            "jurisdiction": "global",
            "lc": {
                "requirements_graph_v1": {
                    "required_document_types": ["commercial_invoice", "bill_of_lading", "insurance_certificate"],
                },
            },
            "invoice": {"currency_code": "USD"},
            "bill_of_lading": {"port_of_loading": "Chittagong"},
            "insurance": {
                "originals_presented": 1,
                "originals_issued": 2,
            },
            "insurance_doc": {
                "originals_presented": 1,
                "originals_issued": 2,
            },
        },
        document_type="commercial_invoice",
    )

    rule_ids = [result.get("rule") for result in results]
    assert rule_ids == ["UCP600-28A"]


@pytest.mark.asyncio
async def test_validate_document_async_uses_projected_lc_aliases_and_normalized_ports_for_live_q28a_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FocusedRulesService:
        async def get_active_ruleset(
            self,
            domain: str,
            jurisdiction: str = "global",
            document_type: str | None = None,
        ) -> dict[str, object] | None:
            if domain != "icc.ucp600":
                return {"rules": [], "ruleset_version": "1.0.2", "rulebook_version": domain}

            return {
                "rules": [
                    {
                        "rule_id": "UCP600-18",
                        "domain": "lc_ops",
                        "jurisdiction": "global",
                        "document_type": "invoice",
                        "severity": "fail",
                        "deterministic": True,
                        "requires_llm": False,
                        "rule_type": "umbrella",
                        "consequence_class": "invoice_discrepancy",
                        "conditions": [
                            {
                                "field": "invoice.issuer",
                                "operator": "not_equals",
                                "reference_field": "lc.beneficiary",
                                "type": "field_match",
                            }
                        ],
                    },
                    {
                        "rule_id": "UCP600-18B",
                        "domain": "lc_ops",
                        "jurisdiction": "global",
                        "document_type": "invoice",
                        "severity": "fail",
                        "deterministic": True,
                        "requires_llm": False,
                        "rule_type": "letter",
                        "consequence_class": "invoice_discrepancy",
                        "conditions": [
                            {
                                "field": "invoice.buyer_name",
                                "operator": "not_equals",
                                "reference_field": "lc.applicant_name",
                                "type": "field_match",
                            }
                        ],
                    },
                    {
                        "rule_id": "UCP600-18C",
                        "domain": "lc_ops",
                        "jurisdiction": "global",
                        "document_type": "invoice",
                        "severity": "fail",
                        "deterministic": True,
                        "requires_llm": False,
                        "rule_type": "letter",
                        "consequence_class": "invoice_discrepancy",
                        "conditions": [
                            {
                                "field": "invoice.currency_code",
                                "operator": "not_equals",
                                "reference_field": "lc.currency_code",
                                "type": "field_match",
                            }
                        ],
                    },
                    {
                        "rule_id": "UCP600-20D",
                        "domain": "lc_ops",
                        "jurisdiction": "global",
                        "document_type": "transport",
                        "severity": "fail",
                        "deterministic": True,
                        "requires_llm": False,
                        "rule_type": "letter",
                        "consequence_class": "bill_of_lading_discrepancy",
                        "conditions": [
                            {
                                "field": "bill_of_lading.port_of_loading",
                                "operator": "not_equals",
                                "reference_field": "lc.port_of_loading",
                                "type": "field_match",
                            }
                        ],
                    },
                    {
                        "rule_id": "UCP600-28A",
                        "domain": "lc_ops",
                        "jurisdiction": "global",
                        "document_type": "insurance",
                        "severity": "fail",
                        "deterministic": True,
                        "requires_llm": False,
                        "rule_type": "letter",
                        "consequence_class": "insurance_doc_discrepancy",
                        "conditions": [
                            {
                                "field": "insurance_doc.originals_presented",
                                "operator": "less_than",
                                "reference_field": "insurance_doc.originals_issued",
                                "type": "amount_comparison",
                            }
                        ],
                    },
                    {
                        "rule_id": "UCP600-28D",
                        "domain": "lc_ops",
                        "jurisdiction": "global",
                        "document_type": "insurance",
                        "severity": "fail",
                        "deterministic": True,
                        "requires_llm": False,
                        "rule_type": "letter",
                        "consequence_class": "insurance_doc_discrepancy",
                        "conditions": [
                            {
                                "field": "insurance_doc.currency_code",
                                "operator": "not_equals",
                                "reference_field": "lc.currency_code",
                                "type": "field_match",
                            }
                        ],
                    },
                ],
                "ruleset_version": "1.0.2",
                "rulebook_version": "UCP600:2007",
            }

    monkeypatch.setattr(rules_service_module, "get_rules_service", lambda: _FocusedRulesService())

    async def _fake_inject_semantic_conditions(rules, document_data, evaluator):
        return rules, {}

    monkeypatch.setattr(
        validator_module,
        "_inject_semantic_conditions",
        _fake_inject_semantic_conditions,
    )

    documents = [
        {
            "document_type": "letter_of_credit",
            "extraction_lane": "document_ai",
            "fact_graph_v1": {
                "version": "fact_graph_v1",
                "document_type": "letter_of_credit",
                "facts": [
                    {"field_name": "applicant", "normalized_value": "Global Trade Corp", "verification_state": "confirmed"},
                    {"field_name": "beneficiary", "normalized_value": "Bangladesh Export Ltd", "verification_state": "confirmed"},
                    {"field_name": "currency", "normalized_value": "USD", "verification_state": "confirmed"},
                    {"field_name": "port_of_loading", "normalized_value": "Chittagong, Bangladesh", "verification_state": "confirmed"},
                ],
            },
            "requirements_graph_v1": {
                "required_document_types": ["commercial_invoice", "bill_of_lading", "insurance_certificate"],
                "requirements_structured_v1": {
                    "document_quantities": {
                        "insurance_certificate": {"originals_required": 2},
                    }
                },
            },
        },
        {
            "document_type": "commercial_invoice",
            "fact_graph_v1": {
                "version": "fact_graph_v1",
                "document_type": "commercial_invoice",
                "facts": [
                    {"field_name": "seller", "normalized_value": "Bangladesh Export Ltd", "verification_state": "confirmed"},
                    {"field_name": "buyer", "normalized_value": "Global Trade Corp", "verification_state": "confirmed"},
                    {"field_name": "currency", "normalized_value": "USD", "verification_state": "confirmed"},
                ],
            },
        },
        {
            "document_type": "bill_of_lading",
            "fact_graph_v1": {
                "version": "fact_graph_v1",
                "document_type": "bill_of_lading",
                "facts": [
                    {"field_name": "port_of_loading", "normalized_value": "Chittagong, Bangladesh", "verification_state": "confirmed"},
                ],
            },
        },
        {
            "document_type": "insurance_certificate",
            "fact_graph_v1": {
                "version": "fact_graph_v1",
                "document_type": "insurance_certificate",
                "facts": [
                    {"field_name": "currency", "normalized_value": "USD", "verification_state": "confirmed"},
                    {"field_name": "originals_presented", "normalized_value": 1, "verification_state": "confirmed"},
                ],
            },
        },
    ]
    payload = {
        "domain": "icc.ucp600",
        "jurisdiction": "global",
        "documents": documents,
        "lc": {},
    }
    extracted_context = {
        "documents": documents,
        "lc": {},
    }

    apply_lc_fact_graph_to_validation_inputs(payload, extracted_context)
    apply_invoice_fact_graph_to_validation_inputs(payload, extracted_context)
    apply_bl_fact_graph_to_validation_inputs(payload, extracted_context)
    apply_insurance_fact_graph_to_validation_inputs(payload, extracted_context)
    payload["insurance_doc"] = payload["insurance"]

    results = await validator_module.validate_document_async(
        payload,
        document_type="commercial_invoice",
    )

    rule_ids = [result.get("rule") for result in results]
    assert rule_ids == ["UCP600-28A"]


@pytest.mark.asyncio
async def test_validate_document_async_staged_ucp18_shape_passes_when_credit_aliases_exist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Ucp18RulesService:
        async def get_active_ruleset(
            self,
            domain: str,
            jurisdiction: str = "global",
            document_type: str | None = None,
        ) -> dict[str, object] | None:
            if domain != "icc.ucp600":
                return {"rules": [], "ruleset_version": "1.0.2", "rulebook_version": domain}
            return {
                "rules": [
                    {
                        "rule_id": "UCP600-18",
                        "domain": "lc_ops",
                        "jurisdiction": "global",
                        "document_type": "invoice",
                        "severity": "fail",
                        "deterministic": True,
                        "requires_llm": False,
                        "rule_type": "umbrella",
                        "consequence_class": "domain_logic",
                        "conditions": [
                            {"type": "field_match", "left_path": "invoice.issuer", "right_path": "credit.beneficiary"},
                            {"type": "field_match", "left_path": "invoice.applicant_name", "right_path": "credit.applicant_name"},
                            {"type": "field_match", "left_path": "invoice.currency", "right_path": "credit.currency"},
                            {"type": "field_match", "left_path": "invoice.goods_description", "right_path": "credit.goods_description"},
                        ],
                        "expected_outcome": {
                            "valid": ["Invoice issued by beneficiary"],
                            "invalid": ["Invoice issued by third party without Article 38 exception"],
                        },
                    }
                ],
                "ruleset_version": "1.0.2",
                "rulebook_version": "UCP600:2007",
            }

    monkeypatch.setattr(rules_service_module, "get_rules_service", lambda: _Ucp18RulesService())

    async def _fake_inject_semantic_conditions(rules, document_data, evaluator):
        return rules, {}

    monkeypatch.setattr(
        validator_module,
        "_inject_semantic_conditions",
        _fake_inject_semantic_conditions,
    )

    results = await validator_module.validate_document_async(
        {
            "domain": "icc.ucp600",
            "jurisdiction": "global",
            "invoice": {
                "issuer": "Bangladesh Export Ltd",
                "applicant_name": "Global Trade Corp",
                "currency": "USD",
                "goods_description": "100% Cotton T-Shirts, HS Code 6109.10",
            },
            "credit": {
                "beneficiary": "Bangladesh Export Ltd",
                "applicant_name": "Global Trade Corp",
                "currency": "USD",
                "goods_description": "100% Cotton T-Shirts, HS Code 6109.10",
            },
        },
        document_type="commercial_invoice",
    )

    assert [result.get("rule") for result in results] == []


@pytest.mark.asyncio
async def test_validate_document_async_staged_ucp18a_shape_uses_projected_transferability_and_issuer_aliases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Ucp18ARulesService:
        async def get_active_ruleset(
            self,
            domain: str,
            jurisdiction: str = "global",
            document_type: str | None = None,
        ) -> dict[str, object] | None:
            if domain != "icc.ucp600":
                return {"rules": [], "ruleset_version": "1.0.2", "rulebook_version": domain}
            return {
                "rules": [
                    {
                        "rule_id": "UCP600-18A",
                        "domain": "lc_ops",
                        "jurisdiction": "global",
                        "document_type": "invoice",
                        "severity": "fail",
                        "deterministic": True,
                        "requires_llm": False,
                        "rule_type": "letter",
                        "consequence_class": "invoice_discrepancy",
                        "parent_rule": "UCP600-18",
                        "conditions": [
                            {
                                "field": "invoice.issuer_name",
                                "operator": "not_equals",
                                "reference_field": "lc.beneficiary_name",
                                "type": "field_match",
                            },
                            {
                                "field": "lc.is_transferred",
                                "operator": "equals",
                                "value": False,
                                "type": "field_match",
                            },
                        ],
                        "expected_outcome": {
                            "valid": ["Presentation complies"],
                            "invalid": ["Commercial invoice not issued by the LC beneficiary."],
                        },
                    }
                ],
                "ruleset_version": "1.0.2",
                "rulebook_version": "UCP600:2007",
            }

    monkeypatch.setattr(rules_service_module, "get_rules_service", lambda: _Ucp18ARulesService())

    async def _fake_inject_semantic_conditions(rules, document_data, evaluator):
        return rules, {}

    monkeypatch.setattr(
        validator_module,
        "_inject_semantic_conditions",
        _fake_inject_semantic_conditions,
    )

    documents = [
        {
            "document_type": "letter_of_credit",
            "extraction_lane": "document_ai",
            "raw_text": "IRREVOCABLE DOCUMENTARY CREDIT\nField 59: Beneficiary: Bangladesh Export Ltd",
            "fact_graph_v1": {
                "version": "fact_graph_v1",
                "document_type": "letter_of_credit",
                "facts": [
                    {"field_name": "beneficiary", "normalized_value": "Bangladesh Export Ltd", "verification_state": "confirmed"},
                    {"field_name": "applicant", "normalized_value": "Global Trade Corp", "verification_state": "confirmed"},
                    {"field_name": "currency", "normalized_value": "USD", "verification_state": "confirmed"},
                ],
            },
            "requirements_graph_v1": {
                "required_document_types": ["commercial_invoice"],
            },
        },
        {
            "document_type": "commercial_invoice",
            "fact_graph_v1": {
                "version": "fact_graph_v1",
                "document_type": "commercial_invoice",
                "facts": [
                    {"field_name": "seller", "normalized_value": "Eastern Apparel Sourcing Ltd", "verification_state": "confirmed"},
                    {"field_name": "buyer", "normalized_value": "Global Trade Corp", "verification_state": "confirmed"},
                    {"field_name": "currency", "normalized_value": "USD", "verification_state": "confirmed"},
                ],
            },
        },
    ]
    payload = {
        "domain": "icc.ucp600",
        "jurisdiction": "global",
        "documents": documents,
        "lc": {"lc_type": "IRREVOCABLE"},
    }
    extracted_context = {
        "documents": documents,
        "lc": {"lc_type": "IRREVOCABLE"},
    }

    apply_lc_fact_graph_to_validation_inputs(payload, extracted_context)
    apply_invoice_fact_graph_to_validation_inputs(payload, extracted_context)

    results = await validator_module.validate_document_async(
        payload,
        document_type="commercial_invoice",
    )

    rule_ids = [result.get("rule") for result in results]
    assert rule_ids == ["UCP600-18A"]


@pytest.mark.asyncio
async def test_validate_document_async_staged_ucp18b_shape_uses_projected_buyer_aliases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Ucp18BRulesService:
        async def get_active_ruleset(
            self,
            domain: str,
            jurisdiction: str = "global",
            document_type: str | None = None,
        ) -> dict[str, object] | None:
            if domain != "icc.ucp600":
                return {"rules": [], "ruleset_version": "1.0.2", "rulebook_version": domain}
            return {
                "rules": [
                    {
                        "rule_id": "UCP600-18",
                        "domain": "lc_ops",
                        "jurisdiction": "global",
                        "document_type": "invoice",
                        "severity": "fail",
                        "deterministic": True,
                        "requires_llm": False,
                        "rule_type": "umbrella",
                        "consequence_class": "domain_logic",
                        "conditions": [
                            {
                                "field": "invoice.buyer_name",
                                "operator": "not_equals",
                                "reference_field": "lc.applicant_name",
                                "type": "field_match",
                            }
                        ],
                    },
                    {
                        "rule_id": "UCP600-18B",
                        "domain": "lc_ops",
                        "jurisdiction": "global",
                        "document_type": "invoice",
                        "severity": "fail",
                        "deterministic": True,
                        "requires_llm": False,
                        "rule_type": "letter",
                        "consequence_class": "invoice_discrepancy",
                        "conditions": [
                            {
                                "field": "invoice.buyer_name",
                                "operator": "not_equals",
                                "reference_field": "lc.applicant_name",
                                "type": "field_match",
                            }
                        ],
                    },
                ],
                "ruleset_version": "1.0.2",
                "rulebook_version": "UCP600:2007",
            }

    monkeypatch.setattr(rules_service_module, "get_rules_service", lambda: _Ucp18BRulesService())

    async def _fake_inject_semantic_conditions(rules, document_data, evaluator):
        return rules, {}

    monkeypatch.setattr(
        validator_module,
        "_inject_semantic_conditions",
        _fake_inject_semantic_conditions,
    )

    documents = [
        {
            "document_type": "letter_of_credit",
            "fact_graph_v1": {
                "version": "fact_graph_v1",
                "document_type": "letter_of_credit",
                "facts": [
                    {
                        "field_name": "beneficiary",
                        "normalized_value": "Bangladesh Export Ltd",
                        "verification_state": "confirmed",
                    },
                    {
                        "field_name": "applicant",
                        "normalized_value": "Global Trade Corp",
                        "verification_state": "confirmed",
                    },
                ],
            },
            "requirements_graph_v1": {
                "required_document_types": ["commercial_invoice"],
            },
        },
        {
            "document_type": "commercial_invoice",
            "fact_graph_v1": {
                "version": "fact_graph_v1",
                "document_type": "commercial_invoice",
                "facts": [
                    {
                        "field_name": "seller",
                        "normalized_value": "Bangladesh Export Ltd",
                        "verification_state": "confirmed",
                    },
                    {
                        "field_name": "buyer",
                        "normalized_value": "Atlantic Retail Holdings",
                        "verification_state": "confirmed",
                    },
                    {
                        "field_name": "currency",
                        "normalized_value": "USD",
                        "verification_state": "confirmed",
                    },
                ],
            },
        },
    ]
    payload = {
        "domain": "icc.ucp600",
        "jurisdiction": "global",
        "documents": documents,
        "lc": {"lc_type": "IRREVOCABLE"},
    }
    extracted_context = {
        "documents": documents,
        "lc": {"lc_type": "IRREVOCABLE"},
    }

    apply_lc_fact_graph_to_validation_inputs(payload, extracted_context)
    apply_invoice_fact_graph_to_validation_inputs(payload, extracted_context)

    results = await validator_module.validate_document_async(
        payload,
        document_type="commercial_invoice",
    )

    assert [result.get("rule") for result in results] == ["UCP600-18B"]
    assert results[0].get("overlap_keys") == ["invoice.applicant|lc.applicant"]


@pytest.mark.asyncio
async def test_validate_document_async_staged_ucp18d_shape_uses_boolean_overlap_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Ucp18DRulesService:
        async def get_active_ruleset(
            self,
            domain: str,
            jurisdiction: str = "global",
            document_type: str | None = None,
        ) -> dict[str, object] | None:
            if domain != "icc.ucp600":
                return {"rules": [], "ruleset_version": "1.0.2", "rulebook_version": domain}
            return {
                "rules": [
                    {
                        "rule_id": "UCP600-18",
                        "domain": "lc_ops",
                        "jurisdiction": "global",
                        "document_type": "invoice",
                        "severity": "fail",
                        "deterministic": True,
                        "requires_llm": False,
                        "rule_type": "umbrella",
                        "consequence_class": "domain_logic",
                        "conditions": [
                            {
                                "field": "invoice.goods_description_matches_lc",
                                "operator": "equals",
                                "value": False,
                                "type": "field_match",
                            }
                        ],
                    },
                    {
                        "rule_id": "UCP600-18D",
                        "domain": "lc_ops",
                        "jurisdiction": "global",
                        "document_type": "invoice",
                        "severity": "fail",
                        "deterministic": True,
                        "requires_llm": False,
                        "rule_type": "letter",
                        "consequence_class": "invoice_discrepancy",
                        "parent_rule": "UCP600-18",
                        "conditions": [
                            {
                                "field": "invoice.goods_description_matches_lc",
                                "operator": "equals",
                                "value": False,
                                "type": "field_match",
                            }
                        ],
                        "expected_outcome": {
                            "valid": ["Presentation complies"],
                            "invalid": ["Commercial invoice goods description does not correspond with LC goods description."],
                        },
                    },
                ],
                "ruleset_version": "1.0.2",
                "rulebook_version": "UCP600:2007",
            }

    monkeypatch.setattr(rules_service_module, "get_rules_service", lambda: _Ucp18DRulesService())

    async def _fake_inject_semantic_conditions(rules, document_data, evaluator):
        return rules, {}

    monkeypatch.setattr(
        validator_module,
        "_inject_semantic_conditions",
        _fake_inject_semantic_conditions,
    )

    results = await validator_module.validate_document_async(
        {
            "domain": "icc.ucp600",
            "jurisdiction": "global",
            "invoice": {
                "goods_description": "100% Polyester T-Shirts, HS Code 6109.90",
                "goods_description_matches_lc": False,
            },
            "credit": {"goods_description": "100% Cotton T-Shirts, HS Code 6109.10"},
        },
        document_type="commercial_invoice",
    )

    assert [result.get("rule") for result in results] == ["UCP600-18D"]
    assert results[0].get("overlap_keys") == ["invoice.goods_description|lc.goods_description"]


def test_extract_rule_overlap_keys_canonicalizes_ucp20c_late_shipment_paths() -> None:
    rule = {
        "rule_id": "UCP600-20C",
        "document_type": "transport",
        "conditions": [
            {
                "field": "bill_of_lading.on_board_date",
                "operator": "greater_than",
                "reference_field": "lc.latest_shipment_date",
                "type": "date_comparison",
            }
        ],
    }

    assert validator_module._extract_rule_overlap_keys(rule) == [
        "bill_of_lading.on_board_date|lc.latest_shipment_date"
    ]
