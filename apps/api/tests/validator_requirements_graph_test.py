from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "app" / "services" / "validator.py"
LC_TAXONOMY_PATH = ROOT / "app" / "services" / "extraction" / "lc_taxonomy.py"


def _load_lc_taxonomy_module():
    spec = importlib.util.spec_from_file_location("lc_taxonomy_validator_requirements_test", LC_TAXONOMY_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load lc_taxonomy module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_validator_requirement_symbols() -> Dict[str, Any]:
    source = VALIDATOR_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)
    target_assignments = {
        "DOC_KEYWORDS",
        "DOC_SYNONYMS",
        "FIELD_PREFIX_TO_DOC",
        "NEGOTIABILITY_TAGS",
        "SIGNED_INVOICE_TAGS",
        "INSURANCE_TAGS",
        "REQUIREMENTS_GRAPH_TRANSPORT_TYPES",
        "REQUIREMENTS_GRAPH_INVOICE_TYPES",
        "REQUIREMENTS_GRAPH_INSURANCE_TYPES",
    }
    target_functions = {
        "_get_lc_classification",
        "_normalize_doc_label",
        "_infer_targets_from_rule_metadata",
        "_infer_doc_from_field",
        "_extract_rule_field_paths",
        "_normalize_tags",
        "_text_contains_any",
        "_extract_requested_documents",
        "_fallback_documents_from_payload",
        "_resolve_requirements_graph",
        "_infer_document_requirements",
        "_derive_rule_toggles_from_graph",
        "_derive_rule_toggles",
        "_derive_structured_requirement_context_from_graph",
        "_rule_targets_negotiability",
        "_rule_targets_signed_invoice",
        "_rule_targets_insurance",
        "_rule_targets_documents",
        "_condition_declares_document_types",
        "_rule_requires_notice_context",
        "_has_notice_context",
    }

    selected_nodes: List[ast.AST] = []
    for node in parsed.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in target_assignments:
                    selected_nodes.append(node)
                    break
        if isinstance(node, ast.FunctionDef) and node.name in target_functions:
            selected_nodes.append(node)

    module_ast = ast.Module(body=selected_nodes, type_ignores=[])
    ast.fix_missing_locations(module_ast)
    taxonomy = _load_lc_taxonomy_module()
    namespace: Dict[str, Any] = {
        "Any": Any,
        "Dict": Dict,
        "List": List,
        "Optional": Optional,
        "Set": Set,
        "re": __import__("re"),
        "build_lc_classification": taxonomy.build_lc_classification,
    }
    exec(compile(module_ast, str(VALIDATOR_PATH), "exec"), namespace)
    return namespace


def test_infer_document_requirements_prefers_requirements_graph_v1() -> None:
    ns = _load_validator_requirement_symbols()
    infer_document_requirements = ns["_infer_document_requirements"]
    requirements = infer_document_requirements(
        {"requirements_graph_v1": {"required_document_types": ["commercial_invoice", "air_waybill", "insurance_policy"]}},
        "",
        {},
    )

    assert requirements["lc"] is True
    assert requirements["commercial_invoice"] is True
    assert requirements["bill_of_lading"] is True
    assert requirements["insurance_certificate"] is True
    assert requirements["packing_list"] is False
    assert requirements["certificate_of_origin"] is False


def test_infer_document_requirements_falls_back_when_graph_missing() -> None:
    ns = _load_validator_requirement_symbols()
    infer_document_requirements = ns["_infer_document_requirements"]
    requirements = infer_document_requirements(
        {"documents_required": ["INVOICE/PL/COO"]},
        "invoice packing list certificate of origin",
        {},
    )

    assert requirements["commercial_invoice"] is True
    assert requirements["packing_list"] is True
    assert requirements["certificate_of_origin"] is True
    assert requirements["bill_of_lading"] is False


def test_infer_document_requirements_reads_graph_from_extracted_context_documents() -> None:
    ns = _load_validator_requirement_symbols()
    infer_document_requirements = ns["_infer_document_requirements"]
    requirements = infer_document_requirements(
        {},
        "",
        {
            "extracted_context": {
                "documents": [
                    {
                        "document_type": "letter_of_credit",
                        "requirements_graph_v1": {
                            "required_document_types": ["packing_list", "certificate_of_origin"],
                        },
                    }
                ]
            }
        },
    )

    assert requirements["packing_list"] is True
    assert requirements["certificate_of_origin"] is True
    assert requirements["commercial_invoice"] is False


def test_derive_rule_toggles_prefers_structured_required_document_metadata() -> None:
    ns = _load_validator_requirement_symbols()
    derive_rule_toggles = ns["_derive_rule_toggles"]

    toggles = derive_rule_toggles(
        {},
        "",
        {"insurance_certificate": False},
        {
            "required_documents": [
                {
                    "code": "commercial_invoice",
                    "signed": True,
                    "exact_wording": "SIGNED COMMERCIAL INVOICE IN 1 ORIGINAL",
                },
                {
                    "code": "bill_of_lading",
                    "negotiable": False,
                    "exact_wording": "NON-NEGOTIABLE SEA WAYBILL ACCEPTABLE",
                },
                {
                    "code": "insurance_policy",
                    "exact_wording": "INSURANCE POLICY REQUIRED",
                },
            ]
        },
    )

    assert toggles["signed_invoice_required"] is True
    assert toggles["non_negotiable_allowed"] is True
    assert toggles["insurance_required"] is True


def test_derive_rule_toggles_prefers_structured_exact_wording_requirements() -> None:
    ns = _load_validator_requirement_symbols()
    derive_rule_toggles = ns["_derive_rule_toggles"]

    toggles = derive_rule_toggles(
        {},
        "",
        {"insurance_certificate": False},
        {
            "condition_requirements": [
                {
                    "requirement_type": "document_exact_wording",
                    "document_type": "commercial_invoice",
                    "exact_wording": "SIGNED COMMERCIAL INVOICE",
                },
                {
                    "requirement_type": "document_exact_wording",
                    "document_type": "sea_waybill",
                    "exact_wording": "NON NEGOTIABLE SEA WAYBILL",
                },
            ]
        },
    )

    assert toggles["signed_invoice_required"] is True
    assert toggles["non_negotiable_allowed"] is True


def test_derive_structured_requirement_context_from_graph_compiles_quantities_wording_and_identifiers() -> None:
    ns = _load_validator_requirement_symbols()
    derive_structured = ns["_derive_structured_requirement_context_from_graph"]

    structured = derive_structured(
        {
            "required_documents": [
                {
                    "code": "bill_of_lading",
                    "originals": 3,
                    "copies": 2,
                    "exact_wording": "FULL SET CLEAN ON BOARD OCEAN BILLS OF LADING",
                }
            ],
            "condition_requirements": [
                {
                    "requirement_type": "document_field_presence",
                    "document_type": "bill_of_lading",
                    "field_name": "voyage_number",
                },
                {
                    "requirement_type": "document_exact_wording",
                    "document_type": "sea_waybill",
                    "exact_wording": "NON NEGOTIABLE SEA WAYBILL",
                },
                {
                    "requirement_type": "identifier_presence",
                    "identifier_type": "po_number",
                    "value": "GBE-44592",
                },
            ],
        }
    )

    assert structured["document_quantities"]["bill_of_lading"] == {
        "originals_required": 3,
        "copies_required": 2,
    }
    assert structured["document_exact_wording"]["bill_of_lading"] == [
        "FULL SET CLEAN ON BOARD OCEAN BILLS OF LADING"
    ]
    assert structured["document_exact_wording"]["sea_waybill"] == [
        "NON NEGOTIABLE SEA WAYBILL"
    ]
    assert structured["document_field_presence"]["bill_of_lading"] == ["voyage_number"]
    assert structured["identifier_presence"]["po_number"] == ["GBE-44592"]
    assert structured["toggles"]["non_negotiable_allowed"] is True


def test_derive_rule_toggles_reads_insurance_required_from_required_document_types() -> None:
    ns = _load_validator_requirement_symbols()
    derive_rule_toggles = ns["_derive_rule_toggles"]

    toggles = derive_rule_toggles(
        {},
        "",
        {"insurance_certificate": False},
        {"required_document_types": ["insurance_policy"]},
    )

    assert toggles["insurance_required"] is True


def test_validate_document_async_injects_requirements_structured_context_before_rule_evaluation() -> None:
    source = VALIDATOR_PATH.read_text(encoding="utf-8")

    assert 'document_data = _apply_requirements_graph_to_rule_context(document_data, requirements_graph)' in source
    assert 'lc_context["requirements_structured_v1"] = structured' in source
    assert 'payload["_requirements_structured_v1"] = structured' in source


def test_rule_target_helpers_detect_structured_toggle_paths() -> None:
    ns = _load_validator_requirement_symbols()
    extract_rule_field_paths = ns["_extract_rule_field_paths"]
    rule_targets_negotiability = ns["_rule_targets_negotiability"]
    rule_targets_signed_invoice = ns["_rule_targets_signed_invoice"]
    rule_targets_insurance = ns["_rule_targets_insurance"]

    negotiability_rule = {
        "applies_if": [
            {
                "field": "lc.requirements_structured_v1.toggles.non_negotiable_allowed",
                "operator": "equals",
                "value": True,
            }
        ],
        "conditions": [
            {"field": "sea_waybill.signature_party", "operator": "equals", "value": "carrier"}
        ]
    }
    signed_invoice_rule = {
        "conditions": [
            {"field": "_requirements_structured_v1.toggles.signed_invoice_required", "operator": "equals", "value": True}
        ]
    }
    insurance_rule = {
        "applies_if": [
            {
                "field": "lc.requirements_structured_v1.toggles.insurance_required",
                "operator": "equals",
                "value": True,
            }
        ],
        "conditions": [{"field": "insurance_doc.originals_presented", "operator": "exists"}],
    }

    assert "lc.requirements_structured_v1.toggles.non_negotiable_allowed" in extract_rule_field_paths(
        negotiability_rule
    )
    assert "lc.requirements_structured_v1.toggles.insurance_required" in extract_rule_field_paths(
        insurance_rule
    )
    assert rule_targets_negotiability(negotiability_rule) is True
    assert rule_targets_signed_invoice(signed_invoice_rule) is True
    assert rule_targets_insurance(insurance_rule) is True


def test_rule_targets_documents_infers_doc_from_structured_requirement_paths() -> None:
    ns = _load_validator_requirement_symbols()
    rule_targets_documents = ns["_rule_targets_documents"]

    rule = {
        "conditions": [
            {
                "field": "lc.requirements_structured_v1.document_quantities.bill_of_lading.originals_required",
                "operator": "greater_than_or_equal",
                "value": 3,
            },
            {
                "field": "_requirements_structured_v1.document_exact_wording.sea_waybill.0",
                "operator": "contains",
                "value": "NON NEGOTIABLE",
            },
        ]
    }

    assert rule_targets_documents(rule) == {"bill_of_lading"}


def test_rule_targets_documents_infers_insurance_from_structured_quantity_path() -> None:
    ns = _load_validator_requirement_symbols()
    rule_targets_documents = ns["_rule_targets_documents"]

    rule = {
        "conditions": [
            {
                "field": "insurance_doc.originals_presented",
                "operator": "greater_than_or_equal",
                "value_ref": "lc.requirements_structured_v1.document_quantities.insurance_certificate.originals_required",
            }
        ]
    }

    assert rule_targets_documents(rule) == {"insurance_certificate"}
