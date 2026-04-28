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
    "swift_message": "SWIFT Message",
    "lc_application": "LC Application",
    "commercial_invoice": "Commercial Invoice",
    "proforma_invoice": "Proforma Invoice",
    "bill_of_lading": "Bill of Lading",
    "ocean_bill_of_lading": "Ocean Bill of Lading",
    "sea_waybill": "Sea Waybill",
    "air_waybill": "Air Waybill",
    "railway_consignment_note": "Railway Consignment Note",
    "road_transport_document": "Road Transport Document",
    "forwarder_certificate_of_receipt": "Forwarder's Certificate of Receipt",
    "shipping_company_certificate": "Shipping Company Certificate",
    "packing_list": "Packing List",
    "certificate_of_origin": "Certificate of Origin",
    "gsp_form_a": "GSP Form A",
    "eur1_movement_certificate": "EUR1 Movement Certificate",
    "customs_declaration": "Customs Declaration",
    "export_license": "Export License",
    "import_license": "Import License",
    "insurance_certificate": "Insurance Certificate",
    "insurance_policy": "Insurance Policy",
    "inspection_certificate": "Inspection Certificate",
    "pre_shipment_inspection": "Pre-Shipment Inspection",
    "quality_certificate": "Quality Certificate",
    "weight_certificate": "Weight Certificate",
    "weight_list": "Weight List",
    "measurement_certificate": "Measurement Certificate",
    "analysis_certificate": "Analysis Certificate",
    "lab_test_report": "Lab Test Report",
    "sgs_certificate": "SGS Certificate",
    "bureau_veritas_certificate": "Bureau Veritas Certificate",
    "intertek_certificate": "Intertek Certificate",
    "beneficiary_certificate": "Beneficiary Certificate",
    "manufacturer_certificate": "Manufacturer Certificate",
    "conformity_certificate": "Conformity Certificate",
    "non_manipulation_certificate": "Non-Manipulation Certificate",
    "phytosanitary_certificate": "Phytosanitary Certificate",
    "fumigation_certificate": "Fumigation Certificate",
    "health_certificate": "Health Certificate",
    "veterinary_certificate": "Veterinary Certificate",
    "sanitary_certificate": "Sanitary Certificate",
    "halal_certificate": "Halal Certificate",
    "kosher_certificate": "Kosher Certificate",
    "organic_certificate": "Organic Certificate",
    "warehouse_receipt": "Warehouse Receipt",
    "cargo_manifest": "Cargo Manifest",
    "duplicate_lc_candidate": "Duplicate LC Candidate",
    "lc_related_document": "LC-Related Document",
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


def _coerce_single_numeric_scalar(value: Any) -> Optional[Decimal]:
    """Return a numeric value only when the input is unambiguously singular."""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            return None
        matches = re.findall(r"\d[\d,]*(?:\.\d+)?", normalized)
        if len(matches) != 1:
            return None
        return _coerce_decimal(matches[0])
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

    def _required_document_types_from_graph(requirements_graph: Any) -> List[str]:
        if not isinstance(requirements_graph, dict):
            return []
        graph_types = [
            str(item or "").strip().lower()
            for item in (requirements_graph.get("required_document_types") or [])
            if str(item or "").strip()
        ]
        if graph_types:
            return graph_types
        derived: List[str] = []
        for entry in requirements_graph.get("required_documents") or []:
            if isinstance(entry, dict):
                token = (
                    entry.get("code")
                    or entry.get("document_code")
                    or entry.get("document_type")
                    or entry.get("type")
                )
            else:
                token = entry
            normalized = str(token or "").strip().lower()
            if normalized and normalized not in derived:
                derived.append(normalized)
        return derived

    def _has_uploaded_document(*doc_types: str) -> bool:
        return any(document_lookup.get(doc_type) for doc_type in doc_types)

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
    requirements_graph = (
        lc_context.get("requirements_graph_v1")
        or lc_context.get("requirementsGraphV1")
        or payload.get("requirements_graph_v1")
    )
    required_document_types = set(_required_document_types_from_graph(requirements_graph))
    lc_text = (payload.get("lc_text") or "").lower()
    insurance_required = bool(required_document_types & {"insurance_certificate", "insurance_policy"}) or "insurance" in lc_text
    insurance_presence = documents_presence.get("insurance_certificate", {})
    insurance_policy_presence = documents_presence.get("insurance_policy", {})
    insurance_present = (
        bool(insurance_presence.get("present"))
        or bool(insurance_policy_presence.get("present"))
        or _has_uploaded_document("insurance_certificate", "insurance_policy")
    )
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
    severity = _normalize_issue_severity(discrepancy)
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
    # Check multiple possible field names for suggestion
    suggestion = (
        discrepancy.get("suggestion") or 
        discrepancy.get("suggested_fix") or 
        _extract_expected_text(discrepancy.get("expected_outcome"), "invalid")
    )
    
    # If still no suggestion, provide context-aware default based on issue type
    if not suggestion:
        rule_id = (discrepancy.get("rule") or "").upper()
        if "BL" in rule_id or "BILL" in rule_id.replace("-", " "):
            suggestion = "Request an amended Bill of Lading from the carrier/shipping line to correct this discrepancy."
        elif "INVOICE" in rule_id or "AMOUNT" in rule_id:
            suggestion = "Issue an amended Commercial Invoice with corrected details matching the LC terms."
        elif "MISSING" in rule_id:
            suggestion = "Obtain and upload the missing document before bank submission."
        else:
            suggestion = "Review and correct the document to match LC requirements before bank submission."
    actual_text = _stringify_issue_value(discrepancy.get("actual") or discrepancy.get("found"))
    if semantic_payload and semantic_payload.get("found"):
        actual_text = semantic_payload.get("found")
    if semantic_payload and semantic_payload.get("documents"):
        document_label = semantic_payload["documents"][0]
    if semantic_payload and semantic_payload.get("suggested_fix"):
        suggestion = semantic_payload["suggested_fix"]
    # Prefer the persisted Discrepancy UUID injected by
    # finding_persistence.persist_findings_as_discrepancies — it's what
    # the /api/discrepancies/{id}/* endpoints expect. Fall back to the
    # legacy rule-name-based id when persistence didn't run (e.g.,
    # validation_session is None on stub paths).
    discrepancy_id = (
        discrepancy.get("__discrepancy_uuid")
        or discrepancy.get("rule")
        or f"issue-{index}"
    )

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
        "sourceSeverity": discrepancy.get("severity"),
        "priority": discrepancy.get("priority"),
        "documentName": document_label,
        "documentType": discrepancy.get("document_type"),
        "documentIds": discrepancy.get("document_ids") or discrepancy.get("documentIds"),
        "documentTypes": discrepancy.get("document_types") or discrepancy.get("documentTypes"),
        "documents": discrepancy.get("documents"),
        "document_names": discrepancy.get("document_names"),
        "expected": expected_text,
        "actual": actual_text,
        "suggestion": suggestion,
        "field": _extract_field_name(discrepancy),
        "ucp_reference": ucp_ref if ucp_ref else None,
        "isbp_reference": isbp_ref if isbp_ref else None,
        "ruleset_domain": discrepancy.get("ruleset_domain"),
        "rule_type": discrepancy.get("rule_type"),
        "consequence_class": discrepancy.get("consequence_class"),
        "execution_priority": discrepancy.get("execution_priority"),
        "parent_rule": discrepancy.get("parent_rule"),
        "expected_outcome": discrepancy.get("expected_outcome"),
        "conditions": discrepancy.get("conditions"),
        "overlap_keys": discrepancy.get("overlap_keys"),
    }


def _normalize_issue_severity(discrepancy: Dict[str, Any] | Optional[str]) -> str:
    if isinstance(discrepancy, dict):
        value = discrepancy.get("severity")
        if not value:
            return "minor"
        normalized = str(value).lower().strip()
        if normalized in {"critical", "high"}:
            return "critical"
        if normalized in {"major", "medium", "warn", "warning"}:
            return "major"
        if normalized in {"fail", "reject", "blocked"}:
            return "critical" if _is_blocking_temporal_discrepancy(discrepancy) else "major"
        return "minor"
    value = discrepancy
    if not value:
        return "minor"
    normalized = str(value).lower().strip()
    if normalized in {"critical", "high"}:
        return "critical"
    if normalized in {"major", "medium", "warn", "warning"}:
        return "major"
    if normalized in {"fail", "reject", "blocked"}:
        return "major"
    return "minor"


def _is_blocking_temporal_discrepancy(discrepancy: Dict[str, Any]) -> bool:
    title = str(discrepancy.get("title") or "").strip().lower()
    description = str(
        discrepancy.get("description")
        or discrepancy.get("message")
        or ""
    ).strip().lower()
    combined_text = f"{title} {description}"
    if "latest shipment date" in combined_text:
        return True
    if "shipment date" in combined_text and "later than" in combined_text:
        return True
    if "expiry" in combined_text and any(token in combined_text for token in ("after", "later than", "exceed")):
        return True

    for condition in discrepancy.get("conditions") or []:
        if not isinstance(condition, dict):
            continue
        condition_type = str(condition.get("type") or "").strip().lower()
        field = str(condition.get("field") or "").strip().lower()
        reference_field = str(
            condition.get("reference_field")
            or condition.get("referenceField")
            or ""
        ).strip().lower()
        computed_field = str(condition.get("computed_field") or "").strip().lower()
        joined = " ".join(part for part in (field, reference_field, computed_field) if part)
        if condition_type in {"date_comparison", "date_order"} and any(
            token in joined
            for token in (
                "latest_shipment",
                "shipment_date",
                "expiry_date",
                "presentation_period",
            )
        ):
            return True

    return False


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
        "severity": _normalize_issue_severity(discrepancy),
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


# =============================================================================
# PRICE VERIFICATION INTEGRATION (LCopilot)
# =============================================================================

async def run_price_verification_checks(
    payload: Dict[str, Any],
    include_tbml_checks: bool = True,
) -> List[Dict[str, Any]]:
    """
    Run price verification on goods extracted from invoices/LCs.
    
    This integrates Price Verify with LCopilot to automatically check
    if document prices align with market data.
    
    Args:
        payload: The validation payload with extracted data
        include_tbml_checks: Whether to flag potential TBML risks
        
    Returns:
        List of price-related issues in crossdoc format
    """
    issues: List[Dict[str, Any]] = []
    
    try:
        from app.services.price_verification import get_price_verification_service
    except ImportError:
        logger.warning("Price verification service not available")
        return issues
    
    # Extract invoice data
    invoice_context = payload.get("invoice") or {}
    lc_context = payload.get("lc") or {}
    document_lookup = _build_document_lookup(payload.get("documents"))
    
    # Get goods description to attempt commodity matching
    goods_description = (
        invoice_context.get("goods_description") or
        invoice_context.get("product_description") or
        lc_context.get("goods_description") or
        lc_context.get("description")
    )
    
    # Get price info
    invoice_amount = invoice_context.get("invoice_amount") or invoice_context.get("amount")
    if isinstance(invoice_amount, dict):
        invoice_amount = invoice_amount.get("value")
    invoice_amount_value = _coerce_single_numeric_scalar(invoice_amount)
    
    invoice_currency = (
        invoice_context.get("currency") or
        invoice_context.get("invoice_currency") or
        "USD"
    )
    
    # Try to get unit price and quantity
    unit_price = invoice_context.get("unit_price")
    quantity = invoice_context.get("quantity")
    unit_price_value = _coerce_single_numeric_scalar(unit_price)
    quantity_value = _coerce_single_numeric_scalar(quantity)
    
    # Skip if no goods description or price
    if not goods_description or not (invoice_amount_value or unit_price_value):
        logger.debug("No goods or price info for price verification")
        return issues

    if unit_price_value is None:
        logger.info(
            "Skipping price verification because unit price is not available as a safe scalar",
            extra={
                "raw_unit_price": unit_price,
                "raw_quantity": quantity,
                "has_invoice_amount": invoice_amount_value is not None,
            },
        )
        return issues
    
    try:
        service = get_price_verification_service()
        
        # Use resolve_commodity which NEVER fails - always returns usable data
        # This ensures price verification works even for unknown commodities
        hs_code = invoice_context.get("hs_code") or lc_context.get("hs_code")
        resolved = await service.resolve_commodity(goods_description, hs_code)
        
        # Get resolution metadata
        resolution_meta = resolved.get("_resolution", {})
        confidence = resolution_meta.get("confidence", 0.5)
        source = resolution_meta.get("source", "unknown")
        
        # Use the resolved commodity data
        commodity = {
            "code": resolved.get("code", "UNKNOWN"),
            "name": resolved.get("name", goods_description),
            "unit": resolved.get("unit", "kg"),
            "category": resolved.get("category", "general"),
        }
        
        # Log resolution details
        logger.info(f"Price verification: resolved '{goods_description[:30]}' as '{commodity['name']}' via {source} (confidence: {confidence:.2f})")
        
        # Determine price to verify
        price_to_verify = unit_price_value
        
        # Default unit if not specified
        unit = invoice_context.get("unit") or commodity.get("unit", "kg")
        
        # Run verification with resolved commodity
        result = await service.verify_price(
            commodity_input=goods_description,
            document_price=float(price_to_verify),
            document_unit=unit,
            document_currency=invoice_currency,
            quantity=float(quantity_value) if quantity_value is not None else None,
            document_type="invoice",
            hs_code=hs_code,
        )
        
        if not result.get("success"):
            return issues
        
        verdict = result.get("verdict", "pass")
        variance = result.get("variance", {})
        variance_percent = variance.get("percent", 0)
        risk = result.get("risk", {})
        
        # Warning-level market variance is advisory/TBML context, not a
        # documentary-compliance discrepancy for the SME-facing LC workflow.
        # Keep only hard price failures in the main findings path.
        if verdict == "warning":
            logger.info(
                "Suppressing warning-level price variance from LC findings",
                extra={
                    "commodity_code": commodity.get("code"),
                    "variance_percent": variance_percent,
                    "risk_level": risk.get("risk_level"),
                },
            )

        elif verdict == "fail":
            doc_names, doc_ids = _resolve_doc_references(
                document_lookup,
                ["commercial_invoice"],
                ["Commercial Invoice"],
            )
            
            direction = "above" if variance_percent > 0 else "below"
            risk_flags = risk.get("risk_flags", [])
            
            # TBML warning
            tbml_warning = ""
            if include_tbml_checks and "tbml_risk" in risk_flags:
                tbml_warning = " This significant variance may indicate Trade-Based Money Laundering (TBML) risk."
            
            issues.append({
                "rule": "PRICE-VERIFY-2",
                "title": "Significant Price Discrepancy",
                "passed": False,
                "severity": "major" if "tbml_risk" not in risk_flags else "critical",
                "message": f"Invoice price for {commodity.get('name')} is {abs(variance_percent):.1f}% {direction} market average.{tbml_warning}",
                "expected": f"Market price: ${result.get('market_price', {}).get('price', 0):,.2f}/{result.get('market_price', {}).get('unit', unit)}",
                "actual": f"Document price: ${float(price_to_verify):,.2f}/{unit}",
                "suggestion": "Verify price with supplier. Consider requesting justification for pricing deviation. Enhanced due diligence may be required.",
                "document_names": doc_names,
                "document_ids": doc_ids,
                "ruleset_domain": "icc.lcopilot.crossdoc",
                "_price_verify_details": {
                    "commodity_code": commodity.get("code"),
                    "variance_percent": variance_percent,
                    "risk_level": risk.get("risk_level"),
                    "risk_flags": risk_flags,
                    "tbml_alert": "tbml_risk" in risk_flags,
                },
            })
        
    except Exception as e:
        logger.error(f"Price verification integration error: {e}", exc_info=True)
    
    return issues

