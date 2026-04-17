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
        # Reads the LC clauses and checks each document's fields.
        # This is the deterministic core of Part 2 validation.
        # =================================================================
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

            # Convert findings to issue dicts compatible with the existing pipeline
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
                "Clause matcher: %d clause findings + %d crossdoc findings added to v2_issues",
                len(clause_findings), len(crossdoc_findings),
            )
        except Exception:
            logger.exception("Clause-based document matching failed — continuing without")

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

            # Primary jurisdiction (prefer exporter's country)
            primary_jurisdiction = "global"
            if origin_country:
                primary_jurisdiction = origin_country
            elif seller_country:
                primary_jurisdiction = seller_country
            elif detected_jurisdictions:
                primary_jurisdiction = list(detected_jurisdictions)[0]

            logger.info(
                "Dynamic jurisdiction detection: primary=%s, all=%s, supplements=%s",
                primary_jurisdiction, list(detected_jurisdictions), supplement_domains
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
                    import json as _json

                    # Serialize db_rule_payload to plain JSON-safe types.
                    # v2_baseline fields are FieldResult objects that aren't
                    # JSON serializable — extract .value from them.
                    def _jsonable_value(v):
                        if v is None:
                            return None
                        if hasattr(v, 'value'):
                            return v.value
                        if hasattr(v, 'model_dump'):
                            return v.model_dump()
                        return v

                    _rulhub_payload = dict(db_rule_payload)
                    for _k in ('lc_number', 'amount', 'currency', 'expiry_date'):
                        if _k in _rulhub_payload:
                            _rulhub_payload[_k] = _jsonable_value(_rulhub_payload[_k])

                    _rulhub = RulHubRulesAdapter()
                    _rulhub_result = await _rulhub.evaluate_rules(
                        rules=[],
                        input_context={
                            "document_type": primary_doc_type,
                            "jurisdiction": primary_jurisdiction,
                            "rules": "ucp600",
                            "fields": _rulhub_payload,
                        },
                    )
                    db_rule_issues = _rulhub_result.get("outcomes", [])
                    logger.info("RulHub API returned %d findings", len(db_rule_issues))
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
        # OPUS VETO — final review of AI + deterministic findings
        # Runs regardless of whether RulHub or DB rules produced the
        # deterministic findings. Can confirm/drop/modify/add findings.
        # =================================================================
        try:
            from app.config import settings as _veto_settings
            _veto_enabled = bool(getattr(_veto_settings, "VALIDATION_OPUS_VETO_ENABLED", False))
            if _veto_enabled and (ai_issues or db_rule_issues):
                from app.services.validation.tiered_validation import _run_opus_veto_pass
                import asyncio as _asyncio
                _veto_timeout = float(getattr(_veto_settings, "VALIDATION_VETO_TIMEOUT_SECONDS", 90))
                try:
                    vetted_findings = await _asyncio.wait_for(
                        _run_opus_veto_pass(
                            document_data=db_rule_payload if 'db_rule_payload' in dir() else {},
                            document_type=primary_doc_type if 'primary_doc_type' in dir() else "letter_of_credit",
                            ai_findings=[i for i in (ai_issues or []) if isinstance(i, dict)],
                            deterministic_findings=[i for i in (db_rule_issues or []) if isinstance(i, dict)],
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
                    # Replace db_rule_issues with vetted findings (Opus has final say)
                    db_rule_issues = vetted_findings
                    logger.info("Opus veto completed: %d findings after review", len(vetted_findings))
                except _asyncio.TimeoutError:
                    logger.warning("Opus veto timed out after %ss — keeping unvetted findings", _veto_timeout)
                except Exception as _veto_exc:
                    logger.warning("Opus veto failed — keeping unvetted findings: %s", _veto_exc)
        except Exception:
            pass  # Veto is advisory — never block the pipeline

        # Run v2 CrossDocValidator
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
        logger.info("V2 CrossDocValidator found %d issues", len(v2_crossdoc_issues))
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
