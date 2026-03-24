from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from .bl_facts import build_bl_fact_set
from .invoice_facts import build_invoice_fact_set


_INVOICE_DOCUMENT_TYPES = {"commercial_invoice", "proforma_invoice"}
_BL_DOCUMENT_TYPES = {
    "bill_of_lading",
    "ocean_bill_of_lading",
    "house_bill_of_lading",
    "master_bill_of_lading",
    "sea_waybill",
    "air_waybill",
    "multimodal_transport_document",
}
_RESOLVED_FACT_STATES = {"confirmed", "operator_confirmed"}
_INVOICE_VALIDATION_ALIASES = {
    "invoice_number": ("invoice_number", "invoice_no", "inv_no"),
    "invoice_date": ("invoice_date", "date", "issue_date"),
    "amount": ("amount", "invoice_amount", "total_amount", "total"),
    "currency": ("currency", "currency_code"),
    "seller": ("seller", "seller_name", "exporter", "beneficiary"),
    "buyer": ("buyer", "buyer_name", "importer", "applicant"),
}
_BL_VALIDATION_ALIASES = {
    "bl_number": ("bl_number", "bill_of_lading_number", "transport_document_reference", "transport_reference_number"),
    "shipper": ("shipper", "shipper_name", "exporter"),
    "consignee": ("consignee", "consignee_name", "importer", "applicant"),
    "port_of_loading": ("port_of_loading", "pol", "load_port", "loading_port"),
    "port_of_discharge": ("port_of_discharge", "pod", "discharge_port", "destination_port"),
    "on_board_date": ("on_board_date", "shipped_on_board_date", "shipment_date", "date_of_shipment", "date"),
}


def _document_type(document: Dict[str, Any]) -> str:
    return str(
        document.get("document_type")
        or document.get("documentType")
        or document.get("type")
        or ""
    ).strip().lower()


def materialize_document_fact_graph_v1(document: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not isinstance(document, dict):
        return None

    document_type = _document_type(document)
    if document_type in _INVOICE_DOCUMENT_TYPES:
        fact_graph = build_invoice_fact_set(document)
        document["fact_graph_v1"] = fact_graph
        document["factGraphV1"] = fact_graph
        return fact_graph
    if document_type in _BL_DOCUMENT_TYPES:
        fact_graph = build_bl_fact_set(document)
        document["fact_graph_v1"] = fact_graph
        document["factGraphV1"] = fact_graph
        return fact_graph

    existing = document.get("fact_graph_v1") or document.get("factGraphV1")
    if isinstance(existing, dict):
        document["fact_graph_v1"] = existing
        document["factGraphV1"] = existing
        return existing
    return None


def materialize_document_fact_graphs_v1(documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    for document in documents or []:
        if isinstance(document, dict):
            materialize_document_fact_graph_v1(document)
    return documents


def _iter_invoice_documents(documents: Iterable[Dict[str, Any]]) -> Iterable[Dict[str, Any]]:
    for document in documents or []:
        if not isinstance(document, dict):
            continue
        if _document_type(document) in _INVOICE_DOCUMENT_TYPES:
            yield document


def _iter_bl_documents(documents: Iterable[Dict[str, Any]]) -> Iterable[Dict[str, Any]]:
    for document in documents or []:
        if not isinstance(document, dict):
            continue
        if _document_type(document) in _BL_DOCUMENT_TYPES:
            yield document


def project_invoice_validation_context(
    base_context: Optional[Dict[str, Any]],
    *,
    document: Optional[Dict[str, Any]] = None,
    fact_graph: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    source_context = base_context if isinstance(base_context, dict) else {}
    projected: Dict[str, Any] = dict(source_context)

    if not projected and isinstance(document, dict):
        extracted_fields = document.get("extracted_fields")
        if isinstance(extracted_fields, dict):
            projected = {
                str(key): value
                for key, value in extracted_fields.items()
                if not str(key).startswith("_")
            }

    for aliases in _INVOICE_VALIDATION_ALIASES.values():
        for alias in aliases:
            projected.pop(alias, None)

    selected_fact_graph = fact_graph if isinstance(fact_graph, dict) else None
    if selected_fact_graph is None and isinstance(document, dict):
        selected_fact_graph = materialize_document_fact_graph_v1(document)
    if not isinstance(selected_fact_graph, dict):
        return projected

    for fact in selected_fact_graph.get("facts") or []:
        if not isinstance(fact, dict):
            continue
        field_name = str(fact.get("field_name") or "").strip().lower()
        aliases = _INVOICE_VALIDATION_ALIASES.get(field_name)
        if not aliases:
            continue
        verification_state = str(fact.get("verification_state") or "").strip().lower()
        if verification_state not in _RESOLVED_FACT_STATES:
            continue
        fact_value = fact.get("normalized_value")
        if fact_value in (None, ""):
            fact_value = fact.get("value")
        if fact_value in (None, ""):
            continue
        for alias in aliases:
            projected[alias] = fact_value

    projected["fact_graph_v1"] = selected_fact_graph
    projected["factGraphV1"] = selected_fact_graph
    return projected


def project_bl_validation_context(
    base_context: Optional[Dict[str, Any]],
    *,
    document: Optional[Dict[str, Any]] = None,
    fact_graph: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    source_context = base_context if isinstance(base_context, dict) else {}
    projected: Dict[str, Any] = dict(source_context)

    if not projected and isinstance(document, dict):
        extracted_fields = document.get("extracted_fields")
        if isinstance(extracted_fields, dict):
            projected = {
                str(key): value
                for key, value in extracted_fields.items()
                if not str(key).startswith("_")
            }

    for aliases in _BL_VALIDATION_ALIASES.values():
        for alias in aliases:
            projected.pop(alias, None)

    selected_fact_graph = fact_graph if isinstance(fact_graph, dict) else None
    if selected_fact_graph is None and isinstance(document, dict):
        selected_fact_graph = materialize_document_fact_graph_v1(document)
    if not isinstance(selected_fact_graph, dict):
        return projected

    for fact in selected_fact_graph.get("facts") or []:
        if not isinstance(fact, dict):
            continue
        field_name = str(fact.get("field_name") or "").strip().lower()
        aliases = _BL_VALIDATION_ALIASES.get(field_name)
        if not aliases:
            continue
        verification_state = str(fact.get("verification_state") or "").strip().lower()
        if verification_state not in _RESOLVED_FACT_STATES:
            continue
        fact_value = fact.get("normalized_value")
        if fact_value in (None, ""):
            fact_value = fact.get("value")
        if fact_value in (None, ""):
            continue
        for alias in aliases:
            projected[alias] = fact_value

    projected["fact_graph_v1"] = selected_fact_graph
    projected["factGraphV1"] = selected_fact_graph
    return projected


def apply_invoice_fact_graph_to_validation_inputs(
    payload: Dict[str, Any],
    extracted_context: Dict[str, Any],
) -> Dict[str, Any]:
    payload_docs = payload.get("documents") if isinstance(payload, dict) else None
    context_docs = extracted_context.get("documents") if isinstance(extracted_context, dict) else None
    invoice_document = next(
        _iter_invoice_documents(payload_docs if isinstance(payload_docs, list) else context_docs if isinstance(context_docs, list) else []),
        None,
    )

    payload_invoice = payload.get("invoice") if isinstance(payload, dict) and isinstance(payload.get("invoice"), dict) else {}
    context_invoice = (
        extracted_context.get("invoice")
        if isinstance(extracted_context, dict) and isinstance(extracted_context.get("invoice"), dict)
        else {}
    )
    base_invoice_context = payload_invoice or context_invoice
    fact_graph = None
    if isinstance(invoice_document, dict):
        fact_graph = invoice_document.get("fact_graph_v1") or invoice_document.get("factGraphV1")

    projected = project_invoice_validation_context(
        base_invoice_context,
        document=invoice_document,
        fact_graph=fact_graph,
    )

    if isinstance(payload, dict):
        payload["invoice"] = projected
    if isinstance(extracted_context, dict):
        extracted_context["invoice"] = projected
    return projected


def apply_bl_fact_graph_to_validation_inputs(
    payload: Dict[str, Any],
    extracted_context: Dict[str, Any],
) -> Dict[str, Any]:
    payload_docs = payload.get("documents") if isinstance(payload, dict) else None
    context_docs = extracted_context.get("documents") if isinstance(extracted_context, dict) else None
    bl_document = next(
        _iter_bl_documents(payload_docs if isinstance(payload_docs, list) else context_docs if isinstance(context_docs, list) else []),
        None,
    )

    payload_bl = payload.get("bill_of_lading") if isinstance(payload, dict) and isinstance(payload.get("bill_of_lading"), dict) else {}
    context_bl = (
        extracted_context.get("bill_of_lading")
        if isinstance(extracted_context, dict) and isinstance(extracted_context.get("bill_of_lading"), dict)
        else {}
    )
    base_bl_context = payload_bl or context_bl
    fact_graph = None
    if isinstance(bl_document, dict):
        fact_graph = bl_document.get("fact_graph_v1") or bl_document.get("factGraphV1")

    projected = project_bl_validation_context(
        base_bl_context,
        document=bl_document,
        fact_graph=fact_graph,
    )

    if isinstance(payload, dict):
        payload["bill_of_lading"] = projected
    if isinstance(extracted_context, dict):
        extracted_context["bill_of_lading"] = projected
    return projected
