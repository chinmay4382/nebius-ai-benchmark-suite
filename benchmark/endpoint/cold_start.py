"""Cold-start latency benchmark."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional

from benchmark.endpoint.base import BaseEndpointBenchmark
from benchmark.models import BenchmarkConfig, RequestMetric

logger = logging.getLogger(__name__)


class ColdStartBenchmark(BaseEndpointBenchmark):
    """
    Measures first-request latency after a period of endpoint inactivity.
    Because cold starts are controlled by the cloud infrastructure, this
    benchmark records the latency of the very first request to an endpoint
    that has not been exercised recently.
    """

    def __init__(self, config: BenchmarkConfig, measurement_requests: int = 5) -> None:
        super().__init__(config)
        self.measurement_requests = measurement_requests

    async def run(self) -> tuple[Optional[float], list[RequestMetric]]:
        """
        Returns (cold_start_ms, list_of_metrics).
        The first request latency is treated as the cold-start measurement.
        """
        metrics: list[RequestMetric] = []
        async with self._build_client() as client:
            for i in range(self.measurement_requests):
                metric = await self._request_streaming(client, sequence_num=i)
                metrics.append(metric)
                logger.info(
                    "Cold-start probe %d: %.1f ms (success=%s)",
                    i + 1, metric.total_latency_ms, metric.is_success
                )
                if i < self.measurement_requests - 1:
                    await asyncio.sleep(0.5)

        cold_start = metrics[0].total_latency_ms if metrics and metrics[0].is_success else None
        return cold_start, metrics

    def run_sync(self) -> tuple[Optional[float], list[RequestMetric]]:
        return asyncio.run(self.run())
