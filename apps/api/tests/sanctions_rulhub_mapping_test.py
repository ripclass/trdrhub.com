"""Fail-closed semantics of the RulHub sanctions mapping (Phase 2 launch).

These tests guard the status ladder in
``app/services/sanctions_rulhub.map_rulhub_result``:

* a designated-party hit is a ``match`` and carries the block action;
* a fuzzy possible_match (or a severe programme red flag) is ``potential_match``;
* ``clear`` requires that the engine actually evaluated something — a
  coverage_warning, or a name screen whose scope never included list_match,
  maps to ``unavailable``. Fail-closed means "unscreened", never "clear".
"""

from app.services.sanctions_rulhub import map_rulhub_result


def _base(**overrides):
    result = {
        "clear": True,
        "risk_level": "none",
        "flags": [],
        "rules_checked": 0,
        "processing_time_ms": 5,
        "domain": "sanctions",
        "hits": [],
        "screening_scope": [],
    }
    result.update(overrides)
    return result


def _hit(category="hit", action="block", score=1.0):
    return {
        "list_source": "ofac_sdn",
        "list_entry_id": "X1",
        "matched_name": "SOME LISTED PARTY",
        "matched_kind": "primary",
        "primary_name": "SOME LISTED PARTY",
        "programs": ["SDGT"],
        "score": score,
        "match_type": "exact",
        "category": category,
        "action": action,
        "caveats": ["OFAC 50% rule not resolved"],
        "programme_context": [],
    }


def test_hit_maps_to_match_with_block_action():
    mapped = map_rulhub_result(
        _base(clear=False, risk_level="critical", hits=[_hit()], screening_scope=["list_match"]),
        query="SOME LISTED PARTY", screening_type="party", expect_list_match=True,
    )
    assert mapped["status"] == "match"
    assert mapped["matches"][0]["action"] == "block"
    assert mapped["total_matches"] == 1


def test_possible_match_maps_to_potential_match():
    mapped = map_rulhub_result(
        _base(clear=False, risk_level="high",
              hits=[_hit(category="possible_match", action="review", score=0.75)],
              screening_scope=["list_match", "programme_rules"]),
        query="FOO", screening_type="party", expect_list_match=True,
    )
    assert mapped["status"] == "potential_match"
    assert mapped["matches"][0]["action"] == "review"


def test_clear_requires_list_match_scope_for_name_screens():
    mapped = map_rulhub_result(
        _base(rules_checked=12, screening_scope=["list_match", "programme_rules"],
              list_versions={"ofac_sdn": "2026-07-01"}),
        query="Honest Trading Co", screening_type="party", expect_list_match=True,
    )
    assert mapped["status"] == "clear"
    assert mapped["lists_screened"] == ["ofac_sdn"]


def test_name_screen_without_list_scope_is_unavailable_not_clear():
    mapped = map_rulhub_result(
        _base(risk_level="unknown", screening_scope=["programme_rules"]),
        query="Anyone", screening_type="party", expect_list_match=True,
    )
    assert mapped["status"] == "unavailable"


def test_coverage_warning_is_unavailable_even_when_clear():
    mapped = map_rulhub_result(
        _base(screening_scope=["list_match"], coverage_warning="lists not loaded"),
        query="Anyone", screening_type="party", expect_list_match=True,
    )
    assert mapped["status"] == "unavailable"


def test_goods_screen_with_rules_evaluated_can_be_clear():
    mapped = map_rulhub_result(
        _base(risk_level="low", rules_checked=40, screening_scope=["programme_rules"]),
        query="cotton t-shirts", screening_type="goods", expect_list_match=False,
    )
    assert mapped["status"] == "clear"


def test_goods_screen_with_zero_rules_is_unavailable():
    mapped = map_rulhub_result(
        _base(risk_level="unknown"),
        query="cotton", screening_type="goods", expect_list_match=False,
    )
    assert mapped["status"] == "unavailable"


def test_severe_programme_flag_without_hits_is_potential_match():
    mapped = map_rulhub_result(
        _base(clear=False, risk_level="high", rules_checked=40,
              screening_scope=["programme_rules"],
              flags=[{"rule_id": "SANC-IR-1", "severity": "critical",
                      "category": "sanctions_list_ofac",
                      "finding": "Destination country under comprehensive embargo"}]),
        query="machinery", screening_type="goods", expect_list_match=False,
    )
    assert mapped["status"] == "potential_match"
    assert mapped["flags"] == ["Destination country under comprehensive embargo"]


def test_sentinel_fixture_scope_counts_as_screened():
    mapped = map_rulhub_result(
        _base(risk_level="none", screening_scope=["test_fixture"]),
        query="RULHUB TEST CLEAR", screening_type="party", expect_list_match=True,
    )
    assert mapped["status"] == "clear"
