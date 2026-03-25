"""LC intake shaping helpers for validation routes."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from app.core.lc_types import LCType, normalize_lc_type
from app.services.extraction.lc_taxonomy import (
    build_lc_classification,
    normalize_required_documents,
)

from .lc_dates import repair_lc_mt700_dates


logger = logging.getLogger(__name__)


def extract_intake_only(payload: Dict[str, Any]) -> bool:
    options = payload.get("options") or {}
    candidates = [
        payload.get("intake_only"),
        payload.get("intakeOnly"),
        options.get("intake_only"),
        options.get("intakeOnly"),
        payload.get("mode"),
    ]
    truthy = {"1", "true", "yes", "on", "intake", "lc_intake"}
    for candidate in candidates:
        if isinstance(candidate, bool):
            return candidate
        if candidate is None:
            continue
        if str(candidate).strip().lower() in truthy:
            return True
    return False


def _parse_json_if_possible(value: Any) -> Any:
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("{") or stripped.startswith("["):
            try:
                return json.loads(stripped)
            except json.JSONDecodeError:
                logger.warning("Failed to parse JSON string in LC intake helper; leaving raw text")
                return value
    return value


def coerce_text_list(value: Any) -> List[str]:
    parsed = _parse_json_if_possible(value)
    if parsed in (None, "", [], {}):
        return []
    if isinstance(parsed, list):
        return [str(item).strip() for item in parsed if str(item).strip()]
    if isinstance(parsed, str):
        text = parsed.strip()
        if not text:
            return []
        return [text]
    return [str(parsed).strip()]


_DOC_REQUIREMENT_HINTS: List[Tuple[str, Tuple[str, ...]]] = [
    ("commercial_invoice", ("commercial invoice", "invoice", "signed invoice")),
    ("bill_of_lading", ("bill of lading", "full set clean on board", "marine bill of lading", "ocean bill of lading", "bl", "b/l")),
    ("air_waybill", ("air waybill", "awb", "airway bill")),
    ("packing_list", ("packing list", "packing", "detailed packing list", "pl")),
    ("certificate_of_origin", ("certificate of origin", "country of origin", "coo")),
    ("insurance_certificate", ("insurance certificate", "insurance policy", "marine insurance", "insurance")),
    ("inspection_certificate", ("inspection certificate", "certificate of inspection")),
    ("beneficiary_certificate", ("beneficiary certificate", "beneficiary's certificate", "beneficiary statement")),
    ("manufacturer_certificate", ("manufacturer certificate", "manufacturer's certificate")),
    ("conformity_certificate", ("certificate of conformity", "conformity certificate")),
    ("non_manipulation_certificate", ("non-manipulation certificate", "non manipulation certificate")),
    ("weight_certificate", ("weight certificate", "weighment certificate")),
    ("weight_list", ("weight list",)),
    ("phytosanitary_certificate", ("phytosanitary certificate", "phyto certificate")),
    ("fumigation_certificate", ("fumigation certificate",)),
    ("health_certificate", ("health certificate",)),
    ("analysis_certificate", ("certificate of analysis", "analysis certificate")),
    ("lab_test_report", ("test report", "lab test report", "laboratory report")),
    ("quality_certificate", ("quality certificate",)),
]


def infer_required_document_types_from_lc(lc_payload: Dict[str, Any]) -> List[str]:
    requirements_graph = (
        (lc_payload or {}).get("requirements_graph_v1")
        or (lc_payload or {}).get("requirementsGraphV1")
    )
    if isinstance(requirements_graph, dict):
        graph_types = [
            str(item).strip().lower()
            for item in (requirements_graph.get("required_document_types") or [])
            if str(item or "").strip()
        ]
        if graph_types:
            return sorted(set(graph_types))

    normalized_required_documents = normalize_required_documents(lc_payload or {})
    normalized_codes = [
        str(entry.get("code")).strip().lower()
        for entry in normalized_required_documents
        if isinstance(entry, dict) and str(entry.get("code") or "").strip()
    ]
    if normalized_codes:
        return sorted(set(normalized_codes))

    texts: List[str] = []
    for key in ("documents_required", "required_documents"):
        texts.extend(coerce_text_list(lc_payload.get(key)))

    mt700 = lc_payload.get("mt700") or {}
    if isinstance(mt700, dict):
        blocks = mt700.get("blocks") or {}
        if isinstance(blocks, dict):
            texts.extend(coerce_text_list(blocks.get("46A")))

    haystack = "\n".join(texts).lower()
    matches: List[str] = []
    for canonical, hints in _DOC_REQUIREMENT_HINTS:
        if any(hint in haystack for hint in hints):
            matches.append(canonical)
    return sorted(set(matches))


def resolve_legacy_workflow_lc_fields(*contexts: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    for context in contexts:
        if not isinstance(context, dict):
            continue
        classification = context.get("lc_classification")
        if isinstance(classification, dict):
            workflow = normalize_lc_type(str(classification.get("workflow_orientation") or "").strip().lower())
            if workflow:
                return {
                    "lc_type": workflow,
                    "lc_type_reason": "Derived from canonical workflow_orientation.",
                    "lc_type_confidence": 0.85,
                    "lc_type_source": "lc_classification",
                }

    for context in contexts:
        if not isinstance(context, dict):
            continue
        workflow = normalize_lc_type(str(context.get("lc_type") or "").strip().lower())
        if workflow:
            confidence = context.get("lc_type_confidence")
            return {
                "lc_type": workflow,
                "lc_type_reason": context.get("lc_type_reason") or "Preserved workflow alias.",
                "lc_type_confidence": confidence if confidence not in (None, "") else 0,
                "lc_type_source": context.get("lc_type_source") or "legacy_compatibility",
            }

    return {
        "lc_type": LCType.UNKNOWN.value,
        "lc_type_reason": "No workflow alias available from canonical classification or payload.",
        "lc_type_confidence": 0,
        "lc_type_source": "auto",
    }


def prepare_extractor_outputs_for_structured_result(payload: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not payload:
        return None

    extractor_outputs = payload.get("lc_structured_output")
    merged = dict(extractor_outputs) if isinstance(extractor_outputs, dict) else {}
    lc_payload = payload.get("lc") if isinstance(payload.get("lc"), dict) else {}
    merged = repair_lc_mt700_dates(merged) or {}
    if lc_payload:
        lc_payload = repair_lc_mt700_dates(dict(lc_payload)) or lc_payload
    workflow_aliases = {"import", "export", "draft", "unknown"}

    payload_lc_type = str(payload.get("lc_type") or "").strip().lower()
    if payload_lc_type in workflow_aliases:
        merged["lc_type"] = payload_lc_type
        if payload.get("lc_type_reason") not in (None, ""):
            merged["lc_type_reason"] = payload.get("lc_type_reason")
        if payload.get("lc_type_confidence") not in (None, ""):
            merged["lc_type_confidence"] = payload.get("lc_type_confidence")
        if payload.get("lc_type_source") not in (None, ""):
            merged["lc_type_source"] = payload.get("lc_type_source")

    for field in ("lc_type_reason", "lc_type_confidence", "lc_type_source"):
        if merged.get(field) in (None, "") and payload.get(field) not in (None, ""):
            merged[field] = payload.get(field)

    if merged.get("lc_type") in (None, ""):
        payload_workflow_fields = resolve_legacy_workflow_lc_fields(payload)
        merged["lc_type"] = payload_workflow_fields["lc_type"]
        if merged.get("lc_type_reason") in (None, ""):
            merged["lc_type_reason"] = payload_workflow_fields["lc_type_reason"]
        if merged.get("lc_type_confidence") in (None, ""):
            merged["lc_type_confidence"] = payload_workflow_fields["lc_type_confidence"]
        if merged.get("lc_type_source") in (None, ""):
            merged["lc_type_source"] = payload_workflow_fields["lc_type_source"]

    if lc_payload:
        for field in (
            "documents_required",
            "required_documents",
            "requirement_conditions",
            "unmapped_requirements",
            "additional_conditions",
            "clauses",
            "clauses_47a",
            "number",
            "lc_number",
            "applicant",
            "beneficiary",
            "ports",
            "goods",
            "goods_items",
            "goods_description",
            "raw_text",
            "issue_date",
            "expiry_date",
            "latest_shipment",
            "latest_shipment_date",
            "place_of_expiry",
            "dates",
            "timeline",
            "mt700",
        ):
            if merged.get(field) in (None, "", [], {}):
                value = lc_payload.get(field)
                if value not in (None, "", [], {}):
                    merged[field] = value

        if merged.get("required_document_types") in (None, "", [], {}):
            required_document_types = infer_required_document_types_from_lc(lc_payload)
            if required_document_types:
                merged["required_document_types"] = required_document_types

    taxonomy_builder = globals().get("build_lc_classification")
    if callable(taxonomy_builder):
        merged["lc_classification"] = taxonomy_builder(merged or lc_payload, payload)

    merged = repair_lc_mt700_dates(merged) or merged

    legacy_workflow_fields = resolve_legacy_workflow_lc_fields(merged, payload)
    merged["lc_type"] = legacy_workflow_fields["lc_type"]
    merged["lc_type_reason"] = legacy_workflow_fields["lc_type_reason"]
    merged["lc_type_confidence"] = legacy_workflow_fields["lc_type_confidence"]
    merged["lc_type_source"] = legacy_workflow_fields["lc_type_source"]

    if merged:
        return merged

    fallback_workflow_fields = resolve_legacy_workflow_lc_fields(lc_payload, payload)
    fallback = {
        "lc_type": fallback_workflow_fields["lc_type"],
        "lc_type_reason": fallback_workflow_fields["lc_type_reason"],
        "lc_type_confidence": fallback_workflow_fields["lc_type_confidence"],
        "lc_type_source": fallback_workflow_fields["lc_type_source"],
        "mt700": (lc_payload or {}).get("mt700") or {"blocks": {}, "raw_text": None, "version": "mt700_v1"},
        "goods": (lc_payload or {}).get("goods") or (lc_payload or {}).get("goods_items") or [],
        "clauses": (lc_payload or {}).get("clauses") or [],
        "documents_required": (lc_payload or {}).get("documents_required") or (lc_payload or {}).get("required_documents") or [],
        "required_document_types": infer_required_document_types_from_lc(lc_payload or {}),
        "requirement_conditions": (lc_payload or {}).get("requirement_conditions") or [],
        "unmapped_requirements": (lc_payload or {}).get("unmapped_requirements") or [],
        "additional_conditions": (lc_payload or {}).get("additional_conditions") or (lc_payload or {}).get("clauses_47a") or [],
        "timeline": [],
        "issues": [],
    }
    return repair_lc_mt700_dates(fallback) or fallback


def build_minimal_lc_structured_output(lc_data: Optional[Dict[str, Any]], context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    lc_data = lc_data or {}
    context = context or {}
    lc_classification = build_lc_classification(lc_data, context) if lc_data else None

    legacy_lc_type = "unknown"
    legacy_lc_type_reason = "No workflow alias extracted from uploaded documents"
    legacy_lc_type_confidence = 0.0
    legacy_lc_type_source = "auto"

    workflow_orientation = ""
    if isinstance(lc_classification, dict):
        workflow_orientation = str(lc_classification.get("workflow_orientation") or "").strip().lower()
    if workflow_orientation in {"import", "export", "draft", "unknown"}:
        legacy_lc_type = workflow_orientation
        if workflow_orientation != "unknown":
            legacy_lc_type_reason = "Derived from canonical workflow_orientation."
            legacy_lc_type_confidence = 0.85
            legacy_lc_type_source = "lc_classification"

    raw_context_lc_type = str(context.get("lc_type") or "").strip().lower()
    if legacy_lc_type == "unknown" and raw_context_lc_type in {"import", "export", "draft", "unknown"}:
        legacy_lc_type = normalize_lc_type(raw_context_lc_type) or "unknown"
        legacy_lc_type_reason = str(context.get("lc_type_reason") or "Preserved workflow alias from request context.")
        legacy_lc_type_confidence = float(context.get("lc_type_confidence") or 0.0)
        legacy_lc_type_source = str(context.get("lc_type_source") or "context")

    return {
        "lc_type": legacy_lc_type,
        "lc_type_reason": legacy_lc_type_reason,
        "lc_type_confidence": legacy_lc_type_confidence,
        "lc_type_source": legacy_lc_type_source,
        "lc_classification": lc_classification,
        "mt700": lc_data.get("mt700") or {"blocks": {}, "raw_text": lc_data.get("raw_text"), "version": "mt700_v1"},
        "goods": lc_data.get("goods") or lc_data.get("goods_items") or [],
        "clauses": lc_data.get("clauses") or lc_data.get("additional_conditions") or [],
        "timeline": [],
        "issues": [],
    }


def build_lc_intake_summary(lc_payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(lc_payload, dict):
        return {}
    lc_payload = repair_lc_mt700_dates(dict(lc_payload)) or lc_payload

    applicant = lc_payload.get("applicant") if isinstance(lc_payload.get("applicant"), dict) else {}
    beneficiary = lc_payload.get("beneficiary") if isinstance(lc_payload.get("beneficiary"), dict) else {}
    amount = lc_payload.get("amount") if isinstance(lc_payload.get("amount"), dict) else {}
    dates = lc_payload.get("dates") if isinstance(lc_payload.get("dates"), dict) else {}
    ports = lc_payload.get("ports") if isinstance(lc_payload.get("ports"), dict) else {}

    summary = {
        "lc_number": lc_payload.get("number") or lc_payload.get("lc_number"),
        "applicant": applicant.get("name") or lc_payload.get("applicant_name"),
        "beneficiary": beneficiary.get("name") or lc_payload.get("beneficiary_name"),
        "currency": amount.get("currency") or lc_payload.get("currency"),
        "amount": amount.get("amount") or lc_payload.get("lc_amount") or lc_payload.get("amount_value"),
        "issue_date": dates.get("issue_date") or dates.get("issue") or lc_payload.get("issue_date"),
        "expiry_date": dates.get("expiry_date") or dates.get("expiry") or lc_payload.get("expiry_date"),
        "latest_shipment_date": dates.get("latest_shipment_date") or dates.get("latest_shipment") or lc_payload.get("latest_shipment_date") or lc_payload.get("latest_shipment"),
        "port_of_loading": ports.get("port_of_loading") or lc_payload.get("port_of_loading"),
        "port_of_discharge": ports.get("port_of_discharge") or lc_payload.get("port_of_discharge"),
    }
    return {key: value for key, value in summary.items() if value not in (None, "", [], {})}


__all__ = [
    "extract_intake_only",
    "coerce_text_list",
    "infer_required_document_types_from_lc",
    "resolve_legacy_workflow_lc_fields",
    "prepare_extractor_outputs_for_structured_result",
    "build_minimal_lc_structured_output",
    "build_lc_intake_summary",
]
