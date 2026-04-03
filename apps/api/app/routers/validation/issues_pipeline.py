"""Issue/presentation helper functions for validation routes."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from .utilities import priority_to_severity as _priority_to_severity


def _normalize_issue_field_key(value: Any) -> str:
    return str(value or "").strip().lower().replace(" ", "_").replace("-", "_")


def _normalize_issue_document_ids(issue: Dict[str, Any]) -> List[str]:
    raw_ids = issue.get("document_ids")
    if raw_ids in (None, ""):
        raw_ids = issue.get("documentId")
    if raw_ids in (None, ""):
        raw_ids = issue.get("document_id")
    if isinstance(raw_ids, list):
        items = raw_ids
    elif raw_ids in (None, ""):
        items = []
    else:
        items = [raw_ids]
    return [str(item).strip() for item in items if str(item).strip()]


def _is_extraction_provisional_issue(
    issue: Dict[str, Any],
    *,
    unresolved_doc_ids: Set[str],
    unresolved_fields_by_doc: Dict[str, Set[str]],
    unresolved_fields_any: Set[str],
) -> bool:
    if not isinstance(issue, dict):
        return False

    reason_candidates = {
        _normalize_issue_field_key(issue.get("reason_code")),
        _normalize_issue_field_key(issue.get("decision_status")),
        _normalize_issue_field_key((issue.get("decision") or {}).get("reason_code"))
        if isinstance(issue.get("decision"), dict)
        else "",
        _normalize_issue_field_key((issue.get("decision") or {}).get("status"))
        if isinstance(issue.get("decision"), dict)
        else "",
    }
    reason_candidates.discard("")
    extraction_reason_codes = {
        "field_not_found",
        "missing_in_source",
        "extraction_failed",
        "format_invalid",
        "critical_missing",
        "rejected",
        "retry",
    }
    if reason_candidates.intersection(extraction_reason_codes):
        return True

    issue_fields = {
        _normalize_issue_field_key(issue.get("field")),
        _normalize_issue_field_key(issue.get("field_name")),
        _normalize_issue_field_key(issue.get("source_field")),
        _normalize_issue_field_key(issue.get("lc_field")),
    }
    issue_fields.discard("")
    issue_doc_ids = set(_normalize_issue_document_ids(issue))
    if issue_doc_ids and unresolved_doc_ids and not issue_doc_ids.intersection(unresolved_doc_ids):
        return False

    if issue_doc_ids:
        for doc_id in issue_doc_ids.intersection(unresolved_doc_ids):
            if issue_fields.intersection(unresolved_fields_by_doc.get(doc_id) or set()):
                return True
    elif issue_fields.intersection(unresolved_fields_any):
        return True

    signal_text = " ".join(
        str(issue.get(key) or "").lower()
        for key in ("rule", "title", "message", "description", "found", "actual", "expected")
    )
    if any(token in signal_text for token in ("conflict", "mismatch", "discrepancy")):
        return False
    if issue_doc_ids.intersection(unresolved_doc_ids):
        return any(
            token in signal_text
            for token in (
                "field not found",
                "could not confirm",
                "could not be extracted",
                "missing required field",
                "source does not show",
                "extraction",
            )
        )
    return False


def _partition_workflow_stage_issues(
    issues: List[Dict[str, Any]],
    documents: Optional[List[Dict[str, Any]]] = None,
    workflow_stage: Optional[Dict[str, Any]] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    stage = str((workflow_stage or {}).get("stage") or "").strip().lower()
    severe_extraction_reason_codes = {
        "field_not_found",
        "ocr_auth_error",
        "ocr_auth_failure",
        "ocr_empty_result",
        "ocr_provider_unavailable",
        "parser_empty_output",
        "parse_failed",
        "low_confidence",
        "low_confidence_critical",
    }
    degraded_selection_stages = {"binary_metadata_scrape"}
    weak_fallback_document_names = {
        "",
        "supporting document",
        "supporting_document",
        "lc-related document",
        "lc_related_document",
    }

    def _normalize_issue_text(value: Any) -> str:
        return " ".join(str(value or "").strip().lower().split())

    def _normalize_document_type_token(value: Any) -> str:
        return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")

    def _document_alias_tokens(document: Dict[str, Any]) -> Set[str]:
        tokens: Set[str] = set()

        def _add_token(raw: Any) -> None:
            text = _normalize_issue_text(raw)
            if not text:
                return
            tokens.add(text)
            underscored = text.replace(" ", "_")
            tokens.add(underscored)
            basename = text.rsplit(".", 1)[0]
            if basename:
                tokens.add(basename)

        doc_type = _normalize_document_type_token(
            document.get("document_type") or document.get("documentType")
        )
        alias_map = {
            "commercial_invoice": {"invoice", "commercial invoice"},
            "invoice": {"invoice", "commercial invoice"},
            "letter_of_credit": {"letter of credit", "lc"},
            "lc": {"letter of credit", "lc"},
            "bill_of_lading": {"bill of lading", "bl"},
            "ocean_bill_of_lading": {"bill of lading", "bl"},
            "insurance_certificate": {"insurance", "insurance certificate"},
            "insurance_policy": {"insurance", "insurance policy"},
            "insurance": {"insurance", "insurance certificate"},
        }

        if doc_type:
            _add_token(doc_type)
            for alias in alias_map.get(doc_type, set()):
                _add_token(alias)

        for raw in (
            document.get("filename"),
            document.get("file_name"),
            document.get("name"),
        ):
            _add_token(raw)
        return {token for token in tokens if token}

    def _is_ai_major_extraction_unreliable_document(document: Dict[str, Any]) -> bool:
        if not isinstance(document, dict):
            return False

        review_required = bool(
            document.get("review_required") or document.get("reviewRequired")
        )
        extraction_status = str(
            document.get("extraction_status")
            or document.get("extractionStatus")
            or document.get("status")
            or ""
        ).strip().lower()
        critical_field_states = (
            document.get("critical_field_states")
            if isinstance(document.get("critical_field_states"), dict)
            else document.get("criticalFieldStates")
            if isinstance(document.get("criticalFieldStates"), dict)
            else {}
        )
        missing_critical_fields = any(
            str(state or "").strip().lower() == "missing"
            for state in critical_field_states.values()
        )
        ready_for_validation = document.get("ready_for_validation")
        if ready_for_validation is None:
            ready_for_validation = document.get("readyForValidation")
        resolution_required = document.get("resolution_required")
        if resolution_required is None:
            resolution_required = document.get("resolutionRequired")
        extraction_resolution = (
            document.get("extraction_resolution")
            if isinstance(document.get("extraction_resolution"), dict)
            else document.get("extractionResolution")
            if isinstance(document.get("extractionResolution"), dict)
            else {}
        )
        extraction_resolution_required = (
            extraction_resolution.get("required")
            if "required" in extraction_resolution
            else None
        )
        validation_ready = False
        if ready_for_validation is not None:
            validation_ready = bool(ready_for_validation)
        elif resolution_required is not None:
            validation_ready = not bool(resolution_required)
        elif extraction_resolution_required is not None:
            validation_ready = not bool(extraction_resolution_required)

        extraction_artifacts = (
            document.get("extraction_artifacts_v1")
            if isinstance(document.get("extraction_artifacts_v1"), dict)
            else document.get("extractionArtifactsV1")
            if isinstance(document.get("extractionArtifactsV1"), dict)
            else {}
        )
        selected_stage = _normalize_issue_text(extraction_artifacts.get("selected_stage"))
        raw_reason_codes = []
        for key in ("canonical_reason_codes", "reason_codes", "review_reasons", "reviewReasons"):
            values = extraction_artifacts.get(key)
            if isinstance(values, list):
                raw_reason_codes.extend(values)
        reason_codes = {
            _normalize_issue_field_key(code)
            for code in raw_reason_codes
            if str(code or "").strip()
        }

        if not review_required:
            return False

        hard_unreliable_reason_codes = {
            "ocr_auth_error",
            "ocr_auth_failure",
            "ocr_empty_result",
            "ocr_provider_unavailable",
            "parser_empty_output",
            "low_confidence",
            "low_confidence_critical",
        }
        if validation_ready and selected_stage not in degraded_selection_stages:
            if not reason_codes.intersection(hard_unreliable_reason_codes):
                return False

        return bool(
            reason_codes.intersection(severe_extraction_reason_codes)
            or selected_stage in degraded_selection_stages
            or (
                missing_critical_fields
                and extraction_status in {"partial", "warning", "error", "parse_failed", "text_only", "unknown"}
            )
        )

    unresolved_doc_ids: Set[str] = set()
    unresolved_fields_by_doc: Dict[str, Set[str]] = {}
    unresolved_fields_any: Set[str] = set()
    unreliable_doc_ids: Set[str] = set()
    unreliable_doc_tokens: Set[str] = set()
    unreliable_document_types: Set[str] = set()

    for document in documents or []:
        if not isinstance(document, dict):
            continue
        doc_id = str(
            document.get("document_id")
            or document.get("documentId")
            or document.get("id")
            or ""
        ).strip()
        doc_type = _normalize_document_type_token(
            document.get("document_type") or document.get("documentType")
        )
        if _is_ai_major_extraction_unreliable_document(document):
            if doc_id:
                unreliable_doc_ids.add(doc_id)
            if doc_type:
                unreliable_document_types.add(doc_type)
            unreliable_doc_tokens.update(_document_alias_tokens(document))

        extraction_resolution = (
            document.get("extraction_resolution")
            if isinstance(document.get("extraction_resolution"), dict)
            else document.get("extractionResolution")
            if isinstance(document.get("extractionResolution"), dict)
            else {}
        )
        if not bool(extraction_resolution.get("required")):
            continue
        if not doc_id:
            continue
        unresolved_doc_ids.add(doc_id)
        field_names = {
            _normalize_issue_field_key(field.get("field_name") or field.get("fieldName"))
            for field in (extraction_resolution.get("fields") or [])
            if isinstance(field, dict)
        }
        field_names.discard("")
        unresolved_fields_by_doc[doc_id] = field_names
        unresolved_fields_any.update(field_names)

    if stage != "extraction_resolution" and not unreliable_doc_ids and not unreliable_doc_tokens:
        return {"final_issues": list(issues or []), "provisional_issues": []}

    def _issue_signal_text(issue: Dict[str, Any]) -> str:
        parts: List[str] = []
        for key in (
            "rule",
            "rule_id",
            "title",
            "message",
            "description",
            "expected",
            "found",
            "actual",
            "suggestion",
            "documentName",
            "document_name",
            "documentType",
            "document_type",
        ):
            value = issue.get(key)
            if value not in (None, ""):
                parts.append(str(value))
        for key in ("documents", "document_names", "documentNames", "document_types", "documentTypes"):
            value = issue.get(key)
            if isinstance(value, list):
                parts.extend(str(item) for item in value if str(item or "").strip())
        return _normalize_issue_text(" ".join(parts))

    def _issue_targets_unreliable_document(issue: Dict[str, Any]) -> bool:
        rule_id = str(issue.get("rule") or issue.get("rule_id") or issue.get("id") or "").strip().upper()
        if rule_id.startswith("AI-L3-LOW-CONFIDENCE-"):
            return False

        issue_doc_ids = set(_normalize_issue_document_ids(issue))
        if issue_doc_ids and issue_doc_ids.intersection(unreliable_doc_ids):
            return True

        signal_text = _issue_signal_text(issue)
        return any(token in signal_text for token in unreliable_doc_tokens if token)

    def _is_weak_fallback_issue(issue: Dict[str, Any]) -> bool:
        rule_id = str(issue.get("rule") or issue.get("rule_id") or issue.get("id") or "").strip().upper()
        if rule_id.startswith("AI-L3-LOW-CONFIDENCE-"):
            return False

        severity = _normalize_issue_text(issue.get("severity"))
        if severity not in {"minor", "warning"}:
            return False

        if _normalize_issue_document_ids(issue):
            return False

        for key in ("field", "field_name", "source_field", "target_field", "lc_field"):
            if str(issue.get(key) or "").strip():
                return False
        for key in ("documentType", "document_type"):
            if str(issue.get(key) or "").strip():
                return False
        for key in ("documentTypes", "document_types"):
            values = issue.get(key)
            if isinstance(values, list) and any(str(item or "").strip() for item in values):
                return False

        document_name = _normalize_issue_text(issue.get("documentName") or issue.get("document_name"))
        if document_name not in weak_fallback_document_names:
            return False

        expected = _normalize_issue_text(issue.get("expected"))
        actual = _normalize_issue_text(issue.get("actual") or issue.get("found"))
        return expected in {"", "—", "-", "n/a"} and actual in {"", "—", "-", "n/a"}

    final_issues: List[Dict[str, Any]] = []
    provisional_issues: List[Dict[str, Any]] = []
    for issue in issues or []:
        if not isinstance(issue, dict):
            final_issues.append(issue)
            continue

        provisional_reason = None
        if stage == "extraction_resolution" and _is_extraction_provisional_issue(
            issue,
            unresolved_doc_ids=unresolved_doc_ids,
            unresolved_fields_by_doc=unresolved_fields_by_doc,
            unresolved_fields_any=unresolved_fields_any,
        ):
            provisional_reason = "workflow_stage_extraction_resolution"
        elif unreliable_doc_ids or unreliable_doc_tokens:
            if _issue_targets_unreliable_document(issue):
                provisional_reason = "ai_major_extraction_uncertainty"
            elif _is_weak_fallback_issue(issue):
                provisional_reason = "ai_major_extraction_fallback_noise"

        if provisional_reason:
            provisional_issue = dict(issue)
            provisional_issue["provisional"] = True
            provisional_issue["provisional_reason"] = provisional_reason
            if unreliable_document_types:
                provisional_issue["provisional_document_types"] = sorted(unreliable_document_types)
            provisional_issues.append(provisional_issue)
            continue
        final_issues.append(issue)

    return {
        "final_issues": final_issues,
        "provisional_issues": provisional_issues,
    }

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
