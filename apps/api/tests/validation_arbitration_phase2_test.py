from pathlib import Path
import sys

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

import pytest

from app.routers.validate import (
    _apply_pipeline_verification_gate,
    _arbitration_to_final_verdict,
    _build_db_rules_blocked_structured_result,
    _build_l3_findings,
    _build_trace_sections,
)
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


def test_pipeline_verification_gate_verified_case():
    payload = {
        "ai_verdict": "pass",
        "ruleset_verdict": "pass",
        "final_verdict": "SUBMIT",
        "decision_trace": {
            "router_transport": "openrouter",
            "layer_calls": [{"layer": "L1"}],
            "mode": "hybrid_enforced",
            "enforcement_applied": True,
        },
    }

    verified = _apply_pipeline_verification_gate(payload, mode="hybrid_enforced")
    assert verified["pipeline_verification_status"] == "VERIFIED"
    assert verified["pipeline_verification_fail_reasons"] == []
    assert verified["pipeline_verification_warnings"] == []
    assert isinstance(verified["pipeline_verification_checks"], list)
    for check in verified["pipeline_verification_checks"]:
        assert {"check_name", "passed", "observed_value", "required_value"}.issubset(set(check.keys()))
    assert any(
        c.get("check_name") == "enforcement_applied_for_hybrid_enforced" and c.get("passed") is True
        for c in verified["pipeline_verification_checks"]
    )


def test_pipeline_verification_gate_unverified_when_layer_calls_missing():
    payload = {
        "ai_verdict": "pass",
        "ruleset_verdict": "pass",
        "final_verdict": "SUBMIT",
        "decision_trace": {
            "router_transport": "openrouter",
            "layer_calls": [],
            "mode": "hybrid_shadow",
        },
    }

    verified = _apply_pipeline_verification_gate(payload, mode="hybrid_shadow")
    assert verified["pipeline_verification_status"] == "UNVERIFIED"
    assert any("layer_calls_present" in reason for reason in verified["pipeline_verification_fail_reasons"])
    assert len(verified["pipeline_verification_warnings"]) >= 1
    assert verified["final_verdict"] == "SUBMIT"


def test_pipeline_verification_gate_unverified_when_hybrid_enforced_not_applied():
    payload = {
        "ai_verdict": "pass",
        "ruleset_verdict": "pass",
        "final_verdict": "SUBMIT",
        "decision_trace": {
            "router_transport": "openrouter",
            "layer_calls": [{"layer": "L1"}],
            "mode": "hybrid_enforced",
            "enforcement_applied": False,
        },
    }

    verified = _apply_pipeline_verification_gate(payload, mode="hybrid_enforced")
    assert verified["pipeline_verification_status"] == "UNVERIFIED"
    assert any(
        "enforcement_applied_for_hybrid_enforced" in reason
        for reason in verified["pipeline_verification_fail_reasons"]
    )
    assert verified["final_verdict"] == "SUBMIT"


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


def test_deterministic_reject_overrides_l3_pass_in_enforced_mode():
    trace = compute_arbitration_decision(
        ai_verdict="pass",
        ruleset_verdict="reject",
        blocking_rules=[],
        extraction_confidence=0.91,
        mode="hybrid_enforced",
    )
    assert trace["arbitration_verdict"] == "reject"
    assert _arbitration_to_final_verdict(trace["arbitration_verdict"], "SUBMIT") == "REJECT"


def test_deterministic_major_holds_even_if_l3_downplays():
    trace = compute_arbitration_decision(
        ai_verdict="pass",
        ruleset_verdict="review",
        blocking_rules=[],
        extraction_confidence=0.91,
        mode="hybrid_enforced",
    )
    assert trace["arbitration_verdict"] == "review"
    assert _arbitration_to_final_verdict(trace["arbitration_verdict"], "SUBMIT") == "HOLD"


def test_l3_findings_include_evidence_refs_and_trace_ids():
    ai_metadata = {
        "llm_layer_payloads": {
            "L3": {
                "verdict": "pass",
                "confidence_score": 0.87,
                "risk_score": 12,
                "applied_rules": ["L3.R1"],
                "blocking_rules": ["L3.B1"],
                "reasoning_summary": "OK",
                "provider_used": "openai",
                "model_used": "gpt-4o",
                "fallback_used": False,
                "confidence_band": "high",
            }
        }
    }
    trace_ids = {"job_id": "job-1", "correlation_id": "corr-1"}

    findings = _build_l3_findings(ai_metadata, trace_ids=trace_ids)
    assert findings is not None
    assert findings["layer"] == "L3"
    assert findings["verdict"] == "pass"
    assert findings["trace_ids"] == trace_ids
    assert findings["evidence_refs"]["blocking_rules"] == ["L3.B1"]
    assert findings["evidence_refs"]["applied_rules"] == ["L3.R1"]


def test_trace_sections_include_deterministic_ai_l3_summaries_and_trace_ids():
    class _Session:
        id = "session-1"

    ai_metadata = {
        "llm_layer_payloads": {
            "L3": {
                "verdict": "review",
                "confidence_score": 0.72,
                "risk_score": 44,
                "applied_rules": ["L3.R2"],
                "blocking_rules": [],
                "reasoning_summary": "Mixed",
                "provider_used": "openai",
                "model_used": "gpt-4o",
                "fallback_used": False,
                "confidence_band": "medium",
            }
        }
    }

    trace_sections = _build_trace_sections(
        deterministic_counts={"critical": 1, "major": 0},
        ruleset_verdict="reject",
        issue_source_summary={
            "deterministic": {"rules_fired": ["UCP600.14"]},
            "ai": {"rules_fired": ["AI.R1"]},
        },
        ai_counts={"critical": 0, "major": 1},
        ai_metadata=ai_metadata,
        job_id="job-2",
        validation_session=_Session(),
        audit_context={"correlation_id": "corr-2"},
    )

    assert trace_sections["deterministic_summary"]["trace_ids"]["job_id"] == "job-2"
    assert trace_sections["ai_summary"]["trace_ids"]["validation_session_id"] == "session-1"
    assert trace_sections["l3_summary"]["trace_ids"]["correlation_id"] == "corr-2"
    assert trace_sections["l3_findings"]["verdict"] == "review"
