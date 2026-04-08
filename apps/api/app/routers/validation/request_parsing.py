"""Validation request parsing helpers extracted from validate_run.py."""

from __future__ import annotations

from typing import Any, NamedTuple

from app.core.lc_types import LCType, VALID_LC_TYPES, normalize_lc_type

_SHARED_NAMES = [
    "Any",
    "HTTPException",
    "Request",
    "_extract_intake_only",
    "json",
    "status",
    "validate_upload_file",
]


def _shared_get(shared: Any, name: str) -> Any:
    if isinstance(shared, dict):
        return shared[name]
    return getattr(shared, name)


def bind_shared(shared: Any) -> None:
    namespace = globals()
    missing_bindings: list[str] = []
    for name in _SHARED_NAMES:
        if name in namespace:
            continue
        try:
            namespace[name] = _shared_get(shared, name)
        except (KeyError, AttributeError):
            missing_bindings.append(name)
    if missing_bindings:
        raise RuntimeError(
            "Missing shared bindings for validation.request_parsing: "
            + ", ".join(sorted(missing_bindings))
        )


class ParsedValidationRequest(NamedTuple):
    payload: dict[str, Any]
    files_list: list[Any]
    doc_type: str
    intake_only: bool
    extract_only: bool


def extract_request_user_type(payload: dict[str, Any]) -> str:
    value = payload.get("user_type") or payload.get("userType")
    if not value:
        return ""
    return str(value).strip().lower()


def should_force_json_rules(payload: dict[str, Any]) -> bool:
    user_type = extract_request_user_type(payload)
    if user_type in {"exporter", "importer"}:
        return True
    workflow = payload.get("workflow_type") or payload.get("workflowType")
    if workflow:
        normalized = str(workflow).strip().lower()
        if normalized.startswith(("export", "import")):
            return True
    return False


def resolve_shipment_context(payload: dict[str, Any]) -> dict[str, Any]:
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
    lc_context = payload.get("lc") or {}
    if isinstance(lc_context, dict):
        loading_value = lc_context.get("port_of_loading")
        discharge_value = lc_context.get("port_of_discharge")
        if loading_value or discharge_value:
            shipment: dict[str, Any] = {}
            if loading_value:
                shipment["port_of_loading"] = loading_value
            if discharge_value:
                shipment["port_of_discharge"] = discharge_value
            return shipment
        lc_ports = lc_context.get("ports")
        if isinstance(lc_ports, dict):
            shipment = {}
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


def extract_lc_type_override(payload: dict[str, Any]) -> str | None:
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


async def parse_validate_request(request: Request) -> ParsedValidationRequest:
    content_type = request.headers.get("content-type", "")
    payload: dict
    files_list = []  # Collect files for validation

    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        payload = {}
        for key, value in form.multi_items():
            # Check if this is a file upload (UploadFile instance)
            if hasattr(value, "filename") and hasattr(value, "read"):
                # This is a file upload - validate it
                file_obj = value
                header_bytes = await file_obj.read(8)
                await file_obj.seek(0)  # Reset for processing

                # Content-based validation
                is_valid, error_message = validate_upload_file(
                    header_bytes,
                    filename=file_obj.filename,
                    content_type=file_obj.content_type
                )

                if not is_valid:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid file content for {file_obj.filename}: {error_message}. File content does not match declared type."
                    )

                files_list.append(file_obj)
                continue

            # Safely handle form field values - ensure they're strings
            # Handle potential encoding issues by converting to string safely
            # Skip if this looks like binary data (might be misidentified file)
            if isinstance(value, bytes):
                # Check if this looks like binary data (PDF, image, etc.)
                # PDFs start with %PDF, images have magic bytes
                if len(value) > 4 and (
                    value.startswith(b'%PDF') or 
                    value.startswith(b'\x89PNG') or 
                    value.startswith(b'\xff\xd8\xff') or
                    value.startswith(b'GIF8') or
                    value.startswith(b'PK\x03\x04')  # ZIP
                ):
                    # This is likely a file that wasn't properly identified
                    # Skip it or log a warning, but don't try to decode as text
                    continue

                # If value is bytes, try to decode as UTF-8, fallback to latin-1
                try:
                    payload[key] = value.decode('utf-8')
                except UnicodeDecodeError:
                    # Fallback to latin-1 which can decode any byte sequence
                    try:
                        payload[key] = value.decode('latin-1')
                    except Exception:
                        # If all decoding fails, skip this field
                        continue
            elif isinstance(value, str):
                payload[key] = value
            else:
                # Convert other types to string, but skip if it's a file-like object
                if hasattr(value, 'read') or hasattr(value, 'filename'):
                    continue
                try:
                    payload[key] = str(value)
                except Exception:
                    # Skip if conversion fails
                    continue
    else:
        payload = await request.json()

    # Parse JSON fields safely (document_tags, metadata)
    if "document_tags" in payload and isinstance(payload["document_tags"], str):
        try:
            payload["document_tags"] = json.loads(payload["document_tags"])
        except (json.JSONDecodeError, TypeError, UnicodeDecodeError):
            # If parsing fails, set to empty dict
            payload["document_tags"] = {}

    if "metadata" in payload and isinstance(payload["metadata"], str):
        try:
            payload["metadata"] = json.loads(payload["metadata"])
        except (json.JSONDecodeError, TypeError, UnicodeDecodeError):
            # If parsing fails, set to None
            payload["metadata"] = None

    doc_type = (
        payload.get("document_type")
        or payload.get("documentType")
        or "letter_of_credit"
    )
    payload["document_type"] = doc_type
    if not doc_type:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing document_type")

    intake_only = _extract_intake_only(payload)
    extract_only_raw = payload.get("extract_only") or payload.get("extractOnly")
    extract_only = bool(extract_only_raw) and str(extract_only_raw).strip().lower() not in {"false", "0", "no", ""}

    return ParsedValidationRequest(
        payload=payload,
        files_list=files_list,
        doc_type=doc_type,
        intake_only=bool(intake_only),
        extract_only=bool(extract_only),
    )


__all__ = [
    "ParsedValidationRequest",
    "bind_shared",
    "extract_lc_type_override",
    "extract_request_user_type",
    "parse_validate_request",
    "resolve_shipment_context",
    "should_force_json_rules",
]
