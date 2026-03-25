from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
CROSSDOC_VALIDATOR_PATH = ROOT / "app" / "services" / "validation" / "crossdoc_validator.py"


class _LoggerStub:
    def info(self, *args: Any, **kwargs: Any) -> None:
        return None

    def warning(self, *args: Any, **kwargs: Any) -> None:
        return None


def _load_crossdoc_47a_symbols() -> Dict[str, Any]:
    source = CROSSDOC_VALIDATOR_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)
    selected_nodes: List[ast.AST] = []

    for node in parsed.body:
        if isinstance(node, ast.FunctionDef) and node.name == "_condition_texts_from_graph":
            selected_nodes.append(node)
        if isinstance(node, ast.ClassDef) and node.name == "CrossDocValidator":
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == "_parse_47a_requirements":
                    selected_nodes.append(item)
                    break

    module_ast = ast.Module(body=selected_nodes, type_ignores=[])
    ast.fix_missing_locations(module_ast)
    namespace: Dict[str, Any] = {
        "Any": Any,
        "Dict": Dict,
        "List": List,
        "re": re,
        "logger": _LoggerStub(),
        "BIN_REGEX_PATTERNS": [r"EXPORTER\s+BIN[:\s]*([A-Z0-9\\-]+)"],
        "TIN_REGEX_PATTERNS": [r"EXPORTER\s+TIN[:\s]*([A-Z0-9\\-]+)"],
    }
    exec(compile(module_ast, str(CROSSDOC_VALIDATOR_PATH), "exec"), namespace)
    return namespace


def test_parse_47a_requirements_prefers_requirements_graph_conditions() -> None:
    ns = _load_crossdoc_47a_symbols()
    parse_requirements = ns["_parse_47a_requirements"]

    requirements = parse_requirements(
        object(),
        {
            "additional_conditions": ["UNRELATED CONDITION TEXT"],
            "requirements_graph_v1": {
                "documentary_conditions": [
                    "BUYER PURCHASE ORDER NO. GBE-44592 MUST APPEAR ON ALL DOCUMENTS",
                ],
            },
        },
    )

    assert requirements["po_number"] == "GBE-44592"
    assert requirements["all_docs_require_po"] is True
    assert requirements["raw_conditions"] == [
        "BUYER PURCHASE ORDER NO. GBE-44592 MUST APPEAR ON ALL DOCUMENTS",
    ]


def test_parse_47a_requirements_falls_back_to_ambiguous_graph_conditions() -> None:
    ns = _load_crossdoc_47a_symbols()
    parse_requirements = ns["_parse_47a_requirements"]

    requirements = parse_requirements(
        object(),
        {
            "requirements_graph_v1": {
                "documentary_conditions": [],
                "ambiguous_conditions": [
                    "EXPORTER BIN: 000334455-0103 MUST APPEAR ON ALL DOCUMENTS",
                    "EXPORTER TIN: 545342112233 MUST APPEAR ON ALL DOCUMENTS",
                ],
            },
        },
    )

    assert requirements["bin_number"] == "000334455-0103"
    assert requirements["all_docs_require_bin"] is True
    assert requirements["tin_number"] == "545342112233"
    assert requirements["all_docs_require_tin"] is True
