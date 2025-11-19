import asyncio
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

from app.cache import ai_cache
from app.services.llm_provider import LLMProviderFactory

logger = logging.getLogger(__name__)

_SCHEMA_EXAMPLE = """
[
  {
    "title": "Product Description Variation",
    "priority": "medium",
    "documents": ["Commercial_Invoice.pdf", "LC.pdf"],
    "description": "Single sentence describing the discrepancy.",
    "expected": "The expected wording or value",
    "found": "The discovered wording or value",
    "suggested_fix": "Actionable fix the exporter can take",
    "reference": "LC Terms Compliance"
  }
]
""".strip()

_LOW_COST_MODEL = os.getenv("LLM_LOW_COST_MODEL", "gpt-4o-mini")
PRIMARY_MODEL = os.getenv("LLM_MODEL_VERSION", "gpt-4o-mini")
AI_TIMEOUT_SECONDS = 15  # Increased from 6 to handle slower API responses
RETRY_ATTEMPTS = 2
RELEVANT_KEYWORDS = (
    "goods",
    "description",
    "qty",
    "quantity",
    "origin",
    "port",
    "date",
    "hs",
    "insurance",
    "insured",
)


def _extract_json_array(raw_text: str) -> Any:
    """Attempt to unwrap JSON array from model output."""
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\[[\s\S]*\]", raw_text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return []
    return []


def _sanitize_issue(record: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure each AI issue entry contains the expected keys."""

    def _coerce_str(value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()

    def _normalize_priority(value: str) -> str:
        normalized = value.lower()
        if normalized in {"critical", "high"}:
            return "critical"
        if normalized in {"major", "medium", "warn"}:
            return "major"
        if normalized in {"minor", "low"}:
            return "minor"
        return "minor"

    documents = record.get("documents") or []
    if isinstance(documents, str):
        documents = [documents]
    elif not isinstance(documents, list):
        documents = []

    priority_value = _coerce_str(record.get("priority") or record.get("severity"))
    severity = _normalize_priority(priority_value)

    expected = _coerce_str(record.get("expected"))
    found = _coerce_str(record.get("found"))
    suggested_fix = _coerce_str(record.get("suggested_fix"))
    description = _coerce_str(record.get("description"))
    if description:
        description = " ".join(description.split())

    reference = _coerce_str(record.get("reference") or record.get("ucp_reference"))
    if reference.lower().startswith("ucp") or "article" in reference.lower():
        reference = ""
    reference = reference or "LC Terms Compliance"

    return {
        "id": _coerce_str(record.get("id")) or None,
        "title": _coerce_str(record.get("title")) or "Cross-document discrepancy",
        "severity": severity,
        "priority": severity,
        "documents": [str(doc).strip() for doc in documents if str(doc).strip()],
        "description": description,
        "expected": expected,
        "found": found,
        "suggested_fix": suggested_fix,
        "reference": reference,
        "ucp_reference": reference,
    }


def _filter_relevant_fields(data: Any, depth: int = 0) -> Any:
    """Recursively filter data to the required semantic fields."""
    if isinstance(data, dict):
        filtered: Dict[str, Any] = {}
        for key, value in data.items():
            if depth == 0 and key in {"documents", "lc", "invoice", "bl", "packing", "coo", "insurance"}:
                filtered[key] = _filter_relevant_fields(value, depth + 1)
                continue

            if _is_relevant_key(key):
                filtered_value = _filter_relevant_fields(value, depth + 1)
                if filtered_value not in (None, {}, [], ""):
                    filtered[key] = filtered_value
        return filtered

    if isinstance(data, list):
        filtered_list = []
        for value in data:
            filtered_value = _filter_relevant_fields(value, depth + 1)
            if filtered_value not in (None, {}, [], ""):
                filtered_list.append(filtered_value)
        return filtered_list

    if isinstance(data, (str, int, float)):
        return data

    return None


def _is_relevant_key(key: str) -> bool:
    lower_key = key.lower()
    return any(token in lower_key for token in RELEVANT_KEYWORDS)


def _compress_structured_docs(structured_docs: Dict[str, Any]) -> Dict[str, Any]:
    """Retain only fields required for AI reasoning to reduce token usage."""
    trimmed = _filter_relevant_fields(structured_docs)
    if not trimmed:
        return {}

    documents = trimmed.get("documents")
    if isinstance(documents, list):
        normalized_docs = []
        for doc in documents:
            if not isinstance(doc, dict):
                continue
            normalized_docs.append(
                {
                    "name": doc.get("name"),
                    "type": doc.get("type"),
                    "extracted_fields": _filter_relevant_fields(doc.get("extracted_fields", {})),
                }
            )
        trimmed["documents"] = normalized_docs

    return trimmed


def _issues_valid(issues: List[Dict[str, Any]]) -> bool:
    """Check that issues contain expected/found context."""
    if not issues:
        return False
    for issue in issues:
        if not issue.get("expected") or not issue.get("found"):
            return False
    return True


async def _invoke_llm(prompt: str, system_prompt: str, model_override: str) -> str:
    """Invoke the provider with timeout + retry."""
    last_error: Optional[Exception] = None
    delay = 0.5

    for attempt in range(RETRY_ATTEMPTS):
        try:
            coro = LLMProviderFactory.generate_with_fallback(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=800,
                temperature=0.1,
                model_override=model_override,
            )
            output, _, _, provider_used = await asyncio.wait_for(coro, timeout=AI_TIMEOUT_SECONDS)
            logger.debug("AI crossdoc insights generated via %s (model=%s)", provider_used, model_override)
            return output
        except asyncio.TimeoutError as exc:
            last_error = exc
            error_msg = f"Timeout after {AI_TIMEOUT_SECONDS}s (attempt {attempt + 1}/{RETRY_ATTEMPTS})"
            logger.warning("AI request attempt %s failed: %s", attempt + 1, error_msg)
            if attempt < RETRY_ATTEMPTS - 1:
                await asyncio.sleep(delay)
                delay *= 2
        except Exception as exc:
            last_error = exc
            error_msg = str(exc) or type(exc).__name__
            logger.warning("AI request attempt %s failed: %s", attempt + 1, error_msg, exc_info=attempt == RETRY_ATTEMPTS - 1)
            if attempt < RETRY_ATTEMPTS - 1:
                await asyncio.sleep(delay)
                delay *= 2

    error_msg = str(last_error) if last_error else "Unknown error"
    logger.error("AI generation failed after %s attempts: %s", RETRY_ATTEMPTS, error_msg, exc_info=last_error)
    raise last_error or RuntimeError("AI generation failed")


def _fallback_issue() -> List[Dict[str, Any]]:
    """Return a safe fallback issue when AI is unavailable."""
    return [
        {
            "title": "AI Analysis Unavailable",
            "severity": "minor",
            "priority": "minor",
            "documents": [],
            "description": "Automatic cross-document analysis is temporarily unavailable.",
            "expected": "",
            "found": "",
            "suggested_fix": "Retry the validation or contact support if the issue persists.",
            "reference": "LC Terms Compliance",
            "ucp_reference": "LC Terms Compliance",
        }
    ]


async def generate_crossdoc_insights(structured_docs: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Use the LLM provider to generate cross-document discrepancies.

    Args:
        structured_docs: Dict containing lc/invoice/bl/packing/coo/insurance keys
                         plus optional "documents" list with filenames/types.
    """
    if not structured_docs:
        return []

    compressed_payload = _compress_structured_docs(structured_docs)
    cache_key = ai_cache.build_cache_key(compressed_payload)
    cached = await ai_cache.get(cache_key)
    if cached:
        logger.debug("Crossdoc AI cache hit")
        return cached

    system_prompt = (
        "You are an LC compliance analyst. Compare Letters of Credit and supporting "
        "trade documents to spot cross-document discrepancies. Respond ONLY with JSON "
        "arrays of objects containing the keys: title, priority (critical/major/medium/minor), "
        "documents, description (single concise sentence), expected, found, suggested_fix, reference. "
        "Do not include paragraphs, UCP article citations, or ICC commentary in any field."
    )

    prompt = (
        "You will receive structured JSON representing an LC package. "
        "Identify up to 6 meaningful cross-document issues (product description, amounts, "
        "shipment details, ports, dates, HS codes, insurance alignment, consignee/shipper differences).\n\n"
        "Respond with a JSON array that matches the following schema exactly, ensuring descriptions are single sentences and references "
        "are short labels such as 'LC Terms Compliance':\n"
        f"{_SCHEMA_EXAMPLE}\n\n"
        "Always reference the exact filenames from the `documents` list when possible. "
        "Never mention UCP article numbers or ICC commentary. "
        "If there are no discrepancies, return an empty JSON array [].\n\n"
        "Structured document payload:\n"
        f"{json.dumps(compressed_payload, ensure_ascii=False, indent=2)}"
    )

    issues: List[Dict[str, Any]] = []
    try:
        raw_output = await _invoke_llm(prompt, system_prompt, model_override=_LOW_COST_MODEL)
        parsed = _extract_json_array(raw_output)

        if not isinstance(parsed, list):
            raise ValueError("AI output was not a JSON array")

        for record in parsed[:6]:
            if isinstance(record, dict):
                issues.append(_sanitize_issue(record))

        if not _issues_valid(issues):
            logger.info("Low-cost AI response missing required fields, escalating to primary model")
            issues = []
            raise ValueError("Low-cost model produced incomplete issues")

    except Exception as exc:
        error_msg = str(exc) or type(exc).__name__
        logger.warning("Low-cost AI tier failed: %s", error_msg, exc_info=True)
        try:
            raw_output = await _invoke_llm(prompt, system_prompt, model_override=PRIMARY_MODEL)
            parsed = _extract_json_array(raw_output)
            if isinstance(parsed, list):
                for record in parsed[:6]:
                    if isinstance(record, dict):
                        issues.append(_sanitize_issue(record))
        except Exception as fallback_exc:
            fallback_error_msg = str(fallback_exc) or type(fallback_exc).__name__
            logger.error("Primary AI tier failed: %s", fallback_error_msg, exc_info=True)
            issues = _fallback_issue()

    if not issues:
        issues = _fallback_issue()

    await ai_cache.set(cache_key, issues)
    return issues
