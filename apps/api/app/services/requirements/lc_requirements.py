from __future__ import annotations

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
    requirement_conditions = [
        str(item).strip()
        for item in (
            payload.get("requirement_conditions")
            or lc_classification.get("requirement_conditions")
            or []
        )
        if str(item or "").strip()
    ]
    unmapped_requirements = [
        str(item).strip()
        for item in (
            payload.get("unmapped_requirements")
            or lc_classification.get("unmapped_requirements")
            or []
        )
        if str(item or "").strip()
    ]

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
