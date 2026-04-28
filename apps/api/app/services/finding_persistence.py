"""Persist validation findings as Discrepancy rows — Phase A2.

The validation pipeline (AI Examiner → RulHub → Opus veto) emits a
flat list of finding dicts. The frontend's discrepancy-action endpoints
(``/api/discrepancies/{id}/resolve``, ``/comment``, ``/repaper``) key
on ``Discrepancy.id`` UUID. This module bridges the two: every dedup'd
finding gets a backing ``Discrepancy`` row, and the finding dict is
tagged in-place with ``__discrepancy_uuid`` so downstream issue-card
construction can render the UUID as the card's stable id.

Idempotent by ``(validation_session_id, rule_name, field_name,
primary_document)``. Re-running validation on the same session updates
mutable fields (severity, description, expected/actual) on existing
rows rather than duplicating.

Caller responsibility: ``db.flush()`` after this returns to populate
ids; commit is the caller's.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy.orm import Session

from ..models import Discrepancy, ValidationSession

logger = logging.getLogger(__name__)


_RULE_NAME_MAX = 100
_FIELD_NAME_MAX = 100
_DESC_MAX_FOR_SIG = 60  # only used to synthesize a rule when none provided
_VALUE_MAX = 500
_DEFAULT_SEVERITY = "major"
_DEFAULT_TYPE = "validation_finding"


def _slug(text: str, max_len: int) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "-", text or "").strip("-").upper()
    return cleaned[:max_len] or "FINDING"


def _coerce_str(value: Any, max_len: int) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        value = ", ".join(str(v) for v in value if v is not None)
    text = str(value).strip()
    if not text:
        return None
    return text[:max_len]


def _primary_document(finding: Dict[str, Any]) -> Optional[str]:
    for key in ("document_name", "document"):
        v = finding.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()[:100]
    for key in ("document_names", "documents"):
        v = finding.get(key)
        if isinstance(v, list) and v:
            first = v[0]
            if isinstance(first, str) and first.strip():
                return first.strip()[:100]
    return None


def _source_doc_types(finding: Dict[str, Any]) -> Optional[List[str]]:
    candidates: List[str] = []
    for key in ("document_types", "documentTypes", "documents", "document_names"):
        v = finding.get(key)
        if isinstance(v, list):
            for item in v:
                if isinstance(item, str) and item.strip():
                    candidates.append(item.strip())
    if not candidates:
        single = finding.get("document_type") or finding.get("documentType")
        if isinstance(single, str) and single.strip():
            candidates.append(single.strip())
    if not candidates:
        return None
    seen: set[str] = set()
    out: List[str] = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def _rule_name_for(finding: Dict[str, Any]) -> str:
    raw = finding.get("rule") or finding.get("rule_id") or finding.get("ruleId")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()[:_RULE_NAME_MAX]
    title = finding.get("title") or finding.get("message") or finding.get("description") or ""
    return _slug(title[:_DESC_MAX_FOR_SIG], _RULE_NAME_MAX)


def _discrepancy_type_for(finding: Dict[str, Any]) -> str:
    explicit = finding.get("discrepancy_type") or finding.get("type")
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip()[:50]
    layer = finding.get("source_layer") or finding.get("ruleset_domain")
    if isinstance(layer, str) and layer.strip():
        return layer.strip().split(".")[-1][:50] or _DEFAULT_TYPE
    return _DEFAULT_TYPE


def _description_for(finding: Dict[str, Any]) -> str:
    for key in ("message", "description", "explanation", "title"):
        v = finding.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return "Validation finding"


def _severity_for(finding: Dict[str, Any]) -> str:
    raw = finding.get("severity")
    if isinstance(raw, str) and raw.strip():
        norm = raw.strip().lower()
        if norm in ("critical", "major", "minor"):
            return norm
        if norm in ("high", "fail", "reject", "blocked"):
            return "critical"
        if norm in ("medium", "warn", "warning"):
            return "major"
        if norm in ("low", "info"):
            return "minor"
    return _DEFAULT_SEVERITY


def _signature(
    finding: Dict[str, Any],
) -> tuple[str, Optional[str], Optional[str]]:
    rule = _rule_name_for(finding)
    field = _coerce_str(finding.get("field_name") or finding.get("field"), _FIELD_NAME_MAX)
    doc = _primary_document(finding)
    return (rule, field, doc)


def persist_findings_as_discrepancies(
    db: Session,
    validation_session: ValidationSession,
    findings: Iterable[Dict[str, Any]],
) -> int:
    """Upsert one Discrepancy row per finding; tag each finding with
    ``__discrepancy_uuid``.

    Returns count of rows touched (inserted or updated).

    Mutates the finding dicts in-place. Empty/None entries in
    ``findings`` are skipped silently.
    """
    if validation_session is None:
        return 0
    finding_list = [f for f in (findings or []) if isinstance(f, dict)]
    if not finding_list:
        return 0

    session_id = validation_session.id
    existing = (
        db.query(Discrepancy)
        .filter(Discrepancy.validation_session_id == session_id)
        .all()
    )
    by_sig: Dict[tuple[str, Optional[str], Optional[str]], Discrepancy] = {}
    for row in existing:
        # Use the row's own columns to rebuild the same signature shape.
        # Existing rows from prior runs (or from legacy rules/engine.py)
        # will be matched here and re-used rather than duplicated.
        sig = (
            (row.rule_name or "")[:_RULE_NAME_MAX],
            (row.field_name or None),
            None,  # primary doc not stored on the model — match on (rule, field) only
        )
        # Collapse the doc-component for lookup against findings; we
        # match by (rule, field) ignoring doc to maximize re-use of
        # existing rows. Conflicts (same rule+field across docs) get
        # collapsed onto one row, which is the desired behavior — the
        # frontend lists doc names inside the card, not multiplexes.
        by_sig[sig] = row

    touched = 0
    for finding in finding_list:
        rule, field, doc = _signature(finding)
        lookup_sig = (rule, field, None)
        row = by_sig.get(lookup_sig)
        is_new = row is None
        if is_new:
            row = Discrepancy(
                validation_session_id=session_id,
                discrepancy_type=_discrepancy_type_for(finding),
                rule_name=rule,
                field_name=field,
                description=_description_for(finding),
                severity=_severity_for(finding),
                expected_value=_coerce_str(
                    finding.get("expected") or finding.get("expected_value"),
                    _VALUE_MAX,
                ),
                actual_value=_coerce_str(
                    finding.get("actual")
                    or finding.get("found")
                    or finding.get("actual_value"),
                    _VALUE_MAX,
                ),
                source_document_types=_source_doc_types(finding),
            )
            db.add(row)
            by_sig[lookup_sig] = row
        else:
            # Update mutable fields. Don't touch state/owner_user_id —
            # those carry user-resolution context the pipeline can't override.
            row.discrepancy_type = _discrepancy_type_for(finding)
            row.description = _description_for(finding)
            row.severity = _severity_for(finding)
            row.expected_value = _coerce_str(
                finding.get("expected") or finding.get("expected_value"),
                _VALUE_MAX,
            )
            row.actual_value = _coerce_str(
                finding.get("actual")
                or finding.get("found")
                or finding.get("actual_value"),
                _VALUE_MAX,
            )
            row.source_document_types = _source_doc_types(finding) or row.source_document_types

        touched += 1
        # Flush only if we need the id and it's still None (new row,
        # autogen not yet executed). Keep flushes minimal — caller
        # batches the final flush.
        if row.id is None:
            db.flush([row])
        finding["__discrepancy_uuid"] = str(row.id)

    logger.info(
        "Persisted %d findings as Discrepancy rows for session %s (%d existing reused)",
        touched,
        session_id,
        len(existing),
    )
    return touched


__all__ = ["persist_findings_as_discrepancies"]
