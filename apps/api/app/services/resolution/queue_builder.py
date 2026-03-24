from __future__ import annotations

from typing import Any, Dict, List

from .models import ResolutionQueue, ResolutionQueueItem, ResolutionQueueSummary


_INVOICE_DOCUMENT_TYPES = {"commercial_invoice", "proforma_invoice"}
_USER_RESOLVABLE_STATES = {"candidate", "unconfirmed", "operator_rejected"}
_HIGH_PRIORITY_FIELDS = {"invoice_number", "invoice_date", "amount", "currency"}


def _humanize_field_name(field_name: str) -> str:
    return str(field_name or "").replace("_", " ").strip().title()


def _priority_for_field(field_name: str) -> str:
    return "high" if str(field_name or "").strip().lower() in _HIGH_PRIORITY_FIELDS else "medium"


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
        if document_type not in _INVOICE_DOCUMENT_TYPES:
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
