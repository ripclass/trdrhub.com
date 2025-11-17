import asyncio
import json
import logging
import re
import time
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ValidationError, Field

from app.config import settings
from app.services.llm_provider import LLMProviderFactory

logger = logging.getLogger(__name__)

_CACHE_TTL_SECONDS = 7 * 24 * 60 * 60
_cache: Dict[str, Dict[str, Any]] = {}
_cache_lock = asyncio.Lock()


class SemanticComparison(BaseModel):
    match: bool = Field(description="True when the texts are materially equivalent")
    confidence: float = Field(ge=0.0, le=1.0)
    materiality: str = "unknown"
    expected: str = ""
    found: str = ""
    suggested_fix: Optional[str] = None
    reason: Optional[str] = None
    documents: List[str] = Field(default_factory=list)
    source: str = "fallback"
    raw_score: float = 0.0


def _normalize_text(value: Optional[str]) -> str:
    if not value:
        return ""
    text = value.lower()
    text = re.sub(r"\s+", " ", text)
    replacements = {
        "knitted": "knit",
        "garments": "garment",
        "pcs": "pieces",
    }
    for target, replacement in replacements.items():
        text = text.replace(target, replacement)
    text = text.strip()
    return text


def _build_cache_key(left: str, right: str, context: str, threshold: float) -> str:
    payload = json.dumps(
        {"l": left, "r": right, "ctx": context, "th": round(threshold, 3)},
        sort_keys=True,
        ensure_ascii=False,
    )
    return str(hash(payload))


async def _set_cache(key: str, value: Dict[str, Any]) -> None:
    async with _cache_lock:
        _cache[key] = {"ts": time.time(), "value": json.loads(json.dumps(value))}


async def _get_cache(key: str) -> Optional[Dict[str, Any]]:
    async with _cache_lock:
        entry = _cache.get(key)
        if not entry:
            return None
        if time.time() - entry["ts"] > _CACHE_TTL_SECONDS:
            _cache.pop(key, None)
            return None
        return json.loads(json.dumps(entry["value"]))


def _fallback_similarity(
    left_normalized: str,
    right_normalized: str,
    *,
    threshold: float,
    original_left: str,
    original_right: str,
    documents: List[str],
    reason: Optional[str] = None,
) -> SemanticComparison:
    if not left_normalized or not right_normalized:
        return SemanticComparison(
            match=True,
            confidence=1.0,
            materiality="unknown",
            expected=original_left,
            found=original_right,
            suggested_fix=None,
            reason=reason or "Insufficient data for semantic comparison.",
            documents=documents,
            source="fallback",
            raw_score=1.0,
        )

    ratio = SequenceMatcher(None, left_normalized, right_normalized).ratio()
    match = ratio >= threshold
    materiality = "none"
    if ratio < threshold:
        materiality = "major" if ratio < (threshold - 0.2) else "minor"
    elif ratio < 0.95:
        materiality = "minor"

    return SemanticComparison(
        match=match,
        confidence=round(ratio, 3),
        materiality=materiality,
        expected=original_left,
        found=original_right,
        suggested_fix=None if match else "Align the descriptions to match the LC wording.",
        reason=reason,
        documents=documents,
        source="fallback",
        raw_score=ratio,
    )


async def _invoke_llm(prompt: str, system_prompt: str, *, model_override: Optional[str]) -> SemanticComparison:
    timeout = settings.AI_SEMANTIC_TIMEOUT_MS / 1000
    try:
        result = await asyncio.wait_for(
            LLMProviderFactory.generate_with_fallback(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=400,
                temperature=0.1,
                model_override=model_override,
            ),
            timeout=timeout,
        )
    except Exception as exc:
        raise RuntimeError(f"Semantic LLM call failed: {exc}") from exc

    output, _, _, provider_used = result
    try:
        parsed = json.loads(output)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Semantic LLM response was not valid JSON: {exc}") from exc

    try:
        comparison = SemanticComparison(
            **parsed,
            source=f"llm:{provider_used}",
        )
        return comparison
    except ValidationError as exc:
        raise RuntimeError(f"Semantic LLM response missing required fields: {exc}") from exc


async def run_semantic_comparison(
    left_value: Optional[str],
    right_value: Optional[str],
    *,
    context: str,
    documents: Optional[List[str]] = None,
    threshold: Optional[float] = None,
    enable_ai: Optional[bool] = None,
) -> Dict[str, Any]:
    documents = documents or []
    threshold = threshold or settings.AI_SEMANTIC_THRESHOLD_DEFAULT
    enable_ai = settings.AI_SEMANTIC_ENABLED if enable_ai is None else enable_ai

    original_left = left_value or ""
    original_right = right_value or ""

    left_normalized = _normalize_text(left_value)
    right_normalized = _normalize_text(right_value)

    cache_key = _build_cache_key(left_normalized, right_normalized, context, threshold)
    cached = await _get_cache(cache_key)
    if cached:
        return cached

    comparison: SemanticComparison
    if enable_ai and left_normalized and right_normalized:
        try:
            system_prompt = (
                "You are an LC compliance assistant. Compare two extracted strings from trade documents. "
                "Return ONLY JSON with keys: match (bool), confidence (0-1 float), materiality (none/minor/major), "
                "expected, found, suggested_fix, reason, documents (array of strings)."
            )
            prompt = json.dumps(
                {
                    "context": context,
                    "lc_value": original_left,
                    "comparison_value": original_right,
                    "threshold": threshold,
                    "documents": documents,
                },
                ensure_ascii=False,
                indent=2,
            )
            comparison = await _invoke_llm(
                prompt,
                system_prompt,
                model_override=settings.AI_SEMANTIC_MODEL,
            )
            if comparison.confidence < 0 or comparison.confidence > 1:
                raise RuntimeError("Confidence out of bounds")
        except Exception as exc:
            logger.warning("Semantic LLM failed (%s); falling back to fuzzy comparison", exc)
            comparison = _fallback_similarity(
                left_normalized,
                right_normalized,
                threshold=threshold,
                original_left=original_left,
                original_right=original_right,
                documents=documents,
                reason=str(exc),
            )
    else:
        comparison = _fallback_similarity(
            left_normalized,
            right_normalized,
            threshold=threshold,
            original_left=original_left,
            original_right=original_right,
            documents=documents,
            reason="AI semantic comparisons disabled or insufficient input.",
        )

    await _set_cache(cache_key, comparison.model_dump())
    return comparison.model_dump()

