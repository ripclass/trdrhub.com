import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from io import BytesIO
from types import ModuleType, SimpleNamespace
import sys
from uuid import uuid4

if "weasyprint" not in sys.modules:
    class _WeasyStub:
        def __init__(self, *args, **kwargs):
            pass

        def write_pdf(self, *args, **kwargs):
            return b""

    weasy_module = ModuleType("weasyprint")
    weasy_module.HTML = _WeasyStub
    weasy_module.CSS = _WeasyStub
    sys.modules["weasyprint"] = weasy_module

    text_module = ModuleType("weasyprint.text")
    fonts_module = ModuleType("weasyprint.text.fonts")
    fonts_module.FontConfiguration = _WeasyStub
    text_module.fonts = fonts_module
    sys.modules["weasyprint.text"] = text_module
    sys.modules["weasyprint.text.fonts"] = fonts_module

if "aiohttp" not in sys.modules:
    class _ClientResponse:
        def __init__(self, status: int = 200):
            self.status = status

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def text(self):
            return ""

        async def json(self):
            return {}

    class _ClientSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def post(self, *args, **kwargs):
            return _ClientResponse()

    aiohttp_module = ModuleType("aiohttp")
    aiohttp_module.ClientSession = _ClientSession
    sys.modules["aiohttp"] = aiohttp_module

if "supabase" not in sys.modules:
    class _DummyStorage:
        def from_(self, *args, **kwargs):
            return self

        def upload(self, *args, **kwargs):
            return {}

        def download(self, *args, **kwargs):
            return b"{}"

        def create_signed_url(self, *args, **kwargs):
            return {"signedURL": "https://example.com/rules.json"}

        def remove(self, *args, **kwargs):
            return True

    class _SupabaseClient:
        def __init__(self, *args, **kwargs):
            self.storage = _DummyStorage()

    def _create_client(url, key):
        return _SupabaseClient()

    supabase_module = ModuleType("supabase")
    supabase_module.create_client = _create_client
    supabase_module.Client = _SupabaseClient
    sys.modules["supabase"] = supabase_module

from app.database import get_db
from app.routers import validate as validate_router

test_app = FastAPI()
test_app.include_router(validate_router.router)


class _DummyQuery:
    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return None

    def all(self):
        return []

    def delete(self):
        return 0


class _DummyDB:
    def add(self, *args, **kwargs):
        return None

    def commit(self):
        return None

    def refresh(self, *args, **kwargs):
        return None

    def flush(self):
        return None

    def close(self):
        return None

    def query(self, *args, **kwargs):
        return _DummyQuery()

    def execute(self, *args, **kwargs):
        return None


def _override_get_db():
    try:
        yield _DummyDB()
    finally:
        pass


async def _override_user_optional():
    return _create_stub_user()


class _StubUser:
    def __init__(self):
        self.id = str(uuid4())
        self.email = "demo@trdrhub.com"
        self.role = "exporter"
        self.company = SimpleNamespace(id=str(uuid4()))
        self.company_id = self.company.id
        self.is_active = True
        self.onboarding_data = {}


def _create_stub_user():
    return _StubUser()


def _pdf_bytes() -> bytes:
    return b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<<>>\nendobj\n"


@pytest.fixture(autouse=True)
def override_dependencies():
    test_app.dependency_overrides[get_db] = _override_get_db
    test_app.dependency_overrides[validate_router.get_user_optional] = _override_user_optional
    yield
    test_app.dependency_overrides.pop(get_db, None)
    test_app.dependency_overrides.pop(validate_router.get_user_optional, None)


@pytest.fixture
def client():
    return TestClient(test_app)


def test_validate_endpoint_returns_structured_result(monkeypatch, client: TestClient):
    async def fake_build_document_context(files_list, document_tags=None):
        return {
            "lc": {"number": "LC100"},
            "invoice": {"invoice_amount": "48000"},
            "documents": [
                {
                    "id": "lc-doc",
                    "filename": "LC.pdf",
                    "document_type": "letter_of_credit",
                    "extracted_fields": {"lc_number": "LC100"},
                    "extraction_status": "success",
                },
                {
                    "id": "invoice-doc",
                    "filename": "Invoice.pdf",
                    "document_type": "commercial_invoice",
                    "extracted_fields": {"invoice_amount": "48000"},
                    "extraction_status": "success",
                },
            ],
            "documents_presence": {
                "letter_of_credit": {"present": True, "count": 1},
                "commercial_invoice": {"present": True, "count": 1},
            },
            "extraction_status": "success",
        }

    async def fake_validate_document_async(payload, document_type):
        return [
            {
                "rule": "AMOUNT_MATCH",
                "title": "Invoice amount differs",
                "passed": False,
                "severity": "major",
                "documents": ["LC.pdf", "Invoice.pdf"],
                "message": "Invoice amount is below LC value.",
                "expected": "50000 USD",
                "actual": "48000 USD",
            }
        ]

    async def fake_crossdoc_issues(structured_docs):
        return [
            {
                "id": "CROSSDOC-GOODS-FAKE",
                "title": "Goods description mismatch",
                "severity": "minor",
                "documents": ["Invoice.pdf", "LC.pdf"],
                "description": "Descriptions do not line up.",
                "expected": "Refined sugar",
                "found": "Raw sugar",
                "suggested_fix": "Match invoice description to LC clause 45A.",
            }
        ]

    monkeypatch.setattr(validate_router, "_build_document_context", fake_build_document_context)
    monkeypatch.setattr(validate_router, "validate_document_async", fake_validate_document_async)
    monkeypatch.setattr(validate_router, "generate_crossdoc_insights", fake_crossdoc_issues)
    monkeypatch.setattr(
        validate_router,
        "AuditService",
        lambda *args, **kwargs: SimpleNamespace(log_action=lambda *a, **k: None),
    )
    monkeypatch.setattr(
        validate_router,
        "_determine_company_size",
        lambda current_user, payload: ("sme", 5),
    )

    files = [
        ("files", ("Letter_of_Credit.pdf", BytesIO(_pdf_bytes()), "application/pdf")),
        ("files", ("Commercial_Invoice.pdf", BytesIO(_pdf_bytes()), "application/pdf")),
    ]

    response = client.post("/api/validate", files=files)
    assert response.status_code == 200
    payload = response.json()

    assert "structured_result" in payload
    structured = payload["structured_result"]
    assert structured["processing_summary"]["total_documents"] == 2
    assert len(structured["documents"]) == 2
    assert structured["documents"][0]["document_id"] == "lc-doc"
    assert len(structured["issues"]) == 2  # deterministic + crossdoc
    assert any(issue.get("expected") for issue in structured["issues"])
    assert len(structured["timeline"]) == 4
    assert payload["issue_cards"], "Issue cards should be populated for Issues tab"
