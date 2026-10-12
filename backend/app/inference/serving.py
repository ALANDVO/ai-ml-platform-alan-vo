"""Model serving with warm-up, batching, and health checks."""
import time, asyncio, uuid, logging
from typing import List, Optional, Dict, Any

import numpy as np

from api.schemas import PredictRequest, PredictResponse
from inference.batching import DynamicBatcher

logger = logging.getLogger(__name__)


class ServingPool:
    def __init__(self, max_batch: int = 16, timeout_ms: int = 50):
        self.batcher = DynamicBatcher(
            max_batch=max_batch,
            timeout_ms=timeout_ms,
            processor=self._predict_batch,
        )
        self._loaded: Dict[str, np.ndarray] = {}
        self._warmed: set = set()
        self.start_time = time.time()

    def start(self):
        logger.info("Serving pool started (max_batch=%d, timeout=%dms)", self.batcher.max_batch, self.batcher.timeout_ms)

    async def warmup(self, model_id: str, version: int):
        key = f"{model_id}:v{version}"
        if key in self._warmed:
            return
        # Simulate loading model weights (deterministic seed per version)
        rng = np.random.default_rng(hash(key) % 10_000)
        self._loaded[key] = rng.normal(0, 0.5, (32, 10)).astype(np.float64)
        # Run one dummy forward pass
        _ = self._loaded[key] @ np.ones(32)
        self._warmed.add(key)
        logger.info("Warmed up model %s v%d", model_id, version)

    async def _predict_batch(self, payloads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results = []
        for p in payloads:
            model_id = p["model_id"]
            version = p["version"]
            inputs = p["inputs"]
            key = f"{model_id}:v{version}"
            if key not in self._loaded:
                await self.warmup(model_id, version)
            weights = self._loaded[key]
            x = np.asarray(inputs, dtype=np.float64)
            if x.ndim == 1:
                x = x[None, :]
            logits = x @ weights
            exp = np.exp(logits - logits.max(axis=1, keepdims=True))
            probs = (exp / exp.sum(axis=1, keepdims=True)).tolist()
            results.append(probs)
        return results

    async def predict(self, body: PredictRequest) -> PredictResponse:
        start = time.perf_counter()
        payload = {"model_id": body.model_id, "version": body.version, "inputs": body.inputs}
        result = await self.batcher.submit(payload)
        latency_ms = (time.perf_counter() - start) * 1000
        return PredictResponse(
            model_id=body.model_id,
            version=body.version,
            predictions=result,
            batch_id=uuid.uuid4().hex,
            latency_ms=latency_ms,
        )

    def health(self) -> Dict[str, Any]:
        return {
            "status": "ok",
            "uptime_s": time.time() - self.start_time,
            "loaded_models": len(self._loaded),
            "warmed_models": len(self._warmed),
            "batcher": self.batcher.stats(),
        }


serving_pool = ServingPool(max_batch=16, timeout_ms=50)
