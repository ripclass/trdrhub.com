"""RulHub-backed sanctions screening — Phase 2 launch (2026-07).

Replaces the local sample-list screener (``sanctions_screening.py`` screened
against ~60 hardcoded SAMPLE_* entries — a real name would false-"clear")
with RulHub's deterministic engine: POST /v1/screen/sanctions runs tiered
name/IMO matching against OFAC SDN / OFAC consolidated / UN / UK OFSI
designated-party lists plus the sanctions programme-rules corpus.

FAIL-CLOSED is the contract of this module:

* Any transport / API error raises :class:`ScreeningUnavailable` — the router
  turns that into a 503 with "do not treat as clear". Never an empty
  "no hits" response.
* A RulHub response that evaluated nothing (``coverage_warning`` set, or
  ``clear=true`` with ``rules_checked=0`` and no ``list_match`` scope when a
  name/vessel was screened) maps to status ``unavailable``, not ``clear``.

Sentinel names for e2e with an rh_test_* key: "RULHUB TEST HIT" → match /
block, "RULHUB TEST POSSIBLE MATCH" → potential_match / review,
"RULHUB TEST CLEAR" → clear.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.services.rulhub_client import (
    RulHubAPIError,
    get_rulhub_client,
)

logger = logging.getLogger(__name__)

FAIL_CLOSED_MESSAGE = (
    "Sanctions screening is currently unavailable — do NOT treat this as a "
    "clear result. Retry, or escalate to your compliance officer before "
    "proceeding."
)

# Human names for RulHub list_source codes.
LIST_NAMES: Dict[str, str] = {
    "ofac_sdn": "OFAC SDN List (US)",
    "ofac_consolidated": "OFAC Consolidated (Non-SDN) List (US)",
    "un_consolidated": "UN Security Council Consolidated List",
    "uk_ofsi": "UK OFSI Consolidated List",
    "eu_fsf": "EU Consolidated Financial Sanctions List",
}

# The registry shown on /sanctions/lists — what the engine actually screens.
# EU list is pending on the engine side (EU_FSF_TOKEN); shown as such, never
# claimed as covered.
COVERED_LISTS: List[Dict[str, str]] = [
    {"code": "ofac_sdn", "name": LIST_NAMES["ofac_sdn"], "jurisdiction": "US", "status": "active"},
    {"code": "ofac_consolidated", "name": LIST_NAMES["ofac_consolidated"], "jurisdiction": "US", "status": "active"},
    {"code": "un_consolidated", "name": LIST_NAMES["un_consolidated"], "jurisdiction": "UN", "status": "active"},
    {"code": "uk_ofsi", "name": LIST_NAMES["uk_ofsi"], "jurisdiction": "UK", "status": "active"},
    {"code": "eu_fsf", "name": LIST_NAMES["eu_fsf"], "jurisdiction": "EU", "status": "pending"},
]

OFAC_50_CAVEAT = (
    "Ownership structures are not resolved: an entity majority-owned by a "
    "designated party (OFAC 50% rule) may not itself appear on any list."
)


class ScreeningUnavailable(Exception):
    """Raised when screening could not be performed. Callers MUST fail closed."""


def _screening_id() -> str:
    return f"scr_{uuid.uuid4().hex[:16]}"


def map_rulhub_result(
    result: Dict[str, Any],
    *,
    query: str,
    screening_type: str,
    expect_list_match: bool,
) -> Dict[str, Any]:
    """Map RulHub's ScreeningResult into the trdrhub ScreeningResponse shape.

    ``expect_list_match`` — True when a name/vessel was submitted, so a result
    that never consulted the designated-party lists is treated as unavailable
    (fail-closed) rather than clear.
    """
    hits = [h for h in (result.get("hits") or []) if isinstance(h, dict)]
    flags_raw = [f for f in (result.get("flags") or []) if isinstance(f, dict)]
    scope = result.get("screening_scope") or []
    coverage_warning = result.get("coverage_warning")
    rules_checked = int(result.get("rules_checked") or 0)
    list_versions = result.get("list_versions") or {}

    # ---- status ----------------------------------------------------------
    has_hit = any(h.get("category") == "hit" for h in hits)
    has_possible = any(h.get("category") == "possible_match" for h in hits)
    red_flags = [f for f in flags_raw if str(f.get("severity", "")).lower() in ("critical", "reject", "fail", "high")]

    screened_lists = "list_match" in scope or "test_fixture" in scope
    if has_hit:
        status = "match"
    elif has_possible or red_flags:
        status = "potential_match"
    elif coverage_warning:
        status = "unavailable"
    elif expect_list_match and not screened_lists:
        # We sent a name/vessel but the engine never consulted the lists —
        # e.g. lists not loaded. clear=true here means nothing.
        status = "unavailable"
    elif not expect_list_match and rules_checked == 0 and not screened_lists:
        # Goods/route-style screening where no rules were evaluated at all.
        status = "unavailable"
    else:
        status = "clear"

    # ---- matches ---------------------------------------------------------
    matches: List[Dict[str, Any]] = []
    for h in hits:
        list_code = str(h.get("list_source") or "unknown")
        caveats = [str(c) for c in (h.get("caveats") or [])]
        matches.append({
            "list_code": list_code,
            "list_name": LIST_NAMES.get(list_code, list_code),
            "matched_name": str(h.get("matched_name") or h.get("primary_name") or ""),
            "matched_type": str(h.get("entity_type") or "entity"),
            "match_type": str(h.get("category") or "possible_match"),
            "match_score": float(h.get("score") or 0.0),
            "match_method": str(h.get("match_type") or ""),
            "programs": [str(p) for p in (h.get("programs") or [])],
            "source_id": str(h.get("list_entry_id") or "") or None,
            "action": str(h.get("action") or "review"),
            "recommendation": str(h.get("recommendation") or ""),
            "caveats": caveats,
            "programme_context": h.get("programme_context") or [],
        })

    # ---- recommendation --------------------------------------------------
    if status == "match":
        blocked = next((m for m in matches if m["action"] == "block"), matches[0] if matches else None)
        recommendation = (blocked or {}).get("recommendation") or (
            "Designated-party match — do not proceed; escalate to your compliance officer."
        )
    elif status == "potential_match":
        recommendation = (
            "Possible match — manual review required before proceeding. "
            "Compare identifiers (address, DOB, registration numbers) against the listed party."
        )
    elif status == "unavailable":
        recommendation = coverage_warning or FAIL_CLOSED_MESSAGE
    else:
        recommendation = (
            "No designated-party matches found on the screened lists at this time. "
            f"{OFAC_50_CAVEAT}"
        )

    lists_screened = sorted(list_versions.keys()) if list_versions else (
        [l["code"] for l in COVERED_LISTS if l["status"] == "active"] if screened_lists else []
    )

    return {
        "query": query,
        "screening_type": screening_type,
        "screened_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "risk_level": str(result.get("risk_level") or "unknown"),
        "lists_screened": lists_screened,
        "list_versions": list_versions or None,
        "matches": matches,
        "total_matches": len(matches),
        "highest_score": max((m["match_score"] for m in matches), default=0.0),
        "flags": [str(f.get("finding") or f.get("rule_id") or "") for f in flags_raw],
        "recommendation": recommendation,
        "screening_id": _screening_id(),
        "processing_time_ms": int(result.get("processing_time_ms") or 0),
        "rules_checked": rules_checked,
        "screening_scope": scope,
        "coverage_warning": coverage_warning,
        "engine": "rulhub",
    }


async def screen_via_rulhub(
    *,
    query: str,
    screening_type: str,
    entity: Optional[str] = None,
    country: Optional[str] = None,
    vessel: Optional[str] = None,
    transaction: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Screen one subject through RulHub. Raises ScreeningUnavailable on ANY failure."""
    client = get_rulhub_client()
    try:
        raw = await client.screen_sanctions(
            entity=entity, country=country, vessel=vessel, transaction=transaction,
        )
    except RulHubAPIError as exc:
        logger.error("Sanctions screening unavailable (RulHub error): %s", exc)
        raise ScreeningUnavailable(FAIL_CLOSED_MESSAGE) from exc
    except Exception as exc:  # transport errors, timeouts, JSON decode …
        logger.exception("Sanctions screening unavailable (transport error)")
        raise ScreeningUnavailable(FAIL_CLOSED_MESSAGE) from exc

    if not isinstance(raw, dict):
        logger.error("Sanctions screening returned non-dict payload: %r", type(raw))
        raise ScreeningUnavailable(FAIL_CLOSED_MESSAGE)

    mapped = map_rulhub_result(
        raw,
        query=query,
        screening_type=screening_type,
        expect_list_match=bool(entity or vessel),
    )
    logger.info(
        "Sanctions screening [%s] '%s' → status=%s hits=%d risk=%s scope=%s",
        screening_type, query[:80], mapped["status"], mapped["total_matches"],
        mapped["risk_level"], ",".join(mapped.get("screening_scope") or []),
    )
    return mapped
