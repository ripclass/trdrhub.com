from __future__ import annotations

import importlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SESSION_SETUP_MODULE = "app.routers.validation.session_setup"


class _Logger:
    def info(self, *args, **kwargs) -> None:
        return None

    def warning(self, *args, **kwargs) -> None:
        return None


class _Db:
    def commit(self) -> None:
        return None

    def add(self, _value) -> None:
        return None

    def refresh(self, _value) -> None:
        return None


class _ValidationSessionService:
    def __init__(self, db) -> None:
        self.db = db

    def create_session(self, user):
        return SimpleNamespace(
            id="session-123",
            user_id=getattr(user, "id", None),
            company_id=None,
            status="created",
            processing_started_at=None,
            extracted_data={},
        )


def _shared_bindings() -> dict[str, object]:
    async def _build_document_context(_files_list, _document_tags, job_id=None):
        return {
            "documents": [],
            "documents_presence": {},
            "lc": {
                "raw_text": "LC TEXT",
                "workflow_lc_type": "export",
            },
        }

    return {
        "Any": object,
        "AuditAction": object,
        "AuditResult": object,
        "AuditService": object,
        "Company": object,
        "CompanyStatus": object,
        "ComplianceScorer": object,
        "CrossDocValidator": object,
        "Decimal": object,
        "Depends": lambda dependency=None: dependency,
        "Dict": dict,
        "Document": object,
        "EntitlementError": Exception,
        "EntitlementService": object,
        "HTTPException": Exception,
        "IssueEngine": object,
        "LCType": SimpleNamespace(UNKNOWN=SimpleNamespace(value="unknown")),
        "List": list,
        "Optional": object,
        "PlanType": object,
        "Request": object,
        "Session": object,
        "SessionStatus": SimpleNamespace(PROCESSING=SimpleNamespace(value="processing")),
        "UsageAction": object,
        "User": object,
        "ValidationGate": object,
        "ValidationSessionService": _ValidationSessionService,
        "_apply_cycle2_runtime_recovery": lambda *args, **kwargs: None,
        "_augment_doc_field_details_with_decisions": lambda *args, **kwargs: None,
        "_augment_issues_with_field_decisions": lambda *args, **kwargs: None,
        "_backfill_hybrid_secondary_surfaces": lambda *args, **kwargs: None,
        "_build_bank_submission_verdict": lambda *args, **kwargs: None,
        "_build_blocked_structured_result": lambda *args, **kwargs: None,
        "_build_day1_relay_debug": lambda *args, **kwargs: None,
        "_build_document_context": _build_document_context,
        "_build_document_extraction_v1": lambda *args, **kwargs: None,
        "_build_document_summaries": lambda *args, **kwargs: None,
        "_build_extraction_core_bundle": lambda *args, **kwargs: None,
        "_build_issue_dedup_key": lambda *args, **kwargs: None,
        "_build_issue_provenance_v1": lambda *args, **kwargs: None,
        "_build_lc_baseline_from_context": lambda *args, **kwargs: None,
        "_build_lc_intake_summary": lambda _lc: {"summary": "ok"},
        "_build_processing_summary": lambda *args, **kwargs: None,
        "_build_processing_summary_v2": lambda *args, **kwargs: None,
        "_build_submission_eligibility_context": lambda *args, **kwargs: None,
        "_build_validation_contract": lambda *args, **kwargs: None,
        "_coerce_text_list": lambda value: list(value) if isinstance(value, list) else [],
        "_compute_invoice_amount_bounds": lambda *args, **kwargs: None,
        "_count_issue_severity": lambda *args, **kwargs: None,
        "_determine_company_size": lambda *args, **kwargs: None,
        "_empty_extraction_artifacts_v1": lambda **kwargs: {},
        "_extract_field_decisions_from_payload": lambda *args, **kwargs: None,
        "_extract_intake_only": lambda payload: bool(payload.get("intake_only")),
        "_extract_lc_type_override": lambda payload: None,
        "_extract_request_user_type": lambda payload: payload.get("user_type"),
        "_extract_workflow_lc_type": lambda lc: lc.get("workflow_lc_type"),
        "_infer_required_document_types_from_lc": lambda _lc: [],
        "_normalize_lc_payload_structures": lambda lc: lc,
        "_prepare_extractor_outputs_for_structured_result": lambda *args, **kwargs: None,
        "_resolve_shipment_context": lambda payload: {},
        "_response_shaping": object,
        "_run_validation_arbitration_escalation": lambda *args, **kwargs: None,
        "_sync_structured_result_collections": lambda *args, **kwargs: None,
        "adapt_from_structured_result": lambda *args, **kwargs: None,
        "apply_bank_policy": lambda *args, **kwargs: None,
        "batch_lookup_descriptions": lambda *args, **kwargs: None,
        "build_customs_manifest_from_option_e": lambda *args, **kwargs: None,
        "build_issue_cards": lambda *args, **kwargs: None,
        "build_lc_classification": lambda *args, **kwargs: None,
        "build_unified_structured_result": lambda *args, **kwargs: None,
        "calculate_overall_extraction_confidence": lambda *args, **kwargs: None,
        "calculate_total_amendment_cost": lambda *args, **kwargs: None,
        "compute_customs_risk_from_option_e": lambda *args, **kwargs: None,
        "context": {},
        "copy": __import__("copy"),
        "country_str": "",
        "create_audit_context": lambda *args, **kwargs: None,
        "detect_bank_from_lc": lambda *args, **kwargs: None,
        "detect_lc_type": lambda *args, **kwargs: {"lc_type": "export", "reason": "stub", "confidence": 0.9},
        "detect_lc_type_ai": lambda *args, **kwargs: None,
        "enforce_day1_response_contract": lambda *args, **kwargs: None,
        "extract_requirement_conditions": lambda _lc: [],
        "extract_unmapped_requirements": lambda _lc: [],
        "func": SimpleNamespace(now=lambda: "now"),
        "generate_amendments_for_issues": lambda *args, **kwargs: None,
        "get_bank_profile": lambda *args, **kwargs: None,
        "get_db": lambda: None,
        "get_user_optional": lambda: None,
        "json": json,
        "logger": _Logger(),
        "logging": __import__("logging"),
        "name": "",
        "normalize_required_documents": lambda _lc: [],
        "parse_lc_requirements_sync_v2": lambda *args, **kwargs: None,
        "record_usage_manual": lambda *args, **kwargs: None,
        "ref": None,
        "run_ai_validation": lambda *args, **kwargs: None,
        "run_price_verification_checks": lambda *args, **kwargs: None,
        "run_sanctions_screening_for_validation": lambda *args, **kwargs: None,
        "settings": SimpleNamespace(),
        "status": SimpleNamespace(),
        "time": __import__("time"),
        "traceback": __import__("traceback"),
        "uuid4": __import__("uuid").uuid4,
        "validate_and_annotate_response": lambda *args, **kwargs: None,
        "validate_doc": lambda *args, **kwargs: None,
        "validate_document_async": lambda *args, **kwargs: None,
        "validate_document_set_completeness": lambda *args, **kwargs: None,
        "validate_upload_file": lambda *args, **kwargs: None,
    }


@pytest.mark.asyncio
async def test_prepare_validation_session_creates_persisted_session_for_authenticated_thin_requests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEBUG", "false")
    session_setup = importlib.reload(importlib.import_module(SESSION_SETUP_MODULE))
    session_setup.bind_shared(_shared_bindings())
    session_setup.ValidationSessionService = _ValidationSessionService

    runtime_context: dict[str, object] = {}
    payload = {}

    result = await session_setup.prepare_validation_session(
        request=SimpleNamespace(state=SimpleNamespace()),
        current_user=SimpleNamespace(id="user-1", company_id=None, company=None),
        db=_Db(),
        payload=payload,
        files_list=[],
        intake_only=True,
        checkpoint=lambda _name: None,
        start_time=0.0,
        runtime_context=runtime_context,
    )

    assert result["job_id"] == "session-123"
    assert runtime_context["job_id"] == "session-123"
    assert runtime_context["job_id_resolvable"] is True
    assert runtime_context["job_id_source"] == "session"


@pytest.mark.asyncio
async def test_prepare_validation_session_marks_ephemeral_job_ids_as_non_resolvable_for_anonymous_requests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEBUG", "false")
    session_setup = importlib.reload(importlib.import_module(SESSION_SETUP_MODULE))
    session_setup.bind_shared(_shared_bindings())
    session_setup.ValidationSessionService = _ValidationSessionService

    runtime_context: dict[str, object] = {}
    payload = {}

    result = await session_setup.prepare_validation_session(
        request=SimpleNamespace(state=SimpleNamespace()),
        current_user=None,
        db=_Db(),
        payload=payload,
        files_list=[],
        intake_only=True,
        checkpoint=lambda _name: None,
        start_time=0.0,
        runtime_context=runtime_context,
    )

    assert result["job_id"]
    assert runtime_context["job_id"] == result["job_id"]
    assert runtime_context["job_id_resolvable"] is False
    assert runtime_context["job_id_source"] == "ephemeral"
