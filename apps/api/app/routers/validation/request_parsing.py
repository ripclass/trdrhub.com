"""Request parsing helpers for validation routes."""

from typing import Any, Dict, Optional

from app.core.lc_types import LCType, VALID_LC_TYPES, normalize_lc_type


def extract_request_user_type(payload: Dict[str, Any]) -> str:
    value = payload.get("user_type") or payload.get("userType")
    if not value:
        return ""
    return str(value).strip().lower()


def should_force_json_rules(payload: Dict[str, Any]) -> bool:
    user_type = extract_request_user_type(payload)
    if user_type in {"exporter", "importer"}:
        return True
    workflow = payload.get("workflow_type") or payload.get("workflowType")
    if workflow:
        normalized = str(workflow).strip().lower()
        if normalized.startswith(("export", "import")):
            return True
    return False


def resolve_shipment_context(payload: Dict[str, Any]) -> Dict[str, Any]:
    for key in (
        "bill_of_lading",
        "billOfLading",
        "awb",
        "air_waybill",
        "airway_bill",
        "shipment",
    ):
        ctx = payload.get(key)
        if isinstance(ctx, dict):
            return ctx
    lc_ports = (payload.get("lc") or {}).get("ports")
    if isinstance(lc_ports, dict):
        shipment: Dict[str, Any] = {}
        loading_value = lc_ports.get("port_of_loading") or lc_ports.get("loading")
        discharge_value = lc_ports.get("port_of_discharge") or lc_ports.get("discharge")
        if loading_value:
            shipment["port_of_loading"] = loading_value
        if discharge_value:
            shipment["port_of_discharge"] = discharge_value
        if shipment:
            return shipment
        return lc_ports
    return {}


def extract_lc_type_override(payload: Dict[str, Any]) -> Optional[str]:
    options = payload.get("options") or {}
    candidates = [
        payload.get("lc_type_override"),
        payload.get("lcTypeOverride"),
        options.get("lc_type_override"),
        options.get("lc_type"),
        payload.get("lcType"),
        payload.get("lc_type_selection"),
        payload.get("requested_lc_type"),
    ]
    for candidate in candidates:
        normalized = normalize_lc_type(candidate)
        if normalized in VALID_LC_TYPES:
            if normalized == LCType.UNKNOWN.value:
                return LCType.UNKNOWN.value
            return normalized
        if candidate and str(candidate).strip().lower() == "auto":
            return None
    return None
