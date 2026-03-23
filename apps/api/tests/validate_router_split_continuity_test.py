from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

from fastapi import Depends


ROOT = Path(__file__).resolve().parents[1]
VALIDATE_PATH = ROOT / "app" / "routers" / "validate.py"
VALIDATE_RUN_PATH = ROOT / "app" / "routers" / "validate_run.py"
VALIDATE_CUSTOMS_PATH = ROOT / "app" / "routers" / "validate_customs.py"
VALIDATE_RESULTS_PATH = ROOT / "app" / "routers" / "validate_results.py"


def _stub_dependency():
    return None


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _build_shared_stub() -> dict:
    return {
        "Depends": Depends,
        "Request": object,
        "User": object,
        "Session": object,
        "UUID": str,
        "get_db": _stub_dependency,
        "get_user_optional": _stub_dependency,
        "get_current_user": _stub_dependency,
    }


def test_split_validation_subrouters_register_expected_paths() -> None:
    validate_run = _load_module(VALIDATE_RUN_PATH, "validate_run_route_split_test")
    validate_customs = _load_module(VALIDATE_CUSTOMS_PATH, "validate_customs_route_split_test")
    validate_results = _load_module(VALIDATE_RESULTS_PATH, "validate_results_route_split_test")
    shared = _build_shared_stub()

    run_router = validate_run.build_router(shared)
    customs_router = validate_customs.build_router(shared)
    results_router = validate_results.build_router(shared)

    run_paths = {(route.path, tuple(sorted(route.methods or []))) for route in run_router.routes}
    customs_paths = {(route.path, tuple(sorted(route.methods or []))) for route in customs_router.routes}
    results_paths = {(route.path, tuple(sorted(route.methods or []))) for route in results_router.routes}

    assert ("/", ("POST",)) in run_paths
    assert ("/v2", ("POST",)) in run_paths
    assert ("/customs-pack/{session_id}", ("GET",)) in customs_paths
    assert ("/v2/session/{session_id}", ("GET",)) in results_paths


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
