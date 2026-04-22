"""
Amendment Request PDF generator (Moment 1 importer output).

Reads findings off a completed ValidationSession with
workflow_type=importer_draft_lc and produces a clause-by-clause PDF the
importer can hand to their issuing bank.

Follows the same lazy weasyprint import pattern as app.reports.generator so
the import cost stays out of the hot request path.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "templates"


def _import_weasyprint():
    """Lazy import so we don't pay the GTK/Cairo load on startup."""
    from weasyprint import HTML  # type: ignore[import-not-found]
    return HTML


def _import_jinja():
    from jinja2 import Environment, FileSystemLoader, select_autoescape  # type: ignore[import-not-found]
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=select_autoescape(["html"]),
    )


def _normalize_severity(value: Optional[str]) -> str:
    if not value:
        return "minor"
    low = str(value).strip().lower()
    if low in {"critical", "high", "fail", "blocker"}:
        return "critical"
    if low in {"major", "warning", "warn", "medium"}:
        return "major"
    if low in {"info", "informational", "advisory"}:
        return "info"
    return "minor"


def _pick_first_nonempty(*candidates: Any) -> str:
    for c in candidates:
        if c is None:
            continue
        text = str(c).strip()
        if text:
            return text
    return ""


def extract_amendment_context(
    session: Any,
    findings: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Distill a ValidationSession + findings into the template context.

    The canonical LC fields live at
    ``structured_result.lc_structured.fields`` but different code paths
    have used slightly different shapes over the life of the project,
    so we probe a few places before giving up and returning empty.
    """
    structured_result: Dict[str, Any] = getattr(session, "validation_results", None) or {}
    if not isinstance(structured_result, dict):
        structured_result = {}

    lc_structured = (
        structured_result.get("lc_structured")
        or structured_result.get("structured_result", {}).get("lc_structured")
        or {}
    )
    lc_fields = lc_structured.get("fields") if isinstance(lc_structured, dict) else {}
    if not isinstance(lc_fields, dict):
        lc_fields = {}

    amendment_findings: List[Dict[str, Any]] = []
    for f in findings or []:
        if not isinstance(f, dict):
            continue
        current = _pick_first_nonempty(
            f.get("current_text"),
            f.get("found"),
            f.get("clause_cited"),
        )
        suggested = _pick_first_nonempty(
            f.get("suggested_text"),
            f.get("suggested_fix"),
            f.get("recommendation"),
            f.get("expected"),
        )
        amendment_findings.append({
            "rule_id": _pick_first_nonempty(f.get("rule_id"), f.get("rule"), f.get("code")),
            "title": _pick_first_nonempty(f.get("title"), f.get("finding"), f.get("message")),
            "current_text": current,
            "suggested_text": suggested,
            "severity": _normalize_severity(f.get("severity")),
        })

    lc_number = _pick_first_nonempty(
        lc_fields.get("lc_number"),
        lc_fields.get("number"),
        lc_fields.get("credit_number"),
        "UNKNOWN",
    )

    applicant = _pick_first_nonempty(
        lc_fields.get("applicant_name"),
        lc_fields.get("applicant"),
        (lc_fields.get("applicant") or {}).get("name") if isinstance(lc_fields.get("applicant"), dict) else None,
    )
    beneficiary = _pick_first_nonempty(
        lc_fields.get("beneficiary_name"),
        lc_fields.get("beneficiary"),
        (lc_fields.get("beneficiary") or {}).get("name") if isinstance(lc_fields.get("beneficiary"), dict) else None,
    )

    return {
        "lc_number": lc_number,
        "applicant": applicant,
        "beneficiary": beneficiary,
        "issue_date": _pick_first_nonempty(lc_fields.get("issue_date"), lc_fields.get("issued_at")),
        "request_date": datetime.utcnow().strftime("%Y-%m-%d"),
        "session_id": str(getattr(session, "id", "")),
        "findings": amendment_findings,
    }


def build_amendment_request_pdf(context: Dict[str, Any]) -> bytes:
    """Render the amendment-request HTML template and return PDF bytes."""
    env = _import_jinja()
    template = env.get_template("amendment_request.html")
    html_source = template.render(**context)
    HTML = _import_weasyprint()
    return HTML(string=html_source).write_pdf()
