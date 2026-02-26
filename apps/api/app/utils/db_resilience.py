"""Database outage detection and HTTP mapping helpers."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.exc import DisconnectionError, OperationalError, SQLAlchemyError, TimeoutError as SATimeoutError

DB_OUTAGE_MESSAGE = (
    "Database temporarily unavailable. Please retry shortly. "
    "If this continues, contact support and include this request time."
)


def is_database_unavailable_error(exc: Exception) -> bool:
    """Best-effort detection for transient database connectivity failures."""
    if isinstance(exc, (OperationalError, DisconnectionError, SATimeoutError)):
        return True

    if isinstance(exc, SQLAlchemyError):
        raw = str(getattr(exc, "orig", exc)).lower()
    else:
        raw = str(exc).lower()

    db_signals = (
        "connection refused",
        "could not connect to server",
        "server closed the connection unexpectedly",
        "name or service not known",
        "temporary failure in name resolution",
        "timeout expired",
        "connection timed out",
        "port 6543",
    )
    return any(signal in raw for signal in db_signals)


def raise_db_http_503_if_unavailable(exc: Exception, *, detail: Any | None = None) -> None:
    """Raise HTTP 503 for DB outages; no-op otherwise."""
    if not is_database_unavailable_error(exc):
        return

    payload = detail or {
        "error_code": "database_unavailable",
        "message": DB_OUTAGE_MESSAGE,
        "action": "Retry in 30-60 seconds. If persistent, verify DB networking/secrets.",
    }
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=payload) from exc
