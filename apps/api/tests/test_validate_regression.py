from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import UserRole
from app.services.validation.validation_gate import GateResult, GateStatus
from app.services.extraction.lc_baseline import LCBaseline

import app.routers.validate as validate_module


class DummyCompany:
    def __init__(self):
        self.id = uuid4()


class DummyUser:
    def __init__(self, email="demo@trdrhub.com", role=UserRole.EXPORTER, company=None):
        self.id = uuid4()
        self.email = email
        self.role = role
        self.company = company
        self.company_id = getattr(company, "id", None)

    def is_bank_user(self) -> bool:
        return False


class FakeQuery:
    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return None


class FakeResult:
    def first(self):
        return None


class FakeDB:
    def add(self, obj):
        return None

    def commit(self):
        return None

    def flush(self):
        return None

    def refresh(self, obj):
        return None

    def query(self, *args, **kwargs):
        return FakeQuery()

    def execute(self, *args, **kwargs):
        return FakeResult()

    def close(self):
        return None


@pytest.fixture(autouse=True)
def _override_db():
    def _get_db():
        yield FakeDB()

    app.dependency_overrides[validate_module.get_db] = _get_db
    yield
    app.dependency_overrides.pop(validate_module.get_db, None)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def demo_user():
    return DummyUser(company=DummyCompany())


def test_no_lc_gate_blocked(client, monkeypatch, demo_user):
    monkeypatch.setattr(validate_module, "_build_document_context", lambda *args, **kwargs: {})
    monkeypatch.setattr(validate_module, "get_or_create_demo_user", lambda db: demo_user)

    files = {
        "file": ("invoice.pdf", b"%PDF-1.4 test content", "application/pdf"),
    }
    data = {"userType": "exporter"}

    response = client.post("/api/validate/", files=files, data=data)
    assert response.status_code == 200
    payload = response.json()

    assert payload["status"] == "blocked"
    assert payload["block_reason"] == "no_lc_found"
    assert payload["error"]["error_code"] == "NO_LC_FOUND"


def test_dashboard_mismatch_blocked(client, monkeypatch, demo_user):
    monkeypatch.setattr(validate_module, "_build_document_context", lambda *args, **kwargs: {})
    monkeypatch.setattr(validate_module, "get_or_create_demo_user", lambda db: demo_user)

    payload = {
        "userType": "exporter",
        "lc": {
            "lc_type": "import",
            "lc_type_confidence": 0.9,
            "lc_type_reason": "Test import LC",
        },
    }

    response = client.post("/api/validate/", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "blocked"
    assert data["block_reason"] == "dashboard_lc_mismatch"
    assert data["error"]["error_code"] == "WRONG_DASHBOARD"


def test_v2_gate_blocked_missing_critical_fields(client, monkeypatch, demo_user):
    monkeypatch.setattr(validate_module, "_build_document_context", lambda *args, **kwargs: {})
    monkeypatch.setattr(validate_module, "get_or_create_demo_user", lambda db: demo_user)
    monkeypatch.setattr(validate_module, "_build_lc_baseline_from_context", lambda *args, **kwargs: LCBaseline())

    gate_result = GateResult(
        status=GateStatus.BLOCKED,
        can_proceed=False,
        block_reason="missing_critical",
        missing_critical=["lc_number"],
        blocking_issues=[{"rule": "LC-GATE-NUMBER"}],
        completeness=0.0,
        critical_completeness=0.0,
    )
    monkeypatch.setattr(validate_module.ValidationGate, "check_from_baseline", lambda *args, **kwargs: gate_result)

    response = client.post("/api/validate/", json={"document_type": "letter_of_credit"})
    assert response.status_code == 200
    payload = response.json()

    assert payload["structured_result"]["validation_blocked"] is True
    assert payload["structured_result"]["gate_result"]["block_reason"] == "missing_critical"


def test_gate_passed_normal_path_documents_populated(client, monkeypatch, demo_user):
    extracted_context = {
        "documents": [
            {
                "filename": "Invoice.pdf",
                "document_type": "commercial_invoice",
                "extracted_fields": {"amount": "1000"},
                "ocr_confidence": 0.9,
                "extraction_status": "success",
            }
        ],
        "documents_presence": {"commercial_invoice": {"present": True}},
    }

    monkeypatch.setattr(validate_module, "_build_document_context", lambda *args, **kwargs: extracted_context)
    monkeypatch.setattr(validate_module, "get_or_create_demo_user", lambda db: demo_user)
    monkeypatch.setattr(validate_module, "_build_lc_baseline_from_context", lambda *args, **kwargs: LCBaseline())

    gate_result = GateResult(
        status=GateStatus.PASSED,
        can_proceed=True,
        completeness=1.0,
        critical_completeness=1.0,
    )
    monkeypatch.setattr(validate_module.ValidationGate, "check_from_baseline", lambda *args, **kwargs: gate_result)

    async def _noop_validate_document_async(*args, **kwargs):
        return []

    async def _noop_ai_validation(*args, **kwargs):
        return [], {"critical_issues": 0, "major_issues": 0}

    async def _noop_price_checks(*args, **kwargs):
        return []

    async def _noop_record_usage(*args, **kwargs):
        return None

    class _CrossDocResult:
        def __init__(self):
            self.issues = []

    class _CrossDocValidator:
        def validate_all(self, *args, **kwargs):
            return _CrossDocResult()

    class _IssueEngine:
        def generate_extraction_issues(self, *args, **kwargs):
            return []

    from app.services.validation import crossdoc_validator as crossdoc_module
    from app.services.validation import issue_engine as issue_engine_module
    from app.services.validation import ai_validator as ai_validator_module
    from app.services import crossdoc as crossdoc_service_module

    monkeypatch.setattr(validate_module, "validate_document_async", _noop_validate_document_async)
    monkeypatch.setattr(crossdoc_module, "CrossDocValidator", _CrossDocValidator)
    monkeypatch.setattr(issue_engine_module, "IssueEngine", _IssueEngine)
    monkeypatch.setattr(ai_validator_module, "run_ai_validation", _noop_ai_validation)
    monkeypatch.setattr(crossdoc_service_module, "run_price_verification_checks", _noop_price_checks)
    monkeypatch.setattr(validate_module, "parse_lc_requirements_sync_v2", lambda *args, **kwargs: None)
    monkeypatch.setattr(validate_module, "calculate_overall_extraction_confidence", lambda *args, **kwargs: None)
    monkeypatch.setattr(validate_module, "record_usage_manual", _noop_record_usage)
    monkeypatch.setattr(validate_module, "validate_and_annotate_response", lambda structured_result: structured_result)
    monkeypatch.setattr(validate_module, "build_customs_manifest_from_option_e", lambda *args, **kwargs: {})
    monkeypatch.setattr(validate_module, "compute_customs_risk_from_option_e", lambda *args, **kwargs: None)

    response = client.post("/api/validate/", json={"document_type": "letter_of_credit"})
    assert response.status_code == 200
    payload = response.json()
    structured = payload["structured_result"]

    assert structured["documents_structured"]
    assert structured["documents_structured"][0]["filename"] == "Invoice.pdf"


def test_auth_fallback_demo_user_behavior(client, monkeypatch):
    demo_user = DummyUser(company=DummyCompany())
    called = {"flag": False}

    def _demo_user(db):
        called["flag"] = True
        return demo_user

    monkeypatch.setattr(validate_module, "get_or_create_demo_user", _demo_user)

    from app.services.entitlements import EntitlementService

    def _fail_enforce(*args, **kwargs):
        raise AssertionError("quota enforcement should not run for demo user")

    monkeypatch.setattr(EntitlementService, "enforce_quota", _fail_enforce)
    monkeypatch.setattr(validate_module, "_build_document_context", lambda *args, **kwargs: {})

    response = client.post("/api/validate/", json={"document_type": "letter_of_credit"})
    assert response.status_code == 200
    assert called["flag"] is True


def test_multipart_invalid_file_returns_400(client, monkeypatch, demo_user):
    monkeypatch.setattr(validate_module, "get_or_create_demo_user", lambda db: demo_user)

    files = {
        "file": ("bad.pdf", b"not a pdf", "application/pdf"),
    }

    response = client.post("/api/validate/", files=files, data={"userType": "exporter"})
    assert response.status_code == 400


def _wire_validate_success_path(monkeypatch):
    async def _noop_validate_document_async(*args, **kwargs):
        return []

    async def _noop_ai_validation(*args, **kwargs):
        return [], {"critical_issues": 0, "major_issues": 0}

    async def _noop_price_checks(*args, **kwargs):
        return []

    async def _noop_record_usage(*args, **kwargs):
        return None

    class _CrossDocResult:
        def __init__(self):
            self.issues = []

    class _CrossDocValidator:
        def validate_all(self, *args, **kwargs):
            return _CrossDocResult()

    class _IssueEngine:
        def generate_extraction_issues(self, *args, **kwargs):
            return []

    from app.services.validation import crossdoc_validator as crossdoc_module
    from app.services.validation import issue_engine as issue_engine_module
    from app.services.validation import ai_validator as ai_validator_module
    from app.services import crossdoc as crossdoc_service_module

    monkeypatch.setattr(validate_module, "validate_document_async", _noop_validate_document_async)
    monkeypatch.setattr(crossdoc_module, "CrossDocValidator", _CrossDocValidator)
    monkeypatch.setattr(issue_engine_module, "IssueEngine", _IssueEngine)
    monkeypatch.setattr(ai_validator_module, "run_ai_validation", _noop_ai_validation)
    monkeypatch.setattr(crossdoc_service_module, "run_price_verification_checks", _noop_price_checks)
    monkeypatch.setattr(validate_module, "parse_lc_requirements_sync_v2", lambda *args, **kwargs: None)
    monkeypatch.setattr(validate_module, "calculate_overall_extraction_confidence", lambda *args, **kwargs: None)
    monkeypatch.setattr(validate_module, "record_usage_manual", _noop_record_usage)
    monkeypatch.setattr(validate_module, "build_customs_manifest_from_option_e", lambda *args, **kwargs: {})
    monkeypatch.setattr(validate_module, "compute_customs_risk_from_option_e", lambda *args, **kwargs: None)


def test_validate_endpoint_day1_contract_downgrades_low_coverage(client, monkeypatch, demo_user):
    extracted_context = {
        "documents": [
            {
                "filename": "Invoice.pdf",
                "document_type": "commercial_invoice",
                "extracted_fields": {"amount": "1000"},
                "ocr_confidence": 0.9,
                "extraction_status": "success",
                "day1_runtime": {"coverage": 3, "threshold": 5, "schema_ok": True, "errors": []},
            }
        ],
        "documents_presence": {"commercial_invoice": {"present": True}},
    }

    monkeypatch.setattr(validate_module, "_build_document_context", lambda *args, **kwargs: extracted_context)
    monkeypatch.setattr(validate_module, "get_or_create_demo_user", lambda db: demo_user)
    monkeypatch.setattr(validate_module, "_build_lc_baseline_from_context", lambda *args, **kwargs: LCBaseline())
    gate_result = GateResult(status=GateStatus.PASSED, can_proceed=True, completeness=1.0, critical_completeness=1.0)
    monkeypatch.setattr(validate_module.ValidationGate, "check_from_baseline", lambda *args, **kwargs: gate_result)

    _wire_validate_success_path(monkeypatch)

    response = client.post("/api/validate/", json={"document_type": "letter_of_credit"})
    assert response.status_code == 200
    structured = response.json()["structured_result"]
    assert structured.get("_day1_contract", {}).get("status") == "review"
    docs = structured.get("documents_structured") or []
    assert docs and docs[0].get("extraction_status") == "partial"


def test_validate_endpoint_day1_contract_pass_high_coverage(client, monkeypatch, demo_user):
    extracted_context = {
        "documents": [
            {
                "filename": "BL.pdf",
                "document_type": "bill_of_lading",
                "extracted_fields": {"voyage_number": "118E"},
                "ocr_confidence": 0.95,
                "extraction_status": "success",
                "day1_runtime": {"coverage": 6, "threshold": 5, "schema_ok": True, "errors": []},
            }
        ],
        "documents_presence": {"bill_of_lading": {"present": True}},
    }

    monkeypatch.setattr(validate_module, "_build_document_context", lambda *args, **kwargs: extracted_context)
    monkeypatch.setattr(validate_module, "get_or_create_demo_user", lambda db: demo_user)
    monkeypatch.setattr(validate_module, "_build_lc_baseline_from_context", lambda *args, **kwargs: LCBaseline())
    gate_result = GateResult(status=GateStatus.PASSED, can_proceed=True, completeness=1.0, critical_completeness=1.0)
    monkeypatch.setattr(validate_module.ValidationGate, "check_from_baseline", lambda *args, **kwargs: gate_result)

    _wire_validate_success_path(monkeypatch)

    response = client.post("/api/validate/", json={"document_type": "letter_of_credit"})
    assert response.status_code == 200
    structured = response.json()["structured_result"]
    assert structured.get("_day1_contract", {}).get("status") == "pass"
