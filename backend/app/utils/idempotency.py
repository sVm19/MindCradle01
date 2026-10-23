import asyncio
import logging
import time
from typing import Any, Callable, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class IdempotencyRecord:
    def __init__(self):
        self.lock = asyncio.Lock()
        self.status: str = "in_progress"  # "in_progress" | "completed" | "failed"
        self.response: Any = None
        self.error: Optional[Exception] = None
        self.created_at: float = time.time()


class IdempotencyManager:
    """
    In-memory async idempotency manager with TTL and concurrent request locking.
    Prevents duplicate operations when requests with the same idempotency key
    are fired concurrently or retried.
    """

    def __init__(self, ttl_seconds: int = 600):
        self.ttl = ttl_seconds
        self._records: Dict[str, IdempotencyRecord] = {}
        self._global_lock = asyncio.Lock()

    def _cleanup_expired(self):
        now = time.time()
        expired_keys = [
            k for k, v in self._records.items() if (now - v.created_at) > self.ttl
        ]
        for k in expired_keys:
            del self._records[k]

    async def get_or_create(self, key: str) -> Tuple[IdempotencyRecord, bool]:
        """
        Returns (record, is_new).
        If is_new is True, the current caller must execute the operation,
        set record.response, and mark record.status = 'completed'.
        If is_new is False, another request has already started or completed.
        """
        async with self._global_lock:
            self._cleanup_expired()
            if key in self._records:
                return self._records[key], False

            record = IdempotencyRecord()
            self._records[key] = record
            return record, True

    async def evict(self, key: str):
        async with self._global_lock:
            self._records.pop(key, None)


# Default shared idempotency manager with 10-minute TTL
idempotency_manager = IdempotencyManager(ttl_seconds=600)


async def execute_idempotent(key: Optional[str], coro_fn: Callable, *args, **kwargs) -> Any:
    """
    Executes a coroutine idempotently based on the given key.
    If key is None or empty, the coroutine is executed normally.
    If a request with this key is currently in progress, subsequent requests await
    the in-flight request and return the exact same response without re-executing.
    If a request with this key has already completed within the TTL, the cached
    response is returned immediately.
    """
    if not key:
        return await coro_fn(*args, **kwargs)

    record, is_new = await idempotency_manager.get_or_create(key)

    if is_new:
        async with record.lock:
            try:
                result = await coro_fn(*args, **kwargs)
                record.response = result
                record.status = "completed"
                logger.info("Idempotent operation succeeded and cached for key: %s", key)
                return result
            except Exception as e:
                record.status = "failed"
                record.error = e
                # Evict on hard failure so the client can retry safely
                await idempotency_manager.evict(key)
                logger.warning("Idempotent operation failed for key %s, evicted: %s", key, e)
                raise
    else:
        logger.info("Idempotent duplicate request detected for key: %s. Awaiting existing execution.", key)
        async with record.lock:
            if record.status == "completed":
                logger.info("Returning cached idempotent response for key: %s", key)
                return record.response
            if record.status == "failed" and record.error:
                raise record.error
            # Fallback if somehow not marked
            return await coro_fn(*args, **kwargs)
