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


# ``'doc.field' (missing)`` and ``Required field 'doc.field' is missing``
_MISSING_PAREN_RE = re.compile(r"'([a-z][a-z_]+)\.([a-z][a-z_]+)'\s*\(missing\)")
_MISSING_REQUIRED_RE = re.compile(r"required field\s+'([a-z][a-z_]+)\.([a-z][a-z_]+)'\s+is missing")

# field tokens that mark a comparison as semantic (party identity, goods
# wording, addresses) — judgment territory under ISBP, not strict equality
_SEMANTIC_FIELD_TOKENS = (
    "applicant",
    "beneficiary",
    "buyer",
    "seller",
    "consignee",
    "shipper",
    "notify",
    "exporter",
    "importer",
    "issuer_name",
    "insured",
    "goods",
    "description",
    "address",
)


def missing_refs(finding: Dict[str, Any]) -> Set[Tuple[str, str]]:
    """(doc, field) pairs the finding claims are missing from the payload."""
    text = _text_of(finding)
    refs: Set[Tuple[str, str]] = set()
    for doc, fld in _MISSING_PAREN_RE.findall(text):
        norm = _DOC_NORMALIZE.get(doc)
        if norm:
            refs.add((norm, fld))
    for doc, fld in _MISSING_REQUIRED_RE.findall(text):
        norm = _DOC_NORMALIZE.get(doc)
        if norm:
            refs.add((norm, fld))
    return refs


def _semantic_fields_of(finding: Dict[str, Any]) -> Set[str]:
    fields: Set[str] = set()
    for _doc, fld in _field_paths_of(finding):
        if any(t in fld for t in _SEMANTIC_FIELD_TOKENS):
            fields.add(fld)
    return fields


def classify_finding(finding: Dict[str, Any]) -> str:
    """Coarse finding-class for authority routing.

    Classes: arithmetic | presence_payload | dates | semantic | other.
    Order matters — an explicit "(missing)" marker beats everything but
    arithmetic, because a missing-from-payload claim is a presence
    problem regardless of which field is missing.
    """
    if not isinstance(finding, dict):
        return "other"
    rule = _rule_of(finding)
    if any(t in rule for t in _ARITHMETIC_RULE_TOKENS):
        return "arithmetic"
    text = _text_of(finding)
    if any(h in text for h in _ARITHMETIC_TEXT_HINTS):
        return "arithmetic"
    if missing_refs(finding):
        return "presence_payload"
    if any(t in rule for t in _DATE_RULE_TOKENS):
        return "dates"
    if _date_fields_of(finding):
        return "dates"
    if _semantic_fields_of(finding):
        return "semantic"
    return "other"


# ---------------------------------------------------------------------------
# Reconciliation
# ---------------------------------------------------------------------------


def build_extracted_lookup(doc_payload: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Canonical doc-name → raw extracted-field dict, from the merged
    per-doc payload (db_rule_payload shape: source-doc-key → dict)."""
    lookup: Dict[str, Dict[str, Any]] = {}
    if not isinstance(doc_payload, dict):
        return lookup
    for src_key, doc in doc_payload.items():
        if not isinstance(doc, dict) or not doc:
            continue
        canon = _DOC_NORMALIZE.get(str(src_key).strip().lower())
        if not canon:
            continue
        merged = lookup.setdefault(canon, {})
        for k, v in doc.items():
            if v not in (None, "", [], {}):
                merged.setdefault(str(k).lower(), v)
    return lookup


_FIELD_SUFFIXES = ("_name", "_code", "_number", "_no", "_type")


def _field_token(field: str) -> str:
    token = field.lower()
    for suffix in _FIELD_SUFFIXES:
        if token.endswith(suffix):
            token = token[: -len(suffix)]
            break
    return token


def _extraction_has_field(extracted: Dict[str, Any], field: str) -> Optional[str]:
    """Key under which extraction captured ``field``, or None.

    Token match: ``carrier_name`` matches extracted keys containing
    ``carrier``; ``currency_code`` matches ``currency``. Conservative —
    a token shorter than 4 chars never matches (too many collisions).
    """
    token = _field_token(field)
    if len(token) < 4:
        return None
    if field.lower() in extracted:
        return field.lower()
    for key in extracted:
        if token in key:
            return key
    return None


def screen_presence_findings(
    det_findings: List[Dict[str, Any]],
    extracted_lookup: Dict[str, Dict[str, Any]],
    events_out: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Authority-matrix presence cell (item 4): rules win on payload
    presence — but when a finding says ``doc.field (missing)`` and the
    extraction layer DID capture that field, the "missing" is our own
    payload plumbing (alias drift), not the customer's discrepancy.

    Mid-pipeline re-extraction is impossible (uploads are processed in
    memory and never persisted), and unnecessary here: the extracted
    payload IS the record of what extraction saw. A finding whose every
    missing-claim is contradicted by extraction is demoted to advisory
    (verdict-neutral) with an authority_presence_conflict event naming
    the alias gap — the free to-fix list for the RulHub field mapper.
    Findings with any genuinely-missing ref keep their severity.
    """
    def _emit(event: Dict[str, Any]) -> None:
        if events_out is not None:
            events_out.append(event)
        logger.info("authority_veto_event %s", json.dumps(event, default=str))

    out: List[Dict[str, Any]] = []
    for det in det_findings:
        if not isinstance(det, dict) or classify_finding(det) != "presence_payload":
            out.append(det)
            continue
        refs = missing_refs(det)
        # lc-side refs are checked too when the LC context is in the lookup
        contradicted: List[Tuple[str, str, str]] = []
        genuinely_missing = False
        for doc, field in refs:
            extracted = extracted_lookup.get(doc) or {}
            key = _extraction_has_field(extracted, field) if extracted else None
            if key:
                contradicted.append((doc, field, key))
            else:
                genuinely_missing = True
        if contradicted and not genuinely_missing:
            det = dict(det)
            original_severity = det.get("severity")
            det["severity"] = "advisory"
            det["needs_review"] = True
            det["_authority_presence_conflict"] = [
                {"doc": d, "field": f, "extracted_under": k} for d, f, k in contradicted
            ]
            _emit({
                "event": "authority_presence_conflict",
                "rule": det.get("rule") or det.get("rule_id"),
                "title": str(det.get("title") or det.get("message") or "")[:160],
                "severity_from": original_severity,
                "severity_to": "advisory",
                "contradicted": [
                    {"doc": d, "field": f, "extracted_under": k}
                    for d, f, k in contradicted
                ],
                "reason": "extraction captured the field the rules payload lacked — alias gap, not a discrepancy",
            })
        out.append(det)
    return out


def _normalize_comparable(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", " ", value.upper()).strip()


def _concrete_values_of(finding: Dict[str, Any]) -> Optional[Tuple[str, str]]:
    """Both comparison values when the finding carries the
    ``<path> = <value>`` two-sided shape; None otherwise."""
    exp = str(finding.get("expected") or "").strip()
    found = str(finding.get("found") or finding.get("actual") or "").strip()
    if "=" not in exp or "=" not in found:
        return None
    a = exp.split("=", 1)[1].strip()
    b = found.split("=", 1)[1].strip()
    if not a or not b:
        return None
    return a, b


def screen_semantic_findings(
    det_findings: List[Dict[str, Any]],
    events_out: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Authority-matrix semantic cell (item 5): party identity / goods
    wording is judgment territory — strict equality over-flags. The
    deterministic near-match demotion: when one side is contained in
    the other after normalization (name vs name-with-address, LC goods
    text vs invoice's fuller description — ISBP allows both), demote to
    advisory with an ai-assessed/needs-review label. Real mismatches
    (no containment) keep their severity and go to the veto for
    judgment instead of auto-confirming.
    """
    def _emit(event: Dict[str, Any]) -> None:
        if events_out is not None:
            events_out.append(event)
        logger.info("authority_veto_event %s", json.dumps(event, default=str))

    out: List[Dict[str, Any]] = []
    for det in det_findings:
        if not isinstance(det, dict) or classify_finding(det) != "semantic":
            out.append(det)
            continue
        values = _concrete_values_of(det)
        if not values:
            out.append(det)
            continue
        a, b = (_normalize_comparable(values[0]), _normalize_comparable(values[1]))
        shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
        if len(shorter) >= 8 and shorter in longer:
            det = dict(det)
            original_severity = det.get("severity")
            det["severity"] = "advisory"
            det["ai_assessed"] = True
            det["needs_review"] = True
            _emit({
                "event": "authority_semantic_demote",
                "rule": det.get("rule") or det.get("rule_id"),
                "title": str(det.get("title") or det.get("message") or "")[:160],
                "severity_from": original_severity,
                "severity_to": "advisory",
                "relation": "containment",
                "value_short": shorter[:80],
                "value_long": longer[:120],
                "reason": "one value contains the other after normalization — name-with-address / fuller-description pattern, not a mismatch",
            })
        out.append(det)
    return out


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
