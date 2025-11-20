from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.rules_audit import RuleAudit


def record_rule_audit(
    db: Session,
    *,
    action: str,
    rule_id: Optional[str] = None,
    ruleset_id: Optional[UUID] = None,
    actor_id: Optional[UUID] = None,
    detail: Optional[Dict[str, Any]] = None,
) -> None:
    """Persist an audit entry describing a rule mutation."""
    entry = RuleAudit(
        rule_id=rule_id,
        ruleset_id=ruleset_id,
        action=action,
        actor_id=actor_id,
        detail=detail,
    )
    db.add(entry)

