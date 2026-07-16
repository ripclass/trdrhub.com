"""RulHub requirements adapter that stores references, not the rule corpus."""

from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Mapping

from app.services.rulhub_client import RulHubAPIError, RulHubClient, get_rulhub_client

from .base import AdapterResult


class RulHubRequirementsAdapter:
    module = "rulhub"
    version = "rulhub-api-v1"

    def __init__(self, client: RulHubClient | None = None, *, retry_delay: float = 0.2) -> None:
        self.client = client or get_rulhub_client()
        self.retry_delay = retry_delay

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
        transaction_context = {
            "export_country": context.get("origin_country"),
            "import_country": context.get("destination_country"),
            "product": product,
            "transaction_type": context.get("transaction_type") or "trade_case",
            "payment_method": context.get("payment_arrangement"),
            "transport_mode": context.get("transport_mode"),
            "shipment_date": context.get("shipment_date"),
            "document_types": sorted(str(key) for key in (context.get("documents") or {}).keys()),
            "buyer_requirements_requested": bool(context.get("buyer_requirements_present")),
            "regulatory_modules_requested": [
                module for module in ("cbam", "eudr") if context.get(f"{module}_requested")
            ],
        }
        result = None
        for attempt in range(2):
            try:
                result = await self.client.search_rules(query=query, per_page=50)
                break
            except RulHubAPIError as exc:
                if attempt == 0 and exc.status_code in {429, 500, 502, 503, 504}:
                    await asyncio.sleep(self.retry_delay)
                    continue
                raise
        if not isinstance(result, dict):
            raise RulHubAPIError(502, "Invalid structured response")
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
                "evaluation_result": row.get("evaluation_result") or "pending_analyst_application",
            })
        source_id = result.get("request_id") or result.get("evaluation_id")
        if not source_id:
            material = json.dumps(references, sort_keys=True, default=str).encode("utf-8")
            source_id = f"rulhub-{hashlib.sha256(material).hexdigest()[:16]}"
        return AdapterResult(
            state="pending_review",
            summary=f"Retrieved {len(references)} applicable rule reference(s) for analyst application.",
            source_record_type="rulhub_requirement_set",
            source_record_id=str(source_id),
            metadata={
                "evaluated_query": query,
                "transaction_context": transaction_context,
                "requirements": references,
                "evaluated_at": datetime.now(timezone.utc).isoformat(),
            },
        )


__all__ = ["RulHubRequirementsAdapter"]
