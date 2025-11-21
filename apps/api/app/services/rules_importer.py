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
    skipped_existing: int = 0
    skipped: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "total_rules": self.total_rules,
            "inserted": self.inserted,
            "updated": self.updated,
            "skipped_existing": self.skipped_existing,
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
        """
        Safe importer:
        - DRAFT upload: Do NOT overwrite existing rules.
        - PUBLISH/ROLLBACK: Update or insert rules, then activate them.
        """
        summary = RulesImportSummary(total_rules=0)
        
        ruleset_id = getattr(ruleset, "id", None)
        if not ruleset_id:
            raise ValueError("Ruleset ID is required")

        for rule_data in rules_payload:
            summary.total_rules += 1

            # Required fields
            rule_id = rule_data.get("rule_id")
            if not rule_id:
                summary.errors.append("Missing rule_id")
                summary.skipped += 1
                continue

            # Lookup existing rule by rule_id
            existing = (
                self.db.query(RuleRecord)
                .filter(RuleRecord.rule_id == rule_id)
                .first()
            )

            # CASE 1 — DRAFT UPLOAD: do NOT overwrite existing
            if not activate:
                if existing:
                    summary.skipped_existing += 1
                    continue  # skip updates entirely

                # Insert new draft rule
                try:
                    new_rule = self._create_rule_model(rule_data, ruleset_id, activate, ruleset)
                    self.db.add(new_rule)
                    summary.inserted += 1
                except Exception as e:
                    summary.errors.append(f"{rule_id}: {str(e)}")
                    summary.skipped += 1
                continue

            # CASE 2 — ACTIVATE (PUBLISH/ROLLBACK)
            if activate:
                try:
                    if existing:
                        # Update existing rule
                        self._update_rule_model(existing, rule_data, ruleset_id)
                        summary.updated += 1
                    else:
                        # Insert new rule
                        new_rule = self._create_rule_model(rule_data, ruleset_id, activate, ruleset)
                        self.db.add(new_rule)
                        summary.inserted += 1
                except Exception as e:
                    summary.errors.append(f"{rule_id}: {str(e)}")
                    summary.skipped += 1
                    continue

        # After processing all rules:
        if activate:
            # Mark all rules in this ruleset as active
            (
                self.db.query(RuleRecord)
                .filter(RuleRecord.ruleset_id == ruleset_id)
                .update({RuleRecord.is_active: True}, synchronize_session=False)
            )

            # Mark previously-active rules as inactive
            (
                self.db.query(RuleRecord)
                .filter(RuleRecord.ruleset_id != ruleset_id)
                .filter(RuleRecord.is_active == True) # Only update currently active ones
                .update({RuleRecord.is_active: False}, synchronize_session=False)
            )

        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to commit rules import: {e}")
            raise

        record_rule_audit(
            self.db,
            action="import",
            rule_id=None,
            ruleset_id=ruleset_id,
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

    def _create_rule_model(self, data: Dict[str, Any], ruleset_id: UUID, activate: bool, ruleset: Ruleset) -> RuleRecord:
        checksum = self._compute_checksum(data)
        
        # Default title to rule_id if missing
        title = (data.get("title") or data.get("rule_id") or "Untitled Rule").strip()
        
        return RuleRecord(
            rule_id=data["rule_id"],
            rule_version=data.get("rule_version") or data.get("version"),
            article=data.get("article"),
            version=ruleset.rulebook_version, # Use ruleset's rulebook version
            domain=data.get("domain") or ruleset.domain or "icc",
            jurisdiction=data.get("jurisdiction") or ruleset.jurisdiction or "global",
            document_type=data.get("document_type", "lc"),
            rule_type=data.get("rule_type", "deterministic"),
            severity=data.get("severity", "fail"),
            deterministic=bool(data.get("deterministic", True)),
            requires_llm=bool(data.get("requires_llm", False)),
            title=title,
            reference=data.get("reference"),
            description=data.get("description"),
            conditions=data.get("conditions", []),
            expected_outcome=data.get("expected_outcome", {}),
            tags=data.get("tags", []),
            rule_metadata=data.get("metadata", {}), # Mapped to rule_metadata column
            checksum=checksum,
            ruleset_id=ruleset_id,
            ruleset_version=ruleset.ruleset_version,
            is_active=activate,
        )

    def _update_rule_model(self, model: RuleRecord, data: Dict[str, Any], ruleset_id: UUID):
        model.rule_version = data.get("rule_version") or data.get("version")
        model.article = data.get("article")
        # model.version updated from ruleset usually, but here we keep existing or update if we want
        # The provided snippet update logic:
        model.version = data.get("version", model.version)
        
        model.domain = data.get("domain", model.domain)
        model.jurisdiction = data.get("jurisdiction", model.jurisdiction)
        model.document_type = data.get("document_type", model.document_type)
        model.rule_type = data.get("rule_type", model.rule_type)
        model.severity = data.get("severity", model.severity)
        model.deterministic = bool(data.get("deterministic", model.deterministic))
        model.requires_llm = bool(data.get("requires_llm", model.requires_llm))
        model.title = data.get("title") or model.title
        model.reference = data.get("reference", model.reference)
        model.description = data.get("description", model.description)
        model.conditions = data.get("conditions", model.conditions)
        model.expected_outcome = data.get("expected_outcome", model.expected_outcome)
        model.tags = data.get("tags", model.tags)
        model.rule_metadata = data.get("metadata", model.rule_metadata) # Mapped to rule_metadata
        model.checksum = self._compute_checksum(data)
        model.ruleset_id = ruleset_id

    def _compute_checksum(self, rule_data: Dict[str, Any]) -> str:
        return hashlib.md5(
            json.dumps(rule_data, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        ).hexdigest()
