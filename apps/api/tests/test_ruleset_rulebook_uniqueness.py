import pytest

try:
    from sqlalchemy import and_  # noqa: F401
except Exception as exc:  # pragma: no cover - environment guard
    pytest.skip(f"SQLAlchemy unavailable: {exc}", allow_module_level=True)

from app.routers import rules_admin
from app.services.rules_service import DBRulesAdapter


def _expr_to_str(exprs) -> str:
    return str(and_(*exprs))


def test_active_ruleset_filters_include_rulebook():
    filters = rules_admin._active_ruleset_filters(
        domain="icc.ucp600",
        jurisdiction="global",
        rulebook_version="UCP600:2007",
    )
    expr = _expr_to_str(filters)
    assert "rulebook_version" in expr


def test_active_ruleset_filters_omit_rulebook_when_none():
    filters = rules_admin._active_ruleset_filters(
        domain="icc.ucp600",
        jurisdiction="global",
        rulebook_version=None,
    )
    expr = _expr_to_str(filters)
    assert "rulebook_version" not in expr


def test_rules_service_cache_key_includes_rulebook():
    adapter = DBRulesAdapter()
    cache_key = adapter._get_cache_key("icc.ucp600", "global", None, "UCP600:2007")
    assert cache_key == "icc.ucp600:global:UCP600:2007:*"


def test_rules_service_clear_cache_scoped_to_rulebook():
    adapter = DBRulesAdapter()
    key_a = adapter._get_cache_key("icc.ucp600", "global", None, "UCP600:2007")
    key_b = adapter._get_cache_key("icc.ucp600", "global", None, "eUCP2.1")

    adapter._cache[key_a] = {"ruleset": {"id": "a"}}
    adapter._cache[key_b] = {"ruleset": {"id": "b"}}
    now = __import__("datetime").datetime.now()
    adapter._cache_timestamps[key_a] = now
    adapter._cache_timestamps[key_b] = now

    adapter.clear_cache(domain="icc.ucp600", jurisdiction="global", rulebook_version="UCP600:2007")

    assert key_a not in adapter._cache
    assert key_b in adapter._cache
