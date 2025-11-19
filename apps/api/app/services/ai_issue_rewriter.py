import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

from app.services.llm_provider import LLMProviderFactory

logger = logging.getLogger(__name__)

_FALSEY = {"0", "false", "off", "no"}


def _env_truthy(value: Optional[str], *, default: bool = True) -> bool:
    if value is None:
        return default
    return value.strip().lower() not in _FALSEY


def _llm_credentials_present() -> bool:
    return bool(
        os.getenv("OPENAI_API_KEY")
        or os.getenv("ANTHROPIC_API_KEY")
        or os.getenv("LLM_PROVIDER_API_KEY")
    )


# Enabled by default; explicit opt-out (env=false) or missing credentials disables rewriting.
REWRITER_ENABLED = _env_truthy(os.getenv("AI_ISSUE_REWRITER_ENABLED"), default=True) and _llm_credentials_present()
MODEL_OVERRIDE = os.getenv("AI_ISSUE_REWRITER_MODEL", "gpt-4o-mini")
SYSTEM_PROMPT = (
    "You rewrite deterministic LC discrepancy findings into concise SME-friendly cards. "
    "Respond ONLY with JSON containing the keys: "
    "title, priority (critical/major/medium/minor), documents (array of filenames), "
    "description (max 2 sentences), expected, found, suggested_fix. "
    "Do not include UCP commentary, citations, or additional prose."
)


async def rewrite_issue(rule_issue: Dict[str, Any], extracted_docs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Rewrite a deterministic rule issue into a concise SME-friendly issue card.
    Falls back to deterministic formatting when the LLM is disabled or fails.
    """
    fallback = _fallback_issue(rule_issue)
    if not REWRITER_ENABLED:
        return fallback

    prompt_payload = {
        "issue": _serialize_issue(rule_issue),
        "context": _build_context_snapshot(extracted_docs),
    }

    try:
        output, _, _, provider_used = await LLMProviderFactory.generate_with_fallback(
            prompt=json.dumps(prompt_payload, ensure_ascii=False, indent=2),
            system_prompt=SYSTEM_PROMPT,
            max_tokens=400,
            temperature=0.1,
            model_override=MODEL_OVERRIDE,
        )
        parsed = json.loads(output)
        rewrite_payload = _coerce_rewrite(parsed)
        if rewrite_payload:
            rewrite_payload["source"] = provider_used
            return rewrite_payload
    except Exception as exc:
        logger.warning("AI issue rewriting failed: %s", exc)

    return fallback


def _serialize_issue(rule_issue: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "rule": rule_issue.get("rule") or rule_issue.get("rule_id"),
        "title": rule_issue.get("title"),
        "severity": rule_issue.get("severity"),
        "message": rule_issue.get("message") or rule_issue.get("description"),
        "expected": rule_issue.get("expected") or rule_issue.get("expected_value"),
        "actual": rule_issue.get("actual") or rule_issue.get("found"),
        "documents": rule_issue.get("documents") or rule_issue.get("document_names"),
        "suggested_fix": rule_issue.get("suggested_fix") or rule_issue.get("suggestion"),
    }


def _build_context_snapshot(extracted_docs: Dict[str, Any]) -> Dict[str, Any]:
    lc = extracted_docs.get("lc") or {}
    invoice = extracted_docs.get("invoice") or {}
    bill_of_lading = extracted_docs.get("bill_of_lading") or extracted_docs.get("billOfLading") or {}

    context = {
        "lc": {
            "goods_description": lc.get("goods_description"),
            "goods_items": lc.get("goods_items"),
            "incoterm": lc.get("incoterm"),
            "ports": lc.get("ports"),
            "dates": lc.get("dates"),
            "applicant": lc.get("applicant"),
            "beneficiary": lc.get("beneficiary"),
        },
        "invoice": {
            "goods_description": invoice.get("goods_description") or invoice.get("product_description"),
            "amount": invoice.get("invoice_amount"),
            "hs_code": invoice.get("hs_code"),
        },
        "bill_of_lading": {
            "shipper": bill_of_lading.get("shipper"),
            "consignee": bill_of_lading.get("consignee"),
            "ports": {
                "loading": bill_of_lading.get("port_of_loading"),
                "discharge": bill_of_lading.get("port_of_discharge"),
            },
        },
        "lc_type": extracted_docs.get("lc_type"),
        "documents": extracted_docs.get("documents"),
    }

    try:
        return json.loads(json.dumps(context, ensure_ascii=False))
    except TypeError:
        return context


def _coerce_rewrite(payload: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(payload, dict):
        return None

    title = _coerce_text(payload.get("title")) or "Review Required"
    priority = (_coerce_text(payload.get("priority")) or "major").lower()
    documents = payload.get("documents") or []
    if isinstance(documents, str):
        documents = [documents]
    elif not isinstance(documents, list):
        documents = []
    documents = [str(doc).strip() for doc in documents if str(doc).strip()]

    description = _truncate_sentences(_coerce_text(payload.get("description") or "Review the discrepancy details."))
    expected = _coerce_text(payload.get("expected")) or "—"
    found = _coerce_text(payload.get("found")) or "—"
    suggested_fix = _coerce_text(payload.get("suggested_fix")) or "Ensure invoice description corresponds to LC terms."

    return {
        "title": title,
        "priority": priority,
        "documents": documents,
        "description": description,
        "expected": expected,
        "found": found,
        "suggested_fix": suggested_fix,
    }


def _fallback_issue(rule_issue: Dict[str, Any]) -> Dict[str, Any]:
    documents = rule_issue.get("documents") or rule_issue.get("document_names") or []
    if isinstance(documents, str):
        documents = [documents]
    elif not isinstance(documents, list):
        documents = []
    documents = [str(doc).strip() for doc in documents if str(doc).strip()]

    description = rule_issue.get("message") or rule_issue.get("description") or rule_issue.get("title") or ""
    description = _truncate_sentences(_coerce_text(description) or "Review the discrepancy details.")

    expected = _coerce_text(rule_issue.get("expected") or rule_issue.get("expected_value")) or "—"
    actual_value = (
        rule_issue.get("found")
        or rule_issue.get("actual")
        or rule_issue.get("actual_value")
        or rule_issue.get("value_found")
    )
    found = _coerce_text(actual_value) or "—"

    suggested_fix = (
        _coerce_text(rule_issue.get("suggested_fix") or rule_issue.get("suggestion"))
        or "Ensure invoice description corresponds to LC terms."
    )

    severity = (rule_issue.get("priority") or rule_issue.get("severity") or "major").lower()

    return {
        "title": _coerce_text(rule_issue.get("title")) or "Review Required",
        "priority": severity,
        "documents": documents,
        "description": description,
        "expected": expected,
        "found": found,
        "suggested_fix": suggested_fix,
    }


def _truncate_sentences(text: str, max_sentences: int = 2) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    truncated = " ".join(sentence.strip() for sentence in sentences[:max_sentences] if sentence.strip())
    return truncated or text


def _coerce_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        return value.strip()
    try:
        return str(value).strip()
    except Exception:
        return None

