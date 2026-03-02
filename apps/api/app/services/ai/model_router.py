"""Layered model router (Phase A): configurable L1/L2/L3 routing + fallback + telemetry."""

from __future__ import annotations

import asyncio
import contextvars
import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from ...config import settings
from ..llm_provider import LLMProviderFactory

logger = logging.getLogger(__name__)

_ROUTER_TRANSPORT_CTX: contextvars.ContextVar[str] = contextvars.ContextVar(
    "router_transport", default="unknown"
)
_LAYER_CALLS_CTX: contextvars.ContextVar[List[Dict[str, Any]]] = contextvars.ContextVar(
    "layer_calls", default=[]
)


def _resolve_router_transport(provider_used: str, use_openrouter: bool) -> str:
    provider = str(provider_used or "").strip().lower()
    if use_openrouter:
        return "openrouter"
    if provider == "openai":
        return "native_openai"
    if provider == "anthropic":
        return "native_anthropic"
    if provider == "gemini":
        return "native_gemini"
    return "unknown"


def get_router_evidence() -> Dict[str, Any]:
    return {
        "router_transport": _ROUTER_TRANSPORT_CTX.get(),
        "layer_calls": list(_LAYER_CALLS_CTX.get()),
    }


def reset_router_evidence() -> None:
    _ROUTER_TRANSPORT_CTX.set("unknown")
    _LAYER_CALLS_CTX.set([])


@dataclass(frozen=True)
class LayerConfig:
    layer: str
    primary_model: str
    fallback_model: str
    confidence_threshold: float
    timeout_ms: int


@dataclass
class LayerCallResult:
    output_text: str
    tokens_in: int
    tokens_out: int
    provider_used: str
    model_used: str
    fallback_used: bool
    timeout_triggered: bool
    confidence_score: float
    confidence_band: str
    estimated_cost_usd: float
    latency_ms: float


class ModelRouter:
    """Centralized layer-aware model router with fallback triggers."""

    def __init__(self) -> None:
        self._layers: Dict[str, LayerConfig] = {
            "L1": LayerConfig(
                layer="L1",
                primary_model=settings.AI_ROUTER_L1_PRIMARY_MODEL,
                fallback_model=settings.AI_ROUTER_L1_FALLBACK_MODEL,
                confidence_threshold=settings.AI_ROUTER_L1_CONFIDENCE_THRESHOLD,
                timeout_ms=settings.AI_ROUTER_L1_TIMEOUT_MS,
            ),
            "L2": LayerConfig(
                layer="L2",
                primary_model=settings.AI_ROUTER_L2_PRIMARY_MODEL,
                fallback_model=settings.AI_ROUTER_L2_FALLBACK_MODEL,
                confidence_threshold=settings.AI_ROUTER_L2_CONFIDENCE_THRESHOLD,
                timeout_ms=settings.AI_ROUTER_L2_TIMEOUT_MS,
            ),
            "L3": LayerConfig(
                layer="L3",
                primary_model=settings.AI_ROUTER_L3_PRIMARY_MODEL,
                fallback_model=settings.AI_ROUTER_L3_FALLBACK_MODEL,
                confidence_threshold=settings.AI_ROUTER_L3_CONFIDENCE_THRESHOLD,
                timeout_ms=settings.AI_ROUTER_L3_TIMEOUT_MS,
            ),
        }

    async def call_layer(
        self,
        *,
        layer: str,
        prompt: str,
        system_prompt: Optional[str],
        max_tokens: int,
        temperature: float,
        confidence_fn: Callable[[str, int], float],
        primary_provider: Optional[str] = None,
    ) -> LayerCallResult:
        config = self._layers.get(layer.upper())
        if not config:
            raise ValueError(f"Unknown layer: {layer}")

        primary_result, primary_error, primary_timeout = await self._call_model(
            prompt=prompt,
            system_prompt=system_prompt,
            model_override=config.primary_model,
            timeout_ms=config.timeout_ms,
            max_tokens=max_tokens,
            temperature=temperature,
            primary_provider=primary_provider,
        )

        use_fallback = False
        if primary_result is None:
            use_fallback = bool(config.fallback_model)
        else:
            score = confidence_fn(primary_result[0], primary_result[2])
            if score < config.confidence_threshold and bool(config.fallback_model):
                use_fallback = True

        if use_fallback:
            fallback_result, fallback_error, fallback_timeout = await self._call_model(
                prompt=prompt,
                system_prompt=system_prompt,
                model_override=config.fallback_model,
                timeout_ms=config.timeout_ms,
                max_tokens=max_tokens,
                temperature=temperature,
                primary_provider=primary_provider,
            )
            if fallback_result is not None:
                return self._build_result(
                    config=config,
                    model_used=config.fallback_model,
                    fallback_used=True,
                    timeout_triggered=fallback_timeout,
                    result=fallback_result,
                    confidence_fn=confidence_fn,
                )

            if primary_result is None:
                err = fallback_error or primary_error or "layer call failed"
                raise RuntimeError(err)

        if primary_result is None:
            raise RuntimeError(primary_error or "layer call failed")

        return self._build_result(
            config=config,
            model_used=config.primary_model,
            fallback_used=False,
            timeout_triggered=primary_timeout,
            result=primary_result,
            confidence_fn=confidence_fn,
        )

    async def _call_model(
        self,
        *,
        prompt: str,
        system_prompt: Optional[str],
        model_override: str,
        timeout_ms: int,
        max_tokens: int,
        temperature: float,
        primary_provider: Optional[str],
    ) -> Tuple[Optional[Tuple[str, int, int, str, float]], Optional[str], bool]:
        started = time.perf_counter()
        try:
            use_openrouter = bool(settings.OPENROUTER_API_KEY)
            output, tokens_in, tokens_out, provider_used = await asyncio.wait_for(
                LLMProviderFactory.generate_with_fallback(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    primary_provider=primary_provider,
                    model_override=model_override,
                    use_openrouter=use_openrouter,
                ),
                timeout=max(timeout_ms / 1000.0, 0.1),
            )
            _ROUTER_TRANSPORT_CTX.set(_resolve_router_transport(provider_used, use_openrouter))
            latency_ms = (time.perf_counter() - started) * 1000
            return (output, tokens_in, tokens_out, provider_used, latency_ms), None, False
        except asyncio.TimeoutError:
            logger.warning("model_router_timeout", extra={"model": model_override, "timeout_ms": timeout_ms})
            return None, f"timeout for model {model_override}", True
        except Exception as exc:  # noqa: BLE001
            return None, str(exc), False

    def _build_result(
        self,
        *,
        config: LayerConfig,
        model_used: str,
        fallback_used: bool,
        timeout_triggered: bool,
        result: Tuple[str, int, int, str, float],
        confidence_fn: Callable[[str, int], float],
    ) -> LayerCallResult:
        output_text, tokens_in, tokens_out, provider_used, latency_ms = result
        confidence_score = confidence_fn(output_text, tokens_out)
        confidence_band = self._confidence_band(confidence_score)
        provider = LLMProviderFactory.create_provider(provider_used)
        estimated_cost = provider.estimate_cost(tokens_in, tokens_out)

        telemetry = {
            "event": "layer_router_call",
            "layer": config.layer,
            "primary_model": config.primary_model,
            "model_used": model_used,
            "fallback_used": fallback_used,
            "latency_ms": round(latency_ms, 2),
            "timeout_triggered": timeout_triggered,
            "confidence_score": round(confidence_score, 4),
            "confidence_band": confidence_band,
            "estimated_cost_usd": round(estimated_cost, 8),
            "provider_used": provider_used,
        }
        logger.info(json.dumps(telemetry))

        current_calls = list(_LAYER_CALLS_CTX.get())
        current_calls.append(
            {
                "layer": config.layer,
                "model_used": model_used,
                "fallback_used": bool(fallback_used),
                "provider_used": provider_used,
                "latency_ms": round(latency_ms, 2),
                "confidence_band": confidence_band,
            }
        )
        _LAYER_CALLS_CTX.set(current_calls)

        return LayerCallResult(
            output_text=output_text,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            provider_used=provider_used,
            model_used=model_used,
            fallback_used=fallback_used,
            timeout_triggered=timeout_triggered,
            confidence_score=confidence_score,
            confidence_band=confidence_band,
            estimated_cost_usd=estimated_cost,
            latency_ms=latency_ms,
        )

    @staticmethod
    def _confidence_band(score: float) -> str:
        if score >= 0.8:
            return "high"
        if score >= 0.6:
            return "medium"
        return "low"
