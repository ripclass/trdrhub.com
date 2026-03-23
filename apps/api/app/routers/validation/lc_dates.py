"""LC MT700 date extraction and repair helpers."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, Optional


def coerce_mt700_date_iso(value: Any) -> Optional[str]:
    text = str(value or "").strip()
    if not text:
        return None
    digits = re.sub(r"\D", "", text)
    if len(digits) < 6:
        return None
    try:
        return datetime.strptime(digits[:6], "%y%m%d").date().isoformat()
    except ValueError:
        return None


def extract_mt700_block_value(payload: Optional[Dict[str, Any]], block_code: str) -> Optional[str]:
    if not isinstance(payload, dict):
        return None

    mt700 = payload.get("mt700") if isinstance(payload.get("mt700"), dict) else {}
    blocks = mt700.get("blocks") if isinstance(mt700.get("blocks"), dict) else {}
    raw_blocks = mt700.get("raw") if isinstance(mt700.get("raw"), dict) else {}
    if not raw_blocks and isinstance(payload.get("mt700_raw"), dict):
        raw_blocks = payload.get("mt700_raw") or {}
    raw_value = blocks.get(block_code)
    if raw_value not in (None, "", [], {}):
        return str(raw_value).strip() or None
    raw_value = raw_blocks.get(block_code)
    if raw_value not in (None, "", [], {}):
        return str(raw_value).strip() or None

    raw_text = str(mt700.get("raw_text") or payload.get("raw_text") or "").strip()
    if not raw_text:
        return None

    match = re.search(rf"(?im)^\s*:{re.escape(block_code)}:\s*([^\r\n]+)", raw_text)
    if not match:
        return None
    value = str(match.group(1) or "").strip()
    return value or None


def extract_mt700_timeline_fields(payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return {}

    issue_raw = extract_mt700_block_value(payload, "31C")
    expiry_raw = extract_mt700_block_value(payload, "31D")
    latest_raw = extract_mt700_block_value(payload, "44C")

    issue_date = coerce_mt700_date_iso(issue_raw)
    expiry_date = coerce_mt700_date_iso(expiry_raw)
    latest_shipment_date = coerce_mt700_date_iso(latest_raw)

    expiry_place = None
    expiry_text = str(expiry_raw or "").strip()
    expiry_match = re.match(r"^\s*\d{6}\s*([A-Za-z][A-Za-z\s\-.]{1,})\s*$", expiry_text)
    if expiry_match:
        expiry_place = str(expiry_match.group(1) or "").strip().upper() or None

    timeline: Dict[str, Any] = {}
    if issue_date:
        timeline["issue_date"] = issue_date
    if expiry_date:
        timeline["expiry_date"] = expiry_date
    if latest_shipment_date:
        timeline["latest_shipment_date"] = latest_shipment_date
    if expiry_place:
        timeline["place_of_expiry"] = expiry_place
    return timeline


def repair_lc_mt700_dates(payload: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not isinstance(payload, dict):
        return payload

    repaired = dict(payload)
    mt700_dates = extract_mt700_timeline_fields(repaired)
    if not mt700_dates:
        return repaired

    mt700 = dict(repaired.get("mt700") or {}) if isinstance(repaired.get("mt700"), dict) else {}
    blocks = dict(mt700.get("blocks") or {}) if isinstance(mt700.get("blocks"), dict) else {}
    for block_code in ("31C", "31D", "44C"):
        block_value = extract_mt700_block_value(repaired, block_code)
        if block_value and blocks.get(block_code) in (None, "", [], {}):
            blocks[block_code] = block_value
    if blocks or mt700.get("raw_text") or repaired.get("raw_text"):
        mt700["blocks"] = blocks
        mt700["raw_text"] = mt700.get("raw_text") or repaired.get("raw_text")
        mt700["version"] = mt700.get("version") or "mt700_v1"
        repaired["mt700"] = mt700

    dates = dict(repaired.get("dates") or {}) if isinstance(repaired.get("dates"), dict) else {}
    timeline = dict(repaired.get("timeline") or {}) if isinstance(repaired.get("timeline"), dict) else {}
    extracted_fields = dict(repaired.get("extracted_fields") or {}) if isinstance(repaired.get("extracted_fields"), dict) else {}

    lc_classification = (
        dict(repaired.get("lc_classification") or {})
        if isinstance(repaired.get("lc_classification"), dict)
        else {}
    )
    attributes = (
        dict(lc_classification.get("attributes") or {})
        if isinstance(lc_classification.get("attributes"), dict)
        else {}
    )

    issue_date = mt700_dates.get("issue_date")
    expiry_date = mt700_dates.get("expiry_date")
    latest_shipment_date = mt700_dates.get("latest_shipment_date")
    place_of_expiry = mt700_dates.get("place_of_expiry")

    if issue_date:
        repaired["issue_date"] = issue_date
        dates["issue"] = issue_date
        dates["issue_date"] = issue_date
        timeline["issue_date"] = issue_date
        extracted_fields["issue_date"] = issue_date

    if expiry_date:
        repaired["expiry_date"] = expiry_date
        dates["expiry"] = expiry_date
        dates["expiry_date"] = expiry_date
        timeline["expiry_date"] = expiry_date
        extracted_fields["expiry_date"] = expiry_date
        attributes["expiry_date"] = expiry_date

    if latest_shipment_date:
        repaired["latest_shipment_date"] = latest_shipment_date
        repaired["latest_shipment"] = latest_shipment_date
        dates["latest_shipment"] = latest_shipment_date
        dates["latest_shipment_date"] = latest_shipment_date
        timeline["latest_shipment"] = latest_shipment_date
        timeline["latest_shipment_date"] = latest_shipment_date
        extracted_fields["latest_shipment_date"] = latest_shipment_date
        attributes["latest_shipment_date"] = latest_shipment_date

    if place_of_expiry:
        repaired["place_of_expiry"] = place_of_expiry
        dates["place_of_expiry"] = place_of_expiry
        attributes["expiry_place"] = place_of_expiry

    if dates:
        repaired["dates"] = dates
    if timeline:
        repaired["timeline"] = timeline
    if extracted_fields:
        repaired["extracted_fields"] = extracted_fields
    if lc_classification or attributes:
        lc_classification["attributes"] = attributes
        repaired["lc_classification"] = lc_classification

    return repaired


__all__ = [
    "coerce_mt700_date_iso",
    "extract_mt700_block_value",
    "extract_mt700_timeline_fields",
    "repair_lc_mt700_dates",
]
