"""Versioned Proofline report generation on TRDRHub's existing Report/S3 rails."""

from __future__ import annotations

import html
import os
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.models import (
    Document,
    ProoflineFinding,
    RemediationAction,
    Report,
    TradeCase,
    TradeCaseCheckRun,
    TradeCaseDecision,
    TradeCaseDocument,
    TradeCaseEvent,
    TradeCaseParty,
    User,
)
from app.services.lc_report import _html_to_pdf


class ProoflineReportError(RuntimeError):
    """A reviewer-approved report could not be safely finalized."""


def _esc(value: Any) -> str:
    return html.escape(str(value if value is not None else "")).strip()


def _display(value: Any, fallback: str = "Not provided") -> str:
    if value in (None, "", [], {}):
        return fallback
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return format(value, "f")
    return str(value)


def load_report_context(
    db: Session,
    *,
    trade_case: TradeCase,
    decision: TradeCaseDecision,
    reviewer: User,
) -> dict[str, Any]:
    parties = (
        db.query(TradeCaseParty)
        .filter(TradeCaseParty.trade_case_id == trade_case.id)
        .order_by(TradeCaseParty.created_at.asc())
        .all()
    )
    documents = (
        db.query(TradeCaseDocument, Document)
        .join(Document, Document.id == TradeCaseDocument.document_id)
        .filter(TradeCaseDocument.trade_case_id == trade_case.id)
        .order_by(TradeCaseDocument.logical_key.asc(), TradeCaseDocument.version_number.asc())
        .all()
    )
    check_rows = (
        db.query(TradeCaseCheckRun)
        .filter(TradeCaseCheckRun.trade_case_id == trade_case.id)
        .order_by(TradeCaseCheckRun.created_at.asc())
        .all()
    )
    latest_checks: dict[str, TradeCaseCheckRun] = {}
    for item in check_rows:
        latest_checks[item.module] = item
    findings = (
        db.query(ProoflineFinding)
        .filter(
            ProoflineFinding.trade_case_id == trade_case.id,
            ProoflineFinding.visibility == "customer",
        )
        .order_by(ProoflineFinding.created_at.asc())
        .all()
    )
    finding_ids = {item.id for item in findings}
    actions = (
        db.query(RemediationAction)
        .filter(RemediationAction.trade_case_id == trade_case.id)
        .order_by(RemediationAction.created_at.asc())
        .all()
    )
    actions = [item for item in actions if item.finding_id in finding_ids]
    return {
        "case": {
            "case_reference": trade_case.case_reference,
            "title": trade_case.title,
            "payment_arrangement": trade_case.payment_arrangement,
            "origin_country": trade_case.origin_country,
            "destination_country": trade_case.destination_country,
            "currency": trade_case.currency,
            "amount": _display(trade_case.amount),
            "shipment_date": _display(trade_case.shipment_date),
            "payment_terms": trade_case.payment_terms,
        },
        "decision": {
            "decision": decision.decision,
            "summary": decision.summary,
            "reason": decision.reason,
            "decided_at": _display(decision.decided_at),
            "system_version": decision.system_version,
        },
        "reviewer": {
            "id": str(reviewer.id),
            "name": getattr(reviewer, "full_name", None) or reviewer.email,
        },
        "parties": [
            {
                "role": item.role,
                "name": item.name,
                "country_code": item.country_code,
            }
            for item in parties
        ],
        "documents": [
            {
                "filename": document.original_filename,
                "document_type": association.document_type,
                "version": association.version_number,
                "correction_round": association.correction_round,
                "is_current": association.is_current,
            }
            for association, document in documents
        ],
        "checks": [
            {
                "module": item.module,
                "state": item.state,
                "applicable": item.applicable,
                "summary": (item.result_summary or {}).get("summary")
                or item.safe_error_message
                or item.applicability_reason,
            }
            for item in latest_checks.values()
            if item.applicable or item.state == "not_applicable"
        ],
        "findings": [
            {
                "severity": item.severity,
                "title": item.title,
                "explanation": item.explanation,
                "expected": item.expected,
                "observed": item.observed,
                "suggested_correction": item.suggested_correction,
                "status": item.status,
                "rule_reference": item.rule_reference,
                "evidence_references": item.evidence_references or [],
            }
            for item in findings
        ],
        "actions": [
            {
                "requested_action": item.requested_action,
                "responsible_party": item.responsible_party,
                "requested_document_type": item.requested_document_type,
                "status": item.status,
                "customer_response": item.customer_response,
                "resolution_notes": item.resolution_notes,
            }
            for item in actions
        ],
    }


def _table(rows: list[list[Any]], headings: list[str], *, empty: str) -> str:
    if not rows:
        return f'<p class="empty">{_esc(empty)}</p>'
    head = "".join(f"<th>{_esc(item)}</th>" for item in headings)
    body = "".join(
        "<tr>" + "".join(f"<td>{_esc(_display(cell, '—'))}</td>" for cell in row) + "</tr>"
        for row in rows
    )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def build_report_html(context: dict[str, Any]) -> str:
    case = context["case"]
    decision = context["decision"]
    reviewer = context["reviewer"]
    report = context.get("report") or {}
    party_table = _table(
        [[item.get("role"), item.get("name"), item.get("country_code")] for item in context.get("parties", [])],
        ["Role", "Party", "Country"],
        empty="No party records were available.",
    )
    document_table = _table(
        [
            [
                item.get("document_type"),
                item.get("filename"),
                item.get("version"),
                "Current" if item.get("is_current", True) else "Superseded",
            ]
            for item in context.get("documents", [])
        ],
        ["Document", "File", "Version", "Status"],
        empty="No document records were available.",
    )
    check_table = _table(
        [[item.get("module"), item.get("state"), item.get("summary")] for item in context.get("checks", [])],
        ["Module", "Result", "Summary"],
        empty="No automated check records were available.",
    )
    findings: list[str] = []
    for item in context.get("findings", []):
        rule = item.get("rule_reference") or {}
        rule_label = " · ".join(
            str(value)
            for value in (rule.get("source"), rule.get("id"), rule.get("article"))
            if value
        )
        findings.append(
            f'''<article class="finding">
              <div class="finding-head"><span class="severity">{_esc(item.get("severity"))}</span><strong>{_esc(item.get("title"))}</strong><span class="status">{_esc(item.get("status"))}</span></div>
              <p>{_esc(item.get("explanation"))}</p>
              <div class="trace"><div><b>Expected</b>{_esc(item.get("expected"))}</div><div><b>Found</b>{_esc(item.get("observed"))}</div><div><b>Suggested fix</b>{_esc(item.get("suggested_correction"))}</div></div>
              {f'<div class="rule"><b>Rule or policy</b> {_esc(rule_label)}</div>' if rule_label else ''}
            </article>'''
        )
    action_table = _table(
        [[item.get("requested_action"), item.get("responsible_party"), item.get("status")] for item in context.get("actions", [])],
        ["Required action", "Responsible party", "Status"],
        empty="No customer actions remain recorded.",
    )
    generated = report.get("generated_at") or datetime.now(timezone.utc).strftime("%d %b %Y %H:%M UTC")
    return f'''<!doctype html><html><head><meta charset="utf-8"><style>
      @page {{ size: A4; margin: 18mm; }}
      body {{ font-family: -apple-system, Segoe UI, Arial, sans-serif; color: #17352d; font-size: 10.5px; line-height: 1.45; }}
      .header {{ border-bottom: 4px solid #B2F273; padding: 0 0 13px; margin-bottom: 18px; }}
      .brand {{ color: #5e746e; font-size: 9px; letter-spacing: 1.5px; text-transform: uppercase; }}
      h1 {{ margin: 3px 0 0; color: #00261C; font-size: 24px; }} h2 {{ color: #00261C; font-size: 15px; margin: 22px 0 8px; }}
      .descriptor {{ color: #4f6962; font-size: 12px; }}
      .decision {{ background: #EDF5F2; border: 1px solid #c9ddd6; border-left: 5px solid #00382E; padding: 14px; border-radius: 6px; }}
      .decision strong {{ display: block; font-size: 17px; color: #00382E; margin-bottom: 5px; }}
      .meta {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin: 14px 0; }}
      .meta div {{ background: #f7faf9; padding: 8px; border-radius: 4px; }} .meta b, .trace b {{ display: block; color: #6e837d; font-size: 8px; text-transform: uppercase; letter-spacing: .6px; }}
      table {{ width: 100%; border-collapse: collapse; }} th {{ text-align: left; color: #5e746e; font-size: 8px; text-transform: uppercase; letter-spacing: .5px; border-bottom: 2px solid #d5e2de; padding: 6px; }} td {{ padding: 7px 6px; border-bottom: 1px solid #e3ebe8; vertical-align: top; }}
      .finding {{ page-break-inside: avoid; border: 1px solid #d5e2de; border-left: 4px solid #d89b28; border-radius: 5px; padding: 10px; margin: 9px 0; }}
      .finding-head {{ display: flex; gap: 8px; align-items: center; }} .severity, .status {{ font-size: 8px; text-transform: uppercase; border: 1px solid #ccd9d5; border-radius: 10px; padding: 2px 6px; }} .status {{ margin-left: auto; }}
      .trace {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 7px; margin-top: 8px; }} .trace div {{ background: #f7faf9; padding: 7px; border-radius: 4px; }}
      .rule {{ margin-top: 7px; color: #4f6962; font-size: 9px; }} .approval {{ border: 1px solid #c9ddd6; padding: 10px; border-radius: 5px; }}
      .empty {{ color: #778b85; font-style: italic; }} .disclaimer {{ margin-top: 24px; padding-top: 12px; border-top: 1px solid #ccd9d5; color: #667c76; font-size: 8.5px; }}
    </style></head><body>
      <header class="header"><div class="brand">TRDR Hub · Proofline</div><h1>Verified Trade Clearance</h1><div class="descriptor">Identify the document, compliance, identity, and evidence issues that could delay shipment, presentation, or payment.</div></header>
      <section class="decision"><span>Overall decision</span><strong>{_esc(decision.get("decision"))}</strong><div>{_esc(decision.get("summary"))}</div><p><b>Decision reason:</b> {_esc(decision.get("reason"))}</p></section>
      <div class="meta"><div><b>Trade case</b>{_esc(case.get("case_reference"))}</div><div><b>Payment arrangement</b>{_esc(case.get("payment_arrangement"))}</div><div><b>Generated</b>{_esc(generated)}</div><div><b>Route</b>{_esc(case.get("origin_country"))} → {_esc(case.get("destination_country"))}</div><div><b>Transaction value</b>{_esc(case.get("currency"))} {_esc(case.get("amount"))}</div><div><b>Shipment date</b>{_esc(case.get("shipment_date"))}</div></div>
      <h2>Trade-case summary</h2><p><strong>{_esc(case.get("title"))}</strong></p><p><b>Payment terms:</b> {_esc(case.get("payment_terms"))}</p>
      <h2>Scope of work</h2><p>Proofline reviewed the submitted parties, current and superseded evidence, applicable TRDR Hub checks, rule and policy references, and reviewer-confirmed remediation status.</p>
      <h2>Parties</h2>{party_table}
      <h2>Products and shipment</h2><p>Origin: {_esc(case.get("origin_country"))} · Destination: {_esc(case.get("destination_country"))} · Shipment: {_esc(case.get("shipment_date"))}</p>
      <h2>Documents reviewed</h2>{document_table}
      <h2>Applicable checks</h2>{check_table}
      <h2>Findings and required actions</h2>{''.join(findings) if findings else '<p class="empty">No customer-visible findings were recorded.</p>'}{action_table}
      <h2>Reviewer approval</h2><div class="approval"><b>Reviewer</b> {_esc(reviewer.get("name"))}<br><b>Decision timestamp</b> {_esc(decision.get("decided_at"))}<br><b>System version</b> {_esc(decision.get("system_version"))}<br><b>Report version</b> {_esc(report.get("version"))}<br><b>Report ID</b> {_esc(report.get("id"))}</div>
      <div class="disclaimer">Proofline identifies preventable discrepancies, evidence gaps, regulatory issues, and transaction risks based on the information submitted. This report is not legal advice or a legal or regulatory certification. It is not a customs decision and not a bank guarantee. It is not a guarantee of payment, shipment acceptance, customs clearance, bank acceptance, regulatory approval, or financing approval.</div>
    </body></html>'''


def _upload_report(*, payload: bytes, key: str, content_type: str) -> None:
    from app.utils.s3_client import get_s3_client

    get_s3_client().put_object(
        Bucket=os.getenv("S3_BUCKET_NAME", "lcopilot-documents"),
        Key=key,
        Body=payload,
        ContentType=content_type,
    )


def generate_proofline_report(
    db: Session,
    *,
    trade_case: TradeCase,
    decision: TradeCaseDecision,
    reviewer: User,
) -> Report:
    if decision.decision_type != "final":
        raise ProoflineReportError("Only a final reviewer decision can produce a report")
    session_id = trade_case.document_session_id or trade_case.source_lcopilot_session_id
    if session_id is None:
        raise ProoflineReportError("The trade case has no report-compatible document session")
    if trade_case.final_report_id:
        existing = db.query(Report).filter(Report.id == trade_case.final_report_id).first()
        if existing is not None:
            return existing
    latest = (
        db.query(Report)
        .filter(Report.validation_session_id == session_id)
        .order_by(Report.report_version.desc())
        .first()
    )
    version = (latest.report_version + 1) if latest is not None else 1
    report_id = uuid.uuid4()
    context = load_report_context(
        db, trade_case=trade_case, decision=decision, reviewer=reviewer
    )
    context["report"] = {
        "id": str(report_id),
        "version": version,
        "generated_at": datetime.now(timezone.utc).strftime("%d %b %Y %H:%M UTC"),
    }
    report_html = build_report_html(context)
    pdf = _html_to_pdf(report_html)
    payload = pdf if pdf is not None else report_html.encode("utf-8")
    extension = "pdf" if pdf is not None else "html"
    content_type = "application/pdf" if pdf is not None else "text/html; charset=utf-8"
    key = f"reports/{session_id}/proofline/{trade_case.id}/{report_id}.{extension}"
    try:
        _upload_report(payload=payload, key=key, content_type=content_type)
    except Exception as exc:
        raise ProoflineReportError("The clearance report could not be stored safely") from exc

    findings = context.get("findings", [])
    report = Report(
        id=report_id,
        validation_session_id=session_id,
        report_version=version,
        s3_key=key,
        file_size=len(payload),
        total_discrepancies=len(findings),
        critical_discrepancies=sum(item.get("severity") == "critical" for item in findings),
        major_discrepancies=sum(item.get("severity") == "high" for item in findings),
        minor_discrepancies=sum(item.get("severity") in {"medium", "low", "info"} for item in findings),
        generated_by_user_id=reviewer.id,
    )
    db.add(report)
    trade_case.final_report_id = report.id
    decision.report_version = version
    db.add(
        TradeCaseEvent(
            id=uuid.uuid4(),
            company_id=trade_case.company_id,
            trade_case_id=trade_case.id,
            event_type="final_report_generated",
            from_status=getattr(trade_case, "status", None),
            to_status=getattr(trade_case, "status", None),
            actor_type="reviewer",
            actor_user_id=reviewer.id,
            reason="Reviewer-approved Proofline clearance report generated",
            details={"report_id": str(report.id), "report_version": version},
            idempotency_key=f"final-report:{decision.id}",
            occurred_at=datetime.now(timezone.utc),
        )
    )
    db.flush()
    return report


__all__ = [
    "ProoflineReportError",
    "build_report_html",
    "generate_proofline_report",
    "load_report_context",
]
