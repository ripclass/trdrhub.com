"""Proofline customer correction-round guards."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services.proofline.remediation import (
    RemediationWorkflowError,
    next_correction_round,
    validate_resubmission,
)


def test_next_round_uses_plan_safe_monotonic_counter():
    assert next_correction_round(0) == 1
    assert next_correction_round(2) == 3


def test_resubmission_requires_a_response_to_every_open_request():
    actions = [
        SimpleNamespace(status="customer_responded", customer_response="Corrected", correction_document_id=None),
        SimpleNamespace(status="requested", customer_response=None, correction_document_id=None),
    ]
    with pytest.raises(RemediationWorkflowError):
        validate_resubmission(actions)


def test_resubmission_accepts_text_or_corrected_document_evidence():
    validate_resubmission([
        SimpleNamespace(status="customer_responded", customer_response="See explanation", correction_document_id=None),
        SimpleNamespace(status="customer_responded", customer_response=None, correction_document_id="doc-2"),
    ])

