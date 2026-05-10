"""Tests for the public, no-auth LC checker (POST /api/check).

Covers two units without spinning up the full app / DB / pipeline:

  * ``app.utils.anon_rate_limit`` — the Redis-backed 1/IP/24h limiter that is
    the cost control on a public endpoint that runs Sonnet/Opus. Exercised
    against a tiny in-memory fake Redis.
  * The response-trimming helpers in ``app.routers.public_check`` — that the
    public payload is exactly ``{verdict, verdict_label, verdict_color,
    finding_count, top_findings (<=2, severity-sorted), signup_cta}`` and never
    leaks the full structured result / finding list.

The trimming helpers are loaded via AST extraction (the same trick
``public_validation_envelope_test.py`` uses) so the test doesn't drag in the
whole ``app.routers.validate`` import chain.
"""

from __future__ import annotations

import ast
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_CHECK_PATH = ROOT / "app" / "routers" / "public_check.py"


# --------------------------------------------------------------------------
# Fake async Redis
# --------------------------------------------------------------------------
class _FakeAsyncRedis:
    def __init__(self) -> None:
        self.store: Dict[str, int] = {}
        self.ttls: Dict[str, int] = {}

    async def incr(self, key: str) -> int:
        self.store[key] = int(self.store.get(key, 0)) + 1
        return self.store[key]

    async def decr(self, key: str) -> int:
        self.store[key] = int(self.store.get(key, 0)) - 1
        return self.store[key]

    async def expire(self, key: str, seconds: int) -> bool:
        self.ttls[key] = int(seconds)
        return True

    async def ttl(self, key: str) -> int:
        if key not in self.store:
            return -2
        return self.ttls.get(key, -1)

    async def get(self, key: str) -> Optional[str]:
        if key not in self.store:
            return None
        return str(self.store[key])

    async def ping(self) -> bool:
        return True


class _FakeRequest:
    def __init__(self, ip: str = "203.0.113.7", headers: Optional[Dict[str, str]] = None) -> None:
        self.headers = headers or {}
        self.client = type("C", (), {"host": ip})()


# --------------------------------------------------------------------------
# anon_rate_limit
# --------------------------------------------------------------------------
@pytest.fixture()
def fake_redis(monkeypatch):
    import app.utils.anon_rate_limit as arl

    fake = _FakeAsyncRedis()

    async def _get_redis():
        return fake

    monkeypatch.setattr(arl, "get_redis", _get_redis)
    return fake


def test_reserve_then_second_call_is_limited(fake_redis):
    import app.utils.anon_rate_limit as arl

    req = _FakeRequest("198.51.100.4")

    first = asyncio.run(arl.reserve_anon_run(request=req, scope="lc_check", window_seconds=86400, limit=1))
    assert first is None  # allowed

    second = asyncio.run(arl.reserve_anon_run(request=req, scope="lc_check", window_seconds=86400, limit=1))
    assert isinstance(second, int) and second > 0  # limited, seconds-until-reset


def test_different_ips_are_independent(fake_redis):
    import app.utils.anon_rate_limit as arl

    a = _FakeRequest("198.51.100.10")
    b = _FakeRequest("198.51.100.11")

    assert asyncio.run(arl.reserve_anon_run(request=a, scope="lc_check", limit=1)) is None
    assert asyncio.run(arl.reserve_anon_run(request=b, scope="lc_check", limit=1)) is None
    # ...but each is now used up
    assert isinstance(asyncio.run(arl.reserve_anon_run(request=a, scope="lc_check", limit=1)), int)


def test_release_refunds_the_reservation(fake_redis):
    import app.utils.anon_rate_limit as arl

    req = _FakeRequest("198.51.100.20")
    assert asyncio.run(arl.reserve_anon_run(request=req, scope="lc_check", limit=1)) is None
    asyncio.run(arl.release_anon_run(request=req, scope="lc_check"))
    # refunded — a fresh run is allowed again
    assert asyncio.run(arl.reserve_anon_run(request=req, scope="lc_check", limit=1)) is None


def test_peek_does_not_consume(fake_redis):
    import app.utils.anon_rate_limit as arl

    req = _FakeRequest("198.51.100.30")
    assert asyncio.run(arl.peek_anon_run(request=req, scope="lc_check", limit=1)) is None
    # still allowed afterwards
    assert asyncio.run(arl.reserve_anon_run(request=req, scope="lc_check", limit=1)) is None
    # now peek reports it's used
    assert isinstance(asyncio.run(arl.peek_anon_run(request=req, scope="lc_check", limit=1)), int)


def test_unconfigured_redis_fails_open(monkeypatch):
    import app.utils.anon_rate_limit as arl

    async def _no_redis():
        return None

    monkeypatch.setattr(arl, "get_redis", _no_redis)
    req = _FakeRequest("198.51.100.40")
    # No Redis configured (local/stub dev) — never block.
    assert asyncio.run(arl.reserve_anon_run(request=req, scope="lc_check", limit=1)) is None
    assert asyncio.run(arl.reserve_anon_run(request=req, scope="lc_check", limit=1)) is None


def test_client_ip_prefers_forwarded_for(fake_redis):
    import app.utils.anon_rate_limit as arl

    req = _FakeRequest("10.0.0.1", headers={"X-Forwarded-For": "203.0.113.99, 10.0.0.1"})
    assert arl.client_ip(req) == "203.0.113.99"
    req2 = _FakeRequest("10.0.0.2", headers={"X-Real-IP": "203.0.113.50"})
    assert arl.client_ip(req2) == "203.0.113.50"
    req3 = _FakeRequest("203.0.113.7")
    assert arl.client_ip(req3) == "203.0.113.7"


# --------------------------------------------------------------------------
# public_check trimming helpers (AST-loaded — no heavy app import)
# --------------------------------------------------------------------------
def _load_public_check_symbols() -> Dict[str, Any]:
    source = PUBLIC_CHECK_PATH.read_text(encoding="utf-8")
    parsed = ast.parse(source)
    wanted_funcs = {
        "_issue_title",
        "_issue_severity",
        "_extract_verdict",
        "_finding_count",
        "_trim_result",
    }
    wanted_assigns = {"_SEVERITY_RANK", "_MAX_TOP_FINDINGS"}
    selected: List[ast.stmt] = []
    for node in parsed.body:
        if isinstance(node, ast.FunctionDef) and node.name in wanted_funcs:
            selected.append(node)
        elif isinstance(node, ast.Assign):
            names = {t.id for t in node.targets if isinstance(t, ast.Name)}
            if names & wanted_assigns:
                selected.append(node)
    module_ast = ast.Module(body=selected, type_ignores=[])
    ast.fix_missing_locations(module_ast)
    namespace: Dict[str, Any] = {"Any": Any, "Dict": Dict, "List": List, "Optional": Optional}
    exec(compile(module_ast, str(PUBLIC_CHECK_PATH), "exec"), namespace)
    return namespace


PC = _load_public_check_symbols()


def test_trim_result_shape_and_severity_sort():
    envelope = {
        "structured_result": {
            "issues": [
                {"title": "Minor wording nit", "severity": "minor"},
                {"title": "Invoice arithmetic off by USD 61,700", "severity": "critical"},
                {"title": "BL not marked CLEAN ON BOARD", "severity": "major"},
            ],
            "bank_verdict": {
                "verdict": "REJECT",
                "verdict_color": "red",
                "verdict_message": "Documents will be rejected",
                "issue_summary": {"total": 3, "critical": 1, "major": 1, "minor": 1},
            },
        },
        "bank_verdict": {"verdict": "REJECT", "verdict_color": "red", "verdict_message": "Documents will be rejected", "issue_summary": {"total": 3}},
        "final_verdict": "FAIL",
    }
    out = PC["_trim_result"](envelope)

    assert set(out.keys()) == {"verdict", "verdict_label", "verdict_color", "finding_count", "top_findings", "signup_cta"}
    assert out["verdict"] == "REJECT"
    assert out["verdict_color"] == "red"
    assert out["verdict_label"] == "Documents will be rejected"
    assert out["finding_count"] == 3
    assert out["signup_cta"] is True
    # top 2, severity-sorted (critical, then major) — minor dropped
    assert len(out["top_findings"]) == 2
    assert out["top_findings"][0] == {"title": "Invoice arithmetic off by USD 61,700", "severity": "critical"}
    assert out["top_findings"][1] == {"title": "BL not marked CLEAN ON BOARD", "severity": "major"}
    # never leaks the full structured result
    assert "structured_result" not in out


def test_trim_result_clean_presentation():
    out = PC["_trim_result"]({"structured_result": {"issues": []}, "final_verdict": "PASS"})
    assert out["verdict"] == "PASS"
    assert out["finding_count"] == 0
    assert out["top_findings"] == []
    assert out["signup_cta"] is True


def test_trim_result_falls_back_to_review_when_no_verdict():
    out = PC["_trim_result"]({})
    assert out["verdict"] == "REVIEW"
    assert out["finding_count"] == 0
    assert out["top_findings"] == []


def test_trim_result_uses_provisional_when_final_issues_empty():
    envelope = {
        "structured_result": {"issues": [], "_provisional_issues": [{"title": "Held finding", "severity": "major"}]},
        "final_verdict": "REVIEW_REQUIRED",
    }
    out = PC["_trim_result"](envelope)
    assert out["finding_count"] == 1
    assert out["top_findings"] == [{"title": "Held finding", "severity": "major"}]


def test_extract_verdict_prefers_bank_verdict_over_final_verdict():
    out = PC["_extract_verdict"](
        {"bank_verdict": {"verdict": "caution", "verdict_color": "Yellow", "verdict_message": "Minor fixes"}},
        {"final_verdict": "PASS"},
    )
    assert out == {"verdict": "CAUTION", "verdict_label": "Minor fixes", "verdict_color": "yellow"}


def test_issue_helpers_tolerate_objects_and_missing_fields():
    class _Issue:
        title = "Object-style finding"
        severity = "Major"

    assert PC["_issue_title"](_Issue()) == "Object-style finding"
    assert PC["_issue_severity"](_Issue()) == "major"
    assert PC["_issue_title"]({}) == "Discrepancy"
    assert PC["_issue_severity"]({}) == "minor"
    assert PC["_issue_title"]({"message": "from message key"}) == "from message key"
