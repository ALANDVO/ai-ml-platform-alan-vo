"""Request batching with dynamic batch sizing and timeout-based flush."""
import asyncio, time, uuid
from typing import List, Dict, Any, Optional


class BatchItem:
    __slots__ = ("id", "payload", "future", "created_at")

    def __init__(self, payload: Any):
        self.id = uuid.uuid4().hex
        self.payload = payload
        self.future: asyncio.Future = asyncio.get_event_loop().create_future()
        self.created_at = time.time()


class DynamicBatcher:
    """Collects requests into batches, flushing when batch_size is reached or
    timeout_ms elapses since the first queued item."""

    def __init__(self, max_batch: int = 16, timeout_ms: int = 50, processor=None):
        self.max_batch = max_batch
        self.timeout_ms = timeout_ms
        self.processor = processor  # async callable(batch: list) -> list
        self._queue: List[BatchItem] = []
        self._lock = asyncio.Lock()
        self._flush_task: Optional[asyncio.Task] = None
        self.total_batches = 0
        self.total_items = 0

    async def submit(self, payload: Any) -> Any:
        item = BatchItem(payload)
        should_flush = False
        async with self._lock:
            self._queue.append(item)
            should_flush = len(self._queue) >= self.max_batch
        if should_flush:
            await self._flush()
        return await item.future

    async def _flush(self):
        async with self._lock:
            if not self._queue:
                return
            batch = list(self._queue)
            self._queue.clear()
        results = await self._process(batch)
        for item, result in zip(batch, results):
            if not item.future.done():
                item.future.set_result(result)

    async def _process(self, batch: List[BatchItem]) -> List[Any]:
        self.total_batches += 1
        self.total_items += len(batch)
        if self.processor:
            return await self.processor([b.payload for b in batch])
        return [b.payload for b in batch]

    def stats(self) -> Dict[str, Any]:
        return {
            "queue_depth": len(self._queue),
            "max_batch": self.max_batch,
            "timeout_ms": self.timeout_ms,
            "total_batches": self.total_batches,
            "total_items": self.total_items,
        }
