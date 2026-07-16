"""Proofline persistence model continuity and tenant-safety constraints."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from sqlalchemy import UniqueConstraint

from app.database import Base
from app.models import (
    BuyerRequirement,
    ProoflineFinding,
    RemediationAction,
    TradeCase,
    TradeCaseCheckRun,
    TradeCaseDecision,
    TradeCaseDocument,
    TradeCaseEvent,
    TradeCaseOutcome,
    TradeCaseParty,
)


def _index_columns(table):
    return {index.name: tuple(column.name for column in index.columns) for index in table.indexes}


def _unique_columns(table):
    return {
        constraint.name: tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }


def test_all_proofline_tables_are_registered_with_existing_metadata():
    expected = {
        "trade_cases",
        "trade_case_parties",
        "trade_case_documents",
        "trade_case_check_runs",
        "proofline_findings",
        "remediation_actions",
        "trade_case_decisions",
        "trade_case_events",
        "buyer_requirements",
        "trade_case_outcomes",
    }
    assert expected <= set(Base.metadata.tables)


def test_trade_case_reuses_existing_tenant_user_session_and_report_models():
    table = TradeCase.__table__
    foreign_keys = {fk.target_fullname for fk in table.foreign_keys}

    assert table.c.company_id.nullable is False
    assert {
        "companies.id",
        "users.id",
        "validation_sessions.id",
        "reports.id",
    } <= foreign_keys
    assert _unique_columns(table)["uq_trade_cases_company_reference"] == (
        "company_id",
        "case_reference",
    )
    assert _index_columns(table)["ix_trade_cases_company_status_updated"] == (
        "company_id",
        "status",
        "updated_at",
    )
    assert table.c.document_session_id.nullable is True


def test_case_documents_reference_existing_documents_and_preserve_lineage():
    table = TradeCaseDocument.__table__
    foreign_keys = {fk.target_fullname for fk in table.foreign_keys}

    assert "documents.id" in foreign_keys
    assert "trade_case_documents.id" in foreign_keys
    assert table.c.version_number.nullable is False
    assert table.c.correction_round.nullable is False
    assert _unique_columns(table)["uq_trade_case_document_version"] == (
        "trade_case_id",
        "logical_key",
        "version_number",
    )
    assert _index_columns(table)["ix_trade_case_documents_company_case_current"] == (
        "company_id",
        "trade_case_id",
        "is_current",
    )


def test_check_runs_findings_decisions_and_events_have_idempotent_audit_keys():
    check_unique = _unique_columns(TradeCaseCheckRun.__table__)
    finding_unique = _unique_columns(ProoflineFinding.__table__)
    decision_unique = _unique_columns(TradeCaseDecision.__table__)
    event_unique = _unique_columns(TradeCaseEvent.__table__)

    assert check_unique["uq_trade_case_check_idempotency"] == (
        "trade_case_id",
        "module",
        "idempotency_key",
    )
    assert finding_unique["uq_proofline_finding_source"] == (
        "trade_case_id",
        "source_module",
        "source_finding_id",
    )
    assert decision_unique["uq_trade_case_decision_version"] == (
        "trade_case_id",
        "version_number",
    )
    assert event_unique["uq_trade_case_event_idempotency"] == (
        "trade_case_id",
        "idempotency_key",
    )

    assert TradeCaseDecision.__table__.c.previous_recommendation.nullable is True
    assert TradeCaseDecision.__table__.c.override_reason.nullable is True
    assert TradeCaseEvent.__table__.c.actor_type.nullable is False
    assert TradeCaseEvent.__table__.c.occurred_at.nullable is False


def test_case_children_are_tenant_scoped_and_remediation_keeps_correction_links():
    for model in (
        TradeCaseParty,
        TradeCaseDocument,
        TradeCaseCheckRun,
        ProoflineFinding,
        RemediationAction,
        TradeCaseDecision,
        TradeCaseEvent,
        BuyerRequirement,
        TradeCaseOutcome,
    ):
        assert model.__table__.c.company_id.nullable is False, model.__name__

    remediation_fks = {
        fk.target_fullname for fk in RemediationAction.__table__.foreign_keys
    }
    assert "proofline_findings.id" in remediation_fks
    assert "trade_case_documents.id" in remediation_fks
    assert _unique_columns(TradeCaseOutcome.__table__)["uq_trade_case_outcome_case"] == (
        "trade_case_id",
    )


def test_proofline_migration_is_chained_and_reversible():
    path = Path("apps/api/alembic/versions/20260716_add_proofline_trade_cases.py")
    spec = importlib.util.spec_from_file_location("proofline_migration", path)
    assert spec and spec.loader
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    assert migration.revision == "20260716_add_proofline_trade_cases"
    assert migration.down_revision == "20260703_add_payment_fields"
    source = path.read_text(encoding="utf-8")
    for table in (
        "trade_cases",
        "trade_case_parties",
        "trade_case_documents",
        "trade_case_check_runs",
        "proofline_findings",
        "remediation_actions",
        "trade_case_decisions",
        "trade_case_events",
        "buyer_requirements",
    ):
        assert f'op.create_table(\n        "{table}"' in source
        assert f'op.drop_table("{table}")' in source


def test_proofline_document_session_migration_is_chained_and_reversible():
    path = Path("apps/api/alembic/versions/20260716_add_proofline_document_session.py")
    spec = importlib.util.spec_from_file_location("proofline_document_session_migration", path)
    assert spec and spec.loader
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    assert migration.down_revision == "20260716_add_proofline_trade_cases"
    source = path.read_text(encoding="utf-8")
    assert "op.add_column(" in source
    assert '"trade_cases"' in source
    assert '"document_session_id"' in source
    assert 'op.drop_column("trade_cases", "document_session_id")' in source


def test_proofline_outcome_migration_is_chained_and_reversible():
    path = Path("apps/api/alembic/versions/20260716_add_proofline_outcomes.py")
    spec = importlib.util.spec_from_file_location("proofline_outcome_migration", path)
    assert spec and spec.loader
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    assert migration.down_revision == "20260716_add_proofline_pricing"
    source = path.read_text(encoding="utf-8")
    assert '"trade_case_outcomes"' in source
    assert 'op.drop_table("trade_case_outcomes")' in source
