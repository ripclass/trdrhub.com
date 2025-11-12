"""
Queue module stub for bulk processing.

This is a placeholder implementation that allows the code to run
without a full queue system. Jobs are logged but not actually queued.
"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class Queue:
    """Stub queue implementation."""
    
    def __init__(self, name: str):
        self.name = name
        logger.warning(f"Queue '{name}' initialized as stub - jobs will not be queued")
    
    async def enqueue(self, job_type: str, **kwargs):
        """Stub enqueue - logs but doesn't actually queue."""
        logger.info(f"Queue stub: Would enqueue {job_type} with args: {kwargs}")
        # No-op for now
        pass


def get_queue(name: str) -> Queue:
    """Get a queue instance."""
    return Queue(name)

