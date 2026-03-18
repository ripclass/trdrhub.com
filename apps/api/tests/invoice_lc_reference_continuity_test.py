from __future__ import annotations

import ast
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional


ROOT = Path(__file__).resolve().parents[1]
LAUNCH_PIPELINE_PATH = ROOT / "app" / "services" / "extraction" / "launch_pipeline.py"
CROSSDOC_VALIDATOR_PATH = ROOT / "app" / "services" / "validation" / "crossdoc_validator.py"

INVOICE_SAMPLE_TEXT = (
    "COMMERCIAL INVOICE\n"
    "Invoice Number: DKEL/EXP/2026/114\n"
    "LC No: EXP2026BD001\n"
    "Buyer PO Number: GBE-44592\n"
)


def _load_shape_invoice_financial_payload():
    source = LAUNCH_PIPELINE_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)
    selected_nodes = [
        node
        for node in parsed.body
        if isinstance(node, ast.FunctionDef) and node.name == "_shape_invoice_financial_payload"
    ]
    module_ast = ast.Module(body=selected_nodes, type_ignores=[])
    ast.fix_missing_locations(module_ast)
    namespace: Dict[str, Any] = {
        "Any": Any,
        "Dict": Dict,
        "_extract_label_value": lambda raw_text, labels: "EXP2026BD001"
        if any("lc" in str(label).lower() or "credit" in str(label).lower() for label in labels)
        else None,
        "_extract_amount_value": lambda raw_text, labels: None,
        "_apply_canonical_normalization": lambda payload: payload,
    }
    exec(compile(module_ast, str(LAUNCH_PIPELINE_PATH), "exec"), namespace)
    return namespace["_shape_invoice_financial_payload"]


def _load_check_invoice_lc_reference():
    source = CROSSDOC_VALIDATOR_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)
    target = None
    for node in parsed.body:
        if isinstance(node, ast.ClassDef) and node.name == "CrossDocValidator":
            for child in node.body:
                if isinstance(child, ast.FunctionDef) and child.name == "_check_invoice_lc_reference":
                    target = child
                    break
        if target is not None:
            break
    if target is None:
        raise RuntimeError("Unable to locate _check_invoice_lc_reference")

    module_ast = ast.Module(body=[target], type_ignores=[])
    ast.fix_missing_locations(module_ast)

    class IssueSeverity(str, Enum):
        MINOR = "minor"
        MAJOR = "major"

    class DocumentType(str, Enum):
        INVOICE = "commercial_invoice"
        LC = "letter_of_credit"

    @dataclass
    class CrossDocIssue:
        rule_id: str
        title: str
        severity: IssueSeverity
        message: str
        expected: str
        found: str
        suggestion: str
        source_doc: DocumentType
        target_doc: DocumentType
        source_field: str
        target_field: str
        isbp_paragraph: Optional[str] = None
        source_value: Any = None
        target_value: Any = None

    namespace: Dict[str, Any] = {
        "Any": Any,
        "Dict": Dict,
        "Optional": Optional,
        "CrossDocIssue": CrossDocIssue,
        "IssueSeverity": IssueSeverity,
        "DocumentType": DocumentType,
    }
    exec(compile(module_ast, str(CROSSDOC_VALIDATOR_PATH), "exec"), namespace)
    return namespace["_check_invoice_lc_reference"]


class _StubValidator:
    @staticmethod
    def _normalize_text(value: Any) -> str:
        return str(value or "").strip()


def test_shape_invoice_financial_payload_preserves_lc_reference_aliases() -> None:
    shape_invoice_financial_payload = _load_shape_invoice_financial_payload()

    shaped = shape_invoice_financial_payload(
        {
            "invoice_number": "DKEL/EXP/2026/114",
            "lc_reference": "EXP2026BD001",
        },
        invoice_subtype="commercial_invoice",
        raw_text=INVOICE_SAMPLE_TEXT,
    )

    assert shaped["lc_reference"] == "EXP2026BD001"
    assert shaped["lc_number"] == "EXP2026BD001"


def test_crossdoc_invoice_lc_reference_check_passes_when_reference_is_preserved() -> None:
    shape_invoice_financial_payload = _load_shape_invoice_financial_payload()
    check_invoice_lc_reference = _load_check_invoice_lc_reference()

    shaped_invoice = shape_invoice_financial_payload(
        {
            "invoice_number": "DKEL/EXP/2026/114",
            "lc_reference": "EXP2026BD001",
        },
        invoice_subtype="commercial_invoice",
        raw_text=INVOICE_SAMPLE_TEXT,
    )

    issue = check_invoice_lc_reference(
        _StubValidator(),
        shaped_invoice,
        {"lc_number": "EXP2026BD001"},
    )

    assert issue is None
