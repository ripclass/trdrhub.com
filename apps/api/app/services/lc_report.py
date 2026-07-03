"""Cited LC discrepancy report — Phase 1 launch (concierge deliverable).

Renders a ValidationSession's ``structured_result`` into a professional,
bank-ready PDF: findings grouped by severity, each carrying its rule citation,
the LC clause it derives from, the evidence found in the document, and a
suggested fix — plus the mandatory advisory footer. This is the artifact the
customer forwards to their bank at the $49 memo tier.

WeasyPrint is imported lazily and guarded (native deps are absent on Windows
dev). When it is unavailable the report row is still created with an HTML
fallback stored to S3, so delivery never hard-fails on the PDF engine.
"""

from __future__ import annotations

import html
import logging
import os
from datetime import datetime, timezone
from io import BytesIO
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

_ADVISORY_FOOTER = (
    "Advisory document pre-check — not legal advice. This report reflects an "
    "automated examination against UCP 600 / ISBP 821 reviewed by a specialist. "
    "It does not constitute a bank's determination of compliance."
)

_SEVERITY_ORDER = ["critical", "major", "minor", "advisory", "info"]


def _esc(v: Any) -> str:
    return html.escape(str(v if v is not None else "")).strip()


def _severity_of(issue: Dict[str, Any]) -> str:
    raw = str(issue.get("severity") or issue.get("level") or "minor").strip().lower()
    if raw in ("high", "critical", "reject"):
        return "critical"
    if raw in ("medium", "major", "discrepancy"):
        return "major"
    if raw in ("advisory", "warning", "warn"):
        return "advisory"
    if raw in ("info", "informational"):
        return "info"
    return "minor"


def _collect_issues(structured_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    issues = structured_result.get("issues")
    if isinstance(issues, list):
        return [i for i in issues if isinstance(i, dict)]
    return []


def build_report_html(session, structured_result: Dict[str, Any], review_note: Optional[str]) -> str:
    """Build the standalone HTML for the cited report."""
    issues = _collect_issues(structured_result)
    verdict = structured_result.get("bank_verdict") or structured_result.get("verdict") or {}
    verdict_label = _esc(
        (verdict.get("status") if isinstance(verdict, dict) else verdict) or "reviewed"
    ).upper()

    by_sev: Dict[str, List[Dict[str, Any]]] = {}
    for issue in issues:
        by_sev.setdefault(_severity_of(issue), []).append(issue)

    generated = datetime.now(timezone.utc).strftime("%d %b %Y %H:%M UTC")
    lc_number = _esc(structured_result.get("lc_number") or structured_result.get("lc_reference") or "—")

    rows: List[str] = []
    total = 0
    for sev in _SEVERITY_ORDER:
        group = by_sev.get(sev) or []
        if not group:
            continue
        rows.append(f'<h2 class="sev sev-{sev}">{sev.title()} ({len(group)})</h2>')
        for issue in group:
            total += 1
            title = _esc(issue.get("title") or issue.get("message") or issue.get("summary") or "Finding")
            rule = _esc(issue.get("rule") or issue.get("rule_id") or "")
            clause = _esc(issue.get("clause_cited") or issue.get("clause") or "")
            evidence = _esc(issue.get("found_evidence") or issue.get("found") or issue.get("evidence") or "")
            expected = _esc(issue.get("expected") or "")
            fix = _esc(issue.get("suggested_fix") or issue.get("fix") or issue.get("recommendation") or "")
            doc = _esc(issue.get("document_type") or issue.get("document") or "")
            parts = [f'<div class="finding sev-{sev}">', f'<div class="f-title">{title}</div>']
            meta = " · ".join(p for p in [f"Rule {rule}" if rule else "", f"Doc: {doc}" if doc else ""] if p)
            if meta:
                parts.append(f'<div class="f-meta">{meta}</div>')
            if clause:
                parts.append(f'<div class="f-row"><span>LC clause</span><p>{clause}</p></div>')
            if expected:
                parts.append(f'<div class="f-row"><span>Expected</span><p>{expected}</p></div>')
            if evidence:
                parts.append(f'<div class="f-row"><span>Found</span><p>{evidence}</p></div>')
            if fix:
                parts.append(f'<div class="f-row fix"><span>Suggested fix</span><p>{fix}</p></div>')
            parts.append("</div>")
            rows.append("".join(parts))

    if total == 0:
        rows.append('<div class="clean">No discrepancies found. The presentation set passed every check.</div>')

    note_html = f'<div class="note"><h3>Reviewer note</h3><p>{_esc(review_note)}</p></div>' if review_note else ""

    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
      body {{ font-family: -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; color: #1a2230; font-size: 12px; }}
      .hdr {{ border-bottom: 3px solid #0f3d3e; padding-bottom: 12px; margin-bottom: 18px; }}
      .hdr h1 {{ margin: 0; font-size: 20px; color: #0f3d3e; }}
      .hdr .sub {{ color: #556; font-size: 11px; margin-top: 4px; }}
      .meta-grid {{ display: flex; gap: 24px; margin: 12px 0 20px; font-size: 11px; }}
      .meta-grid b {{ display: block; color: #889; font-weight: 600; text-transform: uppercase; font-size: 9px; letter-spacing: .5px; }}
      .verdict {{ display: inline-block; padding: 4px 12px; border-radius: 4px; font-weight: 700; background: #eef; color: #0f3d3e; }}
      h2.sev {{ font-size: 13px; margin: 22px 0 8px; padding-bottom: 4px; border-bottom: 1px solid #dde; }}
      .sev-critical {{ color: #b3261e; }} .sev-major {{ color: #b06a00; }}
      .sev-minor {{ color: #4a5568; }} .sev-advisory {{ color: #2b6cb0; }}
      .finding {{ border-left: 3px solid #ccd; padding: 8px 12px; margin: 8px 0; background: #fafbfc; border-radius: 0 4px 4px 0; }}
      .finding.sev-critical {{ border-left-color: #b3261e; }} .finding.sev-major {{ border-left-color: #b06a00; }}
      .f-title {{ font-weight: 600; margin-bottom: 3px; }}
      .f-meta {{ color: #889; font-size: 10px; margin-bottom: 6px; }}
      .f-row {{ margin: 3px 0; }} .f-row span {{ display: inline-block; width: 90px; color: #889; font-size: 10px; vertical-align: top; }}
      .f-row p {{ display: inline-block; margin: 0; width: calc(100% - 100px); }}
      .f-row.fix p {{ color: #0f3d3e; }}
      .clean {{ padding: 16px; background: #eefaf0; border-radius: 6px; color: #1a7a3a; font-weight: 600; }}
      .note {{ margin: 18px 0; padding: 12px; background: #f4f6ff; border-radius: 6px; }}
      .note h3 {{ margin: 0 0 6px; font-size: 12px; }}
      .footer {{ margin-top: 28px; padding-top: 12px; border-top: 1px solid #dde; color: #889; font-size: 9px; }}
    </style></head><body>
      <div class="hdr">
        <h1>LC Discrepancy Report</h1>
        <div class="sub">TRDR Hub · LCopilot — pre-presentation examination</div>
      </div>
      <div class="meta-grid">
        <div><b>LC Reference</b>{lc_number}</div>
        <div><b>Verdict</b><span class="verdict">{verdict_label}</span></div>
        <div><b>Findings</b>{total}</div>
        <div><b>Generated</b>{_esc(generated)}</div>
      </div>
      {note_html}
      {''.join(rows)}
      <div class="footer">{_esc(_ADVISORY_FOOTER)}</div>
    </body></html>"""


def _html_to_pdf(html_content: str) -> Optional[bytes]:
    """Render HTML → PDF bytes via WeasyPrint. Returns None if unavailable."""
    try:
        from weasyprint import HTML  # type: ignore
    except Exception as exc:  # pragma: no cover - env dependent
        logger.warning("WeasyPrint unavailable, storing HTML fallback: %s", exc)
        return None
    buf = BytesIO()
    HTML(string=html_content).write_pdf(buf)
    return buf.getvalue()


def generate_lc_report(db, session, user, structured_result: Dict[str, Any], review_note: Optional[str] = None):
    """Generate + persist the cited report, upload to storage, return a Report row.

    Never raises on the render/upload path — on failure it still returns a Report
    row (with a null s3_key) so delivery can proceed; the customer always has the
    results UI as the cited surface.
    """
    from app.models import Report
    from app.utils.s3_client import get_s3_client

    issues = _collect_issues(structured_result)
    counts = {"critical": 0, "major": 0, "minor": 0}
    for issue in issues:
        sev = _severity_of(issue)
        if sev == "critical":
            counts["critical"] += 1
        elif sev == "major":
            counts["major"] += 1
        else:
            counts["minor"] += 1

    html_content = build_report_html(session, structured_result, review_note)
    report_id = uuid4()
    s3_key: Optional[str] = None
    file_size = 0

    try:
        pdf_bytes = _html_to_pdf(html_content)
        payload = pdf_bytes if pdf_bytes is not None else html_content.encode("utf-8")
        ext = "pdf" if pdf_bytes is not None else "html"
        s3_key = f"reports/{session.id}/{report_id}.{ext}"
        bucket = os.getenv("S3_BUCKET_NAME", "lcopilot-documents")
        content_type = "application/pdf" if pdf_bytes is not None else "text/html"
        client = get_s3_client()
        client.put_object(Bucket=bucket, Key=s3_key, Body=payload, ContentType=content_type)
        file_size = len(payload)
    except Exception:
        logger.exception("cited report upload failed for session %s (delivering without file)", session.id)
        s3_key = None

    report = Report(
        id=report_id,
        validation_session_id=session.id,
        report_version=1,
        s3_key=s3_key,
        file_size=file_size,
        total_discrepancies=len(issues),
        critical_discrepancies=counts["critical"],
        major_discrepancies=counts["major"],
        minor_discrepancies=counts["minor"],
        generated_by_user_id=getattr(user, "id", None),
        metadata={"kind": "lc_cited_report", "generated_at": datetime.now(timezone.utc).isoformat()},
    )
    db.add(report)
    db.flush()  # assign report.id in the session without full commit
    return report
