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
        normalized_domain = (domain_key or "").strip().lower()
        requested_jurisdiction = (jurisdiction or "global").strip().lower()
        try:
            logger.info(
                "Fetching ruleset from DB",
                extra={
                    "domain": normalized_domain,
                    "jurisdiction": requested_jurisdiction,
                    "document_type": document_type,
                    "index": idx,
                    "is_primary_domain": is_primary_domain,
                },
            )
            ruleset_data = await rules_service.get_active_ruleset(
                normalized_domain,
                requested_jurisdiction,
                document_type=document_type,
            )

            # For ICC global rulebooks, gracefully fallback to global jurisdiction
            # when country-specific jurisdiction has no published ruleset.
            effective_jurisdiction = requested_jurisdiction
            if ruleset_data is None and normalized_domain.startswith("icc.") and requested_jurisdiction != "global":
                ruleset_data = await rules_service.get_active_ruleset(
                    normalized_domain,
                    "global",
                    document_type=document_type,
                )
                if ruleset_data is not None:
                    effective_jurisdiction = "global"
                    logger.info(
                        "Using global ICC ruleset fallback",
                        extra={
                            "domain": normalized_domain,
                            "requested_jurisdiction": requested_jurisdiction,
                            "fallback_jurisdiction": "global",
                            "document_type": document_type,
                        },
                    )

            # Fail-closed for primary domain only; supplements are best-effort.
            if ruleset_data is None:
                if is_primary_domain:
                    raise RuntimeError(
                        f"No active ruleset found for domain={normalized_domain}, jurisdiction={requested_jurisdiction}"
                    )
                logger.warning(
                    "Supplement ruleset unavailable; continuing with primary ruleset",
                    extra={
                        "domain": normalized_domain,
                        "jurisdiction": requested_jurisdiction,
                        "document_type": document_type,
                    },
                )
                continue

            loaded_rule_count = len(ruleset_data.get("rules", []) or [])
            if is_primary_domain and loaded_rule_count == 0 and (document_type or "").strip().lower() not in ("", "lc"):
                logger.warning(
                    "Primary ruleset resolved with zero rules for document_type; retrying unfiltered fetch",
                    extra={
                        "domain": normalized_domain,
                        "jurisdiction": effective_jurisdiction,
                        "document_type": document_type,
                    },
                )
                fallback_ruleset_data = await rules_service.get_active_ruleset(
                    normalized_domain,
                    effective_jurisdiction,
                    document_type=None,
                )
                fallback_rule_count = len((fallback_ruleset_data or {}).get("rules", []) or [])
                if fallback_ruleset_data is not None and fallback_rule_count > 0:
                    logger.info(
                        "Recovered primary ruleset via unfiltered fetch",
                        extra={
                            "domain": normalized_domain,
                            "jurisdiction": effective_jurisdiction,
                            "requested_document_type": document_type,
                            "fallback_document_type": "*",
                            "rule_count": fallback_rule_count,
                        },
                    )
                    ruleset_data = fallback_ruleset_data
                    loaded_rule_count = fallback_rule_count

            logger.info(
                "Loaded ruleset from DB",
                extra={
                    "domain": normalized_domain,
                    "jurisdiction": effective_jurisdiction,
                    "document_type": document_type,
                    "rule_count": loaded_rule_count,
                },
            )
        except Exception as e:
            # For ICC primary rulesets, if country-jurisdiction lookup raises due missing active
            # ruleset, attempt a global fallback before fail-closing.
            if (
                is_primary_domain
                and normalized_domain.startswith("icc.")
                and requested_jurisdiction != "global"
                and "No active ruleset found" in str(e)
            ):
                try:
                    ruleset_data = await rules_service.get_active_ruleset(
                        normalized_domain,
                        "global",
                        document_type=document_type,
                    )
                    if ruleset_data is not None:
                        effective_jurisdiction = "global"
                        logger.info(
                            "Recovered via global ICC ruleset fallback after exception",
                            extra={
                                "domain": normalized_domain,
                                "requested_jurisdiction": requested_jurisdiction,
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
                            "domain": normalized_domain,
                            "jurisdiction": requested_jurisdiction,
                            "document_type": document_type,
                            "is_primary_domain": is_primary_domain,
                            "error": str(e),
                        },
                    )
                    raise RuntimeError(
                        f"Ruleset fetch failed for domain={normalized_domain}, jurisdiction={requested_jurisdiction}: {e}"
                    ) from e
            else:
                logger.error(
                    "Ruleset fetch failed (fail-closed)",
                    exc_info=True,
                    extra={
                        "domain": normalized_domain,
                        "jurisdiction": requested_jurisdiction,
                        "document_type": document_type,
                        "is_primary_domain": is_primary_domain,
                        "error": str(e),
                    },
                )
                # Preserve strict fail-closed behavior for primary ruleset.
                if is_primary_domain:
                    raise RuntimeError(
                        f"Ruleset fetch failed for domain={normalized_domain}, jurisdiction={requested_jurisdiction}: {e}"
                    ) from e

                # Supplements are additive and should not block core validation verdict.
                continue

        ruleset_meta = ruleset_data.get("ruleset") or {}
        meta = {
            "ruleset_id": ruleset_meta.get("id"),
            "domain": normalized_domain,
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
