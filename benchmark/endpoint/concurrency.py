"""Concurrency sweep benchmark — tests multiple concurrency levels."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Callable, Optional

from benchmark.endpoint.base import BaseEndpointBenchmark
from benchmark.metrics.analyzer import MetricsAnalyzer
from benchmark.models import BenchmarkConfig, ConcurrencyResult, RequestMetric

logger = logging.getLogger(__name__)

DEFAULT_LEVELS = [1, 5, 10, 25, 50, 100]


class ConcurrencyBenchmark(BaseEndpointBenchmark):
    """Sweeps through concurrency levels and collects performance curves."""

    def __init__(
        self,
        config: BenchmarkConfig,
        levels: Optional[list[int]] = None,
        requests_per_level: int = 50,
    ) -> None:
        super().__init__(config)
        self.levels = levels or DEFAULT_LEVELS
        self.requests_per_level = requests_per_level

    async def _run_level(
        self,
        client,
        level: int,
        on_metric: Optional[Callable[[RequestMetric, int], None]],
    ) -> ConcurrencyResult:
        num_batches = (self.requests_per_level + level - 1) // level
        all_metrics: list[RequestMetric] = []

        start = time.perf_counter()
        for b in range(num_batches):
            remaining = self.requests_per_level - len(all_metrics)
            batch_size = min(level, remaining)
            tasks = [
                self._request_non_streaming(client, sequence_num=len(all_metrics) + i, concurrency=level)
                for i in range(batch_size)
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in results:
                if isinstance(r, RequestMetric):
                    all_metrics.append(r)
                    if on_metric:
                        on_metric(r, level)
        elapsed = time.perf_counter() - start

        summary = MetricsAnalyzer.analyze_endpoint(all_metrics, elapsed, concurrency_level=level)
        logger.info(
            "Concurrency=%d → RPS=%.2f TTFT_p50=%.1f error=%.1f%%",
            level, summary.throughput_rps, summary.ttft.p50, summary.error_rate * 100,
        )
        return ConcurrencyResult(concurrency_level=level, summary=summary)

    async def run(
        self,
        on_level_complete: Optional[Callable[[ConcurrencyResult], None]] = None,
        on_metric: Optional[Callable[[RequestMetric, int], None]] = None,
    ) -> list[ConcurrencyResult]:
        results: list[ConcurrencyResult] = []
        async with self._build_client() as client:
            for level in self.levels:
                result = await self._run_level(client, level, on_metric)
                results.append(result)
                if on_level_complete:
                    on_level_complete(result)
        return results

    def run_sync(
        self,
        on_level_complete: Optional[Callable[[ConcurrencyResult], None]] = None,
        on_metric: Optional[Callable[[RequestMetric, int], None]] = None,
    ) -> list[ConcurrencyResult]:
        return asyncio.run(self.run(on_level_complete=on_level_complete, on_metric=on_metric))
