import json
import logging
import re
from typing import Any, Dict, List

from app.services.llm_provider import LLMProviderFactory

logger = logging.getLogger(__name__)

_SCHEMA_EXAMPLE = """
[
  {
    "title": "Product Description Variation",
    "severity": "major",
    "documents": ["Commercial_Invoice.pdf", "Letter_of_Credit.pdf"],
    "description": "Describe the discrepancy in one sentence.",
    "expected": "The expected wording or value",
    "found": "The discovered wording or value",
    "suggested_fix": "Actionable fix the exporter can take",
    "ucp_reference": "Relevant UCP or ICC reference"
  }
]
""".strip()


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

    documents = record.get("documents") or []
    if isinstance(documents, str):
        documents = [documents]
    elif not isinstance(documents, list):
        documents = []

    severity = _coerce_str(record.get("severity")).lower()
    if severity not in {"critical", "major", "medium", "minor"}:
        severity = "minor"

    return {
        "title": _coerce_str(record.get("title")) or "Cross-document discrepancy",
        "severity": severity,
        "documents": [str(doc).strip() for doc in documents if str(doc).strip()],
        "description": _coerce_str(record.get("description")),
        "expected": _coerce_str(record.get("expected")),
        "found": _coerce_str(record.get("found")),
        "suggested_fix": _coerce_str(record.get("suggested_fix")),
        "ucp_reference": _coerce_str(record.get("ucp_reference")),
    }


async def generate_crossdoc_insights(structured_docs: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Use the LLM provider to generate cross-document discrepancies.

    Args:
        structured_docs: Dict containing lc/invoice/bl/packing/coo/insurance keys
                         plus optional "documents" list with filenames/types.
    """
    if not structured_docs:
        return []

    system_prompt = (
        "You are an LC compliance analyst. Compare Letters of Credit and supporting "
        "trade documents to spot cross-document discrepancies. Return ONLY valid JSON."
    )

    prompt = (
        "You will receive structured JSON representing an LC package. "
        "Identify up to 6 meaningful cross-document issues (product description, amounts, "
        "shipment details, ports, dates, HS codes, insurance alignment, consignee/shipper differences).\n\n"
        "Respond with a JSON array that matches the following schema:\n"
        f"{_SCHEMA_EXAMPLE}\n\n"
        "Always reference the exact filenames from the `documents` list when possible.\n"
        "If there are no discrepancies, return an empty JSON array [].\n\n"
        "Structured document payload:\n"
        f"{json.dumps(structured_docs, ensure_ascii=False, indent=2)}"
    )

    try:
        output, _, _, provider_used = await LLMProviderFactory.generate_with_fallback(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=800,
            temperature=0.1,
        )
        logger.info("AI crossdoc insights generated via %s", provider_used)
    except Exception as exc:
        logger.error("AI crossdoc generation failed: %s", exc, exc_info=True)
        return []

    parsed = _extract_json_array(output)
    if not isinstance(parsed, list):
        logger.warning("AI crossdoc output was not a list")
        return []

    insights: List[Dict[str, Any]] = []
    for record in parsed[:6]:
        if isinstance(record, dict):
            insights.append(_sanitize_issue(record))

    return insights
