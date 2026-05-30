"""Warm-start latency benchmark."""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from benchmark.endpoint.base import BaseEndpointBenchmark
from benchmark.models import BenchmarkConfig, RequestMetric

logger = logging.getLogger(__name__)


class WarmStartBenchmark(BaseEndpointBenchmark):
    """
    Measures subsequent request latency after the endpoint is warm.
    Runs a short warm-up burst, then measures steady-state latency.
    """

    def __init__(self, config: BenchmarkConfig, warmup_count: int = 3, measurement_count: int = 20) -> None:
        super().__init__(config)
        self.warmup_count = warmup_count
        self.measurement_count = measurement_count

    async def run(self) -> tuple[Optional[float], list[RequestMetric]]:
        """Returns (warm_start_p50_ms, list_of_measurement_metrics)."""
        async with self._build_client() as client:
            logger.info("Running %d warm-up requests...", self.warmup_count)
            for i in range(self.warmup_count):
                await self._request_non_streaming(client, sequence_num=i)

            logger.info("Measuring warm-start latency over %d requests...", self.measurement_count)
            metrics: list[RequestMetric] = []
            for i in range(self.measurement_count):
                metric = await self._request_streaming(client, sequence_num=i)
                metrics.append(metric)

        successful = [m for m in metrics if m.is_success]
        if not successful:
            return None, metrics

        latencies = sorted(m.total_latency_ms for m in successful)
        p50 = latencies[len(latencies) // 2]
        return p50, metrics

    def run_sync(self) -> tuple[Optional[float], list[RequestMetric]]:
        return asyncio.run(self.run())
