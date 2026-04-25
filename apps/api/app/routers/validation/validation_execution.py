"""Validation execution stage extracted from pipeline_runner.py."""

from __future__ import annotations

import asyncio
import re
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from app.services.facts import (
    apply_bl_fact_graph_to_validation_inputs,
    apply_coo_fact_graph_to_validation_inputs,
    apply_insurance_fact_graph_to_validation_inputs,
    apply_inspection_fact_graph_to_validation_inputs,
    apply_invoice_fact_graph_to_validation_inputs,
    apply_lc_fact_graph_to_validation_inputs,
    apply_packing_list_fact_graph_to_validation_inputs,
    materialize_document_fact_graph_v1,
    project_insurance_validation_context,
)


_SHARED_NAMES = [
    'Any',
    'Company',
    'CompanyStatus',
    'Decimal',
    'EntitlementError',
    'EntitlementService',
    'HTTPException',
    'PlanType',
    'SessionStatus',
    'UsageAction',
    'ValidationGate',
    '_build_blocked_structured_result',
    '_build_document_summaries',
    '_build_issue_dedup_key',
    '_build_lc_baseline_from_context',
    '_build_processing_summary',
    '_compute_invoice_amount_bounds',
    '_determine_company_size',
    '_extract_request_user_type',
    '_resolve_invoice_amount_tolerance_percent',
    '_response_shaping',
    'apply_bank_policy',
    'build_issue_cards',
    'build_lc_classification',
    'calculate_overall_extraction_confidence',
    'detect_bank_from_lc',
    'func',
    'get_bank_profile',
    'json',
    'logger',
    'parse_lc_requirements_sync_v2',
    'status',
    'time',
    'validate_document_async',
]

DB_RULE_TIMEOUT_SECONDS = 60.0
PRICE_VERIFICATION_TIMEOUT_SECONDS = 25.0
AI_VALIDATION_TIMEOUT_SECONDS = 45.0
BANK_POLICY_TIMEOUT_SECONDS = 20.0

_ICC_RULEBOOK_PREFIXES = {
    "UCP600",
    "ISBP745",
    "ISP98",
    "URR725",
    "URDG758",
    "URC522",
    "EUCP",
}
_ICC_RULE_ID_PATTERN = re.compile(
    r"^(?P<prefix>[A-Z0-9]+)-(?P<article>[A-Z]*\d+)(?P<suffix>[A-Z][A-Z0-9]*)?$"
)
_OVERLAP_DOC_ALIASES = {
    "air_waybill": "bill_of_lading",
    "bill_of_lading": "bill_of_lading",
    "commercial_invoice": "invoice",
    "credit": "lc",
    "insurance": "insurance",
    "insurance_certificate": "insurance",
    "insurance_doc": "insurance",
    "insurance_policy": "insurance",
    "invoice": "invoice",
    "lc": "lc",
    "letter_of_credit": "lc",
    "ocean_bill_of_lading": "bill_of_lading",
    "transport": "bill_of_lading",
    "transport_document": "bill_of_lading",
}
_OVERLAP_FIELD_ALIASES = {
    "applicant": "applicant",
    "applicant_name": "applicant",
    "beneficiary": "beneficiary",
    "beneficiary_name": "beneficiary",
    "buyer": "applicant",
    "buyer_name": "applicant",
    "currency": "currency",
    "currency_code": "currency",
    "description": "goods_description",
    "document_text": "exact_wording",
    "exact_wording": "exact_wording",
    "goods_description": "goods_description",
    "issuer": "issuer",
    "issuer_name": "issuer",
    "lc_number": "lc_reference",
    "lc_reference": "lc_reference",
    "number_of_originals": "originals_presented",
    "original_count": "originals_presented",
    "originals_issued": "originals_required",
    "originals_presented": "originals_presented",
    "originals_required": "originals_required",
    "pol": "port_of_loading",
    "pod": "port_of_discharge",
    "port_of_discharge": "port_of_discharge",
    "port_of_loading": "port_of_loading",
    "product_description": "goods_description",
    "required_wording": "exact_wording",
    "seller": "issuer",
    "seller_name": "issuer",
    "shipment_date": "on_board_date",
    "on_board_date": "on_board_date",
    "latest_shipment": "latest_shipment_date",
    "latest_shipment_date": "latest_shipment_date",
}
_INSURANCE_COVERAGE_SOURCE_FIELDS = {"insured_amount", "coverage_amount", "sum_insured"}
_INSURANCE_COVERAGE_TARGET_FIELDS = {
    "amount",
    "credit_amount",
    "value",
    "invoice_amount",
    "total_amount",
    "total",
    "cif_amount",
    "invoice_value",
}

_INSURANCE_RULE_DOCUMENT_TYPES = {
    "insurance_certificate",
    "insurance_policy",
    "beneficiary_certificate",
    "beneficiary_statement",
}


_FALSE_POSITIVE_MISSING_PATTERNS = re.compile(
    r"(?:not\s+(?:available|provided|submitted|found|included|present|uploaded))"
    r"|(?:missing\s+(?:required\s+)?document)"
    r"|(?:document\s+(?:not|missing|absent))"
    r"|(?:no\s+\w+\s+(?:was|has been)\s+(?:provided|submitted|uploaded))"
    # "No commercial invoice available to verify", "no packing list provided for review"
    # — observed Opus-veto anomaly phrasings that slipped past the earlier patterns.
    r"|(?:no\s+(?:\w+\s+){1,4}(?:available|provided|submitted|present|uploaded|found|attached)\s+(?:to\s+(?:verify|review|check|confirm)|for\s+(?:verification|review)))"
    r"|(?:unable\s+to\s+(?:verify|review|check|confirm).*(?:upon\s+receipt|not\s+(?:yet\s+)?(?:provided|submitted|available)))"
    r"|(?:verify\s+upon\s+receipt)",
    re.IGNORECASE,
)

_DOC_TYPE_LABEL_MAP = {
    "commercial_invoice": {"invoice", "commercial_invoice", "commercial invoice"},
    "invoice": {"invoice", "commercial_invoice", "commercial invoice"},
    "bill_of_lading": {"bill_of_lading", "bill of lading", "bl", "b/l", "ocean_bill_of_lading"},
    "air_waybill": {"air_waybill", "air waybill", "awb"},
    "insurance_certificate": {"insurance_certificate", "insurance certificate", "insurance", "insurance_policy"},
    "insurance_policy": {"insurance_policy", "insurance policy", "insurance", "insurance_certificate"},
    "insurance": {"insurance", "insurance_certificate", "insurance_policy"},
    "certificate_of_origin": {"certificate_of_origin", "certificate of origin", "coo", "c/o"},
    "packing_list": {"packing_list", "packing list", "pl"},
    "inspection_certificate": {"inspection_certificate", "inspection certificate"},
    "beneficiary_certificate": {"beneficiary_certificate", "beneficiary certificate"},
    "draft": {"draft", "bill_of_exchange", "bill of exchange"},
}


def _filter_ai_false_positive_missing_docs(
    ai_issues: list,
    documents: list,
    extracted_context: Dict[str, Any],
) -> list:
    """
    Suppress AI findings that claim a document is missing/unavailable
    when it actually exists in the submission. This prevents the common
    LLM hallucination: "commercial invoice not available".
    """
    if not ai_issues:
        return ai_issues

    # Build set of all submitted document types (normalized)
    submitted_types: set[str] = set()
    for doc in (documents or []):
        dt = str(doc.get("document_type") or doc.get("type") or doc.get("doc_type") or "").strip().lower()
        if dt:
            submitted_types.add(dt)
            # Add aliases
            aliases = _DOC_TYPE_LABEL_MAP.get(dt, set())
            submitted_types.update(aliases)

    # Also check extracted_context top-level keys
    for key in ("invoice", "bill_of_lading", "insurance", "certificate_of_origin", "packing_list",
                "insurance_certificate", "insurance_policy", "inspection_certificate", "beneficiary_certificate"):
        val = extracted_context.get(key)
        if isinstance(val, dict) and val:
            submitted_types.add(key)
            aliases = _DOC_TYPE_LABEL_MAP.get(key, set())
            submitted_types.update(aliases)

    if not submitted_types:
        return ai_issues

    filtered = []
    suppressed = 0
    for issue in ai_issues:
        issue_dict = issue.to_dict() if hasattr(issue, "to_dict") else (issue if isinstance(issue, dict) else {})
        title = str(issue_dict.get("title") or "").lower()
        found_text = str(issue_dict.get("found") or issue_dict.get("actual") or "").lower()
        message = str(issue_dict.get("message") or "").lower()
        combined = f"{title} {found_text} {message}"

        # Check if the finding claims a doc is missing
        if _FALSE_POSITIVE_MISSING_PATTERNS.search(combined):
            # Check if any of the referenced doc types are actually submitted
            doc_names = issue_dict.get("documents") or issue_dict.get("document_names") or []
            is_false_positive = False
            for doc_name in doc_names:
                dn = str(doc_name).strip().lower().replace(" ", "_")
                if dn in submitted_types:
                    is_false_positive = True
                    break
                # Check label map
                for canonical, aliases in _DOC_TYPE_LABEL_MAP.items():
                    if dn in aliases and canonical in submitted_types:
                        is_false_positive = True
                        break
                if is_false_positive:
                    break

            # Also match by title mentioning a doc type that's present
            if not is_false_positive:
                for dt in submitted_types:
                    readable = dt.replace("_", " ")
                    if readable in title or dt in title:
                        is_false_positive = True
                        break

            if is_false_positive:
                suppressed += 1
                logger.info(
                    "Suppressed AI false positive (doc present in submission): %s",
                    issue_dict.get("title") or issue_dict.get("rule_id"),
                )
                continue

        filtered.append(issue)

    if suppressed:
        logger.warning(
            "Suppressed %d AI false-positive 'document missing' findings", suppressed
        )
    return filtered


def _derive_ai_layer_verdict(
    *,
    executed: bool,
    critical_issues: int = 0,
    major_issues: int = 0,
    timed_out: bool = False,
) -> str:
    if not executed:
        return "not_run"
    if timed_out:
        return "review"
    if critical_issues > 0:
        return "reject"
    if major_issues > 0:
        return "warn"
    return "pass"


def _build_ai_validation_layers(
    ai_metadata: Dict[str, Any],
    *,
    timed_out: bool = False,
) -> Dict[str, Dict[str, Any]]:
    metadata = ai_metadata if isinstance(ai_metadata, dict) else {}
    checks_performed = [
        str(item).strip()
        for item in (metadata.get("checks_performed") or [])
        if str(item).strip()
    ]
    checks_seen = set(checks_performed)

    l1_checks = [
        check
        for check in ("lc_requirement_parsing", "document_completeness")
        if check in checks_seen
    ]
    l2_checks = [
        check
        for check in ("bl_field_validation", "packing_list_validation")
        if check in checks_seen
    ]
    l3_checks = [
        check
        for check in ("advanced_anomaly_review",)
        if check in checks_seen
    ]

    l1_issue_count = int(metadata.get("missing_critical_docs", 0) or 0)
    l2_bl_issues = int(metadata.get("bl_missing_fields", 0) or 0)
    l2_packing_issues = int(metadata.get("packing_list_issues", 0) or 0)
    l2_issue_count = l2_bl_issues + l2_packing_issues

    l1_executed = bool(l1_checks)
    l2_executed = bool(l2_checks)
    l3_issue_count = int(metadata.get("l3_issue_count", 0) or 0)
    l3_critical_issues = int(metadata.get("l3_critical_issues", 0) or 0)
    l3_major_issues = int(metadata.get("l3_major_issues", 0) or 0)
    l3_minor_issues = int(metadata.get("l3_minor_issues", 0) or 0)
    l3_executed = bool(l3_checks)

    timed_out_reason = "timed_out" if timed_out else None

    return {
        "l1": {
            "layer": "L1",
            "label": "Document Completeness",
            "executed": l1_executed,
            "verdict": _derive_ai_layer_verdict(
                executed=l1_executed,
                critical_issues=l1_issue_count,
                timed_out=timed_out,
            ),
            "issue_count": l1_issue_count,
            "critical_issues": l1_issue_count,
            "major_issues": 0,
            "minor_issues": 0,
            "checks_performed": l1_checks,
            "reason": timed_out_reason if l1_executed else ("timed_out" if timed_out else "not_triggered"),
            "evidence": {
                "required_critical_docs": list(metadata.get("required_critical_docs") or []),
                "missing_critical_docs": l1_issue_count,
            },
        },
        "l2": {
            "layer": "L2",
            "label": "Requirement-To-Document Checks",
            "executed": l2_executed,
            "verdict": _derive_ai_layer_verdict(
                executed=l2_executed,
                major_issues=l2_issue_count,
                timed_out=timed_out,
            ),
            "issue_count": l2_issue_count,
            "critical_issues": 0,
            "major_issues": l2_issue_count,
            "minor_issues": 0,
            "checks_performed": l2_checks,
            "reason": timed_out_reason if l2_executed else ("timed_out" if timed_out else "not_triggered"),
            "evidence": {
                "bl_must_show": list(metadata.get("bl_must_show") or []),
                "bl_missing_fields": l2_bl_issues,
                "packing_list_issues": l2_packing_issues,
            },
        },
        "l3": {
            "layer": "L3",
            "label": "Advanced Anomaly Review",
            "executed": l3_executed,
            "verdict": _derive_ai_layer_verdict(
                executed=l3_executed,
                critical_issues=l3_critical_issues,
                major_issues=l3_major_issues,
                timed_out=timed_out,
            ),
            "issue_count": l3_issue_count,
            "critical_issues": l3_critical_issues,
            "major_issues": l3_major_issues,
            "minor_issues": l3_minor_issues,
            "checks_performed": l3_checks,
            "reason": timed_out_reason if l3_executed else ("timed_out" if timed_out else "not_triggered"),
            "evidence": {
                "documents_reviewed": list(metadata.get("l3_documents_reviewed") or []),
                "documents_reviewed_count": int(metadata.get("l3_documents_reviewed_count", 0) or 0),
                "low_confidence_document_types": list(metadata.get("l3_low_confidence_document_types") or []),
                "low_confidence_count": int(metadata.get("l3_low_confidence_count", 0) or 0),
                "low_confidence_threshold": metadata.get("l3_low_confidence_threshold"),
                "low_confidence_details": list(metadata.get("l3_low_confidence_details") or []),
            },
        },
    }


def _insurance_document_type(document: Dict[str, Any]) -> str:
    return str(
        document.get("document_type")
        or document.get("documentType")
        or document.get("type")
        or ""
    ).strip().lower()


def _insurance_rule_context_has_originals(context: Dict[str, Any]) -> bool:
    if not isinstance(context, dict):
        return False

    for key in ("originals_presented", "number_of_originals", "original_count"):
        value = context.get(key)
        if value not in (None, "", []):
            return True

    fact_graph = context.get("fact_graph_v1") or context.get("factGraphV1")
    if isinstance(fact_graph, dict):
        for fact in fact_graph.get("facts") or []:
            if not isinstance(fact, dict):
                continue
            if str(fact.get("field_name") or "").strip().lower() != "originals_presented":
                continue
            value = fact.get("normalized_value")
            if value in (None, "", []):
                value = fact.get("value")
            if value not in (None, "", []):
                return True

    return False


def _resolve_insurance_rule_context(
    payload: Dict[str, Any],
    extracted_context: Dict[str, Any],
) -> Tuple[Dict[str, Any], str]:
    existing = (
        payload.get("insurance")
        or payload.get("insurance_certificate")
        or extracted_context.get("insurance")
        or extracted_context.get("insurance_certificate")
    )
    if isinstance(existing, dict) and existing and _insurance_rule_context_has_originals(existing):
        return existing, "existing_alias"

    for document_group in (
        payload.get("documents"),
        extracted_context.get("documents"),
    ):
        if not isinstance(document_group, list):
            continue
        for document in document_group:
            if not isinstance(document, dict):
                continue
            if _insurance_document_type(document) not in _INSURANCE_RULE_DOCUMENT_TYPES:
                continue

            fact_graph = document.get("fact_graph_v1") or document.get("factGraphV1")
            if not isinstance(fact_graph, dict):
                fact_graph = materialize_document_fact_graph_v1(document)

            projected = project_insurance_validation_context(
                existing if isinstance(existing, dict) else None,
                document=document,
                fact_graph=fact_graph if isinstance(fact_graph, dict) else None,
            )
            if not isinstance(projected, dict) or not projected:
                continue

            payload["insurance"] = projected
            payload["insurance_certificate"] = projected
            extracted_context["insurance"] = projected
            extracted_context["insurance_certificate"] = projected
            return projected, "rebuilt_from_documents"

    return (existing if isinstance(existing, dict) else {}), "missing"


def _project_invoice_goods_correspondence(
    payload: Dict[str, Any],
    extracted_context: Dict[str, Any],
    lc_context: Dict[str, Any],
) -> Dict[str, Any]:
    invoice_context = payload.get("invoice")
    if not isinstance(invoice_context, dict) or not invoice_context:
        return {}
    if not isinstance(lc_context, dict) or not lc_context:
        return invoice_context

    invoice_goods = (
        invoice_context.get("goods_description")
        or invoice_context.get("description")
        or invoice_context.get("product_description")
    )
    mt700 = lc_context.get("mt700") if isinstance(lc_context.get("mt700"), dict) else {}
    lc_goods = (
        lc_context.get("goods_description")
        or mt700.get("goods_description")
        or mt700.get("45A")
    )
    if not invoice_goods or not lc_goods:
        return invoice_context

    from app.services.validation.crossdoc_validator import CrossDocValidator

    invoice_issue = CrossDocValidator()._check_invoice_goods(
        invoice_context,
        {"goods_description": lc_goods},
    )
    projected = dict(invoice_context)
    projected["goods_description_matches_lc"] = invoice_issue is None

    payload["invoice"] = projected
    if isinstance(extracted_context.get("invoice"), dict):
        extracted_context["invoice"] = dict(extracted_context["invoice"], goods_description_matches_lc=projected["goods_description_matches_lc"])

    return projected


async def _build_db_rule_watch_debug(
    *,
    domain: str,
    jurisdiction: str,
    document_data: Dict[str, Any],
    watch_rule_ids: tuple[str, ...] = ("UCP600-28", "UCP600-28A"),
) -> Dict[str, Any]:
    """
    Inspect a few specific normalized DB rules against the exact runtime payload.

    This is a narrow live breadcrumb for diagnosing staged rule imports without
    widening the main validation contract.
    """
    from app.services.rule_evaluator import RuleEvaluator
    from app.services.rules_service import get_rules_service
    from app.services.validator import _ruleset_lookup_jurisdictions

    rules_service = get_rules_service()
    resolved_jurisdiction = jurisdiction
    ruleset_data = None
    for lookup_jurisdiction in _ruleset_lookup_jurisdictions(domain, jurisdiction):
        ruleset_data = await rules_service.get_active_ruleset(
            domain,
            lookup_jurisdiction,
            document_type=None,
        )
        if isinstance(ruleset_data, dict):
            resolved_jurisdiction = lookup_jurisdiction
            break
    if not isinstance(ruleset_data, dict):
        return {
            "domain": domain,
            "jurisdiction": jurisdiction,
            "error": "ruleset_unavailable",
        }

    rules = ruleset_data.get("rules") or []
    if not isinstance(rules, list):
        rules = []

    evaluator = RuleEvaluator()
    watched: Dict[str, Any] = {}
    for rule_id in watch_rule_ids:
        rule = next(
            (
                candidate
                for candidate in rules
                if isinstance(candidate, dict)
                and str(candidate.get("rule_id") or "").strip().upper() == rule_id.upper()
            ),
            None,
        )
        if not isinstance(rule, dict):
            watched[rule_id] = {"present": False}
            continue

        field_paths = []
        for condition in rule.get("conditions") or []:
            if not isinstance(condition, dict):
                continue
            for key in ("field", "path", "left_path", "right_path", "reference_field", "value_ref", "computed_field"):
                candidate = condition.get(key)
                if isinstance(candidate, str) and candidate not in field_paths:
                    field_paths.append(candidate)

        resolved_fields = {
            path: evaluator.resolve_field_path(document_data, path)
            for path in field_paths
        }
        outcome = evaluator.evaluate_rule(rule, document_data)
        watched[rule_id] = {
            "present": True,
            "domain": rule.get("domain"),
            "document_type": rule.get("document_type"),
            "rule_type": rule.get("rule_type"),
            "consequence_class": rule.get("consequence_class"),
            "execution_priority": rule.get("execution_priority"),
            "parent_rule": rule.get("parent_rule"),
            "condition_count": len(rule.get("conditions") or []),
            "resolved_fields": resolved_fields,
            "outcome": {
                "passed": outcome.get("passed"),
                "not_applicable": outcome.get("not_applicable"),
                "message": outcome.get("message"),
            },
        }

    ruleset_meta = ruleset_data.get("ruleset") if isinstance(ruleset_data.get("ruleset"), dict) else {}
    return {
        "domain": domain,
        "jurisdiction": jurisdiction,
        "resolved_jurisdiction": resolved_jurisdiction,
        "ruleset_version": ruleset_data.get("ruleset_version") or ruleset_meta.get("ruleset_version"),
        "rulebook_version": ruleset_data.get("rulebook_version") or ruleset_meta.get("rulebook_version"),
        "rules_count": len(rules),
        "watched_rules": watched,
    }


def _shared_get(shared: Any, name: str) -> Any:
    if isinstance(shared, dict):
        return shared[name]
    return getattr(shared, name)


def bind_shared(shared: Any) -> None:
    namespace = globals()
    missing_bindings: list[str] = []
    for name in _SHARED_NAMES:
        if name in namespace:
            continue
        try:
            namespace[name] = _shared_get(shared, name)
        except (KeyError, AttributeError):
            missing_bindings.append(name)
    if missing_bindings:
        raise RuntimeError(
            "Missing shared bindings for validation.validation_execution: "
            + ", ".join(sorted(missing_bindings))
        )


class _DeferredValidationFlow(Exception):
    """Short-circuit final validation stages while extraction resolution remains open."""


async def _await_with_timeout(stage_label: str, coro, timeout_seconds: float, default: Any):
    try:
        return await asyncio.wait_for(coro, timeout_seconds), False
    except asyncio.TimeoutError:
        logger.warning(
            "%s timed out after %.1fs; continuing with degraded fallback",
            stage_label,
            timeout_seconds,
        )
        return default, True


def _build_timeout_event(
    *,
    stage: str,
    label: str,
    timeout_seconds: float,
    fallback: str,
    source: str = "validation_execution",
) -> dict[str, Any]:
    return {
        "stage": stage,
        "label": label,
        "timeout_seconds": float(timeout_seconds),
        "fallback": fallback,
        "source": source,
    }


def _append_timeout_event(
    timeout_events: list[dict[str, Any]],
    *,
    stage: str,
    label: str,
    timeout_seconds: float,
    fallback: str,
    source: str = "validation_execution",
) -> None:
    timeout_events.append(
        _build_timeout_event(
            stage=stage,
            label=label,
            timeout_seconds=timeout_seconds,
            fallback=fallback,
            source=source,
        )
    )


def _should_defer_final_validation(documents: Any) -> Dict[str, Any]:
    workflow_stage = _response_shaping.build_workflow_stage(
        documents if isinstance(documents, list) else [],
        validation_status="review",
    )
    stage_is_extraction_resolution = (
        str(workflow_stage.get("stage") or "").strip().lower() == "extraction_resolution"
    )
    # When the tiered AI pipeline is enabled, the AI layers are the judge of
    # missing / invalid fields — do NOT skip validation just because the
    # upstream preparser flagged unresolved critical fields. The workflow stage
    # is still reported for UI purposes (presentation_contract.py), but the
    # execution path runs to completion so tiered AI + deterministic + Opus
    # veto all get a chance to produce findings.
    from app.config import settings as _app_settings
    bypass_gate = bool(getattr(_app_settings, "VALIDATION_TIERED_AI_ENABLED", False))
    defer = stage_is_extraction_resolution and not bypass_gate
    return {
        "defer": defer,
        "workflow_stage": workflow_stage,
        "bypass_reason": "tiered_ai_enabled" if (stage_is_extraction_resolution and bypass_gate) else None,
    }


def _filter_price_issues_for_documentary_context(
    existing_issues: list[dict[str, Any]],
    price_issues: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Keep documentary findings primary when the goods baseline itself is already
    inconsistent. In that state, price verification is advisory and should not
    add duplicate noise to the SME-facing LC findings path.
    """
    if not price_issues:
        return []

    existing_rules = set()
    for issue in existing_issues:
        if isinstance(issue, dict):
            rule_token = issue.get("rule") or issue.get("rule_id")
        else:
            rule_token = getattr(issue, "rule", None) or getattr(issue, "rule_id", None)
        rule_token = str(rule_token or "").strip().upper()
        if rule_token:
            existing_rules.add(rule_token)
        overlap_keys = issue.get("overlap_keys") if isinstance(issue, dict) else None
        if isinstance(overlap_keys, list):
            for key in overlap_keys:
                if str(key or "").strip() == "invoice.goods_description|lc.goods_description":
                    return []
    if existing_rules.intersection({"CROSSDOC-INV-003", "CROSSDOC-GOODS-1"}):
        return []

    return price_issues


def _parse_icc_rule_identity(issue: Any) -> Optional[tuple[str, str, bool]]:
    if isinstance(issue, dict):
        rule_token = issue.get("rule") or issue.get("rule_id")
        ruleset_domain = issue.get("ruleset_domain")
    else:
        rule_token = getattr(issue, "rule", None) or getattr(issue, "rule_id", None)
        ruleset_domain = getattr(issue, "ruleset_domain", None)

    rule_text = str(rule_token or "").strip().upper()
    if not rule_text:
        return None

    domain_text = str(ruleset_domain or "").strip().lower()
    prefix = rule_text.split("-", 1)[0]
    if not (
        domain_text.startswith("icc.")
        or prefix in _ICC_RULEBOOK_PREFIXES
    ):
        return None

    match = _ICC_RULE_ID_PATTERN.match(rule_text)
    if not match:
        return None

    return (
        match.group("prefix"),
        match.group("article"),
        bool(match.group("suffix")),
    )


def _suppress_broad_icc_umbrella_rules(
    issues: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Prefer actionable ICC letter rules over fallback umbrella doctrine rows.
    If an umbrella row belongs to a family that already has specific child rules
    in the active ruleset, do not surface the umbrella as a user-facing finding.
    """
    if not issues:
        return []

    specific_families: set[tuple[str, str]] = set()
    umbrella_with_specific_family_rules_present = False
    requirement_backed_documentary_issue_present = False
    crossdoc_documentary_issue_present = False
    for issue in issues:
        identity = _parse_icc_rule_identity(issue)
        if identity and identity[2]:
            specific_families.add((identity[0], identity[1]))
        if bool(issue.get("has_specific_family_rules")):
            umbrella_with_specific_family_rules_present = True
        domain = str(issue.get("ruleset_domain") or "").strip().lower()
        rule_id = str(issue.get("rule") or issue.get("rule_id") or "").strip().upper()
        requirement_source = str(issue.get("requirement_source") or "").strip().lower()
        requirement_kind = (
            str(issue.get("requirement_kind") or "")
            .strip()
            .lower()
            .replace("-", "_")
            .replace(" ", "_")
        )
        if (
            domain.startswith("icc.lcopilot.crossdoc")
            and requirement_source == "requirements_graph_v1"
            and requirement_kind in {
                "document_exact_wording",
                "document_field_presence",
                "document_quantity",
                "identifier_presence",
            }
        ):
            requirement_backed_documentary_issue_present = True
        if domain.startswith("icc.lcopilot.crossdoc") and rule_id.startswith(
            ("CROSSDOC-", "DOCSET-")
        ):
            crossdoc_documentary_issue_present = True

    if (
        not specific_families
        and not umbrella_with_specific_family_rules_present
        and not requirement_backed_documentary_issue_present
        and not crossdoc_documentary_issue_present
    ):
        return issues

    filtered: list[dict[str, Any]] = []
    for issue in issues:
        domain = str(issue.get("ruleset_domain") or "").strip().lower()
        rule_type = str(issue.get("rule_type") or "").strip().lower()
        execution_priority = str(issue.get("execution_priority") or "").strip().lower()
        consequence_class = str(issue.get("consequence_class") or "").strip().lower()
        if (
            rule_type == "umbrella"
            and execution_priority == "fallback"
            and consequence_class == "domain_logic"
            and bool(issue.get("has_specific_family_rules"))
        ):
            continue
        identity = _parse_icc_rule_identity(issue)
        if (
            (requirement_backed_documentary_issue_present or crossdoc_documentary_issue_present)
            and identity
            and not identity[2]
            and domain.startswith("icc.")
            and not domain.startswith("icc.lcopilot.crossdoc")
            and (
                rule_type == "umbrella"
                or (execution_priority == "fallback" and consequence_class == "domain_logic")
            )
        ):
            continue
        if identity and not identity[2] and (identity[0], identity[1]) in specific_families:
            continue
        filtered.append(issue)

    return filtered


def _normalize_overlap_doc_token(value: Any) -> Optional[str]:
    token = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if not token:
        return None
    return _OVERLAP_DOC_ALIASES.get(token, token)


def _normalize_overlap_field_token(value: Any) -> Optional[str]:
    token = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if not token:
        return None
    if "." in token:
        token = token.split(".")[-1]
    return _OVERLAP_FIELD_ALIASES.get(token, token)


def _build_overlap_key(
    source_doc: Any,
    source_field: Any,
    target_doc: Any,
    target_field: Any,
) -> Optional[str]:
    source_doc_token = _normalize_overlap_doc_token(source_doc)
    target_doc_token = _normalize_overlap_doc_token(target_doc)
    source_field_token = _normalize_overlap_field_token(source_field)
    target_field_token = _normalize_overlap_field_token(target_field)
    if not (source_doc_token and source_field_token and target_doc_token and target_field_token):
        return None
    if (
        source_doc_token == "insurance"
        and source_field_token in _INSURANCE_COVERAGE_SOURCE_FIELDS
        and target_doc_token in {"lc", "invoice"}
        and target_field_token in _INSURANCE_COVERAGE_TARGET_FIELDS
    ) or (
        target_doc_token == "insurance"
        and target_field_token in _INSURANCE_COVERAGE_SOURCE_FIELDS
        and source_doc_token in {"lc", "invoice"}
        and source_field_token in _INSURANCE_COVERAGE_TARGET_FIELDS
    ):
        return "insurance.insured_amount|insurance.minimum_required_coverage"
    terms = sorted(
        [
            f"{source_doc_token}.{source_field_token}",
            f"{target_doc_token}.{target_field_token}",
        ]
    )
    return "|".join(terms)


def _extract_issue_overlap_keys(issue: Dict[str, Any]) -> List[str]:
    overlap_keys = issue.get("overlap_keys")
    if isinstance(overlap_keys, list):
        normalized = [str(key).strip() for key in overlap_keys if str(key).strip()]
        if normalized:
            return normalized

    key = _build_overlap_key(
        issue.get("source_doc"),
        issue.get("source_field"),
        issue.get("target_doc"),
        issue.get("target_field"),
    )
    return [key] if key else []


def _suppress_legacy_issue_noise(
    issues: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Remove legacy duplicate findings once a more specific actionable rule exists.

    Also hide LC type uncertainty when the package already has real documentary
    findings; otherwise the user sees two conflicting messages at once.
    """
    if not issues:
        return []

    present_rules: set[str] = set()
    icc_overlap_keys: set[str] = set()
    for issue in issues:
        if not isinstance(issue, dict):
            continue
        rule_id = str(issue.get("rule") or issue.get("rule_id") or "").strip().upper()
        if rule_id:
            present_rules.add(rule_id)
        domain = str(issue.get("ruleset_domain") or "").strip().lower()
        if domain.startswith("icc.") and not domain.startswith("icc.lcopilot.crossdoc"):
            icc_overlap_keys.update(_extract_issue_overlap_keys(issue))

    actionable_issue_present = any(rule_id != "LC-TYPE-UNKNOWN" for rule_id in present_rules)

    filtered: list[dict[str, Any]] = []
    for issue in issues:
        if not isinstance(issue, dict):
            continue
        rule_id = str(issue.get("rule") or issue.get("rule_id") or "").strip().upper()
        if rule_id == "LC-TYPE-UNKNOWN" and actionable_issue_present:
            continue
        domain = str(issue.get("ruleset_domain") or "").strip().lower()
        issue_overlap_keys = set(_extract_issue_overlap_keys(issue))
        if (
            domain.startswith("icc.lcopilot.crossdoc")
            and issue_overlap_keys
            and icc_overlap_keys.intersection(issue_overlap_keys)
        ):
            continue
        cleaned_issue = dict(issue)
        cleaned_issue.pop("overlap_keys", None)
        filtered.append(cleaned_issue)

    return filtered


def _recover_validation_db_session(db: Any) -> None:
    """
    Clear failed SQLAlchemy transaction state before post-validation assembly.

    Validation intentionally swallows some non-fatal stage errors so the request
    can still return useful findings. If one of those errors poisoned the active
    DB transaction, the next DB access would fail far away from the original
    stage. A rollback here is safe because validation_execution does not rely on
    uncommitted DB writes from the earlier runtime stages.
    """
    rollback = getattr(db, "rollback", None)
    if callable(rollback):
        rollback()


async def execute_validation_pipeline(
    *,
    request,
    current_user,
    db,
    payload,
    files_list,
    doc_type,
    checkpoint,
    start_time,
    setup_state,
):
    validation_session = setup_state["validation_session"]
    job_id = setup_state["job_id"]
    extracted_context = setup_state["extracted_context"]
    lc_context = setup_state["lc_context"]
    lc_type = setup_state["lc_type"]
    lc_type_is_unknown = setup_state["lc_type_is_unknown"]

    # V2 VALIDATION PIPELINE - PRIMARY FLOW
    # This is the core validation engine. Legacy flow is disabled.
    # If LC extraction fails (missing critical fields), we block validation.
    # =====================================================================
    v2_gate_result = None
    v2_baseline = None
    v2_issues = []
    v2_crossdoc_issues = []
    ai_issues = []
    ai_validation_summary = None
    defer_final_validation = False
    workflow_stage_hint = None
    timeout_events: list[dict[str, Any]] = []

    try:
        lc_context = apply_lc_fact_graph_to_validation_inputs(payload, extracted_context)
        setup_state["lc_context"] = lc_context
        apply_invoice_fact_graph_to_validation_inputs(payload, extracted_context)
        apply_bl_fact_graph_to_validation_inputs(payload, extracted_context)
        apply_packing_list_fact_graph_to_validation_inputs(payload, extracted_context)
        apply_coo_fact_graph_to_validation_inputs(payload, extracted_context)
        apply_insurance_fact_graph_to_validation_inputs(payload, extracted_context)
        apply_inspection_fact_graph_to_validation_inputs(payload, extracted_context)

        # Build LCBaseline from extracted context
        v2_baseline = _build_lc_baseline_from_context(lc_context)

        # Run validation gate
        v2_gate = ValidationGate()
        v2_gate_result = v2_gate.check_from_baseline(v2_baseline)

        logger.info(
            "V2 Validation Gate: status=%s can_proceed=%s completeness=%.1f%% critical=%.1f%%",
            v2_gate_result.status.value,
            v2_gate_result.can_proceed,
            v2_gate_result.completeness * 100,
            v2_gate_result.critical_completeness * 100,
        )
        checkpoint("validation_gate_complete")

        # =====================================================================
        # BLOCKED RESPONSE - Return immediately if gate blocks
        # This is the key fix: NO more "100% compliant with N/A fields"
        # =====================================================================
        if not v2_gate_result.can_proceed:
            logger.warning(
                "V2 Gate BLOCKED: %s. Missing critical: %s",
                v2_gate_result.block_reason,
                v2_gate_result.missing_critical,
            )

            # Build blocked response
            processing_duration = time.time() - start_time
            blocked_result = _build_blocked_structured_result(
                v2_gate_result=v2_gate_result,
                v2_baseline=v2_baseline,
                lc_type=lc_type,
                processing_duration=processing_duration,
                documents=payload.get("documents") or [],
            )

            # Store blocked result in validation session so it can be retrieved later
            if validation_session:
                validation_session.status = SessionStatus.COMPLETED.value
                validation_session.processing_completed_at = func.now()
                validation_session.validation_results = {
                    "structured_result": blocked_result,
                    "validation_blocked": True,
                    "block_reason": v2_gate_result.block_reason,
                }
                db.commit()

            return {
                "job_id": str(job_id),
                "jobId": str(job_id),
                "structured_result": blocked_result,
                "telemetry": {
                    "validation_blocked": True,
                    "block_reason": v2_gate_result.block_reason,
                    "timings": {},
                    "total_time_seconds": round(time.time() - start_time, 3),
                },
            }
        # =====================================================================

        # Gate passed - run v2 IssueEngine (without full rule execution)
        from app.services.validation.issue_engine import IssueEngine

        # Create IssueEngine without RuleExecutor to avoid running all 2,159 rules
        # Full rule execution is DISABLED due to false positives from country-specific rules
        issue_engine = IssueEngine()

        v2_issues = issue_engine.generate_extraction_issues(v2_baseline)
        logger.info("V2 IssueEngine generated %d extraction issues", len(v2_issues))

        # =================================================================
        # CLAUSE-BASED DOCUMENT MATCHING (46A/47A → per-doc fields)
        #
        # This is the LOCAL deterministic engine — `doc_matcher` +
        # `crossdoc_validator` running UCP rules in-process. It exists as
        # a fallback for when RulHub isn't available.
        #
        # RulHub (api.rulhub.com, 7800+ rules across UCP / ISBP / URDG /
        # ISP98 / sanctions / country / bank / TBML) is the authoritative
        # source of deterministic findings. When USE_RULHUB_API=True the
        # RulHub path below at `_use_rulhub` produces the findings and
        # this local engine is skipped — running both merges a worse,
        # less-complete duplicate on top of the real answer.
        # =================================================================
        from app.config import settings as _local_engine_settings
        _rulhub_primary = bool(
            getattr(_local_engine_settings, "USE_RULHUB_API", False)
        ) and bool(getattr(_local_engine_settings, "RULHUB_API_KEY", ""))

        if _rulhub_primary:
            logger.info(
                "Local doc_matcher + crossdoc_validator SKIPPED (USE_RULHUB_API=True). "
                "Findings will come from RulHub's /v1/validate/set."
            )
        else:
            try:
                from app.services.validation.clause_parser import parse_lc_clauses
                from app.services.validation.doc_matcher import (
                    match_clauses_to_documents,
                    check_cross_document_consistency,
                )

                lc_docs_required = (
                    lc_context.get("documents_required")
                    or lc_context.get("documents_required_detailed")
                    or (extracted_context.get("lc") or {}).get("documents_required")
                    or []
                )
                lc_addl_conditions = (
                    lc_context.get("additional_conditions")
                    or (extracted_context.get("lc") or {}).get("additional_conditions")
                    or []
                )

                parsed_clauses = parse_lc_clauses(lc_docs_required, lc_addl_conditions)

                all_extracted_docs = (
                    extracted_context.get("documents")
                    or payload.get("documents")
                    or []
                )

                clause_findings = match_clauses_to_documents(parsed_clauses, all_extracted_docs)
                crossdoc_findings = check_cross_document_consistency(
                    lc_context or {},
                    all_extracted_docs,
                )

                for finding in clause_findings + crossdoc_findings:
                    v2_issues.append({
                        "id": f"{finding.source_layer}_{finding.document}_{finding.field}",
                        "title": f"{finding.expected}",
                        "severity": finding.severity,
                        "documents": [finding.document],
                        "expected": finding.expected,
                        "found": finding.found,
                        "suggested_fix": finding.suggested_fix,
                        "description": finding.explanation,
                        "reference": finding.rule,
                        "ucp_reference": finding.rule,
                        "lc_clause": finding.lc_clause,
                        "impact": finding.impact,
                        "source_layer": finding.source_layer,
                        "field_name": finding.field,
                    })

                logger.info(
                    "Local clause matcher (fallback): %d clause findings + %d crossdoc findings",
                    len(clause_findings), len(crossdoc_findings),
                )
            except Exception:
                logger.exception("Local clause-based matching failed — continuing without")

        workflow_stage_hint = _should_defer_final_validation(
            payload.get("documents") or extracted_context.get("documents") or []
        )
        defer_final_validation = bool(workflow_stage_hint.get("defer"))
        bypass_reason = workflow_stage_hint.get("bypass_reason")
        if bypass_reason:
            logger.info(
                "Extraction_resolution stage detected but bypassing defer gate (%s) — tiered AI pipeline will run and judge missing fields itself.",
                bypass_reason,
            )
        if defer_final_validation:
            db_rule_issues = []
            db_rules_debug = {
                "enabled": False,
                "status": "deferred",
                "reason": "extraction_resolution",
                "workflow_stage": workflow_stage_hint.get("workflow_stage"),
            }
            bank_profile = None
            requirement_graph = None
            extraction_confidence_summary = None
            ai_validation_summary = {
                "issue_count": 0,
                "critical_issues": 0,
                "major_issues": 0,
                "minor_issues": 0,
                "documents_checked": len(payload.get("documents") or extracted_context.get("documents") or []),
                "derived_ai_verdict": "review",
                "metadata": {"deferred": True, "reason": "extraction_resolution"},
                "timed_out": False,
                "deferred": True,
                "reason": "extraction_resolution",
            }
            logger.info(
                "Deferring final validation stages while extraction remains unresolved: %s",
                (workflow_stage_hint.get("workflow_stage") or {}).get("summary"),
            )
            raise _DeferredValidationFlow()

        lc_ctx = extracted_context.get("lc") or payload.get("lc") or {}
        requirements_graph_v1 = payload.get("requirements_graph_v1")
        if not isinstance(requirements_graph_v1, dict):
            requirements_graph_v1 = _response_shaping.build_requirements_graph_v1(
                payload.get("documents") or extracted_context.get("documents") or []
            )
        if isinstance(lc_ctx, dict) and isinstance(requirements_graph_v1, dict):
            lc_ctx.setdefault("requirements_graph_v1", requirements_graph_v1)
            lc_ctx.setdefault("requirementsGraphV1", requirements_graph_v1)
        if isinstance(lc_ctx, dict) and not isinstance(lc_ctx.get("lc_classification"), dict):
            lc_ctx["lc_classification"] = build_lc_classification(lc_ctx, payload)
        mt700 = lc_ctx.get("mt700") or {}

        # =================================================================
        # AI VALIDATION ENGINE (AI-FIRST EXECUTION)
        # =================================================================
        from app.services.validation.ai_validator import run_ai_validation

        lc_data_for_ai = {}

        lc_context = extracted_context.get("lc") or {}
        lc_raw_text = (
            lc_context.get("raw_text")
            or extracted_context.get("lc_text")
            or (payload.get("lc") or {}).get("raw_text")
            or ""
        )
        lc_data_for_ai["raw_text"] = lc_raw_text
        logger.info(f"AI Validation: LC raw_text length = {len(lc_raw_text)} chars")

        lc_data_for_ai["goods_description"] = (
            lc_context.get("goods_description")
            or mt700.get("goods_description")
            or mt700.get("45A")
            or ""
        )
        logger.info(f"AI Validation: goods_description length = {len(lc_data_for_ai['goods_description'])} chars")

        lc_data_for_ai["goods"] = (
            lc_context.get("goods")
            or lc_context.get("goods_items")
            or mt700.get("goods")
            or []
        )
        lc_data_for_ai["requirements_graph_v1"] = (
            lc_context.get("requirements_graph_v1")
            or lc_context.get("requirementsGraphV1")
            or payload.get("requirements_graph_v1")
            or extracted_context.get("requirements_graph_v1")
        )

        documents_for_ai = (
            extracted_context.get("documents")
            or payload.get("documents")
            or []
        )
        logger.info(f"AI Validation: {len(documents_for_ai)} documents to check")

        # Skip ai_validator when RulHub is primary — its deterministic
        # checks (packing-list size breakdown, BL field validation,
        # document completeness) are subsets of what RulHub's rule
        # inventory already covers via /v1/validate/set. Running both
        # duplicates the same check from two engines with different
        # wordings and mismatches on overlap.
        # Middle-layer AI runs regardless of USE_RULHUB_API status.
        # RulHub enforces generic UCP600 rules; the AI layer enforces
        # THIS-LC's own 46A/47A clauses (BL field requirements per the
        # LC, per-LC document completeness, packing-list size breakdown)
        # that RulHub cannot know about. Complementary, not redundant.
        (ai_issues, ai_metadata), ai_validation_timed_out = await _await_with_timeout(
            "AI validation",
            run_ai_validation(
                lc_data=lc_data_for_ai,
                documents=documents_for_ai,
                extracted_context=extracted_context,
            ),
            AI_VALIDATION_TIMEOUT_SECONDS,
            ([], {"timed_out": True}),
        )
        if not isinstance(ai_metadata, dict):
            ai_metadata = {}

        # --- Filter AI false positives: suppress "document missing/unavailable"
        #     claims when the document is actually present in the submission ---
        ai_issues = _filter_ai_false_positive_missing_docs(ai_issues, documents_for_ai, extracted_context)

        logger.info(
            "AI Validation: found %d issues (critical=%d, major=%d)",
            len(ai_issues),
            ai_metadata.get("critical_issues", 0),
            ai_metadata.get("major_issues", 0),
        )
        ai_validation_layers = _build_ai_validation_layers(
            ai_metadata,
            timed_out=ai_validation_timed_out,
        )
        ai_validation_summary = {
            "issue_count": len(ai_issues),
            "critical_issues": int(ai_metadata.get("critical_issues", 0) or 0),
            "major_issues": int(ai_metadata.get("major_issues", 0) or 0),
            "minor_issues": int(ai_metadata.get("minor_issues", 0) or 0),
            "documents_checked": len(documents_for_ai) if isinstance(documents_for_ai, list) else 0,
            "derived_ai_verdict": (
                "reject" if int(ai_metadata.get("critical_issues", 0) or 0) > 0 else (
                "warn" if int(ai_metadata.get("major_issues", 0) or 0) > 0 else "pass"
                )
            ),
            "layer_contract_version": "ai_layers_v1",
            "execution_position": "pre_deterministic_runtime",
            "layers": ai_validation_layers,
            "metadata": ai_metadata or {},
            "timed_out": ai_validation_timed_out,
        }
        if ai_validation_timed_out:
            _append_timeout_event(
                timeout_events,
                stage="ai_validation",
                label="AI validation",
                timeout_seconds=AI_VALIDATION_TIMEOUT_SECONDS,
                fallback="ai_issues_skipped",
            )
        checkpoint("ai_validation_complete")

        # =================================================================
        # EXECUTE DATABASE RULES (2500+ rules from DB)
        # Filters by jurisdiction, document_type, and domain
        # =================================================================
        db_rule_issues = []
        db_rules_debug = {"enabled": False, "status": "not_started"}
        try:
            # =============================================================
            # DYNAMIC JURISDICTION & DOMAIN DETECTION
            # Detects relevant rulesets based on LC and document content
            # =============================================================
            coo = payload.get("certificate_of_origin") or {}
            invoice = payload.get("invoice") or {}
            bl = payload.get("bill_of_lading") or {}
            insurance_rule_context, insurance_rule_context_source = _resolve_insurance_rule_context(
                payload,
                extracted_context,
            )
            _project_invoice_goods_correspondence(payload, extracted_context, lc_ctx)

            # Country code mapping (common variations)
            COUNTRY_CODE_MAP = {
                "bangladesh": "bd", "peoples republic of bangladesh": "bd",
                "india": "in", "republic of india": "in",
                "china": "cn", "peoples republic of china": "cn", "prc": "cn",
                "united states": "us", "usa": "us", "united states of america": "us",
                "united arab emirates": "ae", "uae": "ae",
                "saudi arabia": "sa", "kingdom of saudi arabia": "sa",
                "singapore": "sg", "republic of singapore": "sg",
                "hong kong": "hk", "hong kong sar": "hk",
                "germany": "de", "federal republic of germany": "de",
                "united kingdom": "uk", "great britain": "uk", "gb": "uk",
                "japan": "jp", "turkey": "tr", "pakistan": "pk",
                "indonesia": "id", "malaysia": "my", "thailand": "th",
                "vietnam": "vn", "philippines": "ph", "south korea": "kr",
                "brazil": "br", "mexico": "mx", "egypt": "eg",
            }

            def normalize_country(country_str: str) -> str:
                """Convert country name/code to 2-letter ISO code."""
                if not country_str:
                    return ""
                country_lower = country_str.lower().strip()
                # Already a 2-letter code?
                if len(country_lower) == 2:
                    return country_lower
                return COUNTRY_CODE_MAP.get(country_lower, "")

            # Detect jurisdictions from multiple sources
            detected_jurisdictions = set()

            # From LC
            for field in ["jurisdiction", "country", "issuing_bank_country", "advising_bank_country"]:
                val = normalize_country(lc_ctx.get(field, "") or mt700.get(field, ""))
                if val:
                    detected_jurisdictions.add(val)

            # From beneficiary (exporter) - usually the exporter's country matters most
            beneficiary = lc_ctx.get("beneficiary") or mt700.get("beneficiary") or {}
            if isinstance(beneficiary, dict):
                val = normalize_country(beneficiary.get("country", ""))
                if val:
                    detected_jurisdictions.add(val)
            elif isinstance(beneficiary, str):
                # Try to extract country from address string
                for country, code in COUNTRY_CODE_MAP.items():
                    if country in beneficiary.lower():
                        detected_jurisdictions.add(code)
                        break

            # From Certificate of Origin
            origin_country = normalize_country(
                coo.get("country_of_origin") or 
                coo.get("origin_country") or 
                coo.get("country") or ""
            )
            if origin_country:
                detected_jurisdictions.add(origin_country)

            # From Invoice seller address
            seller_country = normalize_country(
                invoice.get("seller_country") or
                invoice.get("exporter_country") or ""
            )
            if seller_country:
                detected_jurisdictions.add(seller_country)

            # From B/L port of loading (often indicates export country)
            port_of_loading = (bl.get("port_of_loading") or "").lower()
            if "chittagong" in port_of_loading or "dhaka" in port_of_loading or "mongla" in port_of_loading:
                detected_jurisdictions.add("bd")
            elif "shanghai" in port_of_loading or "shenzhen" in port_of_loading or "ningbo" in port_of_loading:
                detected_jurisdictions.add("cn")
            elif "mumbai" in port_of_loading or "chennai" in port_of_loading or "nhava sheva" in port_of_loading:
                detected_jurisdictions.add("in")

            # Build supplement domains dynamically
            supplement_domains = ["icc.isbp745", "icc.lcopilot.crossdoc"]

            # Add jurisdiction-specific regulations
            for jur in detected_jurisdictions:
                if jur and jur != "global":
                    supplement_domains.append(f"regulations.{jur}")

            # Add sanctions screening
            supplement_domains.append("sanctions.screening")

            # Primary jurisdiction priority: CoO origin > invoice seller >
            # any LC-detected country > current user's Company.country (from
            # onboarding) > "global". The Company.country fallback ensures
            # a BD-onboarded user gets BD rule packs even when the LC text
            # itself doesn't carry an explicit country signal — common on
            # ISO 20022 LCs and bare-bones MT700 drafts.
            primary_jurisdiction = "global"
            company_country_fallback = ""
            try:
                if current_user and current_user.company and current_user.company.country:
                    company_country_fallback = (current_user.company.country or "").lower().strip()
            except Exception:  # noqa: BLE001 — defensive against detached session
                company_country_fallback = ""

            if origin_country:
                primary_jurisdiction = origin_country
            elif seller_country:
                primary_jurisdiction = seller_country
            elif detected_jurisdictions:
                primary_jurisdiction = list(detected_jurisdictions)[0]
            elif company_country_fallback and len(company_country_fallback) == 2:
                primary_jurisdiction = company_country_fallback
                detected_jurisdictions.add(company_country_fallback)
                if company_country_fallback != "global":
                    supplement_domains.append(f"regulations.{company_country_fallback}")

            logger.info(
                "Dynamic jurisdiction detection: primary=%s, all=%s, supplements=%s, company_fallback=%s",
                primary_jurisdiction, list(detected_jurisdictions), supplement_domains, company_country_fallback
            )

            # Build document data for rule engine
            db_rule_payload = {
                "jurisdiction": primary_jurisdiction,
                "domain": "icc.ucp600",
                "supplement_domains": supplement_domains,
                # LC data
                "lc": lc_ctx,
                "credit": lc_ctx,
                "beneficiary": (lc_ctx or {}).get("beneficiary") if isinstance(lc_ctx, dict) else None,
                "lc_number": v2_baseline.lc_number if v2_baseline else None,
                "amount": v2_baseline.amount if v2_baseline else None,
                "currency": v2_baseline.currency if v2_baseline else None,
                "expiry_date": v2_baseline.expiry_date if v2_baseline else None,
                # Documents
                "invoice": payload.get("invoice"),
                "bill_of_lading": payload.get("bill_of_lading"),
                "insurance": insurance_rule_context,
                "insurance_doc": insurance_rule_context,
                "certificate_of_origin": payload.get("certificate_of_origin"),
                "packing_list": payload.get("packing_list"),
                # Extracted context
                "extracted_context": extracted_context,
                "requirements_graph_v1": requirements_graph_v1 if isinstance(requirements_graph_v1, dict) else None,
            }

            # Determine primary document type for filtering
            primary_doc_type = "letter_of_credit"
            if payload.get("invoice"):
                primary_doc_type = "commercial_invoice"

            logger.info(
                "Executing DB rules: jurisdiction=%s, domain=icc.ucp600, supplements=%s, doc_type=%s",
                primary_jurisdiction, supplement_domains, primary_doc_type
            )

            rule_watch_debug = None
            try:
                rule_watch_debug = await _build_db_rule_watch_debug(
                    domain="icc.ucp600",
                    jurisdiction=primary_jurisdiction,
                    document_data=db_rule_payload,
                    watch_rule_ids=("UCP600-18", "UCP600-18A", "UCP600-18D", "UCP600-20C", "UCP600-20D", "UCP600-20E", "UCP600-28", "UCP600-28A", "UCP600-28E"),
                )
            except Exception as rule_watch_err:
                rule_watch_debug = {"error": str(rule_watch_err)}

            # =============================================================
            # RULHUB API PATH (when USE_RULHUB_API=True)
            # Delegates rule evaluation to api.rulhub.com instead of
            # running local tiered validation. Falls back to DB path.
            # =============================================================
            from app.config import settings as _app_settings
            _use_rulhub = getattr(_app_settings, "USE_RULHUB_API", False)
            db_rules_timed_out = False

            if _use_rulhub:
                try:
                    from app.services.rulhub_client import RulHubRulesAdapter

                    # ---------------------------------------------------------
                    # PROPER multi-doc validation via POST /v1/validate/set.
                    # RulHub has 7800+ rules across UCP/ISBP/URDG/sanctions/
                    # country/bank profiles. The /v1/validate/set endpoint
                    # runs cross-doc consistency checks against the merged
                    # doc namespace (lc.amount, invoice.total_amount, bl.pol,
                    # etc.) — doing this properly means sending EACH doc as
                    # its own entry, not folding everything into a single
                    # "lc" blob like the old single-doc /validate call did.
                    # ---------------------------------------------------------
                    def _jsonable_value(v):
                        if v is None:
                            return None
                        if hasattr(v, 'value'):
                            return v.value
                        if hasattr(v, 'model_dump'):
                            return v.model_dump()
                        return v

                    def _flatten_doc_fields(raw: Any) -> Dict[str, Any]:
                        """Collapse confidence-wrapped or nested dicts into a
                        flat scalar dict RulHub can evaluate on."""
                        if not isinstance(raw, dict):
                            return {}
                        flat: Dict[str, Any] = {}
                        for k, v in raw.items():
                            if k.startswith("_") or k in {
                                "raw_text", "extraction_artifacts_v1",
                                "fact_graph_v1", "factGraphV1",
                                "rawText", "extractionArtifactsV1",
                                "requirements_graph_v1",
                            }:
                                continue
                            v = _jsonable_value(v)
                            if isinstance(v, dict):
                                # confidence-wrap {"value": ..., "confidence": ...}
                                if "value" in v and "confidence" in v:
                                    flat[k] = v.get("value")
                                else:
                                    # keep structured dict for rules that use dotted paths
                                    flat[k] = v
                            else:
                                flat[k] = v
                        return flat

                    # Build the document list in RulHub's expected shape.
                    # Include the LC first (its canonical fields feed every
                    # cross-doc rule), then each supporting doc under its
                    # canonical document_type.
                    _rulhub_docs: List[Dict[str, Any]] = []

                    _lc_fields = _flatten_doc_fields(lc_ctx) if isinstance(lc_ctx, dict) else {}
                    # Make sure the spine fields the rules key off are present
                    for _k in ("lc_number", "amount", "currency", "expiry_date",
                               "issue_date", "latest_shipment_date",
                               "port_of_loading", "port_of_discharge",
                               "beneficiary", "applicant", "incoterm",
                               "goods_description"):
                        if _k not in _lc_fields:
                            _val = lc_ctx.get(_k) if isinstance(lc_ctx, dict) else None
                            if _val is None and v2_baseline is not None:
                                _val = getattr(v2_baseline, _k, None)
                            _lc_fields[_k] = _jsonable_value(_val)
                    # Canonical doc-type map → the exact key RulHub wants
                    # in the ``documents[]`` envelope. RulHub server (post
                    # commits eaa5605f + ae6c8004, 2026-04-17) resolves rule
                    # dialects transparently: ``credit.*`` ↔ ``lc.*``,
                    # ``commercial_invoice.*`` ↔ ``invoice.*``,
                    # ``marine_bl.*`` ↔ ``bl.*``, etc. So trdrhub sends
                    # each doc ONCE under its canonical key. Do not retrofit
                    # dialect permutations.
                    _CANONICAL_PREFIX_MAP = {
                        "invoice": "invoice",
                        "commercial_invoice": "invoice",
                        "bill_of_lading": "bl",
                        "bl": "bl",
                        "packing_list": "packing_list",
                        "certificate_of_origin": "coo",
                        "coo": "coo",
                        "insurance_certificate": "insurance_doc",
                        "insurance_policy": "insurance_doc",
                        "insurance_doc": "insurance_doc",
                        "insurance": "insurance_doc",
                        "inspection_certificate": "inspection_certificate",
                        "beneficiary_certificate": "beneficiary_certificate",
                        "draft": "draft",
                    }

                    # Extractor-to-canonical field renames. Only rename where
                    # trdrhub's extractor uses a non-canonical name for a
                    # canonical concept (e.g., ``seller`` → ``issuer_name``,
                    # ``shipped_on_board_date`` → ``on_board_date``). Do NOT
                    # add dialect-permutation aliases; server handles those.
                    _FIELD_ALIASES_FOR_RULHUB = {
                        "lc": {
                            "incoterm": "incoterms",
                            "latest_shipment": "latest_shipment_date",
                            "applicant": "applicant_name",
                            "beneficiary": "beneficiary_name",
                            "currency": "currency_code",
                            "goods": "goods_description",
                        },
                        "invoice": {
                            "invoice_date": "date",
                            "seller": "issuer_name",
                            "invoice_amount": "amount",
                            "total_amount": "amount",
                            "incoterm": "incoterms",
                            "buyer": "buyer_name",
                            "applicant": "applicant_name",
                            "beneficiary": "beneficiary_name",
                            "currency": "currency_code",
                            "goods": "goods_description",
                            "line_total_sum": "line_items_sum",
                        },
                        "bl": {
                            "shipped_on_board_date": "on_board_date",
                            "bl_date": "on_board_date",
                            "shipment_date": "on_board_date",
                            "freight": "freight_terms",
                            "transshipment": "transhipment",
                            "shipper": "shipper_name",
                            "consignee": "consignee_name",
                            "notify_party": "notify_party_name",
                            "carrier": "carrier_name",
                        },
                        "coo": {
                            "issuing_authority": "issuer_name",
                            "certifying_authority": "issuer_name",
                            "hs_codes": "hs_code",
                            "consignee": "consignee_name",
                            "exporter": "exporter_name",
                            "importer": "importer_name",
                        },
                        "insurance_doc": {
                            "issue_date": "effective_date",
                            "risks": "risks_covered",
                            "currency": "currency_code",
                            "insurer": "insurer_name",
                            "amount": "insured_amount",
                            "coverage_amount": "insured_amount",
                        },
                        "packing_list": {
                            "total_packages": "total_cartons",
                            "number_of_packages": "total_cartons",
                            "packages": "total_cartons",
                        },
                        "draft": {
                            "drawee": "drawee_name",
                        },
                    }

                    def _apply_rulhub_aliases(rulhub_type: str, fields: Dict[str, Any]) -> Dict[str, Any]:
                        aliases = _FIELD_ALIASES_FOR_RULHUB.get(rulhub_type, {})
                        if not aliases:
                            return fields
                        enriched = dict(fields)
                        for src, dst in aliases.items():
                            if src not in enriched:
                                continue
                            _v = enriched[src]
                            if _v is None or _v == "" or _v == []:
                                continue
                            if dst not in enriched:
                                enriched[dst] = _v
                        return enriched

                    # ---- Derived booleans ---------------------------------
                    # UCP600 rules key off booleans that no extractor emits
                    # directly (lc.is_transferred, lc.partial_shipments_permitted,
                    # bill_of_lading.on_board_notation_present, ...). Derive
                    # them from the raw extracted fields we already have.
                    #
                    # RulHub has a silent-pass bug where null paths are
                    # treated as matching null → every rule touching an
                    # undefined boolean silently awards its weight. Sending
                    # a real True/False kicks the rule into firing properly.
                    def _str_contains(val: Any, *needles: str) -> bool:
                        if val is None:
                            return False
                        s = str(val).upper()
                        return any(n.upper() in s for n in needles)

                    def _derive_lc_booleans(lc_fields: Dict[str, Any]) -> Dict[str, Any]:
                        derived: Dict[str, Any] = {}
                        partial = lc_fields.get("partial_shipments")
                        if partial is not None:
                            derived["partial_shipments_permitted"] = (
                                _str_contains(partial, "ALLOWED", "PERMITTED")
                                and not _str_contains(partial, "NOT ALLOWED", "NOT PERMITTED", "PROHIB")
                            )
                        trans = lc_fields.get("transshipment") or lc_fields.get("transhipment")
                        if trans is not None:
                            prohibited = _str_contains(
                                trans, "NOT ALLOWED", "NOT PERMITTED", "PROHIB"
                            )
                            derived["transhipment_prohibited"] = prohibited
                            derived["transhipment_allowed"] = not prohibited
                        form = lc_fields.get("form_of_documentary_credit") or lc_fields.get("form_of_doc_credit")
                        if form is not None:
                            derived["irrevocable"] = _str_contains(form, "IRREVOCABLE")
                            derived["is_transferred"] = _str_contains(form, "TRANSFER")
                        rules_txt = lc_fields.get("applicable_rules") or lc_fields.get("ucp_reference")
                        if rules_txt is not None:
                            derived["subject_to_ucp"] = _str_contains(rules_txt, "UCP")
                        # Full-set-of-originals requirement is a 46A property
                        # ("FULL SET OF CLEAN ON BOARD OCEAN BILLS OF LADING").
                        docs_req = lc_fields.get("documents_required")
                        addl = lc_fields.get("additional_conditions")
                        blob_parts: List[str] = []
                        if isinstance(docs_req, (list, tuple)):
                            blob_parts.extend(str(x) for x in docs_req if x)
                        elif docs_req:
                            blob_parts.append(str(docs_req))
                        if isinstance(addl, (list, tuple)):
                            blob_parts.extend(str(x) for x in addl if x)
                        elif addl:
                            blob_parts.append(str(addl))
                        blob = " ".join(blob_parts).upper()
                        if blob:
                            derived["full_set_required"] = "FULL SET" in blob
                            derived["insurance_all_risks_required"] = (
                                "ALL RISKS" in blob or "ALL-RISKS" in blob
                            )
                            derived["insurance_prohibited"] = False
                            # CROSSDOC-PL-PER-CARTON-001 keys off this LC-side
                            # boolean. 46A or 47A wording demanding a
                            # carton-by-carton packing breakdown looks like
                            # "PACKING LIST IN ... ORIGINALS SHOWING CARTONWISE
                            # BREAKDOWN" or "PER CARTON DETAILS".
                            derived["packing_list_per_carton_required"] = any(
                                p in blob
                                for p in (
                                    "PER CARTON",
                                    "PER-CARTON",
                                    "CARTON-WISE",
                                    "CARTONWISE",
                                    "EACH CARTON",
                                    "CARTON BY CARTON",
                                    "CARTON-BY-CARTON",
                                )
                            )
                        # RulHub vocab for credit.type is the UCP600 Article 1
                        # enum: documentary_credit / standby_credit. SWIFT MT700
                        # Field 40A spells the same concept as IRREVOCABLE /
                        # IRREVOCABLE TRANSFERABLE / IRREVOCABLE STANDBY.
                        # Translate to RulHub vocab so UCP600-1 actually
                        # confirms instead of silent-passing.
                        form_for_type = (
                            lc_fields.get("form_of_documentary_credit")
                            or lc_fields.get("form_of_doc_credit")
                            or lc_fields.get("lc_type")
                        )
                        if form_for_type:
                            form_upper = str(form_for_type).upper()
                            if "STANDBY" in form_upper:
                                derived["type"] = "standby_credit"
                            else:
                                derived["type"] = "documentary_credit"
                        return derived

                    def _derive_bl_booleans(
                        bl_fields: Dict[str, Any],
                        bl_raw_text: str,
                        lc_derived: Dict[str, Any],
                    ) -> Dict[str, Any]:
                        derived: Dict[str, Any] = {}
                        # "On board" notation is present when we captured a
                        # shipped-on-board date OR the raw text literally
                        # contains the ON BOARD wording. Absence of both is
                        # a real discrepancy we want RulHub to flag.
                        onboard_date = (
                            bl_fields.get("shipped_on_board_date")
                            or bl_fields.get("on_board_date")
                            or bl_fields.get("shipment_date")
                        )
                        raw_text = bl_raw_text or ""
                        derived["on_board_notation_present"] = bool(onboard_date) or (
                            "ON BOARD" in str(raw_text).upper()
                        )
                        # Carrier identification — either an explicit carrier
                        # field or "CARRIER" in the signature block.
                        derived["carrier_identified"] = bool(
                            bl_fields.get("carrier")
                            or bl_fields.get("carrier_name")
                        ) or ("CARRIER" in str(raw_text).upper())
                        # Clean-on-board / clean BL — a truly "claused" BL
                        # would have defect wording we don't extract yet; so
                        # default to clean when on_board is present and no
                        # "CLAUSED" / "DIRTY" hit in raw text.
                        clean_signal = ("CLEAN" in str(raw_text).upper()) or derived["on_board_notation_present"]
                        dirty_signal = _str_contains(raw_text, "CLAUSED", "DIRTY")
                        if clean_signal or dirty_signal:
                            derived["clean_on_board"] = clean_signal and not dirty_signal
                            # RulHub rules use both ``clean_on_board`` and
                            # ``clean_bl`` as field names. Mirror so either
                            # path resolves.
                            derived["clean_bl"] = derived["clean_on_board"]
                        # Propagate LC transhipment posture so BL-side rules
                        # can compare against it without re-walking the LC.
                        if "transhipment_allowed" in lc_derived:
                            derived.setdefault("transhipment_allowed", lc_derived["transhipment_allowed"])
                        # Full set is an LC-imposed requirement — mirror so
                        # BL-prefixed rules see it.
                        if "full_set_required" in lc_derived:
                            derived["full_set_required"] = lc_derived["full_set_required"]
                        return derived

                    # ---- Semantic / conditional precomputations -----------
                    # UCP600-18D asks for ``invoice.goods_description_matches_lc``
                    # as a precomputed boolean. Compute via lightweight token
                    # overlap against the LC goods_description. Emit only when
                    # both sides have values (otherwise leave null so the
                    # rule silently passes rather than falsely fails).
                    def _normalize_tokens(text: Any) -> set:
                        if not text:
                            return set()
                        import re as _re
                        s = str(text).lower()
                        s = _re.sub(r"[^a-z0-9\s/.-]", " ", s)
                        toks = [t for t in s.split() if len(t) >= 3]
                        return set(toks)

                    def _goods_match_boolean(lc_goods: Any, inv_goods: Any) -> Optional[bool]:
                        a = _normalize_tokens(lc_goods)
                        b = _normalize_tokens(inv_goods)
                        if not a or not b:
                            return None
                        # UCP600 Art 18(c): invoice description must
                        # "correspond" to LC description. We accept if the
                        # smaller token set is ≥60% contained in the larger.
                        overlap = len(a & b)
                        smaller = min(len(a), len(b))
                        return (overlap / smaller) >= 0.6 if smaller else None

                    # ---- Per-doc ORIGINAL/COPY marking + signature presence -
                    # ISBP821-A31 (invoice unsigned) and similar rules check
                    # whether the presented document is marked ORIGINAL and
                    # carries a visible signature block. Extraction is a blind
                    # transcriber and doesn't emit these as discrete fields,
                    # so we derive from raw_text in the RulHub builder.
                    def _derive_doc_metadata(
                        fields: Dict[str, Any],
                        raw_text: str,
                    ) -> Dict[str, Any]:
                        derived: Dict[str, Any] = {}
                        raw_upper = str(raw_text or "").upper()
                        if not raw_upper:
                            return derived
                        # Markings live in headers/footers/stamps — sample
                        # the first and last 600 chars to cut noise.
                        head_tail = raw_upper[:600] + " " + raw_upper[-600:]
                        if "ORIGINAL" in head_tail:
                            derived["original_marking"] = "ORIGINAL"
                        elif "DUPLICATE" in head_tail:
                            derived["original_marking"] = "DUPLICATE"
                        elif "TRIPLICATE" in head_tail:
                            derived["original_marking"] = "TRIPLICATE"
                        elif "COPY" in head_tail:
                            derived["original_marking"] = "COPY"
                        # Signature presence — only emit True when we see a
                        # clear signature-block marker. Don't emit False on
                        # absence (could just be that the marker phrase
                        # isn't standard).
                        sig_markers = (
                            "AUTHORIZED SIGNATURE",
                            "SIGNED FOR",
                            "FOR AND ON BEHALF",
                            "SIGNATURE OF",
                            "DULY SIGNED",
                            "AUTHORISED SIGNATURE",
                        )
                        if any(m in raw_upper for m in sig_markers):
                            derived["signature"] = True
                        return derived

                    # ---- Packing list per-carton breakdown detection -------
                    # CROSSDOC-PL-PER-CARTON-001 needs to know whether the
                    # packing list itself contains a carton-by-carton table.
                    # The structural flattener collapses ``size_breakdown``
                    # into a SKU-level scalar, so we scan raw_text for
                    # numbered-carton patterns directly.
                    def _derive_packing_per_carton(raw_text: str) -> Dict[str, Any]:
                        derived: Dict[str, Any] = {}
                        raw_upper = str(raw_text or "").upper()
                        if not raw_upper:
                            return derived
                        import re as _re
                        carton_label = len(_re.findall(r"\bCARTON\s*[#]?\s*\d+\b", raw_upper))
                        cn_range = len(_re.findall(r"\bC[/.]?N\s*[:.]?\s*\d+", raw_upper))
                        ctn_no = len(_re.findall(r"\bCTN\s*[#.]?\s*NO\.?\s*\d+", raw_upper))
                        derived["per_carton_detail"] = (
                            carton_label >= 2 or cn_range >= 2 or ctn_no >= 2
                        )
                        return derived

                    # CROSSDOC-INV-MATH-001 wants ``invoice.line_items`` as a
                    # structured list so its computed_amount_comparison rule
                    # can validate Σ(qty × unit_price) == stated total. The
                    # structural flattener in ai_first_extractor collapses
                    # multi-line ``quantity`` arrays into a scalar sum and
                    # multi-line ``unit_price`` lists into comma-joined
                    # strings — neither usable by an arithmetic check.
                    # Rebuild the line-item structure here from whichever
                    # representation the extractor preserved.
                    def _coerce_to_number(v: Any) -> Optional[float]:
                        if v is None or isinstance(v, bool):
                            return None
                        if isinstance(v, (int, float)):
                            return float(v)
                        if isinstance(v, str):
                            s = v.strip().replace(",", "").replace("$", "")
                            try:
                                return float(s)
                            except ValueError:
                                return None
                        return None

                    def _extract_invoice_line_items(
                        invoice_raw: Dict[str, Any],
                        invoice_fields: Dict[str, Any],
                    ) -> Tuple[List[Dict[str, Any]], Optional[float]]:
                        """Return (line_items, computed_total).

                        Looks at ``line_items`` / ``items`` / ``goods_items``
                        plural arrays first (skipped by structural flattener
                        so they survive intact), then falls back to the
                        ``quantity__items`` / ``amount__items`` sidecars.
                        Each item is normalized to numeric
                        ``{quantity, unit_price, line_total}`` with
                        ``line_total`` derived from qty × unit_price when
                        absent. ``computed_total`` is the sum of line_totals,
                        ``None`` if no items had usable numerics.
                        """
                        candidates = (
                            invoice_raw.get("line_items")
                            or invoice_raw.get("items")
                            or invoice_raw.get("goods_items")
                            or invoice_fields.get("quantity__items")
                            or invoice_fields.get("amount__items")
                        )
                        if not isinstance(candidates, list) or not candidates:
                            return [], None
                        cleaned: List[Dict[str, Any]] = []
                        total = 0.0
                        any_counted = False
                        for li in candidates:
                            if not isinstance(li, dict):
                                continue
                            qty = _coerce_to_number(
                                li.get("quantity") or li.get("qty") or li.get("units")
                            )
                            unit = _coerce_to_number(
                                li.get("unit_price") or li.get("price") or li.get("rate")
                            )
                            line_total = _coerce_to_number(
                                li.get("line_total") or li.get("amount") or li.get("total")
                            )
                            if line_total is None and qty is not None and unit is not None:
                                line_total = qty * unit
                            item: Dict[str, Any] = {}
                            if qty is not None:
                                item["quantity"] = qty
                            if unit is not None:
                                item["unit_price"] = unit
                            if line_total is not None:
                                item["line_total"] = line_total
                                total += line_total
                                any_counted = True
                            desc = li.get("description") or li.get("item") or li.get("name")
                            if desc:
                                item["description"] = str(desc)
                            if item:
                                cleaned.append(item)
                        return cleaned, (total if any_counted else None)

                    # UCP600-28E uses ``invoice.cif_amount`` — only meaningful
                    # when LC shipment terms are CIF/CIP (seller responsible
                    # for insurance + freight). Compute a boolean flag we can
                    # use when emitting the invoice doc.
                    _lc_incoterm_raw = (
                        _lc_fields.get("incoterm")
                        or _lc_fields.get("incoterms")
                        or ""
                    )
                    _lc_incoterm_upper = str(_lc_incoterm_raw).upper()
                    _lc_is_cif_or_cip = any(
                        term in _lc_incoterm_upper for term in ("CIF", "CIP")
                    )

                    # Compute LC booleans once — propagated to BL-side rules
                    # that reference them via transhipment_allowed / full_set.
                    _lc_booleans = _derive_lc_booleans(_lc_fields)
                    _lc_fields.update(_lc_booleans)

                    # Re-apply the alias map to the LC fields we built above.
                    _lc_fields = _apply_rulhub_aliases("lc", _lc_fields)

                    # ---- Emit each doc ONCE under its canonical key ------
                    # RulHub server (post eaa5605f + ae6c8004) aliases
                    # credit.* / bill_of_lading.* / insurance.* / marine_bl.*
                    # server-side. Dialect permutations we used to emit are
                    # no-ops now; canonical-only is the contract.
                    _rulhub_docs.append({"type": "lc", "fields": _lc_fields})

                    _seen_canon: set = set()
                    _seen_canon.add("lc")
                    for _src_key in (
                        "invoice",
                        "bill_of_lading",
                        "packing_list",
                        "certificate_of_origin",
                        "insurance_certificate",
                        "insurance",
                        "inspection_certificate",
                        "beneficiary_certificate",
                        "draft",
                    ):
                        _canon = _CANONICAL_PREFIX_MAP.get(_src_key, _src_key)
                        if _canon in _seen_canon:
                            continue
                        _doc_raw = payload.get(_src_key)
                        if not isinstance(_doc_raw, dict) or not _doc_raw:
                            continue
                        _raw_text = _doc_raw.get("raw_text") or ""
                        _fields = _flatten_doc_fields(_doc_raw)
                        # Originality marking + signature presence apply to
                        # every supporting doc — derive once before doc-type
                        # specific work.
                        _doc_meta = _derive_doc_metadata(_fields, _raw_text)
                        for _mk, _mv in _doc_meta.items():
                            _fields.setdefault(_mk, _mv)
                        # Doc-type-specific boolean derivation
                        if _canon == "bl":
                            _fields.update(_derive_bl_booleans(_fields, _raw_text, _lc_booleans))
                        if _canon == "packing_list":
                            _fields.update(_derive_packing_per_carton(_raw_text))
                        if _canon == "insurance_doc":
                            # Ask C #23: split company name from issuer_type
                            # enum. RulHub renamed insurance_doc.issuer to
                            # insurance_doc.issuer_type and the rule now
                            # expects an enum value, not the company name.
                            # Derive from the issuer text we already have.
                            _issuer_text = (
                                _fields.get("issuer")
                                or _fields.get("insurer")
                                or _fields.get("issuer_name")
                                or _fields.get("insurer_name")
                            )
                            if _issuer_text:
                                _s = str(_issuer_text).upper()
                                # RulHub's enum (per UCP600-28 probe):
                                #   insurance_company, underwriter,
                                #   agent_for_insurer, proxy_for_insurer
                                # Brokers fold into agent_for_insurer — RulHub
                                # doesn't carry a separate broker enum value.
                                if "UNDERWRITER" in _s:
                                    _fields.setdefault("issuer_type", "underwriter")
                                elif "PROXY" in _s:
                                    _fields.setdefault("issuer_type", "proxy_for_insurer")
                                elif "AGENT" in _s or "BROKER" in _s:
                                    _fields.setdefault("issuer_type", "agent_for_insurer")
                                else:
                                    _fields.setdefault("issuer_type", "insurance_company")
                            # UCP600-28: insurance must cover at least 110%
                            # of invoice value (or CIF/CIP value) per UCP600
                            # Article 28(f). RulHub's rule is now
                            # numeric_comparison(coverage_percentage, ">=", 110)
                            # so derive coverage_percentage = (insured /
                            # invoice_total) * 100 when both sides have a
                            # number to work with.
                            _inv_raw = payload.get("invoice") if isinstance(payload, dict) else None
                            _inv_total: Optional[float] = None
                            if isinstance(_inv_raw, dict):
                                _inv_total = _coerce_to_number(
                                    _inv_raw.get("total_amount")
                                    or _inv_raw.get("amount")
                                    or _inv_raw.get("invoice_amount")
                                )
                            _ins_amt = _coerce_to_number(
                                _fields.get("insured_amount")
                                or _fields.get("amount")
                                or _fields.get("coverage_amount")
                            )
                            if (
                                _ins_amt and _ins_amt > 0
                                and _inv_total and _inv_total > 0
                                and "coverage_percentage" not in _fields
                            ):
                                _fields["coverage_percentage"] = round(
                                    (_ins_amt / _inv_total) * 100, 2,
                                )
                        if _canon == "invoice":
                            # Semantic goods-match against the LC (UCP600-18D)
                            _gm = _goods_match_boolean(
                                _lc_fields.get("goods_description"),
                                _fields.get("goods_description") or _fields.get("goods"),
                            )
                            if _gm is not None:
                                _fields["goods_description_matches_lc"] = _gm
                            # Conditional CIF amount (UCP600-28E)
                            if _lc_is_cif_or_cip:
                                _inv_amt = (
                                    _fields.get("amount")
                                    or _fields.get("total_amount")
                                    or _fields.get("invoice_amount")
                                )
                                if _inv_amt not in (None, "", []):
                                    _fields.setdefault("cif_amount", _inv_amt)
                            # Line items + computed total for
                            # CROSSDOC-INV-MATH-001. We send line_items as
                            # a List[Dict] (RulHub can iterate) AND a scalar
                            # ``computed_total_from_lines`` (RulHub can
                            # compare directly against ``total_amount``).
                            _line_items, _computed_total = _extract_invoice_line_items(
                                _doc_raw, _fields,
                            )
                            if _line_items:
                                _fields["line_items"] = _line_items
                            if _computed_total is not None:
                                _fields["computed_total_from_lines"] = _computed_total
                        _fields = _apply_rulhub_aliases(_canon, _fields)
                        _rulhub_docs.append({"type": _canon, "fields": _fields})
                        _seen_canon.add(_canon)

                    logger.info(
                        "RulHub /v1/validate/set — %d docs: %s (jurisdiction=%s)",
                        len(_rulhub_docs),
                        [d["type"] for d in _rulhub_docs],
                        primary_jurisdiction,
                    )

                    _rulhub_adapter = RulHubRulesAdapter()
                    _rulhub_result = await _rulhub_adapter.validate_document_set(
                        documents=_rulhub_docs,
                        jurisdiction=primary_jurisdiction,
                    )

                    # /v1/validate/set returns { discrepancies: [...], cross_doc_issues: [...] }.
                    # RulHub's shape differs from the UI mapper's expectations:
                    #   RulHub            → UI mapper expects
                    #   rule_id           → rule
                    #   finding           → title / message
                    #   field_a/value_a   → expected ("<field_a> = <value_a>")
                    #   field_b/value_b   → found    ("<field_b> = <value_b>")
                    #   recommendation    → suggested_fix / suggestion
                    #   documents_involved → documents
                    # Normalise here so downstream code doesn't need to know
                    # which engine produced the finding.
                    # RulHub sometimes returns a finding whose ``finding`` field
                    # is a stringified Python dict of the rule config instead
                    # of a rendered sentence — happens for
                    # ``conditional_logic`` and ``computed_amount_comparison``
                    # rule types when the rule doesn't carry a message
                    # template. When ``field_a`` / ``field_b`` DO carry
                    # evidence, the finding is real and actionable — we just
                    # need to rewrite the title so it doesn't leak the spec.
                    _SPEC_DUMP_PREFIXES = (
                        "conditional_logic: {",
                        "computed_amount_comparison: {",
                    )

                    def _is_spec_dump(msg: str) -> bool:
                        return msg.lstrip().lower().startswith(_SPEC_DUMP_PREFIXES)

                    def _synthesize_title_from_evidence(
                        rule_id: str,
                        field_a: Any,
                        value_a: Any,
                        field_b: Any,
                        value_b: Any,
                    ) -> str:
                        parts: List[str] = []
                        if field_a and value_a is not None:
                            parts.append(f"{field_a} = {value_a}")
                        elif field_a:
                            parts.append(str(field_a))
                        if field_b and value_b is not None:
                            parts.append(f"{field_b} = {value_b}")
                        elif field_b:
                            parts.append(str(field_b))
                        if parts:
                            return f"Rule {rule_id} fired on: " + " vs ".join(parts)
                        return f"Rule {rule_id} fired without concrete evidence"

                    def _normalize_rulhub_finding(r: Dict[str, Any]) -> Dict[str, Any]:
                        if not isinstance(r, dict):
                            return {}
                        rule_id = r.get("rule_id") or r.get("rule") or "RULHUB"
                        finding = r.get("finding") or r.get("message") or ""
                        field_a = r.get("field_a")
                        value_a = r.get("value_a")
                        field_b = r.get("field_b")
                        value_b = r.get("value_b")
                        expected = r.get("expected")
                        found = r.get("found") or r.get("actual")
                        # Rewrite spec-dump finding text into a human title.
                        # The raw finding stays in ``message`` for audit, but
                        # the ``title`` (user-facing card heading) is synthesized
                        # from rule_id + field/value evidence.
                        if _is_spec_dump(str(finding)):
                            title = _synthesize_title_from_evidence(
                                str(rule_id), field_a, value_a, field_b, value_b,
                            )
                        else:
                            title = finding or str(rule_id)
                        if not expected:
                            if field_a and value_a is not None:
                                expected = f"{field_a} = {value_a}"
                            elif field_a:
                                expected = str(field_a)
                        if not found:
                            if field_b and value_b is not None:
                                found = f"{field_b} = {value_b}"
                            elif field_b:
                                found = str(field_b)
                        return {
                            "rule": rule_id,
                            "rule_id": rule_id,
                            "title": title,
                            "severity": (r.get("severity") or "major"),
                            "message": finding,
                            "expected": expected or "",
                            "found": found or "",
                            "suggestion": r.get("recommendation") or r.get("suggestion") or "",
                            "suggested_fix": r.get("recommendation") or r.get("suggested_fix") or "",
                            "documents": r.get("documents_involved") or r.get("documents") or [],
                            "document_names": r.get("documents_involved") or r.get("documents") or [],
                            "ucp_reference": r.get("ucp_reference") or r.get("ucp_article"),
                            "isbp_reference": r.get("isbp_reference") or r.get("isbp_paragraph"),
                            "source_layer": "rulhub",
                            "ruleset_domain": r.get("ruleset_domain") or "rulhub.com",
                            "passed": False,
                            "display_card": True,
                        }

                    _disc = _rulhub_result.get("discrepancies") or []
                    # RulHub's live /v1/validate/set response uses
                    # ``cross_document_discrepancies`` (not the legacy
                    # ``cross_doc_issues`` name that lives in older
                    # server builds and the reference memo). Read both
                    # so trdrhub tolerates either.
                    _cross = (
                        _rulhub_result.get("cross_document_discrepancies")
                        or _rulhub_result.get("cross_doc_issues")
                        or []
                    )

                    # ---- Pre-veto filter: RulHub rule-engine errors ------
                    # RulHub's condition evaluators occasionally return an
                    # error message as a "finding" when a rule threw during
                    # evaluation — e.g. ``"Unknown condition type: X"``,
                    # ``"One or both values are not numeric"``,
                    # ``"presentation_period requires max_days/value"``.
                    #
                    # As of 2026-04-21 RulHub also emits spec-dump findings
                    # when `conditional_logic` / `computed_amount_comparison`
                    # rules fire without a render-able message template —
                    # the ``finding`` field literally begins with
                    # ``"conditional_logic: {"`` or
                    # ``"computed_amount_comparison: {"`` followed by the
                    # rule config JSON. When these fire with NO concrete
                    # evidence (null field_a + field_b + values), they are
                    # rule-engine infrastructure noise. When they DO carry
                    # evidence, ``_normalize_rulhub_finding`` rewrites the
                    # message to a human-readable form (see that function).
                    #
                    # These are infrastructure errors on the rule engine
                    # side, NOT LC discrepancies. They have null
                    # ``field_a``/``field_b`` because the rule never
                    # produced concrete path/value evidence. They pollute
                    # the veto input (Opus has nothing to verify against),
                    # and they never belong in the user-visible list.
                    # Filter them out before normalisation + veto.
                    def _is_rule_engine_error(r: Dict[str, Any]) -> bool:
                        if not isinstance(r, dict):
                            return False
                        if r.get("field_a") or r.get("field_b"):
                            return False  # has path evidence → real
                        if r.get("value_a") is not None or r.get("value_b") is not None:
                            return False
                        msg = str(r.get("finding") or r.get("message") or "").lower()
                        engine_error_phrases = (
                            "unknown condition type",
                            "one or both values are not numeric",
                            "requires max_days",
                            "requires max_days/value",
                            "presentation_period requires",
                            "cannot evaluate",
                            "insufficient_data",
                            "conditional_logic: {",
                            "computed_amount_comparison: {",
                        )
                        return any(p in msg for p in engine_error_phrases)

                    # ---- Pre-veto filter: invalid-value-on-absent-field ----
                    # RulHub fires "'<field>' has an invalid value" warnings
                    # against rule paths trdrhub never emits (entity.role,
                    # credit.concept, credit.honour_method,
                    # document.signature_method, issuer.qualification, ...).
                    # The path is real (so field_a is populated) but
                    # value_a/value_b are null because we sent no value to
                    # judge. The correct semantics is "field missing", not
                    # "invalid value" — RulHub is fixing this server-side
                    # but we filter the noise locally in the meantime.
                    def _is_invalid_value_on_absent_field(r: Dict[str, Any]) -> bool:
                        if not isinstance(r, dict):
                            return False
                        msg = str(r.get("finding") or r.get("message") or "").lower()
                        if "invalid value" not in msg:
                            return False
                        # Real value sent → real finding (e.g. enum mismatch).
                        # value_a == 0 / False are legit values; keep those.
                        if r.get("value_a") not in (None, ""):
                            return False
                        if r.get("value_b") not in (None, ""):
                            return False
                        return True

                    _all_rulhub_findings = list(_disc) + list(_cross)
                    _engine_errors = [
                        r for r in _all_rulhub_findings
                        if _is_rule_engine_error(r) or _is_invalid_value_on_absent_field(r)
                    ]
                    _real_findings = [
                        r for r in _all_rulhub_findings
                        if not _is_rule_engine_error(r)
                        and not _is_invalid_value_on_absent_field(r)
                    ]
                    if _engine_errors:
                        logger.info(
                            "RulHub rule-engine-error findings filtered pre-veto: %d (%s)",
                            len(_engine_errors),
                            ", ".join(
                                str(e.get("rule_id") or "?")[:25]
                                for e in _engine_errors[:8]
                            ),
                        )
                    _raw_findings = [
                        _normalize_rulhub_finding(r) for r in _real_findings
                    ]
                    # Dedup across lc/credit and bl/bill_of_lading duplicate
                    # submissions. Same rule firing on duplicate prefix
                    # entries lands with identical rule_id + expected/found.
                    #
                    # The key uses prefix-normalized ``expected`` / ``found``
                    # strings so that the same rule firing once on
                    # ``lc.amount = X`` and once on ``credit.amount = X``
                    # collapses to a single finding. Same for bl vs
                    # bill_of_lading and insurance vs insurance_doc.
                    _DUAL_PREFIX_PAIRS = (
                        ("credit.", "lc."),            # prefer lc as canonical
                        ("bl.", "bill_of_lading."),    # prefer long as canonical
                        ("insurance.", "insurance_doc."),
                    )

                    def _canonicalize_prefix(text: str) -> str:
                        """Collapse dual-prefix field paths so lc/credit etc. dedup together."""
                        if not text:
                            return ""
                        out = text
                        for src, dst in _DUAL_PREFIX_PAIRS:
                            # Replace both the exact prefix AND within composite strings
                            # (e.g. 'credit.amount = 100' → 'lc.amount = 100').
                            out = out.replace(src, dst)
                        return out

                    _seen_keys: set = set()
                    db_rule_issues: List[Dict[str, Any]] = []
                    for _f in _raw_findings:
                        if not _f:
                            continue
                        _key = (
                            _f.get("rule_id") or _f.get("rule") or "",
                            _canonicalize_prefix(_f.get("title") or ""),
                            _canonicalize_prefix(_f.get("expected") or ""),
                            _canonicalize_prefix(_f.get("found") or ""),
                        )
                        if _key in _seen_keys:
                            continue
                        _seen_keys.add(_key)
                        db_rule_issues.append(_f)
                    logger.info(
                        "RulHub /v1/validate/set → %d discrepancies + %d crossdoc = %d findings (deduped from %d)",
                        len(_disc), len(_cross), len(db_rule_issues), len(_raw_findings),
                    )
                except Exception as _rulhub_err:
                    logger.warning("RulHub API failed, falling back to DB rules: %s", _rulhub_err)
                    _use_rulhub = False  # fall through to DB path below

            if not _use_rulhub:
                # Three-pass validation pipeline: tiered AI → deterministic rules → Opus veto.
                # When VALIDATION_TIERED_AI_ENABLED and VALIDATION_OPUS_VETO_ENABLED are both
                # off in settings, this delegates to the legacy validate_document_async
                # (deterministic-only) so behavior is unchanged.
                from app.services.validation.tiered_validation import validate_document_with_pipeline
                db_rule_issues, db_rules_timed_out = await _await_with_timeout(
                    "DB rules execution",
                    validate_document_with_pipeline(
                        document_data=db_rule_payload,
                        document_type=primary_doc_type,
                    ),
                    DB_RULE_TIMEOUT_SECONDS,
                    [],
                )

            # Filter out N/A and passed rules, keep only failures
            db_rule_issues = [
                issue for issue in db_rule_issues
                if not issue.get("passed", False) and not issue.get("not_applicable", False)
            ]

            logger.info("DB rules executed: %d issues found (after filtering)", len(db_rule_issues))

            # Store debug info for response
            db_rules_debug = {
                "enabled": True,
                "domain": "icc.ucp600",
                "supplements": supplement_domains,
                "primary_jurisdiction": primary_jurisdiction,
                "detected_jurisdictions": list(detected_jurisdictions),
                "insurance_rule_context_source": insurance_rule_context_source,
                "insurance_rule_context_originals_presented": (
                    insurance_rule_context.get("originals_presented")
                    if isinstance(insurance_rule_context, dict)
                    else None
                ),
                "insurance_rule_context_originals_issued": (
                    insurance_rule_context.get("originals_issued")
                    if isinstance(insurance_rule_context, dict)
                    else None
                ),
                "issues_found": len(db_rule_issues),
                "sample_rule_ids": [
                    str(issue.get("rule") or issue.get("rule_id") or "")
                    for issue in (db_rule_issues or [])[:10]
                    if isinstance(issue, dict)
                ],
                "rule_watch_debug": rule_watch_debug,
                "timed_out": db_rules_timed_out,
            }
            if db_rules_timed_out:
                _append_timeout_event(
                    timeout_events,
                    stage="db_rules_execution",
                    label="DB rules execution",
                    timeout_seconds=DB_RULE_TIMEOUT_SECONDS,
                    fallback="issues_skipped",
                )

        except Exception as db_rule_err:
            logger.warning("DB rule execution failed (continuing with other validators): %s", str(db_rule_err))
            db_rules_debug = {
                "enabled": False,
                "error": str(db_rule_err),
            }

        # =================================================================
        # OPUS VETO — final review of AI + deterministic findings.
        # Design-intended third stage: deterministic engine (RulHub or
        # local) raises findings, AI supplement adds per-LC-clause
        # findings, Opus veto confirms/drops/modifies as the examiner
        # of record.
        #
        # First-pass pre-partition: findings with concrete two-sided
        # value mismatches (e.g. invoice.currency_code=USD vs
        # lc.currency_code=EUR) are deterministic facts — no judgment
        # needed. Auto-confirm those and skip the LLM for them.
        # Everything else (missing-field claims, one-sided assertions,
        # cross-doc semantic comparisons) goes to Opus.
        # =================================================================
        def _has_concrete_value_mismatch(f: Dict[str, Any]) -> bool:
            if not isinstance(f, dict):
                return False
            exp = str(f.get("expected") or "").strip()
            found = str(f.get("found") or f.get("actual") or "").strip()
            # Require the ``<path> = <value>`` shape that
            # _normalize_rulhub_finding emits when both sides have
            # concrete values. Bare paths without "=" are missing-field
            # findings and need the examiner's judgment.
            if "=" not in exp or "=" not in found:
                return False
            exp_val = exp.split("=", 1)[1].strip()
            found_val = found.split("=", 1)[1].strip()
            if not exp_val or not found_val:
                return False
            return exp_val.lower() != found_val.lower()

        def _coerce_finding_to_dict(f: Any) -> Optional[Dict[str, Any]]:
            """AI findings are AIValidationIssue dataclasses; deterministic
            findings are plain dicts. Normalise to dict so the veto (and
            our partitioner) can inspect either shape."""
            if isinstance(f, dict):
                return f
            if hasattr(f, "to_dict") and callable(f.to_dict):
                try:
                    d = f.to_dict()
                    if isinstance(d, dict):
                        return d
                except Exception:
                    return None
            return None

        try:
            from app.config import settings as _veto_settings
            _veto_enabled = bool(getattr(_veto_settings, "VALIDATION_OPUS_VETO_ENABLED", False))

            _ai_dict_list: List[Dict[str, Any]] = []
            for _raw in (ai_issues or []):
                _coerced = _coerce_finding_to_dict(_raw)
                if _coerced is not None:
                    _ai_dict_list.append(_coerced)
            _det_dict_list = [i for i in (db_rule_issues or []) if isinstance(i, dict)]

            _auto_confirm = [
                f for f in (_ai_dict_list + _det_dict_list) if _has_concrete_value_mismatch(f)
            ]
            _ai_for_veto = [f for f in _ai_dict_list if not _has_concrete_value_mismatch(f)]
            _det_for_veto = [f for f in _det_dict_list if not _has_concrete_value_mismatch(f)]

            if _auto_confirm:
                logger.info(
                    "Veto pre-pass: auto-confirmed %d findings with concrete value mismatch",
                    len(_auto_confirm),
                )

            if _veto_enabled and (_ai_for_veto or _det_for_veto):
                from app.services.validation.tiered_validation import _run_opus_veto_pass
                import asyncio as _asyncio
                _veto_timeout = float(getattr(_veto_settings, "VALIDATION_VETO_TIMEOUT_SECONDS", 90))
                # Tag each entry with its origin layer so we can split the
                # flat return list back into ai/det buckets. _run_opus_veto_pass
                # returns ``[*ai_survivors, *det_survivors]`` concatenated.
                for _f in _ai_for_veto:
                    _f["_origin_layer"] = "ai"
                for _f in _det_for_veto:
                    _f["_origin_layer"] = "deterministic"
                try:
                    vetted_findings = await _asyncio.wait_for(
                        _run_opus_veto_pass(
                            document_data=db_rule_payload if 'db_rule_payload' in dir() else {},
                            document_type=primary_doc_type if 'primary_doc_type' in dir() else "letter_of_credit",
                            ai_findings=_ai_for_veto,
                            deterministic_findings=_det_for_veto,
                        ),
                        timeout=_veto_timeout,
                    )
                    # Post-veto: suppress any "document missing" anomalies Opus
                    # fabricates when the doc is actually present. The pre-veto
                    # filter at line ~1280 only covers ai_issues; anomaly_findings
                    # injected inside _run_opus_veto_pass bypass it.
                    vetted_findings = _filter_ai_false_positive_missing_docs(
                        vetted_findings, documents_for_ai, extracted_context,
                    )
                    # Split survivors back into ai / det via the origin tag.
                    ai_survivors = [
                        f for f in vetted_findings
                        if isinstance(f, dict) and f.get("_origin_layer") == "ai"
                    ]
                    det_survivors = [
                        f for f in vetted_findings
                        if isinstance(f, dict) and f.get("_origin_layer") != "ai"
                    ]
                    # ai_issues replaced with survivors (overrides the raw
                    # dataclass list at line 2326 that used to bypass veto).
                    # Auto-confirmed items are treated as det by convention.
                    ai_issues = ai_survivors
                    db_rule_issues = list(_auto_confirm) + list(det_survivors)
                    logger.info(
                        "Opus veto completed: %d ambiguous → %d survivors "
                        "(ai=%d, det=%d) + %d auto-confirmed",
                        len(_ai_for_veto) + len(_det_for_veto),
                        len(vetted_findings),
                        len(ai_survivors),
                        len(det_survivors),
                        len(_auto_confirm),
                    )
                except _asyncio.TimeoutError:
                    logger.warning("Opus veto timed out after %ss — keeping unvetted findings", _veto_timeout)
                except Exception as _veto_exc:
                    logger.warning("Opus veto failed — keeping unvetted findings: %s", _veto_exc)
            elif _veto_enabled:
                # Veto enabled but nothing ambiguous to review.
                ai_issues = []
                db_rule_issues = list(_auto_confirm)
                if _auto_confirm:
                    logger.info(
                        "Opus veto skipped: %d auto-confirmed, 0 ambiguous",
                        len(_auto_confirm),
                    )
        except Exception:
            pass  # Veto is advisory — never block the pipeline

        # ---------------------------------------------------------------
        # Legacy v2 CrossDocValidator — gated OFF by default (C1 of the
        # consolidation plan). This engine runs its OWN insurance / port /
        # amount / goods checks in parallel with doc_matcher's
        # match_clauses_to_documents + check_cross_document_consistency,
        # and raises findings with its OWN titles and shapes. That was the
        # root cause of the IDEAL SAMPLE's "Insurance Coverage Below LC
        # Requirement" finding firing even when 46A/47A never asked for
        # insurance: CrossDocValidator doesn't consult the LC clause graph,
        # it just runs Art 28(f)(ii) whenever an insurance doc is present.
        #
        # Enable only with VALIDATION_LEGACY_CROSSDOC_ENABLED=true to
        # run a side-by-side comparison; otherwise the spine is doc_matcher
        # (fed from the LC's own parsed 46A/47A clauses) and only that.
        # ---------------------------------------------------------------
        from app.config import settings as _spine_settings
        _legacy_crossdoc_enabled = bool(
            getattr(_spine_settings, "VALIDATION_LEGACY_CROSSDOC_ENABLED", False)
        )

        if _legacy_crossdoc_enabled:
            from app.services.validation.crossdoc_validator import CrossDocValidator
            crossdoc_validator = CrossDocValidator()
            crossdoc_lc_context = dict(lc_ctx) if isinstance(lc_ctx, dict) else {}
            metadata_dict = payload.get("metadata") or {}
            if isinstance(metadata_dict, str):
                try:
                    metadata_dict = json.loads(metadata_dict)
                except Exception:
                    metadata_dict = {}
            if isinstance(metadata_dict, dict):
                date_received = metadata_dict.get("dateReceived") or metadata_dict.get("date_received")
                if date_received and not crossdoc_lc_context.get("date_received"):
                    crossdoc_lc_context["date_received"] = date_received
                    bank_metadata = crossdoc_lc_context.get("bank_metadata")
                    if isinstance(bank_metadata, dict):
                        bank_metadata.setdefault("date_received", date_received)
                    else:
                        crossdoc_lc_context["bank_metadata"] = {"date_received": date_received}
            crossdoc_result = crossdoc_validator.validate_all(
                lc_baseline=v2_baseline,
                invoice=payload.get("invoice"),
                bill_of_lading=payload.get("bill_of_lading"),
                insurance=payload.get("insurance") or payload.get("insurance_certificate"),
                certificate_of_origin=payload.get("certificate_of_origin"),
                packing_list=payload.get("packing_list"),
                inspection_certificate=payload.get("inspection_certificate"),
                beneficiary_certificate=payload.get("beneficiary_certificate"),
                context={
                    "lc": crossdoc_lc_context,
                    "requirements_graph_v1": requirements_graph_v1 if isinstance(requirements_graph_v1, dict) else None,
                },
            )
            v2_crossdoc_issues = crossdoc_result.issues
            logger.info("Legacy CrossDocValidator found %d issues (enabled via flag)", len(v2_crossdoc_issues))
        else:
            logger.info(
                "Legacy CrossDocValidator SKIPPED (VALIDATION_LEGACY_CROSSDOC_ENABLED=false). "
                "Findings come from the doc_matcher clause spine only."
            )
            v2_crossdoc_issues = []
        checkpoint("crossdoc_validation_complete")

        # =================================================================
        # PRICE VERIFICATION (LCopilot Integration)
        # =================================================================
        try:
            from app.services.crossdoc import run_price_verification_checks

            price_verify_payload = {
                "invoice": payload.get("invoice") or {},
                "lc": payload.get("lc") or extracted_context.get("lc") or {},
                "documents": payload.get("documents") or extracted_context.get("documents") or [],
            }

            price_issues, price_checks_timed_out = await _await_with_timeout(
                "Price verification",
                run_price_verification_checks(
                    payload=price_verify_payload,
                    include_tbml_checks=True,
                ),
                PRICE_VERIFICATION_TIMEOUT_SECONDS,
                [],
            )

            price_issues = _filter_price_issues_for_documentary_context(
                v2_crossdoc_issues,
                price_issues,
            )

            if price_issues:
                logger.info("Price verification found %d issues", len(price_issues))
                v2_crossdoc_issues.extend(price_issues)
            if price_checks_timed_out:
                logger.warning("Price verification timed out and was skipped for this run")
                _append_timeout_event(
                    timeout_events,
                    stage="price_verification",
                    label="Price verification",
                    timeout_seconds=PRICE_VERIFICATION_TIMEOUT_SECONDS,
                    fallback="price_checks_skipped",
                )
        except Exception as e:
            logger.warning(f"Price verification skipped: {e}")

        # Convert AI issues to same format as crossdoc issues
        for ai_issue in ai_issues:
            v2_crossdoc_issues.append(ai_issue)

        # =================================================================
        # HYBRID VALIDATION ENHANCEMENTS
        # =================================================================

        # 1. Bank Profile Detection
        bank_profile = None
        try:
            bank_profile = detect_bank_from_lc({
                "issuing_bank": lc_context.get("issuing_bank") or mt700.get("issuing_bank") or "",
                "advising_bank": lc_context.get("advising_bank") or mt700.get("advising_bank") or "",
                "raw_text": lc_raw_text,
            })
            logger.info(f"Bank profile detected: {bank_profile.bank_code} ({bank_profile.strictness.value})")
        except Exception as e:
            logger.warning(f"Bank profile detection failed: {e}")
            bank_profile = get_bank_profile()  # Default profile

        # 2. Enhanced Requirement Parsing (v2 with caching)
        requirement_graph = None
        try:
            requirement_graph = parse_lc_requirements_sync_v2(lc_raw_text)
            if requirement_graph:
                logger.info(
                    f"RequirementGraph: {len(requirement_graph.required_documents)} docs, "
                    f"{len(requirement_graph.tolerances)} tolerances, "
                    f"{len(requirement_graph.contradictions)} contradictions"
                )
                # Store tolerances in metadata for downstream use
                ai_metadata["tolerances"] = {
                    k: v.to_dict() if hasattr(v, 'to_dict') else {
                        "field": v.field,
                        "tolerance_percent": v.tolerance_percent,
                        "source": v.source.value,
                    }
                    for k, v in requirement_graph.tolerances.items()
                }
                ai_metadata["contradictions"] = [
                    {"clause_1": c.clause_1, "clause_2": c.clause_2, "resolution": c.resolution}
                    for c in requirement_graph.contradictions
                ]
        except Exception as e:
            logger.warning(f"RequirementGraph parsing failed: {e}")

        # 3. Calculate overall extraction confidence
        extraction_confidence_summary = None
        try:
            extraction_confidence_summary = calculate_overall_extraction_confidence(extracted_context)
            logger.info(
                f"Extraction confidence: avg={extraction_confidence_summary.get('average_confidence', 0):.2f}, "
                f"lowest={extraction_confidence_summary.get('lowest_confidence_document', 'N/A')}"
            )
        except Exception as e:
            logger.warning(f"Extraction confidence calculation failed: {e}")

    except _DeferredValidationFlow:
        logger.info("Validation stage execution deferred until extraction resolution is complete")
    except Exception as e:
        logger.error("V2 pipeline error: %s", e, exc_info=True)
        # Don't fall back to legacy - just log the error
        # v2_gate_result remains None, issues remain empty
    # =====================================================================

    _recover_validation_db_session(db)
    checkpoint("post_validation_db_recovery")

    # Ensure user has a company (demo user will have one)
    if not current_user.company:
        # Try to get or create company for user
        demo_company = db.query(Company).filter(Company.name == "Demo Company").first()
        if not demo_company:
            demo_company = Company(
                name="Demo Company",
                contact_email=current_user.email or "demo@trdrhub.com",
                plan=PlanType.FREE,
                status=CompanyStatus.ACTIVE,
            )
            db.add(demo_company)
            db.flush()
        current_user.company_id = demo_company.id
        db.commit()
        db.refresh(current_user)
    checkpoint("company_context_ready")

    # Skip quota checks for demo user (allows validation to work without billing)
    if current_user.email != "demo@trdrhub.com":
        entitlements = EntitlementService(db)
        try:
            entitlements.enforce_quota(current_user.company, UsageAction.VALIDATE)
        except EntitlementError as exc:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "code": "quota_exceeded",
                    "message": exc.message,
                    "quota": exc.result.to_dict(),
                    "next_action_url": exc.next_action_url,
                },
            ) from exc
    checkpoint("quota_check_complete")

    # =====================================================================
    # V2 VALIDATION - PRIMARY PATH (Legacy disabled)
    # Note: Session was already created above, before gating check
    # =====================================================================
    request_user_type = _extract_request_user_type(payload)
    checkpoint("request_user_type_resolved")

    # Build unified issues list from v2 components
    results = []  # Legacy results - empty
    failed_results = []

    checkpoint("pre_issue_conversion")

    # =================================================================
    # BATCH LOOKUP: Collect all UCP/ISBP refs FIRST, then ONE query each
    # This replaces N individual DB queries with just 2 batch queries
    # =================================================================
    from app.services.rules_service import batch_lookup_descriptions

    all_ucp_refs = []
    all_isbp_refs = []

    # Collect refs from v2_issues
    if v2_issues:
        for issue in v2_issues:
            issue_dict = issue.to_dict() if hasattr(issue, 'to_dict') else issue
            ucp_ref = issue_dict.get("ucp_reference")
            isbp_ref = issue_dict.get("isbp_reference")
            if ucp_ref and not issue_dict.get("ucp_description"):
                all_ucp_refs.append(ucp_ref)
            if isbp_ref and not issue_dict.get("isbp_description"):
                all_isbp_refs.append(isbp_ref)

    # Collect refs from crossdoc issues
    if v2_crossdoc_issues:
        for issue in v2_crossdoc_issues:
            issue_dict = issue.to_dict() if hasattr(issue, 'to_dict') else issue
            ucp_ref = issue_dict.get("ucp_reference") or issue_dict.get("ucp_article") or ""
            isbp_ref = issue_dict.get("isbp_reference") or issue_dict.get("isbp_paragraph") or ""
            if ucp_ref and not issue_dict.get("ucp_description"):
                all_ucp_refs.append(ucp_ref)
            if isbp_ref and not issue_dict.get("isbp_description"):
                all_isbp_refs.append(isbp_ref)

    # Collect refs from DB rule issues
    if db_rule_issues:
        for issue in db_rule_issues:
            issue_dict = issue if isinstance(issue, dict) else issue.to_dict() if hasattr(issue, 'to_dict') else {}
            ucp_ref = issue_dict.get("ucp_reference") or issue_dict.get("ucp_article") or ""
            isbp_ref = issue_dict.get("isbp_reference") or issue_dict.get("isbp_paragraph") or ""
            if ucp_ref and not issue_dict.get("ucp_description"):
                all_ucp_refs.append(ucp_ref)
            if isbp_ref and not issue_dict.get("isbp_description"):
                all_isbp_refs.append(isbp_ref)

    # BATCH LOOKUP: 2 queries instead of N
    ucp_desc_cache, isbp_desc_cache = batch_lookup_descriptions(all_ucp_refs, all_isbp_refs)
    logger.info(f"Batch lookup: {len(ucp_desc_cache)} UCP refs, {len(isbp_desc_cache)} ISBP refs")

    # Helper to get description from cache
    def _get_ucp_desc(ref: str) -> Optional[str]:
        if not ref:
            return None
        # Try cache first, no fallback to individual query
        return ucp_desc_cache.get(ref) or ucp_desc_cache.get(ref.replace("Article ", "").replace("UCP600 ", ""))

    def _get_isbp_desc(ref: str) -> Optional[str]:
        if not ref:
            return None
        return isbp_desc_cache.get(ref) or isbp_desc_cache.get(ref.replace("ISBP745 ", "").replace("?", ""))

    # Convert v2 issues to legacy format for compatibility
    if v2_issues:
        for issue in v2_issues:
            issue_dict = issue.to_dict() if hasattr(issue, 'to_dict') else issue
            ucp_ref = issue_dict.get("ucp_reference")
            isbp_ref = issue_dict.get("isbp_reference")
            failed_results.append({
                "rule": issue_dict.get("rule", "V2-ISSUE"),
                "title": issue_dict.get("title", "Validation Issue"),
                "passed": False,
                "severity": issue_dict.get("severity", "major"),
                "message": issue_dict.get("message", ""),
                "expected": issue_dict.get("expected", ""),
                "found": issue_dict.get("found", issue_dict.get("actual", "")),
                "suggested_fix": issue_dict.get("suggested_fix", issue_dict.get("suggestion", "")),
                "documents": issue_dict.get("documents", []),
                "ucp_reference": ucp_ref,
                "isbp_reference": isbp_ref,
                "ucp_description": issue_dict.get("ucp_description") or _get_ucp_desc(ucp_ref),
                "isbp_description": issue_dict.get("isbp_description") or _get_isbp_desc(isbp_ref),
                "display_card": True,
                "ruleset_domain": "icc.lcopilot.extraction",
            })

    # Add cross-doc issues (including AI validator issues)
    if v2_crossdoc_issues:
        for issue in v2_crossdoc_issues:
            issue_dict = issue.to_dict() if hasattr(issue, 'to_dict') else issue

            # Handle both CrossDocIssue and AIValidationIssue formats
            # CrossDocIssue uses: "rule", "ucp_article", "actual"
            # AIValidationIssue uses: "rule", "ucp_reference", "actual"
            ucp_ref = issue_dict.get("ucp_reference") or issue_dict.get("ucp_article") or ""
            isbp_ref = issue_dict.get("isbp_reference") or issue_dict.get("isbp_paragraph") or ""
            failed_results.append({
                "rule": issue_dict.get("rule") or issue_dict.get("rule_id") or "CROSSDOC-ISSUE",
                "title": issue_dict.get("title", "Cross-Document Issue"),
                "passed": False,
                "severity": issue_dict.get("severity", "major"),
                "message": issue_dict.get("message", ""),
                "expected": issue_dict.get("expected", ""),
                "found": issue_dict.get("actual") or issue_dict.get("found") or "",
                "suggested_fix": issue_dict.get("suggestion") or issue_dict.get("suggested_fix") or "",
                "documents": issue_dict.get("documents") or issue_dict.get("document_names") or [issue_dict.get("source_doc", ""), issue_dict.get("target_doc", "")],
                "ucp_reference": ucp_ref,
                "isbp_reference": isbp_ref,
                "ucp_description": issue_dict.get("ucp_description") or _get_ucp_desc(ucp_ref),
                "isbp_description": issue_dict.get("isbp_description") or _get_isbp_desc(isbp_ref),
                "display_card": True,
                "ruleset_domain": issue_dict.get("ruleset_domain") or "icc.lcopilot.crossdoc",
                "auto_generated": issue_dict.get("auto_generated", False),
                "source_doc": issue_dict.get("source_doc"),
                "target_doc": issue_dict.get("target_doc"),
                "source_field": issue_dict.get("source_field"),
                "target_field": issue_dict.get("target_field"),
                "requirement_source": issue_dict.get("requirement_source"),
                "requirement_kind": issue_dict.get("requirement_kind"),
                "requirement_text": issue_dict.get("requirement_text"),
                "overlap_keys": _extract_issue_overlap_keys(issue_dict),
            })

    # Add DB rule issues (2500+ rules from database)
    if db_rule_issues:
        for issue in db_rule_issues:
            issue_dict = issue if isinstance(issue, dict) else issue.to_dict() if hasattr(issue, 'to_dict') else {}
            ucp_ref = issue_dict.get("ucp_reference") or issue_dict.get("ucp_article") or ""
            isbp_ref = issue_dict.get("isbp_reference") or issue_dict.get("isbp_paragraph") or ""
            failed_results.append({
                "rule": issue_dict.get("rule") or issue_dict.get("rule_id") or "DB-RULE",
                "title": issue_dict.get("title", "Validation Rule"),
                "passed": False,
                "severity": issue_dict.get("severity", "major"),
                "message": issue_dict.get("message", ""),
                "expected": issue_dict.get("expected", ""),
                "found": issue_dict.get("actual") or issue_dict.get("found") or "",
                "suggested_fix": issue_dict.get("suggestion") or issue_dict.get("suggested_fix") or "",
                "documents": issue_dict.get("documents") or [],
                "ucp_reference": ucp_ref,
                "isbp_reference": isbp_ref,
                "ucp_description": issue_dict.get("ucp_description") or _get_ucp_desc(ucp_ref),
                "isbp_description": issue_dict.get("isbp_description") or _get_isbp_desc(isbp_ref),
                "display_card": True,
                "ruleset_domain": issue_dict.get("ruleset_domain") or "icc.ucp600",
                "rule_type": issue_dict.get("rule_type"),
                "consequence_class": issue_dict.get("consequence_class"),
                "execution_priority": issue_dict.get("execution_priority"),
                "parent_rule": issue_dict.get("parent_rule"),
                "has_specific_family_rules": issue_dict.get("has_specific_family_rules"),
                "overlap_keys": issue_dict.get("overlap_keys") or [],
            })
        logger.info("Added %d DB rule issues to failed_results", len(db_rule_issues))

    # Add LC type unknown warning if applicable
    if lc_type_is_unknown:
        failed_results.append(
            {
                "rule": "LC-TYPE-UNKNOWN",
                "title": "LC Type Not Determined",
                "passed": False,
                "severity": "warning",
                "message": (
                    "We could not determine whether this LC is an import or export workflow. "
                    "Advanced trade-specific checks were disabled for safety."
                ),
                "documents": ["Letter of Credit"],
                "document_names": ["Letter of Credit"],
                "display_card": True,
                "ruleset_domain": "system.lc_type",
                "not_applicable": False,
            }
        )

    # =====================================================================
    # DEDUPLICATION - Remove duplicate issues across layers
    # =====================================================================
    failed_results = _suppress_broad_icc_umbrella_rules(failed_results)
    failed_results = _suppress_legacy_issue_noise(failed_results)

    # Pass 1: exact dedup (same rule + title + expected + found)
    seen_rules = set()
    deduplicated_results = []
    for issue in failed_results:
        dedup_key = _build_issue_dedup_key(issue)
        if dedup_key not in seen_rules:
            seen_rules.add(dedup_key)
            deduplicated_results.append(issue)
        else:
            logger.debug(
                "Removed exact-duplicate issue: %s",
                issue.get("rule") or issue.get("title") or dedup_key,
            )

    # Pass 2: cross-layer dedup — same (document, field) from different
    # source layers (clause_matcher, crossdoc_matcher, AI, DB rules).
    # Keep the highest-priority source; drop duplicates from weaker layers.
    _LAYER_PRIORITY = {
        "crossdoc_matcher": 1,
        "clause_matcher": 2,
        "icc.lcopilot.crossdoc": 3,
        "icc.ucp600": 4,
        "rulhub_deterministic": 5,
        "icc.lcopilot.ai_validation": 6,
        "icc.lcopilot.extraction": 7,
    }

    seen_doc_field: dict[str, int] = {}
    cross_deduped: list[dict[str, Any]] = []
    cross_dedup_count = 0
    for issue in deduplicated_results:
        # Extract document and field for this finding
        docs = issue.get("documents") or issue.get("document_names") or []
        doc_token = str(docs[0]).strip().lower().replace(" ", "_") if docs else ""
        field_token = str(
            issue.get("field_name") or issue.get("field") or ""
        ).strip().lower()

        # Only cross-dedup if we have both doc and field
        if doc_token and field_token:
            composite_key = f"{doc_token}|{field_token}"
            source = str(
                issue.get("source_layer") or issue.get("ruleset_domain") or ""
            ).strip().lower()
            priority = _LAYER_PRIORITY.get(source, 10)

            if composite_key in seen_doc_field:
                existing_priority = seen_doc_field[composite_key]
                if priority >= existing_priority:
                    # Lower priority (higher number) — skip
                    cross_dedup_count += 1
                    logger.debug(
                        "Cross-layer dedup: dropping %s/%s from %s (already covered by higher-priority layer)",
                        doc_token, field_token, source,
                    )
                    continue
                else:
                    # Higher priority — replace the weaker finding
                    # (can't easily remove from list, so just update priority and keep both;
                    #  the weaker one was already added but this is rare enough not to matter)
                    seen_doc_field[composite_key] = priority
            else:
                seen_doc_field[composite_key] = priority

        cross_deduped.append(issue)

    deduplicated_results = cross_deduped

    total_removed = len(failed_results) - len(deduplicated_results)
    if total_removed:
        logger.warning(
            "Deduplication removed %d issues (%d cross-layer)",
            total_removed, cross_dedup_count,
        )

    if validation_session and current_user.is_bank_user() and current_user.company_id:
        try:
            policy_results, bank_policy_timed_out = await _await_with_timeout(
                "Bank policy application",
                apply_bank_policy(
                    validation_results=deduplicated_results,
                    bank_id=str(current_user.company_id),
                    document_data=payload,
                    db_session=db,
                    validation_session_id=str(validation_session.id),
                    user_id=str(current_user.id),
                ),
                BANK_POLICY_TIMEOUT_SECONDS,
                None,
            )
            if policy_results is not None:
                deduplicated_results = [
                    issue for issue in policy_results if not issue.get("passed", False)
                ]
            if bank_policy_timed_out:
                logger.warning("Bank policy application timed out; using pre-policy issue set")
                _append_timeout_event(
                    timeout_events,
                    stage="bank_policy_application",
                    label="Bank policy application",
                    timeout_seconds=BANK_POLICY_TIMEOUT_SECONDS,
                    fallback="pre_policy_issue_set",
                )
        except Exception as e:
            logger.warning("Bank policy application skipped: %s", e)

    results = list(deduplicated_results)

    logger.info(
        "V2 Validation: total_issues=%d (extraction=%d crossdoc=%d db_rules=%d) after_dedup=%d",
        len(failed_results),
        len(v2_issues) if v2_issues else 0,
        len(v2_crossdoc_issues) if v2_crossdoc_issues else 0,
        len(db_rule_issues) if db_rule_issues else 0,
        len(deduplicated_results),
    )

    issue_cards, reference_issues = build_issue_cards(deduplicated_results)
    checkpoint("issue_cards_built")

    # Record usage - link to session if created (skip for demo user)
    quota = None
    company_size, _company_size_tolerance_percent = _determine_company_size(current_user, payload)
    tolerance_percent = _resolve_invoice_amount_tolerance_percent(payload)
    payload["company_profile"] = {
        "size": company_size,
        "invoice_amount_tolerance_percent": float(tolerance_percent),
    }
    tolerance_value, amount_limit = _compute_invoice_amount_bounds(payload, tolerance_percent)
    if tolerance_value is not None:
        payload["invoice_amount_tolerance_value"] = tolerance_value
    if amount_limit is not None:
        payload["invoice_amount_limit"] = amount_limit

    if current_user.email != "demo@trdrhub.com":
        entitlements = EntitlementService(db)
        quota = entitlements.record_usage(
            current_user.company,
            UsageAction.VALIDATE,
            user_id=current_user.id,
            cost=Decimal("0.00"),
            description=f"Validation request for document type {doc_type}",
            session_id=validation_session.id if validation_session else None,
        )

    document_details_for_summaries = (
        payload.get("documents")
        or (setup_state.get("extracted_context") or {}).get("documents")
    )
    # Also ensure files_list is populated from setup_state if empty
    if not files_list and document_details_for_summaries:
        files_list = document_details_for_summaries
    logger.info(
        "Building document summaries: files_list=%d details=%d issues=%d",
        len(files_list) if files_list else 0,
        len(document_details_for_summaries) if document_details_for_summaries else 0,
        len(deduplicated_results) if deduplicated_results else 0,
    )
    # FIX: Use deduplicated_results (actual issues) instead of empty results list
    # This ensures document issue counts are correctly linked to each document
    document_summaries = _build_document_summaries(
        files_list,
        deduplicated_results,  # Was 'results' which was always empty!
        document_details_for_summaries,
    )
    if document_summaries:
        doc_status_counts: Dict[str, int] = {}
        for summary in document_summaries:
            doc_status_val = summary.get("status") or "unknown"
            doc_status_counts[doc_status_val] = doc_status_counts.get(doc_status_val, 0) + 1
        logger.info(
            "Document summaries built: total=%d status_breakdown=%s",
            len(document_summaries),
            doc_status_counts,
        )
    else:
        logger.warning(
            "Document summaries are empty: no documents captured for job %s", job_id
        )

    checkpoint("document_summaries_built")

    processing_duration = time.time() - start_time
    processing_summary = _build_processing_summary(
        document_summaries,
        processing_duration,
        len(deduplicated_results),
    )

    return {
        "validation_session": validation_session,
        "job_id": job_id,
        "extracted_context": extracted_context,
        "lc_context": lc_context,
        "lc_type": lc_type,
        "lc_type_is_unknown": lc_type_is_unknown,
        "v2_gate_result": v2_gate_result,
        "v2_baseline": v2_baseline,
        "v2_issues": v2_issues,
        "v2_crossdoc_issues": v2_crossdoc_issues,
        "db_rule_issues": db_rule_issues if 'db_rule_issues' in locals() else [],
        "db_rules_debug": db_rules_debug if 'db_rules_debug' in locals() else {"enabled": False, "status": "not_started"},
        "bank_profile": bank_profile if 'bank_profile' in locals() else None,
        "requirement_graph": requirement_graph if 'requirement_graph' in locals() else None,
        "extraction_confidence_summary": extraction_confidence_summary if 'extraction_confidence_summary' in locals() else None,
        "ai_validation_summary": ai_validation_summary,
        "timeout_events": timeout_events,
        "validation_deferred": defer_final_validation,
        "workflow_stage_hint": workflow_stage_hint,
        "request_user_type": request_user_type,
        "results": results,
        "failed_results": failed_results,
        "deduplicated_results": deduplicated_results,
        "issue_cards": issue_cards,
        "reference_issues": reference_issues,
        "document_summaries": document_summaries,
        "processing_duration": processing_duration,
        "processing_summary": processing_summary,
    }


__all__ = ["bind_shared", "execute_validation_pipeline"]
