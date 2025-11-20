from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence
from uuid import UUID

from sqlalchemy import literal_column
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.ruleset import Ruleset, RulesetStatus
from app.models.rule_record import RuleRecord
from app.metrics.rules_metrics import rules_import_total
from app.services.rules_audit import record_rule_audit

logger = logging.getLogger(__name__)


@dataclass
class RulesImportSummary:
    """Structured response describing the outcome of an import attempt."""

    total_rules: int
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "total_rules": self.total_rules,
            "inserted": self.inserted,
            "updated": self.updated,
            "skipped": self.skipped,
            "errors": self.errors,
            "warnings": self.warnings,
        }


class RulesImporter:
    """Normalize ruleset JSON into the governance-ready `rules` table."""

    def __init__(self, db: Session):
        self.db = db

    def import_ruleset(
        self,
        *,
        ruleset: Ruleset,
        rules_payload: Sequence[Dict[str, Any]],
        activate: bool = False,
        actor_id: Optional[UUID] = None,
    ) -> RulesImportSummary:
        summary = RulesImportSummary(total_rules=len(rules_payload))

        for index, rule in enumerate(rules_payload, start=1):
            try:
                normalized = self._normalize_rule(
                    rule=rule,
                    ruleset=ruleset,
                    activate=activate,
                )
            except ValueError as exc:
                message = f"Rule #{index} ({rule.get('rule_id', 'unknown')}): {exc}"
                logger.warning(message)
                summary.errors.append(message)
                summary.skipped += 1
                continue

            stmt = (
                insert(RuleRecord.__table__)
                .values(**normalized)
                .returning(
                    RuleRecord.rule_id,
                    literal_column("xmax = 0").label("inserted"),
                )
            )
            conflict_update = normalized.copy()
            conflict_update.pop("rule_id", None)
            stmt = stmt.on_conflict_do_update(
                index_elements=["rule_id"],
                set_=conflict_update,
            )

            row = self.db.execute(stmt).first()

            if row and getattr(row, "inserted", False):
                summary.inserted += 1
            else:
                summary.updated += 1

        record_rule_audit(
            self.db,
            action="import",
            rule_id=None,
            ruleset_id=getattr(ruleset, "id", None),
            actor_id=actor_id,
            detail={
                "activate": activate,
                "summary": summary.as_dict(),
                "ruleset_version": getattr(ruleset, "ruleset_version", None),
                "rulebook_version": getattr(ruleset, "rulebook_version", None),
            },
        )
        result_label = "success" if not summary.errors else "partial"
        rules_import_total.labels(
            action="activate" if activate else "sync",
            result=result_label,
        ).inc(summary.inserted + summary.updated)

        return summary

    def _normalize_rule(
        self,
        *,
        rule: Dict[str, Any],
        ruleset: Ruleset,
        activate: bool,
    ) -> Dict[str, Any]:
        rule_id = (rule.get("rule_id") or "").strip()
        if not rule_id:
            raise ValueError("rule_id is required")

        title = (rule.get("title") or "").strip()
        if not title:
            raise ValueError("title is required")

        domain = (rule.get("domain") or ruleset.domain or "icc").strip()
        jurisdiction = (rule.get("jurisdiction") or ruleset.jurisdiction or "global").strip()
        document_type = (rule.get("document_type") or "lc").strip()

        severity = (rule.get("severity") or "fail").strip()
        deterministic = bool(rule.get("deterministic", True))
        requires_llm = bool(rule.get("requires_llm", False))

        conditions = rule.get("conditions") or []
        if not isinstance(conditions, list):
            raise ValueError("conditions must be an array")

        expected_outcome = rule.get("expected_outcome") or {}
        if not isinstance(expected_outcome, dict):
            raise ValueError("expected_outcome must be an object")
        expected_outcome.setdefault("valid", [])
        expected_outcome.setdefault("invalid", [])

        tags = rule.get("tags") or []
        if isinstance(tags, str):
            tags = [tags]
        elif not isinstance(tags, list):
            raise ValueError("tags must be an array or string")

        metadata = {
            key: value
            for key, value in {
                "documents": rule.get("documents"),
                "supplements": rule.get("supplements"),
                "notes": rule.get("notes"),
                "source": rule.get("source"),
            }.items()
            if value
        }

        checksum = hashlib.md5(
            json.dumps(rule, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        ).hexdigest()

        rule_version = rule.get("rule_version") or rule.get("version")
        rulebook_version = ruleset.rulebook_version

        is_active = activate and ruleset.status == RulesetStatus.ACTIVE.value

        return {
            "rule_id": rule_id,
            "rule_version": rule_version,
            "article": rule.get("article"),
            "version": rulebook_version,
            "domain": domain,
            "jurisdiction": jurisdiction,
            "document_type": document_type,
            "rule_type": rule.get("rule_type") or ("deterministic" if deterministic else "semantic"),
            "severity": severity,
            "deterministic": deterministic,
            "requires_llm": requires_llm,
            "title": title,
            "reference": rule.get("reference"),
            "description": rule.get("description"),
            "conditions": conditions,
            "expected_outcome": expected_outcome,
            "tags": tags,
            "metadata": metadata,
            "checksum": checksum,
            "ruleset_id": getattr(ruleset, "id", None),
            "ruleset_version": ruleset.ruleset_version,
            "is_active": is_active,
            "archived_at": None if is_active else None,
        }

