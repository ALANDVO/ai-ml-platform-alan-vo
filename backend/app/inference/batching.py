"""Request batching with dynamic batch sizing and timeout-based flush."""
import asyncio
import time
import uuid
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
        self.processor = processor
        self._queue: List[BatchItem] = []
        self._lock = asyncio.Lock()
        self._flush_task: Optional[asyncio.Task] = None
        self._first_item_time: Optional[float] = None
        self.total_batches = 0
        self.total_items = 0

    async def submit(self, payload: Any) -> Any:
        item = BatchItem(payload)
        should_flush = False
        async with self._lock:
            if not self._queue:
                self._first_item_time = time.time()
                self._schedule_flush()
            self._queue.append(item)
            should_flush = len(self._queue) >= self.max_batch
        if should_flush:
            await self._flush()
        return await item.future

    def _schedule_flush(self):
        if self._flush_task is None or self._flush_task.done():
            self._flush_task = asyncio.create_task(self._timeout_flush())

    async def _timeout_flush(self):
        # Calculate remaining time until timeout
        async with self._lock:
            if not self._queue or self._first_item_time is None:
                return
            elapsed = (time.time() - self._first_item_time) * 1000
            remaining_ms = max(0, self.timeout_ms - elapsed)
        
        if remaining_ms > 0:
            await asyncio.sleep(remaining_ms / 1000.0)
        
        should_flush = False
        async with self._lock:
            if self._queue and self._first_item_time is not None:
                elapsed = (time.time() - self._first_item_time) * 1000
                if elapsed >= self.timeout_ms:
                    should_flush = True
        if should_flush:
            await self._flush()
        async with self._lock:
            if self._queue:
                self._schedule_flush()

    async def _flush(self):
        batch = None
        async with self._lock:
            if not self._queue:
                return
            batch = list(self._queue)
            self._queue.clear()
            self._first_item_time = None
        if batch:
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
