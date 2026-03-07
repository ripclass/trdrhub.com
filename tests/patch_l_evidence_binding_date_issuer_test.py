from __future__ import annotations

import ast
import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVICES_DIR = ROOT / "apps" / "api" / "app" / "services"

if str(SERVICES_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICES_DIR))

from extraction_core.review_metadata import build_document_extraction  # noqa: E402


def _load_alias_normalization_module():
    module_path = ROOT / "apps" / "api" / "app" / "services" / "validation" / "alias_normalization.py"
    spec = importlib.util.spec_from_file_location("patch_l_alias_normalization", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


ALIAS_NORMALIZATION = _load_alias_normalization_module()
extract_direct_token_recovery = ALIAS_NORMALIZATION.extract_direct_token_recovery


def _field_map(doc):
    return {field.name: field for field in doc.fields}


def _load_apply_direct_token_recovery():
    path = ROOT / "apps" / "api" / "app" / "routers" / "validate.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    target = next(
        node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_apply_direct_token_recovery"
    )
    module = ast.Module(
        body=ast.parse("from typing import Any, Dict, Optional\nimport re\n").body + [target],
        type_ignores=[],
    )
    namespace: dict[str, object] = {"extract_direct_token_recovery": extract_direct_token_recovery}
    exec(compile(module, str(path), "exec"), namespace)
    return namespace["_apply_direct_token_recovery"]


APPLY_DIRECT_TOKEN_RECOVERY = _load_apply_direct_token_recovery()


def _artifacts(raw_text: str) -> dict[str, object]:
    return {
        "raw_text": raw_text,
        "selected_stage": "plaintext_native",
        "final_stage": "plaintext_native",
        "reason_codes": [],
        "stage_errors": {},
        "provider_attempts": [],
        "final_text_length": len(raw_text),
        "spans": [],
    }


def test_patch_l_lc_issue_date_evidence_binds_from_mt700_line():
    raw_text = (
        "27: 1/1\n"
        "20: EXP2026BD001\n"
        "31C: 260415\n"
        "42A: ICBKCNBJ400\n"
    )
    payload = {
        "raw_text": raw_text,
        "issue_date": "2026-04-15",
        "issuer": "ICBKCNBJ400",
        "extracted_fields": {
            "issue_date": "2026-04-15",
            "issuer": "ICBKCNBJ400",
        },
        "_field_details": {
            "issue_date": {"confidence": 0.98},
            "issuer": {"confidence": 0.98, "evidence_snippet": "42A: ICBKCNBJ400"},
        },
        "extraction_artifacts_v1": _artifacts(raw_text),
    }

    APPLY_DIRECT_TOKEN_RECOVERY(payload, payload["extraction_artifacts_v1"])

    assert "31C" in payload["_field_details"]["issue_date"]["evidence_snippet"]

    doc = build_document_extraction(
        {
            "id": "doc-lc-1",
            "document_type": "letter_of_credit",
            "extraction_confidence": 0.98,
            "extracted_fields": payload["extracted_fields"],
            "field_details": payload["_field_details"],
            "extraction_artifacts_v1": _artifacts(raw_text),
        }
    )
    fields = _field_map(doc)

    assert fields["issue_date"].evidence
    assert "31C" in fields["issue_date"].evidence[0].text_span
    assert doc.review_required is False


def test_patch_l_packing_multiline_issuer_and_weights_get_rebound_evidence():
    raw_text = (
        "PACKING LIST\n"
        "Reference: INV-2026-001\n"
        "L/C Number: EXP2026BD001\n"
        "Date: 2026-02-15\n"
        "Shipper:\n"
        "Bangladesh Export Ltd\n"
        "45 Export Zone, Chittagong, Bangladesh\n"
        "Consignee:\n"
        "Global Trade Corp\n"
        "Gross Weight: 2,500 KG\n"
        "Net Weight: 2,200 KG\n"
    )
    payload = {
        "raw_text": raw_text,
        "issue_date": "2026-02-15",
        "issuer": "Bangladesh Export Ltd, 45 Export Zone, Chittagong, Bangladesh",
        "gross_weight": "2,500 KG",
        "net_weight": "2,200 KG",
        "extracted_fields": {
            "issue_date": "2026-02-15",
            "issuer": "Bangladesh Export Ltd, 45 Export Zone, Chittagong, Bangladesh",
            "gross_weight": "2,500 KG",
            "net_weight": "2,200 KG",
        },
        "_field_details": {
            "issue_date": {"confidence": 0.75},
            "issuer": {"confidence": 0.75},
            "gross_weight": {"confidence": 0.75},
            "net_weight": {"confidence": 0.75},
        },
        "extraction_artifacts_v1": _artifacts(raw_text),
    }

    APPLY_DIRECT_TOKEN_RECOVERY(payload, payload["extraction_artifacts_v1"])

    assert "Shipper" in payload["_field_details"]["issuer"]["evidence_snippet"]
    assert payload["_field_details"]["issuer"]["confidence"] >= 0.86
    assert "Gross Weight" in payload["_field_details"]["gross_weight"]["evidence_snippet"]
    assert "Net Weight" in payload["_field_details"]["net_weight"]["evidence_snippet"]

    doc = build_document_extraction(
        {
            "id": "doc-pl-1",
            "document_type": "packing_list",
            "extraction_confidence": 0.75,
            "extracted_fields": payload["extracted_fields"],
            "field_details": payload["_field_details"],
            "extraction_artifacts_v1": _artifacts(raw_text),
        }
    )
    fields = _field_map(doc)

    assert fields["issuer"].evidence and "Shipper" in fields["issuer"].evidence[0].text_span
    assert fields["issue_date"].evidence and "Date: 2026-02-15" in fields["issue_date"].evidence[0].text_span
    assert fields["gross_weight"].confidence >= 0.8
    assert fields["net_weight"].confidence >= 0.8
    assert doc.review_required is False


def test_patch_l_plaintext_invoice_recovery_lifts_issue_date_issuer_and_invoice_number():
    raw_text = (
        "COMMERCIAL INVOICE\n"
        "Invoice Number: INV-2026-001\n"
        "Invoice Date: 2026-02-15\n"
        "SELLER:\n"
        "Bangladesh Export Ltd\n"
        "45 Export Zone, Chittagong, Bangladesh\n"
        "TOTAL AMOUNT: USD 125,000.00\n"
    )
    payload = {
        "raw_text": raw_text,
        "extracted_fields": {},
        "_field_details": {},
        "extraction_artifacts_v1": _artifacts(raw_text),
    }

    APPLY_DIRECT_TOKEN_RECOVERY(payload, payload["extraction_artifacts_v1"])

    assert payload["extracted_fields"]["invoice_number"] == "INV-2026-001"
    assert payload["extracted_fields"]["issue_date"] == "2026-02-15"
    assert payload["extracted_fields"]["issuer"] == "Bangladesh Export Ltd"
    assert payload["_field_details"]["invoice_number"]["confidence"] >= 0.9
    assert "Invoice Date" in payload["_field_details"]["issue_date"]["evidence_snippet"]


def test_patch_l_plaintext_bl_recovery_lifts_bl_number_issue_date_issuer_and_weights():
    raw_text = (
        "BILL OF LADING\n"
        "B/L No: BLA123456\n"
        "Carrier: Oceanic Shipping Line\n"
        "Shipment Date: 2026-09-24\n"
        "Gross Weight: 2,500 KG\n"
        "Net Weight: 2,200 KG\n"
    )

    recovered = extract_direct_token_recovery(raw_text, _artifacts(raw_text))

    assert recovered["bl_number"]["value"] == "BLA123456"
    assert recovered["issue_date"]["value"] == "2026-09-24"
    assert recovered["issuer"]["value"] == "Oceanic Shipping Line"
    assert recovered["gross_weight"]["value"] == "2,500 KG"
    assert recovered["net_weight"]["value"] == "2,200 KG"
    assert recovered["bl_number"]["confidence"] >= 0.9
