"""LLM-driven LC clause → requirement graph.

The regex-based clause_parser only catches wordings we've hand-coded. Every
new LC phrasing (``DULY SIGNED`` vs ``SIGNED BY BENEFICIARY`` vs ``BEARING
ORIGINAL SIGNATURE``) becomes a miss. That's the spinal bug this module
replaces: instead of patterning every possible wording, we ask an LLM to
read THIS LC's 46A/47A and map each clause onto a **closed condition
vocabulary** that the deterministic matcher already knows how to check.

Key discipline:

1. The LLM output is constrained to a closed vocabulary — it cannot invent
   new condition kinds or new value_constraint kinds. If a clause says
   something we haven't modelled, the LLM must fall back to ``statement_
   includes`` (a free-text "the doc must carry this phrase") rather than
   hallucinate a new check.

2. Every emitted requirement carries the verbatim ``source_text`` the
   clause came from. Callers validate that substring membership; a
   requirement whose source_text isn't actually in 46A/47A is dropped.
   This is the safety net against the LLM pulling UCP600 rules from its
   training memory.

3. The LLM never produces findings. It only produces REQUIREMENTS. The
   deterministic matcher produces findings by comparing extracted-doc
   data against those requirements. Findings always cite the requirement
   they came from (source_field + clause_index + raw_text + condition
   kind).
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Closed condition vocabulary
#
# The LLM is ALLOWED to emit exactly these kinds and no others. If the
# clause says something outside this vocabulary, the LLM must express it
# as a `statement_includes` condition carrying the verbatim phrase.
# ---------------------------------------------------------------------------

CONDITION_KINDS: Tuple[str, ...] = (
    # Document-level attestation features
    "signed",                  # must be signed (signature / stamp / seal)
    "clean_on_board",          # must say "clean" + "on board"
    "full_set",                # must be full set of originals
    "copies",                  # value=int, number of copies
    "originals",               # value=int, number of originals
    "dated_within_lc_validity",# must have an issue date within LC issue/expiry window
    "issued_by",               # value=str, required issuing authority
    "consigned_to_order_of",   # value=str, consignee identity
    "freight",                 # value="prepaid"|"collect"|"any"
    "notify_party",            # value=str, required notify party
    "cross_refs_required",     # must carry LC no / PO / BIN / TIN
    "statement_includes",      # value=str, free-text phrase the doc must carry
    # Value-of-a-specific-field conditions
    "field_equals",            # field=name, value=str (e.g., country_of_origin="BANGLADESH")
    "field_matches_pattern",   # field=name, pattern=regex (for format-bound clauses)
)

VALUE_CONSTRAINT_KINDS: Tuple[str, ...] = (
    "amount_matches_lc",
    "amount_not_exceed_lc",
    "currency_matches_lc",
    "hs_codes_match_lc",
    "port_of_loading_matches_lc",
    "port_of_discharge_matches_lc",
    "latest_shipment_not_exceeded",
    "presentation_period_met",
    "beneficiary_matches_lc",
    "applicant_matches_lc",
    "arithmetic_consistency",   # e.g., invoice line items sum to invoice total
    "weight_consistency",       # BL weight == Packing List weight
)


@dataclass
class Condition:
    """One condition on a single document, from the closed vocabulary."""
    kind: str
    value: Any = None                  # interpreted per-kind (int for copies, str for issued_by, …)
    field: Optional[str] = None        # only for field_* kinds
    pattern: Optional[str] = None      # only for field_matches_pattern
    description: str = ""              # human-readable summary
    severity: str = "discrepancy"      # "discrepancy" | "advisory" | "presentation_checklist"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "value": self.value,
            "field": self.field,
            "pattern": self.pattern,
            "description": self.description,
            "severity": self.severity,
        }


@dataclass
class ValueConstraint:
    """One cross-document value constraint, from the closed vocabulary."""
    kind: str
    description: str = ""
    severity: str = "discrepancy"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "description": self.description,
            "severity": self.severity,
        }


@dataclass
class RichClause:
    """A single LC clause parsed into machine-readable requirements.

    Superset of ``clause_parser.ParsedClause``: adds ``conditions`` and
    ``value_constraints`` from the closed vocabularies. Carries the raw
    clause text so findings can cite it verbatim.
    """
    raw_text: str
    source_field: str                  # "46A" | "47A"
    clause_index: int                  # 0-based
    document_type: Optional[str] = None
    document_must_exist: bool = False  # clause mandates the document's presence
    required_fields: List[str] = field(default_factory=list)
    conditions: List[Condition] = field(default_factory=list)
    value_constraints: List[ValueConstraint] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw_text": self.raw_text,
            "source_field": self.source_field,
            "clause_index": self.clause_index,
            "document_type": self.document_type,
            "document_must_exist": self.document_must_exist,
            "required_fields": self.required_fields,
            "conditions": [c.to_dict() for c in self.conditions],
            "value_constraints": [v.to_dict() for v in self.value_constraints],
        }


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = (
    "You are a Letter of Credit clause parser. Your ONLY job is to read the "
    "46A (Documents Required) and 47A (Additional Conditions) fields of the "
    "LC supplied by the user and transcribe each numbered clause into a "
    "structured requirement. You do NOT add rules from UCP600 general "
    "knowledge. You do NOT add rules the LC does not state. If the clause "
    "doesn't say it, it doesn't belong in the output. This is an audit-grade "
    "transcription task, not a compliance review.\n\n"
    "You emit requirements using a CLOSED vocabulary. If a clause says "
    "something outside the vocabulary, express it as a "
    "`statement_includes` condition carrying the verbatim phrase the "
    "document must bear — never invent a new condition kind.\n\n"
    "Each requirement MUST include the verbatim source_text it came from, "
    "so the caller can verify the requirement is actually in the LC."
)


def _build_user_prompt(lc_46a: str, lc_47a: str) -> str:
    return (
        "Parse the following LC fields into a structured requirement graph.\n\n"
        f"### 46A — Documents Required\n```\n{lc_46a or '(empty)'}\n```\n\n"
        f"### 47A — Additional Conditions\n```\n{lc_47a or '(empty)'}\n```\n\n"
        "Return JSON with this exact shape:\n"
        "```json\n"
        "{\n"
        "  \"clauses\": [\n"
        "    {\n"
        "      \"source_field\": \"46A\" | \"47A\",\n"
        "      \"clause_index\": <0-based int, position within its source field>,\n"
        "      \"raw_text\": \"<verbatim clause text>\",\n"
        "      \"document_type\": \"letter_of_credit\" | \"commercial_invoice\" | \"bill_of_lading\" | \"air_waybill\" | \"packing_list\" | \"certificate_of_origin\" | \"insurance_certificate\" | \"insurance_policy\" | \"inspection_certificate\" | \"beneficiary_certificate\" | \"draft\" | \"health_certificate\" | \"phytosanitary_certificate\" | \"weight_certificate\" | \"fumigation_certificate\" | null,\n"
        "      \"document_must_exist\": true | false,\n"
        "      \"required_fields\": [\"<canonical_field_name>\", ...],\n"
        "      \"conditions\": [\n"
        "        {\"kind\": \"<one of the closed condition kinds>\", \"value\": <kind-specific>, \"field\": \"<optional, for field_* kinds>\", \"description\": \"<one sentence>\"}\n"
        "      ],\n"
        "      \"value_constraints\": [\n"
        "        {\"kind\": \"<one of the closed value_constraint kinds>\", \"description\": \"<one sentence>\"}\n"
        "      ]\n"
        "    }\n"
        "  ]\n"
        "}\n"
        "```\n\n"
        "Rules:\n"
        f"- Allowed condition.kind values: {', '.join(CONDITION_KINDS)}\n"
        f"- Allowed value_constraint.kind values: {', '.join(VALUE_CONSTRAINT_KINDS)}\n"
        "- document_type must come from the enumerated list; if the clause applies "
        "  to no specific doc type (e.g., a dating rule for all docs), use null "
        "  and express the rule via value_constraint.\n"
        "- document_must_exist=true only when the clause actually lists the doc "
        "  as required (not when it merely mentions the doc type in passing).\n"
        "- Canonical field names for required_fields (use these verbatim when applicable): "
        "  lc_number, buyer_purchase_order_number, exporter_bin, exporter_tin, "
        "  hs_code, quantity, unit_price, total_amount, goods_description, "
        "  vessel_name, voyage_number, container_number, seal_number, "
        "  gross_weight, net_weight, port_of_loading, port_of_discharge, "
        "  notify_party, issue_date, country_of_origin, issuing_authority, "
        "  coverage_percentage, insured_amount.\n"
        "- For 'DOCUMENTS MUST NOT BE DATED EARLIER THAN LC ISSUE DATE' style "
        "  clauses, emit one clause with document_type=null and a single "
        "  condition kind='dated_within_lc_validity' (the matcher will apply "
        "  this to every submitted doc).\n"
        "- For 'SIGNED COMMERCIAL INVOICE IN 6 COPIES INDICATING HS CODE, QTY, "
        "  UNIT PRICE AND TOTAL' you emit ONE clause with document_type="
        "  'commercial_invoice', document_must_exist=true, required_fields="
        "  ['hs_code','quantity','unit_price','total_amount'], and conditions "
        "  [{kind:'signed',...}, {kind:'copies',value:6,...}].\n"
        "- For cross-document cues like 'BL SHALL MATCH THE PORT OF LOADING IN "
        "  THIS CREDIT', emit value_constraints=[{kind:'port_of_loading_matches_lc'}].\n"
        "- If the text has nothing the vocabulary covers, still emit the clause "
        "  with document_type=null and a single condition kind='statement_includes' "
        "  carrying the verbatim phrase — never drop a clause silently.\n\n"
        "Return JSON only, no prose. If 46A or 47A is empty, return clauses=[]."
    )


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


async def llm_parse_lc_clauses(
    lc_46a: Any,
    lc_47a: Any,
    *,
    timeout_seconds: float = 45.0,
) -> Tuple[List[RichClause], Dict[str, Any]]:
    """Call the LLM to parse the LC's own clauses into RichClause objects.

    Returns ``(clauses, meta)``. ``meta`` carries diagnostics useful for
    telemetry (provider, tokens, parse errors, validation drops).

    Never raises — on any failure returns ``([], {"error": ...})`` and the
    caller falls back to the regex parser.
    """
    meta: Dict[str, Any] = {"source": "llm_clause_graph"}
    lc_46a_text = _flatten_clause_text(lc_46a)
    lc_47a_text = _flatten_clause_text(lc_47a)

    if not lc_46a_text and not lc_47a_text:
        meta["skipped"] = "empty LC"
        return [], meta

    try:
        from app.services.llm_provider import LLMProviderFactory
    except ImportError:
        meta["error"] = "LLMProviderFactory unavailable"
        return [], meta

    import asyncio
    prompt = _build_user_prompt(lc_46a_text, lc_47a_text)

    try:
        result_tuple = await asyncio.wait_for(
            LLMProviderFactory.generate_with_fallback(
                prompt=prompt,
                system_prompt=_SYSTEM_PROMPT,
                router_layer="L3",
                temperature=0.0,
                max_tokens=4000,
            ),
            timeout=timeout_seconds,
        )
    except asyncio.TimeoutError:
        meta["error"] = f"LLM clause parse timed out after {timeout_seconds}s"
        return [], meta
    except Exception as exc:  # noqa: BLE001
        meta["error"] = f"LLM clause parse failed: {exc}"
        return [], meta

    response_text = result_tuple[0] if isinstance(result_tuple, tuple) else str(result_tuple)
    meta["response_len"] = len(response_text or "")
    if not response_text:
        meta["error"] = "empty LLM response"
        return [], meta

    parsed = _safe_parse_json(response_text)
    if not isinstance(parsed, dict):
        meta["error"] = "non-JSON LLM response"
        return [], meta

    raw_clauses = parsed.get("clauses") if isinstance(parsed.get("clauses"), list) else []
    clauses: List[RichClause] = []
    dropped: List[Dict[str, Any]] = []

    source_text_for_validation = (lc_46a_text + "\n" + lc_47a_text).upper()

    for entry in raw_clauses:
        if not isinstance(entry, dict):
            continue
        rich = _validate_and_build_clause(entry, source_text_for_validation)
        if rich is None:
            dropped.append({"raw": entry})
            continue
        clauses.append(rich)

    meta["clauses_in"] = len(raw_clauses)
    meta["clauses_out"] = len(clauses)
    meta["clauses_dropped"] = len(dropped)
    if dropped:
        meta["dropped_samples"] = dropped[:3]

    logger.info(
        "LLM clause parse: %d clauses in → %d out (%d dropped)",
        meta["clauses_in"], meta["clauses_out"], meta["clauses_dropped"],
    )
    return clauses, meta


# ---------------------------------------------------------------------------
# Validation + helpers
# ---------------------------------------------------------------------------


_ALLOWED_DOC_TYPES = frozenset({
    "letter_of_credit", "commercial_invoice", "bill_of_lading", "air_waybill",
    "packing_list", "certificate_of_origin", "insurance_certificate",
    "insurance_policy", "inspection_certificate", "beneficiary_certificate",
    "draft", "health_certificate", "phytosanitary_certificate",
    "weight_certificate", "fumigation_certificate",
})


def _validate_and_build_clause(
    entry: Dict[str, Any],
    source_text_upper: str,
) -> Optional[RichClause]:
    """Validate one LLM-emitted clause dict and return a RichClause, or None
    if the entry fails the safety contract."""
    raw_text = str(entry.get("raw_text") or "").strip()
    if not raw_text:
        return None

    # Safety net: drop any clause whose raw_text doesn't appear in the LC
    # the caller sent us. This defends against the LLM hallucinating a rule
    # from training data and writing a plausible-looking raw_text for it.
    # We match on the first 30 chars (upper-cased, whitespace-collapsed) —
    # long enough to be unique, short enough to tolerate minor LLM edits.
    probe = re.sub(r"\s+", " ", raw_text[:30]).upper().strip()
    haystack = re.sub(r"\s+", " ", source_text_upper)
    if probe and probe not in haystack:
        logger.warning(
            "Dropping LLM clause — source_text not found in LC: %r", raw_text[:80]
        )
        return None

    source_field = str(entry.get("source_field") or "").strip()
    if source_field not in ("46A", "47A"):
        return None

    try:
        clause_index = int(entry.get("clause_index", 0))
    except (TypeError, ValueError):
        clause_index = 0

    document_type = entry.get("document_type")
    if document_type is not None:
        if str(document_type) not in _ALLOWED_DOC_TYPES:
            # Unknown doc type — normalise to None rather than drop, so the
            # clause's conditions / value_constraints can still fire if
            # they're doc-agnostic.
            document_type = None

    document_must_exist = bool(entry.get("document_must_exist", False))

    required_fields = [
        str(f).strip()
        for f in (entry.get("required_fields") or [])
        if isinstance(f, str) and str(f).strip()
    ]

    conditions: List[Condition] = []
    for c in (entry.get("conditions") or []):
        if not isinstance(c, dict):
            continue
        kind = str(c.get("kind") or "").strip()
        if kind not in CONDITION_KINDS:
            # Unknown condition — demote to statement_includes carrying the
            # verbatim raw_text, so the check still fires as a text-scan.
            conditions.append(Condition(
                kind="statement_includes",
                value=raw_text,
                description=f"Clause requires (demoted from unknown kind {kind!r}): {raw_text[:200]}",
                severity="advisory",
            ))
            continue
        conditions.append(Condition(
            kind=kind,
            value=c.get("value"),
            field=(str(c["field"]).strip() if c.get("field") else None),
            pattern=(str(c["pattern"]).strip() if c.get("pattern") else None),
            description=str(c.get("description") or "").strip(),
            severity=str(c.get("severity") or "discrepancy").strip(),
        ))

    value_constraints: List[ValueConstraint] = []
    for vc in (entry.get("value_constraints") or []):
        if not isinstance(vc, dict):
            continue
        kind = str(vc.get("kind") or "").strip()
        if kind not in VALUE_CONSTRAINT_KINDS:
            continue
        value_constraints.append(ValueConstraint(
            kind=kind,
            description=str(vc.get("description") or "").strip(),
            severity=str(vc.get("severity") or "discrepancy").strip(),
        ))

    return RichClause(
        raw_text=raw_text,
        source_field=source_field,
        clause_index=clause_index,
        document_type=document_type,
        document_must_exist=document_must_exist,
        required_fields=required_fields,
        conditions=conditions,
        value_constraints=value_constraints,
    )


def _flatten_clause_text(val: Any) -> str:
    """Flatten 46A / 47A payload (string / list-of-strings / list-of-dicts /
    dict / None) into a single searchable text blob."""
    if val is None:
        return ""
    if isinstance(val, str):
        return val
    if isinstance(val, list):
        parts: List[str] = []
        for item in val:
            if isinstance(item, dict):
                parts.append(str(item.get("raw_text") or item.get("text") or item.get("value") or ""))
            else:
                parts.append(str(item))
        return "\n".join(p for p in parts if p)
    if isinstance(val, dict):
        return str(val.get("raw_text") or val.get("text") or json.dumps(val, default=str))
    return str(val)


def _safe_parse_json(text: str) -> Optional[Any]:
    """Parse JSON from an LLM response, tolerating markdown fences and
    leading/trailing prose."""
    if not text:
        return None
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except (ValueError, TypeError):
        pass
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(cleaned[start: end + 1])
        except (ValueError, TypeError):
            pass
    return None


__all__ = [
    "Condition",
    "ValueConstraint",
    "RichClause",
    "CONDITION_KINDS",
    "VALUE_CONSTRAINT_KINDS",
    "llm_parse_lc_clauses",
]
