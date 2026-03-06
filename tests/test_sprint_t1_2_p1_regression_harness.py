from __future__ import annotations

import ast
import importlib.util
import json
import re
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple

from app.core.lc_types import LCType, VALID_LC_TYPES, normalize_lc_type
from app.services.validation.ai_validator import validate_bl_fields, validate_packing_list
from app.services.validation.crossdoc_validator import CrossDocValidator
from app.routers.validation.response_shaping import build_issue_provenance_v1


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "sprint_t1_2_p1"
VALIDATE_PATH = ROOT / "apps" / "api" / "app" / "routers" / "validate.py"
STRUCTURED_BUILDER_PATH = (
    ROOT / "apps" / "api" / "app" / "services" / "extraction" / "structured_lc_builder.py"
)


def _load_fixture(name: str) -> Dict[str, Any]:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def _load_module_from_path(module_name: str, module_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec and spec.loader, f"Unable to load module from {module_path}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_validate_functions(
    function_names: List[str],
    extra_globals: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    source = VALIDATE_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)

    selected: List[ast.FunctionDef] = []
    seen = set()
    for node in parsed.body:
        if isinstance(node, ast.FunctionDef) and node.name in function_names:
            selected.append(node)
            seen.add(node.name)

    missing = sorted(set(function_names) - seen)
    assert not missing, f"Missing function(s) in validate.py: {missing}"

    module_ast = ast.Module(body=selected, type_ignores=[])
    ast.fix_missing_locations(module_ast)

    namespace: Dict[str, Any] = {
        "Any": Any,
        "Dict": Dict,
        "List": List,
        "Optional": Optional,
        "Tuple": Tuple,
        "canonical_field_key": lambda key: key,
    }
    if extra_globals:
        namespace.update(extra_globals)

    exec(compile(module_ast, str(VALIDATE_PATH), "exec"), namespace)
    return {name: namespace[name] for name in function_names}


@dataclass
class _FakeStatus:
    value: str


@dataclass
class _FakeFieldResult:
    normalized_value: Any
    status: _FakeStatus
    ai_confidence: float
    validation_score: float
    final_confidence: float
    issues: List[str]


class _FakeTwoStageExtractor:
    def __init__(self, validated_fields: Dict[str, _FakeFieldResult], summary: Dict[str, Any]):
        self.validated_fields = validated_fields
        self.summary = summary
        self.last_ai_extraction: Optional[Dict[str, Any]] = None
        self.last_document_type: Optional[str] = None

    def process(self, ai_extraction: Dict[str, Any], document_type: str):
        self.last_ai_extraction = ai_extraction
        self.last_document_type = document_type
        return self.validated_fields

    def get_extraction_summary(self, _validated: Dict[str, _FakeFieldResult]):
        return self.summary


def test_partial_extraction_path_raw_text_only_and_partial_statuses():
    fixture = _load_fixture("partial_extraction_path.json")
    builder = _load_module_from_path("structured_builder_partial", STRUCTURED_BUILDER_PATH)

    structured = builder.build_unified_structured_result(
        session_documents=fixture["session_documents"],
        extractor_outputs=fixture["extractor_outputs"],
        legacy_payload=None,
    )["structured_result"]

    docs = structured["documents_structured"]
    assert [doc["extraction_status"] for doc in docs] == ["partial", "text_only"]
    assert structured["lc_structured"]["mt700"]["raw_text"] == fixture["extractor_outputs"]["mt700"]["raw_text"]


def test_two_stage_validation_summary_keeps_review_counters_for_unverified_flow():
    fixture = _load_fixture("two_stage_review_counter.json")

    validated_fields = {
        "number": _FakeFieldResult(
            normalized_value=fixture["normalized_values"]["number"],
            status=_FakeStatus("trusted"),
            ai_confidence=0.95,
            validation_score=1.0,
            final_confidence=0.95,
            issues=[],
        ),
        "amount": _FakeFieldResult(
            normalized_value=fixture["normalized_values"]["amount"],
            status=_FakeStatus("review"),
            ai_confidence=0.82,
            validation_score=0.6,
            final_confidence=0.71,
            issues=["manual_review_recommended"],
        ),
    }
    extractor = _FakeTwoStageExtractor(validated_fields, fixture["summary"])

    funcs = _load_validate_functions(
        ["_apply_two_stage_validation"],
        extra_globals={
            "_get_two_stage_extractor": lambda: extractor,
            "logger": SimpleNamespace(
                info=lambda *args, **kwargs: None,
                warning=lambda *args, **kwargs: None,
            ),
        },
    )
    apply_two_stage = funcs["_apply_two_stage_validation"]

    validated, summary = apply_two_stage(fixture["input_fields"], "lc", "LC_scan.pdf")

    assert extractor.last_ai_extraction is not None
    assert "raw_text" not in extractor.last_ai_extraction
    assert summary == fixture["summary"]
    assert validated["_two_stage_validation"]["summary"]["review"] == fixture["summary"]["review"]
    assert validated["raw_text"] == fixture["input_fields"]["raw_text"]


def test_issue_cards_present_in_structured_result_when_failures_exist():
    fixture = _load_fixture("issue_cards_failures.json")
    builder = _load_module_from_path("structured_builder_issues", STRUCTURED_BUILDER_PATH)

    structured = builder.build_unified_structured_result(
        session_documents=fixture["session_documents"],
        extractor_outputs=fixture["extractor_outputs"],
        legacy_payload=None,
    )["structured_result"]

    issues = structured["issues"]
    assert len(issues) == 2
    assert {issue["id"] for issue in issues} == {"RULE-41A", "RULE-44C"}
    assert all(issue.get("documents") for issue in issues)


def test_documents_structured_preserves_discrepancy_and_ocr_fields():
    fixture = {
        "session_documents": [
            {
                "id": "doc-1",
                "document_type": "commercial_invoice",
                "filename": "Invoice.pdf",
                "extraction_status": "success",
                "extracted_fields": {"amount": "1000"},
                "extractedFields": {"amount": "1000", "currency": "USD"},
                "discrepancyCount": 2,
                "issues_count": 2,
                "ocrConfidence": 0.91,
                "extraction_artifacts_v1": {
                    "version": "extraction_artifacts_v1",
                    "raw_text": "Invoice content",
                    "tables": [[{"text": "Amount", "row": 1, "col": 1}, {"text": "1000", "row": 1, "col": 2}]],
                    "key_value_candidates": [{"key": "Invoice No", "value": "INV-123"}],
                    "spans": [{"text": "INV-123", "confidence": 0.93, "element_type": "word"}],
                    "bbox": [{"x1": 10, "y1": 20, "x2": 40, "y2": 30, "page": 1}],
                    "ocr_confidence": 0.91,
                },
            },
            {
                "id": "doc-2",
                "documentType": "bill_of_lading",
                "name": "BL.pdf",
                "extractionStatus": "partial",
                "extractedFields": {"bl_no": "BL123"},
                "issuesCount": 1,
                "ocr_confidence": 0.75,
            },
        ],
        "extractor_outputs": {
            "mt700": {"blocks": {}, "raw_text": None, "version": "mt700_v1"},
            "issues": [],
        },
    }
    builder = _load_module_from_path("structured_builder_docs", STRUCTURED_BUILDER_PATH)

    structured = builder.build_unified_structured_result(
        session_documents=fixture["session_documents"],
        extractor_outputs=fixture["extractor_outputs"],
        legacy_payload=None,
    )["structured_result"]

    docs = structured["documents_structured"]
    assert docs[0]["discrepancyCount"] == 2
    assert docs[0]["issues_count"] == 2
    assert docs[0]["ocrConfidence"] == 0.91
    assert docs[0]["extracted_fields"]["amount"] == "1000"
    assert docs[0]["extractedFields"]["currency"] == "USD"
    assert docs[0]["extraction_artifacts_v1"]["raw_text"] == "Invoice content"
    assert isinstance(docs[0]["extraction_artifacts_v1"]["tables"], list)
    assert isinstance(docs[0]["extraction_artifacts_v1"]["key_value_candidates"], list)
    assert isinstance(docs[0]["extraction_artifacts_v1"]["spans"], list)
    assert isinstance(docs[0]["extraction_artifacts_v1"]["bbox"], list)
    assert docs[0]["extraction_artifacts_v1"]["ocr_confidence"] == 0.91

    assert docs[1]["issues_count"] == 1
    assert docs[1]["ocrConfidence"] == 0.75
    assert docs[1]["extracted_fields"]["bl_no"] == "BL123"
    assert docs[1]["extractedFields"]["bl_no"] == "BL123"
    # fallback/default artifact shape remains present for backward-compatible callers
    assert docs[1]["extraction_artifacts_v1"]["version"] == "extraction_artifacts_v1"
    assert docs[1]["extraction_artifacts_v1"]["raw_text"] == ""
    assert docs[1]["extraction_artifacts_v1"]["ocr_confidence"] == 0.75


def test_lc_type_override_handling_and_source_markers():
    fixture = _load_fixture("lc_override_source_markers.json")

    funcs = _load_validate_functions(
        ["_extract_lc_type_override"],
        extra_globals={
            "LCType": LCType,
            "VALID_LC_TYPES": VALID_LC_TYPES,
            "normalize_lc_type": normalize_lc_type,
        },
    )
    extract_override = funcs["_extract_lc_type_override"]

    for case in fixture["override_cases"]:
        assert extract_override(case["payload"]) == case["expected"]

    builder = _load_module_from_path("structured_builder_override", STRUCTURED_BUILDER_PATH)
    structured = builder.build_unified_structured_result(
        session_documents=fixture["session_documents"],
        extractor_outputs=fixture["extractor_outputs"],
        legacy_payload=None,
    )["structured_result"]

    assert structured["lc_type"] == "import"
    assert structured["lc_type_source"] == "override"
    assert abs(structured["lc_type_confidence"] - 0.88) < 1e-9


def test_document_composition_analytics_presence_and_consistency_markers():
    fixture = _load_fixture("document_composition_source_markers.json")
    source = VALIDATE_PATH.read_text(encoding="utf-8")

    for fragment in fixture["required_fragments"]:
        assert fragment in source

    assert re.search(
        r'structured_result\["analytics"\]\["document_composition"\]\s*=\s*composition_result\.get\("composition",\s*\{\}\)',
        source,
    )
    assert re.search(
        r'structured_result\["analytics"\]\["lc_only_mode"\]\s*=\s*composition_result\.get\("composition",\s*\{\}\)\.get\("lc_only_mode",\s*False\)',
        source,
    )


def test_issue_provenance_uses_raw_issue_source_and_keeps_doc_refs():
    source = VALIDATE_PATH.read_text(encoding="utf-8")
    assert "issue_provenance_input" in source
    assert "deduplicated_results" in source

    provenance = build_issue_provenance_v1(
        [
            {
                "rule": "CROSSDOC-1",
                "severity": "major",
                "document_ids": ["doc-1"],
                "document_types": ["commercial_invoice"],
                "documents": ["Invoice.pdf"],
            },
            {
                "id": "card-1",
                "severity": "minor",
                "documentName": "Bill of Lading",
            },
        ]
    )

    assert provenance["total_issues"] == 2
    assert provenance["issues"][0]["document_ids"] == ["doc-1"]
    assert provenance["issues"][1]["document_names"] == ["Bill of Lading"]


def test_bl_alias_fields_match_required_must_show():
    fixture = _load_fixture("phase_b1_alias_extraction.json")

    issues = validate_bl_fields(
        required_fields=fixture["bl_required_fields"],
        bl_data=fixture["bl_data"],
    )

    assert issues == []


def test_bl_raw_text_fallback_recovers_required_fields():
    bl_data = {
        "raw_text": "BILL OF LADING\nVSL/VOY: EVER GLORY 123E\nGROSS WEIGHT: 20,400 KGS\nNET WT 18,950 KGS",
    }

    issues = validate_bl_fields(
        required_fields=["voyage_number", "gross_weight", "net_weight"],
        bl_data=bl_data,
    )

    assert issues == []


def test_bl_raw_text_fallback_recovers_gross_net_combined_line():
    bl_data = {
        "raw_text": "BILL OF LADING\nVESSEL/VOY: OCEAN STAR / 119E\nGROSS/NET WEIGHT: 20,400 / 18,950 KGS",
    }

    issues = validate_bl_fields(
        required_fields=["voyage_number", "gross_weight", "net_weight"],
        bl_data=bl_data,
    )

    assert issues == []


def test_bl_raw_text_fallback_recovers_vessel_and_voyage_ampersand_plus_gross_wt_net_wt():
    fixture = _load_fixture("phase_b1_bl_variant_exp2026bd001.json")

    issues = validate_bl_fields(
        required_fields=fixture["bl_required_fields"],
        bl_data=fixture["bl_data"],
    )

    assert issues == []


def test_bl_alias_variants_cover_vessel_voy_and_weight_shortcuts():
    issues = validate_bl_fields(
        required_fields=["voyage_number", "gross_weight", "net_weight"],
        bl_data={
            "vessel_voy": "VSL-77A",
            "g.w.": "1,200 KGS",
            "n.w.": "1,150 KGS",
        },
    )

    assert issues == []


def test_bl_alias_variants_cover_vessel_voyage_and_gross_net_combo():
    issues = validate_bl_fields(
        required_fields=["voyage_number", "gross_weight", "net_weight"],
        bl_data={
            "vessel/voyage": "CALISTA/991E",
            "gross/net_weight": "1200/1100 KGS",
        },
    )

    assert issues == []


def test_bl_raw_text_fallback_accepts_vvd_label_variant():
    issues = validate_bl_fields(
        required_fields=["voyage_number", "gross_weight", "net_weight"],
        bl_data={
            "raw_text": "BILL OF LADING\nVVD NO: 778W\nGROSS WEIGHT: 20,400 KGS\nNET WEIGHT: 18,950 KGS",
        },
    )

    assert issues == []


def test_bl_targeted_candidates_from_ocr_spans_recover_header_zone_combined_lines():
    issues = validate_bl_fields(
        required_fields=["voyage_number", "gross_weight", "net_weight"],
        bl_data={
            "raw_text": "BILL OF LADING\n...",
            "extraction_artifacts_v1": {
                "spans": [
                    {"text": "VESSEL/VOY: MSC MAEVA / 778W", "bbox": {"page": 1, "x1": 80, "y1": 95}},
                    {"text": "GROSS/NET WEIGHT: 20,400 / 18,950 KGS", "bbox": {"page": 1, "x1": 82, "y1": 120}},
                ]
            },
        },
    )

    assert issues == []


def test_bl_targeted_candidates_handle_label_value_split_across_neighbor_spans():
    issues = validate_bl_fields(
        required_fields=["voyage_number", "gross_weight", "net_weight"],
        bl_data={
            "raw_text": "BILL OF LADING",
            "extraction_artifacts_v1": {
                "spans": [
                    {"text": "VSL/VOY", "bbox": {"page": 1, "x1": 70, "y1": 88}},
                    {"text": "EVER GLORY / 123E", "bbox": {"page": 1, "x1": 125, "y1": 88}},
                    {"text": "GROSS/NET WT", "bbox": {"page": 1, "x1": 70, "y1": 108}},
                    {"text": "20,400/18,950 KGS", "bbox": {"page": 1, "x1": 124, "y1": 108}},
                ]
            },
        },
    )

    assert issues == []


def test_bl_targeted_candidates_reject_non_numeric_gross_net_pair():
    issues = validate_bl_fields(
        required_fields=["voyage_number", "gross_weight", "net_weight"],
        bl_data={
            "raw_text": "BILL OF LADING\nVSL/VOY: MSC MAEVA / 778W",
            "extraction_artifacts_v1": {
                "spans": [
                    {"text": "GROSS/NET WEIGHT: HEAVY / LIGHT", "bbox": {"page": 1, "x1": 80, "y1": 120}},
                ]
            },
        },
    )

    issue_ids = {issue.rule_id for issue in issues}
    assert "AI-BL-MISSING-GROSS_WEIGHT" in issue_ids
    assert "AI-BL-MISSING-NET_WEIGHT" in issue_ids


def test_ai_first_bl_canonical_filter_splits_combined_alias_values():
    from app.services.extraction.ai_first_extractor import BLAIFirstExtractor

    extractor = BLAIFirstExtractor()
    filtered = extractor._filter_canonical_ai_result(
        {
            "vessel&voyage": "MSC MAEVA/778W",
            "gross/net_weight": "20,400/18,950 KGS",
        },
        "bill_of_lading",
    )

    assert filtered["vessel_name"] == "MSC MAEVA"
    assert filtered["voyage_number"] == "778W"
    assert filtered["gross_weight"] == "20,400"
    assert filtered["net_weight"] == "18,950 KGS"


def test_build_issue_context_projects_bl_fields_from_extracted_fields_map():
    funcs = _load_validate_functions(["_build_issue_context"])
    build_issue_context = funcs["_build_issue_context"]

    context = build_issue_context(
        {
            "bill_of_lading": {
                "extracted_fields": {
                    "voyage_number": "778W",
                    "gross_weight": "20,400 KGS",
                    "net_weight": "18,950 KGS",
                }
            }
        }
    )

    assert context["bill_of_lading"]["voyage_number"] == "778W"
    assert context["bill_of_lading"]["gross_weight"] == "20,400 KGS"
    assert context["bill_of_lading"]["net_weight"] == "18,950 KGS"


def test_build_issue_context_prefers_top_level_bl_fields_after_projection():
    funcs = _load_validate_functions(["_build_issue_context"])
    build_issue_context = funcs["_build_issue_context"]

    context = build_issue_context(
        {
            "bill_of_lading": {
                "voyage_number": "991E",
                "gross_weight": "1,200 KGS",
                "net_weight": "1,100 KGS",
                "extracted_fields": {},
            }
        }
    )

    assert context["bill_of_lading"]["voyage_number"] == "991E"
    assert context["bill_of_lading"]["gross_weight"] == "1,200 KGS"
    assert context["bill_of_lading"]["net_weight"] == "1,100 KGS"


def test_fields_to_flat_context_preserves_reason_metadata():
    funcs = _load_validate_functions(["_fields_to_flat_context"])
    to_context = funcs["_fields_to_flat_context"]

    fields = [
        SimpleNamespace(
            field_name="voyage_number",
            value=None,
            reason="missing_in_source",
            confidence=0.4,
            raw_text=None,
        ),
        SimpleNamespace(
            field_name="gross_weight",
            value="20,400 KGS",
            reason="parser_failed",
            confidence=0.6,
            raw_text="GROSS WEIGHT: 20,400 KGS",
        ),
    ]

    context = to_context(fields)

    assert context["gross_weight"] == "20,400 KGS"
    assert context["_field_details"]["voyage_number"]["reason"] == "missing_in_source"
    assert context["_field_details"]["gross_weight"]["reason"] == "parser_failed"
    assert "confidence" in context["_field_details"]["gross_weight"]


def test_packing_list_table_text_counts_as_size_breakdown():
    fixture = _load_fixture("phase_b1_alias_extraction.json")

    issues = validate_packing_list(
        lc_text=fixture["lc_text"],
        packing_list_data=fixture["packing_list"],
    )

    assert issues == []


def test_packing_list_carton_size_counts_as_size_info():
    lc_text = "PACKING LIST MUST SHOW SIZE BREAKDOWN PER LC CLAUSE 46A."
    issues = validate_packing_list(
        lc_text=lc_text,
        packing_list_data={
            "raw_text": "PACKING LIST\nCARTON SIZE: 50 X 40 X 30 CM",
        },
    )

    assert issues == []


def test_packing_list_prepack_ratio_pack_counts_as_size_info():
    lc_text = "PACKING LIST MUST SHOW SIZE BREAKDOWN PER LC CLAUSE 46A."
    issues = validate_packing_list(
        lc_text=lc_text,
        packing_list_data={
            "raw_text": "PACKING LIST\nPRE-PACK: S-10 M-20 L-30\nRATIO PACK 1:2:3",
        },
    )

    assert issues == []


def test_47a_bin_tin_variants_extract_and_require_all_docs():
    fixture = _load_fixture("phase_b1_alias_extraction.json")
    validator = CrossDocValidator()

    requirements = validator._parse_47a_requirements(
        {"additional_conditions": fixture["conditions_text"]}
    )

    assert requirements["bin_number"] == fixture["expected_bin"]
    assert requirements["tin_number"] == fixture["expected_tin"]
    assert requirements["all_docs_require_bin"] is True
    assert requirements["all_docs_require_tin"] is True


def test_47a_bin_tin_accepts_dot_variants_and_tax_id_labels():
    validator = CrossDocValidator()
    requirements = validator._parse_47a_requirements(
        {
            "additional_conditions": (
                "EXPORTER B.I.N. NO. 998877-0101 MUST APPEAR ON ALL DOCUMENTS. "
                "TAX ID# 556677889900 MUST APPEAR ON ALL DOCUMENTS."
            )
        }
    )

    assert requirements["bin_number"] == "998877-0101"
    assert requirements["tin_number"] == "556677889900"
    assert requirements["all_docs_require_bin"] is True
    assert requirements["all_docs_require_tin"] is True


def test_47a_bin_tin_accepts_vat_tax_reg_taxpayer_etin_labels():
    validator = CrossDocValidator()
    requirements = validator._parse_47a_requirements(
        {
            "additional_conditions": (
                "VAT REG NO. 445566-0102 MUST APPEAR ON ALL DOCUMENTS. "
                "TAX REG NO. 9988776655 MUST APPEAR ON ALL DOCUMENTS."
            )
        }
    )

    assert requirements["bin_number"] == "445566-0102"
    assert requirements["tin_number"] == "9988776655"
    assert requirements["all_docs_require_bin"] is True
    assert requirements["all_docs_require_tin"] is True


def test_47a_bin_tin_accepts_vat_no_taxpayer_id_and_etin_labels():
    validator = CrossDocValidator()
    requirements = validator._parse_47a_requirements(
        {
            "additional_conditions": (
                "VAT NO. 112233-0099 MUST APPEAR ON ALL DOCUMENTS. "
                "TAXPAYER ID NO. 556677889900 / ETIN 556677889900 MUST APPEAR ON ALL DOCUMENTS."
            )
        }
    )

    assert requirements["bin_number"] == "112233-0099"
    assert requirements["tin_number"] == "556677889900"
    assert requirements["all_docs_require_bin"] is True
    assert requirements["all_docs_require_tin"] is True


def test_47a_bin_tin_accepts_vat_registration_number_and_e_tin_no_labels():
    validator = CrossDocValidator()
    requirements = validator._parse_47a_requirements(
        {
            "additional_conditions": (
                "EXPORTER VAT REGISTRATION NUMBER 443322-1100 MUST APPEAR ON ALL DOCUMENTS. "
                "E-TIN NO. 889900112233 MUST APPEAR ON ALL DOCUMENTS."
            )
        }
    )

    assert requirements["bin_number"] == "443322-1100"
    assert requirements["tin_number"] == "889900112233"
    assert requirements["all_docs_require_bin"] is True
    assert requirements["all_docs_require_tin"] is True


def test_bin_tin_doc_level_detection_across_invoice_packing_bl_coo():
    validator = CrossDocValidator()
    docs = {
        "invoice": {
            "raw_text": "COMMERCIAL INVOICE\nVAT REG NO. 112233-0099\nTAXPAYER ID NO. 556677889900",
            "exporter_bin": "112233-0099",
            "exporter_tin": "556677889900",
        },
        "packing_list": {
            "raw_text": "PACKING LIST\nVAT NO. 112233-0099\nE-TIN NO. 556677889900",
            "vat_no": "112233-0099",
            "etin": "556677889900",
        },
        "bill_of_lading": {
            "raw_text": "BILL OF LADING\nBUSINESS IDENTIFICATION NO. 112233-0099\nTAX REG NO. 556677889900",
            "business_identification_no": "112233-0099",
            "tax_reg_no": "556677889900",
        },
        "certificate_of_origin": {
            "raw_text": "CERTIFICATE OF ORIGIN\nVAT REGISTRATION NUMBER: 112233-0099\nETIN: 556677889900",
            "vat_registration_number": "112233-0099",
            "etin": "556677889900",
        },
    }

    bin_issues, bin_executed, bin_passed = validator._validate_bin_all_docs("112233-0099", docs, {})
    tin_issues, tin_executed, tin_passed = validator._validate_tin_all_docs("556677889900", docs, {})

    assert bin_issues == []
    assert tin_issues == []
    assert (bin_executed, bin_passed) == (4, 4)
    assert (tin_executed, tin_passed) == (4, 4)


def test_bin_tin_doc_level_missing_reports_target_docs():
    validator = CrossDocValidator()
    docs = {
        "invoice": {"exporter_bin": "112233-0099", "exporter_tin": "556677889900"},
        "packing_list": {"exporter_bin": "112233-0099", "exporter_tin": "556677889900"},
        "bill_of_lading": {"exporter_bin": "112233-0099"},
        "certificate_of_origin": {"exporter_tin": "556677889900"},
    }

    bin_issues, _, _ = validator._validate_bin_all_docs("112233-0099", docs, {})
    tin_issues, _, _ = validator._validate_tin_all_docs("556677889900", docs, {})

    assert len(bin_issues) == 1
    assert "Certificate of Origin" in bin_issues[0].message
    assert len(tin_issues) == 1
    assert "Bill of Lading" in tin_issues[0].message


def test_bin_tin_doc_level_presence_distinguishes_missing_vs_parse_failed():
    validator = CrossDocValidator()
    docs = {
        "invoice": {"exporter_bin": "112233-0099", "exporter_tin": "556677889900"},
        "packing_list": {
            "_field_details": {
                "exporter_bin": {"reason": "parser_failed"},
                "exporter_tin": {"reason": "parser_failed"},
            }
        },
        "bill_of_lading": {"exporter_bin": "112233-0099"},
        "certificate_of_origin": {"exporter_tin": "556677889900"},
    }

    bin_issues, _, _ = validator._validate_bin_all_docs("112233-0099", docs, {})
    tin_issues, _, _ = validator._validate_tin_all_docs("556677889900", docs, {})

    assert len(bin_issues) == 1
    assert "Parse failed on: Packing List" in bin_issues[0].message
    assert "Missing on: Certificate of Origin" in bin_issues[0].message

    assert len(tin_issues) == 1
    assert "Parse failed on: Packing List" in tin_issues[0].message
    assert "Missing on: Bill of Lading" in tin_issues[0].message


def test_47a_po_bin_tin_detection_handles_formatting_variants_case_hyphen_space():
    validator = CrossDocValidator()
    requirements = validator._parse_47a_requirements(
        {
            "additional_conditions": (
                "Buyer Purchase Order No. PO-AB-7788 must appear on all documents. "
                "Exporter B.I.N. No. 112233-0099 must appear on all documents. "
                "E-TIN No. 5566 7788 9900 must appear on all documents."
            )
        }
    )

    docs = {
        "invoice": {
            "raw_text": "COMMERCIAL INVOICE\nPO AB 7788\nBIN 1122330099\nTIN 556677889900",
            "po_number": "PO AB 7788",
            "exporter_bin": "1122330099",
            "exporter_tin": "556677889900",
        },
        "packing_list": {
            "raw_text": "PACKING LIST\nP.O.-AB-7788\nB.I.N 112233-0099\nE TIN: 5566-7788-9900",
        },
        "bill_of_lading": {
            "raw_text": "BILL OF LADING\nPO: POAB7788\nVAT REG NO 112233 0099\nTAX ID 556677889900",
        },
        "certificate_of_origin": {
            "raw_text": "CERTIFICATE OF ORIGIN\nPO NO PO-AB-7788\nBUSINESS IDENTIFICATION NO 112233-0099\nETIN 556677889900",
        },
    }

    po_issues, _, _ = validator._validate_po_number_all_docs(requirements["po_number"], docs, {})
    bin_issues, _, _ = validator._validate_bin_all_docs(requirements["bin_number"], docs, {})
    tin_issues, _, _ = validator._validate_tin_all_docs(requirements["tin_number"], docs, {})

    assert po_issues == []
    assert bin_issues == []
    assert tin_issues == []


def test_47a_bin_tin_detection_finds_token_in_noisy_ocr_text():
    validator = CrossDocValidator()
    docs = {
        "invoice": {
            "raw_text": "COMMERCIAL INVOICE\nEXPORTER B1N N0: 112233-0099\nE-T1N N0: 556677889900",
            "exporter_bin": "112233-0099",
            "exporter_tin": "556677889900",
        },
        "packing_list": {
            "raw_text": "PACKING LIST\n1122 33-00 99\n5566 7788 9900",
            "exporter_bin": "1122 33-00 99",
            "exporter_tin": "5566 7788 9900",
        },
    }

    bin_issues, _, _ = validator._validate_bin_all_docs("112233-0099", docs, {})
    tin_issues, _, _ = validator._validate_tin_all_docs("556677889900", docs, {})

    assert bin_issues == []
    assert tin_issues == []


def test_47a_token_detection_reports_true_missing_with_presence_matrix():
    validator = CrossDocValidator()
    docs = {
        "invoice": {"raw_text": "INVOICE PO-AB-7788 BIN 112233-0099 TIN 556677889900"},
        "packing_list": {"raw_text": "PACKING LIST PO-AB-7788 BIN 112233-0099"},
        "bill_of_lading": {"raw_text": "B/L PO-AB-7788 BIN 112233-0099"},
        "certificate_of_origin": {"raw_text": "COO PO-AB-7788 TIN 556677889900"},
    }

    po_issues, _, _ = validator._validate_po_number_all_docs("PO-AB-7788", docs, {})
    bin_issues, _, _ = validator._validate_bin_all_docs("112233-0099", docs, {})
    tin_issues, _, _ = validator._validate_tin_all_docs("556677889900", docs, {})

    assert po_issues == []
    assert len(bin_issues) == 1
    assert "Missing on: Certificate of Origin" in bin_issues[0].found
    assert "Presence matrix:" in bin_issues[0].found
    assert len(tin_issues) == 1
    assert "Missing on: Packing List, Bill of Lading" in tin_issues[0].found
    assert "Presence matrix:" in tin_issues[0].found


def test_two_stage_validation_promotes_vat_tax_aliases_to_exporter_bin_tin_for_doc_level_output():
    funcs = _load_validate_functions(
        ["_apply_two_stage_validation"],
        extra_globals={
            "json": json,
            "logger": SimpleNamespace(info=lambda *a, **k: None, warning=lambda *a, **k: None),
            "_get_two_stage_extractor": lambda: _FakeTwoStageExtractor(validated_fields={}, summary={"total": 0, "trusted": 0, "review": 0, "untrusted": 0}),
            "_count_populated_canonical_fields": lambda fields: len([k for k, v in (fields or {}).items() if not str(k).startswith("_") and v not in (None, "")]),
            "canonical_field_key": lambda key: {
                "vat_no": "exporter_bin",
                "tax_reg_no": "exporter_tin",
            }.get(str(key), str(key)),
        },
    )

    apply_two_stage = funcs["_apply_two_stage_validation"]
    validated, _ = apply_two_stage(
        {
            "extracted_fields": {
                "vat_no": "112233-0099",
                "tax_reg_no": "556677889900",
            }
        },
        "certificate_of_origin",
        "coo.pdf",
    )

    assert validated["extracted_fields"]["exporter_bin"] == "112233-0099"
    assert validated["extracted_fields"]["exporter_tin"] == "556677889900"


def test_blocked_submission_reason_codes_include_validation_blocked():
    @dataclass
    class _FakeValue:
        value: Any

    @dataclass
    class _FakeBaseline:
        lc_number: _FakeValue
        amount: _FakeValue
        currency: _FakeValue
        applicant: _FakeValue
        beneficiary: _FakeValue
        extraction_completeness: float
        critical_completeness: float

    @dataclass
    class _FakeGateResult:
        blocking_issues: List[Dict[str, Any]]
        completeness: float
        critical_completeness: float
        missing_critical: List[str]
        missing_required: List[str]
        block_reason: str

        def to_dict(self):
            return {
                "status": "blocked",
                "missing_critical": self.missing_critical,
            }

    funcs = _load_validate_functions(
        [
            "_build_unresolved_critical_context",
            "_build_submission_eligibility_context",
            "_build_blocked_structured_result",
        ],
        extra_globals={
            "uuid4": lambda: "doc-123",
            "_build_document_extraction_v1": lambda docs: {"documents": docs},
            "_build_processing_summary_v2": lambda summary, documents, issues, compliance_rate: {
                "documents": documents,
                "severity_breakdown": summary.get("severity_breakdown", {}),
            },
            "_build_issue_provenance_v1": lambda issues: {"issues": issues},
            "LCBaseline": _FakeBaseline,
        },
    )

    build_blocked = funcs["_build_blocked_structured_result"]
    gate = _FakeGateResult(
        blocking_issues=[{"rule": "LC-MISSING-NUMBER"}],
        completeness=0.45,
        critical_completeness=0.2,
        missing_critical=["lc_number"],
        missing_required=[],
        block_reason="Missing LC number",
    )
    baseline = _FakeBaseline(
        lc_number=_FakeValue("LC-001"),
        amount=_FakeValue(100000),
        currency=_FakeValue("USD"),
        applicant=_FakeValue("Applicant"),
        beneficiary=_FakeValue("Beneficiary"),
        extraction_completeness=0.5,
        critical_completeness=0.25,
    )

    result = build_blocked(
        v2_gate_result=gate,
        v2_baseline=baseline,
        lc_type="import",
        processing_duration=0.5,
        documents=[{"document_type": "letter_of_credit", "extraction_status": "partial"}],
    )

    assert result["submission_eligibility"]["reasons"] == ["validation_blocked"]
    assert result["submission_eligibility"]["source"] == "validation"


def test_issue_payload_includes_decision_status_and_reason_code_when_field_matches():
    funcs = _load_validate_functions(["_augment_issues_with_field_decisions"])
    augment = funcs["_augment_issues_with_field_decisions"]

    issues = [
        {"id": "i-1", "field_name": "amount", "severity": "critical"},
        {"id": "i-2", "title": "Doc mismatch"},
    ]
    decisions = {
        "amount": {"status": "retry", "reason_code": "extraction_failed"},
    }

    augment(issues, decisions)

    assert issues[0]["decision_status"] == "retry"
    assert issues[0]["reason_code"] == "extraction_failed"
    provenance = build_issue_provenance_v1(issues)
    assert provenance["issues"][0]["decision_status"] == "retry"
    assert provenance["issues"][0]["reason_code"] == "extraction_failed"


def test_document_field_details_include_decision_and_retry_trace():
    funcs = _load_validate_functions(["_augment_doc_field_details_with_decisions"])
    augment = funcs["_augment_doc_field_details_with_decisions"]

    docs = [
        {
            "filename": "lc.pdf",
            "field_details": {"amount": {"confidence": 0.42}},
            "extracted_fields": {
                "_field_decisions": {
                    "amount": {
                        "status": "retry",
                        "reason_code": "extraction_failed",
                        "retry_trace": {"attempted_passes": ["regex_fallback"], "recovered": False},
                    }
                }
            },
        }
    ]

    augment(docs)

    amount = docs[0]["field_details"]["amount"]
    assert amount["decision_status"] == "retry"
    assert amount["reason_code"] == "extraction_failed"
    assert amount["retry_trace"]["recovered"] is False


def test_submission_eligibility_aggregates_missing_reason_codes_and_unresolved_statuses():
    funcs = _load_validate_functions(
        ["_build_unresolved_critical_context", "_build_submission_eligibility_context"]
    )
    build_context = funcs["_build_submission_eligibility_context"]

    gate_result = {"missing_reason_codes": ["missing_in_source"]}
    decisions = {
        "amount": {"status": "retry", "reason_code": "extraction_failed"},
        "lc_number": {"status": "rejected", "reason_code": "conflict_detected"},
    }

    eligibility = build_context(gate_result, decisions)

    assert set(eligibility["missing_reason_codes"]) == {
        "missing_in_source",
        "extraction_failed",
        "conflict_detected",
    }
    assert set(eligibility["unresolved_critical_statuses"]) == {"retry", "rejected"}


def test_unresolved_critical_fields_always_have_status_and_reason_code():
    funcs = _load_validate_functions(["_build_unresolved_critical_context"])
    build_unresolved = funcs["_build_unresolved_critical_context"]

    unresolved = build_unresolved(
        {
            "amount": {"status": "retry", "reason_code": "extraction_failed"},
            "beneficiary": {"status": "rejected"},
        }
    )

    by_field = {item["field"]: item for item in unresolved}
    assert by_field["amount"]["status"] == "retry"
    assert by_field["amount"]["reason_code"] == "extraction_failed"
    assert by_field["beneficiary"]["status"] == "rejected"
    assert by_field["beneficiary"]["reason_code"] == "unknown"
