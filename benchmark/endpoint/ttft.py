"""Time-To-First-Token benchmark."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Callable, Optional

import httpx

from benchmark.endpoint.base import BaseEndpointBenchmark
from benchmark.models import BenchmarkConfig, RequestMetric

logger = logging.getLogger(__name__)


class TTFTBenchmark(BaseEndpointBenchmark):
    """Measures TTFT using streaming requests for accurate first-token timing."""

    def __init__(self, config: BenchmarkConfig) -> None:
        super().__init__(config)
        self.config = BenchmarkConfig(**{**config.model_dump(), "streaming": True})

    async def run(
        self,
        on_metric: Optional[Callable[[RequestMetric], None]] = None,
    ) -> list[RequestMetric]:
        results: list[RequestMetric] = []

        async with self._build_client() as client:
            for i in range(self.config.request_count):
                metric = await self._request_streaming(client, sequence_num=i)
                results.append(metric)
                if on_metric:
                    on_metric(metric)
                logger.debug(
                    "TTFT[%d/%d] ttft=%.1fms latency=%.1fms",
                    i + 1,
                    self.config.request_count,
                    metric.ttft_ms or 0,
                    metric.total_latency_ms,
                )

        return results

    def run_sync(
        self, on_metric: Optional[Callable[[RequestMetric], None]] = None
    ) -> list[RequestMetric]:
        return asyncio.run(self.run(on_metric=on_metric))
