"""Page 6 — Report Generator."""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from app.ui_utils import (
    NEBIUS_BLUE, NEBIUS_CARD, NEBIUS_BORDER, NEBIUS_MUTED, NEBIUS_TEXT,
    NEBIUS_SUCCESS, NEBIUS_ERROR, NEBIUS_WARNING,
    apply_global_styles, page_header,
)
from benchmark.metrics.reporter import MetricsReporter
from benchmark.models import (
    BenchmarkConfig, BenchmarkRun, BenchmarkStatus, BenchmarkType,
    ConcurrencyResult, CostEstimate, EndpointBenchmarkSummary, PercentileStats,
    ReportFormat,
)
from benchmark.storage.database import get_session_factory, init_db
from benchmark.storage.repository import BenchmarkRepository
from benchmark.runner import estimate_cost

st.set_page_config(page_title="Report Generator · NebiusBench", page_icon="📄", layout="wide")
apply_global_styles()
page_header("Report Generator", "Generate and download Markdown, JSON, and HTML reports", "📄")

init_db()


def _load_runs():
    try:
        factory = get_session_factory()
        with factory() as db:
            repo = BenchmarkRepository(db)
            return repo.get_run_summary_list()
    except Exception:
        return []


def _load_results(run_id: str):
    try:
        factory = get_session_factory()
        with factory() as db:
            repo = BenchmarkRepository(db)
            return repo.get_results(run_id)
    except Exception:
        return []


def _reconstruct_run(run_meta: dict, results) -> BenchmarkRun:
    """Reconstruct a BenchmarkRun from persisted ORM data for report generation."""
    from datetime import datetime

    endpoint_result = next((r for r in results if r.result_type == "endpoint"), None)
    sweep_results = [r for r in results if r.result_type == "concurrency"]

    config = BenchmarkConfig(
        endpoint_url=run_meta.get("id", "https://api.studio.nebius.com/v1"),
        api_key="[redacted]",
        model=run_meta.get("model", "unknown"),
        concurrency=run_meta.get("concurrency", 1),
        request_count=run_meta.get("request_count", 0),
    )

    summary = None
    if endpoint_result:
        m = endpoint_result.metrics

        def _pct(d: dict) -> PercentileStats:
            return PercentileStats(**{k: d.get(k, 0.0) for k in ["p50", "p90", "p95", "p99", "mean", "min", "max", "std"]})

        summary = EndpointBenchmarkSummary(
            total_requests=m.get("total_requests", 0),
            successful_requests=m.get("successful_requests", 0),
            failed_requests=m.get("failed_requests", 0),
            error_rate=m.get("error_rate", 0.0),
            success_rate=m.get("success_rate", 0.0),
            ttft=_pct(m.get("ttft", {})),
            latency=_pct(m.get("latency", {})),
            inter_token_latency=_pct(m.get("inter_token_latency", {})),
            throughput_rps=m.get("throughput_rps", 0.0),
            tokens_per_second=m.get("tokens_per_second", 0.0),
            total_tokens_total=m.get("total_tokens", 0),
            duration_seconds=m.get("duration_seconds", 0.0),
            cold_start_ms=m.get("cold_start_ms"),
            warm_start_ms=m.get("warm_start_ms"),
        )

    concurrency_list: list[ConcurrencyResult] = []
    for sr in sweep_results:
        m = sr.metrics

        def _pct2(d: dict) -> PercentileStats:
            return PercentileStats(**{k: d.get(k, 0.0) for k in ["p50", "p90", "p95", "p99", "mean", "min", "max", "std"]})

        s = EndpointBenchmarkSummary(
            ttft=_pct2(m.get("ttft", {})),
            throughput_rps=m.get("throughput_rps", 0.0),
            tokens_per_second=m.get("tokens_per_second", 0.0),
            error_rate=m.get("error_rate", 0.0),
            concurrency_level=sr.concurrency_level,
        )
        concurrency_list.append(ConcurrencyResult(concurrency_level=sr.concurrency_level, summary=s))

    cost_est = None
    if summary and summary.total_tokens_total > 0:
        cost_est = estimate_cost(
            model_id=run_meta.get("model", ""),
            prompt_tokens=summary.prompt_tokens_total or int(summary.total_tokens_total * 0.6),
            completion_tokens=summary.completion_tokens_total or int(summary.total_tokens_total * 0.4),
            request_count=summary.total_requests,
        )

    try:
        created_at = datetime.strptime(run_meta["created_at"], "%Y-%m-%d %H:%M")
    except Exception:
        created_at = datetime.utcnow()

    return BenchmarkRun(
        id=run_meta["id"],
        name=run_meta["name"],
        benchmark_type=BenchmarkType(run_meta.get("type", "endpoint")),
        config=config,
        status=BenchmarkStatus(run_meta.get("status", "completed")),
        created_at=created_at,
        endpoint_summary=summary,
        concurrency_results=concurrency_list,
        cost_estimate=cost_est,
    )


runs = _load_runs()
completed_runs = [r for r in runs if r["status"] == "completed"]

if not completed_runs:
    st.markdown(
        f"""<div style="background:{NEBIUS_CARD};border:1px dashed {NEBIUS_BORDER};
                      border-radius:12px;padding:60px;text-align:center;color:{NEBIUS_MUTED}">
            <div style="font-size:3rem;margin-bottom:16px">📄</div>
            <h3 style="color:{NEBIUS_TEXT}">No completed runs available</h3>
            <p>Run a benchmark first to generate reports.</p>
        </div>""",
        unsafe_allow_html=True,
    )
    st.stop()

col_sidebar, col_main = st.columns([3, 7])

with col_sidebar:
    st.markdown(f"<div style='background:{NEBIUS_CARD};border:1px solid {NEBIUS_BORDER};border-radius:12px;padding:20px'>",
                unsafe_allow_html=True)
    st.markdown("##### Select Run")
    run_options = {r["id"]: f"{r['name']}" for r in completed_runs}
    selected_id = st.selectbox("Benchmark Run", list(run_options.keys()),
                                format_func=lambda x: run_options[x])

    sel_meta = next((r for r in completed_runs if r["id"] == selected_id), {})
    st.markdown(
        f"""<div style="margin:12px 0;padding:12px;background:#0e1117;border-radius:8px">
        <div style="color:{NEBIUS_MUTED};font-size:0.75rem">MODEL</div>
        <div style="color:{NEBIUS_TEXT};font-size:0.85rem;font-weight:600">{sel_meta.get('model','').split('/')[-1]}</div>
        <div style="color:{NEBIUS_MUTED};font-size:0.75rem;margin-top:8px">REQUESTS</div>
        <div style="color:{NEBIUS_TEXT};font-size:0.85rem">{sel_meta.get('request_count', 0)}</div>
        <div style="color:{NEBIUS_MUTED};font-size:0.75rem;margin-top:8px">DATE</div>
        <div style="color:{NEBIUS_TEXT};font-size:0.85rem">{sel_meta.get('created_at','')}</div>
        </div>""",
        unsafe_allow_html=True,
    )

    st.markdown("##### Report Options")
    include_raw = st.checkbox("Include raw metrics (JSON only)", value=False)
    notes = st.text_area("Add notes to report", placeholder="e.g. Baseline measurement for Llama 70B...", height=80)

    st.markdown("</div>", unsafe_allow_html=True)

with col_main:
    results = _load_results(selected_id)
    run = _reconstruct_run(sel_meta, results)
    if notes:
        run.notes = notes

    reporter = MetricsReporter()

    st.markdown(f"#### Report Preview: {run.name}")

    preview_tab, md_tab, json_tab, html_tab = st.tabs(["Preview", "Markdown", "JSON", "HTML"])

    with preview_tab:
        if run.endpoint_summary:
            s = run.endpoint_summary
            st.markdown(f"**Model:** `{sel_meta.get('model', 'unknown')}`")
            st.markdown(f"**Status:** {run.status.value.upper()}")

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("TTFT p50", f"{s.ttft.p50:.1f} ms")
            c2.metric("TTFT p99", f"{s.ttft.p99:.1f} ms")
            c3.metric("Throughput", f"{s.throughput_rps:.2f} rps")
            c4.metric("Error Rate", f"{s.error_rate*100:.1f}%")

            if run.concurrency_results:
                st.markdown("**Concurrency Sweep Summary:**")
                sweep_df = [
                    {
                        "Concurrency": r.concurrency_level,
                        "TTFT p50 (ms)": round(r.summary.ttft.p50, 1),
                        "TTFT p99 (ms)": round(r.summary.ttft.p99, 1),
                        "RPS": round(r.summary.throughput_rps, 2),
                        "Error %": round(r.summary.error_rate * 100, 1),
                    }
                    for r in run.concurrency_results
                ]
                import pandas as pd
                st.dataframe(pd.DataFrame(sweep_df), use_container_width=True, hide_index=True)

            if run.cost_estimate:
                c = run.cost_estimate
                st.markdown("**Cost Estimate:**")
                cc1, cc2, cc3 = st.columns(3)
                cc1.metric("Total Cost", f"${c.total_cost_usd:.6f}")
                cc2.metric("Per Request", f"${c.cost_per_request_usd:.8f}")
                cc3.metric("Per 1M Tokens", f"${c.cost_per_1m_tokens_usd:.4f}")

    # ── Generate reports on demand ─────────────────────────────────────────────
    with md_tab:
        if st.button("Generate Markdown Report", type="primary", key="gen_md"):
            with st.spinner("Generating..."):
                rpt = reporter.generate_markdown(run)
            st.code(rpt.content, language="markdown")
            st.download_button(
                "Download Markdown", rpt.content,
                file_name=f"nebiusbench_{run.id[:8]}.md",
                mime="text/markdown",
                use_container_width=True,
            )
            if rpt.file_path:
                st.success(f"Saved to: {rpt.file_path}")

    with json_tab:
        if st.button("Generate JSON Report", type="primary", key="gen_json"):
            with st.spinner("Generating..."):
                rpt = reporter.generate_json(run)
            st.json(json.loads(rpt.content))
            st.download_button(
                "Download JSON", rpt.content,
                file_name=f"nebiusbench_{run.id[:8]}.json",
                mime="application/json",
                use_container_width=True,
            )
            if rpt.file_path:
                st.success(f"Saved to: {rpt.file_path}")

    with html_tab:
        if st.button("Generate HTML Report", type="primary", key="gen_html"):
            with st.spinner("Generating..."):
                rpt = reporter.generate_html(run)
            st.components.v1.html(rpt.content, height=500, scrolling=True)
            st.download_button(
                "Download HTML", rpt.content,
                file_name=f"nebiusbench_{run.id[:8]}.html",
                mime="text/html",
                use_container_width=True,
            )
            if rpt.file_path:
                st.success(f"Saved to: {rpt.file_path}")

    st.divider()
    st.markdown("#### Generate All Reports at Once")
    if st.button("Generate All Formats (MD + JSON + HTML)", use_container_width=True):
        with st.spinner("Generating all reports..."):
            md_rpt = reporter.generate_markdown(run)
            json_rpt = reporter.generate_json(run)
            html_rpt = reporter.generate_html(run)

        c_dl1, c_dl2, c_dl3 = st.columns(3)
        c_dl1.download_button("📄 Markdown", md_rpt.content,
                               file_name=f"nebiusbench_{run.id[:8]}.md",
                               mime="text/markdown", use_container_width=True)
        c_dl2.download_button("📊 JSON", json_rpt.content,
                               file_name=f"nebiusbench_{run.id[:8]}.json",
                               mime="application/json", use_container_width=True)
        c_dl3.download_button("🌐 HTML", html_rpt.content,
                               file_name=f"nebiusbench_{run.id[:8]}.html",
                               mime="text/html", use_container_width=True)
        st.success(f"Reports saved to: reports/markdown/, reports/json/, reports/html/")
