"""Generate Markdown, JSON, and HTML reports from benchmark summaries."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from benchmark.models import (
    BenchmarkReport,
    BenchmarkRun,
    BenchmarkType,
    CostEstimate,
    EndpointBenchmarkSummary,
    ReportFormat,
)


class MetricsReporter:
    def __init__(self, reports_dir: str = "reports") -> None:
        self._reports_dir = Path(reports_dir)
        self._reports_dir.mkdir(parents=True, exist_ok=True)
        (self._reports_dir / "markdown").mkdir(exist_ok=True)
        (self._reports_dir / "json").mkdir(exist_ok=True)
        (self._reports_dir / "html").mkdir(exist_ok=True)

    # ── Markdown ──────────────────────────────────────────────────────────────

    def generate_markdown(self, run: BenchmarkRun) -> BenchmarkReport:
        lines: list[str] = []
        ts = run.created_at.strftime("%Y-%m-%d %H:%M UTC")
        lines += [
            f"# NebiusBench Report: {run.name}",
            f"> Generated: {ts} | Status: **{run.status.value.upper()}**",
            "",
        ]

        if run.benchmark_type == BenchmarkType.ENDPOINT and run.endpoint_summary:
            s = run.endpoint_summary
            cfg = run.config  # type: ignore[union-attr]
            lines += [
                "## Configuration",
                f"| Key | Value |",
                f"|-----|-------|",
                f"| Model | `{getattr(cfg, 'model', 'N/A')}` |",
                f"| Endpoint | `{getattr(cfg, 'endpoint_url', 'N/A')}` |",
                f"| Concurrency | {getattr(cfg, 'concurrency', 'N/A')} |",
                f"| Requests | {getattr(cfg, 'request_count', 'N/A')} |",
                f"| Streaming | {getattr(cfg, 'streaming', False)} |",
                "",
                "## Summary",
                f"| Metric | Value |",
                f"|--------|-------|",
                f"| Total Requests | {s.total_requests} |",
                f"| Successful | {s.successful_requests} ({s.success_rate*100:.1f}%) |",
                f"| Failed | {s.failed_requests} ({s.error_rate*100:.1f}%) |",
                f"| Duration | {s.duration_seconds:.1f}s |",
                "",
                "## Latency (ms)",
                "| Metric | p50 | p90 | p95 | p99 | Mean |",
                "|--------|-----|-----|-----|-----|------|",
                f"| TTFT | {s.ttft.p50:.1f} | {s.ttft.p90:.1f} | {s.ttft.p95:.1f} | {s.ttft.p99:.1f} | {s.ttft.mean:.1f} |",
                f"| End-to-End | {s.latency.p50:.1f} | {s.latency.p90:.1f} | {s.latency.p95:.1f} | {s.latency.p99:.1f} | {s.latency.mean:.1f} |",
                "",
                "## Throughput",
                f"| Metric | Value |",
                f"|--------|-------|",
                f"| Requests/sec | {s.throughput_rps:.2f} |",
                f"| Tokens/sec | {s.tokens_per_second:.1f} |",
                f"| Total Tokens | {s.total_tokens_total:,} |",
                "",
            ]

            if s.cold_start_ms is not None:
                lines += [
                    "## Cold/Warm Start",
                    f"| Metric | Value |",
                    f"|--------|-------|",
                    f"| Cold Start | {s.cold_start_ms:.1f} ms |",
                    f"| Warm Start | {(s.warm_start_ms or 0):.1f} ms |",
                    "",
                ]

        if run.cost_estimate:
            c = run.cost_estimate
            lines += [
                "## Cost Estimate",
                f"| Metric | Value |",
                f"|--------|-------|",
                f"| Total Cost | ${c.total_cost_usd:.4f} |",
                f"| Cost/Request | ${c.cost_per_request_usd:.6f} |",
                f"| Cost/1M Tokens | ${c.cost_per_1m_tokens_usd:.4f} |",
                f"| Projected Monthly | ${c.projected_monthly_cost_usd:.2f} |",
                "",
            ]

        if run.concurrency_results:
            lines += [
                "## Concurrency Sweep",
                "| Concurrency | TTFT p50 | TTFT p99 | RPS | Tokens/s | Error % |",
                "|------------|----------|----------|-----|----------|---------|",
            ]
            for r in run.concurrency_results:
                s = r.summary
                lines.append(
                    f"| {r.concurrency_level} | {s.ttft.p50:.1f} | {s.ttft.p99:.1f} | "
                    f"{s.throughput_rps:.2f} | {s.tokens_per_second:.1f} | {s.error_rate*100:.1f}% |"
                )
            lines.append("")

        content = "\n".join(lines)
        path = self._reports_dir / "markdown" / f"{run.id}.md"
        path.write_text(content, encoding="utf-8")

        return BenchmarkReport(
            run_id=run.id,
            run_name=run.name,
            format=ReportFormat.MARKDOWN,
            content=content,
            file_path=str(path),
        )

    # ── JSON ──────────────────────────────────────────────────────────────────

    def generate_json(self, run: BenchmarkRun) -> BenchmarkReport:
        payload: dict[str, Any] = {
            "run_id": run.id,
            "name": run.name,
            "status": run.status.value,
            "benchmark_type": run.benchmark_type.value,
            "created_at": run.created_at.isoformat(),
            "notes": run.notes,
        }

        if run.endpoint_summary:
            s = run.endpoint_summary
            payload["endpoint_summary"] = {
                "total_requests": s.total_requests,
                "successful_requests": s.successful_requests,
                "error_rate": round(s.error_rate, 4),
                "success_rate": round(s.success_rate, 4),
                "throughput_rps": round(s.throughput_rps, 3),
                "tokens_per_second": round(s.tokens_per_second, 2),
                "total_tokens": s.total_tokens_total,
                "duration_seconds": round(s.duration_seconds, 2),
                "ttft_ms": s.ttft.model_dump(),
                "latency_ms": s.latency.model_dump(),
                "cold_start_ms": s.cold_start_ms,
                "warm_start_ms": s.warm_start_ms,
            }

        if run.cost_estimate:
            c = run.cost_estimate
            payload["cost"] = {
                "total_cost_usd": round(c.total_cost_usd, 6),
                "cost_per_request_usd": round(c.cost_per_request_usd, 8),
                "cost_per_1m_tokens_usd": round(c.cost_per_1m_tokens_usd, 4),
                "projected_monthly_usd": round(c.projected_monthly_cost_usd, 2),
            }

        if run.concurrency_results:
            payload["concurrency_sweep"] = [
                {
                    "concurrency": r.concurrency_level,
                    "ttft_p50_ms": round(r.summary.ttft.p50, 2),
                    "ttft_p99_ms": round(r.summary.ttft.p99, 2),
                    "throughput_rps": round(r.summary.throughput_rps, 3),
                    "tokens_per_second": round(r.summary.tokens_per_second, 2),
                    "error_rate": round(r.summary.error_rate, 4),
                }
                for r in run.concurrency_results
            ]

        content = json.dumps(payload, indent=2, ensure_ascii=False)
        path = self._reports_dir / "json" / f"{run.id}.json"
        path.write_text(content, encoding="utf-8")

        return BenchmarkReport(
            run_id=run.id,
            run_name=run.name,
            format=ReportFormat.JSON,
            content=content,
            file_path=str(path),
        )

    # ── HTML ──────────────────────────────────────────────────────────────────

    def generate_html(self, run: BenchmarkRun) -> BenchmarkReport:
        template_path = Path("templates")
        if not template_path.exists():
            template_path = Path(__file__).parent.parent.parent / "templates"

        try:
            env = Environment(
                loader=FileSystemLoader(str(template_path)),
                autoescape=select_autoescape(["html"]),
            )
            template = env.get_template("report.html.jinja2")
            content = template.render(run=run, generated_at=datetime.utcnow())
        except Exception:
            content = self._fallback_html(run)

        path = self._reports_dir / "html" / f"{run.id}.html"
        path.write_text(content, encoding="utf-8")

        return BenchmarkReport(
            run_id=run.id,
            run_name=run.name,
            format=ReportFormat.HTML,
            content=content,
            file_path=str(path),
        )

    def _fallback_html(self, run: BenchmarkRun) -> str:
        s = run.endpoint_summary
        rows = ""
        if s:
            rows = f"""
            <tr><td>Total Requests</td><td>{s.total_requests}</td></tr>
            <tr><td>Success Rate</td><td>{s.success_rate*100:.1f}%</td></tr>
            <tr><td>TTFT p50</td><td>{s.ttft.p50:.1f} ms</td></tr>
            <tr><td>TTFT p99</td><td>{s.ttft.p99:.1f} ms</td></tr>
            <tr><td>Throughput</td><td>{s.throughput_rps:.2f} req/s</td></tr>
            <tr><td>Tokens/sec</td><td>{s.tokens_per_second:.1f}</td></tr>
            """
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>NebiusBench Report: {run.name}</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 900px; margin: 40px auto; background: #0e1117; color: #e8eaf0; }}
  h1 {{ color: #00a3ff; }} table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ padding: 10px 14px; border: 1px solid #2d3748; text-align: left; }}
  th {{ background: #1c2333; }} tr:nth-child(even) {{ background: #1a2035; }}
</style>
</head>
<body>
<h1>NebiusBench Report</h1>
<h2>{run.name}</h2>
<p>Status: <strong>{run.status.value}</strong> | Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</p>
<table><thead><tr><th>Metric</th><th>Value</th></tr></thead><tbody>{rows}</tbody></table>
</body>
</html>"""
