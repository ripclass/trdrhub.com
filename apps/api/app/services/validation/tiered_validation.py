"""Three-pass validation orchestrator: tiered AI → deterministic → Opus veto.

This module implements the validation architecture Imran designed:

  Pass A — Tiered AI validation
      L1 (default GPT-4.1) reads the documents and produces preliminary
      findings with confidence scores. If L1 hits low confidence or
      explicitly asks for help, the call escalates to L2 (Sonnet 4.6) and
      then L3 (Opus 4.6). Each finding carries the layer that produced it.

  Pass B — Deterministic rules
      The existing UCP600/ISBP745/crossdoc rule evaluator runs unchanged
      via app.services.validator.validate_document_async. Each finding is
      tagged with source = "deterministic".

  Pass C — Opus veto
      A single Claude Opus 4.6 call reviews the documents plus the
      combined finding set from Passes A + B. Opus can confirm, drop, or
      modify any finding, and can ADD new findings (TBML signals, fraud
      patterns, structural anomalies that the rules and AI missed). Its
      decision is final.

Each pass is failure-isolated: if any pass times out or errors, the
others still produce their results and the function returns the best
information it has. The orchestrator never raises — it always returns
SOMETHING the upstream pipeline can use.

Feature flags (in app.config.settings):
- VALIDATION_TIERED_AI_ENABLED  — turns on Pass A (default off)
- VALIDATION_OPUS_VETO_ENABLED  — turns on Pass C (default off)

When both flags are off, the orchestrator delegates to
validate_document_async and behaves identically to the legacy pipeline.
This is the safe default.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from app.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public orchestrator
# ---------------------------------------------------------------------------


async def validate_document_with_pipeline(
    document_data: Dict[str, Any],
    document_type: str,
) -> List[Dict[str, Any]]:
    """Run the three-pass validation pipeline and return the merged findings.

    The return shape matches the legacy ``validate_document_async``: a flat
    list of finding dicts. Each finding now carries metadata about which
    layer raised it (``_source_layer``), whether the Opus veto modified it
    (``_vetoed``), and any veto reason (``_veto_reason``).

    When tiered AI is disabled, this function delegates straight to the
    legacy ``validate_document_async`` and returns its output as-is.
    """
    from app.services.validator import validate_document_async

    tiered_enabled = bool(getattr(settings, "VALIDATION_TIERED_AI_ENABLED", False))
    veto_enabled = bool(getattr(settings, "VALIDATION_OPUS_VETO_ENABLED", False))

    if not tiered_enabled and not veto_enabled:
        # Legacy path: deterministic-only.
        return await validate_document_async(document_data, document_type)

    # Pass A — tiered AI validation (failure isolated)
    ai_findings: List[Dict[str, Any]] = []
    if tiered_enabled:
        try:
            ai_findings = await asyncio.wait_for(
                _run_tiered_ai_validation_pass(document_data, document_type),
                timeout=float(getattr(settings, "VALIDATION_AI_PASS_TIMEOUT_SECONDS", 60)),
            )
        except asyncio.TimeoutError:
            logger.warning(
                "Tiered AI validation pass timed out after %ss for document_type=%s",
                getattr(settings, "VALIDATION_AI_PASS_TIMEOUT_SECONDS", 60),
                document_type,
            )
        except Exception as exc:  # noqa: BLE001 — pass must never crash
            logger.warning(
                "Tiered AI validation pass failed for document_type=%s: %s",
                document_type,
                exc,
                exc_info=True,
            )

    # Pass B — deterministic rules (existing pipeline)
    deterministic_findings: List[Dict[str, Any]] = []
    try:
        deterministic_findings = await validate_document_async(document_data, document_type)
        for finding in deterministic_findings:
            finding.setdefault("_source_layer", "deterministic")
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "Deterministic rules pass failed for document_type=%s: %s",
            document_type,
            exc,
            exc_info=True,
        )

    # Pass C — Opus veto (failure isolated)
    if veto_enabled and (ai_findings or deterministic_findings):
        try:
            final_findings = await asyncio.wait_for(
                _run_opus_veto_pass(
                    document_data=document_data,
                    document_type=document_type,
                    ai_findings=ai_findings,
                    deterministic_findings=deterministic_findings,
                ),
                timeout=float(getattr(settings, "VALIDATION_VETO_TIMEOUT_SECONDS", 90)),
            )
            return final_findings
        except asyncio.TimeoutError:
            logger.warning(
                "Opus veto pass timed out after %ss for document_type=%s",
                getattr(settings, "VALIDATION_VETO_TIMEOUT_SECONDS", 90),
                document_type,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Opus veto pass failed for document_type=%s: %s",
                document_type,
                exc,
                exc_info=True,
            )

    # Veto disabled or failed — return AI + deterministic findings combined.
    return [*ai_findings, *deterministic_findings]


# ---------------------------------------------------------------------------
# Pass A — Tiered AI validation
# ---------------------------------------------------------------------------


_AI_VALIDATION_SYSTEM_PROMPT = (
    "You are a senior trade-finance bank examiner. You review extracted data "
    "from Letter of Credit document sets and identify compliance issues "
    "BEFORE the bank examines them. You speak in plain English and only flag "
    "issues you are confident about.\n\n"
    "IMPORTANT CONTEXT:\n"
    "- Each document was extracted independently by a blind OCR transcriber.\n"
    "- The extractor does NOT know what the LC demands — it only transcribes "
    "what is printed on each page.\n"
    "- Field names may appear under variant aliases (e.g. 'seller_name' vs "
    "'exporter', 'lc_no' vs 'lc_number'). Treat these as equivalent.\n"
    "- A field absent from a document does NOT mean the exporter failed to "
    "include it — it may simply not be printed on that document type.\n"
    "- Focus on material discrepancies that would cause a bank to reject "
    "the presentation, not on formatting or stylistic differences."
)


def _build_ai_validation_prompt(
    document_data: Dict[str, Any],
    document_type: str,
) -> str:
    """Build the user prompt for the tiered AI validation call."""
    sections = _render_document_sections_for_prompt(document_data)
    return (
        f"You are reviewing the following extracted document data for an LC "
        f"validation. The primary document being evaluated is: {document_type}.\n\n"
        f"{sections}\n\n"
        "Identify compliance issues with these documents. For each issue you "
        "find, return a JSON object with these fields:\n"
        "- title: short headline (one sentence, plain English)\n"
        "- severity: one of \"compliance\" / \"discrepancy\" / \"advisory\"\n"
        "- expected: what the LC or the rules require\n"
        "- found: what was actually present in the documents\n"
        "- next_action: what the user should do to fix this\n"
        "- confidence: 0.0 to 1.0, your confidence that this is a real issue\n"
        "- documents: list of document type strings this issue touches\n"
        "- rule_basis: short reference if you know it (e.g. \"UCP600 18(a)(ii)\"), or null\n\n"
        "Only flag issues you are confident about. If you are unsure, lower "
        "the confidence rather than skipping the finding. Do not flag stylistic "
        "differences that would not cause a bank to discrepancy the documents.\n\n"
        "If a section below says \"(not submitted)\" then that document type is "
        "genuinely missing from the presentation. If a section contains data, the "
        "document IS present — never respond with phrases like 'no X available to "
        "verify' or 'verify upon receipt' for a document that appears here.\n\n"
        "Return a JSON object with shape:\n"
        "{\n"
        "  \"findings\": [ ... ],\n"
        "  \"overall_confidence\": 0.0-1.0,\n"
        "  \"requested_escalation\": true|false  // true if you want a more powerful model to take a second look\n"
        "}\n\n"
        "Return JSON only. No prose."
    )


# Keys the prompt renderer treats as distinct documents. Each gets its own
# labeled section with its own char budget so one doc (typically the LC)
# can never truncate the others off the end of the prompt.
_PROMPT_DOCUMENT_KEYS: Tuple[str, ...] = (
    "lc",
    "invoice",
    "bill_of_lading",
    "insurance",
    "certificate_of_origin",
    "packing_list",
    "inspection_certificate",
    "beneficiary_certificate",
    "draft",
)

# Top-level duplicates / large internal blobs that were silently eating the
# prompt budget. Dropping them does NOT lose information: `credit` duplicates
# `lc`; `insurance_doc` duplicates `insurance`; `extracted_context` re-nests
# every document we already render as its own section; `requirements_graph_v1`
# comes along inside the LC context already.
_PROMPT_DROP_TOP_LEVEL: frozenset = frozenset({
    "credit",
    "insurance_doc",
    "extracted_context",
    "requirements_graph_v1",
    "requirementsGraphV1",
})

# Per-field keys stripped recursively before serialization.
_PROMPT_DROP_NESTED: frozenset = frozenset({
    "_field_details",
    "_status_counts",
    "_semantic",
    "raw_text",
    "extraction_artifacts_v1",
    "rawText",
    "extractionArtifactsV1",
    "fact_graph_v1",
    "factGraphV1",
})

# Per-doc budgets (chars of pretty-printed JSON). The LC is bigger because it
# carries 46A/47A clauses. Supporting docs are a few KB each of extracted
# fields. 9 docs × 3500 + LC 6000 ≈ 37.5 KB ≈ 9K tokens — well under any
# frontier-model context.
_PROMPT_LC_CHAR_BUDGET = 6000
_PROMPT_DOC_CHAR_BUDGET = 3500


def _trim_document_data_for_prompt(document_data: Dict[str, Any]) -> Dict[str, Any]:
    """Strip large/internal fields before sending to the LLM."""
    if not isinstance(document_data, dict):
        return {}
    cleaned: Dict[str, Any] = {}
    for key, value in document_data.items():
        if key in _PROMPT_DROP_NESTED:
            continue
        if key.startswith("_"):
            continue
        if isinstance(value, dict):
            cleaned[key] = _trim_document_data_for_prompt(value)
        elif isinstance(value, list):
            cleaned[key] = [
                _trim_document_data_for_prompt(item) if isinstance(item, dict) else item
                for item in value[:20]  # cap list length
            ]
        else:
            cleaned[key] = value
    return cleaned


def _render_document_sections_for_prompt(document_data: Dict[str, Any]) -> str:
    """Render the document set as explicit per-doc sections with per-doc budgets.

    Each document type gets its own labeled ```json``` block. Missing doc types
    are rendered as "(not submitted)" so the LLM can tell the difference between
    "absent from the presentation" and "silently truncated off the prompt" — the
    latter used to happen with a single big-blob ``[:10000]`` slice and produced
    false-positive "no X available to verify" findings on docs that were in
    fact fully extracted.
    """
    if not isinstance(document_data, dict):
        document_data = {}

    sections: List[str] = []

    # LC first, with a larger budget (46A/47A clauses can be verbose).
    lc_payload = document_data.get("lc") if isinstance(document_data.get("lc"), dict) else None
    lc_trimmed = _trim_document_data_for_prompt(lc_payload) if lc_payload else None
    sections.append(_format_doc_section(
        "lc",
        lc_trimmed,
        _PROMPT_LC_CHAR_BUDGET,
    ))

    # Each supporting doc type gets its own section.
    for key in _PROMPT_DOCUMENT_KEYS:
        if key == "lc":
            continue
        raw_doc = document_data.get(key)
        doc_trimmed = _trim_document_data_for_prompt(raw_doc) if isinstance(raw_doc, dict) else None
        sections.append(_format_doc_section(key, doc_trimmed, _PROMPT_DOC_CHAR_BUDGET))

    # Anything else (e.g. lc_number / amount / currency scalars at top level,
    # jurisdiction, domain) gets a compact "misc" block so rule-targeting
    # context is preserved.
    misc: Dict[str, Any] = {}
    for key, value in document_data.items():
        if key in _PROMPT_DOCUMENT_KEYS:
            continue
        if key in _PROMPT_DROP_TOP_LEVEL:
            continue
        if key in _PROMPT_DROP_NESTED or key.startswith("_"):
            continue
        if isinstance(value, dict):
            misc[key] = _trim_document_data_for_prompt(value)
        elif isinstance(value, list):
            misc[key] = [
                _trim_document_data_for_prompt(item) if isinstance(item, dict) else item
                for item in value[:20]
            ]
        else:
            misc[key] = value
    if misc:
        sections.append(_format_doc_section("context", misc, _PROMPT_DOC_CHAR_BUDGET))

    return "\n\n".join(sections)


def _format_doc_section(label: str, payload: Optional[Dict[str, Any]], char_budget: int) -> str:
    pretty_label = label.replace("_", " ").upper()
    if not payload:
        return f"### {pretty_label}\n(not submitted)"
    body = json.dumps(payload, indent=2, default=str)
    if len(body) > char_budget:
        body = body[:char_budget] + "\n… [truncated]"
    return f"### {pretty_label}\n```json\n{body}\n```"


async def _run_tiered_ai_validation_pass(
    document_data: Dict[str, Any],
    document_type: str,
) -> List[Dict[str, Any]]:
    """Pass A: tiered AI validation with L1→L2→L3 escalation.

    Uses the existing LLMProviderFactory.generate_with_fallback router so
    we get the env-configured tier models. Each tier is tried in turn:
    L1 first, escalate to L2 only if the result is empty / low confidence /
    explicit-escalation-requested, then L3 as the last resort.

    Returns a list of finding dicts, each tagged with ``_source_layer``.
    """
    try:
        from app.services.llm_provider import LLMProviderFactory
    except ImportError:
        logger.warning("LLMProviderFactory not available — skipping tiered AI validation")
        return []

    prompt = _build_ai_validation_prompt(document_data, document_type)

    findings: List[Dict[str, Any]] = []
    last_overall_confidence: Optional[float] = None
    last_layer_used: Optional[str] = None

    for tier in ("L1", "L2", "L3"):
        try:
            result_tuple = await LLMProviderFactory.generate_with_fallback(
                prompt=prompt,
                system_prompt=_AI_VALIDATION_SYSTEM_PROMPT,
                router_layer=tier,
                temperature=0.1,
                max_tokens=2000,
            )
            # generate_with_fallback returns (output_text, tokens_in, tokens_out, provider_used)
            response_text = result_tuple[0] if isinstance(result_tuple, tuple) else str(result_tuple)
        except Exception as exc:  # noqa: BLE001
            logger.warning("AI validation tier=%s failed: %s", tier, exc)
            continue

        if not response_text:
            logger.info("AI validation tier=%s returned empty — escalating", tier)
            continue

        parsed = _safe_parse_json(response_text)
        if not parsed:
            logger.info("AI validation tier=%s JSON parse failed — escalating", tier)
            continue

        raw_findings = parsed.get("findings") if isinstance(parsed, dict) else None
        overall = parsed.get("overall_confidence") if isinstance(parsed, dict) else None
        requested_escalation = bool(parsed.get("requested_escalation")) if isinstance(parsed, dict) else False

        if isinstance(raw_findings, list):
            findings = [_normalize_ai_finding(f, tier) for f in raw_findings if isinstance(f, dict)]
        last_overall_confidence = overall if isinstance(overall, (int, float)) else last_overall_confidence
        last_layer_used = tier

        # Decide whether to escalate
        is_strong_enough = (
            isinstance(overall, (int, float))
            and float(overall) >= 0.7
            and not requested_escalation
        )
        if is_strong_enough:
            logger.info(
                "AI validation tier=%s accepted (confidence=%s, findings=%d)",
                tier, overall, len(findings),
            )
            return findings

        logger.info(
            "AI validation tier=%s weak (confidence=%s, requested_escalation=%s) — escalating",
            tier, overall, requested_escalation,
        )

    # All three tiers ran — return whatever the last layer produced.
    if findings:
        logger.info(
            "AI validation exhausted tiers (last_layer=%s, last_confidence=%s, findings=%d)",
            last_layer_used, last_overall_confidence, len(findings),
        )
    return findings


def _normalize_ai_finding(raw: Dict[str, Any], tier: str) -> Dict[str, Any]:
    """Convert an AI-produced finding dict into the standard finding shape."""
    return {
        "rule": raw.get("rule_basis") or f"AI-{tier}-{raw.get('title', '')[:30]}",
        "title": raw.get("title") or "AI finding",
        "description": raw.get("expected") or raw.get("title") or "",
        "severity": raw.get("severity") or "advisory",
        "message": raw.get("title") or raw.get("expected") or "",
        "expected": raw.get("expected"),
        "actual": raw.get("found"),
        "found": raw.get("found"),
        "suggestion": raw.get("next_action"),
        "next_action": raw.get("next_action"),
        "documents": raw.get("documents") or [],
        "rule_basis": raw.get("rule_basis"),
        "ai_confidence": raw.get("confidence"),
        "_source_layer": tier,
        "passed": False,
        "not_applicable": False,
    }


# ---------------------------------------------------------------------------
# Pass C — Opus veto
# ---------------------------------------------------------------------------


_OPUS_VETO_SYSTEM_PROMPT = (
    "You are the senior reviewer for a trade-finance document validation "
    "system. You see findings produced by the deterministic rule engine "
    "(and sometimes an AI examiner layer), and your ONLY job is to decide "
    "which of those findings survive. You can confirm, drop, or modify any "
    "finding. You CANNOT add new findings — if the deterministic engine did "
    "not raise it, it does not belong in the output.\n\n"
    "Why this rule exists: every finding in this product must cite a specific "
    "46A/47A clause of the LC under review. The deterministic engine already "
    "parses those clauses and raises findings for each one. If you invent a "
    "new finding here, it won't carry a clause citation and will usually be "
    "a UCP600 rule you remembered from training rather than something the "
    "LC itself demands — that's the exact failure mode we are eliminating.\n\n"
    "Be ruthless about DROPPING false positives. If the doc-section in the "
    "prompt clearly contradicts a finding's 'found' text, drop it with a "
    "reason. If a finding is substantively correct but phrased poorly, "
    "modify the title/severity. If in doubt, confirm.\n\n"
    "IMPORTANT: Each document was extracted independently by a blind per-doc "
    "OCR transcriber. Field names may appear under variant aliases. A field "
    "absent from a document may simply not be printed on that doc type — do "
    "NOT treat alias differences as discrepancies."
)


def _build_opus_veto_prompt(
    document_data: Dict[str, Any],
    document_type: str,
    ai_findings: List[Dict[str, Any]],
    deterministic_findings: List[Dict[str, Any]],
) -> str:
    doc_sections = _render_document_sections_for_prompt(document_data)
    ai_summary = [
        {
            "title": f.get("title"),
            "severity": f.get("severity"),
            "expected": f.get("expected"),
            "found": f.get("found"),
            "ai_confidence": f.get("ai_confidence"),
            "source_layer": f.get("_source_layer"),
        }
        for f in ai_findings
    ]
    det_summary = [
        {
            "rule": f.get("rule"),
            "title": f.get("title"),
            "severity": f.get("severity"),
            "message": f.get("message"),
            "expected": f.get("expected") or f.get("expected_value"),
            "found": f.get("actual") or f.get("found") or f.get("actual_value"),
        }
        for f in deterministic_findings
    ]
    return (
        f"Document type under review: {document_type}\n\n"
        f"{doc_sections}\n\n"
        f"AI examiner findings ({len(ai_summary)}):\n```json\n{json.dumps(ai_summary, indent=2)[:6000]}\n```\n\n"
        f"Deterministic rule findings ({len(det_summary)}):\n```json\n{json.dumps(det_summary, indent=2)[:6000]}\n```\n\n"
        "Review these findings and return JSON with this exact shape:\n"
        "{\n"
        "  \"actions\": [\n"
        "    {\"source\": \"ai\"|\"deterministic\", \"index\": <int>, \"action\": \"confirm\"|\"drop\"|\"modify\", \"reason\": \"...\", \"updated_title\": \"...\"|null, \"updated_severity\": \"...\"|null}\n"
        "  ],\n"
        "  \"overall_assessment\": \"one-sentence summary\"\n"
        "}\n\n"
        "Rules for actions:\n"
        "- index is the position in the source array (0-based)\n"
        "- \"confirm\" means keep the finding as-is\n"
        "- \"drop\" means delete it (false positive). Always include a reason.\n"
        "- \"modify\" means keep but adjust title/severity. Include updated_title and/or updated_severity.\n"
        "- You CANNOT add new findings. Only the deterministic engine sources findings — "
        "it reads the LC's own 46A/47A clauses and raises one finding per unmet clause. "
        "Any new 'finding' you invent here would bypass that citation contract and "
        "almost always reflects a UCP600 rule you remembered from training rather than "
        "something this specific LC demands.\n"
        "- Be conservative: only drop a finding if you are confident it's a false positive.\n"
        "- If a document section above contains data, that document IS present. Drop any\n"
        "  finding whose 'found' text claims the document is missing/unavailable when the\n"
        "  section above shows it with extracted fields.\n\n"
        "Return JSON only, no prose."
    )


async def _run_opus_veto_pass(
    *,
    document_data: Dict[str, Any],
    document_type: str,
    ai_findings: List[Dict[str, Any]],
    deterministic_findings: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Pass C: single Opus call that reviews and finalizes the finding set.

    Returns the merged final list. If Opus fails, callers should fall back
    to ai_findings + deterministic_findings concatenated.
    """
    try:
        from app.services.llm_provider import LLMProviderFactory
    except ImportError:
        logger.warning("LLMProviderFactory not available — skipping Opus veto pass")
        return [*ai_findings, *deterministic_findings]

    prompt = _build_opus_veto_prompt(document_data, document_type, ai_findings, deterministic_findings)

    try:
        result_tuple = await LLMProviderFactory.generate_with_fallback(
            prompt=prompt,
            system_prompt=_OPUS_VETO_SYSTEM_PROMPT,
            router_layer="L3",  # Force the top tier — this IS the veto, always Opus
            temperature=0.1,
            max_tokens=3000,
        )
        response_text = result_tuple[0] if isinstance(result_tuple, tuple) else str(result_tuple)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Opus veto call failed: %s", exc)
        return [*ai_findings, *deterministic_findings]

    if not response_text:
        return [*ai_findings, *deterministic_findings]

    parsed = _safe_parse_json(response_text)
    if not isinstance(parsed, dict):
        logger.warning("Opus veto response was not a parseable JSON object")
        return [*ai_findings, *deterministic_findings]

    actions = parsed.get("actions") or []

    # Apply actions to ai_findings and deterministic_findings. The veto's ONLY
    # job is confirm/drop/modify on the finding set the deterministic engine
    # produced. The Opus "anomalies" branch used to be parsed here and merged
    # back in as fresh findings — that's what produced false-positive titles
    # like "Insurance Coverage Below LC Requirement" on an LC that never
    # required insurance, "Invoice port name mismatch" when the two names
    # are just aliases for the same UN/LOCODE, and so on. Those findings had
    # no clause citation because they weren't rooted in this LC's 46A/47A —
    # they came from the LLM's general UCP600 training. Intentionally dropped
    # in C1 of the consolidation plan: deterministic is the only source.
    final_ai = _apply_veto_actions(ai_findings, actions, "ai")
    final_det = _apply_veto_actions(deterministic_findings, actions, "deterministic")

    # If Opus emitted any "anomalies" anyway (ignoring the system prompt),
    # log their titles so we can spot regressions and tune the prompt — but
    # never feed them back into the findings list.
    stray_anomalies = parsed.get("anomalies") or []
    if stray_anomalies:
        logger.warning(
            "Opus veto emitted %d anomalies despite the instruction to only "
            "confirm/drop/modify. Suppressing. Titles: %s",
            len(stray_anomalies),
            [str(a.get("title"))[:80] for a in stray_anomalies if isinstance(a, dict)],
        )

    overall = parsed.get("overall_assessment")
    if overall:
        logger.info("Opus veto overall_assessment: %s", overall)

    return [*final_ai, *final_det]


def _apply_veto_actions(
    findings: List[Dict[str, Any]],
    actions: List[Any],
    source_label: str,
) -> List[Dict[str, Any]]:
    """Apply Opus veto actions to a finding list and return the survivors."""
    drop_set: set = set()
    modifications: Dict[int, Dict[str, Any]] = {}

    for action in actions:
        if not isinstance(action, dict):
            continue
        if (action.get("source") or "").lower() != source_label:
            continue
        try:
            idx = int(action.get("index", -1))
        except (TypeError, ValueError):
            continue
        if idx < 0 or idx >= len(findings):
            continue

        action_type = (action.get("action") or "").lower()
        if action_type == "drop":
            drop_set.add(idx)
        elif action_type == "modify":
            modifications[idx] = {
                "updated_title": action.get("updated_title"),
                "updated_severity": action.get("updated_severity"),
                "reason": action.get("reason"),
            }
        # "confirm" is the default — no-op

    survivors: List[Dict[str, Any]] = []
    for idx, finding in enumerate(findings):
        if idx in drop_set:
            continue  # vetoed out
        finding = dict(finding)  # don't mutate caller's data
        if idx in modifications:
            mod = modifications[idx]
            if mod.get("updated_title"):
                finding["title"] = mod["updated_title"]
                finding["message"] = mod["updated_title"]
            if mod.get("updated_severity"):
                finding["severity"] = mod["updated_severity"]
            finding["_vetoed"] = True
            finding["_veto_reason"] = mod.get("reason")
        survivors.append(finding)
    return survivors


def _normalize_anomaly_finding(raw: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "rule": f"VETO-ANOMALY-{(raw.get('category') or 'general').upper()}",
        "title": raw.get("title") or "Anomaly flagged by veto reviewer",
        "description": raw.get("expected") or raw.get("title") or "",
        "severity": raw.get("severity") or "advisory",
        "message": raw.get("title") or raw.get("expected") or "",
        "expected": raw.get("expected"),
        "actual": raw.get("found"),
        "found": raw.get("found"),
        "suggestion": raw.get("next_action"),
        "next_action": raw.get("next_action"),
        "category": raw.get("category"),
        "_source_layer": "veto",
        "_added_by_veto": True,
        "passed": False,
        "not_applicable": False,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_parse_json(text: str) -> Optional[Any]:
    """Parse JSON from an LLM response, tolerating leading/trailing prose."""
    if not text:
        return None
    text = text.strip()
    # Try direct parse first
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        pass
    # Try to find a JSON object inside the text
    try:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
    except (ValueError, TypeError):
        pass
    return None


__all__ = ["validate_document_with_pipeline"]
