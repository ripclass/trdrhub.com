from __future__ import annotations

"""
One-off audit script for ICC ruleset integrity.

Usage (from apps/api directory):
    python scripts/audit_rules_integrity.py

This script connects using the same SQLAlchemy configuration as the main app
and runs structural integrity checks on:
    - `rulesets` (Ruleset model)
    - `rules` (RuleRecord model)

Focus domains:
    - icc.ucp600
    - icc.eucp2.1
    - icc.urdg758
    - icc.lcopilot.crossdoc
"""

import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.rule_record import RuleRecord
from app.models.ruleset import Ruleset, RulesetStatus


ICC_DOMAINS = [
    "icc.ucp600",
    "icc.eucp2.1",
    "icc.urdg758",
    "icc.lcopilot.crossdoc",
]

# Derived from RuleEvaluator._normalize_condition
KNOWN_CONDITION_TYPES: Set[str] = {
    "enum_value",
    "field_presence",
    "doc_required",
    "equality_match",
    "consistency_check",
    "date_order",
    "numeric_range",
    "time_constraint",
}


class AuditSummary:
    def __init__(self) -> None:
        self.total_icc_rulesets: int = 0
        self.active_icc_rulesets: int = 0
        self.total_icc_rules: int = 0

        self.rulesets_count_mismatch: int = 0
        self.rulesets_active_with_zero_rules: int = 0

        self.rules_missing_fields: int = 0
        self.rules_bad_severity_flags: int = 0
        self.rules_bad_condition_types: int = 0

        self.duplicate_rule_ids_within_ruleset: int = 0
        self.cross_ruleset_collisions: int = 0
        self.orphan_rules: int = 0


def _print_header(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def check_ruleset_rule_counts(session: Session, summary: AuditSummary) -> None:
    """
    A) Ruleset ↔ Rules counts
    """
    _print_header("A) Ruleset ↔ Rules counts")

    rulesets: List[Ruleset] = (
        session.query(Ruleset)
        .filter(Ruleset.domain.in_(ICC_DOMAINS))
        .order_by(Ruleset.domain.asc(), Ruleset.ruleset_version.asc())
        .all()
    )

    summary.total_icc_rulesets = len(rulesets)
    summary.active_icc_rulesets = sum(1 for r in rulesets if r.status == RulesetStatus.ACTIVE.value)

    for rs in rulesets:
        actual_count = (
            session.query(func.count(RuleRecord.rule_id))
            .filter(RuleRecord.ruleset_id == rs.id)
            .scalar()
            or 0
        )
        summary.total_icc_rules += actual_count

        mismatch = rs.rule_count != actual_count
        active_zero = rs.status == RulesetStatus.ACTIVE.value and actual_count == 0

        if mismatch:
            summary.rulesets_count_mismatch += 1
        if active_zero:
            summary.rulesets_active_with_zero_rules += 1

        print(
            f"- ruleset_id={rs.id} "
            f"domain={rs.domain} "
            f"rulebook_version={rs.rulebook_version} "
            f"ruleset_version={rs.ruleset_version} "
            f"status={rs.status} "
            f"rule_count_meta={rs.rule_count} "
            f"actual_count={actual_count} "
            f"{'MISMATCH' if mismatch else ''} "
            f"{'ACTIVE_WITH_ZERO' if active_zero else ''}"
        )


def check_field_completeness(session: Session, summary: AuditSummary) -> None:
    """
    B) Field completeness per rule
    """
    _print_header("B) Field completeness per rule (active ICC rulesets)")
    print("ruleset_domain, rule_id, missing_fields")

    rows: List[Tuple[RuleRecord, Ruleset]] = (
        session.query(RuleRecord, Ruleset)
        .join(Ruleset, RuleRecord.ruleset_id == Ruleset.id)
        .filter(
            Ruleset.status == RulesetStatus.ACTIVE.value,
            Ruleset.domain.in_(ICC_DOMAINS),
        )
        .all()
    )

    for rule, rs in rows:
        missing: List[str] = []

        if not (rule.rule_id and str(rule.rule_id).strip()):
            missing.append("rule_id")
        if not (rule.domain and str(rule.domain).strip()):
            missing.append("domain")
        if not (rule.jurisdiction and str(rule.jurisdiction).strip()):
            missing.append("jurisdiction")
        if not (rule.document_type and str(rule.document_type).strip()):
            missing.append("document_type")
        if not (rule.severity and str(rule.severity).strip()):
            missing.append("severity")
        if not (rule.title and str(rule.title).strip()):
            missing.append("title")

        conditions = rule.conditions
        if not isinstance(conditions, list) or len(conditions) == 0:
            missing.append("conditions")

        expected = rule.expected_outcome or {}
        if not isinstance(expected, dict):
            missing.append("expected_outcome_not_object")
        else:
            valid_present = "valid" in expected and isinstance(expected.get("valid"), list)
            invalid_present = "invalid" in expected and isinstance(expected.get("invalid"), list)
            if not (valid_present or invalid_present):
                missing.append("expected_outcome_missing_valid_and_invalid")

        if missing:
            summary.rules_missing_fields += 1
            print(f"{rs.domain}, {rule.rule_id}, {missing}")


def check_severity_and_flags(session: Session, summary: AuditSummary) -> None:
    """
    C) Severity + flags sanity
    """
    _print_header("C) Severity + deterministic/requires_llm sanity (active ICC rulesets)")
    print("ruleset_domain, rule_id, severity, deterministic, requires_llm, problem")

    rows: List[Tuple[RuleRecord, Ruleset]] = (
        session.query(RuleRecord, Ruleset)
        .join(Ruleset, RuleRecord.ruleset_id == Ruleset.id)
        .filter(
            Ruleset.status == RulesetStatus.ACTIVE.value,
            Ruleset.domain.in_(ICC_DOMAINS),
        )
        .all()
    )

    allowed_severities = {"fail", "warn", "info"}

    for rule, rs in rows:
        problems: List[str] = []

        sev = (rule.severity or "").strip().lower()
        if sev not in allowed_severities:
            problems.append(f"invalid_severity={rule.severity!r}")

        if rule.deterministic is None or not isinstance(rule.deterministic, bool):
            problems.append(f"deterministic_not_boolean={rule.deterministic!r}")

        if rule.requires_llm is None or not isinstance(rule.requires_llm, bool):
            problems.append(f"requires_llm_not_boolean={rule.requires_llm!r}")

        if problems:
            summary.rules_bad_severity_flags += 1
            print(
                f"{rs.domain}, {rule.rule_id}, {rule.severity}, "
                f"{rule.deterministic}, {rule.requires_llm}, {problems}"
            )


def check_condition_types(session: Session, summary: AuditSummary) -> None:
    """
    D) Condition types sanity
    """
    _print_header("D) Condition types sanity (active ICC rulesets)")

    rows: List[Tuple[RuleRecord, Ruleset]] = (
        session.query(RuleRecord, Ruleset)
        .join(Ruleset, RuleRecord.ruleset_id == Ruleset.id)
        .filter(
            Ruleset.status == RulesetStatus.ACTIVE.value,
            Ruleset.domain.in_(ICC_DOMAINS),
        )
        .all()
    )

    all_types_found: Set[Optional[str]] = set()

    for rule, rs in rows:
        conds = rule.conditions or []
        if not isinstance(conds, list):
            continue

        for cond in conds:
            if not isinstance(cond, dict):
                continue
            cond_type = cond.get("type")
            all_types_found.add(cond_type)

            if cond_type is None:
                summary.rules_bad_condition_types += 1
                print(
                    f"{rs.domain}, {rule.rule_id}, missing_type, "
                    f"condition={str(cond)[:200]}"
                )
                continue

            if cond_type not in KNOWN_CONDITION_TYPES:
                summary.rules_bad_condition_types += 1
                print(
                    f"{rs.domain}, {rule.rule_id}, bad_type={cond_type!r}, "
                    f"condition={str(cond)[:200]}"
                )

    print("\nALL condition types found (including None):")
    print(all_types_found)


def check_duplicates_and_collisions(session: Session, summary: AuditSummary) -> None:
    """
    E) Duplicates & collisions
    """
    _print_header("E) Duplicates & collisions")

    # 1) Within same ruleset (by ruleset_id)
    print("\nE1) Duplicate rule_id within the same ruleset:")

    within_dupes = (
        session.query(
            RuleRecord.ruleset_id,
            RuleRecord.rule_id,
            func.count(RuleRecord.rule_id).label("cnt"),
        )
        .join(Ruleset, RuleRecord.ruleset_id == Ruleset.id)
        .filter(Ruleset.domain.in_(ICC_DOMAINS))
        .group_by(RuleRecord.ruleset_id, RuleRecord.rule_id)
        .having(func.count(RuleRecord.rule_id) > 1)
        .all()
    )

    ruleset_by_id: Dict[Any, Ruleset] = {
        rs.id: rs
        for rs in session.query(Ruleset).filter(Ruleset.domain.in_(ICC_DOMAINS)).all()
    }

    for ruleset_id, rule_id, cnt in within_dupes:
        summary.duplicate_rule_ids_within_ruleset += 1
        rs = ruleset_by_id.get(ruleset_id)
        domain = rs.domain if rs else "unknown"
        print(
            f"ruleset_id={ruleset_id}, domain={domain}, rule_id={rule_id}, count={cnt}"
        )

    # 2) Across active rulesets (same domain/jurisdiction/document_type/rule_id)
    print("\nE2) Cross-ruleset collisions (active rulesets, same domain/jurisdiction/document_type/rule_id):")

    rows = (
        session.query(
            RuleRecord.domain,
            RuleRecord.jurisdiction,
            RuleRecord.document_type,
            RuleRecord.rule_id,
            RuleRecord.ruleset_id,
            Ruleset.status,
        )
        .join(Ruleset, RuleRecord.ruleset_id == Ruleset.id)
        .filter(
            Ruleset.status == RulesetStatus.ACTIVE.value,
            Ruleset.domain.in_(ICC_DOMAINS),
        )
        .all()
    )

    groups: Dict[Tuple[str, str, str, str], Set[Any]] = defaultdict(set)
    for domain, jurisdiction, document_type, rule_id, ruleset_id, status in rows:
        key = (domain, jurisdiction, document_type, rule_id)
        groups[key].add(ruleset_id)

    for (domain, jurisdiction, document_type, rule_id), ruleset_ids in groups.items():
        if len(ruleset_ids) > 1:
            summary.cross_ruleset_collisions += 1
            print(
                f"domain={domain}, jurisdiction={jurisdiction}, document_type={document_type}, "
                f"rule_id={rule_id}, ruleset_ids={[str(rid) for rid in ruleset_ids]}"
            )


def check_orphans(session: Session, summary: AuditSummary) -> None:
    """
    F) Orphan rules (no or invalid ruleset_id)
    """
    _print_header("F) Orphan rules (no or invalid ruleset_id)")
    print("rule_id, ruleset_id, domain, document_type")

    # ruleset_id is NULL
    orphans_null = (
        session.query(RuleRecord)
        .filter(RuleRecord.ruleset_id.is_(None))
        .all()
    )

    # ruleset_id points to non-existent ruleset
    orphans_fk = (
        session.query(RuleRecord)
        .outerjoin(Ruleset, RuleRecord.ruleset_id == Ruleset.id)
        .filter(
            RuleRecord.ruleset_id.is_not(None),
            Ruleset.id.is_(None),
        )
        .all()
    )

    for rule in orphans_null + orphans_fk:
        summary.orphan_rules += 1
        print(
            f"{rule.rule_id}, {rule.ruleset_id}, {rule.domain}, {rule.document_type}"
        )


def check_crossdoc_sanity(session: Session, summary: AuditSummary) -> None:
    """
    G) Crossdoc quick sanity (icc.lcopilot.crossdoc)
    """
    _print_header("G) Crossdoc sanity (icc.lcopilot.crossdoc)")
    print("rule_id, document_type, condition_types, conditions_len, problems")

    rules: List[RuleRecord] = (
        session.query(RuleRecord)
        .filter(RuleRecord.domain == "icc.lcopilot.crossdoc")
        .order_by(RuleRecord.rule_id.asc())
        .all()
    )

    for rule in rules:
        conds = rule.conditions or []
        cond_types: Set[Optional[str]] = set()
        problems: List[str] = []

        if not rule.document_type or not str(rule.document_type).strip():
            problems.append("missing_document_type")

        if not isinstance(conds, list) or len(conds) == 0:
            problems.append("empty_conditions")
        else:
            for cond in conds:
                if not isinstance(cond, dict):
                    problems.append("non_dict_condition")
                    continue
                cond_type = cond.get("type")
                cond_types.add(cond_type)
                if cond_type is None:
                    problems.append("condition_missing_type")

        print(
            f"{rule.rule_id}, {rule.document_type}, {cond_types}, {len(conds)}, {problems}"
        )


def main() -> None:
    logging.basicConfig(level=logging.INFO)

    summary = AuditSummary()
    session: Session = SessionLocal()

    try:
        check_ruleset_rule_counts(session, summary)
        check_field_completeness(session, summary)
        check_severity_and_flags(session, summary)
        check_condition_types(session, summary)
        check_duplicates_and_collisions(session, summary)
        check_orphans(session, summary)
        check_crossdoc_sanity(session, summary)

        _print_header("RULESET INTEGRITY SUMMARY")
        print(f"Total ICC rulesets: {summary.total_icc_rulesets}")
        print(f"Active ICC rulesets: {summary.active_icc_rulesets}")
        print(f"Total rules in ICC rulesets: {summary.total_icc_rules}")
        print(f"Rulesets with count mismatch: {summary.rulesets_count_mismatch}")
        print(f"Active rulesets with zero rules: {summary.rulesets_active_with_zero_rules}")
        print(f"Rules with missing fields: {summary.rules_missing_fields}")
        print(f"Rules with bad severity/flags: {summary.rules_bad_severity_flags}")
        print(f"Rules with bad condition types: {summary.rules_bad_condition_types}")
        print(f"Duplicate rule_ids (within ruleset): {summary.duplicate_rule_ids_within_ruleset}")
        print(
            f"Cross-ruleset collisions (same domain/jurisdiction/document_type/rule_id): "
            f"{summary.cross_ruleset_collisions}"
        )
        print(f"Orphan rules: {summary.orphan_rules}")

    finally:
        session.close()


if __name__ == "__main__":
    main()


