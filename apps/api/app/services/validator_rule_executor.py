from __future__ import annotations

import copy
import logging
from typing import Any, Dict, List, Tuple

from app.config import settings
from app.services.rule_evaluator import RuleEvaluator
from app.services.semantic_compare import run_semantic_comparison

logger = logging.getLogger(__name__)


async def execute_rules_with_semantics(
    rules_with_meta: List[Tuple[Dict[str, Any], Dict[str, Any]]],
    document_data: Dict[str, Any],
    base_metadata: Dict[str, Any],
    *,
    domain_sequence: List[str],
    jurisdiction: str,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Execute prepared validator rules including semantic_check condition expansion.

    Returns:
        (result_rows, prepared_rule_count)
    """
    evaluator = RuleEvaluator()
    rule_envelopes = [
        {"rule": rule, "meta": meta}
        for rule, meta in rules_with_meta
    ]
    prepared_rules = [env["rule"] for env in rule_envelopes]

    prepared_rules, semantic_registry = await _inject_semantic_conditions(
        prepared_rules,
        document_data,
        evaluator,
    )
    for idx, rule in enumerate(prepared_rules):
        rule_envelopes[idx]["rule"] = rule

    evaluation_result = await evaluator.evaluate_rules(prepared_rules, document_data)
    outcomes = evaluation_result.get("outcomes", [])

    results: List[Dict[str, Any]] = []
    for idx, outcome in enumerate(outcomes):
        if outcome.get("not_applicable", False):
            continue

        envelope = rule_envelopes[idx] if idx < len(rule_envelopes) else {"rule": {}, "meta": base_metadata}
        rule_def = envelope.get("rule", {}) or {}
        meta = envelope.get("meta") or base_metadata or {}

        result_payload = {
            "rule": outcome.get("rule_id", rule_def.get("rule_id", "unknown")),
            "title": rule_def.get("title") or outcome.get("rule_id", "unknown"),
            "description": rule_def.get("description"),
            "article": rule_def.get("article"),
            "tags": rule_def.get("tags"),
            "documents": rule_def.get("documents") or rule_def.get("document_types"),
            "display_card": rule_def.get("display_card") or rule_def.get("ui_card"),
            "expected_outcome": rule_def.get("expected_outcome"),
            "passed": outcome.get("passed", False),
            "severity": outcome.get("severity", rule_def.get("severity", "warning")),
            "message": outcome.get("message", rule_def.get("description") or ""),
            "ruleset_id": meta.get("ruleset_id"),
            "ruleset_version": meta.get("ruleset_version"),
            "rulebook_version": meta.get("rulebook_version"),
            "ruleset_domain": meta.get("domain"),
            "jurisdiction": meta.get("jurisdiction"),
            "rule_count_used": meta.get("rule_count_used"),
        }

        sem_keys = semantic_registry.get(result_payload["rule"], [])
        if sem_keys:
            semantic_store = document_data.get("_semantic") or {}
            comparisons = [
                semantic_store.get(key)
                for key in sem_keys
                if semantic_store.get(key)
            ]
            if comparisons:
                result_payload["semantic_differences"] = comparisons
                primary = comparisons[0]
                if primary.get("expected"):
                    result_payload.setdefault("expected", primary.get("expected"))
                if primary.get("found"):
                    result_payload.setdefault("actual", primary.get("found"))
                if primary.get("suggested_fix"):
                    result_payload.setdefault("suggestion", primary.get("suggested_fix"))
                if not result_payload.get("documents") and primary.get("documents"):
                    result_payload["documents"] = primary.get("documents")

        results.append(result_payload)

    logger.info(
        "Evaluated %d rules using DB-backed system (domains=%s, jurisdiction=%s)",
        len(prepared_rules),
        domain_sequence,
        jurisdiction,
    )
    return results, len(prepared_rules)


async def _inject_semantic_conditions(
    rules: List[Dict[str, Any]],
    document_data: Dict[str, Any],
    evaluator: RuleEvaluator,
) -> Tuple[List[Dict[str, Any]], Dict[str, List[str]]]:
    """
    Scan rules for semantic_check operators, evaluate them (AI or fallback), and
    replace with deterministic boolean checks.
    """
    if not rules:
        return rules, {}

    semantic_registry: Dict[str, List[str]] = {}
    semantic_store: Dict[str, Dict[str, Any]] = {}
    updated_rules: List[Dict[str, Any]] = []

    for rule in rules:
        working_rule = copy.deepcopy(rule)
        rule_id = working_rule.get("rule_id") or working_rule.get("rule") or "rule"
        conditions = working_rule.get("conditions") or []

        for idx, condition in enumerate(list(conditions)):
            operator = (condition.get("operator") or "").lower()
            if operator != "semantic_check":
                continue

            field_path = condition.get("field")
            left_value = evaluator.resolve_field_path(document_data, field_path) if field_path else None

            right_value = None
            if condition.get("value_ref"):
                right_value = evaluator.resolve_field_path(document_data, condition["value_ref"])
            elif condition.get("value") is not None:
                right_value = condition.get("value")

            semantic_cfg = condition.get("semantic") or {}
            context_label = semantic_cfg.get("context") or field_path or working_rule.get("title") or "cross_document"
            doc_hints = semantic_cfg.get("documents") or working_rule.get("documents") or working_rule.get("document_types") or []
            if isinstance(doc_hints, str):
                doc_hints = [doc_hints]

            comparison = await run_semantic_comparison(
                left_value,
                right_value,
                context=context_label,
                documents=doc_hints,
                threshold=semantic_cfg.get("threshold") or settings.AI_SEMANTIC_THRESHOLD_DEFAULT,
                enable_ai=semantic_cfg.get("enable_ai"),
            )

            semantic_key = f"{rule_id}:{idx}"
            semantic_store[semantic_key] = comparison
            semantic_registry.setdefault(rule_id, []).append(semantic_key)

            working_rule["conditions"][idx] = {
                "field": f"_semantic.{semantic_key}.match",
                "operator": "equals",
                "value": True,
                "message": condition.get("message"),
                "rule_type": condition.get("rule_type"),
            }

        updated_rules.append(working_rule)

    if semantic_store:
        document_data.setdefault("_semantic", {}).update(semantic_store)

    return updated_rules, semantic_registry
