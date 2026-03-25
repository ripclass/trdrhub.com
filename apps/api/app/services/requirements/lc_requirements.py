from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional, Set

from app.services.extraction.lc_taxonomy import build_lc_classification, normalize_required_documents
from app.services.facts.lc_facts import build_lc_fact_set


_LC_DOCUMENT_TYPES = {
    "letter_of_credit",
    "swift_message",
    "lc_application",
    "bank_guarantee",
    "standby_letter_of_credit",
}

_TRANSPORT_DOCUMENT_TYPES = {
    "bill_of_lading",
    "ocean_bill_of_lading",
    "charter_party_bill_of_lading",
    "house_bill_of_lading",
    "master_bill_of_lading",
    "sea_waybill",
    "air_waybill",
    "multimodal_transport_document",
    "combined_transport_document",
    "railway_consignment_note",
    "road_transport_document",
    "forwarders_certificate_of_receipt",
    "forwarder_certificate_of_receipt",
    "delivery_order",
    "mates_receipt",
    "shipping_company_certificate",
    "warehouse_receipt",
    "cargo_manifest",
    "courier_or_post_receipt_or_certificate_of_posting",
}
_INVOICE_EQUIVALENT_TYPES = {
    "commercial_invoice",
    "proforma_invoice",
    "draft_bill_of_exchange",
    "promissory_note",
    "payment_receipt",
    "debit_note",
    "credit_note",
}
_SEA_TRANSPORT_TYPES = {
    "bill_of_lading",
    "ocean_bill_of_lading",
    "charter_party_bill_of_lading",
    "house_bill_of_lading",
    "master_bill_of_lading",
    "sea_waybill",
    "mates_receipt",
    "shipping_company_certificate",
}
_AIR_TRANSPORT_TYPES = {"air_waybill"}
_INSURANCE_EQUIVALENT_TYPES = {"insurance_certificate", "insurance_policy"}
_LC_BASE_REQUIRED_FACT_FIELDS = {
    "lc_number",
    "issue_date",
    "expiry_date",
    "applicant",
    "beneficiary",
    "amount",
    "currency",
}
_LC_OPTIONAL_FACT_FIELDS = {
    "latest_shipment_date",
    "issuing_bank",
    "advising_bank",
    "port_of_loading",
    "port_of_discharge",
}
_ALL_DOCUMENTS_PATTERNS = (
    r"ALL\s+DOCUMENTS\s+MUST\s+SHOW",
    r"ALL\s+DOCUMENTS\s+SHOULD\s+SHOW",
    r"MUST\s+APPEAR\s+ON\s+ALL\s+DOCUMENTS",
    r"MUST\s+BE\s+SHOWN\s+ON\s+ALL\s+DOCUMENTS",
    r"SHOULD\s+APPEAR\s+ON\s+ALL\s+DOCUMENTS",
    r"ON\s+ALL\s+DOCUMENTS",
)
_PO_PATTERNS = (
    r"(?:BUYER\s+)?PURCHASE\s+ORDER\s+(?:NO\.?|NUMBER)[:\s]*([A-Z0-9\-]+)",
    r"P\.?O\.?\s+(?:NO\.?|NUMBER)[:\s]*([A-Z0-9\-]+)",
    r"PO[:\s]+([A-Z0-9\-]+)",
)
_BIN_REGEX_PATTERNS = (
    r"(?:EXPORTER\s+)?(?:B\.?I\.?N\.?|BIN|VAT\s*REG(?:ISTRATION)?|VAT\s*REG\.?|VAT\s*NO\.?|VAT\s*REG\s*NO\.?|VAT\s*REGISTRATION\s*NO\.?|VAT\s*REGISTRATION\s*NUMBER)\s*(?:NO\.?|NUMBER|#|:)?\s*([0-9][0-9\-]+)",
    r"(?:BUSINESS\s+IDENTIFICATION|BUSINESS\s+ID(?:ENTIFICATION)?)\s*(?:NO\.?|NUMBER|#|:)?\s*([0-9][0-9\-]+)",
)
_TIN_REGEX_PATTERNS = (
    r"(?:EXPORTER\s+)?(?:T\.?I\.?N\.?|TIN|TAX\s*ID(?:ENTIFICATION)?|TAXPAYER\s*ID|ETIN|E[\-\s]?TIN)\s*(?:NO\.?|NUMBER|#|:)?\s*([0-9][0-9\-]+)",
    r"(?:TAX\s+IDENTIFICATION|TAXPAYER\s+IDENTIFICATION)\s*(?:NO\.?|NUMBER|#|:)?\s*([0-9][0-9\-]+)",
)


def _document_type(document: Dict[str, Any]) -> str:
    return str(
        document.get("document_type")
        or document.get("documentType")
        or document.get("type")
        or ""
    ).strip().lower()


def _is_populated(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) > 0
    return True


def _fact_value_map(fact_graph: Dict[str, Any]) -> Dict[str, Any]:
    values: Dict[str, Any] = {}
    for fact in fact_graph.get("facts") or []:
        if not isinstance(fact, dict):
            continue
        field_name = str(fact.get("field_name") or "").strip().lower()
        if not field_name:
            continue
        normalized = fact.get("normalized_value")
        value = normalized if _is_populated(normalized) else fact.get("value")
        if _is_populated(value):
            values[field_name] = value
    return values


def _required_document_types(required_documents: Iterable[Dict[str, Any]]) -> List[str]:
    codes: List[str] = []
    for item in required_documents or []:
        if not isinstance(item, dict):
            continue
        code = str(item.get("code") or "").strip().lower()
        if code and code not in codes:
            codes.append(code)
    return codes


def _normalize_condition_texts(items: Iterable[Any]) -> List[str]:
    texts: List[str] = []
    for item in items or []:
        text = str(item or "").strip()
        if text:
            texts.append(text)
    return texts


def _build_condition_requirements(
    documentary_conditions: List[str],
    ambiguous_conditions: List[str],
) -> List[Dict[str, Any]]:
    requirements: List[Dict[str, Any]] = []
    seen: Set[tuple[str, str, str]] = set()
    condition_buckets = (
        ("documentary_conditions", documentary_conditions),
        ("ambiguous_conditions", ambiguous_conditions),
    )

    def _append_requirement(
        identifier_type: str,
        value: Optional[str],
        applies_to: str,
        source_text: str,
        source_bucket: str,
    ) -> None:
        token = str(value or "").strip()
        if not token:
            return
        key = (identifier_type, token, applies_to)
        if key in seen:
            return
        seen.add(key)
        requirements.append(
            {
                "requirement_type": "identifier_presence",
                "identifier_type": identifier_type,
                "value": token,
                "applies_to": applies_to,
                "source_text": source_text,
                "source_bucket": source_bucket,
            }
        )

    for source_bucket, condition_texts in condition_buckets:
        for text in condition_texts:
            normalized_text = str(text or "").strip()
            if not normalized_text:
                continue
            upper_text = normalized_text.upper()
            applies_to = (
                "all_documents"
                if any(re.search(pattern, upper_text) for pattern in _ALL_DOCUMENTS_PATTERNS)
                else "unspecified"
            )

            po_number = None
            for pattern in _PO_PATTERNS:
                match = re.search(pattern, upper_text)
                if match:
                    po_number = match.group(1).strip()
                    break
            _append_requirement("po_number", po_number, applies_to, normalized_text, source_bucket)

            bin_number = None
            for pattern in _BIN_REGEX_PATTERNS:
                match = re.search(pattern, upper_text)
                if match:
                    bin_number = match.group(1).strip()
                    break
            _append_requirement("bin_number", bin_number, applies_to, normalized_text, source_bucket)

            tin_number = None
            for pattern in _TIN_REGEX_PATTERNS:
                match = re.search(pattern, upper_text)
                if match:
                    tin_number = match.group(1).strip()
                    break
            _append_requirement("tin_number", tin_number, applies_to, normalized_text, source_bucket)

            lc_number_match = re.search(r"LC\s+(?:NO\.?|NUMBER)[:\s]*([A-Z0-9\-]+)", upper_text)
            _append_requirement(
                "lc_number",
                lc_number_match.group(1).strip() if lc_number_match else None,
                applies_to,
                normalized_text,
                source_bucket,
            )

    return requirements


def _required_fact_fields(required_document_types: Set[str], fact_values: Dict[str, Any]) -> List[str]:
    required = set(_LC_BASE_REQUIRED_FACT_FIELDS)
    for field_name in _LC_OPTIONAL_FACT_FIELDS:
        if _is_populated(fact_values.get(field_name)):
            required.add(field_name)

    if required_document_types & _TRANSPORT_DOCUMENT_TYPES:
        required.update({"port_of_loading", "port_of_discharge", "latest_shipment_date"})

    return sorted(required)


def build_lc_requirements_graph_v1(document_payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    payload = document_payload or {}
    document_type = _document_type(payload)
    if document_type not in _LC_DOCUMENT_TYPES:
        return None

    existing = payload.get("requirements_graph_v1") or payload.get("requirementsGraphV1")
    if isinstance(existing, dict):
        return existing

    lc_classification = payload.get("lc_classification")
    if not isinstance(lc_classification, dict):
        lc_classification = build_lc_classification(payload)

    required_documents = normalize_required_documents(
        {
            **payload,
            "lc_classification": lc_classification,
        }
    )
    if not required_documents and isinstance(lc_classification, dict):
        required_documents = [
            dict(item)
            for item in (lc_classification.get("required_documents") or [])
            if isinstance(item, dict)
        ]
    required_document_types = _required_document_types(required_documents)
    requirement_conditions = _normalize_condition_texts(
        payload.get("requirement_conditions")
        or lc_classification.get("requirement_conditions")
        or []
    )
    unmapped_requirements = _normalize_condition_texts(
        payload.get("unmapped_requirements")
        or lc_classification.get("unmapped_requirements")
        or []
    )
    condition_requirements = _build_condition_requirements(
        requirement_conditions,
        unmapped_requirements,
    )

    fact_graph = payload.get("fact_graph_v1") or payload.get("factGraphV1")
    if not isinstance(fact_graph, dict):
        fact_graph = build_lc_fact_set(payload)
    fact_values = _fact_value_map(fact_graph)

    core_terms = {
        field_name: fact_values.get(field_name)
        for field_name in (
            "lc_number",
            "issue_date",
            "expiry_date",
            "latest_shipment_date",
            "applicant",
            "beneficiary",
            "issuing_bank",
            "advising_bank",
            "amount",
            "currency",
            "port_of_loading",
            "port_of_discharge",
            "incoterm",
            "goods_description",
            "documents_required",
            "ucp_reference",
        )
        if _is_populated(fact_values.get(field_name))
    }

    return {
        "version": "requirements_graph_v1",
        "source_document_id": payload.get("document_id") or payload.get("documentId") or payload.get("id"),
        "source_document_type": document_type,
        "source_lane": payload.get("extraction_lane") or payload.get("extractionLane"),
        "workflow_orientation": lc_classification.get("workflow_orientation") if isinstance(lc_classification, dict) else None,
        "applicable_rules": lc_classification.get("applicable_rules") if isinstance(lc_classification, dict) else None,
        "required_documents": required_documents,
        "required_document_types": required_document_types,
        "documentary_conditions": requirement_conditions,
        "non_documentary_conditions": [],
        "ambiguous_conditions": unmapped_requirements,
        "condition_requirements": condition_requirements,
        "required_fact_fields": _required_fact_fields(set(required_document_types), fact_values),
        "core_terms": core_terms,
    }


def materialize_document_requirements_graph_v1(document: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not isinstance(document, dict):
        return None
    if _document_type(document) not in _LC_DOCUMENT_TYPES:
        return None

    existing = document.get("requirements_graph_v1") or document.get("requirementsGraphV1")
    if isinstance(existing, dict):
        document["requirements_graph_v1"] = existing
        document["requirementsGraphV1"] = existing
        return existing

    graph = build_lc_requirements_graph_v1(document)
    if not isinstance(graph, dict):
        return None
    document["requirements_graph_v1"] = graph
    document["requirementsGraphV1"] = graph
    return graph


def materialize_document_requirements_graphs_v1(documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    for document in documents or []:
        materialize_document_requirements_graph_v1(document)
    return documents


def resolve_case_requirements_graph_v1(documents: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    materialize_document_requirements_graphs_v1(documents)
    for document in documents or []:
        if not isinstance(document, dict):
            continue
        graph = document.get("requirements_graph_v1") or document.get("requirementsGraphV1")
        if isinstance(graph, dict):
            return graph
    return None


def is_lc_fact_required_by_graph(field_name: str, requirements_graph: Optional[Dict[str, Any]]) -> bool:
    if not isinstance(requirements_graph, dict):
        return True
    required_fields = requirements_graph.get("required_fact_fields")
    if not isinstance(required_fields, list) or not required_fields:
        return True
    normalized = str(field_name or "").strip().lower()
    return normalized in {
        str(item or "").strip().lower()
        for item in required_fields
        if str(item or "").strip()
    }


def is_document_type_required_by_graph(document_type: str, requirements_graph: Optional[Dict[str, Any]]) -> bool:
    if not isinstance(requirements_graph, dict):
        return True

    required_document_types = requirements_graph.get("required_document_types")
    if not isinstance(required_document_types, list) or not required_document_types:
        return True

    required = {
        str(item or "").strip().lower()
        for item in required_document_types
        if str(item or "").strip()
    }
    normalized = str(document_type or "").strip().lower()
    if not normalized:
        return True
    if normalized in required:
        return True
    if normalized in _INVOICE_EQUIVALENT_TYPES and required & _INVOICE_EQUIVALENT_TYPES:
        return True
    if normalized in _SEA_TRANSPORT_TYPES and required & _SEA_TRANSPORT_TYPES:
        return True
    if normalized in _AIR_TRANSPORT_TYPES and required & _AIR_TRANSPORT_TYPES:
        return True
    if normalized in _INSURANCE_EQUIVALENT_TYPES and required & _INSURANCE_EQUIVALENT_TYPES:
        return True
    return False
