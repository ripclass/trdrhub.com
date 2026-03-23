from __future__ import annotations

import ast
import importlib.util
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional


ROOT = Path(__file__).resolve().parents[1]
LAUNCH_PIPELINE_PATH = ROOT / "app" / "services" / "extraction" / "launch_pipeline.py"
LC_DATES_PATH = ROOT / "app" / "routers" / "validation" / "lc_dates.py"
LC_INTAKE_PATH = ROOT / "app" / "routers" / "validation" / "lc_intake.py"
STRUCTURED_BUILDER_PATH = ROOT / "app" / "services" / "extraction" / "structured_lc_builder.py"
LC_TAXONOMY_PATH = ROOT / "app" / "services" / "extraction" / "lc_taxonomy.py"

MT700_SAMPLE_TEXT = (
    "MT700 Export Letter of Credit - MASTER\n"
    ":20: EXP2026BD001\n"
    ":31C: 260415\n"
    ":31D: 261015USA\n"
    ":44E: CHITTAGONG SEA PORT, BANGLADESH\n"
    ":44F: NEW YORK, USA\n"
    ":44C: 260930\n"
)


def _load_launch_pipeline_symbols() -> Dict[str, Any]:
    source = LAUNCH_PIPELINE_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)
    target_functions = {
        "_build_lc_user_facing_extracted_fields",
        "_coerce_mt700_date_iso",
        "_extract_mt700_timeline_fields",
        "_shape_lc_financial_payload",
    }

    selected_nodes: List[ast.AST] = []
    for node in parsed.body:
        if isinstance(node, ast.FunctionDef) and node.name in target_functions:
            selected_nodes.append(node)

    module_ast = ast.Module(body=selected_nodes, type_ignores=[])
    ast.fix_missing_locations(module_ast)
    namespace: Dict[str, Any] = {
        "Any": Any,
        "Dict": Dict,
        "Optional": Optional,
        "date": date,
        "re": re,
        "_extract_label_value": lambda raw_text, labels: None,
        "_extract_amount_value": lambda raw_text, labels: None,
        "_apply_canonical_normalization": lambda payload: payload,
    }
    exec(compile(module_ast, str(LAUNCH_PIPELINE_PATH), "exec"), namespace)
    return namespace


def _load_validate_symbols() -> Dict[str, Any]:
    lc_dates = _load_lc_dates_symbols()
    lc_intake = _load_lc_intake_symbols(lc_dates)
    return {
        "backfill_lc_mt700_sources": lc_dates["backfill_lc_mt700_sources"],
        "_coerce_mt700_date_iso": lc_dates["coerce_mt700_date_iso"],
        "_extract_mt700_block_value": lc_dates["extract_mt700_block_value"],
        "_extract_mt700_timeline_fields": lc_dates["extract_mt700_timeline_fields"],
        "_repair_lc_mt700_dates": lc_dates["repair_lc_mt700_dates"],
        "_build_lc_intake_summary": lc_intake["build_lc_intake_summary"],
    }


def _load_module(path: Path, name: str):
    root_str = str(ROOT)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_lc_dates_symbols() -> Dict[str, Any]:
    source = LC_DATES_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)
    selected_nodes = [
        node
        for node in parsed.body
        if isinstance(node, ast.FunctionDef)
        and node.name
        in {
            "backfill_lc_mt700_sources",
            "coerce_mt700_date_iso",
            "extract_mt700_block_value",
            "extract_mt700_timeline_fields",
            "repair_lc_mt700_dates",
        }
    ]
    module_ast = ast.Module(body=selected_nodes, type_ignores=[])
    ast.fix_missing_locations(module_ast)
    namespace: Dict[str, Any] = {
        "Any": Any,
        "Dict": Dict,
        "Optional": Optional,
        "datetime": __import__("datetime").datetime,
        "re": re,
    }
    exec(compile(module_ast, str(LC_DATES_PATH), "exec"), namespace)
    return namespace


def _load_lc_intake_symbols(lc_dates: Dict[str, Any]) -> Dict[str, Any]:
    source = LC_INTAKE_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)
    selected_nodes = [
        node
        for node in parsed.body
        if isinstance(node, ast.FunctionDef) and node.name == "build_lc_intake_summary"
    ]
    module_ast = ast.Module(body=selected_nodes, type_ignores=[])
    ast.fix_missing_locations(module_ast)
    namespace: Dict[str, Any] = {
        "Any": Any,
        "Dict": Dict,
        "repair_lc_mt700_dates": lc_dates["repair_lc_mt700_dates"],
    }
    exec(compile(module_ast, str(LC_INTAKE_PATH), "exec"), namespace)
    return namespace


def _load_structured_builder_module():
    spec = importlib.util.spec_from_file_location("structured_lc_builder_mt700_timeline_test", STRUCTURED_BUILDER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load structured_lc_builder module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_lc_taxonomy_module():
    spec = importlib.util.spec_from_file_location("lc_taxonomy_mt700_timeline_test", LC_TAXONOMY_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load lc_taxonomy module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_mt700_shape_reanchors_swapped_ai_dates_from_raw_tags() -> None:
    ns = _load_launch_pipeline_symbols()
    shape_lc_financial_payload = ns["_shape_lc_financial_payload"]

    shaped = shape_lc_financial_payload(
        {
            "lc_number": "EXP2026BD001",
            "issue_date": "2026-04-15",
            "expiry_date": "2026-09-30",
            "latest_shipment_date": "2026-10-15",
            "timeline": {
                "issue_date": "2026-04-15",
                "expiry_date": "2026-09-30",
                "latest_shipment": "2026-10-15",
            },
        },
        lc_subtype="letter_of_credit",
        raw_text=MT700_SAMPLE_TEXT,
        source_type="letter_of_credit",
        lc_format="mt700",
    )

    assert shaped["issue_date"] == "2026-04-15"
    assert shaped["expiry_date"] == "2026-10-15"
    assert shaped["latest_shipment_date"] == "2026-09-30"
    assert shaped["latest_shipment"] == "2026-09-30"
    assert shaped["timeline"]["expiry_date"] == "2026-10-15"
    assert shaped["timeline"]["latest_shipment"] == "2026-09-30"
    assert shaped["dates"]["expiry"] == "2026-10-15"
    assert shaped["dates"]["latest_shipment"] == "2026-09-30"
    assert shaped["dates"]["place_of_expiry"] == "USA"


def test_lc_intake_summary_accepts_canonical_nested_mt700_dates() -> None:
    ns = _load_validate_symbols()
    build_lc_intake_summary = ns["_build_lc_intake_summary"]

    summary = build_lc_intake_summary(
        {
            "lc_number": "EXP2026BD001",
            "currency": "USD",
            "dates": {
                "issue": "2026-04-15",
                "expiry": "2026-10-15",
                "latest_shipment": "2026-09-30",
            },
            "port_of_loading": "CHITTAGONG SEA PORT, BANGLADESH",
            "port_of_discharge": "NEW YORK, USA",
        }
    )

    assert summary["issue_date"] == "2026-04-15"
    assert summary["expiry_date"] == "2026-10-15"
    assert summary["latest_shipment_date"] == "2026-09-30"


def test_validate_mt700_date_repair_reanchors_swapped_flat_dates_from_raw_tags() -> None:
    ns = _load_validate_symbols()
    repair_lc_mt700_dates = ns["_repair_lc_mt700_dates"]

    repaired = repair_lc_mt700_dates(
        {
            "issue_date": "2026-04-15",
            "expiry_date": "2026-09-30",
            "latest_shipment_date": "2026-10-15",
            "mt700": {"blocks": {}, "raw_text": MT700_SAMPLE_TEXT, "version": "mt700_v1"},
        }
    )

    assert repaired["issue_date"] == "2026-04-15"
    assert repaired["expiry_date"] == "2026-10-15"
    assert repaired["latest_shipment_date"] == "2026-09-30"
    assert repaired["latest_shipment"] == "2026-09-30"
    assert repaired["dates"]["expiry"] == "2026-10-15"
    assert repaired["dates"]["latest_shipment"] == "2026-09-30"
    assert repaired["place_of_expiry"] == "USA"


def test_validate_mt700_date_repair_accepts_mt700_raw_block_map() -> None:
    ns = _load_validate_symbols()
    repair_lc_mt700_dates = ns["_repair_lc_mt700_dates"]

    repaired = repair_lc_mt700_dates(
        {
            "issue_date": "2026-04-15",
            "expiry_date": "2026-09-30",
            "latest_shipment_date": "2026-10-15",
            "mt700": {"raw": {"31C": "260415", "31D": "261015USA", "44C": "260930"}},
        }
    )

    assert repaired["issue_date"] == "2026-04-15"
    assert repaired["expiry_date"] == "2026-10-15"
    assert repaired["latest_shipment_date"] == "2026-09-30"
    assert repaired["latest_shipment"] == "2026-09-30"
    assert repaired["dates"]["expiry"] == "2026-10-15"
    assert repaired["dates"]["latest_shipment"] == "2026-09-30"


def test_backfill_lc_mt700_sources_uses_extracted_context_lc_text_for_intake_repair() -> None:
    ns = _load_validate_symbols()
    backfill_lc_mt700_sources = ns["backfill_lc_mt700_sources"]
    repair_lc_mt700_dates = ns["_repair_lc_mt700_dates"]
    build_lc_intake_summary = ns["_build_lc_intake_summary"]

    enriched = backfill_lc_mt700_sources(
        {
            "issue_date": "2026-04-15",
            "expiry_date": "2026-09-30",
            "latest_shipment_date": "2026-10-15",
        },
        {"lc_text": MT700_SAMPLE_TEXT},
    )

    assert enriched["raw_text"] == MT700_SAMPLE_TEXT.strip()
    assert enriched["mt700"]["raw_text"] == MT700_SAMPLE_TEXT.strip()

    repaired = repair_lc_mt700_dates(enriched)
    summary = build_lc_intake_summary(repaired)

    assert summary["issue_date"] == "2026-04-15"
    assert summary["expiry_date"] == "2026-10-15"
    assert summary["latest_shipment_date"] == "2026-09-30"


def test_validate_source_backfills_lc_mt700_sources_before_repair() -> None:
    source = (ROOT / "app" / "routers" / "validate.py").read_text(encoding="utf-8")
    assert "_backfill_lc_mt700_sources(" in source


def test_structured_builder_preserves_mt700_timeline_dates_after_shaping() -> None:
    launch_ns = _load_launch_pipeline_symbols()
    shape_lc_financial_payload = launch_ns["_shape_lc_financial_payload"]
    structured_builder = _load_structured_builder_module()

    shaped = shape_lc_financial_payload(
        {
            "lc_number": "EXP2026BD001",
            "issue_date": "2026-04-15",
            "expiry_date": "2026-09-30",
            "latest_shipment_date": "2026-10-15",
        },
        lc_subtype="letter_of_credit",
        raw_text=MT700_SAMPLE_TEXT,
        source_type="letter_of_credit",
        lc_format="mt700",
    )

    result = structured_builder.build_unified_structured_result([], shaped, None)["structured_result"]["lc_structured"]

    assert result["dates"]["issue"] == "2026-04-15"
    assert result["dates"]["expiry"] == "2026-10-15"
    assert result["dates"]["latest_shipment"] == "2026-09-30"
    assert result["dates"]["place_of_expiry"] == "USA"


def test_structured_builder_hydrates_mt700_raw_blocks_when_blocks_are_missing() -> None:
    structured_builder = _load_structured_builder_module()

    result = structured_builder.build_unified_structured_result(
        [],
        {
            "lc_number": "EXP2026BD001",
            "issue_date": "2026-04-15",
            "expiry_date": "2026-09-30",
            "latest_shipment_date": "2026-10-15",
            "mt700": {
                "raw": {"31C": "260415", "31D": "261015USA", "44C": "260930"},
                "version": "mt700_v1",
            },
        },
        None,
    )["structured_result"]["lc_structured"]

    assert result["expiry_date"] == "2026-10-15"
    assert result["latest_shipment_date"] == "2026-09-30"
    assert result["dates"]["expiry"] == "2026-10-15"
    assert result["dates"]["latest_shipment"] == "2026-09-30"


def test_lc_taxonomy_attribute_payload_prefers_mt700_dates_over_swapped_flat_values() -> None:
    lc_taxonomy = _load_lc_taxonomy_module()

    attrs = lc_taxonomy.build_attribute_payload(
        {
            "expiry_date": "2026-09-30",
            "latest_shipment_date": "2026-10-15",
            "mt700": {"blocks": {}, "raw_text": MT700_SAMPLE_TEXT, "version": "mt700_v1"},
        },
        applicable_rules="ucp600",
        instrument_type="documentary_credit",
        required_documents=[],
    )

    assert attrs["expiry_date"] == "2026-10-15"
    assert attrs["latest_shipment_date"] == "2026-09-30"
    assert attrs["expiry_place"] == "USA"


def test_lc_taxonomy_attribute_payload_accepts_mt700_raw_block_map() -> None:
    lc_taxonomy = _load_lc_taxonomy_module()

    attrs = lc_taxonomy.build_attribute_payload(
        {
            "expiry_date": "2026-09-30",
            "latest_shipment_date": "2026-10-15",
            "mt700": {"raw": {"31C": "260415", "31D": "261015USA", "44C": "260930"}},
        },
        applicable_rules="ucp600",
        instrument_type="documentary_credit",
        required_documents=[],
    )

    assert attrs["expiry_date"] == "2026-10-15"
    assert attrs["latest_shipment_date"] == "2026-09-30"


def test_lc_user_facing_extracted_fields_prefer_canonical_snapshot_values() -> None:
    launch_ns = _load_launch_pipeline_symbols()
    shape_lc_financial_payload = launch_ns["_shape_lc_financial_payload"]
    build_lc_user_facing_extracted_fields = launch_ns["_build_lc_user_facing_extracted_fields"]

    shaped = shape_lc_financial_payload(
        {
            "number": "EXP2026BD001",
            "issue_date": "2026-04-15",
            "beneficiary": "Dhaka Knitwear & Exports Ltd.",
            "goods_description": "100% cotton knit t-shirts",
            "required_documents_detailed": [
                {
                    "code": "beneficiary_certificate",
                    "display_name": "Beneficiary Certificate",
                    "raw_text": "BENEFICIARY CERTIFICATE CONFIRMING GOODS ARE BRAND NEW AND MANUFACTURED IN 2026.",
                }
            ],
            "requirement_conditions": [
                "ALL DOCUMENTS MUST SHOW LC NO. EXP2026BD001 AND BUYER PURCHASE ORDER NO. GBE-44592."
            ],
            "unmapped_requirements": [
                "UNKNOWN CERTIFICATE WORDING REQUIRING MANUAL MAPPING."
            ],
        },
        lc_subtype="letter_of_credit",
        raw_text=MT700_SAMPLE_TEXT,
        source_type="letter_of_credit",
        lc_format="mt700",
    )

    user_facing = build_lc_user_facing_extracted_fields(shaped)

    assert user_facing["lc_number"] == "EXP2026BD001"
    assert user_facing["issue_date"] == "2026-04-15"
    assert user_facing["expiry_date"] == "2026-10-15"
    assert user_facing["latest_shipment_date"] == "2026-09-30"
    assert user_facing["documents_required"] == [
        "BENEFICIARY CERTIFICATE CONFIRMING GOODS ARE BRAND NEW AND MANUFACTURED IN 2026."
    ]
    assert user_facing["requirement_conditions"] == [
        "ALL DOCUMENTS MUST SHOW LC NO. EXP2026BD001 AND BUYER PURCHASE ORDER NO. GBE-44592."
    ]
    assert user_facing["unmapped_requirements"] == [
        "UNKNOWN CERTIFICATE WORDING REQUIRING MANUAL MAPPING."
    ]
