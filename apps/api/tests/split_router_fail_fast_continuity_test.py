from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

FILES = [
    ROOT / "app" / "routers" / "validate_run.py",
    ROOT / "app" / "routers" / "validate_customs.py",
    ROOT / "app" / "routers" / "validate_results.py",
    ROOT / "app" / "routers" / "validation" / "request_parsing.py",
    ROOT / "app" / "routers" / "validation" / "result_finalization.py",
    ROOT / "app" / "routers" / "validation" / "validation_execution.py",
]


def test_split_binding_modules_fail_fast_on_missing_shared_bindings() -> None:
    for path in FILES:
        source = path.read_text(encoding="utf-8")
        assert "missing_bindings" in source, path.name
        assert "raise RuntimeError(" in source, path.name
