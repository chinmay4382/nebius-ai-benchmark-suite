"""Throughput benchmark — measures requests/sec and tokens/sec."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Callable, Optional

from benchmark.endpoint.base import BaseEndpointBenchmark
from benchmark.models import BenchmarkConfig, RequestMetric

logger = logging.getLogger(__name__)


class ThroughputBenchmark(BaseEndpointBenchmark):
    """Runs N concurrent requests and measures sustained throughput."""

    async def _run_batch(
        self,
        client,
        batch_size: int,
        batch_num: int,
        on_metric: Optional[Callable[[RequestMetric], None]],
    ) -> list[RequestMetric]:
        tasks = [
            self._request_non_streaming(client, sequence_num=batch_num * batch_size + i)
            for i in range(batch_size)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        metrics: list[RequestMetric] = []
        for r in results:
            if isinstance(r, RequestMetric):
                metrics.append(r)
                if on_metric:
                    on_metric(r)
            elif isinstance(r, Exception):
                logger.warning("Request failed: %s", r)
        return metrics

    async def run(
        self, on_metric: Optional[Callable[[RequestMetric], None]] = None
    ) -> tuple[list[RequestMetric], float]:
        all_metrics: list[RequestMetric] = []
        concurrency = self.config.concurrency
        total = self.config.request_count
        num_batches = (total + concurrency - 1) // concurrency

        async with self._build_client() as client:
            start = time.perf_counter()
            for b in range(num_batches):
                remaining = total - len(all_metrics)
                batch_size = min(concurrency, remaining)
                batch = await self._run_batch(client, batch_size, b, on_metric)
                all_metrics.extend(batch)
                logger.debug(
                    "Throughput batch %d/%d done (%d total)",
                    b + 1, num_batches, len(all_metrics)
                )
            elapsed = time.perf_counter() - start

        return all_metrics, elapsed

    def run_sync(
        self, on_metric: Optional[Callable[[RequestMetric], None]] = None
    ) -> tuple[list[RequestMetric], float]:
        return asyncio.run(self.run(on_metric=on_metric))
