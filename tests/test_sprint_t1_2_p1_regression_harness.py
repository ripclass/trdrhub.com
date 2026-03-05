from __future__ import annotations

import ast
import importlib.util
import json
import re
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple

from app.core.lc_types import LCType, VALID_LC_TYPES, normalize_lc_type


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "sprint_t1_2_p1"
VALIDATE_PATH = ROOT / "apps" / "api" / "app" / "routers" / "validate.py"
STRUCTURED_BUILDER_PATH = (
    ROOT / "apps" / "api" / "app" / "services" / "extraction" / "structured_lc_builder.py"
)


def _load_fixture(name: str) -> Dict[str, Any]:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def _load_module_from_path(module_name: str, module_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec and spec.loader, f"Unable to load module from {module_path}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_validate_functions(
    function_names: List[str],
    extra_globals: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    source = VALIDATE_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)

    selected: List[ast.FunctionDef] = []
    seen = set()
    for node in parsed.body:
        if isinstance(node, ast.FunctionDef) and node.name in function_names:
            selected.append(node)
            seen.add(node.name)

    missing = sorted(set(function_names) - seen)
    assert not missing, f"Missing function(s) in validate.py: {missing}"

    module_ast = ast.Module(body=selected, type_ignores=[])
    ast.fix_missing_locations(module_ast)

    namespace: Dict[str, Any] = {
        "Any": Any,
        "Dict": Dict,
        "List": List,
        "Optional": Optional,
        "Tuple": Tuple,
    }
    if extra_globals:
        namespace.update(extra_globals)

    exec(compile(module_ast, str(VALIDATE_PATH), "exec"), namespace)
    return {name: namespace[name] for name in function_names}


@dataclass
class _FakeStatus:
    value: str


@dataclass
class _FakeFieldResult:
    normalized_value: Any
    status: _FakeStatus
    ai_confidence: float
    validation_score: float
    final_confidence: float
    issues: List[str]


class _FakeTwoStageExtractor:
    def __init__(self, validated_fields: Dict[str, _FakeFieldResult], summary: Dict[str, Any]):
        self.validated_fields = validated_fields
        self.summary = summary
        self.last_ai_extraction: Optional[Dict[str, Any]] = None
        self.last_document_type: Optional[str] = None

    def process(self, ai_extraction: Dict[str, Any], document_type: str):
        self.last_ai_extraction = ai_extraction
        self.last_document_type = document_type
        return self.validated_fields

    def get_extraction_summary(self, _validated: Dict[str, _FakeFieldResult]):
        return self.summary


def test_partial_extraction_path_raw_text_only_and_partial_statuses():
    fixture = _load_fixture("partial_extraction_path.json")
    builder = _load_module_from_path("structured_builder_partial", STRUCTURED_BUILDER_PATH)

    structured = builder.build_unified_structured_result(
        session_documents=fixture["session_documents"],
        extractor_outputs=fixture["extractor_outputs"],
        legacy_payload=None,
    )["structured_result"]

    docs = structured["documents_structured"]
    assert [doc["extraction_status"] for doc in docs] == ["partial", "text_only"]
    assert structured["lc_structured"]["mt700"]["raw_text"] == fixture["extractor_outputs"]["mt700"]["raw_text"]


def test_two_stage_validation_summary_keeps_review_counters_for_unverified_flow():
    fixture = _load_fixture("two_stage_review_counter.json")

    validated_fields = {
        "number": _FakeFieldResult(
            normalized_value=fixture["normalized_values"]["number"],
            status=_FakeStatus("trusted"),
            ai_confidence=0.95,
            validation_score=1.0,
            final_confidence=0.95,
            issues=[],
        ),
        "amount": _FakeFieldResult(
            normalized_value=fixture["normalized_values"]["amount"],
            status=_FakeStatus("review"),
            ai_confidence=0.82,
            validation_score=0.6,
            final_confidence=0.71,
            issues=["manual_review_recommended"],
        ),
    }
    extractor = _FakeTwoStageExtractor(validated_fields, fixture["summary"])

    funcs = _load_validate_functions(
        ["_apply_two_stage_validation"],
        extra_globals={
            "_get_two_stage_extractor": lambda: extractor,
            "logger": SimpleNamespace(
                info=lambda *args, **kwargs: None,
                warning=lambda *args, **kwargs: None,
            ),
        },
    )
    apply_two_stage = funcs["_apply_two_stage_validation"]

    validated, summary = apply_two_stage(fixture["input_fields"], "lc", "LC_scan.pdf")

    assert extractor.last_ai_extraction is not None
    assert "raw_text" not in extractor.last_ai_extraction
    assert summary == fixture["summary"]
    assert validated["_two_stage_validation"]["summary"]["review"] == fixture["summary"]["review"]
    assert validated["raw_text"] == fixture["input_fields"]["raw_text"]


def test_issue_cards_present_in_structured_result_when_failures_exist():
    fixture = _load_fixture("issue_cards_failures.json")
    builder = _load_module_from_path("structured_builder_issues", STRUCTURED_BUILDER_PATH)

    structured = builder.build_unified_structured_result(
        session_documents=fixture["session_documents"],
        extractor_outputs=fixture["extractor_outputs"],
        legacy_payload=None,
    )["structured_result"]

    issues = structured["issues"]
    assert len(issues) == 2
    assert {issue["id"] for issue in issues} == {"RULE-41A", "RULE-44C"}
    assert all(issue.get("documents") for issue in issues)


def test_lc_type_override_handling_and_source_markers():
    fixture = _load_fixture("lc_override_source_markers.json")

    funcs = _load_validate_functions(
        ["_extract_lc_type_override"],
        extra_globals={
            "LCType": LCType,
            "VALID_LC_TYPES": VALID_LC_TYPES,
            "normalize_lc_type": normalize_lc_type,
        },
    )
    extract_override = funcs["_extract_lc_type_override"]

    for case in fixture["override_cases"]:
        assert extract_override(case["payload"]) == case["expected"]

    builder = _load_module_from_path("structured_builder_override", STRUCTURED_BUILDER_PATH)
    structured = builder.build_unified_structured_result(
        session_documents=fixture["session_documents"],
        extractor_outputs=fixture["extractor_outputs"],
        legacy_payload=None,
    )["structured_result"]

    assert structured["lc_type"] == "import"
    assert structured["lc_type_source"] == "override"
    assert abs(structured["lc_type_confidence"] - 0.88) < 1e-9


def test_document_composition_analytics_presence_and_consistency_markers():
    fixture = _load_fixture("document_composition_source_markers.json")
    source = VALIDATE_PATH.read_text(encoding="utf-8")

    for fragment in fixture["required_fragments"]:
        assert fragment in source

    assert re.search(
        r'structured_result\["analytics"\]\["document_composition"\]\s*=\s*composition_result\.get\("composition",\s*\{\}\)',
        source,
    )
    assert re.search(
        r'structured_result\["analytics"\]\["lc_only_mode"\]\s*=\s*composition_result\.get\("composition",\s*\{\}\)\.get\("lc_only_mode",\s*False\)',
        source,
    )
