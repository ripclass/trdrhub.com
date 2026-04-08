"""Publish validation pipeline progress events to Redis pub/sub.

These events power the SSE stream consumed by the frontend during upload,
giving the user real-time stage progress instead of a fake client-side timer.

Channels:
- ``validation:job:{job_id}`` — keyed by the validation session UUID
- ``validation:client:{client_request_id}`` — keyed by a client-generated UUID
  the frontend supplies via the ``X-Client-Request-ID`` header. This lets the
  frontend subscribe BEFORE the backend has even created the session.

Both channels carry the same event payload. Publishers should call this from
inside the existing ``checkpoint()`` closure in validate_run.py — failures are
swallowed silently because progress streaming is best-effort and must never
break the validation pipeline itself.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, Optional

from redis.exceptions import RedisError

from app.utils.redis_cache import get_redis

logger = logging.getLogger(__name__)


# Map of checkpoint name -> (progress_pct, human-readable message)
# Progress percentages are coarse buckets that approximate where the user is
# in the pipeline. The frontend uses these to drive a determinate progress bar.
CHECKPOINT_PROGRESS: Dict[str, tuple[int, str]] = {
    "request_received": (5, "Request received"),
    "form_parsed": (10, "Files received and parsed"),
    "session_created": (15, "Validation session created"),
    "ocr_extraction_complete": (35, "Document text extracted"),
    "lc_type_detected": (40, "Letter of credit type detected"),
    "validation_gate_complete": (50, "Validation gate cleared"),
    "ai_validation_complete": (65, "AI document review complete"),
    "crossdoc_validation_complete": (75, "Cross-document checks complete"),
    "issue_cards_built": (80, "Discrepancies compiled"),
    "structured_result_built": (85, "Validation result assembled"),
    "post_sanctions_screening": (90, "Sanctions screening complete"),
    "response_building": (95, "Finalizing response"),
}


async def publish_progress(
    *,
    checkpoint_name: str,
    job_id: Optional[str] = None,
    client_request_id: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """Publish a progress event for a single checkpoint.

    Best-effort: any Redis or serialization error is logged at DEBUG level
    and swallowed. The validation pipeline must never fail because progress
    publishing failed.
    """
    if not job_id and not client_request_id:
        return

    progress_pct, message = CHECKPOINT_PROGRESS.get(checkpoint_name, (None, checkpoint_name))

    payload: Dict[str, Any] = {
        "stage": checkpoint_name,
        "progress": progress_pct,
        "message": message,
        "ts": time.time(),
    }
    if extra:
        payload.update(extra)

    try:
        redis_client = await get_redis()
    except Exception as exc:  # noqa: BLE001 - best-effort
        logger.debug("Progress publish skipped (no redis): %s", exc)
        return

    if redis_client is None:
        return

    serialized = json.dumps(payload)

    try:
        if job_id:
            await redis_client.publish(f"validation:job:{job_id}", serialized)
        if client_request_id:
            await redis_client.publish(f"validation:client:{client_request_id}", serialized)
    except RedisError as exc:
        logger.debug("Progress publish failed: %s", exc)
    except Exception as exc:  # noqa: BLE001 - best-effort
        logger.debug("Unexpected progress publish error: %s", exc)


async def publish_completion(
    *,
    job_id: Optional[str] = None,
    client_request_id: Optional[str] = None,
    success: bool = True,
    error_message: Optional[str] = None,
) -> None:
    """Publish a terminal completion event.

    The SSE stream uses this to know it should close the connection.
    """
    if not job_id and not client_request_id:
        return

    payload: Dict[str, Any] = {
        "stage": "completed" if success else "failed",
        "progress": 100,
        "message": "Validation complete" if success else (error_message or "Validation failed"),
        "ts": time.time(),
        "terminal": True,
        "success": success,
    }
    if job_id:
        payload["job_id"] = job_id
    if error_message:
        payload["error"] = error_message

    try:
        redis_client = await get_redis()
    except Exception as exc:  # noqa: BLE001
        logger.debug("Completion publish skipped (no redis): %s", exc)
        return

    if redis_client is None:
        return

    serialized = json.dumps(payload)

    try:
        if job_id:
            await redis_client.publish(f"validation:job:{job_id}", serialized)
        if client_request_id:
            await redis_client.publish(f"validation:client:{client_request_id}", serialized)
    except RedisError as exc:
        logger.debug("Completion publish failed: %s", exc)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Unexpected completion publish error: %s", exc)
