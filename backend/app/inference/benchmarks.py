"""Benchmarking harness for dynamic batching inference server.

Measures latency vs queue depth under simulated inference loads and
adaptive timeout adjustment under variable concurrency.
"""
import asyncio
import time
import statistics
import uuid
from dataclasses import dataclass, field
from typing import List, Dict, Any, Callable, Optional
from inference.batching import DynamicBatcher, BatchItem


@dataclass
class BenchmarkResult:
    """Results from a single benchmark run."""
    concurrency: int
    total_requests: int
    max_batch: int
    timeout_ms: int
    processor_ms: float
    latencies_ms: List[float]
    batch_sizes: List[int]
    throughput_rps: float
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    avg_batch_size: float
    max_queue_depth: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "concurrency": self.concurrency,
            "total_requests": self.total_requests,
            "max_batch": self.max_batch,
            "timeout_ms": self.timeout_ms,
            "processor_ms": self.processor_ms,
            "throughput_rps": round(self.throughput_rps, 2),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "p50_latency_ms": round(self.p50_latency_ms, 2),
            "p95_latency_ms": round(self.p95_latency_ms, 2),
            "p99_latency_ms": round(self.p99_latency_ms, 2),
            "avg_batch_size": round(self.avg_batch_size, 2),
            "max_queue_depth": self.max_queue_depth,
            "batch_size_distribution": self._batch_distribution(),
        }

    def _batch_distribution(self) -> Dict[int, int]:
        dist: Dict[int, int] = {}
        for size in self.batch_sizes:
            dist[size] = dist.get(size, 0) + 1
        return dict(sorted(dist.items()))


@dataclass
class AdaptiveBenchmarkResult:
    """Results from adaptive timeout benchmark."""
    initial_timeout_ms: int
    final_timeout_ms: int
    concurrency: int
    total_requests: int
    max_batch: int
    latencies_before_ms: List[float]
    latencies_after_ms: List[float]
    throughput_before_rps: float
    throughput_after_rps: float
    timeout_adjustments: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "initial_timeout_ms": self.initial_timeout_ms,
            "final_timeout_ms": self.final_timeout_ms,
            "concurrency": self.concurrency,
            "total_requests": self.total_requests,
            "max_batch": self.max_batch,
            "throughput_before_rps": round(self.throughput_before_rps, 2),
            "throughput_after_rps": round(self.throughput_after_rps, 2),
            "avg_latency_before_ms": round(statistics.mean(self.latencies_before_ms), 2) if self.latencies_before_ms else 0,
            "avg_latency_after_ms": round(statistics.mean(self.latencies_after_ms), 2) if self.latencies_after_ms else 0,
            "p95_latency_before_ms": round(_percentile(self.latencies_before_ms, 95), 2) if self.latencies_before_ms else 0,
            "p95_latency_after_ms": round(_percentile(self.latencies_after_ms, 95), 2) if self.latencies_after_ms else 0,
            "timeout_adjustments": self.timeout_adjustments,
        }


def _percentile(values: List[float], p: float) -> float:
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    k = (len(sorted_vals) - 1) * p / 100
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return sorted_vals[f]
    return sorted_vals[f] * (c - k) + sorted_vals[c] * (k - f)


async def _mock_processor(batch: List[Any], processing_time_ms: float) -> List[Any]:
    """Mock processor that simulates inference work."""
    await asyncio.sleep(processing_time_ms / 1000.0)
    return [{"result": f"item_{i}", "batch_size": len(batch)} for i, _ in enumerate(batch)]


class BatchingBenchmark:
    """Runs benchmarks against DynamicBatcher with configurable load patterns."""

    def __init__(
        self,
        max_batch: int = 16,
        timeout_ms: int = 50,
        processor: Optional[Callable] = None,
        processor_ms: float = 5.0,
    ):
        self.max_batch = max_batch
        self.timeout_ms = timeout_ms
        self.processor_ms = processor_ms
        self._processor = processor or (lambda batch: _mock_processor(batch, processor_ms))
        self._latencies: List[float] = []
        self._batch_sizes: List[int] = []
        self._max_queue_depth = 0

    async def _submit_with_timing(self, batcher: DynamicBatcher, payload: Any) -> float:
        """Submit a request and measure latency."""
        start = time.perf_counter()
        await batcher.submit(payload)
        return (time.perf_counter() - start) * 1000

    async def run_concurrency_benchmark(
        self,
        concurrency: int,
        total_requests: int,
    ) -> BenchmarkResult:
        """Run benchmark with fixed concurrency level."""
        self._latencies.clear()
        self._batch_sizes.clear()
        self._max_queue_depth = 0

        batcher = DynamicBatcher(
            max_batch=self.max_batch,
            timeout_ms=self.timeout_ms,
            processor=self._processor,
        )

        async def worker(worker_id: int, requests_per_worker: int):
            for i in range(requests_per_worker):
                payload = {"worker": worker_id, "seq": i, "data": [0.0] * 10}
                latency = await self._submit_with_timing(batcher, payload)
                self._latencies.append(latency)

                # Track batch sizes from batcher stats
                stats = batcher.stats()
                self._batch_sizes.append(stats.get("total_batches", 0))
                self._max_queue_depth = max(self._max_queue_depth, stats.get("queue_depth", 0))

        requests_per_worker = total_requests // concurrency
        remainder = total_requests % concurrency

        tasks = []
        for w in range(concurrency):
            rpw = requests_per_worker + (1 if w < remainder else 0)
            if rpw > 0:
                tasks.append(asyncio.create_task(worker(w, rpw)))

        await asyncio.gather(*tasks)

        # Collect final batch sizes from batcher internal state if available
        final_stats = batcher.stats()
        total_batches = final_stats.get("total_batches", 1)
        total_items = final_stats.get("total_items", total_requests)
        avg_batch = total_items / total_batches if total_batches > 0 else 1

        # Reconstruct batch sizes from total items/batches (approximation)
        self._batch_sizes = [min(self.max_batch, total_items // total_batches + (1 if i < total_items % total_batches else 0))
                             for i in range(total_batches)]

        duration_s = (max(self._latencies) if self._latencies else 0) / 1000
        throughput = total_requests / duration_s if duration_s > 0 else 0

        return BenchmarkResult(
            concurrency=concurrency,
            total_requests=total_requests,
            max_batch=self.max_batch,
            timeout_ms=self.timeout_ms,
            processor_ms=self.processor_ms,
            latencies_ms=self._latencies,
            batch_sizes=self._batch_sizes,
            throughput_rps=throughput,
            avg_latency_ms=statistics.mean(self._latencies) if self._latencies else 0,
            p50_latency_ms=_percentile(self._latencies, 50) if self._latencies else 0,
            p95_latency_ms=_percentile(self._latencies, 95) if self._latencies else 0,
            p99_latency_ms=_percentile(self._latencies, 99) if self._latencies else 0,
            avg_batch_size=avg_batch,
            max_queue_depth=self._max_queue_depth,
        )

    async def run_sweep(
        self,
        concurrency_levels: List[int],
        total_requests: int = 1000,
    ) -> List[BenchmarkResult]:
        """Run benchmarks across multiple concurrency levels."""
        results = []
        for concurrency in concurrency_levels:
            result = await self.run_concurrency_benchmark(concurrency, total_requests)
            results.append(result)
        return results


class AdaptiveTimeoutBenchmark:
    """Benchmarks adaptive timeout adjustment under variable concurrency."""

    def __init__(
        self,
        max_batch: int = 16,
        initial_timeout_ms: int = 50,
        processor_ms: float = 5.0,
        target_latency_ms: float = 100.0,
        adjustment_factor: float = 1.2,
        max_timeout_ms: int = 500,
        min_timeout_ms: int = 10,
    ):
        self.max_batch = max_batch
        self.initial_timeout_ms = initial_timeout_ms
        self.target_latency_ms = target_latency_ms
        self.adjustment_factor = adjustment_factor
        self.max_timeout_ms = max_timeout_ms
        self.min_timeout_ms = min_timeout_ms
        self.processor_ms = processor_ms

    def _adjust_timeout(
        self,
        current_timeout: int,
        p95_latency: float,
    ) -> int:
        """Adjust timeout based on observed p95 latency."""
        if p95_latency > self.target_latency_ms * 1.5:
            # Latency too high, increase timeout to allow more batching
            new_timeout = min(int(current_timeout * self.adjustment_factor), self.max_timeout_ms)
        elif p95_latency < self.target_latency_ms * 0.5:
            # Latency low, decrease timeout for responsiveness
            new_timeout = max(int(current_timeout / self.adjustment_factor), self.min_timeout_ms)
        else:
            new_timeout = current_timeout
        return new_timeout

    async def run(self, concurrency: int, total_requests: int, adjustment_interval: int = 100) -> AdaptiveBenchmarkResult:
        """Run adaptive benchmark with periodic timeout adjustments."""
        timeouts = [self.initial_timeout_ms]
        latencies_before: List[float] = []
        latencies_after: List[float] = []
        timeout_adjustments = []

        current_timeout = self.initial_timeout_ms
        requests_done = 0
        phase = "before"  # "before" or "after"

        async def processor(batch: List[Any]) -> List[Any]:
            await asyncio.sleep(self.processor_ms / 1000.0)
            return [{"result": f"item", "batch_size": len(batch)} for _ in batch]

        while requests_done < total_requests:
            batcher = DynamicBatcher(
                max_batch=self.max_batch,
                timeout_ms=current_timeout,
                processor=processor,
            )

            batch_latencies: List[float] = []

            async def worker(worker_id: int, count: int):
                nonlocal requests_done
                for i in range(count):
                    start = time.perf_counter()
                    await batcher.submit({"worker": worker_id, "seq": i})
                    latency = (time.perf_counter() - start) * 1000
                    batch_latencies.append(latency)
                    requests_done += 1

            # Run a batch of requests at current timeout
            batch_size = min(adjustment_interval, total_requests - requests_done)
            tasks = [asyncio.create_task(worker(w, max(1, batch_size // concurrency))) for w in range(concurrency)]
            await asyncio.gather(*tasks)

            if batch_latencies:
                p95 = _percentile(batch_latencies, 95)
                avg = statistics.mean(batch_latencies)

                if phase == "before":
                    latencies_before.extend(batch_latencies)
                else:
                    latencies_after.extend(batch_latencies)

                new_timeout = self._adjust_timeout(current_timeout, p95)
                if new_timeout != current_timeout:
                    timeout_adjustments.append({
                        "requests_done": requests_done,
                        "old_timeout_ms": current_timeout,
                        "new_timeout_ms": new_timeout,
                        "p95_latency_ms": round(p95, 2),
                        "avg_latency_ms": round(avg, 2),
                    })
                    current_timeout = new_timeout
                    timeouts.append(current_timeout)
                    phase = "after"

        # Calculate throughput
        duration_s = max(max(latencies_before) if latencies_before else 0, max(latencies_after) if latencies_after else 0) / 1000
        throughput_before = len(latencies_before) / duration_s if duration_s > 0 else 0
        throughput_after = len(latencies_after) / duration_s if duration_s > 0 else 0

        return AdaptiveBenchmarkResult(
            initial_timeout_ms=self.initial_timeout_ms,
            final_timeout_ms=current_timeout,
            concurrency=concurrency,
            total_requests=total_requests,
            max_batch=self.max_batch,
            latencies_before_ms=latencies_before,
            latencies_after_ms=latencies_after,
            throughput_before_rps=throughput_before,
            throughput_after_rps=throughput_after,
            timeout_adjustments=timeout_adjustments,
        )


async def run_standard_benchmarks() -> Dict[str, Any]:
    """Run standard benchmark suite and return results."""
    results = {}

    # Baseline benchmark
    bench = BatchingBenchmark(max_batch=16, timeout_ms=50, processor_ms=5.0)
    sweep_results = await bench.run_sweep([1, 2, 4, 8, 16, 32], total_requests=500)
    results["concurrency_sweep"] = [r.to_dict() for r in sweep_results]

    # High throughput benchmark
    bench_high = BatchingBenchmark(max_batch=32, timeout_ms=100, processor_ms=2.0)
    high_results = await bench_high.run_concurrency_benchmark(32, 1000)
    results["high_throughput"] = high_results.to_dict()

    # Low latency benchmark
    bench_low = BatchingBenchmark(max_batch=8, timeout_ms=10, processor_ms=1.0)
    low_results = await bench_low.run_concurrency_benchmark(8, 500)
    results["low_latency"] = low_results.to_dict()

    return results


async def run_adaptive_benchmarks() -> Dict[str, Any]:
    """Run adaptive timeout benchmark suite."""
    results = {}

    # Adaptive benchmark at moderate concurrency
    adaptive = AdaptiveTimeoutBenchmark(
        max_batch=16,
        initial_timeout_ms=50,
        processor_ms=5.0,
        target_latency_ms=80.0,
    )
    result = await adaptive.run(concurrency=16, total_requests=800, adjustment_interval=100)
    results["adaptive_moderate"] = result.to_dict()

    # Adaptive benchmark at high concurrency
    adaptive_high = AdaptiveTimeoutBenchmark(
        max_batch=32,
        initial_timeout_ms=100,
        processor_ms=3.0,
        target_latency_ms=100.0,
    )
    result_high = await adaptive_high.run(concurrency=32, total_requests=1000, adjustment_interval=150)
    results["adaptive_high"] = result_high.to_dict()

    return results


async def main():
    """Run all benchmarks and print results."""
    print("=== Standard Benchmarks ===")
    standard = await run_standard_benchmarks()
    for name, data in standard.items():
        print(f"\n{name}:")
        for k, v in data.items():
            if isinstance(v, list):
                print(f"  {k}: {len(v)} results")
                for i, item in enumerate(v):
                    print(f"    [{i}] concurrency={item['concurrency']}, "
                          f"throughput={item['throughput_rps']:.1f} rps, "
                          f"avg_lat={item['avg_latency_ms']:.1f}ms, "
                          f"p95={item['p95_latency_ms']:.1f}ms, "
                          f"avg_batch={item['avg_batch_size']:.1f}")
            else:
                print(f"  {k}: {v}")

    print("\n=== Adaptive Benchmarks ===")
    adaptive = await run_adaptive_benchmarks()
    for name, data in adaptive.items():
        print(f"\n{name}:")
        for k, v in data.items():
            if k == "timeout_adjustments":
                print(f"  {k}: {len(v)} adjustments")
                for adj in v:
                    print(f"    req={adj['requests_done']}, "
                          f"timeout={adj['old_timeout_ms']}->{adj['new_timeout_ms']}ms, "
                          f"p95={adj['p95_latency_ms']:.1f}ms")
            else:
                print(f"  {k}: {v}")

    return {"standard": standard, "adaptive": adaptive}


if __name__ == "__main__":
    asyncio.run(main())