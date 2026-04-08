"""Validation contract and submission-eligibility helpers."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from .issues_pipeline import _build_document_field_hint_index, _build_unresolved_critical_context


logger = logging.getLogger(__name__)


def _build_issue_lane_summary(issues: Optional[List[Dict[str, Any]]]) -> Dict[str, Dict[str, Any]]:
    severity_rank = {
        "critical": 4,
        "error": 4,
        "high": 4,
        "major": 3,
        "warning": 2,
        "warn": 2,
        "medium": 2,
        "minor": 1,
        "low": 1,
        "info": 0,
    }
    rank_to_severity = {
        4: "critical",
        3: "major",
        2: "warning",
        1: "minor",
        0: "info",
    }
    advisory_tokens = ("price-verify", "sanctions", "tbml", "shell")
    documentary_tokens = ("crossdoc", "docset", "ucp600", "isbp", "lc-missing")
    lanes: Dict[str, Dict[str, Any]] = {
        "documentary": {
            "count": 0,
            "blocking_count": 0,
            "rule_ids": [],
            "titles": [],
            "highest_severity": None,
        },
        "advisory": {
            "count": 0,
            "blocking_count": 0,
            "rule_ids": [],
            "titles": [],
            "highest_severity": None,
        },
    }

    def _coerce_issue_text(issue: Dict[str, Any], *keys: str) -> str:
        for key in keys:
            value = issue.get(key)
            text = str(value or "").strip()
            if text:
                return text
        return ""

    def _issue_lane(issue: Dict[str, Any]) -> str:
        requirement_source = _coerce_issue_text(issue, "requirement_source").lower()
        if requirement_source == "requirements_graph_v1":
            return "documentary"

        rule_id = _coerce_issue_text(issue, "rule", "rule_id").lower()
        ruleset_domain = _coerce_issue_text(issue, "ruleset_domain").lower()
        combined = f"{rule_id} {ruleset_domain}"
        if any(token in combined for token in advisory_tokens):
            return "advisory"
        if any(token in combined for token in documentary_tokens):
            return "documentary"
        return "documentary"

    for issue in issues or []:
        if not isinstance(issue, dict):
            continue
        lane_name = _issue_lane(issue)
        lane = lanes[lane_name]
        severity = _coerce_issue_text(issue, "severity", "level").lower() or "major"
        rank = severity_rank.get(severity, 2)
        rule_id = _coerce_issue_text(issue, "rule", "rule_id")
        title = _coerce_issue_text(issue, "title", "message")

        lane["count"] += 1
        if lane_name == "documentary" and rank >= severity_rank["critical"]:
            lane["blocking_count"] += 1
        if rule_id and rule_id not in lane["rule_ids"]:
            lane["rule_ids"].append(rule_id)
        if title and title not in lane["titles"]:
            lane["titles"].append(title)

        current_rank = severity_rank.get(str(lane.get("highest_severity") or "").lower(), -1)
        if rank > current_rank:
            lane["highest_severity"] = rank_to_severity.get(rank, severity)

    return lanes

def _classify_reason_semantics(
    submission_eligibility: Optional[Dict[str, Any]],
    bank_verdict: Optional[Dict[str, Any]] = None,
) -> Dict[str, List[str]]:
    submission_eligibility = submission_eligibility or {}
    bank_verdict = bank_verdict or {}
    reason_codes = [str(x).strip().lower() for x in (submission_eligibility.get("missing_reason_codes") or []) if str(x).strip()]
    submission_reasons = [str(x).strip().lower() for x in (submission_eligibility.get("reasons") or []) if str(x).strip()]
    bank_reasons = [str(x).strip().lower() for x in (bank_verdict.get("reasons") or []) if str(x).strip()]
    unresolved = submission_eligibility.get("unresolved_critical_fields") or []

    extraction_failures: List[str] = []
    missing_fields: List[str] = []
    parse_failures: List[str] = []
    rule_decision_basis: List[str] = []
    requirement_findings: List[str] = []

    for item in unresolved:
        if isinstance(item, dict):
            field_name = str(item.get("field") or "").strip()
            reason_code = str(item.get("reason_code") or "").strip().lower()
            status = str(item.get("status") or "").strip().lower()
            if field_name:
                missing_fields.append(field_name)
            if "parse_failed" in reason_code or status == "rejected":
                parse_failures.append(field_name or reason_code)
            if any(token in reason_code for token in ["ocr_", "field_not_found", "format_invalid", "fallback_text_recovered"]):
                extraction_failures.append(reason_code)
        else:
            field_name = str(item).strip()
            if field_name:
                missing_fields.append(field_name)

    for code in reason_codes:
        if any(token in code for token in ["ocr_", "field_not_found", "format_invalid", "fallback_text_recovered"]):
            extraction_failures.append(code)

    for reason in submission_reasons + bank_reasons:
        if reason == "bank_verdict_reject":
            rule_decision_basis.append("bank_submission_verdict")
        elif reason == "bank_verdict_caution":
            rule_decision_basis.append("rules_review_signal")
        elif reason == "lc_required_statement_missing" or reason.startswith("requirements_"):
            requirement_findings.append(reason)
        elif "sanction" in reason:
            rule_decision_basis.append("sanctions")
        elif "tbml" in reason:
            rule_decision_basis.append("tbml")
        elif "shell" in reason:
            rule_decision_basis.append("shell_risk")

    return {
        "extraction_failures": sorted(set(x for x in extraction_failures if x)),
        "missing_fields": sorted(set(x for x in missing_fields if x)),
        "parse_failures": sorted(set(x for x in parse_failures if x)),
        "rule_decision_basis": sorted(set(x for x in rule_decision_basis if x)),
        "requirement_findings": sorted(set(x for x in requirement_findings if x)),
    }

def _extract_requirement_readiness_items(issues: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()

    def _first_document_name(issue: Dict[str, Any]) -> Optional[str]:
        candidates = (
            issue.get("affected_document_names")
            or issue.get("document_names")
            or issue.get("documents")
            or issue.get("document_name")
            or issue.get("document_type")
        )
        if isinstance(candidates, str):
            candidate = candidates.strip()
            if candidate and candidate.lower() != "letter of credit":
                return candidate
            return None
        if isinstance(candidates, list):
            for value in candidates:
                candidate = str(value or "").strip()
                if candidate and candidate.lower() != "letter of credit":
                    return candidate
        return None

    for issue in issues or []:
        if not isinstance(issue, dict):
            continue
        requirement_source = str(issue.get("requirement_source") or "").strip().lower()
        requirement_kind = str(issue.get("requirement_kind") or "").strip().lower()
        if requirement_source != "requirements_graph_v1" or not requirement_kind:
            continue

        normalized_kind = requirement_kind.replace("-", "_").replace(" ", "_")
        reason_code = (
            "lc_required_statement_missing"
            if normalized_kind == "document_exact_wording"
            else f"requirements_{normalized_kind}"
        )
        document_name = _first_document_name(issue) or ""
        requirement_text = str(issue.get("requirement_text") or "").strip()
        title = str(issue.get("title") or issue.get("message") or "LC requirement review needed").strip()
        key = (reason_code, document_name, requirement_text, title)
        if key in seen:
            continue
        seen.add(key)
        items.append(
            {
                "reason_code": reason_code,
                "requirement_source": "requirements_graph_v1",
                "requirement_kind": requirement_kind,
                "severity": str(issue.get("severity") or issue.get("level") or "major").strip().lower() or "major",
                "title": title,
                "document_name": document_name or None,
                "requirement_text": requirement_text or None,
                "action": issue.get("suggestion") or issue.get("suggested_fix") or issue.get("message"),
            }
        )
    return items[:10]

def _extract_rule_evidence_items(issues: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for issue in issues or []:
        if not isinstance(issue, dict):
            continue
        rule_id = (
            issue.get("rule_id")
            or issue.get("rule")
            or issue.get("ruleId")
            or issue.get("source_rule_id")
            or issue.get("sourceRuleId")
        )
        severity = issue.get("severity") or issue.get("level")
        expected_outcome = issue.get("expected_outcome") or issue.get("expectedOutcome")
        conditions = issue.get("conditions") or issue.get("trigger_conditions") or issue.get("triggerConditions")
        code = issue.get("code") or issue.get("reason_code") or issue.get("reasonCode")
        if not any([rule_id, severity, expected_outcome, conditions, code]):
            continue
        items.append({
            "rule_id": rule_id,
            "severity": severity,
            "expected_outcome": expected_outcome,
            "conditions": conditions,
            "reason_code": code,
        })
    return items[:10]

def _classify_rules_signal_classes(
    bank_verdict: Optional[Dict[str, Any]],
    gate_result: Optional[Dict[str, Any]],
    submission_eligibility: Optional[Dict[str, Any]],
) -> Tuple[List[str], List[str]]:
    bank_verdict = bank_verdict or {}
    gate_result = gate_result or {}
    submission_eligibility = submission_eligibility or {}

    veto_classes: List[str] = []
    trigger_classes: List[str] = []
    signal_texts: List[str] = []

    signal_texts.extend(str(x) for x in (submission_eligibility.get("reasons") or []) if x)
    signal_texts.extend(str(x) for x in (submission_eligibility.get("missing_reason_codes") or []) if x)
    signal_texts.extend(str(x) for x in (bank_verdict.get("reasons") or []) if x)
    signal_texts.extend(str(x) for x in (bank_verdict.get("risk_flags") or []) if x)
    signal_texts.extend(str(x) for x in (gate_result.get("missing_reason_codes") or []) if x)

    normalized = " | ".join(signal_texts).lower()

    if any(token in normalized for token in ["sanction", "watchlist", "ofac", "sdn"]):
        trigger_classes.append("sanctions")
    if any(token in normalized for token in ["tbml", "trade_based_money_laundering", "overinvoic", "underinvoic", "routing_anomal", "quantity_value_mismatch"]):
        trigger_classes.append("tbml")
    if any(token in normalized for token in ["shell_risk", "shell-risk", "ownership_opacity", "weak_business_footprint", "high_risk_counterparty"]):
        trigger_classes.append("shell_risk")

    missing_critical = [
        str(field).strip()
        for field in ((gate_result or {}).get("missing_critical") or [])
        if str(field).strip()
    ]
    if missing_critical:
        veto_classes.append("missing_critical_controls")

    rules_raw = str(bank_verdict.get("verdict") or "").strip().upper()
    if rules_raw == "CAUTION":
        trigger_classes.append("rules_review_signal")

    return sorted(set(veto_classes)), sorted(set(trigger_classes))

def _build_validation_contract(
    ai_validation: Optional[Dict[str, Any]],
    bank_verdict: Optional[Dict[str, Any]],
    gate_result: Optional[Dict[str, Any]],
    submission_eligibility: Optional[Dict[str, Any]],
    issues: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Build side-by-side AI/rules/final validation verdict contract."""
    ai_validation = ai_validation or {}
    bank_verdict = bank_verdict or {}
    gate_result = gate_result or {}
    submission_eligibility = submission_eligibility or {}

    ai_critical = int(ai_validation.get("critical_issues", 0) or 0)
    ai_major = int(ai_validation.get("major_issues", 0) or 0)
    ai_minor = int(ai_validation.get("minor_issues", 0) or 0)
    ai_layers = ai_validation.get("layers") if isinstance(ai_validation.get("layers"), dict) else {}
    ai_execution_position = str(ai_validation.get("execution_position") or "").strip() or None
    ai_layer_contract_version = str(ai_validation.get("layer_contract_version") or "").strip() or None
    ai_layer_verdicts = {
        layer_name: str(layer.get("verdict") or "").strip().lower()
        for layer_name, layer in ai_layers.items()
        if isinstance(layer, dict)
    }
    executed_ai_layer_verdicts = [
        verdict
        for layer_name, verdict in ai_layer_verdicts.items()
        if verdict in {"pass", "warn", "reject"}
        and isinstance(ai_layers.get(layer_name), dict)
        and bool(ai_layers.get(layer_name, {}).get("executed"))
    ]

    if "reject" in executed_ai_layer_verdicts:
        ai_verdict = "reject"
    elif "warn" in executed_ai_layer_verdicts:
        ai_verdict = "warn"
    elif executed_ai_layer_verdicts:
        ai_verdict = "pass"
    elif ai_critical > 0:
        ai_verdict = "reject"
    elif ai_major > 0:
        ai_verdict = "warn"
    else:
        ai_verdict = "pass"
    ai_source_verdict = ai_verdict

    rules_raw = str(bank_verdict.get("verdict") or "").strip().upper()
    rules_map = {
        "REJECT": "reject",
        "HOLD": "reject",
        "CAUTION": "review",
        "SUBMIT": "pass",
    }
    ruleset_verdict = rules_map.get(rules_raw, "review" if gate_result.get("missing_critical") else "pass")

    missing_critical = [
        str(field).strip()
        for field in ((gate_result or {}).get("missing_critical") or [])
        if str(field).strip()
    ]
    issue_lanes = _build_issue_lane_summary(issues)
    documentary_lane = dict(issue_lanes.get("documentary") or {})
    advisory_lane = dict(issue_lanes.get("advisory") or {})
    documentary_issue_count = int(documentary_lane.get("count") or 0)
    documentary_blocking_count = int(documentary_lane.get("blocking_count") or 0)
    advisory_issue_count = int(advisory_lane.get("count") or 0)
    requirement_readiness_items = _extract_requirement_readiness_items(issues)
    requirement_reason_codes = sorted(
        {
            str(item.get("reason_code") or "").strip()
            for item in requirement_readiness_items
            if str(item.get("reason_code") or "").strip()
        }
    )
    if requirement_reason_codes and not submission_eligibility.get("can_submit", True):
        submission_reasons_existing = [
            str(item).strip() for item in (submission_eligibility.get("reasons") or []) if str(item).strip()
        ]
        submission_reasons_seen = {item.lower() for item in submission_reasons_existing}
        for reason_code in requirement_reason_codes:
            if reason_code.lower() not in submission_reasons_seen:
                submission_reasons_existing.append(reason_code)
                submission_reasons_seen.add(reason_code.lower())
        submission_eligibility["reasons"] = submission_reasons_existing
    rules_veto_classes, rules_trigger_classes = _classify_rules_signal_classes(
        bank_verdict,
        gate_result,
        submission_eligibility,
    )
    reason_semantics = _classify_reason_semantics(submission_eligibility, bank_verdict)
    rule_evidence_items = _extract_rule_evidence_items(issues)
    documentary_decision_clear = (
        not missing_critical
        and documentary_issue_count == 0
        and not requirement_readiness_items
        and documentary_blocking_count == 0
    )
    advisory_classes = {
        trigger
        for trigger in rules_trigger_classes
        if trigger in {"sanctions", "tbml", "shell_risk"}
    }
    advisory_review_needed = bool(advisory_issue_count or advisory_classes)
    documentary_review_needed = bool(
        documentary_issue_count
        or documentary_blocking_count
        or missing_critical
        or requirement_readiness_items
    )
    advisory_only_submission_gate_override = (
        documentary_decision_clear
        and advisory_review_needed
        and bool(submission_eligibility)
        and not submission_eligibility.get("can_submit", True)
    )
    if documentary_decision_clear and advisory_review_needed:
        ai_verdict = "pass"
    advisory_only_rules_override = (
        documentary_decision_clear
        and advisory_review_needed
        and rules_raw in {"REJECT", "HOLD", "CAUTION"}
    )
    if advisory_only_rules_override:
        ruleset_verdict = "pass"
    elif ruleset_verdict == "pass":
        if documentary_blocking_count > 0:
            ruleset_verdict = "reject"
        elif documentary_review_needed:
            ruleset_verdict = "review"
    primary_decision_lane = (
        "documentary"
        if documentary_review_needed
        else "advisory"
        if advisory_review_needed
        else "none"
    )
    domain_risk_summary = {
        "sanctions": "advisory" if "sanctions" in rules_trigger_classes else None,
        "tbml": "advisory" if "tbml" in rules_trigger_classes else None,
        "shell_risk": "advisory" if "shell_risk" in rules_trigger_classes else None,
        "missing_critical_controls": "hard_fail" if "missing_critical_controls" in rules_veto_classes else None,
    }

    disagreement_flag = ai_verdict != ruleset_verdict
    final_verdict = ruleset_verdict
    override_reason = None
    arbitration_mode = "aligned"

    if ai_verdict == "pass" and ruleset_verdict == "reject":
        final_verdict = "reject"
        override_reason = "rules_veto_critical_control"
        arbitration_mode = "rules_veto"
    elif ai_verdict == "reject" and ruleset_verdict == "pass":
        final_verdict = "review"
        override_reason = "ai_reject_rules_clean_review_required"
        arbitration_mode = "disagreement_review"
    elif ai_verdict == "warn" and ruleset_verdict in {"pass", "review"}:
        final_verdict = "review"
        override_reason = "ai_warn_requires_review" if ruleset_verdict == "pass" else "combined_review_signal"
        arbitration_mode = "ai_escalation"
    elif ruleset_verdict == "review":
        final_verdict = "review"
        if ai_verdict == "pass":
            override_reason = "rules_require_review"
            arbitration_mode = "rules_review"

    if (
        submission_eligibility
        and not submission_eligibility.get("can_submit", True)
        and not advisory_only_submission_gate_override
    ):
        if final_verdict == "pass":
            final_verdict = "review"
            override_reason = override_reason or "submission_not_ready"
            arbitration_mode = "submission_gate_review"

    review_required_reason = []
    if disagreement_flag:
        review_required_reason.append("ai_rules_disagreement")
    if ruleset_verdict == "review":
        review_required_reason.append("rules_review_signal")
    if ai_verdict in {"warn", "reject"} and final_verdict == "review":
        review_required_reason.append("ai_escalation")
    if (
        submission_eligibility
        and not submission_eligibility.get("can_submit", True)
        and not advisory_only_submission_gate_override
        and final_verdict == "review"
    ):
        review_required_reason.append("submission_not_ready")

    immediate_rules_veto = bool(rules_veto_classes)
    escalation_triggers: List[str] = []
    if disagreement_flag and not immediate_rules_veto:
        escalation_triggers.append("ai_rules_disagreement")
    if ai_verdict in {"warn", "reject"} and ruleset_verdict == "pass":
        escalation_triggers.append("ai_detected_non_deterministic_risk")
    if ruleset_verdict == "review":
        escalation_triggers.append("rules_review_signal")
    escalation_triggers.extend(rules_trigger_classes)
    if (
        submission_eligibility
        and not submission_eligibility.get("can_submit", True)
        and not advisory_only_submission_gate_override
        and final_verdict == "review"
    ):
        escalation_triggers.append("submission_not_ready")

    recommended_escalation_layer = None
    next_action = "accept_final_verdict"
    if immediate_rules_veto:
        next_action = "respect_rules_veto"
    elif escalation_triggers:
        recommended_escalation_layer = "L2"
        next_action = "escalate_to_l2"
        if ai_verdict == "reject" and ruleset_verdict == "pass":
            recommended_escalation_layer = "L3"
            next_action = "escalate_to_l3"

    submission_reasons = list(submission_eligibility.get("reasons") or [])
    missing_reason_codes = list(submission_eligibility.get("missing_reason_codes") or [])
    unresolved_critical_fields = [
        item.get("field") if isinstance(item, dict) else item
        for item in (submission_eligibility.get("unresolved_critical_fields") or [])
    ]
    unresolved_critical_fields = [str(x).strip() for x in unresolved_critical_fields if str(x).strip()]
    review_required_reason = sorted(set(review_required_reason))
    escalation_triggers = sorted(set(escalation_triggers))

    return {
        "ai_verdict": ai_verdict,
        "ai_layers": ai_layers or None,
        "ai_execution_position": ai_execution_position,
        "ai_layer_contract_version": ai_layer_contract_version,
        "ruleset_verdict": ruleset_verdict,
        "final_verdict": final_verdict,
        "override_reason": override_reason,
        "disagreement_flag": disagreement_flag,
        "arbitration_mode": arbitration_mode,
        "review_required_reason": review_required_reason,
        "rules_veto_classes": rules_veto_classes,
        "rules_trigger_classes": rules_trigger_classes,
        "immediate_rules_veto": immediate_rules_veto,
        "escalation_triggers": escalation_triggers,
        "recommended_escalation_layer": recommended_escalation_layer,
        "next_action": next_action,
        "ai_source_verdict": ai_source_verdict,
        "rules_evidence": {
            "missing_critical_fields": missing_critical,
            "unresolved_critical_fields": unresolved_critical_fields,
            "missing_reason_codes": missing_reason_codes,
            "submission_can_submit": bool(submission_eligibility.get("can_submit", True)),
            "submission_reasons": submission_reasons,
            "bank_reasons": list(bank_verdict.get("reasons") or []),
            "bank_risk_flags": list(bank_verdict.get("risk_flags") or []),
            "bank_issue_summary": dict(bank_verdict.get("issue_summary") or {}),
            "bank_recommendation": bank_verdict.get("recommendation"),
            "bank_action_items": list(bank_verdict.get("action_items") or []),
            "bank_action_items_count": bank_verdict.get("action_items_count"),
            "rule_evidence_items": rule_evidence_items,
            "requirement_readiness_items": requirement_readiness_items,
            "requirement_reason_codes": requirement_reason_codes,
            "requirements_review_needed": bool(requirement_readiness_items),
            "documentary_review_needed": documentary_review_needed,
            "advisory_review_needed": advisory_review_needed,
            "issue_lanes": issue_lanes,
            "primary_decision_lane": primary_decision_lane,
            "domain_risk_summary": {k: v for k, v in domain_risk_summary.items() if v is not None},
            "reason_semantics": reason_semantics,
            "ai_execution_position": ai_execution_position,
            "ai_layer_verdicts": ai_layer_verdicts,
        },
        "evidence_summary": {
            "primary_review_drivers": review_required_reason,
            "primary_veto_drivers": rules_veto_classes,
            "primary_escalation_drivers": escalation_triggers,
            "submission_readiness": "ready" if submission_eligibility.get("can_submit", True) else "not_ready",
            "primary_decision_lane": primary_decision_lane,
            "advisory_review_needed": advisory_review_needed,
            "documentary_review_needed": documentary_review_needed,
            "domain_risk_summary": {k: v for k, v in domain_risk_summary.items() if v is not None},
            "reason_semantics": reason_semantics,
            "decision_basis": reason_semantics.get("rule_decision_basis", []),
            "evidence_quality": "rule_direct" if (reason_semantics.get("rule_decision_basis") or reason_semantics.get("requirement_findings")) else ("extraction_only" if reason_semantics.get("extraction_failures") else "mixed_or_unknown"),
            "bank_recommendation": bank_verdict.get("recommendation"),
            "bank_action_items_count": bank_verdict.get("action_items_count"),
            "requirement_reason_codes": requirement_reason_codes,
            "requirements_review_needed": bool(requirement_readiness_items),
            "advisory_action_titles": list(advisory_lane.get("titles") or [])[:5],
            "ai_execution_position": ai_execution_position,
            "ai_layer_verdicts": ai_layer_verdicts,
            "ai_layers_executed": sorted(
                layer_name
                for layer_name, layer in ai_layers.items()
                if isinstance(layer, dict) and layer.get("executed")
            ),
            "primary_requirement_actions": [
                str(item.get("title") or "").strip()
                for item in requirement_readiness_items
                if str(item.get("title") or "").strip()
            ][:5],
        },
        "ai_issue_counts": {
            "critical": ai_critical,
            "major": ai_major,
            "minor": ai_minor,
        },
        "rules_source_verdict": rules_raw or None,
    }

async def _run_validation_arbitration_escalation(
    validation_contract: Dict[str, Any],
    ai_validation: Optional[Dict[str, Any]],
    bank_verdict: Optional[Dict[str, Any]],
    submission_eligibility: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Run L2/L3 arbitration when the contract recommends escalation."""
    contract = dict(validation_contract or {})
    layer = str(contract.get("recommended_escalation_layer") or "").strip().upper()
    if not layer or layer not in {"L2", "L3"}:
        return contract
    if contract.get("immediate_rules_veto"):
        contract["escalation_result"] = {
            "attempted": False,
            "bypassed": True,
            "reason": "immediate_rules_veto",
        }
        return contract

    from app.services.llm_provider import LLMProviderFactory

    ai_validation = ai_validation or {}
    bank_verdict = bank_verdict or {}
    submission_eligibility = submission_eligibility or {}

    system_prompt = (
        "You are a conservative trade-finance arbitration layer. "
        "Given AI findings and deterministic rules findings, return JSON only with keys: "
        "escalated_verdict (pass|review|reject), confidence (0..1), rationale, rules_should_veto (boolean). "
        "Never override a hard deterministic veto. Prefer review over false pass."
    )
    prompt = json.dumps({
        "ai_verdict": contract.get("ai_verdict"),
        "ruleset_verdict": contract.get("ruleset_verdict"),
        "final_verdict_before_escalation": contract.get("final_verdict"),
        "override_reason": contract.get("override_reason"),
        "disagreement_flag": contract.get("disagreement_flag"),
        "review_required_reason": contract.get("review_required_reason"),
        "rules_veto_classes": contract.get("rules_veto_classes"),
        "rules_evidence": contract.get("rules_evidence"),
        "ai_issue_counts": contract.get("ai_issue_counts"),
        "bank_verdict": bank_verdict,
        "submission_eligibility": {
            "can_submit": submission_eligibility.get("can_submit"),
            "reasons": submission_eligibility.get("reasons"),
        },
    }, ensure_ascii=False)

    try:
        raw_output, _, _, provider_used = await LLMProviderFactory.generate_with_fallback(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.1,
            max_tokens=500,
            router_layer=layer,
        )
        parsed = _parse_json_if_possible(raw_output)
        escalated_verdict = str((parsed or {}).get("escalated_verdict") or "").strip().lower()
        if escalated_verdict not in {"pass", "review", "reject"}:
            escalated_verdict = contract.get("final_verdict")
        confidence = (parsed or {}).get("confidence")
        rationale = str((parsed or {}).get("rationale") or "").strip() or None
        rules_should_veto = bool((parsed or {}).get("rules_should_veto", False))

        if rules_should_veto and contract.get("rules_veto_classes"):
            escalated_verdict = "reject"

        if escalated_verdict == "pass" and contract.get("final_verdict") != "pass":
            escalated_verdict = "review"

        if escalated_verdict in {"review", "reject"} and escalated_verdict != contract.get("final_verdict"):
            contract["final_verdict"] = escalated_verdict
            contract["override_reason"] = contract.get("override_reason") or f"{layer.lower()}_arbitration_adjustment"

        contract["escalation_result"] = {
            "attempted": True,
            "layer": layer,
            "provider": provider_used,
            "escalated_verdict": escalated_verdict,
            "confidence": confidence,
            "rationale": rationale,
            "rules_should_veto": rules_should_veto,
        }
        if layer == "L2" and escalated_verdict == "review" and contract.get("disagreement_flag"):
            contract["next_action"] = "escalate_to_l3"
            contract["recommended_escalation_layer"] = "L3"
        else:
            contract["next_action"] = "accept_final_verdict"
            contract["recommended_escalation_layer"] = None
        return contract
    except Exception as exc:
        contract["escalation_result"] = {
            "attempted": True,
            "layer": layer,
            "error": str(exc),
        }
        return contract

def _build_submission_eligibility_context(
    gate_result: Dict[str, Any],
    field_decisions: Dict[str, Dict[str, Any]],
    documents: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Aggregate missing reason codes + unresolved critical statuses for submission eligibility."""
    gate_missing_critical = {
        str(field).strip()
        for field in ((gate_result or {}).get("missing_critical") or [])
        if str(field).strip()
    }
    unresolved = _build_unresolved_critical_context(
        field_decisions,
        critical_fields=gate_missing_critical,
        documents=documents,
    )
    unresolved_by_field = {
        str(item.get("field") or "").strip(): item
        for item in unresolved
        if isinstance(item, dict) and str(item.get("field") or "").strip()
    }

    hint_index = _build_document_field_hint_index(documents or [])
    for field_name in sorted(gate_missing_critical):
        if field_name in unresolved_by_field:
            continue
        fallback_entry = {
            "field": field_name,
            "status": "rejected",
            "reason_code": "critical_missing",
        }
        hint = hint_index.get(field_name) or {}
        if hint.get("source_document"):
            fallback_entry["source_document"] = hint.get("source_document")
        if hint.get("document_type"):
            fallback_entry["document_type"] = hint.get("document_type")
        unresolved.append(fallback_entry)
        unresolved_by_field[field_name] = fallback_entry

    reasons = set((gate_result or {}).get("missing_reason_codes") or [])
    statuses = set()
    for item in unresolved:
        reasons.add(item.get("reason_code") or "unknown")
        statuses.add(item.get("status") or "unknown")

    return {
        "missing_reason_codes": sorted(str(r) for r in reasons if r),
        "unresolved_critical_fields": unresolved,
        "unresolved_critical_statuses": sorted(str(s) for s in statuses if s),
    }

def _apply_workflow_stage_contract_overrides(
    workflow_stage: Optional[Dict[str, Any]],
    bank_verdict: Optional[Dict[str, Any]],
    submission_eligibility: Optional[Dict[str, Any]],
    validation_contract: Optional[Dict[str, Any]] = None,
    resolution_queue: Optional[Dict[str, Any]] = None,
) -> Dict[str, Dict[str, Any]]:
    workflow_stage = workflow_stage or {}
    stage = str(workflow_stage.get("stage") or "").strip().lower()

    bank_verdict = dict(bank_verdict or {})
    submission_eligibility = dict(submission_eligibility or {})
    validation_contract = dict(validation_contract or {})
    resolution_queue = dict(resolution_queue or {})

    if stage == "validation_results":
        summary = (
            str(workflow_stage.get("summary") or "").strip()
            or "Extraction is sufficiently resolved. Validation findings reflect the current confirmed document set."
        )
        queue_items = []
        queue_summary = {
            "total_items": 0,
            "user_resolvable_items": 0,
            "unresolved_documents": 0,
            "document_counts": {},
        }
        if isinstance(resolution_queue.get("summary"), dict):
            queue_summary.update(
                {
                    "total_items": 0,
                    "user_resolvable_items": 0,
                    "unresolved_documents": 0,
                    "document_counts": {},
                }
            )
        bank_reasons = [
            str(item).strip()
            for item in (bank_verdict.get("reasons") or [])
            if str(item).strip()
            and str(item).strip().lower() != "workflow_stage_extraction_resolution"
        ]
        action_items = [
            item
            for item in (bank_verdict.get("action_items") or [])
            if not (
                isinstance(item, dict)
                and str(item.get("issue") or "").strip().lower()
                == "confirm unresolved extracted fields"
            )
        ]
        bank_verdict.update(
            {
                "reasons": bank_reasons,
                "action_items": action_items,
                "action_items_count": len(action_items),
                "provisional_validation": False,
                "workflow_stage": dict(workflow_stage),
            }
        )
        submission_reasons = [
            str(item).strip()
            for item in (submission_eligibility.get("reasons") or [])
            if str(item).strip()
            and str(item).strip().lower() != "workflow_stage_extraction_resolution"
        ]
        submission_eligibility.update(
            {
                "reasons": submission_reasons,
                "missing_reason_codes": [],
                "unresolved_critical_fields": [],
                "unresolved_critical_statuses": [],
                "provisional_validation": False,
                "workflow_stage": dict(workflow_stage),
                "workflow_stage_summary": summary,
            }
        )

        review_required_reason = [
            str(item).strip()
            for item in (validation_contract.get("review_required_reason") or [])
            if str(item).strip()
            and str(item).strip().lower() != "workflow_stage_extraction_resolution"
            and not (
                submission_eligibility.get("can_submit", True)
                and str(item).strip().lower() == "submission_not_ready"
            )
        ]
        escalation_triggers = [
            str(item).strip()
            for item in (validation_contract.get("escalation_triggers") or [])
            if str(item).strip()
            and str(item).strip().lower() != "workflow_stage_extraction_resolution"
            and not (
                submission_eligibility.get("can_submit", True)
                and str(item).strip().lower() == "submission_not_ready"
            )
        ]

        rules_evidence = dict(validation_contract.get("rules_evidence") or {})
        reason_semantics = dict(rules_evidence.get("reason_semantics") or {})
        reason_semantics.update(
            {
                "extraction_failures": [],
                "missing_fields": [],
                "parse_failures": [],
            }
        )
        rules_evidence.update(
            {
                "missing_reason_codes": [],
                "unresolved_critical_fields": [],
                "submission_can_submit": bool(submission_eligibility.get("can_submit", True)),
                "workflow_stage": dict(workflow_stage),
                "workflow_stage_summary": summary,
                "reason_semantics": reason_semantics,
                "resolution_queue_v1": {
                    "version": "resolution_queue_v1",
                    "items": queue_items,
                    "summary": queue_summary,
                },
            }
        )

        evidence_summary = dict(validation_contract.get("evidence_summary") or {})
        summary_reason_semantics = dict(evidence_summary.get("reason_semantics") or {})
        summary_reason_semantics.update(
            {
                "extraction_failures": [],
                "missing_fields": [],
                "parse_failures": [],
            }
        )
        evidence_summary.update(
            {
                "submission_readiness": "ready" if submission_eligibility.get("can_submit", True) else "not_ready",
                "workflow_stage": stage,
                "workflow_stage_summary": summary,
                "provisional_validation": False,
                "reason_semantics": summary_reason_semantics,
            }
        )

        if str(validation_contract.get("override_reason") or "").strip().lower() == "extraction_resolution_pending":
            validation_contract["override_reason"] = None
        if str(validation_contract.get("arbitration_mode") or "").strip().lower() == "workflow_stage_resolution":
            validation_contract["arbitration_mode"] = "aligned"

        validation_contract.update(
            {
                "review_required_reason": sorted(set(review_required_reason)),
                "escalation_triggers": sorted(set(escalation_triggers)),
                "rules_evidence": rules_evidence,
                "evidence_summary": evidence_summary,
                "provisional_validation": False,
                "workflow_stage": dict(workflow_stage),
            }
        )

        return {
            "bank_verdict": bank_verdict,
            "submission_eligibility": submission_eligibility,
            "validation_contract": validation_contract,
        }

    if stage != "extraction_resolution":
        return {
            "bank_verdict": bank_verdict,
            "submission_eligibility": submission_eligibility,
            "validation_contract": validation_contract,
        }

    # When the tiered AI validation pipeline is enabled, validation actually
    # runs to completion even if the two-stage extractor flagged unresolved
    # critical fields — the AI layers are the judge. In that case we do NOT
    # apply the extraction_resolution override below (which locks out the
    # results UI and flips the verdict to provisional). Unresolved-field hints
    # remain on the workflow_stage payload as a soft note, but the findings
    # the pipeline actually produced flow through to the user.
    try:
        from app.config import settings as _app_settings
        _tiered_ai_enabled = bool(getattr(_app_settings, "VALIDATION_TIERED_AI_ENABLED", False))
    except Exception:
        _tiered_ai_enabled = False
    if _tiered_ai_enabled:
        return {
            "bank_verdict": bank_verdict,
            "submission_eligibility": submission_eligibility,
            "validation_contract": validation_contract,
        }

    summary = (
        str(workflow_stage.get("summary") or "").strip()
        or "Validation is still provisional until extracted fields are confirmed."
    )
    unresolved_documents = int(workflow_stage.get("unresolved_documents") or 0)
    unresolved_fields = int(workflow_stage.get("unresolved_fields") or 0)
    reason_code = "workflow_stage_extraction_resolution"

    bank_reasons = [str(item).strip() for item in (bank_verdict.get("reasons") or []) if str(item).strip()]
    if reason_code not in {item.lower() for item in bank_reasons}:
        bank_reasons.append(reason_code)
    action_items = list(bank_verdict.get("action_items") or [])
    if not any(
        str(item.get("issue") or "").strip().lower() == "confirm unresolved extracted fields"
        for item in action_items
        if isinstance(item, dict)
    ):
        action_items.insert(
            0,
            {
                "priority": "high",
                "issue": "Confirm unresolved extracted fields",
                "action": summary,
            },
        )
    issue_summary = dict(bank_verdict.get("issue_summary") or {})
    issue_summary["major"] = max(
        int(issue_summary.get("major") or 0),
        unresolved_documents or (1 if unresolved_fields else 0),
    )
    issue_summary["total"] = max(
        int(issue_summary.get("total") or 0),
        int(issue_summary.get("critical") or 0)
        + int(issue_summary.get("major") or 0)
        + int(issue_summary.get("minor") or 0),
    )
    bank_verdict.update(
        {
            "verdict": "CAUTION",
            "verdict_color": "yellow",
            "verdict_message": "Extraction resolution required before bank review",
            "recommendation": summary,
            "can_submit": False,
            "reasons": bank_reasons,
            "action_items": action_items,
            "action_items_count": len(action_items),
            "issue_summary": issue_summary,
            "provisional_validation": True,
            "workflow_stage": dict(workflow_stage),
        }
    )

    submission_reasons = [
        str(item).strip() for item in (submission_eligibility.get("reasons") or []) if str(item).strip()
    ]
    if reason_code not in {item.lower() for item in submission_reasons}:
        submission_reasons.append(reason_code)
    submission_eligibility.update(
        {
            "can_submit": False,
            "reasons": submission_reasons,
            "source": submission_eligibility.get("source") or "validation",
            "provisional_validation": True,
            "workflow_stage": dict(workflow_stage),
            "workflow_stage_summary": summary,
        }
    )

    review_required_reason = [
        str(item).strip() for item in (validation_contract.get("review_required_reason") or []) if str(item).strip()
    ]
    if reason_code not in {item.lower() for item in review_required_reason}:
        review_required_reason.append(reason_code)
    escalation_triggers = [
        str(item).strip() for item in (validation_contract.get("escalation_triggers") or []) if str(item).strip()
    ]
    if reason_code not in {item.lower() for item in escalation_triggers}:
        escalation_triggers.append(reason_code)

    rules_evidence = dict(validation_contract.get("rules_evidence") or {})
    rules_submission_reasons = [
        str(item).strip() for item in (rules_evidence.get("submission_reasons") or []) if str(item).strip()
    ]
    if reason_code not in {item.lower() for item in rules_submission_reasons}:
        rules_submission_reasons.append(reason_code)
    rules_evidence.update(
        {
            "submission_can_submit": False,
            "submission_reasons": rules_submission_reasons,
            "workflow_stage": dict(workflow_stage),
            "workflow_stage_summary": summary,
        }
    )

    evidence_summary = dict(validation_contract.get("evidence_summary") or {})
    evidence_summary.update(
        {
            "submission_readiness": "not_ready",
            "workflow_stage": stage,
            "workflow_stage_summary": summary,
            "provisional_validation": True,
        }
    )

    validation_contract.update(
        {
            "final_verdict": "review",
            "override_reason": "extraction_resolution_pending",
            "arbitration_mode": "workflow_stage_resolution",
            "review_required_reason": sorted(set(review_required_reason)),
            "escalation_triggers": sorted(set(escalation_triggers)),
            "recommended_escalation_layer": None,
            "next_action": "confirm_extracted_fields",
            "rules_evidence": rules_evidence,
            "evidence_summary": evidence_summary,
            "provisional_validation": True,
            "workflow_stage": dict(workflow_stage),
        }
    )

    return {
        "bank_verdict": bank_verdict,
        "submission_eligibility": submission_eligibility,
        "validation_contract": validation_contract,
    }


def _apply_validation_contract_decision_surfaces(
    bank_verdict: Optional[Dict[str, Any]],
    submission_eligibility: Optional[Dict[str, Any]],
    validation_contract: Optional[Dict[str, Any]] = None,
) -> Dict[str, Dict[str, Any]]:
    bank_verdict = dict(bank_verdict or {})
    submission_eligibility = dict(submission_eligibility or {})
    validation_contract = dict(validation_contract or {})

    final_verdict = str(validation_contract.get("final_verdict") or "").strip().lower()
    if final_verdict not in {"pass", "review", "reject"}:
        return {
            "bank_verdict": bank_verdict,
            "submission_eligibility": submission_eligibility,
            "validation_contract": validation_contract,
        }

    final_can_submit = final_verdict == "pass"
    verdict_map = {
        "pass": "SUBMIT",
        "review": "CAUTION",
        "reject": "REJECT",
    }
    verdict_color_map = {
        "pass": "green",
        "review": "yellow",
        "reject": "red",
    }
    verdict_message_map = {
        "pass": "Ready for presentation based on current validation findings",
        "review": "Review required before bank submission",
        "reject": "Blocking discrepancies must be resolved before submission",
    }
    recommendation_map = {
        "pass": "Proceed with submission using the current validated document set.",
        "review": "Resolve review items before submitting to the bank.",
        "reject": "Do not submit until blocking discrepancies are resolved.",
    }

    bank_verdict.update(
        {
            "verdict": verdict_map[final_verdict],
            "verdict_color": verdict_color_map[final_verdict],
            "verdict_message": verdict_message_map[final_verdict],
            "recommendation": recommendation_map[final_verdict],
            "can_submit": final_can_submit,
        }
    )

    prior_reasons = [
        str(item).strip()
        for item in (submission_eligibility.get("reasons") or [])
        if str(item).strip()
    ]
    normalized_prior = {
        reason.lower()
        for reason in prior_reasons
        if not reason.lower().startswith("validation_contract_")
        and not reason.lower().startswith("bank_verdict_")
    }
    submission_reasons = [
        reason
        for reason in prior_reasons
        if reason.lower() in normalized_prior
    ]
    if not final_can_submit:
        submission_reasons.append(f"validation_contract_{final_verdict}")

    deduped_reasons: List[str] = []
    seen_reasons: set[str] = set()
    for reason in submission_reasons:
        normalized_reason = reason.lower()
        if normalized_reason in seen_reasons:
            continue
        seen_reasons.add(normalized_reason)
        deduped_reasons.append(reason)

    submission_eligibility.update(
        {
            "can_submit": final_can_submit,
            "reasons": deduped_reasons,
            "review_required": final_verdict == "review",
        }
    )

    rules_evidence = dict(validation_contract.get("rules_evidence") or {})
    rules_evidence.update(
        {
            "submission_can_submit": final_can_submit,
            "submission_reasons": list(deduped_reasons),
            "bank_recommendation": bank_verdict.get("recommendation"),
            "bank_action_items_count": bank_verdict.get("action_items_count"),
        }
    )

    evidence_summary = dict(validation_contract.get("evidence_summary") or {})
    evidence_summary.update(
        {
            "submission_readiness": "ready" if final_can_submit else "not_ready",
            "bank_recommendation": bank_verdict.get("recommendation"),
            "bank_action_items_count": bank_verdict.get("action_items_count"),
        }
    )

    validation_contract.update(
        {
            "rules_evidence": rules_evidence,
            "evidence_summary": evidence_summary,
        }
    )

    return {
        "bank_verdict": bank_verdict,
        "submission_eligibility": submission_eligibility,
        "validation_contract": validation_contract,
    }

def _parse_json_if_possible(value: Any) -> Any:
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("{") or stripped.startswith("["):
            try:
                return json.loads(stripped)
            except json.JSONDecodeError:
                logger.warning("Failed to parse JSON string in LC payload; leaving raw text")
                return value
    return value
