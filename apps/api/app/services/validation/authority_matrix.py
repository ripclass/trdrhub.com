"""Authority-matrix reconciliation pass (item 3, 2026-06-12).

Runs where the AI layer (examiner + AI-prefixed backstops) and the
deterministic layer (RulHub / local rules) merge, BEFORE the veto.
For mechanical fact classes — arithmetic and dates — the deterministic
engine is authoritative: a duplicate AI finding about the same fact is
dropped and logged as an ``authority_dedup`` disagreement-log event,
never silently. This is the "finding deduplication" Part 2 backlog item
done per the authority matrix: one mechanism decides which copy
survives.

The validator family already on each finding is the routing key — rule
ids like ``CROSSDOC-INV-MATH-001`` / ``AI-INV-ARITHMETIC`` /
``UCP600-14C`` carry enough signal; no new metadata is required.

Conservative by design: a dedup fires only when the class matches AND
the findings reference an overlapping document AND (for dates) share a
date-field token. A false merge hides a real discrepancy — when unsure,
keep both copies and let the veto decide.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

_ARITHMETIC_RULE_TOKENS = ("MATH", "ARITHMETIC")
_ARITHMETIC_TEXT_HINTS = (
    "sum of line",
    "unit price",
    "computed total",
    "arithmetic",
    "does not equal the stated total",
)

_DATE_RULE_TOKENS = (
    "DATE",
    "EXPIR",
    "PRESENTATION-PERIOD",
    "PRESENTATION_PERIOD",
    "LATE-SHIPMENT",
    "LATE_SHIPMENT",
    "STALE",
)

# field-path tokens that mark a finding as date-class
_DATE_FIELD_HINTS = ("date", "expiry", "period")

# ``doc.field`` references inside expected/found/message text
_FIELD_PATH_RE = re.compile(r"\b([a-z][a-z_]+)\.([a-z][a-z_]+)\b")

# doc-name fragments inside rule ids (CROSSDOC-INV-MATH-001 → invoice)
_RULE_DOC_TOKENS = {
    "-INV-": "invoice",
    "-INVOICE-": "invoice",
    "-BL-": "bl",
    "-PKL-": "packing_list",
    "-PL-": "packing_list",
    "-INS-": "insurance_doc",
    "-COO-": "coo",
    "-LC-": "lc",
}

_DOC_NORMALIZE = {
    "commercial_invoice": "invoice",
    "invoice": "invoice",
    "bill_of_lading": "bl",
    "bl": "bl",
    "marine_bl": "bl",
    "lc": "lc",
    "credit": "lc",
    "letter_of_credit": "lc",
    "packing_list": "packing_list",
    "certificate_of_origin": "coo",
    "coo": "coo",
    "insurance": "insurance_doc",
    "insurance_certificate": "insurance_doc",
    "insurance_policy": "insurance_doc",
    "insurance_doc": "insurance_doc",
    "inspection": "inspection",
    "inspection_certificate": "inspection",
    "beneficiary_cert": "beneficiary_cert",
    "beneficiary_certificate": "beneficiary_cert",
    "draft": "draft",
    "draft_bill_of_exchange": "draft",
}


def _rule_of(finding: Dict[str, Any]) -> str:
    return str(finding.get("rule") or finding.get("rule_id") or "").upper()


def _text_of(finding: Dict[str, Any]) -> str:
    parts = [
        finding.get("title"),
        finding.get("message"),
        finding.get("expected"),
        finding.get("actual"),
        finding.get("found"),
    ]
    return " ".join(str(p) for p in parts if p).lower()


def _field_paths_of(finding: Dict[str, Any]) -> Set[Tuple[str, str]]:
    paths: Set[Tuple[str, str]] = set()
    for doc, fld in _FIELD_PATH_RE.findall(_text_of(finding)):
        norm = _DOC_NORMALIZE.get(doc)
        if norm:
            paths.add((norm, fld))
    return paths


def _docs_of(finding: Dict[str, Any]) -> Set[str]:
    docs: Set[str] = set()
    for key in ("documents", "document_names", "documents_involved"):
        val = finding.get(key)
        if isinstance(val, list):
            for d in val:
                norm = _DOC_NORMALIZE.get(str(d).strip().lower())
                if norm:
                    docs.add(norm)
    for doc, _fld in _field_paths_of(finding):
        if doc != "lc":  # the LC appears in nearly every crossdoc message
            docs.add(doc)
    rule = _rule_of(finding)
    for token, doc in _RULE_DOC_TOKENS.items():
        if token in rule and doc != "lc":
            docs.add(doc)
    return docs


def _date_fields_of(finding: Dict[str, Any]) -> Set[str]:
    fields: Set[str] = set()
    for _doc, fld in _field_paths_of(finding):
        if any(h in fld for h in _DATE_FIELD_HINTS):
            fields.add(fld)
    return fields


def classify_finding(finding: Dict[str, Any]) -> str:
    """Coarse finding-class for authority routing.

    v1 classifies only the two classes where the deterministic layer is
    unconditionally authoritative (arithmetic, dates). Presence and
    semantic classes land with items 4/5.
    """
    if not isinstance(finding, dict):
        return "other"
    rule = _rule_of(finding)
    if any(t in rule for t in _ARITHMETIC_RULE_TOKENS):
        return "arithmetic"
    text = _text_of(finding)
    if any(h in text for h in _ARITHMETIC_TEXT_HINTS):
        return "arithmetic"
    if any(t in rule for t in _DATE_RULE_TOKENS):
        return "dates"
    if _date_fields_of(finding):
        return "dates"
    return "other"


# ---------------------------------------------------------------------------
# Reconciliation
# ---------------------------------------------------------------------------


def reconcile_findings(
    ai_findings: List[Dict[str, Any]],
    det_findings: List[Dict[str, Any]],
    events_out: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Drop AI copies of mechanical facts the deterministic layer already
    raised. Returns the surviving AI list; det findings are never touched
    here (deterministic is authoritative for these classes).

    Every drop emits an ``authority_dedup`` event — when both layers
    raise the same mechanical fact they AGREE, and the dedup simply
    picks the authoritative copy. The event trail still matters: it
    shows the redundancy is alive (the backstop fired) without
    double-billing the customer's finding list.
    """
    det_facts: List[Tuple[str, Set[str], Set[str], Dict[str, Any]]] = []
    for det in det_findings:
        if not isinstance(det, dict):
            continue
        cls = classify_finding(det)
        if cls in ("arithmetic", "dates"):
            det_facts.append((cls, _docs_of(det), _date_fields_of(det), det))

    if not det_facts:
        return list(ai_findings)

    def _emit(event: Dict[str, Any]) -> None:
        if events_out is not None:
            events_out.append(event)
        logger.info("authority_veto_event %s", json.dumps(event, default=str))

    kept: List[Dict[str, Any]] = []
    for ai in ai_findings:
        if not isinstance(ai, dict):
            kept.append(ai)
            continue
        cls = classify_finding(ai)
        if cls not in ("arithmetic", "dates"):
            kept.append(ai)
            continue
        ai_docs = _docs_of(ai)
        ai_date_fields = _date_fields_of(ai)
        winner: Optional[Dict[str, Any]] = None
        for det_cls, det_docs, det_date_fields, det in det_facts:
            if det_cls != cls:
                continue
            if not (ai_docs & det_docs):
                continue
            if cls == "dates" and ai_date_fields and det_date_fields and not (
                ai_date_fields & det_date_fields
            ):
                continue
            winner = det
            break
        if winner is None:
            kept.append(ai)
            continue
        _emit({
            "event": "authority_dedup",
            "class": cls,
            "dropped_source": "ai",
            "dropped_rule": ai.get("rule") or ai.get("rule_id"),
            "dropped_title": str(ai.get("title") or ai.get("message") or "")[:160],
            "kept_rule": winner.get("rule") or winner.get("rule_id"),
            "kept_title": str(winner.get("title") or winner.get("message") or "")[:160],
            "reason": f"deterministic engine is authoritative for {cls} facts",
        })
    return kept
