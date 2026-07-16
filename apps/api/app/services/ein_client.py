"""Narrow server-side client for the external EIN credential service."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from app.config import settings


class EINAPIError(RuntimeError):
    """EIN could not verify the requested presentations."""


def is_ein_configured() -> bool:
    return bool(
        getattr(settings, "PROOFLINE_EIN_ENABLED", False)
        and getattr(settings, "EIN_API_URL", "")
        and getattr(settings, "EIN_API_KEY", "")
    )


class EINClient:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        verify_path: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self.base_url = (base_url or settings.EIN_API_URL).rstrip("/")
        self.api_key = api_key or settings.EIN_API_KEY
        self.verify_path = verify_path or settings.EIN_VERIFY_PATH
        self.timeout_seconds = timeout_seconds or settings.EIN_API_TIMEOUT_SECONDS

    async def verify_presentations(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.base_url or not self.api_key:
            raise EINAPIError("EIN verification is not configured")
        last_transport_error: Exception | None = None
        for attempt in range(2):
            try:
                async with httpx.AsyncClient(
                    base_url=self.base_url,
                    headers={"Content-Type": "application/json", "X-API-Key": self.api_key},
                    timeout=httpx.Timeout(self.timeout_seconds),
                ) as client:
                    response = await client.post(self.verify_path, json=payload)
            except httpx.TimeoutException as exc:
                last_transport_error = exc
                if attempt == 0:
                    await asyncio.sleep(0.2)
                    continue
                raise TimeoutError("EIN verification timed out") from exc
            except httpx.TransportError as exc:
                last_transport_error = exc
                if attempt == 0:
                    await asyncio.sleep(0.2)
                    continue
                raise EINAPIError("EIN verification service is unreachable") from exc
            if response.status_code >= 500 and attempt == 0:
                await asyncio.sleep(0.2)
                continue
            if response.status_code >= 400:
                raise EINAPIError(f"EIN verification failed with status {response.status_code}")
            body = response.json()
            if not isinstance(body, dict):
                raise EINAPIError("EIN returned an invalid verification response")
            data = body.get("data", body)
            if not isinstance(data, dict):
                raise EINAPIError("EIN returned an invalid verification payload")
            return data
        raise EINAPIError("EIN verification service is unreachable") from last_transport_error


def get_ein_client() -> EINClient:
    return EINClient()


__all__ = ["EINAPIError", "EINClient", "get_ein_client", "is_ein_configured"]
