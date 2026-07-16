"""RulHub references are auditable and never mistaken for an evaluated clearance."""

from __future__ import annotations

import asyncio

from app.integrations.proofline.rulhub import RulHubRequirementsAdapter
from app.services.rulhub_client import RulHubAPIError


class _Client:
    def __init__(self):
        self.calls = 0

    async def search_rules(self, **payload):
        self.calls += 1
        if self.calls == 1:
            raise RulHubAPIError(503, "temporary outage with private diagnostics")
        assert "document_type" not in payload
        return {
            "request_id": "rh-request-1",
            "results": [{
                "id": "rule-9", "version": "2025-07", "source": "Bangladesh Bank",
                "article": "Part D", "domain": "export.open_account",
                "title": "full corpus text must not be copied",
            }],
        }


def test_rulhub_retries_transient_failure_and_returns_references_for_review():
    client = _Client()
    result = asyncio.run(RulHubRequirementsAdapter(client=client, retry_delay=0).run({
        "trade_case_id": "case-1", "origin_country": "BD", "destination_country": "US",
        "payment_arrangement": "open_account", "transport_mode": "sea",
        "shipment_date": "2026-07-30", "product": "cotton garments",
        "documents": {"commercial_invoice": {}, "transport_document": {}},
        "cbam_requested": False, "eudr_requested": False,
    }))

    assert client.calls == 2
    assert result.state == "pending_review"
    assert result.source_record_id == "rh-request-1"
    reference = result.metadata["requirements"][0]
    assert reference == {
        "id": "rule-9", "version": "2025-07", "source": "Bangladesh Bank",
        "article": "Part D", "domain": "export.open_account",
        "evaluation_result": "pending_analyst_application",
    }
    assert "title" not in reference
    assert result.metadata["transaction_context"]["document_types"] == ["commercial_invoice", "transport_document"]
