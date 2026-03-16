from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.models.sme_workspace import AmendmentStatus, DraftStatus
from app.schemas.sme_workspace import AmendmentRead, DraftRead


def test_draft_read_uses_extra_metadata_field() -> None:
    now = datetime.now(timezone.utc)
    draft = SimpleNamespace(
        id=uuid4(),
        user_id=uuid4(),
        company_id=uuid4(),
        lc_number="LC-001",
        client_name="ACME",
        draft_type="exporter_draft",
        notes="Draft notes",
        extra_metadata={"source": "workspace"},
        status=DraftStatus.DRAFT,
        uploaded_docs=[],
        validation_session_id=None,
        created_at=now,
        updated_at=now,
    )

    parsed = DraftRead.model_validate(draft)

    assert parsed.metadata == {"source": "workspace"}


def test_amendment_read_uses_extra_metadata_field() -> None:
    now = datetime.now(timezone.utc)
    amendment = SimpleNamespace(
        id=uuid4(),
        user_id=uuid4(),
        company_id=uuid4(),
        lc_number="LC-002",
        notes="Amendment notes",
        extra_metadata={"reason": "bank request"},
        version=2,
        previous_version_id=None,
        validation_session_id=uuid4(),
        previous_validation_session_id=None,
        status=AmendmentStatus.PENDING,
        changes_diff={"field": "amount"},
        document_changes=[],
        created_at=now,
        updated_at=now,
    )

    parsed = AmendmentRead.model_validate(amendment)

    assert parsed.metadata == {"reason": "bank request"}
