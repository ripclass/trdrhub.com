from pathlib import Path
import sys

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.routers.validate import _build_db_rules_blocked_structured_result


def test_phase1_dual_track_fields_exist_in_blocked_payload():
    payload = _build_db_rules_blocked_structured_result(
        reason="rules offline",
        processing_duration=0.42,
        documents=[],
    )

    assert "ai_verdict" in payload
    assert "ruleset_verdict" in payload
    assert "final_verdict" in payload
    assert "override_reason" in payload
    assert "blocking_rules" in payload
    assert "confidence_band" in payload

    assert payload["ai_verdict"] is None or isinstance(payload["ai_verdict"], str)
    assert isinstance(payload["ruleset_verdict"], str)
    assert isinstance(payload["final_verdict"], str)
    assert payload["override_reason"] is None or isinstance(payload["override_reason"], str)
    assert isinstance(payload["blocking_rules"], list)
    assert payload["confidence_band"] is None or isinstance(payload["confidence_band"], str)
