"""Normalize source-module findings without replacing source details."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from sqlalchemy.orm import Session

from app.models import ProoflineFinding, TradeCase, TradeCaseCheckRun


SEVERITY_MAP = {
    "critical": "critical",
    "blocker": "critical",
    "error": "high",
    "major": "high",
    "high": "high",
    "warning": "medium",
    "medium": "medium",
    "minor": "low",
    "low": "low",
    "info": "info",
    "informational": "info",
}


def _first(source: Mapping[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        value = source.get(key)
        if value is not None and value != "":
            return value
    return default


def _stable_source_id(module: str, source: Mapping[str, Any]) -> str:
    explicit = _first(source, "source_finding_id", "id", "rule", "rule_id")
    if explicit is not None:
        return str(explicit)
    material = json.dumps(
        {
            "module": module,
            "title": source.get("title"),
            "category": source.get("category"),
            "document": source.get("document_id"),
            "field": source.get("field") or source.get("affected_field"),
        },
        sort_keys=True,
        default=str,
    ).encode("utf-8")
    return f"{module.upper()}-{hashlib.sha256(material).hexdigest()[:16]}"


def _uuid_or_none(value: Any) -> Optional[uuid.UUID]:
    if value is None:
        return None
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        return None


def normalize_source_finding(module: str, source: Mapping[str, Any]) -> dict[str, Any]:
    source_id = _stable_source_id(module, source)
    severity = SEVERITY_MAP.get(str(source.get("severity") or "medium").lower(), "medium")
    expected = _first(
        source,
        "expected",
        "expected_value",
        "requirement",
        default="Not provided by source module",
    )
    observed = _first(
        source,
        "observed",
        "actual",
        "found",
        "actual_value",
        default="Not provided by source module",
    )
    correction = _first(
        source,
        "suggested_correction",
        "suggestion",
        "suggested_fix",
        "remediation",
        default="Review and resolve this finding with an analyst.",
    )
    title = str(_first(source, "title", "rule_name", default="Source module finding"))
    explanation = str(
        _first(source, "explanation", "description", "message", default=title)
    )

    return {
        "source_module": module,
        "source_finding_id": source_id,
        "source_detail_reference": {
            "source_module": module,
            "source_finding_id": source_id,
            "source_keys": sorted(str(key) for key in source.keys()),
        },
        "category": str(source.get("category") or "source_finding"),
        "severity": severity,
        "title": title,
        "explanation": explanation,
        "affected_entity": _first(source, "affected_entity", "entity", "document_name"),
        "affected_document_id": _uuid_or_none(
            _first(source, "affected_document_id", "document_id")
        ),
        "affected_field": _first(source, "affected_field", "field", "field_name"),
        "expected": str(expected),
        "observed": str(observed),
        "suggested_correction": str(correction),
        "rule_reference": source.get("rule_reference"),
        "evidence_references": list(source.get("evidence_references") or []),
        "is_automated": bool(source.get("automated", True)),
        "visibility": str(source.get("visibility") or "customer"),
        "status": str(source.get("status") or "open"),
        "reviewer_decision": source.get("reviewer_decision"),
    }


def upsert_normalized_finding(
    db: Session,
    *,
    trade_case: TradeCase,
    check_run: TradeCaseCheckRun,
    module: str,
    source: Mapping[str, Any],
) -> ProoflineFinding:
    values = normalize_source_finding(module, source)
    existing = (
        db.query(ProoflineFinding)
        .filter(
            ProoflineFinding.trade_case_id == trade_case.id,
            ProoflineFinding.source_module == module,
            ProoflineFinding.source_finding_id == values["source_finding_id"],
        )
        .first()
    )
    if existing is not None:
        for key, value in values.items():
            setattr(existing, key, value)
        existing.check_run_id = check_run.id
        existing.updated_at = datetime.now(timezone.utc)
        return existing

    finding = ProoflineFinding(
        id=uuid.uuid4(),
        company_id=trade_case.company_id,
        trade_case_id=trade_case.id,
        check_run_id=check_run.id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        **values,
    )
    db.add(finding)
    return finding


__all__ = ["normalize_source_finding", "upsert_normalized_finding"]

