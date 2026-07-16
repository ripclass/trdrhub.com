"""RulHub requirements adapter that stores references, not the rule corpus."""

from __future__ import annotations

from typing import Any, Mapping

from app.services.rulhub_client import get_rulhub_client

from .base import AdapterResult


class RulHubRequirementsAdapter:
    module = "rulhub"
    version = "rulhub-api-v1"

    async def run(self, context: Mapping[str, Any]) -> AdapterResult:
        product = context.get("product") or context.get("commodity") or "trade transaction"
        query = " ".join(
            str(value) for value in (
                product,
                context.get("origin_country"),
                context.get("destination_country"),
                context.get("payment_arrangement"),
                context.get("transport_mode"),
            ) if value
        )
        result = await get_rulhub_client().search_rules(query=query, per_page=50)
        rows = result.get("results") if isinstance(result, dict) else []
        references: list[dict[str, Any]] = []
        for row in rows or []:
            if not isinstance(row, dict):
                continue
            references.append({
                "id": row.get("id") or row.get("rule_id"),
                "version": row.get("version") or row.get("rule_version"),
                "source": row.get("source"),
                "article": row.get("article") or row.get("clause"),
                "domain": row.get("domain"),
            })
        return AdapterResult(
            state="clear",
            summary=f"Retrieved {len(references)} applicable rule reference(s) for analyst application.",
            source_record_type="rulhub_requirement_set",
            metadata={"evaluated_query": query, "requirements": references},
        )


__all__ = ["RulHubRequirementsAdapter"]
