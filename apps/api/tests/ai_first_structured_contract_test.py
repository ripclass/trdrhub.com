import ast
import importlib.util
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

MODULE_PATH = Path(__file__).resolve().parents[1] / "app" / "services" / "extraction" / "ai_first_extractor.py"
spec = importlib.util.spec_from_file_location("ai_first_extractor_testmod", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
import sys
sys.modules["ai_first_extractor_testmod"] = mod
spec.loader.exec_module(mod)

AIFirstExtractor = mod.AIFirstExtractor
InvoiceAIFirstExtractor = mod.InvoiceAIFirstExtractor
BLAIFirstExtractor = mod.BLAIFirstExtractor
PackingListAIFirstExtractor = mod.PackingListAIFirstExtractor
CertificateOfOriginAIFirstExtractor = mod.CertificateOfOriginAIFirstExtractor
InsuranceCertificateAIFirstExtractor = mod.InsuranceCertificateAIFirstExtractor
ExtractedFieldResult = mod.ExtractedFieldResult
FieldStatus = mod.FieldStatus
_parse_llm_json_with_repair = mod._parse_llm_json_with_repair


@pytest.mark.parametrize(
    "extractor,doc_type,seed_field",
    [
        (AIFirstExtractor(), "letter_of_credit", "lc_number"),
        (InvoiceAIFirstExtractor(), "commercial_invoice", "invoice_number"),
        (BLAIFirstExtractor(), "bill_of_lading", "bl_number"),
        (PackingListAIFirstExtractor(), "packing_list", "packing_list_number"),
        (CertificateOfOriginAIFirstExtractor(), "certificate_of_origin", "certificate_number"),
        (InsuranceCertificateAIFirstExtractor(), "insurance_certificate", "certificate_number"),
    ],
)
def test_doc_type_contract_shape(extractor, doc_type, seed_field):
    fields = {
        seed_field: ExtractedFieldResult(
            name=seed_field,
            value="X-123",
            normalized_value="X-123",
            ai_confidence=0.9,
            validator_agrees=True,
            status=FieldStatus.TRUSTED,
        )
    }

    output = extractor._build_output(fields, ai_provider="test", doc_type=doc_type)

    assert "extracted_fields" in output
    assert "field_confidence" in output
    assert "field_evidence_spans" in output
    assert "missing_fields" in output
    assert "conflicts" in output

    schema = extractor.DOC_TYPE_FIELDS[doc_type]
    canonical = set(schema["required"] + schema["optional"])

    assert set(output["extracted_fields"].keys()) == canonical
    assert set(output["field_confidence"].keys()) == canonical
    assert set(output["field_evidence_spans"].keys()) == canonical
    assert seed_field not in output["missing_fields"]


@pytest.mark.asyncio
async def test_invalid_json_repair_path_runs_once():
    class FakeProvider:
        def __init__(self):
            self.calls = 0

        async def generate(self, prompt, system_prompt, temperature, max_tokens):
            self.calls += 1
            return '{"invoice_number":"INV-1"}', 10, 10

    provider = FakeProvider()
    malformed = '{"invoice_number":"INV-1",}'

    parsed = await _parse_llm_json_with_repair(provider, malformed)

    assert parsed == {"invoice_number": "INV-1"}
    assert provider.calls == 1


def test_non_canonical_keys_are_filtered():
    extractor = InvoiceAIFirstExtractor()
    ai_result = {
        "invoice_number": {"value": "INV-001", "confidence": 0.8},
        "random_extra": {"value": "SHOULD_NOT_PASS", "confidence": 0.8},
        "_meta": "ok",
    }

    filtered = extractor._filter_canonical_ai_result(ai_result, "commercial_invoice")

    assert "invoice_number" in filtered
    assert "random_extra" not in filtered
    assert "_meta" in filtered


def test_response_shaping_downgrades_success_when_parse_incomplete():
    module_path = Path(__file__).resolve().parents[1] / "app" / "routers" / "validation" / "response_shaping.py"
    source = module_path.read_text(encoding="utf-8")
    parsed = ast.parse(source)

    target_names = {"_normalize_doc_status", "build_document_extraction_v1", "summarize_document_statuses"}
    selected = [node for node in parsed.body if isinstance(node, ast.FunctionDef) and node.name in target_names]
    module_ast = ast.Module(body=selected, type_ignores=[])
    ast.fix_missing_locations(module_ast)

    namespace = {"Any": Any, "Dict": Dict, "List": List, "Optional": Optional}
    exec(compile(module_ast, str(module_path), "exec"), namespace)
    build_document_extraction_v1 = namespace["build_document_extraction_v1"]

    payload = build_document_extraction_v1(
        [
            {
                "document_id": "doc-1",
                "document_type": "certificate_of_origin",
                "filename": "COO.pdf",
                "status": "success",
                "extraction_status": "success",
                "parse_complete": False,
                "required_fields_found": 2,
                "required_fields_total": 6,
                "missing_required_fields": ["goods_description"],
            }
        ]
    )

    doc = payload["documents"][0]
    assert doc["status"] == "warning"
    assert doc["parse_complete"] is False
    assert payload["summary"]["status_counts"]["warning"] == 1
    assert payload["summary"]["status_counts"]["success"] == 0


def test_coo_parse_completeness_requires_minimum_fields_for_verified():
    module_path = Path(__file__).resolve().parents[1] / "app" / "routers" / "validate.py"
    source = module_path.read_text(encoding="utf-8")
    parsed = ast.parse(source)

    target_names = {
        "_is_populated_field_value",
        "_assess_required_field_completeness",
        "_assess_coo_parse_completeness",
    }
    selected = [node for node in parsed.body if isinstance(node, ast.FunctionDef) and node.name in target_names]
    module_ast = ast.Module(body=selected, type_ignores=[])
    ast.fix_missing_locations(module_ast)

    namespace = {"Any": Any, "Dict": Dict, "List": List, "Optional": Optional}
    exec(compile(module_ast, str(module_path), "exec"), namespace)
    assess = namespace["_assess_coo_parse_completeness"]

    shallow = assess({"country_of_origin": "Bangladesh", "certificate_number": "COO-1"})
    assert shallow["parse_complete"] is False
    assert shallow["required_found"] == 2

    complete = assess(
        {
            "country_of_origin": "Bangladesh",
            "certificate_number": "COO-1",
            "goods_description": "Cotton shirts",
        }
    )
    assert complete["parse_complete"] is True
    assert complete["required_found"] >= complete["min_required_for_verified"]
