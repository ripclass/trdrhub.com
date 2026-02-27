from __future__ import annotations

from typing import Any, Dict, List, Optional


def build_validation_results(
    *,
    outcomes: List[Dict[str, Any]],
    rule_envelopes: List[Dict[str, Any]],
    document_data: Dict[str, Any],
    semantic_registry: Dict[str, List[str]],
    base_metadata: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
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

    return results


def build_validation_provenance(
    *,
    base_metadata: Optional[Dict[str, Any]],
    jurisdiction: str,
    prepared_rule_count: int,
    provenance_rulesets: List[Dict[str, Any]],
) -> Dict[str, Any]:
    return {
        "success": True,
        "domain": base_metadata.get("domain") if base_metadata else None,
        "jurisdiction": jurisdiction,
        "ruleset_id": base_metadata.get("ruleset_id") if base_metadata else None,
        "ruleset_version": base_metadata.get("ruleset_version") if base_metadata else None,
        "rule_count_used": prepared_rule_count,
        "rulesets": provenance_rulesets,
    }
