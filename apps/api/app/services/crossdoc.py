"""
Cross-document validation helpers shared between the validation router and tests.
"""

from decimal import Decimal, InvalidOperation
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

DEFAULT_LABELS = {
    "letter_of_credit": "Letter of Credit",
    "commercial_invoice": "Commercial Invoice",
    "bill_of_lading": "Bill of Lading",
    "packing_list": "Packing List",
    "insurance_certificate": "Insurance Certificate",
    "certificate_of_origin": "Certificate of Origin",
    "supporting_document": "Supporting Document",
}


def _coerce_decimal(value: Any) -> Optional[Decimal]:
    if value is None:
        return None
    try:
        if isinstance(value, Decimal):
            return value
        if isinstance(value, (int, float)):
            return Decimal(str(value))
        if isinstance(value, str):
            normalized = value.replace(",", "").strip()
            if not normalized:
                return None
            return Decimal(normalized)
    except InvalidOperation:
        return None
    return None


def run_cross_document_checks(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Perform deterministic cross-document checks to create SME-friendly discrepancies.
    Returns list of result dicts in the same shape as JSON rule outcomes.
    """
    issues: List[Dict[str, Any]] = []
    lc_context = payload.get("lc") or {}
    invoice_context = payload.get("invoice") or {}
    bl_context = payload.get("bill_of_lading") or {}
    documents_presence = payload.get("documents_presence") or {}
    document_lookup = _build_document_lookup(payload.get("documents"))

    def _clean_text(value: Optional[str]) -> str:
        if not value:
            return ""
        normalized = re.sub(r"\s+", " ", value).strip()
        return normalized

    def _text_signature(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", value.lower())

    # 1. Goods description mismatch (LC vs Commercial Invoice)
    lc_goods = _clean_text(lc_context.get("goods_description") or lc_context.get("description"))
    invoice_goods = _clean_text(
        invoice_context.get("product_description") or invoice_context.get("goods_description")
    )
    if lc_goods and invoice_goods and _text_signature(lc_goods) != _text_signature(invoice_goods):
        doc_names, doc_ids = _resolve_doc_references(
            document_lookup,
            ["letter_of_credit", "commercial_invoice"],
            ["Letter of Credit", "Commercial Invoice"],
        )
        issues.append({
            "rule": "CROSSDOC-GOODS-1",
            "title": "Product Description Variation",
            "passed": False,
            "severity": "major",
            "message": "Product description in the commercial invoice differs from LC terms and may trigger a bank discrepancy.",
            "expected": lc_goods,
            "actual": invoice_goods,
            "documents": doc_names,
            "document_names": doc_names,
            "document_ids": doc_ids,
            "display_card": True,
            "ruleset_domain": "icc.lcopilot.crossdoc",
            "not_applicable": False,
        })

    # 2. Invoice amount exceeds LC amount + tolerance (deterministic version for clearer messaging)
    invoice_amount = _coerce_decimal(invoice_context.get("invoice_amount"))
    invoice_limit = _coerce_decimal(payload.get("invoice_amount_limit"))
    tolerance_value = _coerce_decimal(payload.get("invoice_amount_tolerance_value"))
    if invoice_amount is not None and invoice_limit is not None and invoice_amount > invoice_limit:
        lc_amount = _coerce_decimal(((lc_context.get("amount") or {}).get("value")))
        tolerance_display = f"{tolerance_value:,.2f} USD" if tolerance_value is not None else "tolerance limit"
        expected_amount_msg = (
            f"<= {invoice_limit:,.2f} USD (LC amount {lc_amount:,.2f} + allowed {tolerance_display})"
            if lc_amount is not None and tolerance_value is not None
            else f"<= {invoice_limit:,.2f} USD"
        )
        doc_names, doc_ids = _resolve_doc_references(
            document_lookup,
            ["commercial_invoice", "letter_of_credit"],
            ["Commercial Invoice", "Letter of Credit"],
        )
        issues.append({
            "rule": "CROSSDOC-AMOUNT-1",
            "title": "Invoice Amount Exceeds LC + Tolerance",
            "passed": False,
            "severity": "warning",
            "message": (
                "The invoiced amount exceeds the LC face value plus the allowed tolerance, "
                "which may lead to refusal."
            ),
            "expected": expected_amount_msg,
            "actual": f"{invoice_amount:,.2f} USD",
            "documents": doc_names,
            "document_names": doc_names,
            "document_ids": doc_ids,
            "display_card": True,
            "ruleset_domain": "icc.lcopilot.crossdoc",
            "not_applicable": False,
        })

    # 3. Insurance certificate missing when LC references insurance
    lc_text = (payload.get("lc_text") or "").lower()
    insurance_required = "insurance" in lc_text
    insurance_presence = documents_presence.get("insurance_certificate", {})
    insurance_present = insurance_presence.get("present", False)
    if insurance_required and not insurance_present:
        doc_names, doc_ids = _resolve_doc_references(
            document_lookup,
            ["insurance_certificate"],
            ["Insurance Certificate"],
        )
        if not doc_names:
            doc_names = ["Letter of Credit"]
        issues.append({
            "rule": "CROSSDOC-DOC-1",
            "title": "Insurance Certificate Missing",
            "passed": False,
            "severity": "major",
            "message": "The LC references insurance coverage, but no insurance certificate was uploaded with the presentation.",
            "expected": "Upload an insurance certificate that matches the LC requirements.",
            "actual": "No insurance certificate detected among the uploaded documents.",
            "documents": doc_names,
            "document_names": doc_names,
            "document_ids": doc_ids,
            "display_card": True,
            "ruleset_domain": "icc.lcopilot.crossdoc",
            "not_applicable": False,
        })

    # 4. Bill of Lading shipper/consignee vs LC parties (deterministic mirror of JSON rule)
    lc_applicant = _clean_text((lc_context.get("applicant") or {}).get("name") if isinstance(lc_context.get("applicant"), dict) else lc_context.get("applicant"))
    bl_shipper = _clean_text(bl_context.get("shipper"))
    if lc_applicant and bl_shipper and _text_signature(lc_applicant) != _text_signature(bl_shipper):
        doc_names, doc_ids = _resolve_doc_references(
            document_lookup,
            ["bill_of_lading", "letter_of_credit"],
            ["Bill of Lading", "Letter of Credit"],
        )
        issues.append({
            "rule": "CROSSDOC-BL-1",
            "title": "B/L Shipper differs from LC Applicant",
            "passed": False,
            "severity": "major",
            "message": "The shipper shown on the Bill of Lading does not match the applicant named in the LC.",
            "expected": lc_applicant,
            "actual": bl_shipper,
            "documents": doc_names,
            "document_names": doc_names,
            "document_ids": doc_ids,
            "display_card": True,
            "ruleset_domain": "icc.lcopilot.crossdoc",
            "not_applicable": False,
        })

    lc_beneficiary = _clean_text((lc_context.get("beneficiary") or {}).get("name") if isinstance(lc_context.get("beneficiary"), dict) else lc_context.get("beneficiary"))
    bl_consignee = _clean_text(bl_context.get("consignee"))
    if lc_beneficiary and bl_consignee and _text_signature(lc_beneficiary) != _text_signature(bl_consignee):
        doc_names, doc_ids = _resolve_doc_references(
            document_lookup,
            ["bill_of_lading", "letter_of_credit"],
            ["Bill of Lading", "Letter of Credit"],
        )
        issues.append({
            "rule": "CROSSDOC-BL-2",
            "title": "B/L Consignee differs from LC Beneficiary",
            "passed": False,
            "severity": "major",
            "message": "The consignee on the Bill of Lading is different from the LC beneficiary, which may cause the bank to refuse documents.",
            "expected": lc_beneficiary,
            "actual": bl_consignee,
            "documents": doc_names,
            "document_names": doc_names,
            "document_ids": doc_ids,
            "display_card": True,
            "ruleset_domain": "icc.lcopilot.crossdoc",
            "not_applicable": False,
        })

    return issues


def build_issue_cards(discrepancies: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Partition discrepancies into user-facing issue cards vs technical references.
    """
    issue_cards: List[Dict[str, Any]] = []
    references: List[Dict[str, Any]] = []

    for idx, item in enumerate(discrepancies):
        domain = (item.get("ruleset_domain") or "").lower()
        display_card = bool(item.get("display_card"))

        if domain == "icc.lcopilot.crossdoc" or display_card:
            issue_cards.append(_format_issue_card(item, idx))
        else:
            references.append(_format_reference_issue(item))

    return issue_cards, references


def _format_issue_card(discrepancy: Dict[str, Any], index: int) -> Dict[str, Any]:
    severity = _normalize_issue_severity(discrepancy.get("severity"))
    semantic_payload = None
    semantic_list = discrepancy.get("semantic_differences")
    if isinstance(semantic_list, list) and semantic_list:
        semantic_payload = semantic_list[0]
    document_label = _infer_primary_document(discrepancy)
    expected_text = _stringify_issue_value(
        discrepancy.get("expected")
        or _extract_expected_text(discrepancy.get("expected_outcome"), "valid")
    )
    if semantic_payload and semantic_payload.get("expected"):
        expected_text = semantic_payload.get("expected")
    suggestion = discrepancy.get("suggestion") or _extract_expected_text(
        discrepancy.get("expected_outcome"), "invalid"
    ) or "Align the document with the LC requirement."
    actual_text = _stringify_issue_value(discrepancy.get("actual") or discrepancy.get("found"))
    if semantic_payload and semantic_payload.get("found"):
        actual_text = semantic_payload.get("found")
    if semantic_payload and semantic_payload.get("documents"):
        document_label = semantic_payload["documents"][0]
    if semantic_payload and semantic_payload.get("suggested_fix"):
        suggestion = semantic_payload["suggested_fix"]
    discrepancy_id = discrepancy.get("rule") or f"issue-{index}"

    # Extract UCP/ISBP references - check multiple possible field names
    ucp_ref = (
        discrepancy.get("ucp_reference") or 
        discrepancy.get("ucp_article") or 
        ""
    )
    isbp_ref = (
        discrepancy.get("isbp_reference") or 
        discrepancy.get("isbp_paragraph") or 
        ""
    )

    return {
        "id": str(discrepancy_id),
        "rule": discrepancy.get("rule"),
        "title": discrepancy.get("title") or discrepancy.get("rule") or "Review Required",
        "description": discrepancy.get("message") or discrepancy.get("description") or "",
        "severity": severity,
        "documentName": document_label,
        "documentType": discrepancy.get("document_type"),
        "expected": expected_text,
        "actual": actual_text,
        "suggestion": suggestion,
        "field": _extract_field_name(discrepancy),
        "ucp_reference": ucp_ref if ucp_ref else None,
        "isbp_reference": isbp_ref if isbp_ref else None,
    }


def _normalize_issue_severity(value: Optional[str]) -> str:
    if not value:
        return "minor"
    normalized = value.lower()
    if normalized in {"critical", "high"}:
        return "critical"
    if normalized in {"major", "medium", "warn", "warning"}:
        return "major"
    return "minor"


def _infer_primary_document(discrepancy: Dict[str, Any]) -> str:
    document_names = discrepancy.get("document_names")
    if isinstance(document_names, list) and document_names:
        return document_names[0]
    documents = discrepancy.get("documents")
    if isinstance(documents, list) and documents:
        return documents[0]
    if discrepancy.get("document_name"):
        return discrepancy["document_name"]
    if discrepancy.get("document"):
        return discrepancy["document"]
    return "Supporting Document"


def _stringify_issue_value(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, (list, tuple)):
        return ", ".join(str(item) for item in value if item is not None)
    return str(value)


def _extract_expected_text(expected_outcome: Any, key: str) -> Optional[str]:
    if isinstance(expected_outcome, dict):
        target = expected_outcome.get(key)
        if isinstance(target, dict):
            return target.get("message") or target.get("text")
        if isinstance(target, str):
            return target
    return None


def _extract_field_name(discrepancy: Dict[str, Any]) -> Optional[str]:
    if discrepancy.get("field"):
        return discrepancy["field"]
    if discrepancy.get("field_name"):
        return discrepancy["field_name"]
    metadata = discrepancy.get("metadata") or {}
    if isinstance(metadata, dict):
        return metadata.get("field")
    return None


def _format_reference_issue(discrepancy: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "rule": discrepancy.get("rule"),
        "title": discrepancy.get("title") or discrepancy.get("rule") or "",
        "description": discrepancy.get("message") or discrepancy.get("description") or "",
        "severity": discrepancy.get("severity", "minor"),
        "documents": discrepancy.get("documents", []),
        "document_names": discrepancy.get("document_names", []),
        "document_ids": discrepancy.get("document_ids", []),
        "expected": discrepancy.get("expected"),
        "actual": discrepancy.get("actual") or discrepancy.get("found"),
        "suggestion": discrepancy.get("suggestion"),
        "ruleset_domain": discrepancy.get("ruleset_domain"),
    }


# Backwards compatibility for modules still using the legacy private names
_run_cross_document_checks = run_cross_document_checks
_build_issue_cards = build_issue_cards


def _build_document_lookup(documents: Optional[List[Dict[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
    lookup: Dict[str, List[Dict[str, Any]]] = {}
    if not documents:
        return lookup
    for doc in documents:
        doc_type = doc.get("document_type") or doc.get("type")
        if not doc_type:
            continue
        entry = {
            "name": doc.get("filename") or doc.get("name"),
            "id": doc.get("id"),
            "type": doc_type,
        }
        lookup.setdefault(doc_type, []).append(entry)
    return lookup


def _resolve_doc_references(
    lookup: Dict[str, List[Dict[str, Any]]],
    canonical_types: List[str],
    fallback_labels: List[str],
) -> Tuple[List[str], List[str]]:
    names: List[str] = []
    ids: List[str] = []
    for doc_type in canonical_types:
        entries = lookup.get(doc_type) or []
        for entry in entries:
            label = entry.get("name") or DEFAULT_LABELS.get(doc_type, doc_type.replace("_", " ").title())
            names.append(label)
            if entry.get("id"):
                ids.append(entry["id"])
    if not names:
        names = fallback_labels
    return names, ids

