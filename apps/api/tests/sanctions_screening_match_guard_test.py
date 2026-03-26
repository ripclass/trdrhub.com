from __future__ import annotations

import ast
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Tuple


ROOT = Path(__file__).resolve().parents[1]
SANCTIONS_SCREENING_PATH = ROOT / "app" / "services" / "sanctions_screening.py"


def _load_sanctions_symbols() -> Dict[str, Any]:
    source = SANCTIONS_SCREENING_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)
    selected_nodes: List[ast.AST] = []

    constant_names = {
        "LEGAL_SUFFIXES",
        "WORD_REPLACEMENTS",
        "TRANSLITERATION",
        "GENERIC_ENTITY_TOKENS",
    }
    function_names = {
        "normalize_name",
        "jaro_winkler_similarity",
        "token_set_ratio",
        "_distinctive_entity_tokens",
        "_has_meaningful_entity_overlap",
        "calculate_match_score",
    }

    for node in parsed.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in constant_names:
                    selected_nodes.append(node)
                    break
        if isinstance(node, ast.FunctionDef) and node.name in function_names:
            selected_nodes.append(node)

    module_ast = ast.Module(body=selected_nodes, type_ignores=[])
    ast.fix_missing_locations(module_ast)

    namespace: Dict[str, Any] = {
        "Any": Any,
        "Dict": Dict,
        "List": List,
        "Tuple": Tuple,
        "SequenceMatcher": SequenceMatcher,
        "re": __import__("re"),
    }
    exec(compile(module_ast, str(SANCTIONS_SCREENING_PATH), "exec"), namespace)
    return namespace


def test_medium_confidence_bank_name_collision_is_capped_below_match_threshold() -> None:
    symbols = _load_sanctions_symbols()
    calculate_match_score = symbols["calculate_match_score"]

    score, match_type, match_method = calculate_match_score(
        "Standard Chartered Bank",
        "Syria International Islamic Bank",
        [],
    )

    assert match_type == "fuzzy"
    assert match_method == "jaro_winkler"
    assert score < 70.0


def test_meaningful_shared_entity_tokens_still_allow_strong_fuzzy_matches() -> None:
    symbols = _load_sanctions_symbols()
    calculate_match_score = symbols["calculate_match_score"]

    score, match_type, match_method = calculate_match_score(
        "Global Trade Corp",
        "Global Trading Corp",
        [],
    )

    assert match_type == "fuzzy"
    assert match_method == "jaro_winkler"
    assert score >= 85.0

