from __future__ import annotations

from typing import Any, Dict, List, Optional

from .invoice_facts import build_invoice_fact_set


_INVOICE_DOCUMENT_TYPES = {"commercial_invoice", "proforma_invoice"}


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
