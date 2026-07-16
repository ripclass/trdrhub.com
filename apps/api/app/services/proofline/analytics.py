"""Privacy-bounded operational metrics derived from persisted Proofline facts."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any, Iterable, Optional


def _duration_hours(start: Optional[datetime], end: Optional[datetime]) -> Optional[float]:
    if start is None or end is None or end < start:
        return None
    return (end - start).total_seconds() / 3600


def _average(values: Iterable[Optional[float]]) -> float:
    measured = [value for value in values if value is not None]
    return round(sum(measured) / len(measured), 2) if measured else 0.0


def _outcome_counts(rows: list[Any], field: str) -> dict[str, int]:
    values = [getattr(row, field, None) for row in rows]
    return {
        "yes": sum(value is True for value in values),
        "no": sum(value is False for value in values),
        "not_reported": sum(value is None for value in values),
    }


def build_operational_metrics(
    *,
    cases: Iterable[Any],
    findings: Iterable[Any],
    outcomes: Iterable[Any],
    period_days: int,
) -> dict[str, Any]:
    """Aggregate operational facts without loading document or credential contents."""
    case_rows = list(cases)
    finding_rows = list(findings)
    outcome_rows = list(outcomes)
    completed = [row for row in case_rows if getattr(row, "final_decision_at", None)]
    review_hours = [
        _duration_hours(getattr(row, "submitted_at", None), row.final_decision_at)
        for row in completed
    ]
    automated_hours = [
        _duration_hours(
            getattr(row, "processing_started_at", None),
            getattr(row, "automated_review_completed_at", None),
        )
        for row in case_rows
    ]
    analyst_hours = [
        _duration_hours(
            getattr(row, "automated_review_completed_at", None),
            getattr(row, "final_decision_at", None),
        )
        for row in completed
    ]
    measured_analyst_hours = [value for value in analyst_hours if value is not None]
    categories = Counter(
        str(getattr(row, "category", None) or "uncategorized") for row in finding_rows
    )
    decisions = Counter(
        str(row.final_decision)
        for row in completed
        if getattr(row, "final_decision", None)
    )
    statuses = Counter(str(getattr(row, "status", "unknown")) for row in case_rows)
    packages = Counter(
        str(row.service_package_id)
        for row in case_rows
        if getattr(row, "service_package_id", None)
    )
    customers = Counter(str(row.company_id) for row in case_rows)
    repeat_customers = sum(count > 1 for count in customers.values())
    paid_cents = sum(
        int(getattr(row, "amount_paid_cents", None) or 0)
        for row in case_rows
        if getattr(row, "refunded_at", None) is None
    )

    return {
        "period_days": period_days,
        "cases": {
            "created": len(case_rows),
            "submitted": sum(bool(getattr(row, "submitted_at", None)) for row in case_rows),
            "completed": len(completed),
        },
        "status_counts": dict(sorted(statuses.items())),
        "timing": {
            "average_review_hours": _average(review_hours),
            "average_automated_processing_minutes": round(
                _average(automated_hours) * 60, 2
            ),
            "average_analyst_hours": _average(analyst_hours),
            "total_analyst_hours": round(sum(measured_analyst_hours), 2),
        },
        "findings": {
            "total": len(finding_rows),
            "average_per_case": round(
                len(finding_rows) / len(case_rows), 2
            ) if case_rows else 0.0,
            "most_common_categories": [
                {"category": category, "count": count}
                for category, count in categories.most_common(10)
            ],
        },
        "correction_rounds": sum(
            int(getattr(row, "correction_rounds_used", 0) or 0) for row in case_rows
        ),
        "decisions": dict(sorted(decisions.items())),
        "lcopilot_upgrades": sum(
            bool(getattr(row, "source_lcopilot_session_id", None)) for row in case_rows
        ),
        "service_package_volume": dict(sorted(packages.items())),
        "revenue": {
            "paid_cents": paid_cents,
            "gross_margin_estimate": None,
            "gross_margin_note": "Not calculated until validated analyst-cost data is available.",
        },
        "repeat_customer_rate_percent": round(
            (repeat_customers / len(customers)) * 100, 2
        ) if customers else 0.0,
        "voluntary_outcomes": {
            "responses": len(outcome_rows),
            "documents_accepted": _outcome_counts(outcome_rows, "documents_accepted"),
            "payment_delayed": _outcome_counts(outcome_rows, "payment_delayed"),
            "bank_additional_discrepancies": _outcome_counts(
                outcome_rows, "bank_additional_discrepancies"
            ),
            "shipment_held": _outcome_counts(outcome_rows, "shipment_held"),
            "disclaimer": "Customer-reported operational outcomes; not independently validated ground truth.",
        },
    }


__all__ = ["build_operational_metrics"]
