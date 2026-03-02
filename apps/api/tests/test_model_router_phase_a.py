import pytest

from app.config import Settings
from app.services.ai.model_router import ModelRouter
from app.services import llm_provider


class _CostProvider:
    def estimate_cost(self, tokens_in: int, tokens_out: int) -> float:
        return (tokens_in + tokens_out) / 1_000_000


@pytest.mark.asyncio
async def test_layer_router_fallback_on_low_confidence(monkeypatch):
    monkeypatch.setattr("app.config.settings.AI_ROUTER_L1_PRIMARY_MODEL", "model-primary")
    monkeypatch.setattr("app.config.settings.AI_ROUTER_L1_FALLBACK_MODEL", "model-fallback")
    monkeypatch.setattr("app.config.settings.AI_ROUTER_L1_CONFIDENCE_THRESHOLD", 0.9)
    monkeypatch.setattr("app.config.settings.AI_ROUTER_L1_TIMEOUT_MS", 5000)

    calls = []

    async def fake_generate_with_fallback(**kwargs):
        calls.append(kwargs["model_override"])
        if kwargs["model_override"] == "model-primary":
            return "tiny", 5, 3, "openai"
        return "this is a confident fallback output with enough tokens", 20, 30, "openai"

    monkeypatch.setattr(llm_provider.LLMProviderFactory, "generate_with_fallback", fake_generate_with_fallback)
    monkeypatch.setattr(llm_provider.LLMProviderFactory, "create_provider", lambda _: _CostProvider())

    router = ModelRouter()
    result = await router.call_layer(
        layer="L1",
        prompt="p",
        system_prompt="s",
        max_tokens=100,
        temperature=0.1,
        confidence_fn=lambda out, t: 0.2 if out == "tiny" else 0.95,
    )

    assert result.fallback_used is True
    assert result.model_used == "model-fallback"
    assert calls == ["model-primary", "model-fallback"]


def test_router_settings_defaults_load():
    cfg = Settings()
    assert cfg.OPENROUTER_BASE_URL
    assert cfg.AI_ROUTER_L1_PRIMARY_MODEL
    assert cfg.AI_ROUTER_L2_PRIMARY_MODEL
    assert cfg.AI_ROUTER_L3_PRIMARY_MODEL
    assert cfg.AI_ROUTER_L1_TIMEOUT_MS > 0
