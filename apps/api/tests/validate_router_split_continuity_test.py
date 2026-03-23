from __future__ import annotations

import ast
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

VALIDATE_PATH = ROOT / "app" / "routers" / "validate.py"
VALIDATE_RUN_PATH = ROOT / "app" / "routers" / "validate_run.py"
VALIDATE_CUSTOMS_PATH = ROOT / "app" / "routers" / "validate_customs.py"
VALIDATE_RESULTS_PATH = ROOT / "app" / "routers" / "validate_results.py"


def test_split_validation_subrouters_register_expected_paths() -> None:
    run_source = VALIDATE_RUN_PATH.read_text(encoding="utf-8")
    customs_source = VALIDATE_CUSTOMS_PATH.read_text(encoding="utf-8")
    results_source = VALIDATE_RESULTS_PATH.read_text(encoding="utf-8")

    assert 'router.add_api_route("/", validate_doc, methods=["POST"])' in run_source
    assert 'router.add_api_route("/v2", validate_doc_v2, methods=["POST"])' in run_source
    assert 'router.add_api_route("/customs-pack/{session_id}", generate_customs_pack, methods=["GET"])' in customs_source
    assert 'router.add_api_route("/v2/session/{session_id}", get_validation_result_v2, methods=["GET"])' in results_source


def test_validate_module_aggregates_split_subrouters_instead_of_inline_route_defs() -> None:
    source = VALIDATE_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)

    route_functions = {
        node.name
        for node in parsed.body
        if isinstance(node, ast.AsyncFunctionDef)
        and any(
            isinstance(dec, ast.Call)
            and isinstance(dec.func, ast.Attribute)
            and isinstance(dec.func.value, ast.Name)
            and dec.func.value.id == "router"
            for dec in node.decorator_list
        )
    }

    assert "validate_doc" not in route_functions
    assert "validate_doc_v2" not in route_functions
    assert "generate_customs_pack" not in route_functions
    assert "get_validation_result_v2" not in route_functions

    assert "router.include_router(_build_validate_run_router(globals()))" in source
    assert "router.include_router(_build_validate_customs_router(globals()))" in source
    assert "router.include_router(_build_validate_results_router(globals()))" in source
