"""Operational Proofline metrics remain deterministic and privacy bounded."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.services.proofline.analytics import build_operational_metrics


def test_build_operational_metrics_captures_service_and_voluntary_outcomes():
    now = datetime(2026, 7, 16, tzinfo=timezone.utc)
    company_a = uuid4()
    company_b = uuid4()
    first_case_id = uuid4()
    second_case_id = uuid4()
    cases = [
        SimpleNamespace(
            id=first_case_id,
            company_id=company_a,
            status="cleared",
            final_decision="CLEAR",
            created_at=now - timedelta(days=12),
            submitted_at=now - timedelta(days=10),
            processing_started_at=now - timedelta(days=9),
            automated_review_completed_at=now - timedelta(days=8),
            final_decision_at=now - timedelta(days=6),
            correction_rounds_used=1,
            amount_paid_cents=19_900,
            refunded_at=None,
            source_lcopilot_session_id=uuid4(),
            service_package_id="standard",
        ),
        SimpleNamespace(
            id=second_case_id,
            company_id=company_a,
            status="conditionally_cleared",
            final_decision="CONDITIONAL_CLEARANCE",
            created_at=now - timedelta(days=6),
            submitted_at=now - timedelta(days=5),
            processing_started_at=now - timedelta(days=4, hours=12),
            automated_review_completed_at=now - timedelta(days=4),
            final_decision_at=now - timedelta(days=2),
            correction_rounds_used=2,
            amount_paid_cents=39_900,
            refunded_at=None,
            source_lcopilot_session_id=None,
            service_package_id="managed",
        ),
        SimpleNamespace(
            id=uuid4(),
            company_id=company_b,
            status="draft",
            final_decision=None,
            created_at=now - timedelta(days=1),
            submitted_at=None,
            processing_started_at=None,
            automated_review_completed_at=None,
            final_decision_at=None,
            correction_rounds_used=0,
            amount_paid_cents=None,
            refunded_at=None,
            source_lcopilot_session_id=None,
            service_package_id=None,
        ),
    ]
    findings = [
        SimpleNamespace(trade_case_id=first_case_id, category="document"),
        SimpleNamespace(trade_case_id=first_case_id, category="document"),
        SimpleNamespace(trade_case_id=second_case_id, category="regulatory"),
    ]
    outcomes = [
        SimpleNamespace(
            documents_accepted=True,
            payment_delayed=False,
            bank_additional_discrepancies=None,
            shipment_held=False,
        )
    ]

    metrics = build_operational_metrics(
        cases=cases,
        findings=findings,
        outcomes=outcomes,
        period_days=30,
    )

    assert metrics["cases"] == {"created": 3, "submitted": 2, "completed": 2}
    assert metrics["timing"]["average_review_hours"] == 84.0
    assert metrics["timing"]["average_automated_processing_minutes"] == 1080.0
    assert metrics["timing"]["average_analyst_hours"] == 48.0
    assert metrics["timing"]["total_analyst_hours"] == 96.0
    assert metrics["findings"]["total"] == 3
    assert metrics["findings"]["average_per_case"] == 1.0
    assert metrics["findings"]["most_common_categories"][0] == {
        "category": "document",
        "count": 2,
    }
    assert metrics["correction_rounds"] == 3
    assert metrics["decisions"]["CLEAR"] == 1
    assert metrics["decisions"]["CONDITIONAL_CLEARANCE"] == 1
    assert metrics["lcopilot_upgrades"] == 1
    assert metrics["revenue"]["paid_cents"] == 59_800
    assert metrics["revenue"]["gross_margin_estimate"] is None
    assert metrics["repeat_customer_rate_percent"] == 50.0
    assert metrics["voluntary_outcomes"]["responses"] == 1
    assert metrics["voluntary_outcomes"]["documents_accepted"] == {
        "yes": 1,
        "no": 0,
        "not_reported": 0,
    }
    assert metrics["voluntary_outcomes"]["bank_additional_discrepancies"][
        "not_reported"
    ] == 1


def test_metrics_do_not_invent_margin_or_divide_by_zero():
    metrics = build_operational_metrics(
        cases=[], findings=[], outcomes=[], period_days=7
    )

    assert metrics["cases"]["created"] == 0
    assert metrics["findings"]["average_per_case"] == 0.0
    assert metrics["repeat_customer_rate_percent"] == 0.0
    assert metrics["revenue"]["gross_margin_estimate"] is None
