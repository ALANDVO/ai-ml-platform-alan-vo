"""Tests for dynamic batching benchmarks."""
import pytest
import asyncio
import sys
sys.path.insert(0, "backend")
from app.inference.benchmarks import (
    BatchingBenchmark,
    AdaptiveTimeoutBenchmark,
    BenchmarkResult,
    AdaptiveBenchmarkResult,
    _percentile,
    run_standard_benchmarks,
    run_adaptive_benchmarks,
)


def test_percentile():
    assert _percentile([], 50) == 0
    assert _percentile([1, 2, 3, 4, 5], 50) == 3
    assert _percentile([1, 2, 3, 4], 50) == 2.5
    assert _percentile([10, 20, 30], 99) == pytest.approx(29.8)


@pytest.mark.asyncio
async def test_batching_benchmark_basic():
    bench = BatchingBenchmark(max_batch=4, timeout_ms=20, processor_ms=2.0)
    result = await bench.run_concurrency_benchmark(concurrency=2, total_requests=20)

    assert isinstance(result, BenchmarkResult)
    assert result.concurrency == 2
    assert result.total_requests == 20
    assert result.max_batch == 4
    assert result.timeout_ms == 20
    assert result.processor_ms == 2.0
    assert len(result.latencies_ms) == 20
    assert result.throughput_rps > 0
    assert result.avg_latency_ms > 0
    assert result.p50_latency_ms > 0
    assert result.p95_latency_ms >= result.p50_latency_ms
    assert result.p99_latency_ms >= result.p95_latency_ms
    assert result.avg_batch_size > 0
    assert result.max_queue_depth >= 0


@pytest.mark.asyncio
async def test_batching_benchmark_sweep():
    bench = BatchingBenchmark(max_batch=8, timeout_ms=30, processor_ms=1.0)
    results = await bench.run_sweep([1, 2, 4, 8], total_requests=100)

    assert len(results) == 4
    for i, r in enumerate(results):
        assert r.concurrency == [1, 2, 4, 8][i]
        assert r.total_requests == 100
        assert len(r.latencies_ms) == 100


@pytest.mark.asyncio
async def test_adaptive_timeout_benchmark():
    adaptive = AdaptiveTimeoutBenchmark(
        max_batch=16,
        initial_timeout_ms=50,
        processor_ms=5.0,
        target_latency_ms=100.0,
    )
    result = await adaptive.run(concurrency=8, total_requests=200, adjustment_interval=50)

    assert isinstance(result, AdaptiveBenchmarkResult)
    assert result.initial_timeout_ms == 50
    assert result.concurrency == 8
    assert result.total_requests == 200
    assert result.max_batch == 16
    assert len(result.latencies_before_ms) + len(result.latencies_after_ms) == 200
    assert result.throughput_before_rps >= 0
    assert result.throughput_after_rps >= 0


@pytest.mark.asyncio
async def test_adaptive_timeout_adjustment_increases():
    """Test that timeout increases when latency is high."""
    adaptive = AdaptiveTimeoutBenchmark(
        max_batch=16,
        initial_timeout_ms=10,
        processor_ms=100.0,
        target_latency_ms=30.0,
        adjustment_factor=1.5,
        max_timeout_ms=500,
    )
    result = await adaptive.run(concurrency=16, total_requests=400, adjustment_interval=50)

    assert result.final_timeout_ms > result.initial_timeout_ms
    assert len(result.timeout_adjustments) > 0


@pytest.mark.asyncio
async def test_adaptive_timeout_adjustment_decreases():
    """Test that timeout decreases when latency is low."""
    adaptive = AdaptiveTimeoutBenchmark(
        max_batch=16,
        initial_timeout_ms=20,
        processor_ms=1.0,
        target_latency_ms=100.0,
        adjustment_factor=1.5,
        min_timeout_ms=10,
    )
    result = await adaptive.run(concurrency=4, total_requests=200, adjustment_interval=50)

    assert result.final_timeout_ms < result.initial_timeout_ms
    assert len(result.timeout_adjustments) > 0


@pytest.mark.asyncio
async def test_benchmark_result_to_dict():
    bench = BatchingBenchmark(max_batch=4, timeout_ms=20, processor_ms=2.0)
    result = await bench.run_concurrency_benchmark(concurrency=2, total_requests=20)
    d = result.to_dict()

    assert d["concurrency"] == 2
    assert d["total_requests"] == 20
    assert d["max_batch"] == 4
    assert d["timeout_ms"] == 20
    assert d["processor_ms"] == 2.0
    assert "throughput_rps" in d
    assert "avg_latency_ms" in d
    assert "p50_latency_ms" in d
    assert "p95_latency_ms" in d
    assert "p99_latency_ms" in d
    assert "avg_batch_size" in d
    assert "max_queue_depth" in d
    assert "batch_size_distribution" in d


@pytest.mark.asyncio
async def test_adaptive_result_to_dict():
    adaptive = AdaptiveTimeoutBenchmark(
        max_batch=16,
        initial_timeout_ms=50,
        processor_ms=5.0,
        target_latency_ms=100.0,
    )
    result = await adaptive.run(concurrency=8, total_requests=200, adjustment_interval=50)
    d = result.to_dict()

    assert d["initial_timeout_ms"] == 50
    assert d["concurrency"] == 8
    assert d["total_requests"] == 200
    assert d["max_batch"] == 16
    assert "throughput_before_rps" in d
    assert "throughput_after_rps" in d
    assert "avg_latency_before_ms" in d
    assert "avg_latency_after_ms" in d
    assert "p95_latency_before_ms" in d
    assert "p95_latency_after_ms" in d
    assert "timeout_adjustments" in d


@pytest.mark.asyncio
async def test_standard_benchmarks_run():
    """Integration test that benchmark suite runs without error (minimal workload)."""
    # Use minimal workload for fast test
    bench = BatchingBenchmark(max_batch=8, timeout_ms=20, processor_ms=1.0)
    sweep_results = await bench.run_sweep([1, 2, 4], total_requests=50)
    results = {"concurrency_sweep": [r.to_dict() for r in sweep_results]}
    
    bench_high = BatchingBenchmark(max_batch=16, timeout_ms=50, processor_ms=1.0)
    high_results = await bench_high.run_concurrency_benchmark(8, 50)
    results["high_throughput"] = high_results.to_dict()
    
    bench_low = BatchingBenchmark(max_batch=4, timeout_ms=10, processor_ms=1.0)
    low_results = await bench_low.run_concurrency_benchmark(4, 50)
    results["low_latency"] = low_results.to_dict()
    
    assert "concurrency_sweep" in results
    assert "high_throughput" in results
    assert "low_latency" in results
    assert len(results["concurrency_sweep"]) == 3


@pytest.mark.asyncio
async def test_adaptive_benchmarks_run():
    """Integration test that adaptive benchmark suite runs without error."""
    results = await run_adaptive_benchmarks()
    assert "adaptive_moderate" in results
    assert "adaptive_high" in results


@pytest.mark.asyncio
async def test_batch_size_distribution():
    bench = BatchingBenchmark(max_batch=4, timeout_ms=50, processor_ms=1.0)
    result = await bench.run_concurrency_benchmark(concurrency=4, total_requests=100)

    dist = result.to_dict()["batch_size_distribution"]
    assert isinstance(dist, dict)
    for size, count in dist.items():
        assert size <= 4
        assert count > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
