"""Statistical analysis of raw benchmark metrics."""

from __future__ import annotations

import math
from typing import Optional

import numpy as np

from benchmark.models import (
    ConcurrencyResult,
    EndpointBenchmarkSummary,
    JobBenchmarkSummary,
    JobMetric,
    PercentileStats,
    RequestMetric,
)


def _percentile_stats(values: list[float]) -> PercentileStats:
    if not values:
        return PercentileStats()
    arr = np.array(values, dtype=float)
    return PercentileStats(
        p50=float(np.percentile(arr, 50)),
        p90=float(np.percentile(arr, 90)),
        p95=float(np.percentile(arr, 95)),
        p99=float(np.percentile(arr, 99)),
        mean=float(np.mean(arr)),
        min=float(np.min(arr)),
        max=float(np.max(arr)),
        std=float(np.std(arr)),
    )


class MetricsAnalyzer:
    """Converts raw RequestMetric lists into structured summaries."""

    @staticmethod
    def analyze_endpoint(
        metrics: list[RequestMetric],
        duration_seconds: float,
        concurrency_level: int = 1,
        cold_start_ms: Optional[float] = None,
        warm_start_ms: Optional[float] = None,
    ) -> EndpointBenchmarkSummary:
        total = len(metrics)
        if total == 0:
            return EndpointBenchmarkSummary()

        successful = [m for m in metrics if m.is_success]
        failed = [m for m in metrics if not m.is_success]

        ttft_vals = [m.ttft_ms for m in successful if m.ttft_ms is not None]
        itl_vals = [m.inter_token_latency_ms for m in successful if m.inter_token_latency_ms is not None]
        latency_vals = [m.total_latency_ms for m in successful]
        tps_vals = [m.tokens_per_second for m in successful if m.tokens_per_second > 0]

        total_prompt = sum(m.prompt_tokens for m in successful)
        total_completion = sum(m.completion_tokens for m in successful)
        total_tokens = total_prompt + total_completion

        throughput_rps = len(successful) / duration_seconds if duration_seconds > 0 else 0.0
        avg_tps = total_completion / duration_seconds if duration_seconds > 0 else 0.0

        return EndpointBenchmarkSummary(
            total_requests=total,
            successful_requests=len(successful),
            failed_requests=len(failed),
            error_rate=len(failed) / total,
            success_rate=len(successful) / total,
            ttft=_percentile_stats(ttft_vals),
            latency=_percentile_stats(latency_vals),
            inter_token_latency=_percentile_stats(itl_vals),
            throughput_rps=throughput_rps,
            tokens_per_second=avg_tps,
            prompt_tokens_total=total_prompt,
            completion_tokens_total=total_completion,
            total_tokens_total=total_tokens,
            duration_seconds=duration_seconds,
            concurrency_level=concurrency_level,
            cold_start_ms=cold_start_ms,
            warm_start_ms=warm_start_ms,
            raw_metrics=metrics,
        )

    @staticmethod
    def analyze_concurrency_sweep(
        results: list[ConcurrencyResult],
    ) -> dict[str, list]:
        """Flatten concurrency sweep into plottable series."""
        levels = [r.concurrency_level for r in results]
        ttft_p50 = [r.summary.ttft.p50 for r in results]
        ttft_p95 = [r.summary.ttft.p95 for r in results]
        throughput = [r.summary.throughput_rps for r in results]
        tps = [r.summary.tokens_per_second for r in results]
        error_rate = [r.summary.error_rate * 100 for r in results]
        latency_p50 = [r.summary.latency.p50 for r in results]
        latency_p99 = [r.summary.latency.p99 for r in results]

        return {
            "concurrency": levels,
            "ttft_p50_ms": ttft_p50,
            "ttft_p95_ms": ttft_p95,
            "throughput_rps": throughput,
            "tokens_per_second": tps,
            "error_rate_pct": error_rate,
            "latency_p50_ms": latency_p50,
            "latency_p99_ms": latency_p99,
        }

    @staticmethod
    def analyze_jobs(
        metrics: list[JobMetric],
    ) -> JobBenchmarkSummary:
        total = len(metrics)
        if total == 0:
            return JobBenchmarkSummary()

        successful = [m for m in metrics if m.status == "completed"]
        failed = [m for m in metrics if m.status != "completed"]

        return JobBenchmarkSummary(
            total_jobs=total,
            successful_jobs=len(successful),
            failed_jobs=len(failed),
            creation_time=_percentile_stats([m.creation_time_ms for m in successful]),
            queue_delay=_percentile_stats([m.queue_delay_ms for m in successful]),
            startup_time=_percentile_stats([m.startup_time_ms for m in successful]),
            execution_time=_percentile_stats([m.execution_time_ms for m in successful]),
            total_time=_percentile_stats([m.total_time_ms for m in successful]),
            raw_metrics=metrics,
        )

    @staticmethod
    def compute_percentile_timeline(
        metrics: list[RequestMetric],
        window: int = 20,
    ) -> dict[str, list]:
        """Rolling percentile timeline for live chart display."""
        if not metrics:
            return {"idx": [], "p50": [], "p90": [], "p99": []}

        successful = [m for m in metrics if m.is_success and m.ttft_ms is not None]
        idxs, p50s, p90s, p99s = [], [], [], []

        for i in range(1, len(successful) + 1):
            window_slice = [m.ttft_ms for m in successful[max(0, i - window): i]]  # type: ignore[misc]
            arr = np.array(window_slice, dtype=float)
            idxs.append(i)
            p50s.append(float(np.percentile(arr, 50)))
            p90s.append(float(np.percentile(arr, 90)))
            p99s.append(float(np.percentile(arr, 99)))

        return {"idx": idxs, "p50": p50s, "p90": p90s, "p99": p99s}
