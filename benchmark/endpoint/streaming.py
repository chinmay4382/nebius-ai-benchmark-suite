"""Streaming benchmark — measures TTFT and inter-token latency via SSE."""

from __future__ import annotations

import asyncio
import logging
from typing import Callable, Optional

from benchmark.endpoint.base import BaseEndpointBenchmark
from benchmark.models import BenchmarkConfig, RequestMetric

logger = logging.getLogger(__name__)


class StreamingBenchmark(BaseEndpointBenchmark):
    """Dedicated streaming benchmark for accurate ITL measurement."""

    def __init__(self, config: BenchmarkConfig) -> None:
        super().__init__(config)
        self.config = BenchmarkConfig(**{**config.model_dump(), "streaming": True})

    async def run(
        self, on_metric: Optional[Callable[[RequestMetric], None]] = None
    ) -> list[RequestMetric]:
        results: list[RequestMetric] = []

        semaphore = asyncio.Semaphore(self.config.concurrency)

        async def bounded_request(seq: int) -> RequestMetric:
            async with semaphore:
                async with self._build_client() as client:
                    return await self._request_streaming(client, sequence_num=seq)

        tasks = [bounded_request(i) for i in range(self.config.request_count)]
        for coro in asyncio.as_completed(tasks):
            metric = await coro
            results.append(metric)
            if on_metric:
                on_metric(metric)
            logger.debug(
                "Stream[%d] ttft=%.1fms itl=%.1fms tokens=%d",
                len(results),
                metric.ttft_ms or 0,
                metric.inter_token_latency_ms or 0,
                metric.completion_tokens,
            )

        return results

    def run_sync(
        self, on_metric: Optional[Callable[[RequestMetric], None]] = None
    ) -> list[RequestMetric]:
        return asyncio.run(self.run(on_metric=on_metric))
