"""Issue/presentation helper functions for validation routes."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from .utilities import priority_to_severity as _priority_to_severity

def _build_issue_context(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a context snapshot from the validation payload for AI issue rewriting.
    Extracts key document data that helps the AI produce accurate issue descriptions.
    """
    lc = payload.get("lc") or payload.get("lc_data") or {}
    invoice = payload.get("invoice") or {}
    bill_of_lading = payload.get("bill_of_lading") or payload.get("billOfLading") or {}
    bl_fields = bill_of_lading.get("extracted_fields") if isinstance(bill_of_lading.get("extracted_fields"), dict) else {}
    certificate_of_origin = payload.get("certificate_of_origin") or payload.get("certificateOfOrigin") or {}
    insurance = payload.get("insurance") or payload.get("insurance_certificate") or {}
    packing_list = payload.get("packing_list") or payload.get("packingList") or {}
    
    return {
        "lc": {
            "goods_description": lc.get("goods_description"),
            "goods_items": lc.get("goods_items"),
            "incoterm": lc.get("incoterm"),
            "ports": lc.get("ports"),
            "dates": lc.get("dates"),
            "applicant": lc.get("applicant"),
            "beneficiary": lc.get("beneficiary"),
            "amount": lc.get("amount") or lc.get("lc_amount"),
            "currency": lc.get("currency"),
        },
        "invoice": {
            "goods_description": invoice.get("goods_description") or invoice.get("product_description"),
            "amount": invoice.get("invoice_amount") or invoice.get("amount"),
            "currency": invoice.get("currency"),
            "hs_code": invoice.get("hs_code"),
            "consignee": invoice.get("consignee"),
            "shipper": invoice.get("shipper"),
        },
        "bill_of_lading": {
            "goods_description": bill_of_lading.get("goods_description") or bl_fields.get("goods_description"),
            "port_of_loading": bill_of_lading.get("port_of_loading") or bl_fields.get("port_of_loading"),
            "port_of_discharge": bill_of_lading.get("port_of_discharge") or bl_fields.get("port_of_discharge"),
            "vessel": bill_of_lading.get("vessel") or bill_of_lading.get("vessel_name") or bl_fields.get("vessel_name"),
            "voyage_number": bill_of_lading.get("voyage_number") or bl_fields.get("voyage_number"),
            "gross_weight": bill_of_lading.get("gross_weight") or bl_fields.get("gross_weight"),
            "net_weight": bill_of_lading.get("net_weight") or bl_fields.get("net_weight"),
            "on_board_date": bill_of_lading.get("on_board_date") or bill_of_lading.get("shipped_on_board_date") or bl_fields.get("shipped_on_board_date"),
            "consignee": bill_of_lading.get("consignee") or bl_fields.get("consignee"),
            "shipper": bill_of_lading.get("shipper") or bl_fields.get("shipper"),
        },
        "certificate_of_origin": {
            "origin_country": certificate_of_origin.get("origin_country") or certificate_of_origin.get("country_of_origin"),
            "goods_description": certificate_of_origin.get("goods_description"),
        },
        "insurance": {
            "coverage_amount": insurance.get("coverage_amount") or insurance.get("amount"),
            "currency": insurance.get("currency"),
            "risks_covered": insurance.get("risks_covered"),
        },
        "packing_list": {
            "total_packages": packing_list.get("total_packages"),
            "gross_weight": packing_list.get("gross_weight"),
            "net_weight": packing_list.get("net_weight"),
        },
        "metadata": {
            "lc_number": payload.get("lc_number") or payload.get("lcNumber"),
            "user_type": payload.get("user_type") or payload.get("userType"),
            "workflow_type": payload.get("workflow_type") or payload.get("workflowType"),
        },
    }

def _apply_issue_rewrite(issue: Dict[str, Any], rewrite_payload: Dict[str, Any]) -> None:
    title = rewrite_payload.get("title")
    if title:
        issue["title"] = title

    description = rewrite_payload.get("description")
    if description:
        issue["description"] = description
        issue["message"] = description

    expected = rewrite_payload.get("expected")
    if expected is not None:
        issue["expected"] = expected

    found = rewrite_payload.get("found")
    if found is not None:
        issue["found"] = found
        issue["actual"] = found

    suggestion = rewrite_payload.get("suggested_fix") or rewrite_payload.get("suggestion")
    if suggestion is not None:
        issue["suggested_fix"] = suggestion
        issue["suggestion"] = suggestion

    documents = rewrite_payload.get("documents")
    if documents:
        issue["documents"] = documents
        issue["document_names"] = documents

    priority = rewrite_payload.get("priority")
    severity = _priority_to_severity(priority, issue.get("severity"))
    issue["severity"] = severity
    if priority:
        issue["priority"] = priority

def _extract_field_decisions_from_payload(payload: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Best-effort extraction of LC field decisions from current payload/context."""
    if not isinstance(payload, dict):
        return {}

    for candidate in (
        payload.get("lc"),
        payload.get("lc_structured_output"),
        payload.get("extracted_fields"),
    ):
        if isinstance(candidate, dict):
            decisions = candidate.get("_field_decisions")
            if isinstance(decisions, dict):
                return decisions
    return {}

def _build_document_field_hint_index(documents: List[Dict[str, Any]]) -> Dict[str, Dict[str, str]]:
    """Best-effort field -> source document/type hint map from document surfaces."""
    hint_index: Dict[str, Dict[str, str]] = {}
    for document in documents or []:
        if not isinstance(document, dict):
            continue
        doc_hint = str(
            document.get("filename")
            or document.get("file_name")
            or document.get("name")
            or document.get("document_type")
            or document.get("documentType")
            or document.get("source_type")
            or ""
        ).strip()
        doc_type_hint = str(
            document.get("document_type")
            or document.get("documentType")
            or document.get("source_type")
            or document.get("sourceType")
            or ""
        ).strip()

        candidate_maps = [
            document.get("critical_field_states"),
            document.get("criticalFieldStates"),
            (document.get("extraction_artifacts_v1") or {}).get("field_diagnostics") if isinstance(document.get("extraction_artifacts_v1"), dict) else None,
            document.get("field_details"),
            document.get("_field_details"),
        ]
        for candidate in candidate_maps:
            if not isinstance(candidate, dict):
                continue
            for field_name in candidate.keys():
                field_key = str(field_name or "").strip()
                if not field_key or field_key in hint_index:
                    continue
                hint_index[field_key] = {
                    "source_document": doc_hint,
                    "document_type": doc_type_hint,
                }
    return hint_index

def _build_unresolved_critical_context(
    field_decisions: Dict[str, Dict[str, Any]],
    critical_fields: Optional[Set[str]] = None,
    documents: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Return unresolved critical field diagnostics with mandatory status + reason_code."""
    unresolved: List[Dict[str, Any]] = []
    critical_filter = {str(field).strip() for field in (critical_fields or set()) if str(field).strip()}
    hint_index = _build_document_field_hint_index(documents or [])
    for field, decision in (field_decisions or {}).items():
        if not isinstance(decision, dict):
            continue
        normalized_field = str(field or "").strip()
        if critical_filter and normalized_field not in critical_filter:
            continue
        status = str(decision.get("status") or "").strip().lower()
        if status not in {"retry", "rejected"}:
            continue
        reason_code = str(decision.get("reason_code") or "").strip()
        if not reason_code:
            reason_code = "unknown"
        entry = {
            "field": normalized_field,
            "status": status,
            "reason_code": reason_code,
        }
        hint = hint_index.get(normalized_field) or {}
        if hint.get("source_document"):
            entry["source_document"] = hint.get("source_document")
        if hint.get("document_type"):
            entry["document_type"] = hint.get("document_type")
        if "retry_trace" in decision:
            entry["retry_trace"] = decision.get("retry_trace")
        unresolved.append(entry)
    return unresolved

def _augment_doc_field_details_with_decisions(documents: List[Dict[str, Any]]) -> None:
    """Inject decision/status/reason/retry_trace into document field_details (in-place)."""
    for doc in documents or []:
        if not isinstance(doc, dict):
            continue
        extracted_fields = doc.get("extracted_fields") or {}
        if not isinstance(extracted_fields, dict):
            continue

        field_decisions = extracted_fields.get("_field_decisions")
        if not isinstance(field_decisions, dict) or not field_decisions:
            continue

        field_details = doc.get("field_details")
        if not isinstance(field_details, dict):
            field_details = {}
            doc["field_details"] = field_details

        for field, decision in field_decisions.items():
            if not isinstance(decision, dict):
                continue
            details = field_details.get(field)
            if not isinstance(details, dict):
                details = {}
                field_details[field] = details

            details["decision_status"] = str(decision.get("status") or details.get("decision_status") or "unknown").lower()
            details["reason_code"] = str(decision.get("reason_code") or details.get("reason_code") or "unknown")
            details["decision"] = {
                "status": details["decision_status"],
                "reason_code": details["reason_code"],
            }
            if "retry_trace" in decision:
                details["retry_trace"] = decision.get("retry_trace")

def _augment_issues_with_field_decisions(
    issues: List[Dict[str, Any]],
    field_decisions: Dict[str, Dict[str, Any]],
) -> None:
    """Inject decision status/reason_code in issue payload where a field decision exists."""
    if not issues or not field_decisions:
        return

    for issue in issues:
        if not isinstance(issue, dict):
            continue
        field_name = (
            issue.get("field")
            or issue.get("field_name")
            or issue.get("source_field")
            or issue.get("lc_field")
        )
        if not field_name:
            continue
        decision = field_decisions.get(str(field_name))
        if not isinstance(decision, dict):
            continue

        issue["decision_status"] = str(decision.get("status") or issue.get("decision_status") or "unknown").lower()
        issue["reason_code"] = str(decision.get("reason_code") or issue.get("reason_code") or "unknown")
        issue["decision"] = {
            "status": issue["decision_status"],
            "reason_code": issue["reason_code"],
        }
