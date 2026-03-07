"""
Internal OCR health endpoint.
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request

from ..config import settings
from ..middleware.logging import get_request_logger
from ..services.ocr_diagnostics import collect_ocr_health_snapshot


router = APIRouter(prefix="/api/ocr", tags=["ocr"])


def _authorize_ocr_health_request(request: Request) -> None:
    if not bool(getattr(settings, "OCR_HEALTH_ENDPOINT_ENABLED", True)):
        raise HTTPException(status_code=404, detail="OCR health endpoint disabled")

    health_token = getattr(settings, "OCR_HEALTH_TOKEN", None)
    if health_token:
        provided_token = request.headers.get("X-OCR-Health") or request.query_params.get("token")
        if provided_token != health_token:
            raise HTTPException(status_code=403, detail="OCR health token required")
        return

    client_host = getattr(request.client, "host", "")
    if client_host not in {"127.0.0.1", "::1", "localhost"}:
        raise HTTPException(status_code=403, detail="OCR health diagnostics limited to local access")


@router.get("/health")
async def get_ocr_health(request: Request) -> Dict[str, Any]:
    _authorize_ocr_health_request(request)
    logger = get_request_logger(request, "ocr_health")
    snapshot = await collect_ocr_health_snapshot(refresh_checks=True)
    logger.info(
        "OCR health requested",
        provider_count=len(snapshot.get("providers") or []),
        effective_provider_order=snapshot.get("effective_provider_order") or [],
    )
    return snapshot
