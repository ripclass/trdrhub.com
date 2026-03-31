from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any, Dict


ROOT = Path(__file__).resolve().parents[1]
VALIDATION_EXECUTION_PATH = ROOT / "app" / "routers" / "validation" / "validation_execution.py"


def _load_symbols() -> Dict[str, Any]:
    source = VALIDATION_EXECUTION_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)
    selected_nodes: list[ast.AST] = []

    for node in parsed.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in {
                    "_ICC_RULEBOOK_PREFIXES",
                    "_ICC_RULE_ID_PATTERN",
                }:
                    selected_nodes.append(node)
                    break
        elif isinstance(node, ast.FunctionDef) and node.name in {
            "_parse_icc_rule_identity",
            "_suppress_broad_icc_umbrella_rules",
        }:
            selected_nodes.append(node)

    module_ast = ast.Module(body=selected_nodes, type_ignores=[])
    ast.fix_missing_locations(module_ast)
    namespace: Dict[str, Any] = {
        "Any": Any,
        "Dict": Dict,
        "Optional": __import__("typing").Optional,
        "re": re,
    }
    exec(compile(module_ast, str(VALIDATION_EXECUTION_PATH), "exec"), namespace)
    return namespace


def test_validation_execution_prefers_specific_ucp_letter_rule_over_umbrella_article() -> None:
    fn = _load_symbols()["_suppress_broad_icc_umbrella_rules"]

    filtered = fn(
        [
            {"rule": "UCP600-28", "ruleset_domain": "icc.ucp600", "title": "Insurance Document and Coverage"},
            {"rule": "UCP600-28A", "ruleset_domain": "icc.ucp600", "title": "Insurance Originals Match LC Requirement"},
        ]
    )

    assert [issue["rule"] for issue in filtered] == ["UCP600-28A"]


def test_validation_execution_keeps_umbrella_icc_rule_without_specific_letter_failure() -> None:
    fn = _load_symbols()["_suppress_broad_icc_umbrella_rules"]

    issues = [
        {"rule": "UCP600-28", "ruleset_domain": "icc.ucp600", "title": "Insurance Document and Coverage"},
    ]

    assert fn(issues) == issues


def test_validation_execution_prefers_specific_isbp_letter_rule_over_umbrella_article() -> None:
    fn = _load_symbols()["_suppress_broad_icc_umbrella_rules"]

    filtered = fn(
        [
            {"rule": "ISBP745-A14", "ruleset_domain": "icc.isbp745", "title": "Invoice Requirements"},
            {"rule": "ISBP745-A14B", "ruleset_domain": "icc.isbp745", "title": "Invoice Currency Match"},
        ]
    )

    assert [issue["rule"] for issue in filtered] == ["ISBP745-A14B"]
