"""Real-time metrics collection during benchmark execution."""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Callable, Optional

from benchmark.models import LiveUpdate, RequestMetric


class MetricsCollector:
    """Thread-safe collector that accumulates RequestMetric objects during a run."""

    def __init__(self, total_requests: int, on_update: Optional[Callable[[LiveUpdate], None]] = None) -> None:
        self._lock = threading.Lock()
        self._metrics: list[RequestMetric] = []
        self._total_requests = total_requests
        self._on_update = on_update
        self._start_time = time.time()
        self._recent: deque[RequestMetric] = deque(maxlen=20)

    def record(self, metric: RequestMetric) -> None:
        with self._lock:
            self._metrics.append(metric)
            self._recent.append(metric)
            count = len(self._metrics)

        if self._on_update:
            update = LiveUpdate(
                timestamp=time.time(),
                request_num=count,
                total_requests=self._total_requests,
                latest_metric=metric,
                running_summary=self._build_running_summary(),
                message=f"Completed request {count}/{self._total_requests}",
            )
            self._on_update(update)

    def _build_running_summary(self) -> dict:
        with self._lock:
            metrics = list(self._metrics)

        if not metrics:
            return {}

        successful = [m for m in metrics if m.is_success]
        ttft_values = [m.ttft_ms for m in successful if m.ttft_ms is not None]
        latency_values = [m.total_latency_ms for m in successful]
        tps_values = [m.tokens_per_second for m in successful if m.tokens_per_second > 0]

        elapsed = time.time() - self._start_time
        rps = len(successful) / elapsed if elapsed > 0 else 0.0

        return {
            "total": len(metrics),
            "successful": len(successful),
            "failed": len(metrics) - len(successful),
            "error_rate": (len(metrics) - len(successful)) / len(metrics) if metrics else 0.0,
            "avg_ttft_ms": sum(ttft_values) / len(ttft_values) if ttft_values else None,
            "avg_latency_ms": sum(latency_values) / len(latency_values) if latency_values else None,
            "avg_tps": sum(tps_values) / len(tps_values) if tps_values else None,
            "throughput_rps": rps,
            "elapsed_seconds": elapsed,
        }

    def get_all(self) -> list[RequestMetric]:
        with self._lock:
            return list(self._metrics)

    def get_recent(self, n: int = 20) -> list[RequestMetric]:
        with self._lock:
            return list(self._recent)[-n:]

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._metrics)

    def reset(self) -> None:
        with self._lock:
            self._metrics.clear()
            self._recent.clear()
        self._start_time = time.time()
