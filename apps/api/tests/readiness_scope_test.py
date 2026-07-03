"""CBAM/EUDR readiness — scope verdicts + engine degradation (Phase 3 launch)."""

import asyncio
from unittest.mock import patch

from app.services.readiness import (
    cbam_scope_verdict,
    eudr_scope_verdict,
    run_readiness_engine,
)


# ---------------------------------------------------------------------------
# CBAM scope ladder
# ---------------------------------------------------------------------------

def test_cbam_covered_category_over_50t_is_in_scope():
    v = cbam_scope_verdict({"product_category": "iron_steel", "sells_to_eu": "yes",
                            "annual_volume": "over_50t"})
    assert v["verdict"] == "likely_in_scope"


def test_cbam_cn_code_alone_matches_annex():
    v = cbam_scope_verdict({"product_category": "other", "cn_code": "7208 51",
                            "sells_to_eu": "yes", "annual_volume": "over_50t"})
    assert v["verdict"] == "likely_in_scope"
    assert any("7208" in r for r in v["reasons"])


def test_cbam_uncovered_category_is_out():
    v = cbam_scope_verdict({"product_category": "other", "cn_code": "6109",
                            "sells_to_eu": "yes", "annual_volume": "over_50t"})
    assert v["verdict"] == "likely_out_of_scope"


def test_cbam_no_eu_sales_is_out():
    v = cbam_scope_verdict({"product_category": "aluminium", "sells_to_eu": "no",
                            "annual_volume": "over_50t"})
    assert v["verdict"] == "likely_out_of_scope"


def test_cbam_under_de_minimis_is_borderline():
    v = cbam_scope_verdict({"product_category": "cement", "sells_to_eu": "yes",
                            "annual_volume": "under_50t"})
    assert v["verdict"] == "borderline"


def test_cbam_unknown_volume_is_borderline():
    v = cbam_scope_verdict({"product_category": "fertilisers", "sells_to_eu": "yes",
                            "annual_volume": "unsure"})
    assert v["verdict"] == "borderline"


# ---------------------------------------------------------------------------
# EUDR scope ladder
# ---------------------------------------------------------------------------

def test_eudr_covered_commodity_to_eu_is_in_scope():
    v = eudr_scope_verdict({"commodity": "cattle_leather", "sells_to_eu": "yes",
                            "buyer_size": "large", "geolocation": "no"})
    assert v["verdict"] == "likely_in_scope"
    assert any("30 December 2026" in r for r in v["reasons"])


def test_eudr_uncovered_commodity_is_out():
    v = eudr_scope_verdict({"commodity": "other", "sells_to_eu": "yes"})
    assert v["verdict"] == "likely_out_of_scope"


def test_eudr_no_eu_sales_is_out():
    v = eudr_scope_verdict({"commodity": "coffee", "sells_to_eu": "no"})
    assert v["verdict"] == "likely_out_of_scope"


# ---------------------------------------------------------------------------
# Paid engine — severity from answers, citations from RulHub, degradation
# ---------------------------------------------------------------------------

class _StubClient:
    def __init__(self, fail=False):
        self.fail = fail

    async def lookup_rules(self, **params):
        if self.fail:
            raise RuntimeError("rulhub down")
        return {"results": [{"rule_id": "cbam.Art-35", "source": "cbam_regulation",
                             "article": "35", "text": "Reporting obligations…"}]}

    async def search_rules(self, query, **kwargs):
        if self.fail:
            raise RuntimeError("rulhub down")
        return {"results": [{"rule_id": "cbam.Art-35", "source": "cbam_regulation",
                             "article": "35", "text": "The reporting declarant shall report…"}]}


def test_engine_maps_gap_answers_to_major_with_citation():
    with patch("app.services.rulhub_client.get_rulhub_client", return_value=_StubClient()):
        result = asyncio.run(run_readiness_engine("cbam", {
            "emissions_data": "no", "monitoring_system": "partial",
            "carbon_price_paid": "yes", "buyer_requests": "yes",
        }))
    assert result["engine_error"] is None
    by_sev = {i["title"]: i["severity"] for i in result["issues"]}
    assert any(sev == "major" and t.startswith("[GAP]") for t, sev in by_sev.items())
    assert any(sev == "minor" and t.startswith("[PARTIAL]") for t, sev in by_sev.items())
    # Every finding cites the corpus when RulHub is up.
    assert all(i["clause_cited"] for i in result["issues"])


def test_engine_survives_rulhub_outage_with_error_flag():
    with patch("app.services.rulhub_client.get_rulhub_client", return_value=_StubClient(fail=True)):
        result = asyncio.run(run_readiness_engine("eudr", {
            "supply_chain_visibility": "no", "cutoff_evidence": "no",
            "legality_docs": "partial", "traceability_system": "yes",
        }))
    # Findings still produced (uncited), job can still enter the queue.
    assert len(result["issues"]) == 4
    assert result["engine_error"] is not None
    assert all(i["clause_cited"] == "" for i in result["issues"])


def test_engine_both_covers_both_corpora():
    with patch("app.services.rulhub_client.get_rulhub_client", return_value=_StubClient()):
        result = asyncio.run(run_readiness_engine("both", {}))
    assert len(result["issues"]) == 8  # 4 CBAM + 4 EUDR topics
