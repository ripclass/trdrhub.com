from __future__ import annotations

import ast
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

from app.services.crossdoc import DEFAULT_LABELS  # noqa: E402


DOC_TYPES_PATH = ROOT / "app" / "routers" / "validation" / "doc_types.py"
UTILITIES_PATH = ROOT / "app" / "routers" / "validation" / "utilities.py"


def _load_doc_type_symbols():
    source = DOC_TYPES_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)
    selected_nodes = []
    for node in parsed.body:
        if isinstance(node, ast.Assign):
            target_names = {
                target.id
                for target in node.targets
                if isinstance(target, ast.Name)
            }
            if "DOCUMENT_TYPE_ALIASES" in target_names:
                selected_nodes.append(node)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.target.id == "DOCUMENT_TYPE_ALIASES":
                selected_nodes.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in {
            "canonical_document_tag",
            "infer_document_type",
            "infer_document_type_from_name",
            "fallback_doc_type",
        }:
            selected_nodes.append(node)
    module_ast = ast.Module(body=selected_nodes, type_ignores=[])
    ast.fix_missing_locations(module_ast)
    namespace = {"Dict": dict, "Any": object, "Optional": object}
    exec(compile(module_ast, str(DOC_TYPES_PATH), "exec"), namespace)
    return namespace


def _load_utility_symbols():
    source = UTILITIES_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)
    selected_nodes = []
    for node in parsed.body:
        if isinstance(node, ast.Assign):
            target_names = {
                target.id
                for target in node.targets
                if isinstance(target, ast.Name)
            }
            if target_names & {
                "_SUPPORTING_SUBTYPE_TO_CANONICAL",
                "_SUPPORTING_FAMILY_TO_CANONICAL",
            }:
                selected_nodes.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in {
            "normalize_doc_type_key",
            "infer_document_type_from_name",
            "fallback_doc_type",
            "resolve_structured_document_type",
        }:
            selected_nodes.append(node)
    module_ast = ast.Module(body=selected_nodes, type_ignores=[])
    ast.fix_missing_locations(module_ast)
    namespace = {"DEFAULT_LABELS": DEFAULT_LABELS, "Dict": dict, "Any": object, "Optional": object}
    exec(compile(module_ast, str(UTILITIES_PATH), "exec"), namespace)
    return namespace


def test_canonical_document_tag_preserves_transport_subtypes() -> None:
    namespace = _load_doc_type_symbols()
    canonical_document_tag = namespace["canonical_document_tag"]

    assert canonical_document_tag("air_waybill") == "air_waybill"
    assert canonical_document_tag("awb") == "air_waybill"
    assert canonical_document_tag("sea waybill") == "sea_waybill"
    assert canonical_document_tag("road transport document") == "road_transport_document"


def test_infer_document_type_preserves_transport_subtypes_from_filename() -> None:
    namespace = _load_doc_type_symbols()
    infer_document_type = namespace["infer_document_type"]

    assert infer_document_type("Air_Waybill.pdf", 5) == "air_waybill"
    assert infer_document_type("Sea_Waybill.pdf", 5) == "sea_waybill"
    assert infer_document_type("Road_Transport_Document.pdf", 5) == "road_transport_document"


def test_infer_document_type_from_name_preserves_transport_subtypes() -> None:
    doc_type_namespace = _load_doc_type_symbols()
    infer_document_type_from_name = doc_type_namespace["infer_document_type_from_name"]

    assert infer_document_type_from_name("Air_Waybill.pdf", 5) == "air_waybill"
    assert infer_document_type_from_name("Sea_Waybill.pdf", 5) == "sea_waybill"
    assert infer_document_type_from_name("Forwarders_Certificate_of_Receipt.pdf", 5) == "forwarder_certificate_of_receipt"


def test_resolve_structured_document_type_keeps_specific_transport_type() -> None:
    utility_namespace = _load_utility_symbols()
    resolve_structured_document_type = utility_namespace["resolve_structured_document_type"]

    payload = {
        "document_type": "air_waybill",
        "filename": "Air_Waybill.pdf",
        "supporting_subtype_guess": "air_waybill",
    }
    assert resolve_structured_document_type(payload, filename="Air_Waybill.pdf", index=5) == "air_waybill"
