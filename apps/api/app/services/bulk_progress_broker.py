"""In-memory pub/sub for bulk-job progress events — Phase A1 part 2.

Process-local, single-instance design. The bulk validation processor
publishes per-item events as it runs; the SSE endpoint subscribes and
streams them to the customer dashboard. No Redis, no external queue:
Path A v1 runs on a single Render instance, and this broker dies with
the process.

If/when we go multi-instance, this is the seam to swap for a Redis
pubsub or Vercel Queues. The public surface (``publish``, ``subscribe``,
``close``) stays stable.

Event shape is whatever the publisher hands in — typically:
    {"event": "item_started", "item_id": str, "lc_identifier": str, ...}
The SSE endpoint serializes the whole dict to JSON and forwards it.

Cleanup contract: every ``subscribe()`` returns an async iterator. When
the consumer's task ends (client disconnect, request cancel), it calls
``unsubscribe`` in a finally — even if it doesn't, ``close()`` on job
completion drops every queue and frees memory.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, AsyncIterator, Dict, Set
from uuid import UUID

logger = logging.getLogger(__name__)

# Sentinel pushed to a subscriber's queue when the broker decides this
# subscription should drain and exit. Using a private object means
# events themselves can never collide with this signal.
_TERMINATED = object()


class BulkProgressBroker:
    """Per-process broker mapping job_id -> set of subscriber queues."""

    def __init__(self) -> None:
        # job_id -> set of asyncio.Queue (one per active subscriber).
        self._subscribers: Dict[str, Set[asyncio.Queue]] = {}
        # Lock guards the dict + set mutations. Events are dispatched
        # outside the lock to keep publish() non-blocking on slow
        # subscribers.
        self._lock = asyncio.Lock()

    @staticmethod
    def _key(job_id: UUID | str) -> str:
        return str(job_id)

    async def publish(self, job_id: UUID | str, event: Dict[str, Any]) -> None:
        """Fan out ``event`` to every subscriber for ``job_id``.

        Non-blocking on the publisher side: if a subscriber's queue is
        full (subscriber is slow), the event is dropped FOR THAT
        subscriber only. Other subscribers still receive it. This
        prevents one stuck SSE client from stalling the worker.
        """
        key = self._key(job_id)
        async with self._lock:
            queues = list(self._subscribers.get(key, ()))
        for q in queues:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning(
                    "bulk_progress_broker: dropping event for slow subscriber on job=%s",
                    key,
                )

    async def subscribe(
        self, job_id: UUID | str, *, maxsize: int = 256
    ) -> AsyncIterator[Dict[str, Any]]:
        """Yield events for ``job_id`` until ``close(job_id)`` is called
        or the consumer's task is cancelled.

        Usage:
            async for event in broker.subscribe(job_id):
                yield f"data: {json.dumps(event)}\\n\\n"
        """
        key = self._key(job_id)
        queue: asyncio.Queue = asyncio.Queue(maxsize=maxsize)
        async with self._lock:
            self._subscribers.setdefault(key, set()).add(queue)
        try:
            while True:
                item = await queue.get()
                if item is _TERMINATED:
                    return
                yield item
        finally:
            async with self._lock:
                bucket = self._subscribers.get(key)
                if bucket is not None:
                    bucket.discard(queue)
                    if not bucket:
                        self._subscribers.pop(key, None)

    async def close(self, job_id: UUID | str) -> None:
        """Signal every subscriber for ``job_id`` to exit cleanly.

        Called by the bulk processor when a job reaches a terminal
        state (succeeded, failed, partial, cancelled). Subscribers
        receive any already-queued events first, then the sentinel,
        then their generator exits.
        """
        key = self._key(job_id)
        async with self._lock:
            queues = list(self._subscribers.get(key, ()))
        for q in queues:
            try:
                q.put_nowait(_TERMINATED)
            except asyncio.QueueFull:
                # If the queue is full, the consumer is already going to
                # drain it eventually — close() best-effort, the
                # subscribe() finally still runs on cancel.
                pass

    async def subscriber_count(self, job_id: UUID | str) -> int:
        """How many active SSE consumers are watching this job. Mostly
        for tests + observability.
        """
        async with self._lock:
            return len(self._subscribers.get(self._key(job_id), ()))


# Process-wide singleton. Routers + the processor import this directly.
broker = BulkProgressBroker()


__all__ = ["BulkProgressBroker", "broker"]
