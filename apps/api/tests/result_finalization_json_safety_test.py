from __future__ import annotations

import importlib.util
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from pathlib import Path
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "app" / "routers" / "validation" / "result_finalization.py"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "result_finalization_json_safety_test_module",
        MODULE_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Status(Enum):
    REVIEW = "review"


@dataclass
class _DataRow:
    value: Decimal


class _Shape:
    def to_dict(self):
        return {"payload": b"\xff\x00"}


def test_make_json_safe_normalizes_runtime_only_values() -> None:
    module = _load_module()

    payload = {
        "nan": float("nan"),
        "inf": float("inf"),
        "decimal": Decimal("12.50"),
        "when": datetime(2026, 4, 2, 12, 34, 56, tzinfo=timezone.utc),
        "uuid": uuid4(),
        "enum": _Status.REVIEW,
        "bytes": b"\xff\x00",
        "nested": [_DataRow(value=Decimal("7.25")), _Shape()],
    }

    sanitized = module._make_json_safe(payload)

    assert sanitized["nan"] is None
    assert sanitized["inf"] is None
    assert math.isclose(sanitized["decimal"], 12.5)
    assert sanitized["when"] == "2026-04-02T12:34:56+00:00"
    assert isinstance(sanitized["uuid"], str)
    assert sanitized["enum"] == "review"
    assert sanitized["bytes"] == "<binary:2 bytes>"
    assert math.isclose(sanitized["nested"][0]["value"], 7.25)
    assert sanitized["nested"][1]["payload"] == "<binary:2 bytes>"


def test_make_json_safe_recurses_through_lists_and_maps() -> None:
    module = _load_module()

    sanitized = module._make_json_safe(
        [
            {"score": Decimal("1.10"), "bad": float("-inf")},
            {"blob": bytearray(b"abc"), "status": _Status.REVIEW},
        ]
    )

    assert sanitized == [
        {"score": 1.1, "bad": None},
        {"blob": "abc", "status": "review"},
    ]
