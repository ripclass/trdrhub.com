"""
OCR provider diagnostics helpers.

Tracks provider health, classifies provider failures, and exposes a safe
diagnostics snapshot for internal health tooling.
"""

from __future__ import annotations

import logging
import re
import threading
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional

from app.config import settings


logger = logging.getLogger(__name__)

_PROVIDER_ALIASES = {
    "gdocai": "google_documentai",
    "google": "google_documentai",
    "google_documentai": "google_documentai",
    "textract": "aws_textract",
    "aws": "aws_textract",
    "aws_textract": "aws_textract",
    "deepseek": "deepseek_ocr",
    "deepseek_ocr": "deepseek_ocr",
    "stub": "stub_ocr",
    "stub_ocr": "stub_ocr",
    "ocr_service": "ocr_service",
}

_KNOWN_PROVIDERS = (
    "google_documentai",
    "aws_textract",
    "deepseek_ocr",
    "stub_ocr",
    "ocr_service",
)

_PROVIDER_CAPABILITIES: Dict[str, Dict[str, bool]] = {
    "google_documentai": {"pdf": True, "image": True},
    "aws_textract": {"pdf": True, "image": True},
    "deepseek_ocr": {"pdf": True, "image": True},
    "stub_ocr": {"pdf": True, "image": True},
    "ocr_service": {"pdf": True, "image": True},
}

_SECRET_FIELD_PATTERNS = (
    re.compile(r'("?(?:api[_-]?key|access[_-]?key|secret|token|password|credential(?:s)?|private[_-]?key)"?\s*[:=]\s*)"[^"]+"', re.IGNORECASE),
    re.compile(r"((?:api[_-]?key|access[_-]?key|secret|token|password|credential(?:s)?|private[_-]?key)\s*[:=]\s*)[^\s,;]+", re.IGNORECASE),
    re.compile(r"-----BEGIN [^-]+-----.*?-----END [^-]+-----", re.IGNORECASE),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._\-+/=]{16,}\b", re.IGNORECASE),
)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ocr_runtime_diagnostics_enabled() -> bool:
    return bool(getattr(settings, "OCR_RUNTIME_DIAGNOSTICS_ENABLED", True))


def resolve_ocr_provider_name(provider_name: Optional[str]) -> str:
    normalized = str(provider_name or "").strip().lower()
    return _PROVIDER_ALIASES.get(normalized, normalized)


def get_ocr_provider_capabilities(provider_name: Optional[str]) -> Dict[str, bool]:
    return dict(_PROVIDER_CAPABILITIES.get(resolve_ocr_provider_name(provider_name), {"pdf": False, "image": False}))


def sanitize_ocr_error_message(message: Optional[str]) -> Optional[str]:
    if message in (None, ""):
        return None

    sanitized = str(message).replace("\r", " ").replace("\n", " ").strip()
    if not sanitized:
        return None

    for pattern in _SECRET_FIELD_PATTERNS:
        sanitized = pattern.sub(lambda match: f"{match.group(1)}[REDACTED]" if match.groups() else "[REDACTED]", sanitized)

    sanitized = re.sub(r"\s+", " ", sanitized).strip()
    if len(sanitized) > 240:
        sanitized = f"{sanitized[:237]}..."
    return sanitized


def classify_ocr_provider_error(error: Optional[str]) -> Optional[str]:
    if not error:
        return None

    lowered = str(error).strip().lower()
    if not lowered:
        return None

    unsupported_tokens = (
        "unsupported",
        "invalid mime",
        "content type",
        "content-type",
        "mime type",
        "bad format",
        "invalid document format",
        "unsupporteddocumentexception",
        "unsupported document",
        "unsupported file type",
    )
    empty_tokens = (
        "empty_output",
        "empty output",
        "empty result",
        "empty_result",
        "no text",
        "no text extracted",
        "no output",
        "no_ocr_provider_returned_text",
        "blank document",
    )
    processor_not_found_tokens = (
        "processor not found",
        "processor_not_found",
        "document ai processor not found",
        "processors/",
    )
    permission_tokens = (
        "permission denied",
        "forbidden",
        "access denied",
        "not authorized",
        "not allowed",
        "insufficient permissions",
        "status code 403",
    )
    auth_tokens = (
        "unauthenticated",
        "authentication failed",
        "auth failed",
        "auth failure",
        "invalid credentials",
        "invalid api key",
        "api key",
        "credential",
        "credentials",
        "expiredtoken",
        "signaturedoesnotmatch",
        "could not load default credentials",
        "status code 401",
    )
    timeout_tokens = (
        "timeout",
        "timed out",
        "deadline exceeded",
        "read timed out",
        "connect timeout",
        "request timeout",
    )
    network_tokens = (
        "connection reset",
        "connection error",
        "connection refused",
        "connection aborted",
        "connection closed",
        "network",
        "dns",
        "temporary failure in name resolution",
        "name or service not known",
        "failed to establish a new connection",
        "service unavailable",
        "ssl",
        "tls",
        "unreachable",
        "proxyerror",
        "remote disconnected",
    )

    if any(token in lowered for token in unsupported_tokens):
        return "OCR_UNSUPPORTED_FORMAT"
    if any(token in lowered for token in empty_tokens):
        return "OCR_EMPTY_RESULT"
    if any(token in lowered for token in processor_not_found_tokens) and "not found" in lowered:
        return "OCR_PROCESSOR_NOT_FOUND"
    if any(token in lowered for token in permission_tokens):
        return "OCR_PERMISSION_DENIED"
    if any(token in lowered for token in auth_tokens):
        return "OCR_AUTH_FAILURE"
    if any(token in lowered for token in timeout_tokens):
        return "OCR_TIMEOUT"
    if any(token in lowered for token in network_tokens):
        return "OCR_NETWORK_ERROR"
    if "not found" in lowered and "processor" in lowered:
        return "OCR_PROCESSOR_NOT_FOUND"
    return "OCR_UNKNOWN_PROVIDER_ERROR"


def build_effective_ocr_provider_order() -> List[str]:
    if bool(getattr(settings, "USE_STUBS", False)):
        return ["stub_ocr"]

    configured: List[str] = []
    for provider_name in list(getattr(settings, "OCR_PROVIDER_ORDER", []) or []):
        resolved = resolve_ocr_provider_name(provider_name)
        if resolved and resolved not in configured:
            configured.append(resolved)

    if bool(getattr(settings, "USE_DEEPSEEK_OCR", False)) and "deepseek_ocr" not in configured:
        configured.append("deepseek_ocr")
    if bool(getattr(settings, "GOOGLE_CLOUD_PROJECT", None)) and bool(getattr(settings, "GOOGLE_DOCUMENTAI_PROCESSOR_ID", None)):
        if "google_documentai" not in configured:
            configured.append("google_documentai")
    if "aws_textract" not in configured:
        configured.append("aws_textract")
    return configured


def build_ocr_feature_flags() -> Dict[str, Any]:
    return {
        "OCR_ENABLED": bool(getattr(settings, "OCR_ENABLED", True)),
        "OCR_RUNTIME_DIAGNOSTICS_ENABLED": ocr_runtime_diagnostics_enabled(),
        "OCR_HEALTH_ENDPOINT_ENABLED": bool(getattr(settings, "OCR_HEALTH_ENDPOINT_ENABLED", True)),
        "USE_STUBS": bool(getattr(settings, "USE_STUBS", False)),
        "USE_DEEPSEEK_OCR": bool(getattr(settings, "USE_DEEPSEEK_OCR", False)),
        "OCR_NORMALIZATION_SHIM_ENABLED": bool(getattr(settings, "OCR_NORMALIZATION_SHIM_ENABLED", True)),
        "OCR_TIMEOUT_SEC": int(getattr(settings, "OCR_TIMEOUT_SEC", 0) or 0),
        "OCR_MAX_BYTES": int(getattr(settings, "OCR_MAX_BYTES", 0) or 0),
        "OCR_MAX_PAGES": int(getattr(settings, "OCR_MAX_PAGES", 0) or 0),
    }


@dataclass
class OCRProviderHealthState:
    provider_name: str
    configured: bool = False
    initialized: bool = False
    healthy: bool = False
    last_check_at: Optional[str] = None
    last_error_code: Optional[str] = None
    last_error_message_sanitized: Optional[str] = None
    capabilities: Dict[str, bool] = field(default_factory=dict)


class OCRDiagnosticsRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._states: Dict[str, OCRProviderHealthState] = {}
        self._recent_errors: Deque[Dict[str, Any]] = deque(
            maxlen=max(1, int(getattr(settings, "OCR_DIAGNOSTICS_MAX_ERRORS", 10) or 10))
        )

    def reset(self) -> None:
        with self._lock:
            self._states = {}
            self._recent_errors = deque(
                maxlen=max(1, int(getattr(settings, "OCR_DIAGNOSTICS_MAX_ERRORS", 10) or 10))
            )

    def _ensure_state(self, provider_name: str) -> OCRProviderHealthState:
        normalized = resolve_ocr_provider_name(provider_name)
        state = self._states.get(normalized)
        if state is None:
            state = OCRProviderHealthState(
                provider_name=normalized,
                capabilities=get_ocr_provider_capabilities(normalized),
            )
            self._states[normalized] = state
        elif not state.capabilities:
            state.capabilities = get_ocr_provider_capabilities(normalized)
        return state

    def sync_from_settings(self) -> List[str]:
        effective_order = build_effective_ocr_provider_order()
        configured = set(effective_order)
        if (
            bool(getattr(settings, "OCR_ENABLED", True))
            and not bool(getattr(settings, "USE_STUBS", False))
            and bool(getattr(settings, "GOOGLE_CLOUD_PROJECT", None))
            and bool(getattr(settings, "GOOGLE_DOCUMENTAI_PROCESSOR_ID", None))
        ):
            configured.add("ocr_service")

        with self._lock:
            for provider_name in sorted(set(_KNOWN_PROVIDERS) | configured):
                state = self._ensure_state(provider_name)
                state.configured = provider_name in configured
        return effective_order

    def set_provider_state(
        self,
        provider_name: str,
        *,
        configured: Optional[bool] = None,
        initialized: Optional[bool] = None,
        healthy: Optional[bool] = None,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        checked: bool = True,
    ) -> Dict[str, Any]:
        with self._lock:
            state = self._ensure_state(provider_name)
            if configured is not None:
                state.configured = bool(configured)
            if initialized is not None:
                state.initialized = bool(initialized)
            if healthy is not None:
                state.healthy = bool(healthy)
            if error_code:
                state.last_error_code = str(error_code)
                state.last_error_message_sanitized = sanitize_ocr_error_message(error_message)
            elif checked:
                state.last_error_code = None
                state.last_error_message_sanitized = None
            if checked or error_code or error_message:
                state.last_check_at = _utcnow_iso()
            return asdict(state)

    def record_recent_error(
        self,
        provider_name: str,
        error_code: str,
        error_message: Optional[str],
        *,
        stage: Optional[str] = None,
        attempt_number: Optional[int] = None,
        normalized_mime: Optional[str] = None,
        page_count: Optional[int] = None,
        bytes_sent: Optional[int] = None,
    ) -> Dict[str, Any]:
        entry = {
            "timestamp": _utcnow_iso(),
            "provider_name": resolve_ocr_provider_name(provider_name),
            "error_code": str(error_code),
            "error_message_sanitized": sanitize_ocr_error_message(error_message),
            "stage": str(stage) if stage else None,
            "attempt_number": int(attempt_number) if isinstance(attempt_number, int) else None,
            "normalized_mime": str(normalized_mime) if normalized_mime else None,
            "page_count": int(page_count) if isinstance(page_count, int) else None,
            "bytes_sent": int(bytes_sent) if isinstance(bytes_sent, int) else None,
        }
        with self._lock:
            self._recent_errors.append(entry)
            self._ensure_state(entry["provider_name"])
        return entry

    def recent_errors(self, max_errors: Optional[int] = None) -> List[Dict[str, Any]]:
        with self._lock:
            items = list(self._recent_errors)
        if max_errors is not None:
            items = items[-max(0, int(max_errors)) :]
        return list(reversed(items))

    def ordered_states(self, effective_provider_order: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        effective = [resolve_ocr_provider_name(name) for name in list(effective_provider_order or []) if name]
        with self._lock:
            names = list(self._states.keys())
            order_map = {provider_name: index for index, provider_name in enumerate(effective)}
            ordered_names = sorted(
                names,
                key=lambda provider_name: (order_map.get(provider_name, len(order_map) + 1), provider_name),
            )
            return [asdict(self._states[name]) for name in ordered_names]


_ocr_diagnostics = OCRDiagnosticsRegistry()


def get_ocr_diagnostics() -> OCRDiagnosticsRegistry:
    return _ocr_diagnostics


def record_ocr_provider_initialization(
    provider_name: str,
    *,
    configured: bool,
    initialized: bool,
    healthy: Optional[bool] = None,
    error_code: Optional[str] = None,
    error_message: Optional[str] = None,
) -> Dict[str, Any]:
    registry = get_ocr_diagnostics()
    if not ocr_runtime_diagnostics_enabled():
        registry.sync_from_settings()
        return {}
    return registry.set_provider_state(
        provider_name,
        configured=configured,
        initialized=initialized,
        healthy=healthy if healthy is not None else initialized,
        error_code=error_code,
        error_message=error_message,
        checked=True,
    )


def record_ocr_provider_health_check(
    provider_name: str,
    *,
    configured: Optional[bool] = None,
    initialized: Optional[bool] = None,
    healthy: bool,
    error_code: Optional[str] = None,
    error_message: Optional[str] = None,
) -> Dict[str, Any]:
    registry = get_ocr_diagnostics()
    if not ocr_runtime_diagnostics_enabled():
        registry.sync_from_settings()
        return {}
    return registry.set_provider_state(
        provider_name,
        configured=configured,
        initialized=initialized,
        healthy=healthy,
        error_code=error_code,
        error_message=error_message,
        checked=True,
    )


def record_ocr_runtime_failure(
    provider_name: str,
    *,
    error_code: str,
    error_message: Optional[str],
    stage: Optional[str] = None,
    attempt_number: Optional[int] = None,
    normalized_mime: Optional[str] = None,
    page_count: Optional[int] = None,
    bytes_sent: Optional[int] = None,
) -> Dict[str, Any]:
    registry = get_ocr_diagnostics()
    if not ocr_runtime_diagnostics_enabled():
        registry.sync_from_settings()
        return {}
    state = registry.set_provider_state(
        provider_name,
        initialized=True,
        healthy=False,
        error_code=error_code,
        error_message=error_message,
        checked=True,
    )
    registry.record_recent_error(
        provider_name,
        error_code,
        error_message,
        stage=stage,
        attempt_number=attempt_number,
        normalized_mime=normalized_mime,
        page_count=page_count,
        bytes_sent=bytes_sent,
    )
    return state


def record_ocr_runtime_success(
    provider_name: str,
    *,
    stage: Optional[str] = None,
) -> Dict[str, Any]:
    registry = get_ocr_diagnostics()
    if not ocr_runtime_diagnostics_enabled():
        registry.sync_from_settings()
        return {}
    return registry.set_provider_state(
        provider_name,
        initialized=True,
        healthy=True,
        checked=True,
    )


async def collect_ocr_health_snapshot(*, refresh_checks: bool = True) -> Dict[str, Any]:
    registry = get_ocr_diagnostics()
    effective_provider_order = registry.sync_from_settings()

    if refresh_checks and ocr_runtime_diagnostics_enabled():
        try:
            from app.ocr.factory import get_ocr_factory

            factory = get_ocr_factory()
            effective_provider_order = list(factory.configured_providers or effective_provider_order)
            if hasattr(factory, "refresh_provider_health_states"):
                await factory.refresh_provider_health_states()
        except Exception as exc:
            logger.warning(
                "OCR diagnostics factory probe failed error_type=%s message=%s",
                type(exc).__name__,
                sanitize_ocr_error_message(str(exc)),
            )

        try:
            from app.services.ocr_service import get_ocr_service

            service = get_ocr_service()
            if hasattr(service, "refresh_health_state"):
                await service.refresh_health_state()
            else:
                healthy = await service.health_check()
                record_ocr_provider_health_check(
                    "ocr_service",
                    configured=True,
                    initialized=healthy,
                    healthy=healthy,
                )
        except Exception as exc:
            error_code = classify_ocr_provider_error(str(exc)) or "OCR_UNKNOWN_PROVIDER_ERROR"
            record_ocr_runtime_failure(
                "ocr_service",
                error_code=error_code,
                error_message=str(exc),
                stage="health_check",
            )

    return {
        "timestamp": _utcnow_iso(),
        "effective_provider_order": list(effective_provider_order),
        "feature_flags": build_ocr_feature_flags(),
        "providers": registry.ordered_states(effective_provider_order),
        "recent_errors": registry.recent_errors(max_errors=max(1, int(getattr(settings, "OCR_DIAGNOSTICS_MAX_ERRORS", 10) or 10))),
    }


async def emit_ocr_startup_summary() -> Dict[str, Any]:
    snapshot = await collect_ocr_health_snapshot(refresh_checks=True)
    provider_summary = {
        entry["provider_name"]: {
            "configured": entry["configured"],
            "initialized": entry["initialized"],
            "healthy": entry["healthy"],
            "last_error_code": entry["last_error_code"],
        }
        for entry in snapshot.get("providers") or []
    }
    logger.info(
        "OCR startup summary effective_provider_order=%s providers=%s",
        snapshot.get("effective_provider_order") or [],
        provider_summary,
    )
    return snapshot
