from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple


ROOT = Path(__file__).resolve().parents[1]
VALIDATE_PATH = ROOT / "app" / "routers" / "validate.py"
LC_INTAKE_PATH = ROOT / "app" / "routers" / "validation" / "lc_intake.py"
REQUEST_PARSING_PATH = ROOT / "app" / "routers" / "validation" / "request_parsing.py"
LC_TYPES_PATH = ROOT / "app" / "core" / "lc_types.py"
LC_CLASSIFIER_PATH = ROOT / "app" / "services" / "lc_classifier.py"
LC_TYPE_DETECTOR_PATH = ROOT / "app" / "services" / "lc_type_detector.py"
LC_TAXONOMY_PATH = ROOT / "app" / "services" / "extraction" / "lc_taxonomy.py"
STRUCTURED_BUILDER_PATH = ROOT / "app" / "services" / "extraction" / "structured_lc_builder.py"


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


def _load_validate_workflow_symbols() -> Dict[str, Any]:
    source = VALIDATE_PATH.read_text(encoding="utf-8-sig")
    parsed = ast.parse(source)
    target_functions = {"_extract_workflow_lc_type"}

    selected_nodes: List[ast.AST] = []
    for node in parsed.body:
        if isinstance(node, ast.FunctionDef) and node.name in target_functions:
            selected_nodes.append(node)

    module_ast = ast.Module(body=selected_nodes, type_ignores=[])
    ast.fix_missing_locations(module_ast)

    lc_types = _load_module(LC_TYPES_PATH, "lc_types_validate_live_test")
    lc_intake = _load_lc_intake_symbols()
    namespace: Dict[str, Any] = {
        "Any": Any,
        "Dict": Dict,
        "List": List,
        "Optional": Optional,
        "Tuple": Tuple,
        "json": json,
        "LCType": lc_types.LCType,
        "normalize_lc_type": lc_types.normalize_lc_type,
    }
    exec(compile(module_ast, str(VALIDATE_PATH), "exec"), namespace)
    return {
        "_extract_workflow_lc_type": namespace["_extract_workflow_lc_type"],
        "_coerce_text_list": lc_intake["coerce_text_list"],
        "_infer_required_document_types_from_lc": lc_intake["infer_required_document_types_from_lc"],
        "_resolve_legacy_workflow_lc_fields": lc_intake["resolve_legacy_workflow_lc_fields"],
        "_prepare_extractor_outputs_for_structured_result": lc_intake["prepare_extractor_outputs_for_structured_result"],
        "module": lc_intake,
    }


def _load_lc_intake_symbols() -> Dict[str, Any]:
    source = LC_INTAKE_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)
    target_functions = {
        "_parse_json_if_possible",
        "coerce_text_list",
        "infer_required_document_types_from_lc",
        "resolve_legacy_workflow_lc_fields",
        "prepare_extractor_outputs_for_structured_result",
    }
    selected_nodes: List[ast.AST] = []
    for node in parsed.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "_DOC_REQUIREMENT_HINTS":
                    selected_nodes.append(node)
                    break
        if isinstance(node, ast.FunctionDef) and node.name in target_functions:
            selected_nodes.append(node)

    module_ast = ast.Module(body=selected_nodes, type_ignores=[])
    ast.fix_missing_locations(module_ast)
    taxonomy = _load_module(LC_TAXONOMY_PATH, "lc_taxonomy_validate_live_test")
    lc_types = _load_module(LC_TYPES_PATH, "lc_types_validate_live_test_for_intake")
    lc_dates = _load_lc_dates_symbols()
    namespace: Dict[str, Any] = {
        "Any": Any,
        "Dict": Dict,
        "List": List,
        "Optional": Optional,
        "Tuple": Tuple,
        "json": json,
        "LCType": lc_types.LCType,
        "normalize_lc_type": lc_types.normalize_lc_type,
        "normalize_required_documents": taxonomy.normalize_required_documents,
        "build_lc_classification": taxonomy.build_lc_classification,
        "repair_lc_mt700_dates": lc_dates["repair_lc_mt700_dates"],
    }
    exec(compile(module_ast, str(LC_INTAKE_PATH), "exec"), namespace)
    return namespace


def _load_lc_dates_symbols() -> Dict[str, Any]:
    lc_dates_path = ROOT / "app" / "routers" / "validation" / "lc_dates.py"
    source = lc_dates_path.read_text(encoding="utf-8")
    parsed = ast.parse(source)
    selected_nodes = [
        node
        for node in parsed.body
        if isinstance(node, ast.FunctionDef)
        and node.name
        in {
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
        "re": __import__("re"),
    }
    exec(compile(module_ast, str(lc_dates_path), "exec"), namespace)
    return namespace


def _load_lc_classifier_symbols() -> Dict[str, Any]:
    source = LC_CLASSIFIER_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)
    selected_nodes: List[ast.AST] = []
    for node in parsed.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "COUNTRY_SYNONYMS":
                    selected_nodes.append(node)
                    break
        if isinstance(node, ast.FunctionDef):
            selected_nodes.append(node)

    module_ast = ast.Module(body=selected_nodes, type_ignores=[])
    ast.fix_missing_locations(module_ast)
    lc_types = _load_module(LC_TYPES_PATH, "lc_types_validate_live_test_for_classifier")
    lc_type_detector = _load_module(LC_TYPE_DETECTOR_PATH, "lc_type_detector_validate_live_test")
    namespace: Dict[str, Any] = {
        "Any": Any,
        "Dict": Dict,
        "Optional": Optional,
        "re": __import__("re"),
        "LCType": lc_types.LCType,
        "LCTypeGuess": dict,
        "detect_lc_family": lc_type_detector.detect_lc_family,
    }
    exec(compile(module_ast, str(LC_CLASSIFIER_PATH), "exec"), namespace)
    return namespace


def _load_request_parsing_symbols() -> Dict[str, Any]:
    source = REQUEST_PARSING_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)
    target_functions = {"extract_request_user_type", "should_force_json_rules", "resolve_shipment_context"}
    selected_nodes = [
        node
        for node in parsed.body
        if isinstance(node, ast.FunctionDef) and node.name in target_functions
    ]
    module_ast = ast.Module(body=selected_nodes, type_ignores=[])
    ast.fix_missing_locations(module_ast)
    namespace: Dict[str, Any] = {
        "Any": Any,
        "Dict": Dict,
    }
    exec(compile(module_ast, str(REQUEST_PARSING_PATH), "exec"), namespace)
    return namespace


def _live_like_lc_context(
    *,
    loading_port: str = "CHITTAGONG SEA PORT, BANGLADESH",
    discharge_port: str = "NEW YORK, USA",
) -> Dict[str, Any]:
    return {
        "format": "mt700",
        "schema": "mt700",
        "raw_text": (
            "MT700 Export Letter of Credit\n"
            ":50: GLOBAL IMPORTERS INC.\n"
            ":59: DHAKA KNITWEAR & EXPORTS LTD.\n"
            ":44E: CHITTAGONG SEA PORT, BANGLADESH\n"
            ":44F: NEW YORK, USA\n"
        ),
        "applicant": "Global Importers Inc.",
        "beneficiary": "Dhaka Knitwear & Exports Ltd.",
        "port_of_loading": loading_port,
        "port_of_discharge": discharge_port,
        "documents_required": [
            "SIGNED COMMERCIAL INVOICE IN 6 COPIES",
            "FULL SET OF CLEAN ON-BOARD BILL OF LADING",
            "DETAILED PACKING LIST IN 6 COPIES",
            "CERTIFICATE OF ORIGIN",
            "SGS/INTERTEK INSPECTION CERTIFICATE",
            "BENEFICIARY CERTIFICATE",
        ],
    }


def test_live_route_detector_classifies_export_from_exporter_lane_and_raw_port_strings() -> None:
    classifier = _load_lc_classifier_symbols()
    lc_context = _live_like_lc_context()

    guess = classifier["detect_lc_type"](
        lc_context,
        {
            "port_of_loading": lc_context["port_of_loading"],
            "port_of_discharge": lc_context["port_of_discharge"],
        },
        request_context={
            "user_type": "exporter",
            "workflow_type": "export-lc-upload",
            "company_country": None,
        },
    )

    assert guess["lc_type"] == "export"
    assert guess["confidence"] > 0.5
    assert guess["confidence_mode"] == "estimated"
    assert guess["detection_basis"] == "lane_only_context"


def test_live_route_detector_classifies_export_from_flat_lc_ports_without_shipment_context() -> None:
    classifier = _load_lc_classifier_symbols()
    lc_context = _live_like_lc_context()

    guess = classifier["detect_lc_type"](
        lc_context,
        {},
        request_context={
            "user_type": "exporter",
            "workflow_type": "export-lc-intake",
            "company_country": None,
        },
    )

    assert guess["lc_type"] == "export"
    assert guess["confidence"] > 0.5
    assert guess["confidence_mode"] == "estimated"
    assert guess["detection_basis"] == "lane_only_context"


def test_live_route_response_builder_preserves_prepared_workflow_fields_for_live_shaped_payload() -> None:
    validate_symbols = _load_validate_workflow_symbols()
    prepare_structured = validate_symbols["_prepare_extractor_outputs_for_structured_result"]
    structured_builder = _load_module(STRUCTURED_BUILDER_PATH, "structured_lc_builder_live_route_test")

    lc_context = _live_like_lc_context()
    payload = {
        "user_type": "exporter",
        "workflow_type": "export-lc-upload",
        "lc_structured_output": dict(lc_context),
        "lc": dict(lc_context),
    }

    merged = prepare_structured(payload)
    assert merged["lc_type"] in {"export", "unknown"}

    structured_result = structured_builder.build_unified_structured_result(
        session_documents=[],
        extractor_outputs=merged,
        legacy_payload=None,
    )["structured_result"]

    assert structured_result["lc_type"] == merged["lc_type"]
    assert structured_result["lc_structured"]["lc_classification"]["workflow_orientation"] == (
        merged["lc_classification"]["workflow_orientation"]
    )


def test_intake_route_uses_top_level_lc_ports_for_shipment_context() -> None:
    request_parsing = _load_request_parsing_symbols()
    payload = {
        "user_type": "exporter",
        "workflow_type": "export-lc-intake",
        "lc": {
            "ports": {"unrelated": "value"},
            "port_of_loading": "CHITTAGONG SEA PORT, BANGLADESH",
            "port_of_discharge": "NEW YORK, USA",
        },
    }

    shipment_context = request_parsing["resolve_shipment_context"](payload)

    assert shipment_context == {
        "port_of_loading": "CHITTAGONG SEA PORT, BANGLADESH",
        "port_of_discharge": "NEW YORK, USA",
    }


def test_intake_route_ignores_unknown_extracted_workflow_and_falls_back_to_detection() -> None:
    validate_symbols = _load_validate_workflow_symbols()
    extract_workflow_lc_type = validate_symbols["_extract_workflow_lc_type"]
    classifier = _load_lc_classifier_symbols()
    request_parsing = _load_request_parsing_symbols()

    lc_context = _live_like_lc_context()
    lc_context["ports"] = {"unrelated": "value"}
    lc_context["lc_classification"] = {"workflow_orientation": "unknown"}
    lc_context["lc_type"] = "unknown"
    payload = {
        "user_type": "exporter",
        "workflow_type": "export-lc-intake",
        "lc": lc_context,
    }

    assert extract_workflow_lc_type(lc_context) is None

    guess = classifier["detect_lc_type"](
        lc_context,
        request_parsing["resolve_shipment_context"](payload),
        request_context={
            "user_type": payload["user_type"],
            "workflow_type": payload["workflow_type"],
            "company_country": None,
        },
    )

    assert guess["lc_type"] == "export"


def test_exporter_lane_stays_unknown_when_ports_do_not_expose_country_signal() -> None:
    classifier = _load_lc_classifier_symbols()
    lc_context = _live_like_lc_context(
        loading_port="CHITTAGONG SEA PORT",
        discharge_port="NEW YORK HARBOR",
    )

    guess = classifier["detect_lc_type"](
        lc_context,
        {
            "port_of_loading": lc_context["port_of_loading"],
            "port_of_discharge": lc_context["port_of_discharge"],
        },
        request_context={
            "user_type": "exporter",
            "workflow_type": "export-lc-upload",
            "company_country": None,
        },
    )

    assert guess["lc_type"] == "unknown"
