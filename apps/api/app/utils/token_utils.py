"""Utility helpers for signed, expiring tokens."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any, Dict


def _urlsafe_b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _urlsafe_b64decode(data: str) -> bytes:
    padding = '=' * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def create_signed_token(secret_key: str, payload: Dict[str, Any], expires_in: int) -> str:
    """Create a signed token with embedded expiry."""

    data = dict(payload)
    data["exp"] = int(time.time()) + int(expires_in)

    body = json.dumps(data, separators=(",", ":"), sort_keys=True)
    signature = hmac.new(secret_key.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).digest()

    return f"{_urlsafe_b64encode(body.encode('utf-8'))}.{_urlsafe_b64encode(signature)}"


def verify_signed_token(secret_key: str, token: str) -> Dict[str, Any]:
    """Verify token signature and expiry and return payload."""

    try:
        body_part, sig_part = token.split(".", 1)
    except ValueError as exc:  # pragma: no cover - defensive
        raise ValueError("invalid token format") from exc

    body_bytes = _urlsafe_b64decode(body_part)
    expected_sig = hmac.new(secret_key.encode("utf-8"), body_bytes, hashlib.sha256).digest()
    provided_sig = _urlsafe_b64decode(sig_part)

    if not hmac.compare_digest(expected_sig, provided_sig):
        raise ValueError("invalid token signature")

    payload = json.loads(body_bytes.decode("utf-8"))

    exp = payload.get("exp")
    if not isinstance(exp, int):
        raise ValueError("missing expiry")
    if time.time() > exp:
        raise ValueError("token expired")

    return payload

