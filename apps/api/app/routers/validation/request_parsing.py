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
    shipment: Dict[str, Any] = {}
    lc_context = payload.get("lc")
    if not isinstance(lc_context, dict):
        return {}

    lc_ports = lc_context.get("ports")
    if isinstance(lc_ports, dict):
        for source_key, shipment_key in (
            ("port_of_loading", "port_of_loading"),
            ("loading", "port_of_loading"),
            ("port_of_discharge", "port_of_discharge"),
            ("discharge", "port_of_discharge"),
            ("port_of_shipment", "port_of_shipment"),
            ("port_of_destination", "port_of_destination"),
            ("port_of_loading_country", "port_of_loading_country"),
            ("port_of_discharge_country", "port_of_discharge_country"),
            ("port_of_loading_country_name", "port_of_loading_country_name"),
            ("port_of_discharge_country_name", "port_of_discharge_country_name"),
            ("port_of_loading_country_code", "port_of_loading_country_code"),
            ("port_of_discharge_country_code", "port_of_discharge_country_code"),
        ):
            value = lc_ports.get(source_key)
            if value not in (None, ""):
                shipment[shipment_key] = value

    for source_key, shipment_key in (
        ("port_of_loading", "port_of_loading"),
        ("port_of_discharge", "port_of_discharge"),
        ("port_of_shipment", "port_of_shipment"),
        ("port_of_destination", "port_of_destination"),
        ("port_of_loading_country", "port_of_loading_country"),
        ("port_of_discharge_country", "port_of_discharge_country"),
        ("port_of_loading_country_name", "port_of_loading_country_name"),
        ("port_of_discharge_country_name", "port_of_discharge_country_name"),
        ("port_of_loading_country_code", "port_of_loading_country_code"),
        ("port_of_discharge_country_code", "port_of_discharge_country_code"),
    ):
        value = lc_context.get(source_key)
        if value not in (None, "") and shipment.get(shipment_key) in (None, ""):
            shipment[shipment_key] = value

    return shipment


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
