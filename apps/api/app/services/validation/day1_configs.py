from __future__ import annotations

from pathlib import Path
import json
from typing import Any, Dict

import yaml


_BASE = Path(__file__).resolve().parents[3] / "config" / "day1"


def _read_text(name: str) -> str:
    return (_BASE / name).read_text(encoding="utf-8")


def load_day1_schema() -> Dict[str, Any]:
    return json.loads(_read_text("schema.day1.v1.0.0-day1.json"))


def load_day1_anchors() -> Dict[str, Any]:
    return yaml.safe_load(_read_text("anchors.v1.yaml"))


def load_day1_reason_codes() -> Dict[str, Any]:
    return yaml.safe_load(_read_text("reason_codes.v1.yaml"))


def load_day1_telemetry_events() -> Dict[str, Any]:
    return yaml.safe_load(_read_text("telemetry_events.v1.yaml"))
