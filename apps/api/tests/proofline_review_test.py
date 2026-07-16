"""Proofline analyst workflow guards."""

from __future__ import annotations

import pytest

from app.services.proofline.review import (
    REVIEW_QUEUE_STATUSES,
    ReviewWorkflowError,
    decision_target_status,
    ensure_reviewable_status,
)


def test_review_queue_contains_only_active_analyst_states():
    assert "awaiting_analyst_review" in REVIEW_QUEUE_STATUSES
    assert "action_required" in REVIEW_QUEUE_STATUSES
    assert "final_review" in REVIEW_QUEUE_STATUSES
    assert "draft" not in REVIEW_QUEUE_STATUSES
    assert "cleared" not in REVIEW_QUEUE_STATUSES


@pytest.mark.parametrize(
    ("decision", "status"),
    [
        ("CLEAR", "cleared"),
        ("CONDITIONAL_CLEARANCE", "conditionally_cleared"),
        ("BLOCKED", "blocked"),
        ("ACTION_REQUIRED", "action_required"),
        ("MANUAL_REVIEW_REQUIRED", "action_required"),
        ("UNABLE_TO_ASSESS", "action_required"),
    ],
)
def test_final_decision_maps_to_separate_workflow_status(decision, status):
    assert decision_target_status(decision).value == status


def test_only_active_cases_can_be_claimed_or_curated():
    ensure_reviewable_status("awaiting_analyst_review")
    ensure_reviewable_status("action_required")
    with pytest.raises(ReviewWorkflowError):
        ensure_reviewable_status("closed")

