from pathlib import Path
import sys

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.config import Settings


def test_validation_mode_alias_maps_to_decision_mode():
    s = Settings.model_validate({"VALIDATION_MODE": "hybrid_enforced"})
    assert s.VALIDATION_DECISION_MODE == "hybrid_enforced"
