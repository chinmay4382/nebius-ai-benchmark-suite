"""Main benchmark runner — orchestrates all benchmark types."""

from __future__ import annotations

import logging
import os
import time
import uuid
from datetime import datetime
from typing import Callable, Iterator, Optional

import yaml

from benchmark.endpoint.cold_start import ColdStartBenchmark
from benchmark.endpoint.concurrency import ConcurrencyBenchmark
from benchmark.endpoint.streaming import StreamingBenchmark
from benchmark.endpoint.throughput import ThroughputBenchmark
from benchmark.endpoint.ttft import TTFTBenchmark
from benchmark.endpoint.warm_start import WarmStartBenchmark
from benchmark.jobs.completion import JobCompletionBenchmark
from benchmark.metrics.analyzer import MetricsAnalyzer
from benchmark.metrics.reporter import MetricsReporter
from benchmark.models import (
    BenchmarkConfig,
    BenchmarkReport,
    BenchmarkRun,
    BenchmarkStatus,
    BenchmarkType,
    ConcurrencyResult,
    CostEstimate,
    JobBenchmarkConfig,
    LiveUpdate,
    ModelPricing,
    PromptDataset,
    ReportFormat,
    RequestMetric,
)
from benchmark.storage.database import get_session_factory, init_db
from benchmark.storage.repository import BenchmarkRepository

logger = logging.getLogger(__name__)


def _load_model_pricing() -> dict[str, ModelPricing]:
    """Load pricing data from config/models.yaml."""
    pricing: dict[str, ModelPricing] = {}
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "models.yaml")
    try:
        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        for m in data.get("models", []):
            p = m.get("pricing", {})
            pricing[m["id"]] = ModelPricing(
                model_id=m["id"],
                display_name=m["display_name"],
                input_per_1m_tokens=p.get("input_per_1m_tokens", 0.0),
                output_per_1m_tokens=p.get("output_per_1m_tokens", 0.0),
            )
    except Exception as exc:
        logger.warning("Could not load model pricing: %s", exc)
    return pricing


_MODEL_PRICING: dict[str, ModelPricing] = {}


def get_model_pricing() -> dict[str, ModelPricing]:
    global _MODEL_PRICING
    if not _MODEL_PRICING:
        _MODEL_PRICING = _load_model_pricing()
    return _MODEL_PRICING


def estimate_cost(
    model_id: str,
    prompt_tokens: int,
    completion_tokens: int,
    request_count: int,
    daily_requests: int = 10_000,
) -> CostEstimate:
    pricing = get_model_pricing().get(model_id)
    if pricing is None:
        pricing = ModelPricing(
            model_id=model_id,
            display_name=model_id,
            input_per_1m_tokens=1.0,
            output_per_1m_tokens=1.0,
        )

    input_cost = (prompt_tokens / 1_000_000) * pricing.input_per_1m_tokens
    output_cost = (completion_tokens / 1_000_000) * pricing.output_per_1m_tokens
    total_cost = input_cost + output_cost
    cost_per_request = total_cost / request_count if request_count > 0 else 0.0
    total_tokens = prompt_tokens + completion_tokens
    cpm = (total_cost / total_tokens * 1_000_000) if total_tokens > 0 else 0.0

    avg_prompt = prompt_tokens / request_count if request_count > 0 else 0
    avg_completion = completion_tokens / request_count if request_count > 0 else 0
    monthly_cost = (
        daily_requests
        * 30
        * ((avg_prompt / 1_000_000) * pricing.input_per_1m_tokens
           + (avg_completion / 1_000_000) * pricing.output_per_1m_tokens)
    )

    projections = {
        "1k_req_day": cost_per_request * 1_000 * 30,
        "10k_req_day": cost_per_request * 10_000 * 30,
        "100k_req_day": cost_per_request * 100_000 * 30,
        "1m_req_day": cost_per_request * 1_000_000 * 30,
    }

    return CostEstimate(
        model_id=model_id,
        total_input_tokens=prompt_tokens,
        total_output_tokens=completion_tokens,
        input_cost_usd=input_cost,
        output_cost_usd=output_cost,
        total_cost_usd=total_cost,
        cost_per_request_usd=cost_per_request,
        cost_per_1m_tokens_usd=cpm,
        projected_monthly_cost_usd=monthly_cost,
        projected_monthly_cost_at_rps=projections,
    )


class BenchmarkRunner:
    """
    High-level orchestrator that runs benchmark suites, persists results,
    and emits live updates to the UI.
    """

    def __init__(self, persist: bool = True) -> None:
        self._persist = persist
        self._reporter = MetricsReporter()
        if persist:
            init_db()

    def run_endpoint_benchmark(
        self,
        config: BenchmarkConfig,
        run_name: str = "",
        concurrency_levels: Optional[list[int]] = None,
        include_cold_start: bool = True,
        include_sweep: bool = True,
        on_update: Optional[Callable[[LiveUpdate], None]] = None,
        tags: Optional[list[str]] = None,
    ) -> BenchmarkRun:
        run_id = str(uuid.uuid4())
        name = run_name or f"Endpoint {config.model} @ {datetime.utcnow().strftime('%H:%M')}"

        run = BenchmarkRun(
            id=run_id,
            name=name,
            benchmark_type=BenchmarkType.ENDPOINT,
            config=config,
            status=BenchmarkStatus.RUNNING,
            started_at=datetime.utcnow(),
            tags=tags or [],
        )

        if self._persist:
            self._persist_run_start(run)

        try:
            run = self._execute_endpoint(
                run=run,
                config=config,
                concurrency_levels=concurrency_levels,
                include_cold_start=include_cold_start,
                include_sweep=include_sweep,
                on_update=on_update,
            )
            run.status = BenchmarkStatus.COMPLETED
        except Exception as exc:
            logger.exception("Benchmark failed: %s", exc)
            run.status = BenchmarkStatus.FAILED
            run.error_message = str(exc)

        run.completed_at = datetime.utcnow()

        if self._persist:
            self._persist_run_end(run)

        return run

    def _execute_endpoint(
        self,
        run: BenchmarkRun,
        config: BenchmarkConfig,
        concurrency_levels: Optional[list[int]],
        include_cold_start: bool,
        include_sweep: bool,
        on_update: Optional[Callable[[LiveUpdate], None]],
    ) -> BenchmarkRun:

        cold_start_ms: Optional[float] = None
        warm_start_ms: Optional[float] = None

        # ── Cold/Warm start probes ────────────────────────────────────────────
        if include_cold_start:
            if on_update:
                on_update(LiveUpdate(
                    timestamp=time.time(), request_num=0,
                    total_requests=config.request_count,
                    message="Measuring cold-start latency...",
                ))
            cold_bm = ColdStartBenchmark(config)
            cold_start_ms, _ = cold_bm.run_sync()

            warm_bm = WarmStartBenchmark(config)
            warm_start_ms, _ = warm_bm.run_sync()
            logger.info("Cold=%.1f ms, Warm=%.1f ms", cold_start_ms or 0, warm_start_ms or 0)

        # ── Main throughput/TTFT run ──────────────────────────────────────────
        if on_update:
            on_update(LiveUpdate(
                timestamp=time.time(), request_num=0,
                total_requests=config.request_count,
                message=f"Running main benchmark ({config.request_count} requests @ concurrency={config.concurrency})...",
            ))

        completed: list[RequestMetric] = []
        counter = [0]

        def _on_metric(m: RequestMetric) -> None:
            completed.append(m)
            counter[0] += 1
            if on_update and counter[0] % max(1, config.request_count // 20) == 0:
                on_update(LiveUpdate(
                    timestamp=time.time(),
                    request_num=counter[0],
                    total_requests=config.request_count,
                    latest_metric=m,
                    message=f"Request {counter[0]}/{config.request_count}",
                ))

        use_streaming = config.streaming
        if use_streaming:
            bench = StreamingBenchmark(config)
            raw_metrics = bench.run_sync(on_metric=_on_metric)
        else:
            bench_t = ThroughputBenchmark(config)
            raw_metrics, elapsed = bench_t.run_sync(on_metric=_on_metric)

        elapsed_total = sum(m.total_latency_ms for m in raw_metrics if m.is_success) / 1000
        elapsed_wall = (raw_metrics[-1].end_time - raw_metrics[0].start_time) if raw_metrics else 1.0

        summary = MetricsAnalyzer.analyze_endpoint(
            raw_metrics,
            duration_seconds=max(elapsed_wall, 0.1),
            concurrency_level=config.concurrency,
            cold_start_ms=cold_start_ms,
            warm_start_ms=warm_start_ms,
        )
        run.endpoint_summary = summary

        # ── Cost estimate ─────────────────────────────────────────────────────
        run.cost_estimate = estimate_cost(
            model_id=config.model,
            prompt_tokens=summary.prompt_tokens_total,
            completion_tokens=summary.completion_tokens_total,
            request_count=summary.total_requests,
        )

        # ── Concurrency sweep ─────────────────────────────────────────────────
        if include_sweep:
            levels = concurrency_levels or [1, 5, 10, 25, 50]
            if on_update:
                on_update(LiveUpdate(
                    timestamp=time.time(), request_num=config.request_count,
                    total_requests=config.request_count,
                    message=f"Running concurrency sweep over {levels}...",
                ))

            sweep_bm = ConcurrencyBenchmark(
                config=config,
                levels=levels,
                requests_per_level=min(50, config.request_count),
            )

            concurrency_results: list[ConcurrencyResult] = []

            def _on_level(result: ConcurrencyResult) -> None:
                concurrency_results.append(result)
                if on_update:
                    on_update(LiveUpdate(
                        timestamp=time.time(),
                        request_num=config.request_count,
                        total_requests=config.request_count,
                        message=f"Concurrency {result.concurrency_level}: "
                                f"RPS={result.summary.throughput_rps:.2f}",
                    ))

            sweep_bm.run_sync(on_level_complete=_on_level)
            run.concurrency_results = concurrency_results

        return run

    def run_job_benchmark(
        self,
        config: JobBenchmarkConfig,
        run_name: str = "",
        tags: Optional[list[str]] = None,
    ) -> BenchmarkRun:
        run_id = str(uuid.uuid4())
        name = run_name or f"Jobs benchmark @ {datetime.utcnow().strftime('%H:%M')}"

        run = BenchmarkRun(
            id=run_id,
            name=name,
            benchmark_type=BenchmarkType.JOBS,
            config=config,
            status=BenchmarkStatus.RUNNING,
            started_at=datetime.utcnow(),
            tags=tags or [],
        )

        if self._persist:
            self._persist_run_start(run)

        try:
            bm = JobCompletionBenchmark(config)
            job_metrics = bm.run_sync()
            run.job_summary = MetricsAnalyzer.analyze_jobs(job_metrics)
            run.status = BenchmarkStatus.COMPLETED
        except Exception as exc:
            logger.exception("Job benchmark failed: %s", exc)
            run.status = BenchmarkStatus.FAILED
            run.error_message = str(exc)

        run.completed_at = datetime.utcnow()

        if self._persist:
            self._persist_run_end(run)

        return run

    def generate_reports(
        self, run: BenchmarkRun, formats: Optional[list[ReportFormat]] = None
    ) -> list[BenchmarkReport]:
        formats = formats or [ReportFormat.MARKDOWN, ReportFormat.JSON, ReportFormat.HTML]
        reports: list[BenchmarkReport] = []
        for fmt in formats:
            if fmt == ReportFormat.MARKDOWN:
                reports.append(self._reporter.generate_markdown(run))
            elif fmt == ReportFormat.JSON:
                reports.append(self._reporter.generate_json(run))
            elif fmt == ReportFormat.HTML:
                reports.append(self._reporter.generate_html(run))
        return reports

    # ── Persistence helpers ───────────────────────────────────────────────────

    def _persist_run_start(self, run: BenchmarkRun) -> None:
        try:
            factory = get_session_factory()
            with factory() as db:
                repo = BenchmarkRepository(db)
                repo.create_run(run)
                db.commit()
        except Exception as exc:
            logger.warning("Failed to persist run start: %s", exc)

    def _persist_run_end(self, run: BenchmarkRun) -> None:
        try:
            factory = get_session_factory()
            with factory() as db:
                repo = BenchmarkRepository(db)
                repo.update_run_status(run.id, run.status, run.error_message)

                if run.endpoint_summary:
                    s = run.endpoint_summary
                    metrics_dict = {
                        "ttft": s.ttft.model_dump(),
                        "latency": s.latency.model_dump(),
                        "inter_token_latency": s.inter_token_latency.model_dump(),
                        "throughput_rps": s.throughput_rps,
                        "tokens_per_second": s.tokens_per_second,
                        "error_rate": s.error_rate,
                        "success_rate": s.success_rate,
                        "total_requests": s.total_requests,
                        "successful_requests": s.successful_requests,
                        "failed_requests": s.failed_requests,
                        "total_tokens": s.total_tokens_total,
                        "duration_seconds": s.duration_seconds,
                        "cold_start_ms": s.cold_start_ms,
                        "warm_start_ms": s.warm_start_ms,
                    }
                    raw = [m.model_dump(exclude={"request_id"}) for m in s.raw_metrics[:1000]]
                    repo.save_result(
                        run_id=run.id,
                        result_type="endpoint",
                        metrics=metrics_dict,
                        raw_data=raw,
                        concurrency_level=s.concurrency_level,
                    )

                if run.concurrency_results:
                    for cr in run.concurrency_results:
                        cs = cr.summary
                        repo.save_result(
                            run_id=run.id,
                            result_type="concurrency",
                            metrics={
                                "ttft": cs.ttft.model_dump(),
                                "throughput_rps": cs.throughput_rps,
                                "tokens_per_second": cs.tokens_per_second,
                                "error_rate": cs.error_rate,
                            },
                            raw_data=[],
                            concurrency_level=cr.concurrency_level,
                        )

                db.commit()
        except Exception as exc:
            logger.warning("Failed to persist run end: %s", exc)


def main() -> None:
    """CLI entry point for running benchmarks."""
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

    parser = argparse.ArgumentParser(description="NebiusBench CLI")
    parser.add_argument("--endpoint", required=True, help="API endpoint URL")
    parser.add_argument("--api-key", default=os.getenv("NEBIUS_API_KEY", ""), help="API key")
    parser.add_argument("--model", default="meta-llama/Meta-Llama-3.1-8B-Instruct-fast")
    parser.add_argument("--requests", type=int, default=50)
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--streaming", action="store_true")
    parser.add_argument("--no-sweep", action="store_true")
    parser.add_argument("--no-cold-start", action="store_true")
    parser.add_argument("--name", default="")
    args = parser.parse_args()

    config = BenchmarkConfig(
        endpoint_url=args.endpoint,
        api_key=args.api_key,
        model=args.model,
        request_count=args.requests,
        concurrency=args.concurrency,
        streaming=args.streaming,
    )

    runner = BenchmarkRunner(persist=True)
    run = runner.run_endpoint_benchmark(
        config=config,
        run_name=args.name,
        include_cold_start=not args.no_cold_start,
        include_sweep=not args.no_sweep,
        on_update=lambda u: print(f"  {u.message}"),
    )

    print(f"\n{'='*60}")
    print(f"Run: {run.name} | Status: {run.status.value}")
    if run.endpoint_summary:
        s = run.endpoint_summary
        print(f"TTFT p50: {s.ttft.p50:.1f}ms | p99: {s.ttft.p99:.1f}ms")
        print(f"Throughput: {s.throughput_rps:.2f} req/s | {s.tokens_per_second:.1f} tok/s")
        print(f"Error rate: {s.error_rate*100:.1f}%")
    if run.cost_estimate:
        c = run.cost_estimate
        print(f"Cost: ${c.total_cost_usd:.6f} | /1M tok: ${c.cost_per_1m_tokens_usd:.4f}")

    reports = runner.generate_reports(run)
    for r in reports:
        print(f"Report ({r.format.value}): {r.file_path}")
