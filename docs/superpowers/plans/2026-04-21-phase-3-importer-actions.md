# Phase 3 — Importer Post-Validation Action Endpoints Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the four importer-specific post-validation actions end-to-end. Amendment-Request (Moment 1) as NEW; Supplier Fix Pack / Notify Supplier / Bank Precheck (Moment 2) upgraded from stubs to real side effects.

**Architecture:** One endpoint per action under `/api/importer/...`. No per-endpoint server flags — the client flag `VITE_LCOPILOT_IMPORTER_V2` already hides the action buttons, which contains the blast radius. Rollback = git revert + redeploy. Frontend hooks under `apps/web/src/hooks/use-importer-actions.ts`. UI wires each action button into `VerdictTab`'s `actionSlot` prop (from Phase 1) via a moment-aware `<DraftLcActions>` or `<SupplierDocActions>` component rendered by `ImportResults`.

**Tech Stack:** FastAPI + SQLAlchemy + boto3 (S3) + existing email service (Resend / SES — discover at impl time). React Query + React for frontend.

**Prereq:** Phase 1 + Phase 2 complete.

**Spec:** `docs/superpowers/specs/2026-04-21-importer-parity-design.md` (Phase 3 section)

---

## Pre-flight

### Task 0: Discover existing infrastructure

**Files:**
- Read-only

- [ ] **Step 1: Locate existing S3 client in backend**

Run:
```
grep -rln "boto3\|s3.*client\|aws.*s3" apps/api/app --include="*.py" | head -10
```
Expected: file(s) that already set up an S3 client. Note the module for reuse.

- [ ] **Step 2: Locate existing email-sending service**

Run:
```
grep -rln "resend\|sendgrid\|ses\|send_email\|send_mail" apps/api/app --include="*.py" | head -10
```
Expected: existing email service module. Note for reuse. If none exists, Task 4 adds one via env-config.

- [ ] **Step 3: Read current `apps/api/app/routers/importer.py`**

Read the full file (it's 514 lines). Note:
- Current schemas for the three existing stubs
- The existing `supplier-fix-pack` implementation (needs S3 wire-up)
- `require_importer_user` dependency
- Audit logging pattern

- [ ] **Step 4: Check for weasyprint or other PDF renderer**

Run:
```
grep -rln "weasyprint\|reportlab\|pdfkit\|fpdf" apps/api --include="*.py" apps/api/requirements*.txt pyproject.toml
```
Expected: existing PDF renderer. If none, Task 1 adds `weasyprint` to requirements.

- [ ] **Step 5: No commit (recon only)**

---

## Task 1: NEW — `POST /api/importer/amendment-request` (Moment 1)

**Files:**
- Create: `apps/api/app/services/importer/amendment_request.py`
- Create: `apps/api/app/services/importer/__init__.py` (if folder new)
- Create: `apps/api/app/templates/amendment_request.html` (jinja2 template)
- Modify: `apps/api/app/routers/importer.py` (add endpoint)
- Modify: `apps/api/requirements.txt` (add weasyprint if not present)

- [ ] **Step 1: Add weasyprint dependency (if not present)**

If Task 0 Step 4 showed no PDF renderer, append to `apps/api/requirements.txt`:
```
weasyprint>=60.0
jinja2>=3.1.0
```

Run: `cd apps/api && pip install -r requirements.txt`
Expected: installs succeed.

- [ ] **Step 2: Write a failing test**

Create `apps/api/tests/test_amendment_request.py`:

```python
"""Amendment request PDF generator + endpoint tests."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.importer.amendment_request import build_amendment_request_pdf

client = TestClient(app)


def test_build_amendment_request_pdf_returns_bytes():
    session_data = {
        "lc_number": "LC-TEST-001",
        "applicant": "Test Importer Co.",
        "beneficiary": "Test Supplier Ltd.",
        "issue_date": "2026-04-01",
        "findings": [
            {
                "rule_id": "UCP-14A",
                "title": "Presentation period too tight",
                "current_text": "Documents must be presented within 5 days",
                "suggested_text": "Documents must be presented within 21 days",
                "severity": "major",
            },
        ],
    }
    pdf = build_amendment_request_pdf(session_data)
    assert isinstance(pdf, bytes)
    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 1000


def test_amendment_request_endpoint_requires_auth():
    resp = client.post("/api/importer/amendment-request", json={"validation_session_id": "00000000-0000-0000-0000-000000000000"})
    assert resp.status_code in (401, 403)


def test_amendment_request_endpoint_returns_pdf(
    authenticated_headers, importer_draft_lc_session
):
    resp = client.post(
        "/api/importer/amendment-request",
        json={"validation_session_id": str(importer_draft_lc_session.id)},
        headers=authenticated_headers,
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF-")


def test_amendment_request_rejects_non_draft_lc_workflow(
    authenticated_headers, importer_supplier_docs_session
):
    resp = client.post(
        "/api/importer/amendment-request",
        json={"validation_session_id": str(importer_supplier_docs_session.id)},
        headers=authenticated_headers,
    )
    assert resp.status_code == 400
    assert "draft_lc" in resp.json().get("detail", "").lower()
```

(The fixtures `importer_draft_lc_session`, `importer_supplier_docs_session` may need to be added to `conftest.py` — they create `ValidationSession` rows with the respective `workflow_type` + at least one finding. Copy patterns from existing session fixtures.)

- [ ] **Step 3: Run to fail**

Run: `cd apps/api && pytest tests/test_amendment_request.py -v`
Expected: FAIL (module + endpoint missing).

- [ ] **Step 4: Create the jinja2 template**

Create `apps/api/app/templates/amendment_request.html`:

```html
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Amendment Request for LC {{ lc_number }}</title>
<style>
  body { font-family: "Helvetica", sans-serif; font-size: 10pt; }
  h1 { font-size: 14pt; }
  .meta { border-bottom: 1px solid #333; padding-bottom: 10px; margin-bottom: 20px; }
  .finding { border: 1px solid #ccc; padding: 10px; margin: 10px 0; page-break-inside: avoid; }
  .finding.major { border-left: 4px solid #c0392b; }
  .finding.minor { border-left: 4px solid #e67e22; }
  .finding.info  { border-left: 4px solid #2980b9; }
  .label { font-weight: bold; color: #555; }
  .current { background: #fff5f5; padding: 6px; border-radius: 2px; font-family: monospace; }
  .suggested { background: #f0fff4; padding: 6px; border-radius: 2px; font-family: monospace; }
</style>
</head>
<body>
<h1>Amendment Request — LC {{ lc_number }}</h1>
<div class="meta">
  <div><span class="label">Applicant:</span> {{ applicant }}</div>
  <div><span class="label">Beneficiary:</span> {{ beneficiary }}</div>
  <div><span class="label">LC issue date:</span> {{ issue_date }}</div>
  <div><span class="label">Request date:</span> {{ request_date }}</div>
</div>

<p>
  Please amend the following clauses in the above-referenced draft letter of credit
  to address the risks identified during review:
</p>

{% for f in findings %}
<div class="finding {{ f.severity }}">
  <div><span class="label">Rule:</span> {{ f.rule_id }} — {{ f.title }}</div>
  <div><span class="label">Current wording:</span></div>
  <div class="current">{{ f.current_text }}</div>
  <div><span class="label">Suggested wording:</span></div>
  <div class="suggested">{{ f.suggested_text }}</div>
</div>
{% endfor %}

<p style="margin-top:30px; font-size:9pt; color:#666;">
  Generated by TRDR Hub LCopilot. Substantiated by review session {{ session_id }}.
</p>
</body>
</html>
```

- [ ] **Step 5: Implement the PDF builder**

Create `apps/api/app/services/importer/__init__.py` (empty).

Create `apps/api/app/services/importer/amendment_request.py`:

```python
"""Generate PDF amendment requests for Moment 1 (Draft LC Risk Analysis)."""
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "templates"

_jinja = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=select_autoescape(["html"]),
)


def build_amendment_request_pdf(session_data: Dict[str, Any]) -> bytes:
    """Render the amendment-request HTML template and convert to PDF bytes."""
    template = _jinja.get_template("amendment_request.html")
    context = {
        "lc_number": session_data.get("lc_number", ""),
        "applicant": session_data.get("applicant", ""),
        "beneficiary": session_data.get("beneficiary", ""),
        "issue_date": session_data.get("issue_date", ""),
        "request_date": datetime.utcnow().strftime("%Y-%m-%d"),
        "session_id": session_data.get("session_id", ""),
        "findings": session_data.get("findings", []),
    }
    html = template.render(**context)
    return HTML(string=html).write_pdf()


def extract_amendment_context(session, findings) -> Dict[str, Any]:
    """Distill ValidationSession + findings into the template context.

    For each finding, if the finding already carries `current_text`/`suggested_text`
    (structured from the AI Examiner), use them; otherwise derive a minimal pair
    from `title` + `recommendation`.
    """
    lc = (session.structured_result or {}).get("lc_structured", {})
    lc_fields = lc.get("fields", {}) if isinstance(lc, dict) else {}

    amendment_findings = []
    for f in findings:
        current = f.get("current_text") or f.get("found") or ""
        suggested = f.get("suggested_text") or f.get("suggested_fix") or f.get("recommendation") or ""
        amendment_findings.append({
            "rule_id": f.get("rule_id") or f.get("rule") or "",
            "title": f.get("title") or f.get("finding") or "",
            "current_text": str(current),
            "suggested_text": str(suggested),
            "severity": (f.get("severity") or "minor").lower(),
        })

    return {
        "lc_number": lc_fields.get("lc_number") or lc_fields.get("number") or "UNKNOWN",
        "applicant": lc_fields.get("applicant_name") or lc_fields.get("applicant") or "",
        "beneficiary": lc_fields.get("beneficiary_name") or lc_fields.get("beneficiary") or "",
        "issue_date": lc_fields.get("issue_date") or "",
        "session_id": str(session.id),
        "findings": amendment_findings,
    }
```

- [ ] **Step 6: Add the endpoint in `importer.py`**

Append to `apps/api/app/routers/importer.py`:

```python
from fastapi.responses import StreamingResponse
import io
from uuid import UUID

from ..models.validation_session import WorkflowType
from ..services.importer.amendment_request import (
    build_amendment_request_pdf,
    extract_amendment_context,
)


class AmendmentRequestRequest(BaseModel):
    validation_session_id: UUID


@router.post("/amendment-request")
async def amendment_request(
    payload: AmendmentRequestRequest,
    current_user: User = Depends(require_importer_user),
    db: Session = Depends(get_db),
    request: Request = None,
):
    session = (
        db.query(ValidationSession)
        .filter(ValidationSession.id == payload.validation_session_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Validation session not found")

    if session.user_id != current_user.id and current_user.role != UserRole.TENANT_ADMIN:
        raise HTTPException(status_code=403, detail="Not your session")

    if session.workflow_type != WorkflowType.IMPORTER_DRAFT_LC:
        raise HTTPException(
            status_code=400,
            detail="Amendment request is only available for importer_draft_lc sessions",
        )

    findings = (session.structured_result or {}).get("issues", [])
    context = extract_amendment_context(session, findings)
    pdf_bytes = build_amendment_request_pdf(context)

    # Audit log
    AuditService.log(
        db=db,
        action=AuditAction.DOCUMENT_GENERATED,
        result=AuditResult.SUCCESS,
        user_id=current_user.id,
        resource_type="amendment_request",
        resource_id=str(session.id),
        context=create_audit_context(request) if request else {},
    )

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="amendment-request-{context["lc_number"]}.pdf"',
        },
    )
```

- [ ] **Step 7: Run tests**

Run: `cd apps/api && pytest tests/test_amendment_request.py -v`
Expected: 4/4 PASS.

- [ ] **Step 8: Commit**

```
git add -A
git commit -m "Add POST /api/importer/amendment-request endpoint + PDF generator"
```

---

## Task 2: Wire S3 upload into existing supplier-fix-pack endpoint

**Files:**
- Modify: `apps/api/app/routers/importer.py` (remove TODO at ~line 193, wire S3)
- Possibly: `apps/api/app/services/s3_client.py` (or wherever the S3 client lives per Task 0)

- [ ] **Step 1: Locate the current TODO**

Run: `grep -n "TODO" apps/api/app/routers/importer.py | head -5`
Expected: find the TODO around the fix-pack S3 upload. Read 20 lines before/after.

- [ ] **Step 2: Write a failing test**

Create `apps/api/tests/test_supplier_fix_pack_s3.py`:

```python
"""Tests that supplier-fix-pack uploads to S3 and returns a signed URL."""
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_fix_pack_returns_signed_s3_url(
    authenticated_headers, importer_supplier_docs_session
):
    # Mock the S3 client's upload + signed-url generator
    with patch("app.services.s3_client.upload_bytes") as upload, \
         patch("app.services.s3_client.generate_signed_url") as signer:
        upload.return_value = "s3://fixtures-bucket/fix-packs/abc.zip"
        signer.return_value = "https://fixtures-bucket.s3.amazonaws.com/fix-packs/abc.zip?X-Amz=..."

        resp = client.post(
            "/api/importer/supplier-fix-pack",
            json={"validation_session_id": str(importer_supplier_docs_session.id)},
            headers=authenticated_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["download_url"].startswith("https://")
        assert "X-Amz" in body["download_url"]
        assert body["file_name"].endswith(".zip")
        assert body["issue_count"] >= 0
        upload.assert_called_once()
        signer.assert_called_once()
```

(If the actual S3 client module path is different from `app.services.s3_client`, update the patch targets to match what Task 0 Step 1 found.)

- [ ] **Step 3: Run to fail**

Run: `cd apps/api && pytest tests/test_supplier_fix_pack_s3.py -v`
Expected: FAIL.

- [ ] **Step 4: Replace the TODO in `importer.py`**

In the current `/supplier-fix-pack` handler, replace the TODO section with real S3 upload:

```python
from app.services.s3_client import upload_bytes, generate_signed_url
from app.config import settings

# ...inside the handler, after the ZIP is built as `zip_bytes`:
key = f"fix-packs/{session.id}/{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.zip"
upload_bytes(
    bucket=settings.FIX_PACK_BUCKET,
    key=key,
    data=zip_bytes,
    content_type="application/zip",
)
signed_url = generate_signed_url(
    bucket=settings.FIX_PACK_BUCKET,
    key=key,
    expires_in=86400,  # 24 hours
)

return SupplierFixPackResponse(
    download_url=signed_url,
    file_name=f"fix-pack-{session.id}.zip",
    generated_at=datetime.utcnow(),
    issue_count=len(findings),
)
```

Update `apps/api/app/config.py` to include:
```python
FIX_PACK_BUCKET: str = os.getenv("FIX_PACK_BUCKET", "lcopilot-fix-packs-dev")
```

- [ ] **Step 5: Add S3 lifecycle note in README or DEPLOYMENT doc**

Append to `apps/api/docs/DEPLOYMENT.md` (or a similar existing doc):
```
### Fix-pack bucket lifecycle

`$FIX_PACK_BUCKET` should have a lifecycle rule that expires objects under
`fix-packs/` after 30 days. Bucket policy must deny public writes; signed URLs
with 24-hour expiry are the only supported access method.
```

- [ ] **Step 6: Run tests**

Run: `cd apps/api && pytest tests/test_supplier_fix_pack_s3.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```
git add -A
git commit -m "Wire S3 upload + signed URL into supplier-fix-pack endpoint"
```

---

## Task 3: Implement `notify-supplier` endpoint

**Files:**
- Modify: `apps/api/app/routers/importer.py` (fill in the stubbed endpoint body)
- Possibly: `apps/api/app/services/email.py` or similar (from Task 0 Step 2)

- [ ] **Step 1: Locate the existing stub**

Run: `grep -n "notify.supplier\|NotifySupplier" apps/api/app/routers/importer.py | head -5`
Expected: schema defined, endpoint body stubbed.

- [ ] **Step 2: Write a failing test**

Create `apps/api/tests/test_notify_supplier.py`:

```python
"""Tests that notify-supplier sends an email and records an audit row."""
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_notify_supplier_sends_email(
    authenticated_headers, importer_supplier_docs_session
):
    with patch("app.services.email.send_email") as send:
        send.return_value = {"id": "msg-abc", "sent_at": "2026-04-21T12:00:00Z"}

        resp = client.post(
            "/api/importer/notify-supplier",
            json={
                "validation_session_id": str(importer_supplier_docs_session.id),
                "supplier_email": "supplier@example.com",
                "message": "Please review the attached fix pack.",
                "lc_number": "LC-TEST-001",
            },
            headers=authenticated_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["notification_id"]
        assert body["sent_at"]
        send.assert_called_once()
        kwargs = send.call_args.kwargs
        assert kwargs["to"] == "supplier@example.com"
        assert "Please review" in kwargs["body"]


def test_notify_supplier_validates_email_format(authenticated_headers, importer_supplier_docs_session):
    resp = client.post(
        "/api/importer/notify-supplier",
        json={
            "validation_session_id": str(importer_supplier_docs_session.id),
            "supplier_email": "not-an-email",
            "message": "hi",
        },
        headers=authenticated_headers,
    )
    assert resp.status_code == 422  # EmailStr validation in pydantic
```

- [ ] **Step 3: Run to fail**

Run: `cd apps/api && pytest tests/test_notify_supplier.py -v`
Expected: FAIL.

- [ ] **Step 4: If no email service exists, create a minimal one**

If Task 0 Step 2 found nothing, create `apps/api/app/services/email.py`:

```python
"""Thin email sender. Defers to the configured provider."""
import logging
import os
import httpx

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, body: str, from_addr: str | None = None) -> dict:
    """Send via Resend (default) or SES. Returns {id, sent_at}."""
    provider = os.getenv("EMAIL_PROVIDER", "resend").lower()
    if provider == "resend":
        api_key = os.getenv("RESEND_API_KEY", "")
        if not api_key:
            raise RuntimeError("RESEND_API_KEY not set")
        resp = httpx.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "from": from_addr or os.getenv("EMAIL_FROM", "no-reply@trdrhub.com"),
                "to": [to],
                "subject": subject,
                "text": body,
            },
            timeout=15.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return {"id": data.get("id", ""), "sent_at": data.get("created_at", "")}

    # SES path (if needed)
    import boto3
    ses = boto3.client("ses", region_name=os.getenv("AWS_REGION", "us-east-1"))
    ses_resp = ses.send_email(
        Source=from_addr or os.getenv("EMAIL_FROM", "no-reply@trdrhub.com"),
        Destination={"ToAddresses": [to]},
        Message={
            "Subject": {"Data": subject},
            "Body": {"Text": {"Data": body}},
        },
    )
    return {"id": ses_resp.get("MessageId", ""), "sent_at": ""}
```

Append to `apps/api/.env.example`:
```
EMAIL_PROVIDER=resend
RESEND_API_KEY=
EMAIL_FROM=no-reply@trdrhub.com
```

- [ ] **Step 5: Implement the endpoint body**

Replace the stubbed body of `POST /api/importer/notify-supplier` in `importer.py`:

```python
from app.services.email import send_email

@router.post("/notify-supplier", response_model=NotifySupplierResponse)
async def notify_supplier(
    payload: NotifySupplierRequest,
    current_user: User = Depends(require_importer_user),
    db: Session = Depends(get_db),
    request: Request = None,
):
    session = (
        db.query(ValidationSession)
        .filter(ValidationSession.id == payload.validation_session_id)
        .first()
    )
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Validation session not found")

    subject = f"Document discrepancies for LC {payload.lc_number or ''}".strip()
    body_text = (payload.message or "") + (
        f"\n\nReview validation session: {session.id}\n"
        f"Presented by: {current_user.email}"
    )

    try:
        sent = send_email(
            to=payload.supplier_email,
            subject=subject,
            body=body_text,
        )
    except Exception as exc:
        logger.error("notify-supplier send failed: %s", exc)
        raise HTTPException(status_code=502, detail="Email send failed")

    AuditService.log(
        db=db,
        action=AuditAction.SUPPLIER_NOTIFIED,
        result=AuditResult.SUCCESS,
        user_id=current_user.id,
        resource_type="validation_session",
        resource_id=str(session.id),
        context={
            **(create_audit_context(request) if request else {}),
            "supplier_email": payload.supplier_email,
            "notification_id": sent["id"],
        },
    )

    return NotifySupplierResponse(
        success=True,
        message="Supplier notified",
        notification_id=sent["id"],
        sent_at=datetime.utcnow(),
    )
```

If `AuditAction.SUPPLIER_NOTIFIED` doesn't exist in the enum, add it in `apps/api/app/models/audit_log.py`.

- [ ] **Step 6: Run tests**

Run: `cd apps/api && pytest tests/test_notify_supplier.py -v`
Expected: 2/2 PASS.

- [ ] **Step 7: Commit**

```
git add -A
git commit -m "Implement notify-supplier endpoint with email + audit log"
```

---

## Task 4: Implement `bank-precheck` endpoint

**Files:**
- Modify: `apps/api/app/routers/importer.py` (fill in stub)
- Create: `apps/api/app/services/importer/bank_precheck.py`

- [ ] **Step 1: Write a failing test**

Create `apps/api/tests/test_bank_precheck.py`:

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_bank_precheck_returns_verdict_memo(
    authenticated_headers, importer_supplier_docs_session
):
    resp = client.post(
        "/api/importer/bank-precheck",
        json={
            "validation_session_id": str(importer_supplier_docs_session.id),
            "lc_number": "LC-TEST-001",
            "bank_name": "ExampleBank",
            "notes": "Please precheck before payment authorization.",
        },
        headers=authenticated_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "precheck_verdict" in body  # "approve" | "review" | "reject"
    assert body["precheck_verdict"] in ("approve", "review", "reject")
    assert "memo" in body
    assert "submitted_at" in body


def test_bank_precheck_tightens_threshold(
    authenticated_headers, importer_supplier_docs_session_with_minor_issues
):
    """Issues that would pass normal validation get escalated under precheck."""
    resp = client.post(
        "/api/importer/bank-precheck",
        json={
            "validation_session_id": str(importer_supplier_docs_session_with_minor_issues.id),
            "lc_number": "LC-TEST-002",
        },
        headers=authenticated_headers,
    )
    body = resp.json()
    # Precheck is stricter — 2+ minor issues should at least trigger review
    assert body["precheck_verdict"] in ("review", "reject")
```

- [ ] **Step 2: Run to fail**

Run: `cd apps/api && pytest tests/test_bank_precheck.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement the service**

Create `apps/api/app/services/importer/bank_precheck.py`:

```python
"""Bank precheck — stricter verdict over a completed validation session."""
from typing import Any, Dict, List


def compute_precheck_verdict(findings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Under precheck thresholds, any critical → reject; 2+ major or 3+ minor → review; else approve."""
    critical = sum(1 for f in findings if (f.get("severity") or "").lower() == "critical")
    major = sum(1 for f in findings if (f.get("severity") or "").lower() == "major")
    minor = sum(1 for f in findings if (f.get("severity") or "").lower() == "minor")

    if critical > 0:
        verdict = "reject"
    elif major >= 2 or minor >= 3:
        verdict = "review"
    elif major == 1:
        verdict = "review"  # precheck is tighter — exporter flow would allow this as pass
    else:
        verdict = "approve"

    return {
        "precheck_verdict": verdict,
        "counts": {"critical": critical, "major": major, "minor": minor},
    }


def build_memo(session, verdict_payload: Dict[str, Any], bank_name: str | None, notes: str | None) -> str:
    c = verdict_payload["counts"]
    lines = [
        f"Bank Precheck Memo",
        f"Session: {session.id}",
        f"Bank: {bank_name or '—'}",
        f"Verdict: {verdict_payload['precheck_verdict'].upper()}",
        f"Findings: {c['critical']} critical · {c['major']} major · {c['minor']} minor",
    ]
    if notes:
        lines.append("")
        lines.append(f"Operator notes: {notes}")
    return "\n".join(lines)
```

- [ ] **Step 4: Replace the endpoint body**

In `apps/api/app/routers/importer.py`, replace the stubbed `bank-precheck` body:

```python
from app.services.importer.bank_precheck import compute_precheck_verdict, build_memo


class BankPrecheckResponse(BaseModel):
    precheck_verdict: str
    counts: Dict[str, int]
    memo: str
    submitted_at: datetime


@router.post("/bank-precheck", response_model=BankPrecheckResponse)
async def bank_precheck(
    payload: BankPrecheckRequest,
    current_user: User = Depends(require_importer_user),
    db: Session = Depends(get_db),
    request: Request = None,
):
    session = (
        db.query(ValidationSession)
        .filter(ValidationSession.id == payload.validation_session_id)
        .first()
    )
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Validation session not found")

    findings = (session.structured_result or {}).get("issues", [])
    verdict_payload = compute_precheck_verdict(findings)
    memo = build_memo(session, verdict_payload, payload.bank_name, payload.notes)

    AuditService.log(
        db=db,
        action=AuditAction.BANK_PRECHECK,
        result=AuditResult.SUCCESS,
        user_id=current_user.id,
        resource_type="validation_session",
        resource_id=str(session.id),
        context={
            **(create_audit_context(request) if request else {}),
            "verdict": verdict_payload["precheck_verdict"],
            "bank_name": payload.bank_name,
        },
    )

    return BankPrecheckResponse(
        precheck_verdict=verdict_payload["precheck_verdict"],
        counts=verdict_payload["counts"],
        memo=memo,
        submitted_at=datetime.utcnow(),
    )
```

Add `AuditAction.BANK_PRECHECK` to `apps/api/app/models/audit_log.py` if missing.

- [ ] **Step 5: Run tests**

Run: `cd apps/api && pytest tests/test_bank_precheck.py -v`
Expected: 2/2 PASS.

- [ ] **Step 6: Commit**

```
git add -A
git commit -m "Implement bank-precheck endpoint with tightened verdict thresholds"
```

---

## Task 5: Frontend — `use-importer-actions` hooks

**Files:**
- Create: `apps/web/src/hooks/use-importer-actions.ts`
- Create: `apps/web/src/api/importer.ts` (if needed — check first)
- Create: `apps/web/src/hooks/__tests__/use-importer-actions.test.ts`

- [ ] **Step 1: Check existing importer API client**

Run: `cat apps/web/src/api/importer.ts 2>/dev/null || echo "FILE_NOT_PRESENT"`
Expected: either content or `FILE_NOT_PRESENT`. If present, extend; if absent, create.

- [ ] **Step 2: Write failing tests**

Create `apps/web/src/hooks/__tests__/use-importer-actions.test.ts`:

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  useAmendmentRequest,
  useSupplierFixPack,
  useNotifySupplier,
  useBankPrecheck,
} from "../use-importer-actions";

const postSpy = vi.fn();
vi.mock("@/api/client", () => ({
  default: {
    post: (...args: unknown[]) => postSpy(...args),
    get: () => Promise.resolve({ data: {} }),
  },
}));

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("importer action hooks", () => {
  beforeEach(() => postSpy.mockReset());

  it("useAmendmentRequest POSTs to the amendment-request endpoint", async () => {
    postSpy.mockResolvedValue({ data: new Blob([new Uint8Array([0x25, 0x50, 0x44, 0x46])], { type: "application/pdf" }) });
    const { result } = renderHook(() => useAmendmentRequest(), { wrapper });
    await result.current.mutateAsync({ validationSessionId: "s-1" });
    expect(postSpy.mock.calls[0][0]).toContain("/api/importer/amendment-request");
  });

  it("useSupplierFixPack POSTs to the supplier-fix-pack endpoint", async () => {
    postSpy.mockResolvedValue({ data: { download_url: "https://x", file_name: "fp.zip" } });
    const { result } = renderHook(() => useSupplierFixPack(), { wrapper });
    await result.current.mutateAsync({ validationSessionId: "s-2" });
    expect(postSpy.mock.calls[0][0]).toContain("/api/importer/supplier-fix-pack");
  });

  it("useNotifySupplier POSTs with supplier email + message", async () => {
    postSpy.mockResolvedValue({ data: { success: true, notification_id: "n-1", sent_at: "..." } });
    const { result } = renderHook(() => useNotifySupplier(), { wrapper });
    await result.current.mutateAsync({
      validationSessionId: "s-3",
      supplierEmail: "x@y.com",
      message: "hi",
    });
    expect(postSpy.mock.calls[0][0]).toContain("/api/importer/notify-supplier");
    expect(postSpy.mock.calls[0][1]).toMatchObject({ supplier_email: "x@y.com" });
  });

  it("useBankPrecheck POSTs and receives verdict", async () => {
    postSpy.mockResolvedValue({ data: { precheck_verdict: "approve", counts: {}, memo: "...", submitted_at: "..." } });
    const { result } = renderHook(() => useBankPrecheck(), { wrapper });
    const res = await result.current.mutateAsync({ validationSessionId: "s-4", lcNumber: "LC-1" });
    expect(res.precheck_verdict).toBe("approve");
  });
});
```

- [ ] **Step 3: Run to fail**

Run: `cd apps/web && npm run test -- use-importer-actions`
Expected: FAIL.

- [ ] **Step 4: Implement the hooks**

Create `apps/web/src/hooks/use-importer-actions.ts`:

```typescript
import { useMutation } from "@tanstack/react-query";
import apiClient from "@/api/client";

export interface AmendmentRequestVars {
  validationSessionId: string;
}

export interface SupplierFixPackVars {
  validationSessionId: string;
  lcNumber?: string;
}
export interface SupplierFixPackResult {
  download_url: string;
  file_name: string;
  generated_at: string;
  issue_count: number;
}

export interface NotifySupplierVars {
  validationSessionId: string;
  supplierEmail: string;
  message: string;
  lcNumber?: string;
}
export interface NotifySupplierResult {
  success: boolean;
  notification_id: string;
  sent_at: string;
}

export interface BankPrecheckVars {
  validationSessionId: string;
  lcNumber: string;
  bankName?: string;
  notes?: string;
}
export interface BankPrecheckResult {
  precheck_verdict: "approve" | "review" | "reject";
  counts: { critical: number; major: number; minor: number };
  memo: string;
  submitted_at: string;
}

export function useAmendmentRequest() {
  return useMutation({
    mutationFn: async (vars: AmendmentRequestVars): Promise<Blob> => {
      const resp = await apiClient.post(
        "/api/importer/amendment-request",
        { validation_session_id: vars.validationSessionId },
        { responseType: "blob" },
      );
      return resp.data as Blob;
    },
  });
}

export function useSupplierFixPack() {
  return useMutation({
    mutationFn: async (vars: SupplierFixPackVars): Promise<SupplierFixPackResult> => {
      const resp = await apiClient.post("/api/importer/supplier-fix-pack", {
        validation_session_id: vars.validationSessionId,
        lc_number: vars.lcNumber,
      });
      return resp.data as SupplierFixPackResult;
    },
  });
}

export function useNotifySupplier() {
  return useMutation({
    mutationFn: async (vars: NotifySupplierVars): Promise<NotifySupplierResult> => {
      const resp = await apiClient.post("/api/importer/notify-supplier", {
        validation_session_id: vars.validationSessionId,
        supplier_email: vars.supplierEmail,
        message: vars.message,
        lc_number: vars.lcNumber,
      });
      return resp.data as NotifySupplierResult;
    },
  });
}

export function useBankPrecheck() {
  return useMutation({
    mutationFn: async (vars: BankPrecheckVars): Promise<BankPrecheckResult> => {
      const resp = await apiClient.post("/api/importer/bank-precheck", {
        validation_session_id: vars.validationSessionId,
        lc_number: vars.lcNumber,
        bank_name: vars.bankName,
        notes: vars.notes,
      });
      return resp.data as BankPrecheckResult;
    },
  });
}
```

- [ ] **Step 5: Run tests to pass**

Run: `cd apps/web && npm run test -- use-importer-actions`
Expected: 4/4 PASS.

- [ ] **Step 6: Commit**

```
git add -A
git commit -m "Add use-importer-actions hooks for amendment, fix-pack, notify, precheck"
```

---

## Task 6: UI — `<DraftLcActions>` component

**Files:**
- Create: `apps/web/src/pages/importer/actions/DraftLcActions.tsx`
- Create: `apps/web/src/pages/importer/actions/__tests__/DraftLcActions.test.tsx`

- [ ] **Step 1: Write a failing test**

Create `apps/web/src/pages/importer/actions/__tests__/DraftLcActions.test.tsx`:

```typescript
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { DraftLcActions } from "../DraftLcActions";

vi.mock("@/hooks/use-importer-actions", () => ({
  useAmendmentRequest: () => ({
    mutateAsync: vi.fn().mockResolvedValue(new Blob(["%PDF-"], { type: "application/pdf" })),
    isPending: false,
  }),
}));

function renderActions() {
  const qc = new QueryClient();
  return render(
    <QueryClientProvider client={qc}>
      <DraftLcActions sessionId="s-1" />
    </QueryClientProvider>,
  );
}

describe("DraftLcActions", () => {
  it("renders Amendment Request button", () => {
    renderActions();
    expect(screen.getByRole("button", { name: /amendment request/i })).toBeInTheDocument();
  });

  it("triggers download on click", async () => {
    const createURL = vi.fn().mockReturnValue("blob:http://localhost/abc");
    Object.assign(URL, { createObjectURL: createURL, revokeObjectURL: vi.fn() });
    renderActions();
    fireEvent.click(screen.getByRole("button", { name: /amendment request/i }));
    await waitFor(() => expect(createURL).toHaveBeenCalled());
  });
});
```

- [ ] **Step 2: Run to fail**

Run: `cd apps/web && npm run test -- DraftLcActions`
Expected: FAIL.

- [ ] **Step 3: Implement**

Create `apps/web/src/pages/importer/actions/DraftLcActions.tsx`:

```typescript
import { Button } from "@/components/ui/button";
import { useAmendmentRequest } from "@/hooks/use-importer-actions";
import { Download } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

export interface DraftLcActionsProps {
  sessionId: string;
  lcNumber?: string;
}

export function DraftLcActions({ sessionId, lcNumber }: DraftLcActionsProps) {
  const amendment = useAmendmentRequest();
  const { toast } = useToast();

  const onDownload = async () => {
    try {
      const blob = await amendment.mutateAsync({ validationSessionId: sessionId });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `amendment-request-${lcNumber ?? sessionId}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
      toast({ title: "Amendment request downloaded", description: "Send to your issuing bank." });
    } catch {
      toast({ title: "Download failed", variant: "destructive" });
    }
  };

  return (
    <div className="flex flex-col gap-2">
      <Button onClick={onDownload} disabled={amendment.isPending}>
        <Download className="mr-2 h-4 w-4" />
        Download Amendment Request
      </Button>
    </div>
  );
}
```

- [ ] **Step 4: Run to pass**

Run: `cd apps/web && npm run test -- DraftLcActions`
Expected: PASS.

- [ ] **Step 5: Commit**

```
git add -A
git commit -m "Add DraftLcActions component with Amendment Request download"
```

---

## Task 7: UI — `<SupplierDocActions>` component

**Files:**
- Create: `apps/web/src/pages/importer/actions/SupplierDocActions.tsx`
- Create: `apps/web/src/pages/importer/actions/__tests__/SupplierDocActions.test.tsx`
- Create: `apps/web/src/pages/importer/actions/NotifySupplierDialog.tsx`

- [ ] **Step 1: Write failing test**

Create `apps/web/src/pages/importer/actions/__tests__/SupplierDocActions.test.tsx`:

```typescript
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SupplierDocActions } from "../SupplierDocActions";

vi.mock("@/hooks/use-importer-actions", () => ({
  useSupplierFixPack: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useNotifySupplier: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useBankPrecheck: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

function renderActions() {
  const qc = new QueryClient();
  return render(
    <QueryClientProvider client={qc}>
      <SupplierDocActions sessionId="s-1" />
    </QueryClientProvider>,
  );
}

describe("SupplierDocActions", () => {
  it("renders three action buttons", () => {
    renderActions();
    expect(screen.getByRole("button", { name: /fix pack/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /notify supplier/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /bank precheck/i })).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run to fail**

Run: `cd apps/web && npm run test -- SupplierDocActions`
Expected: FAIL.

- [ ] **Step 3: Implement `NotifySupplierDialog`**

Create `apps/web/src/pages/importer/actions/NotifySupplierDialog.tsx`:

```typescript
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger,
} from "@/components/ui/dialog";
import { useNotifySupplier } from "@/hooks/use-importer-actions";
import { useToast } from "@/hooks/use-toast";

export interface NotifySupplierDialogProps {
  sessionId: string;
  lcNumber?: string;
  trigger: React.ReactNode;
}

export function NotifySupplierDialog({ sessionId, lcNumber, trigger }: NotifySupplierDialogProps) {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [open, setOpen] = useState(false);
  const notify = useNotifySupplier();
  const { toast } = useToast();

  const onSend = async () => {
    try {
      await notify.mutateAsync({
        validationSessionId: sessionId,
        supplierEmail: email,
        message,
        lcNumber,
      });
      toast({ title: "Supplier notified" });
      setOpen(false);
    } catch {
      toast({ title: "Notify failed", variant: "destructive" });
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Notify Supplier</DialogTitle>
          <DialogDescription>Send discrepancy fix pack link to your supplier.</DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <div>
            <Label htmlFor="supplier-email">Supplier email</Label>
            <Input id="supplier-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div>
            <Label htmlFor="supplier-message">Message (optional)</Label>
            <Textarea id="supplier-message" value={message} onChange={(e) => setMessage(e.target.value)} rows={4} />
          </div>
        </div>
        <DialogFooter>
          <Button onClick={onSend} disabled={!email || notify.isPending}>
            {notify.isPending ? "Sending…" : "Send"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
```

- [ ] **Step 4: Implement `SupplierDocActions`**

Create `apps/web/src/pages/importer/actions/SupplierDocActions.tsx`:

```typescript
import { Button } from "@/components/ui/button";
import { Download, Send, ShieldCheck } from "lucide-react";
import { useSupplierFixPack, useBankPrecheck } from "@/hooks/use-importer-actions";
import { NotifySupplierDialog } from "./NotifySupplierDialog";
import { useToast } from "@/hooks/use-toast";

export interface SupplierDocActionsProps {
  sessionId: string;
  lcNumber?: string;
}

export function SupplierDocActions({ sessionId, lcNumber }: SupplierDocActionsProps) {
  const fixPack = useSupplierFixPack();
  const precheck = useBankPrecheck();
  const { toast } = useToast();

  const onFixPack = async () => {
    try {
      const result = await fixPack.mutateAsync({ validationSessionId: sessionId, lcNumber });
      window.open(result.download_url, "_blank", "noopener,noreferrer");
      toast({ title: "Fix pack generated" });
    } catch {
      toast({ title: "Fix pack failed", variant: "destructive" });
    }
  };

  const onPrecheck = async () => {
    try {
      const result = await precheck.mutateAsync({
        validationSessionId: sessionId,
        lcNumber: lcNumber ?? "",
      });
      toast({
        title: `Precheck: ${result.precheck_verdict.toUpperCase()}`,
        description: result.memo.split("\n")[0] ?? "",
      });
    } catch {
      toast({ title: "Precheck failed", variant: "destructive" });
    }
  };

  return (
    <div className="flex flex-col gap-2">
      <Button onClick={onFixPack} disabled={fixPack.isPending}>
        <Download className="mr-2 h-4 w-4" />
        Generate Fix Pack
      </Button>
      <NotifySupplierDialog
        sessionId={sessionId}
        lcNumber={lcNumber}
        trigger={
          <Button variant="secondary">
            <Send className="mr-2 h-4 w-4" />
            Notify Supplier
          </Button>
        }
      />
      <Button variant="outline" onClick={onPrecheck} disabled={precheck.isPending}>
        <ShieldCheck className="mr-2 h-4 w-4" />
        Bank Precheck
      </Button>
    </div>
  );
}
```

- [ ] **Step 5: Run tests**

Run: `cd apps/web && npm run test -- SupplierDocActions`
Expected: PASS.

- [ ] **Step 6: Commit**

```
git add -A
git commit -m "Add SupplierDocActions component with fix-pack, notify-supplier dialog, and precheck"
```

---

## Task 8: Wire action components into `ImportResults`

**Files:**
- Modify: `apps/web/src/pages/ImportResults.tsx`

- [ ] **Step 1: Add action slot wiring**

Edit `apps/web/src/pages/ImportResults.tsx` — replace the placeholder `actionSlot={null}` from Phase 2 with:

```typescript
import { DraftLcActions } from "./importer/actions/DraftLcActions";
import { SupplierDocActions } from "./importer/actions/SupplierDocActions";

// ...inside the component:
const lcNumber =
  data.structured_result?.lc_structured?.fields?.lc_number ??
  data.structured_result?.lc_structured?.fields?.number;

const actionSlot =
  workflowType === "importer_draft_lc" ? (
    <DraftLcActions sessionId={jobId!} lcNumber={lcNumber} />
  ) : workflowType === "importer_supplier_docs" ? (
    <SupplierDocActions sessionId={jobId!} lcNumber={lcNumber} />
  ) : null;

// ...then in the VerdictTab render:
<VerdictTab results={results} actionSlot={actionSlot} />
```

- [ ] **Step 2: Type-check**

Run: `cd apps/web && npm run type-check`
Expected: PASS.

- [ ] **Step 3: Manual smoke**

Run dev server, navigate to a Moment 1 results page — verify Amendment Request button renders. Navigate to a Moment 2 results — verify 3 buttons render. Click each and verify network calls fire.

- [ ] **Step 4: Commit**

```
git add -A
git commit -m "Wire moment-aware action slot into ImportResults"
```

---

## Task 9: Phase 3 final verification

**Files:**
- Verify: all

- [ ] **Step 1: Backend test sweep**

Run: `cd apps/api && pytest tests/ -v -m "not slow"`
Expected: all PASS including the 4 new action-endpoint tests.

- [ ] **Step 2: Frontend test sweep**

Run: `cd apps/web && npm run type-check && npm run lint && npm run test`
Expected: all PASS.

- [ ] **Step 3: Manual e2e with real side effects**

With dev server + real S3 + test email provider:
- **Moment 1 flow:** upload a draft LC, validate, click "Download Amendment Request" → PDF downloads
- **Moment 2 flow:** upload LC + supplier docs, validate, click "Generate Fix Pack" → real S3 signed URL, download works
- **Moment 2 flow:** click "Notify Supplier" → dialog opens, fill email+message, send → real email arrives at sandbox address
- **Moment 2 flow:** click "Bank Precheck" → toast with verdict; check `audit_log` table for row

- [ ] **Step 4: Audit log verification**

Run:
```
psql $DATABASE_URL -c "SELECT action, resource_type, context FROM audit_logs ORDER BY created_at DESC LIMIT 10;"
```
Expected: rows for `DOCUMENT_GENERATED`, `SUPPLIER_NOTIFIED`, `BANK_PRECHECK` from the manual flows.

- [ ] **Step 5: No commit — verification only**

---

## Phase 3 Exit Criteria

- [ ] All 4 action endpoints implemented with real side effects (S3 upload, email send, precheck memo, PDF generation)
- [ ] Audit-log row written for every action
- [ ] Frontend hooks (`use-importer-actions`) with full test coverage
- [ ] `<DraftLcActions>` and `<SupplierDocActions>` components rendered in `ImportResults` based on `workflow_type`
- [ ] Integration tests + manual e2e confirm real side effects

Phase 3 complete. Proceed to Phase 4 plan.
