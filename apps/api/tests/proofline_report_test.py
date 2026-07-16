"""Proofline final report composition, persistence, and customer safety."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

from app.models import Report
from app.services.proofline import reports


def _context():
    return {
        "case": {
            "case_reference": "PL-REPORT1",
            "title": "US buyer shipment",
            "payment_arrangement": "open_account",
            "origin_country": "BD",
            "destination_country": "US",
            "currency": "USD",
            "amount": "125000.00",
            "shipment_date": "2026-07-20",
            "payment_terms": "Net 60 after invoice approval",
        },
        "decision": {
            "decision": "CONDITIONAL_CLEARANCE",
            "summary": "Proceed after the listed evidence correction.",
            "reason": "One credential must be renewed.",
            "decided_at": "2026-07-16T12:00:00+00:00",
            "system_version": "proofline-v1",
        },
        "reviewer": {"name": "Trade Analyst", "id": str(uuid.uuid4())},
        "parties": [
            {"role": "buyer", "name": "US Buyer Inc", "country_code": "US"},
            {"role": "seller", "name": "Dhaka Exporter Ltd", "country_code": "BD"},
        ],
        "documents": [
            {"filename": "invoice.pdf", "document_type": "commercial_invoice", "version": 2},
        ],
        "checks": [
            {"module": "sanctions", "state": "clear", "summary": "No matches found"},
            {"module": "eudr", "state": "not_applicable", "summary": "Outside scope"},
        ],
        "findings": [
            {
                "severity": "high",
                "title": "Credential expired",
                "explanation": "The factory credential expired.",
                "expected": "A current credential",
                "observed": "Expired on 30 June",
                "suggested_correction": "Upload the renewed credential.",
                "status": "customer_action_required",
                "rule_reference": {"id": "BUYER-ENV-1", "source": "Buyer policy"},
            }
        ],
        "actions": [
            {"requested_action": "Upload renewed credential", "status": "requested"},
        ],
        "report": {"id": "RPT-1", "version": 1, "generated_at": "16 Jul 2026"},
    }


def test_report_html_contains_required_sections_traceability_and_disclaimer():
    html = reports.build_report_html(_context())

    for label in (
        "Verified Trade Clearance",
        "Overall decision",
        "Parties",
        "Documents reviewed",
        "Applicable checks",
        "Findings and required actions",
        "Reviewer approval",
        "Report version",
    ):
        assert label in html
    assert "Expected" in html and "Found" in html and "Suggested fix" in html
    assert "BUYER-ENV-1" in html
    assert "not a bank guarantee" in html.lower()
    assert "guarantee of payment" in html.lower()


class _Query:
    def filter(self, *_args):
        return self

    def order_by(self, *_args):
        return self

    def first(self):
        return None


class _Db:
    def __init__(self):
        self.added = []

    def query(self, model):
        assert model is Report
        return _Query()

    def add(self, value):
        self.added.append(value)

    def flush(self):
        return None


def test_generate_report_uploads_existing_report_record_and_links_version(monkeypatch):
    db = _Db()
    case_id = uuid.uuid4()
    session_id = uuid.uuid4()
    reviewer_id = uuid.uuid4()
    trade_case = SimpleNamespace(
        id=case_id,
        case_reference="PL-REPORT1",
        company_id=uuid.uuid4(),
        document_session_id=session_id,
        source_lcopilot_session_id=None,
        final_report_id=None,
    )
    decision = SimpleNamespace(
        id=uuid.uuid4(), decision_type="final", report_version=None
    )
    reviewer = SimpleNamespace(id=reviewer_id, full_name="Trade Analyst")
    uploads = []

    monkeypatch.setattr(reports, "load_report_context", lambda *_args, **_kwargs: _context())
    monkeypatch.setattr(reports, "_html_to_pdf", lambda _html: b"%PDF-proofline")
    monkeypatch.setattr(
        reports,
        "_upload_report",
        lambda *, payload, key, content_type: uploads.append((payload, key, content_type)),
    )

    report = reports.generate_proofline_report(
        db, trade_case=trade_case, decision=decision, reviewer=reviewer
    )

    assert isinstance(report, Report)
    assert report.validation_session_id == session_id
    assert report.report_version == 1
    assert report.generated_by_user_id == reviewer_id
    assert report.s3_key.startswith(f"reports/{session_id}/proofline/{case_id}/")
    assert uploads[0][0] == b"%PDF-proofline"
    assert uploads[0][2] == "application/pdf"
    assert trade_case.final_report_id == report.id
    assert decision.report_version == 1
