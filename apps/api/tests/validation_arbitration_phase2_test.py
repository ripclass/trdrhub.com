from pathlib import Path
import sys

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

import pytest

from app.routers.validate import _arbitration_to_final_verdict, _build_db_rules_blocked_structured_result
from app.services.validation.arbitration import compute_arbitration_decision, compute_shadow_arbitration
from app.services.ai.model_router import ModelRouter, reset_router_evidence
from app.services import llm_provider


def test_phase2_shadow_arbitration_policy_outcomes():
    reject = compute_shadow_arbitration(
        ai_verdict="pass",
        ruleset_verdict="pass",
        blocking_rules=["UCP600.14"],
        extraction_confidence=0.95,
    )
    assert reject["arbitration_verdict"] == "reject"

    review = compute_shadow_arbitration(
        ai_verdict="reject",
        ruleset_verdict="pass",
        blocking_rules=[],
        extraction_confidence=0.92,
    )
    assert review["arbitration_verdict"] == "review"

    passed = compute_shadow_arbitration(
        ai_verdict="pass",
        ruleset_verdict="pass",
        blocking_rules=[],
        extraction_confidence=0.92,
    )
    assert passed["arbitration_verdict"] == "pass"

    low_conf = compute_shadow_arbitration(
        ai_verdict="pass",
        ruleset_verdict="pass",
        blocking_rules=[],
        extraction_confidence=0.2,
    )
    assert low_conf["arbitration_verdict"] == "review"


def test_phase2_shadow_wiring_present_in_blocked_payload():
    payload = _build_db_rules_blocked_structured_result(
        reason="rules offline",
        processing_duration=0.42,
        documents=[],
    )
    assert "decision_trace" in payload
    assert payload["decision_trace"] is None or isinstance(payload["decision_trace"], dict)
    if isinstance(payload["decision_trace"], dict):
        assert payload["decision_trace"].get("router_transport") in {
            "openrouter",
            "native_openai",
            "native_anthropic",
            "native_gemini",
            "unknown",
        }
        assert isinstance(payload["decision_trace"].get("layer_calls"), list)


def test_phase2_enforced_arbitration_policy_and_mapping():
    trace = compute_arbitration_decision(
        ai_verdict="pass",
        ruleset_verdict="pass",
        blocking_rules=[],
        extraction_confidence=0.95,
        mode="hybrid_enforced",
    )
    assert trace["enforced"] is True
    assert trace["enforcement_applied"] is True
    assert trace["arbitration_verdict"] == "pass"
    assert _arbitration_to_final_verdict(trace["arbitration_verdict"], "CAUTION") == "SUBMIT"

    trace = compute_arbitration_decision(
        ai_verdict="pass",
        ruleset_verdict="pass",
        blocking_rules=["UCP600.14"],
        extraction_confidence=0.95,
        mode="hybrid_enforced",
    )
    assert trace["arbitration_verdict"] == "reject"
    assert _arbitration_to_final_verdict(trace["arbitration_verdict"], "SUBMIT") == "REJECT"

    trace = compute_arbitration_decision(
        ai_verdict="reject",
        ruleset_verdict="pass",
        blocking_rules=[],
        extraction_confidence=0.95,
        mode="hybrid_enforced",
    )
    assert trace["arbitration_verdict"] == "review"
    assert _arbitration_to_final_verdict(trace["arbitration_verdict"], "SUBMIT") == "HOLD"


@pytest.mark.asyncio
async def test_phase2_decision_trace_includes_runtime_router_evidence_when_routing_used(monkeypatch):
    async def fake_generate_with_fallback(**kwargs):
        return "strong output", 10, 20, "openai"

    class _CostProvider:
        def estimate_cost(self, tokens_in: int, tokens_out: int) -> float:
            return 0.0

    monkeypatch.setattr(llm_provider.LLMProviderFactory, "generate_with_fallback", fake_generate_with_fallback)
    monkeypatch.setattr(llm_provider.LLMProviderFactory, "create_provider", lambda _: _CostProvider())

    reset_router_evidence()
    router = ModelRouter()
    await router.call_layer(
        layer="L1",
        prompt="p",
        system_prompt="s",
        max_tokens=100,
        temperature=0.1,
        confidence_fn=lambda _out, _t: 0.9,
    )

    payload = _build_db_rules_blocked_structured_result(
        reason="rules offline",
        processing_duration=0.42,
        documents=[],
    )
    trace = payload["decision_trace"]

    assert isinstance(trace, dict)
    assert trace.get("router_transport") in {
        "openrouter",
        "native_openai",
        "native_anthropic",
        "native_gemini",
        "unknown",
    }
    assert isinstance(trace.get("layer_calls"), list)
    assert len(trace["layer_calls"]) >= 1

    call = trace["layer_calls"][0]
    assert call.get("layer") in {"L1", "L2", "L3"}
    assert isinstance(call.get("model_used"), str)
    assert isinstance(call.get("fallback_used"), bool)
    assert isinstance(call.get("provider_used"), str)
    assert isinstance(call.get("latency_ms"), (int, float))
    assert call.get("confidence_band") in {"low", "medium", "high"}
