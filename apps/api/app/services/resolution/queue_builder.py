from __future__ import annotations

from typing import Any, Dict, List

from .models import ResolutionQueue, ResolutionQueueItem, ResolutionQueueSummary


_INVOICE_DOCUMENT_TYPES = {
    "commercial_invoice",
    "proforma_invoice",
    "draft_bill_of_exchange",
    "promissory_note",
    "payment_receipt",
    "debit_note",
    "credit_note",
}
_LC_DOCUMENT_TYPES = {
    "letter_of_credit",
    "swift_message",
    "lc_application",
    "bank_guarantee",
    "standby_letter_of_credit",
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
_USER_RESOLVABLE_STATES = {"candidate", "unconfirmed", "operator_rejected"}
_HIGH_PRIORITY_FIELDS = {
    "invoice_number",
    "instrument_number",
    "receipt_number",
    "lc_reference",
    "invoice_date",
    "amount",
    "currency",
}
_LC_HIGH_PRIORITY_FIELDS = {
    "lc_number",
    "issue_date",
    "expiry_date",
    "latest_shipment_date",
    "applicant",
    "beneficiary",
    "amount",
    "currency",
}
_LC_USER_RESOLVABLE_FIELDS = {
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
}
_BL_HIGH_PRIORITY_FIELDS = {"bl_number", "on_board_date", "port_of_loading", "port_of_discharge"}
_BL_HIGH_PRIORITY_FIELDS.update(
    {
        "consignment_reference",
        "airway_bill_number",
        "airport_of_departure",
        "airport_of_destination",
        "transport_mode_chain",
        "carriage_vessel_name",
        "carriage_voyage_number",
    }
)
_PACKING_LIST_HIGH_PRIORITY_FIELDS = {
    "packing_list_number",
    "document_date",
    "total_packages",
    "gross_weight",
    "net_weight",
}
_COO_HIGH_PRIORITY_FIELDS = {
    "certificate_number",
    "country_of_origin",
    "exporter_name",
    "goods_description",
    "issue_date",
    "certifying_authority",
    "license_number",
    "declaration_reference",
    "permit_number",
}
_INSURANCE_HIGH_PRIORITY_FIELDS = {
    "policy_number",
    "certificate_number",
    "insured_amount",
    "coverage_type",
    "issuer_name",
    "issue_date",
}
_INSPECTION_HIGH_PRIORITY_FIELDS = {
    "certificate_number",
    "inspection_agency",
    "inspection_date",
    "inspection_result",
    "quality_finding",
    "analysis_result",
    "gross_weight",
    "net_weight",
    "measurement_value",
}


def _humanize_field_name(field_name: str) -> str:
    return str(field_name or "").replace("_", " ").strip().title()


def _priority_for_field(field_name: str) -> str:
    normalized = str(field_name or "").strip().lower()
    if (
        normalized in _HIGH_PRIORITY_FIELDS
        or normalized in _LC_HIGH_PRIORITY_FIELDS
        or normalized in _BL_HIGH_PRIORITY_FIELDS
        or normalized in _PACKING_LIST_HIGH_PRIORITY_FIELDS
        or normalized in _COO_HIGH_PRIORITY_FIELDS
        or normalized in _INSURANCE_HIGH_PRIORITY_FIELDS
        or normalized in _INSPECTION_HIGH_PRIORITY_FIELDS
    ):
        return "high"
    return "medium"


def _reason_for_state(verification_state: str) -> str:
    state = str(verification_state or "").strip().lower()
    if state == "operator_rejected":
        return "operator_rejected_candidate"
    return "system_could_not_confirm"


def build_resolution_queue_v1(documents: List[Dict[str, Any]]) -> Dict[str, Any]:
    items: List[ResolutionQueueItem] = []
    document_counts: Dict[str, int] = {}
    unresolved_document_ids: List[str] = []

    for document in documents or []:
        if not isinstance(document, dict):
            continue
        document_type = str(
            document.get("document_type")
            or document.get("documentType")
            or document.get("type")
            or ""
        ).strip().lower()
        if (
            document_type not in _LC_DOCUMENT_TYPES
            and document_type not in _INVOICE_DOCUMENT_TYPES
            and document_type not in _BL_DOCUMENT_TYPES
            and document_type not in _PACKING_LIST_DOCUMENT_TYPES
            and document_type not in _COO_DOCUMENT_TYPES
            and document_type not in _INSURANCE_DOCUMENT_TYPES
            and document_type not in _INSPECTION_DOCUMENT_TYPES
        ):
            continue

        if document_type in _LC_DOCUMENT_TYPES:
            extraction_lane = str(
                document.get("extraction_lane")
                or document.get("extractionLane")
                or ""
            ).strip().lower()
            existing_fact_graph = document.get("fact_graph_v1") or document.get("factGraphV1")
            if extraction_lane != "document_ai" and not isinstance(existing_fact_graph, dict):
                continue

        fact_graph = document.get("fact_graph_v1") or document.get("factGraphV1")
        if not isinstance(fact_graph, dict):
            continue

        doc_items = 0
        for fact in fact_graph.get("facts") or []:
            if not isinstance(fact, dict):
                continue
            verification_state = str(fact.get("verification_state") or "").strip().lower()
            if verification_state not in _USER_RESOLVABLE_STATES:
                continue
            field_name = str(fact.get("field_name") or "").strip()
            if not field_name:
                continue
            if (
                document_type in _LC_DOCUMENT_TYPES
                and field_name.strip().lower() not in _LC_USER_RESOLVABLE_FIELDS
            ):
                continue

            items.append(
                ResolutionQueueItem(
                    document_id=str(
                        document.get("document_id")
                        or document.get("documentId")
                        or document.get("id")
                        or ""
                    ),
                    document_type=document_type,
                    filename=document.get("filename") or document.get("name"),
                    field_name=field_name,
                    label=_humanize_field_name(field_name),
                    priority=_priority_for_field(field_name),
                    candidate_value=fact.get("value"),
                    normalized_value=fact.get("normalized_value"),
                    evidence_snippet=fact.get("evidence_snippet"),
                    evidence_source=fact.get("evidence_source"),
                    page=fact.get("page") if isinstance(fact.get("page"), int) else None,
                    reason=_reason_for_state(verification_state),
                    verification_state=verification_state,
                    resolvable_by_user=True,
                    origin=fact.get("origin"),
                )
            )
            doc_items += 1

        if doc_items > 0:
            document_counts[document_type] = document_counts.get(document_type, 0) + doc_items
            unresolved_document_ids.append(
                str(
                    document.get("document_id")
                    or document.get("documentId")
                    or document.get("id")
                    or ""
                )
            )

    return ResolutionQueue(
        version="resolution_queue_v1",
        items=items,
        summary=ResolutionQueueSummary(
            total_items=len(items),
            user_resolvable_items=len(items),
            unresolved_documents=len([doc_id for doc_id in unresolved_document_ids if doc_id]),
            document_counts=document_counts,
        ),
    ).to_dict()
