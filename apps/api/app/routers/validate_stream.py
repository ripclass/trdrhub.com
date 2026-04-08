"""SSE endpoint for real-time validation pipeline progress.

This stream lets the frontend receive checkpoint events as the validation
pipeline runs, replacing the fake client-side timer in the upload UI.

Architecture:
- The frontend generates a UUID v4 (``client_request_id``) BEFORE submitting
  the validation POST. It opens an EventSource connection to this stream,
  subscribed to ``validation:client:{client_request_id}``. Then it submits the
  POST with the same UUID in the ``X-Client-Request-ID`` header.
- The validation pipeline's ``checkpoint()`` closure publishes events to that
  Redis pub/sub channel as it processes. The SSE consumer receives them in
  real time.
- Once the pipeline completes (success or failure), a terminal event is
  published with ``terminal: true`` and the SSE connection closes itself.

Why client-generated request IDs:
- The frontend doesn't have the server-side ``job_id`` until the POST returns
  (which is the very thing we want to avoid waiting for). The client request
  ID solves the chicken-and-egg problem without requiring the API to return
  early.
- The synchronous POST contract is preserved — zero risk of breaking the
  existing useValidate hook or its consumers.
"""

from __future__ import annotations

import asyncio
import json
import logging
import secrets
import time
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from app.config import settings
from app.utils.redis_cache import get_redis
from app.utils.token_utils import create_signed_token, verify_signed_token

logger = logging.getLogger(__name__)


# Stream tokens are short-lived — frontend fetches one immediately before
# opening the EventSource. 60 seconds is plenty for that round trip.
STREAM_TOKEN_EXPIRY_SECONDS = 60

# Maximum lifetime of a single SSE connection. Validation pipelines that take
# longer than this should be the rare exception; the frontend will reconnect
# automatically via EventSource's built-in retry.
MAX_STREAM_DURATION_SECONDS = 300


def build_router(shared: Any) -> APIRouter:
    """Build the validation stream router.

    Receives the same ``shared`` namespace as the other validate sub-routers
    so it can access ``Depends``, ``get_user_optional``, etc. We only need a
    couple of them.
    """

    if isinstance(shared, dict):
        get_user_optional = shared["get_user_optional"]
        Depends = shared["Depends"]
        User = shared["User"]
    else:
        get_user_optional = getattr(shared, "get_user_optional")
        Depends = getattr(shared, "Depends")
        User = getattr(shared, "User")

    router = APIRouter()

    @router.get("/stream-token")
    async def get_validation_stream_token(
        current_user: User = Depends(get_user_optional),
    ):
        """Issue a short-lived signed token for the validation progress SSE.

        Auth is intentionally lenient — anonymous users can also stream their
        own progress (the upload endpoint itself accepts anonymous validation
        in some configurations). Token expiry is short, and the channel is
        keyed by a client-generated UUID that the user already knows.
        """
        token = create_signed_token(
            secret_key=settings.SECRET_KEY,
            payload={
                "uid": str(current_user.id) if current_user else "anonymous",
                "nonce": secrets.token_urlsafe(8),
            },
            expires_in=STREAM_TOKEN_EXPIRY_SECONDS,
        )

        return {
            "token": token,
            "expires_in": STREAM_TOKEN_EXPIRY_SECONDS,
        }

    @router.get("/stream/{client_request_id}")
    async def stream_validation_progress(
        client_request_id: str,
        sse_token: str = Query(..., description="Short-lived signed token from /stream-token"),
    ):
        """Stream validation progress events for a single client request id.

        The frontend opens this connection BEFORE posting to /api/validate,
        using the same client_request_id it will send in the X-Client-Request-ID
        header. The pipeline publishes checkpoint events to a Redis pub/sub
        channel keyed by this id; this endpoint relays them as SSE.
        """
        # Verify token signature and expiry
        try:
            verify_signed_token(settings.SECRET_KEY, sse_token)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired stream token",
            )

        # Basic sanity check on the client_request_id (must look like a UUID)
        if not client_request_id or len(client_request_id) < 8 or len(client_request_id) > 64:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid client_request_id",
            )

        channel_name = f"validation:client:{client_request_id}"

        async def event_generator():
            redis_client = None
            pubsub = None
            stream_started_at = time.monotonic()
            last_keepalive = stream_started_at

            try:
                redis_client = await get_redis()
            except Exception as exc:  # noqa: BLE001
                logger.debug("SSE: failed to get redis client: %s", exc)
                redis_client = None

            if redis_client is None:
                # Redis unavailable — emit a single info event then close.
                # Frontend will fall back to its own fake timer.
                yield f"data: {json.dumps({'stage': 'unavailable', 'message': 'Real-time progress unavailable', 'terminal': True})}\n\n"
                return

            try:
                pubsub = redis_client.pubsub()
                await pubsub.subscribe(channel_name)

                # Send initial connection event so the frontend knows we're live
                yield f"data: {json.dumps({'stage': 'connected', 'progress': 0, 'message': 'Connected to progress stream'})}\n\n"

                while True:
                    # Check overall stream duration
                    if time.monotonic() - stream_started_at > MAX_STREAM_DURATION_SECONDS:
                        yield f"data: {json.dumps({'stage': 'timeout', 'message': 'Stream max duration reached', 'terminal': True})}\n\n"
                        break

                    # Poll Redis pubsub for the next message with a short timeout
                    try:
                        message = await asyncio.wait_for(
                            pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0),
                            timeout=2.0,
                        )
                    except asyncio.TimeoutError:
                        message = None

                    if message and message.get("type") == "message":
                        data = message.get("data")
                        if isinstance(data, bytes):
                            data = data.decode("utf-8")
                        if isinstance(data, str):
                            yield f"data: {data}\n\n"
                            # If this was a terminal event, close the stream
                            try:
                                parsed = json.loads(data)
                                if parsed.get("terminal"):
                                    break
                            except (ValueError, TypeError):
                                pass

                    # Send keepalive comment every 15s to prevent proxy timeouts
                    now = time.monotonic()
                    if now - last_keepalive >= 15:
                        yield ": keepalive\n\n"
                        last_keepalive = now

            except asyncio.CancelledError:
                # Client disconnected
                pass
            except Exception as exc:  # noqa: BLE001
                logger.debug("SSE event generator error: %s", exc)
                error_payload = {"stage": "error", "message": str(exc), "terminal": True}
                yield f"data: {json.dumps(error_payload)}\n\n"
            finally:
                if pubsub is not None:
                    try:
                        await pubsub.unsubscribe(channel_name)
                        await pubsub.close()
                    except Exception:  # noqa: BLE001
                        pass

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    return router


__all__ = ["build_router"]
