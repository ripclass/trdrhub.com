from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from .bl_facts import build_bl_fact_set
from .coo_facts import build_coo_fact_set
from .insurance_facts import build_insurance_fact_set
from .inspection_facts import build_inspection_fact_set
from .invoice_facts import build_invoice_fact_set
from .packing_list_facts import build_packing_list_fact_set
from .supporting_facts import build_supporting_fact_set


_INVOICE_DOCUMENT_TYPES = {
    "commercial_invoice",
    "proforma_invoice",
    "draft_bill_of_exchange",
    "promissory_note",
    "payment_receipt",
    "debit_note",
    "credit_note",
}
_BL_DOCUMENT_TYPES = {
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
_PACKING_LIST_DOCUMENT_TYPES = {"packing_list"}
_COO_DOCUMENT_TYPES = {
    "certificate_of_origin",
    "gsp_form_a",
    "eur1_movement_certificate",
    "customs_declaration",
    "export_license",
    "import_license",
    "phytosanitary_certificate",
    "fumigation_certificate",
    "health_certificate",
    "veterinary_certificate",
    "sanitary_certificate",
    "cites_permit",
    "radiation_certificate",
}
_INSURANCE_DOCUMENT_TYPES = {
    "insurance_certificate",
    "insurance_policy",
    "beneficiary_certificate",
    "beneficiary_statement",
    "manufacturer_certificate",
    "manufacturers_certificate",
    "conformity_certificate",
    "certificate_of_conformity",
    "non_manipulation_certificate",
    "halal_certificate",
    "kosher_certificate",
    "organic_certificate",
}
_INSPECTION_DOCUMENT_TYPES = {
    "inspection_certificate",
    "pre_shipment_inspection",
    "quality_certificate",
    "weight_certificate",
    "weight_list",
    "measurement_certificate",
    "analysis_certificate",
    "lab_test_report",
    "sgs_certificate",
    "bureau_veritas_certificate",
    "intertek_certificate",
}
_SUPPORTING_DOCUMENT_TYPES = {
    "shipment_advice",
    "delivery_note",
    "other_specified_document",
    "supporting_document",
}
_RESOLVED_FACT_STATES = {"confirmed", "operator_confirmed"}
_INVOICE_VALIDATION_ALIASES = {
    "invoice_number": ("invoice_number", "invoice_no", "inv_no"),
    "instrument_number": ("instrument_number", "invoice_number", "invoice_no", "inv_no"),
    "receipt_number": ("receipt_number", "receipt_no", "receipt_reference"),
    "invoice_date": ("invoice_date", "date", "issue_date"),
    "amount": ("amount", "invoice_amount", "total_amount", "total"),
    "currency": ("currency", "currency_code"),
    "seller": ("seller", "seller_name", "exporter", "beneficiary"),
    "buyer": ("buyer", "buyer_name", "importer", "applicant"),
}
_BL_VALIDATION_ALIASES = {
    "bl_number": ("bl_number", "bill_of_lading_number", "transport_document_reference", "transport_reference_number"),
    "consignment_reference": (
        "consignment_reference",
        "transport_document_reference",
        "transport_reference_number",
        "bl_number",
        "receipt_number",
        "courier_receipt_number",
    ),
    "airway_bill_number": ("airway_bill_number", "awb_number", "bl_number"),
    "shipper": ("shipper", "shipper_name", "exporter"),
    "consignee": ("consignee", "consignee_name", "importer", "applicant"),
    "port_of_loading": ("port_of_loading", "pol", "load_port", "loading_port"),
    "port_of_discharge": ("port_of_discharge", "pod", "discharge_port", "destination_port"),
    "airport_of_departure": ("airport_of_departure", "port_of_loading"),
    "airport_of_destination": ("airport_of_destination", "port_of_discharge"),
    "transport_mode_chain": ("transport_mode_chain",),
    "carriage_vessel_name": ("carriage_vessel_name", "vessel_name"),
    "carriage_voyage_number": ("carriage_voyage_number", "voyage_number"),
    "on_board_date": ("on_board_date", "shipped_on_board_date", "shipment_date", "date_of_shipment", "date"),
}
_PACKING_LIST_VALIDATION_ALIASES = {
    "packing_list_number": ("packing_list_number", "packing_no", "packing_reference"),
    "document_date": ("document_date", "date", "issue_date"),
    "total_packages": ("total_packages", "package_count", "number_of_packages", "cartons", "total_cartons"),
    "gross_weight": ("gross_weight", "gross_wt", "total_gross_weight"),
    "net_weight": ("net_weight", "net_wt", "total_net_weight"),
    "marks_and_numbers": ("marks_and_numbers", "shipping_marks", "marks"),
    "packing_size_breakdown": ("packing_size_breakdown", "size_breakdown", "carton_size", "dimensions"),
}
_COO_VALIDATION_ALIASES = {
    "certificate_number": ("certificate_number", "certificate_no", "coo_number", "reference_number"),
    "country_of_origin": ("country_of_origin", "origin_country", "country_origin"),
    "exporter_name": ("exporter_name", "exporter", "shipper", "seller_name", "seller"),
    "importer_name": ("importer_name", "importer", "consignee", "buyer_name", "buyer", "applicant"),
    "goods_description": ("goods_description", "description", "product_description"),
    "certifying_authority": ("certifying_authority", "issuing_authority", "issuer_name", "issuer", "chamber_of_commerce", "chamber_name"),
    "issue_date": ("issue_date", "date", "document_date"),
    "license_number": ("license_number",),
    "declaration_reference": ("declaration_reference",),
    "permit_number": ("permit_number",),
}
_INSURANCE_VALIDATION_ALIASES = {
    "policy_number": ("policy_number", "policy_no", "insurance_policy_number", "certificate_number", "certificate_no"),
    "certificate_number": ("certificate_number", "certificate_no", "policy_number", "policy_no"),
    "insured_amount": ("insured_amount", "coverage_amount", "sum_insured", "amount"),
    "currency": ("currency", "currency_code", "insured_currency"),
    "coverage_type": ("coverage_type", "coverage", "risk_coverage", "risks_covered"),
    "issuer_name": ("issuer_name", "insurer", "issuing_authority", "issuer", "beneficiary"),
    "issue_date": ("issue_date", "date", "document_date", "doc_date", "date_of_issue"),
    "lc_reference": ("lc_reference", "lc_number", "credit_number"),
}
_INSPECTION_VALIDATION_ALIASES = {
    "certificate_number": ("certificate_number", "certificate_no", "report_number", "reference_number"),
    "inspection_agency": ("inspection_agency", "inspection_company", "issuing_authority", "issuer_name", "inspector_name"),
    "inspection_date": ("inspection_date", "issue_date", "date", "document_date"),
    "inspection_result": ("inspection_result", "inspection_results"),
    "goods_description": ("goods_description", "description", "product_description"),
    "quantity_verified": ("quantity_verified", "quantity", "inspected_quantity"),
    "quality_finding": ("quality_finding", "inspection_result", "inspection_results"),
    "analysis_result": ("analysis_result", "inspection_result", "inspection_results"),
    "gross_weight": ("gross_weight", "gross_wt", "total_gross_weight"),
    "net_weight": ("net_weight", "net_wt", "total_net_weight"),
    "measurement_value": ("measurement_value", "dimensions", "dimension", "size"),
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
    if document_type in _PACKING_LIST_DOCUMENT_TYPES:
        fact_graph = build_packing_list_fact_set(document)
        document["fact_graph_v1"] = fact_graph
        document["factGraphV1"] = fact_graph
        return fact_graph
    if document_type in _COO_DOCUMENT_TYPES:
        fact_graph = build_coo_fact_set(document)
        document["fact_graph_v1"] = fact_graph
        document["factGraphV1"] = fact_graph
        return fact_graph
    if document_type in _INSURANCE_DOCUMENT_TYPES:
        fact_graph = build_insurance_fact_set(document)
        document["fact_graph_v1"] = fact_graph
        document["factGraphV1"] = fact_graph
        return fact_graph
    if document_type in _INSPECTION_DOCUMENT_TYPES:
        fact_graph = build_inspection_fact_set(document)
        document["fact_graph_v1"] = fact_graph
        document["factGraphV1"] = fact_graph
        return fact_graph
    if document_type in _SUPPORTING_DOCUMENT_TYPES:
        fact_graph = build_supporting_fact_set(document)
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


def _iter_packing_list_documents(documents: Iterable[Dict[str, Any]]) -> Iterable[Dict[str, Any]]:
    for document in documents or []:
        if not isinstance(document, dict):
            continue
        if _document_type(document) in _PACKING_LIST_DOCUMENT_TYPES:
            yield document


def _iter_coo_documents(documents: Iterable[Dict[str, Any]]) -> Iterable[Dict[str, Any]]:
    for document in documents or []:
        if not isinstance(document, dict):
            continue
        if _document_type(document) in _COO_DOCUMENT_TYPES:
            yield document


def _iter_insurance_documents(documents: Iterable[Dict[str, Any]]) -> Iterable[Dict[str, Any]]:
    for document in documents or []:
        if not isinstance(document, dict):
            continue
        if _document_type(document) in _INSURANCE_DOCUMENT_TYPES:
            yield document


def _iter_inspection_documents(documents: Iterable[Dict[str, Any]]) -> Iterable[Dict[str, Any]]:
    for document in documents or []:
        if not isinstance(document, dict):
            continue
        if _document_type(document) in _INSPECTION_DOCUMENT_TYPES:
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


def project_packing_list_validation_context(
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

    for aliases in _PACKING_LIST_VALIDATION_ALIASES.values():
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
        aliases = _PACKING_LIST_VALIDATION_ALIASES.get(field_name)
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


def project_coo_validation_context(
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

    for aliases in _COO_VALIDATION_ALIASES.values():
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
        aliases = _COO_VALIDATION_ALIASES.get(field_name)
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


def project_insurance_validation_context(
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

    for aliases in _INSURANCE_VALIDATION_ALIASES.values():
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
        aliases = _INSURANCE_VALIDATION_ALIASES.get(field_name)
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


def project_inspection_validation_context(
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

    for aliases in _INSPECTION_VALIDATION_ALIASES.values():
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
        aliases = _INSPECTION_VALIDATION_ALIASES.get(field_name)
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


def apply_packing_list_fact_graph_to_validation_inputs(
    payload: Dict[str, Any],
    extracted_context: Dict[str, Any],
) -> Dict[str, Any]:
    payload_docs = payload.get("documents") if isinstance(payload, dict) else None
    context_docs = extracted_context.get("documents") if isinstance(extracted_context, dict) else None
    packing_document = next(
        _iter_packing_list_documents(
            payload_docs if isinstance(payload_docs, list) else context_docs if isinstance(context_docs, list) else []
        ),
        None,
    )

    payload_packing = (
        payload.get("packing_list")
        if isinstance(payload, dict) and isinstance(payload.get("packing_list"), dict)
        else {}
    )
    context_packing = (
        extracted_context.get("packing_list")
        if isinstance(extracted_context, dict) and isinstance(extracted_context.get("packing_list"), dict)
        else {}
    )
    base_packing_context = payload_packing or context_packing
    fact_graph = None
    if isinstance(packing_document, dict):
        fact_graph = packing_document.get("fact_graph_v1") or packing_document.get("factGraphV1")

    projected = project_packing_list_validation_context(
        base_packing_context,
        document=packing_document,
        fact_graph=fact_graph,
    )

    if isinstance(payload, dict):
        payload["packing_list"] = projected
    if isinstance(extracted_context, dict):
        extracted_context["packing_list"] = projected
    return projected


def apply_coo_fact_graph_to_validation_inputs(
    payload: Dict[str, Any],
    extracted_context: Dict[str, Any],
) -> Dict[str, Any]:
    payload_docs = payload.get("documents") if isinstance(payload, dict) else None
    context_docs = extracted_context.get("documents") if isinstance(extracted_context, dict) else None
    coo_document = next(
        _iter_coo_documents(
            payload_docs if isinstance(payload_docs, list) else context_docs if isinstance(context_docs, list) else []
        ),
        None,
    )

    payload_coo = (
        payload.get("certificate_of_origin")
        if isinstance(payload, dict) and isinstance(payload.get("certificate_of_origin"), dict)
        else {}
    )
    context_coo = (
        extracted_context.get("certificate_of_origin")
        if isinstance(extracted_context, dict) and isinstance(extracted_context.get("certificate_of_origin"), dict)
        else {}
    )
    base_coo_context = payload_coo or context_coo
    fact_graph = None
    if isinstance(coo_document, dict):
        fact_graph = coo_document.get("fact_graph_v1") or coo_document.get("factGraphV1")

    projected = project_coo_validation_context(
        base_coo_context,
        document=coo_document,
        fact_graph=fact_graph,
    )

    if isinstance(payload, dict):
        payload["certificate_of_origin"] = projected
    if isinstance(extracted_context, dict):
        extracted_context["certificate_of_origin"] = projected
    return projected


def apply_insurance_fact_graph_to_validation_inputs(
    payload: Dict[str, Any],
    extracted_context: Dict[str, Any],
) -> Dict[str, Any]:
    payload_docs = payload.get("documents") if isinstance(payload, dict) else None
    context_docs = extracted_context.get("documents") if isinstance(extracted_context, dict) else None
    insurance_document = next(
        _iter_insurance_documents(
            payload_docs if isinstance(payload_docs, list) else context_docs if isinstance(context_docs, list) else []
        ),
        None,
    )

    payload_insurance = (
        payload.get("insurance_certificate")
        if isinstance(payload, dict) and isinstance(payload.get("insurance_certificate"), dict)
        else {}
    )
    context_insurance = (
        extracted_context.get("insurance_certificate")
        if isinstance(extracted_context, dict) and isinstance(extracted_context.get("insurance_certificate"), dict)
        else {}
    )
    base_insurance_context = payload_insurance or context_insurance
    fact_graph = None
    if isinstance(insurance_document, dict):
        fact_graph = insurance_document.get("fact_graph_v1") or insurance_document.get("factGraphV1")

    projected = project_insurance_validation_context(
        base_insurance_context,
        document=insurance_document,
        fact_graph=fact_graph,
    )

    if isinstance(payload, dict):
        payload["insurance_certificate"] = projected
    if isinstance(extracted_context, dict):
        extracted_context["insurance_certificate"] = projected
    return projected


def apply_inspection_fact_graph_to_validation_inputs(
    payload: Dict[str, Any],
    extracted_context: Dict[str, Any],
) -> Dict[str, Any]:
    payload_docs = payload.get("documents") if isinstance(payload, dict) else None
    context_docs = extracted_context.get("documents") if isinstance(extracted_context, dict) else None
    inspection_document = next(
        _iter_inspection_documents(
            payload_docs if isinstance(payload_docs, list) else context_docs if isinstance(context_docs, list) else []
        ),
        None,
    )

    payload_inspection = (
        payload.get("inspection_certificate")
        if isinstance(payload, dict) and isinstance(payload.get("inspection_certificate"), dict)
        else {}
    )
    context_inspection = (
        extracted_context.get("inspection_certificate")
        if isinstance(extracted_context, dict) and isinstance(extracted_context.get("inspection_certificate"), dict)
        else {}
    )
    base_inspection_context = payload_inspection or context_inspection
    fact_graph = None
    if isinstance(inspection_document, dict):
        fact_graph = inspection_document.get("fact_graph_v1") or inspection_document.get("factGraphV1")

    projected = project_inspection_validation_context(
        base_inspection_context,
        document=inspection_document,
        fact_graph=fact_graph,
    )

    if isinstance(payload, dict):
        payload["inspection_certificate"] = projected
    if isinstance(extracted_context, dict):
        extracted_context["inspection_certificate"] = projected
    return projected
