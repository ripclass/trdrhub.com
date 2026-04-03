from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any, Dict


ROOT = Path(__file__).resolve().parents[1]
VALIDATION_EXECUTION_PATH = ROOT / "app" / "routers" / "validation" / "validation_execution.py"


def _load_symbols() -> Dict[str, Any]:
    source = VALIDATION_EXECUTION_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)
    selected_nodes: list[ast.AST] = []

    for node in parsed.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in {
                    "_ICC_RULEBOOK_PREFIXES",
                    "_ICC_RULE_ID_PATTERN",
                    "_OVERLAP_DOC_ALIASES",
                    "_OVERLAP_FIELD_ALIASES",
                    "_INSURANCE_COVERAGE_SOURCE_FIELDS",
                    "_INSURANCE_COVERAGE_TARGET_FIELDS",
                }:
                    selected_nodes.append(node)
                    break
        elif isinstance(node, ast.FunctionDef) and node.name in {
            "_normalize_overlap_doc_token",
            "_normalize_overlap_field_token",
            "_build_overlap_key",
            "_extract_issue_overlap_keys",
            "_parse_icc_rule_identity",
            "_suppress_broad_icc_umbrella_rules",
            "_suppress_legacy_issue_noise",
        }:
            selected_nodes.append(node)

    module_ast = ast.Module(body=selected_nodes, type_ignores=[])
    ast.fix_missing_locations(module_ast)
    namespace: Dict[str, Any] = {
        "Any": Any,
        "Dict": Dict,
        "List": __import__("typing").List,
        "Optional": __import__("typing").Optional,
        "re": re,
    }
    exec(compile(module_ast, str(VALIDATION_EXECUTION_PATH), "exec"), namespace)
    return namespace


def test_validation_execution_prefers_specific_ucp_letter_rule_over_umbrella_article() -> None:
    fn = _load_symbols()["_suppress_broad_icc_umbrella_rules"]

    filtered = fn(
        [
            {"rule": "UCP600-28", "ruleset_domain": "icc.ucp600", "title": "Insurance Document and Coverage"},
            {"rule": "UCP600-28A", "ruleset_domain": "icc.ucp600", "title": "Insurance Originals Match LC Requirement"},
        ]
    )

    assert [issue["rule"] for issue in filtered] == ["UCP600-28A"]


def test_validation_execution_keeps_umbrella_icc_rule_without_specific_letter_failure() -> None:
    fn = _load_symbols()["_suppress_broad_icc_umbrella_rules"]

    issues = [
        {"rule": "UCP600-28", "ruleset_domain": "icc.ucp600", "title": "Insurance Document and Coverage"},
    ]

    assert fn(issues) == issues


def test_validation_execution_suppresses_fallback_umbrella_when_family_has_specific_rules() -> None:
    fn = _load_symbols()["_suppress_broad_icc_umbrella_rules"]

    filtered = fn(
        [
            {
                "rule": "UCP600-18",
                "ruleset_domain": "icc.ucp600",
                "rule_type": "umbrella",
                "execution_priority": "fallback",
                "consequence_class": "domain_logic",
                "has_specific_family_rules": True,
            },
            {"rule": "UCP600-28A", "ruleset_domain": "icc.ucp600"},
        ]
    )

    assert [issue["rule"] for issue in filtered] == ["UCP600-28A"]


def test_validation_execution_prefers_specific_isbp_letter_rule_over_umbrella_article() -> None:
    fn = _load_symbols()["_suppress_broad_icc_umbrella_rules"]

    filtered = fn(
        [
            {"rule": "ISBP745-A14", "ruleset_domain": "icc.isbp745", "title": "Invoice Requirements"},
            {"rule": "ISBP745-A14B", "ruleset_domain": "icc.isbp745", "title": "Invoice Currency Match"},
        ]
    )

    assert [issue["rule"] for issue in filtered] == ["ISBP745-A14B"]


def test_validation_execution_suppresses_legacy_crossdoc_duplicate_when_specific_ucp_rule_exists() -> None:
    fn = _load_symbols()["_suppress_legacy_issue_noise"]

    filtered = fn(
        [
            {
                "rule": "CROSSDOC-BL-001",
                "ruleset_domain": "icc.lcopilot.crossdoc",
                "source_doc": "bill_of_lading",
                "source_field": "port_of_loading",
                "target_doc": "letter_of_credit",
                "target_field": "port_of_loading",
            },
            {
                "rule": "UCP600-20D",
                "ruleset_domain": "icc.ucp600",
                "overlap_keys": ["bill_of_lading.port_of_loading|lc.port_of_loading"],
            },
        ]
    )

    assert [issue["rule"] for issue in filtered] == ["UCP600-20D"]


def test_validation_execution_suppresses_legacy_late_shipment_duplicate_when_specific_ucp_rule_exists() -> None:
    fn = _load_symbols()["_suppress_legacy_issue_noise"]

    filtered = fn(
        [
            {
                "rule": "CROSSDOC-BL-003",
                "ruleset_domain": "icc.lcopilot.crossdoc",
                "source_doc": "bill_of_lading",
                "source_field": "shipment_date",
                "target_doc": "letter_of_credit",
                "target_field": "latest_shipment",
            },
            {
                "rule": "UCP600-20C",
                "ruleset_domain": "icc.ucp600",
                "overlap_keys": ["bill_of_lading.on_board_date|lc.latest_shipment_date"],
            },
        ]
    )

    assert [issue["rule"] for issue in filtered] == ["UCP600-20C"]


def test_validation_execution_suppresses_legacy_discharge_port_duplicate_when_specific_ucp_rule_exists() -> None:
    fn = _load_symbols()["_suppress_legacy_issue_noise"]

    filtered = fn(
        [
            {
                "rule": "CROSSDOC-BL-002",
                "ruleset_domain": "icc.lcopilot.crossdoc",
                "source_doc": "bill_of_lading",
                "source_field": "port_of_discharge",
                "target_doc": "letter_of_credit",
                "target_field": "port_of_discharge",
            },
            {
                "rule": "UCP600-20E",
                "ruleset_domain": "icc.ucp600",
                "overlap_keys": ["bill_of_lading.port_of_discharge|lc.port_of_discharge"],
            },
        ]
    )

    assert [issue["rule"] for issue in filtered] == ["UCP600-20E"]


def test_validation_execution_suppresses_legacy_invoice_issuer_duplicate_when_specific_ucp_rule_exists() -> None:
    fn = _load_symbols()["_suppress_legacy_issue_noise"]

    filtered = fn(
        [
            {
                "rule": "CROSSDOC-INV-002",
                "ruleset_domain": "icc.lcopilot.crossdoc",
                "source_doc": "commercial_invoice",
                "source_field": "issuer",
                "target_doc": "letter_of_credit",
                "target_field": "beneficiary",
            },
            {
                "rule": "UCP600-18A",
                "ruleset_domain": "icc.ucp600",
                "overlap_keys": ["invoice.issuer|lc.beneficiary"],
            },
        ]
    )

    assert [issue["rule"] for issue in filtered] == ["UCP600-18A"]


def test_validation_execution_suppresses_legacy_invoice_goods_duplicate_when_specific_ucp_rule_exists() -> None:
    fn = _load_symbols()["_suppress_legacy_issue_noise"]

    filtered = fn(
        [
            {
                "rule": "CROSSDOC-INV-003",
                "ruleset_domain": "icc.lcopilot.crossdoc",
                "source_doc": "commercial_invoice",
                "source_field": "goods_description",
                "target_doc": "letter_of_credit",
                "target_field": "goods_description",
            },
            {
                "rule": "UCP600-18D",
                "ruleset_domain": "icc.ucp600",
                "overlap_keys": ["invoice.goods_description|lc.goods_description"],
            },
        ]
    )

    assert [issue["rule"] for issue in filtered] == ["UCP600-18D"]


def test_validation_execution_hides_lc_type_unknown_when_actionable_findings_exist() -> None:
    fn = _load_symbols()["_suppress_legacy_issue_noise"]

    filtered = fn(
        [
            {"rule": "LC-TYPE-UNKNOWN", "ruleset_domain": "system.lc_type"},
            {
                "rule": "UCP600-20D",
                "ruleset_domain": "icc.ucp600",
                "overlap_keys": ["bill_of_lading.port_of_loading|lc.port_of_loading"],
            },
        ]
    )

    assert [issue["rule"] for issue in filtered] == ["UCP600-20D"]


def test_validation_execution_keeps_lc_type_unknown_when_it_is_the_only_signal() -> None:
    fn = _load_symbols()["_suppress_legacy_issue_noise"]

    issues = [{"rule": "LC-TYPE-UNKNOWN", "ruleset_domain": "system.lc_type"}]

    assert fn(issues) == issues


def test_validation_execution_suppresses_legacy_insurance_currency_duplicate_when_specific_ucp_rule_exists() -> None:
    fn = _load_symbols()["_suppress_legacy_issue_noise"]

    filtered = fn(
        [
            {
                "rule": "CROSSDOC-INS-003",
                "ruleset_domain": "icc.lcopilot.crossdoc",
                "source_doc": "insurance_certificate",
                "source_field": "currency",
                "target_doc": "letter_of_credit",
                "target_field": "currency",
            },
            {
                "rule": "UCP600-28D",
                "ruleset_domain": "icc.ucp600",
                "overlap_keys": ["insurance.currency|lc.currency"],
            },
        ]
    )

    assert [issue["rule"] for issue in filtered] == ["UCP600-28D"]


def test_validation_execution_suppresses_legacy_insurance_coverage_duplicate_when_specific_ucp_rule_exists() -> None:
    fn = _load_symbols()["_suppress_legacy_issue_noise"]

    filtered = fn(
        [
            {
                "rule": "CROSSDOC-INSURANCE-1",
                "ruleset_domain": "icc.lcopilot.crossdoc",
                "source_doc": "insurance_certificate",
                "source_field": "insured_amount",
                "target_doc": "letter_of_credit",
                "target_field": "amount",
            },
            {
                "rule": "UCP600-28E",
                "ruleset_domain": "icc.ucp600",
                "overlap_keys": ["insurance.insured_amount|insurance.minimum_required_coverage"],
            },
        ]
    )

    assert [issue["rule"] for issue in filtered] == ["UCP600-28E"]


def test_validation_execution_extracts_exact_wording_overlap_key_from_crossdoc_issue() -> None:
    fn = _load_symbols()["_extract_issue_overlap_keys"]

    overlap_keys = fn(
        {
            "rule": "CROSSDOC-EXACT-WORDING",
            "ruleset_domain": "icc.lcopilot.crossdoc",
            "source_doc": "letter_of_credit",
            "source_field": "Required wording",
            "target_doc": "commercial_invoice",
            "target_field": "Document text",
        }
    )

    assert overlap_keys == ["invoice.exact_wording|lc.exact_wording"]


def test_validation_execution_suppresses_fallback_icc_umbrellas_when_requirement_backed_documentary_issue_exists() -> None:
    fn = _load_symbols()["_suppress_broad_icc_umbrella_rules"]

    filtered = fn(
        [
            {
                "rule": "CROSSDOC-EXACT-WORDING",
                "ruleset_domain": "icc.lcopilot.crossdoc",
                "requirement_source": "requirements_graph_v1",
                "requirement_kind": "document_exact_wording",
                "source_doc": "letter_of_credit",
                "source_field": "Required wording",
                "target_doc": "commercial_invoice",
                "target_field": "Document text",
            },
            {
                "rule": "UCP600-18",
                "ruleset_domain": "icc.ucp600",
                "rule_type": "umbrella",
                "execution_priority": "fallback",
                "consequence_class": "domain_logic",
            },
            {
                "rule": "UCP600-20",
                "ruleset_domain": "icc.ucp600",
                "rule_type": "umbrella",
                "execution_priority": "fallback",
                "consequence_class": "domain_logic",
            },
            {
                "rule": "UCP600-28",
                "ruleset_domain": "icc.ucp600",
                "rule_type": "umbrella",
                "execution_priority": "fallback",
                "consequence_class": "domain_logic",
            },
        ]
    )

    assert [issue["rule"] for issue in filtered] == ["CROSSDOC-EXACT-WORDING"]
