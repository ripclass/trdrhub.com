from pathlib import Path
import sys

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.routers.validate import _build_db_rules_blocked_structured_result
from app.services.validation.arbitration import compute_shadow_arbitration


def test_phase2_shadow_arbitration_policy_outcomes():
    reject = compute_shadow_arbitration(
        ai_verdict="pass",
        ruleset_verdict="pass",
        blocking_rules=["UCP600.14"],
        extraction_confidence=0.95,
    )
    assert reject["arbitration_verdict"] == "reject"

    review = compute_shadow_arbitration(
        ai_verdict="reject",
        ruleset_verdict="pass",
        blocking_rules=[],
        extraction_confidence=0.92,
    )
    assert review["arbitration_verdict"] == "review"

    passed = compute_shadow_arbitration(
        ai_verdict="pass",
        ruleset_verdict="pass",
        blocking_rules=[],
        extraction_confidence=0.92,
    )
    assert passed["arbitration_verdict"] == "pass"

    low_conf = compute_shadow_arbitration(
        ai_verdict="pass",
        ruleset_verdict="pass",
        blocking_rules=[],
        extraction_confidence=0.2,
    )
    assert low_conf["arbitration_verdict"] == "review"


def test_phase2_shadow_wiring_present_in_blocked_payload():
    payload = _build_db_rules_blocked_structured_result(
        reason="rules offline",
        processing_duration=0.42,
        documents=[],
    )
    assert "decision_trace" in payload
    assert payload["decision_trace"] is None or isinstance(payload["decision_trace"], dict)
