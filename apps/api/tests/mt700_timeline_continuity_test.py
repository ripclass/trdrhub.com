from __future__ import annotations

import ast
import importlib.util
import re
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional


ROOT = Path(__file__).resolve().parents[1]
LAUNCH_PIPELINE_PATH = ROOT / "app" / "services" / "extraction" / "launch_pipeline.py"
VALIDATE_PATH = ROOT / "app" / "routers" / "validate.py"
STRUCTURED_BUILDER_PATH = ROOT / "app" / "services" / "extraction" / "structured_lc_builder.py"

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
    source = VALIDATE_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)
    selected_nodes: List[ast.AST] = []
    for node in parsed.body:
        if isinstance(node, ast.FunctionDef) and node.name == "_build_lc_intake_summary":
            selected_nodes.append(node)

    module_ast = ast.Module(body=selected_nodes, type_ignores=[])
    ast.fix_missing_locations(module_ast)
    namespace: Dict[str, Any] = {"Dict": Dict}
    exec(compile(module_ast, str(VALIDATE_PATH), "exec"), namespace)
    return namespace


def _load_structured_builder_module():
    spec = importlib.util.spec_from_file_location("structured_lc_builder_mt700_timeline_test", STRUCTURED_BUILDER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load structured_lc_builder module")
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
