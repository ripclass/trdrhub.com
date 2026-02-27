from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


async def load_rules_with_provenance(
    *,
    rules_service,
    domain_sequence: List[str],
    jurisdiction: str,
    document_type: str,
) -> Tuple[List[Tuple[Dict[str, Any], Dict[str, Any]]], Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Load rules across primary + supplemental domains and attach per-rule provenance.

    Contract preserved from validator pipeline:
    - Primary domain is fail-closed.
    - Supplemental domains are best-effort.
    - Returned tuples are (rule, meta).
    """
    aggregated_rules: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
    base_metadata: Optional[Dict[str, Any]] = None
    provenance_rulesets: List[Dict[str, Any]] = []

    for idx, domain_key in enumerate(domain_sequence):
        is_primary_domain = idx == 0
        try:
            logger.info(
                "Fetching ruleset from DB",
                extra={
                    "domain": domain_key,
                    "jurisdiction": jurisdiction,
                    "document_type": document_type,
                    "index": idx,
                    "is_primary_domain": is_primary_domain,
                },
            )
            ruleset_data = await rules_service.get_active_ruleset(
                domain_key,
                jurisdiction,
                document_type=document_type,
            )

            # For ICC global rulebooks, gracefully fallback to global jurisdiction
            # when country-specific jurisdiction has no published ruleset.
            effective_jurisdiction = jurisdiction
            if ruleset_data is None and domain_key.startswith("icc.") and jurisdiction != "global":
                ruleset_data = await rules_service.get_active_ruleset(
                    domain_key,
                    "global",
                    document_type=document_type,
                )
                if ruleset_data is not None:
                    effective_jurisdiction = "global"
                    logger.info(
                        "Using global ICC ruleset fallback",
                        extra={
                            "domain": domain_key,
                            "requested_jurisdiction": jurisdiction,
                            "fallback_jurisdiction": "global",
                            "document_type": document_type,
                        },
                    )

            # Fail-closed for primary domain only; supplements are best-effort.
            if ruleset_data is None:
                if is_primary_domain:
                    raise RuntimeError(
                        f"No active ruleset found for domain={domain_key}, jurisdiction={jurisdiction}"
                    )
                logger.warning(
                    "Supplement ruleset unavailable; continuing with primary ruleset",
                    extra={
                        "domain": domain_key,
                        "jurisdiction": jurisdiction,
                        "document_type": document_type,
                    },
                )
                continue

            logger.info(
                "Loaded ruleset from DB",
                extra={
                    "domain": domain_key,
                    "jurisdiction": jurisdiction,
                    "document_type": document_type,
                    "rule_count": len(ruleset_data.get("rules", [])),
                },
            )
        except Exception as e:
            # For ICC primary rulesets, if country-jurisdiction lookup raises due missing active
            # ruleset, attempt a global fallback before fail-closing.
            if (
                is_primary_domain
                and domain_key.startswith("icc.")
                and jurisdiction != "global"
                and "No active ruleset found" in str(e)
            ):
                try:
                    ruleset_data = await rules_service.get_active_ruleset(
                        domain_key,
                        "global",
                        document_type=document_type,
                    )
                    if ruleset_data is not None:
                        effective_jurisdiction = "global"
                        logger.info(
                            "Recovered via global ICC ruleset fallback after exception",
                            extra={
                                "domain": domain_key,
                                "requested_jurisdiction": jurisdiction,
                                "fallback_jurisdiction": "global",
                                "document_type": document_type,
                            },
                        )
                    else:
                        raise e
                except Exception:
                    logger.error(
                        "Ruleset fetch failed (fail-closed)",
                        exc_info=True,
                        extra={
                            "domain": domain_key,
                            "jurisdiction": jurisdiction,
                            "document_type": document_type,
                            "is_primary_domain": is_primary_domain,
                            "error": str(e),
                        },
                    )
                    raise RuntimeError(
                        f"Ruleset fetch failed for domain={domain_key}, jurisdiction={jurisdiction}: {e}"
                    ) from e
            else:
                logger.error(
                    "Ruleset fetch failed (fail-closed)",
                    exc_info=True,
                    extra={
                        "domain": domain_key,
                        "jurisdiction": jurisdiction,
                        "document_type": document_type,
                        "is_primary_domain": is_primary_domain,
                        "error": str(e),
                    },
                )
                # Preserve strict fail-closed behavior for primary ruleset.
                if is_primary_domain:
                    raise RuntimeError(
                        f"Ruleset fetch failed for domain={domain_key}, jurisdiction={jurisdiction}: {e}"
                    ) from e

                # Supplements are additive and should not block core validation verdict.
                continue

        ruleset_meta = ruleset_data.get("ruleset") or {}
        meta = {
            "ruleset_id": ruleset_meta.get("id"),
            "domain": domain_key,
            "jurisdiction": effective_jurisdiction,
            "ruleset_version": ruleset_data.get("ruleset_version"),
            "rulebook_version": ruleset_data.get("rulebook_version"),
            "rule_count_used": len(ruleset_data.get("rules", []) or []),
        }
        provenance_rulesets.append({
            "ruleset_id": meta.get("ruleset_id"),
            "ruleset_version": meta.get("ruleset_version"),
            "domain": meta.get("domain"),
            "jurisdiction": meta.get("jurisdiction"),
            "rule_count_used": meta.get("rule_count_used"),
        })
        if idx == 0:
            base_metadata = meta

        for rule in ruleset_data.get("rules", []) or []:
            aggregated_rules.append((rule, meta))

    return aggregated_rules, base_metadata, provenance_rulesets
