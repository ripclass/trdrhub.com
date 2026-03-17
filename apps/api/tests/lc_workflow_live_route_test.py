from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple


ROOT = Path(__file__).resolve().parents[1]
VALIDATE_PATH = ROOT / "app" / "routers" / "validate.py"
LC_TYPES_PATH = ROOT / "app" / "core" / "lc_types.py"
LC_CLASSIFIER_PATH = ROOT / "app" / "services" / "lc_classifier.py"
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
    source = VALIDATE_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)
    target_functions = {
        "_parse_json_if_possible",
        "_coerce_text_list",
        "_infer_required_document_types_from_lc",
        "_extract_workflow_lc_type",
        "_resolve_legacy_workflow_lc_fields",
        "_prepare_extractor_outputs_for_structured_result",
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
    lc_types = _load_module(LC_TYPES_PATH, "lc_types_validate_live_test")
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
    }
    exec(compile(module_ast, str(VALIDATE_PATH), "exec"), namespace)
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
    classifier = _load_module(LC_CLASSIFIER_PATH, "lc_classifier_live_route_test")
    lc_context = _live_like_lc_context()

    guess = classifier.detect_lc_type(
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


def test_live_route_response_builder_keeps_export_workflow_for_live_shaped_payload() -> None:
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
    assert merged["lc_classification"]["workflow_orientation"] == "export"

    structured_result = structured_builder.build_unified_structured_result(
        session_documents=[],
        extractor_outputs=merged,
        legacy_payload=None,
    )["structured_result"]

    assert structured_result["lc_type"] == "export"
    assert structured_result["lc_structured"]["lc_classification"]["workflow_orientation"] == "export"


def test_exporter_lane_stays_unknown_when_ports_do_not_expose_country_signal() -> None:
    classifier = _load_module(LC_CLASSIFIER_PATH, "lc_classifier_live_route_ambiguity_test")
    lc_context = _live_like_lc_context(
        loading_port="CHITTAGONG SEA PORT",
        discharge_port="NEW YORK HARBOR",
    )

    guess = classifier.detect_lc_type(
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
