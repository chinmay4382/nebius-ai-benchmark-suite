"""Page 2 — Run Benchmark."""

from __future__ import annotations

import os
import sys
import threading
import time
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from app.ui_utils import (
    NEBIUS_BLUE, NEBIUS_CARD, NEBIUS_BORDER, NEBIUS_MUTED, NEBIUS_TEXT,
    NEBIUS_SUCCESS, NEBIUS_ERROR, NEBIUS_WARNING,
    apply_global_styles, page_header,
    chart_latency_percentiles, chart_throughput_vs_concurrency,
    chart_latency_vs_concurrency, chart_error_rate_vs_concurrency,
)
from benchmark.models import (
    BenchmarkConfig, BenchmarkRun, BenchmarkStatus, LiveUpdate,
    PromptDataset, BenchmarkType,
)
from benchmark.runner import BenchmarkRunner, estimate_cost, get_model_pricing
from benchmark.metrics.analyzer import MetricsAnalyzer

st.set_page_config(page_title="Run Benchmark · NebiusBench", page_icon="🚀", layout="wide")
apply_global_styles()
page_header("Run Benchmark", "Configure and launch a benchmark against a Nebius AI endpoint", "🚀")

# ─── Session state ────────────────────────────────────────────────────────────
if "bench_run" not in st.session_state:
    st.session_state.bench_run: Optional[BenchmarkRun] = None
if "live_updates" not in st.session_state:
    st.session_state.live_updates: list[LiveUpdate] = []
if "running" not in st.session_state:
    st.session_state.running = False


def _load_models() -> list[str]:
    pricing = get_model_pricing()
    models = list(pricing.keys())
    if not models:
        models = ["meta-llama/Meta-Llama-3.1-8B-Instruct-fast",
                  "meta-llama/Meta-Llama-3.1-70B-Instruct-fast",
                  "mistralai/Mistral-7B-Instruct-v0.3"]
    return models


# ─── Config Form ──────────────────────────────────────────────────────────────
col_form, col_results = st.columns([4, 6])

with col_form:
    st.markdown(
        f"<div style='background:{NEBIUS_CARD};border:1px solid {NEBIUS_BORDER};"
        f"border-radius:12px;padding:24px'>",
        unsafe_allow_html=True,
    )
    st.markdown(f"##### Endpoint Configuration")

    default_url = os.getenv("NEBIUS_BASE_URL", "https://api.studio.nebius.com/v1")
    endpoint_url = st.text_input(
        "Endpoint URL",
        value=default_url,
        placeholder="https://api.studio.nebius.com/v1",
        help="OpenAI-compatible base URL (without /chat/completions)",
    )

    models = _load_models()
    model = st.selectbox("Model", models, index=0)

    st.markdown(f"##### Benchmark Parameters")
    col_a, col_b = st.columns(2)
    with col_a:
        request_count = st.number_input("Request Count", min_value=1, max_value=5000, value=50, step=10)
        max_tokens = st.number_input("Max Output Tokens", min_value=1, max_value=4096, value=256, step=64)
    with col_b:
        concurrency = st.number_input("Concurrency", min_value=1, max_value=200, value=10, step=5)
        temperature = st.slider("Temperature", 0.0, 2.0, 0.7, 0.1)

    prompt_dataset = st.selectbox(
        "Prompt Dataset",
        [p.value for p in PromptDataset],
        index=1,
        help="short / medium / long / code / custom",
    )
    custom_prompt = ""
    if prompt_dataset == PromptDataset.CUSTOM.value:
        custom_prompt = st.text_area("Custom Prompt", height=80)

    streaming = st.toggle("Enable Streaming (SSE)", value=True,
                          help="Streaming is required for accurate TTFT measurement")

    st.markdown(f"##### Advanced Options")
    col_c, col_d = st.columns(2)
    with col_c:
        include_cold_start = st.checkbox("Cold/Warm Start Probes", value=True)
    with col_d:
        include_sweep = st.checkbox("Concurrency Sweep", value=True)

    if include_sweep:
        sweep_levels_raw = st.text_input(
            "Concurrency Levels (comma-separated)",
            value="1, 5, 10, 25, 50",
        )
        sweep_levels = [int(x.strip()) for x in sweep_levels_raw.split(",") if x.strip().isdigit()]
    else:
        sweep_levels = []

    run_name = st.text_input("Run Name (optional)", placeholder="e.g. Llama 70B baseline")
    tags_raw = st.text_input("Tags (optional, comma-separated)", placeholder="prod, llama, 70b")
    tags = [t.strip() for t in tags_raw.split(",") if t.strip()]

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("")
    can_run = bool(endpoint_url and not st.session_state.running)
    run_btn = st.button(
        "🚀 Run Benchmark",
        disabled=not can_run,
        use_container_width=True,
        type="primary",
    )

# ─── Benchmark Execution ──────────────────────────────────────────────────────
with col_results:
    if run_btn and can_run:
        st.session_state.running = True
        st.session_state.live_updates = []
        st.session_state.bench_run = None

        config = BenchmarkConfig(
            endpoint_url=endpoint_url,
            model=model,
            concurrency=concurrency,
            request_count=request_count,
            max_tokens=max_tokens,
            temperature=temperature,
            streaming=streaming,
            prompt_dataset=PromptDataset(prompt_dataset),
            custom_prompt=custom_prompt or None,
        )

        status_container = st.empty()
        progress_bar = st.progress(0.0)
        progress_text = st.empty()
        live_chart = st.empty()

        updates: list[LiveUpdate] = []
        completed_metrics = []

        def on_update(u: LiveUpdate) -> None:
            updates.append(u)
            if u.latest_metric:
                completed_metrics.append(u.latest_metric)

        result_holder: dict = {}

        def _run_in_thread() -> None:
            runner = BenchmarkRunner(persist=True)
            try:
                run = runner.run_endpoint_benchmark(
                    config=config,
                    run_name=run_name or "",
                    concurrency_levels=sweep_levels or None,
                    include_cold_start=include_cold_start,
                    include_sweep=include_sweep,
                    on_update=on_update,
                    tags=tags,
                )
                result_holder["run"] = run
            except Exception as exc:
                result_holder["error"] = str(exc)

        thread = threading.Thread(target=_run_in_thread, daemon=True)
        thread.start()

        with status_container:
            st.info("Benchmark started — streaming results...")

        while thread.is_alive():
            if updates:
                latest = updates[-1]
                prog = min(latest.request_num / max(request_count, 1), 0.95)
                progress_bar.progress(prog)
                progress_text.markdown(
                    f"<span style='color:{NEBIUS_MUTED};font-size:0.85rem'>{latest.message}</span>",
                    unsafe_allow_html=True,
                )

                if len(completed_metrics) >= 5:
                    ttft_vals = [m.ttft_ms for m in completed_metrics if m.ttft_ms is not None]
                    lat_vals = [m.total_latency_ms for m in completed_metrics if m.is_success]
                    if len(ttft_vals) >= 3:
                        import numpy as np
                        window = 10
                        p50s, p90s, p99s, xs = [], [], [], []
                        for i in range(window, len(ttft_vals) + 1, max(1, len(ttft_vals) // 30)):
                            sl = ttft_vals[max(0, i - window): i]
                            arr = np.array(sl)
                            p50s.append(float(np.percentile(arr, 50)))
                            p90s.append(float(np.percentile(arr, 90)))
                            p99s.append(float(np.percentile(arr, 99)))
                            xs.append(i)
                        if xs:
                            fig = chart_latency_percentiles(p50s, p90s, p99s, xs)
                            fig.update_layout(title="Live TTFT Percentiles", height=280)
                            live_chart.plotly_chart(fig, use_container_width=True)

            time.sleep(0.5)

        thread.join()
        progress_bar.progress(1.0)

        if "error" in result_holder:
            status_container.error(f"Benchmark failed: {result_holder['error']}")
            st.session_state.running = False
        else:
            run: BenchmarkRun = result_holder["run"]
            st.session_state.bench_run = run
            st.session_state.running = False
            status_container.success(f"Benchmark completed: {run.name}")
            st.rerun()

    # ── Results Display ───────────────────────────────────────────────────────
    run = st.session_state.get("bench_run")
    if run and run.endpoint_summary:
        s = run.endpoint_summary
        st.markdown(f"#### Results: {run.name}")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("TTFT p50", f"{s.ttft.p50:.1f} ms", f"p99: {s.ttft.p99:.1f} ms")
        col2.metric("Throughput", f"{s.throughput_rps:.2f} req/s")
        col3.metric("Tokens/sec", f"{s.tokens_per_second:.0f}")
        col4.metric(
            "Error Rate",
            f"{s.error_rate*100:.1f}%",
            delta_color="inverse" if s.error_rate > 0.05 else "normal",
        )

        col5, col6, col7, col8 = st.columns(4)
        col5.metric("TTFT p90", f"{s.ttft.p90:.1f} ms")
        col6.metric("TTFT p99", f"{s.ttft.p99:.1f} ms")
        col7.metric("Latency p50", f"{s.latency.p50:.1f} ms")
        col8.metric("Total Tokens", f"{s.total_tokens_total:,}")

        if s.cold_start_ms is not None:
            c9, c10 = st.columns(2)
            c9.metric("Cold Start", f"{s.cold_start_ms:.0f} ms")
            c10.metric("Warm Start", f"{(s.warm_start_ms or 0):.0f} ms")

        tab1, tab2, tab3, tab4 = st.tabs(["TTFT Chart", "Concurrency Sweep", "Cost", "Raw Data"])

        with tab1:
            ttft_vals = [m.ttft_ms for m in s.raw_metrics if m.ttft_ms is not None]
            if ttft_vals:
                import plotly.express as px
                fig = px.histogram(
                    x=ttft_vals, nbins=40,
                    title=f"TTFT Distribution (n={len(ttft_vals)})",
                    labels={"x": "TTFT (ms)", "y": "Count"},
                    color_discrete_sequence=[NEBIUS_BLUE],
                )
                fig.update_layout(
                    plot_bgcolor=NEBIUS_CARD, paper_bgcolor="#0E1117",
                    font_color=NEBIUS_TEXT, height=350,
                )
                st.plotly_chart(fig, use_container_width=True)

                timeline = MetricsAnalyzer.compute_percentile_timeline(s.raw_metrics)
                if timeline["idx"]:
                    fig2 = chart_latency_percentiles(
                        timeline["p50"], timeline["p90"], timeline["p99"], timeline["idx"]
                    )
                    fig2.update_layout(title="TTFT Percentiles Over Request Timeline")
                    st.plotly_chart(fig2, use_container_width=True)

        with tab2:
            if run.concurrency_results:
                sweep_data = MetricsAnalyzer.analyze_concurrency_sweep(run.concurrency_results)
                c_fig1 = chart_throughput_vs_concurrency(
                    sweep_data["concurrency"],
                    sweep_data["throughput_rps"],
                    sweep_data["tokens_per_second"],
                )
                st.plotly_chart(c_fig1, use_container_width=True)

                c_fig2 = chart_latency_vs_concurrency(
                    sweep_data["concurrency"],
                    sweep_data["ttft_p50_ms"],
                    sweep_data["ttft_p95_ms"],
                )
                st.plotly_chart(c_fig2, use_container_width=True)

                c_fig3 = chart_error_rate_vs_concurrency(
                    sweep_data["concurrency"], sweep_data["error_rate_pct"]
                )
                st.plotly_chart(c_fig3, use_container_width=True)
            else:
                st.info("Enable concurrency sweep to see scaling data.")

        with tab3:
            if run.cost_estimate:
                c = run.cost_estimate
                cc1, cc2, cc3 = st.columns(3)
                cc1.metric("Total Cost", f"${c.total_cost_usd:.6f}")
                cc2.metric("Cost / Request", f"${c.cost_per_request_usd:.8f}")
                cc3.metric("Cost / 1M Tokens", f"${c.cost_per_1m_tokens_usd:.4f}")

                from app.ui_utils import chart_cost_projection
                proj_fig = chart_cost_projection(c.projected_monthly_cost_at_rps)
                st.plotly_chart(proj_fig, use_container_width=True)

        with tab4:
            if s.raw_metrics:
                import pandas as pd
                df_raw = pd.DataFrame([
                    {
                        "Seq": m.sequence_num,
                        "TTFT (ms)": round(m.ttft_ms, 1) if m.ttft_ms else None,
                        "Latency (ms)": round(m.total_latency_ms, 1),
                        "Tokens/s": round(m.tokens_per_second, 1),
                        "Completion Tokens": m.completion_tokens,
                        "Success": "✓" if m.is_success else "✗",
                        "Error": m.error or "",
                    }
                    for m in s.raw_metrics[:500]
                ])
                st.dataframe(df_raw, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("**Generate Reports**")
        r_col1, r_col2, r_col3 = st.columns(3)
        runner_instance = BenchmarkRunner(persist=False)
        if r_col1.button("📄 Markdown"):
            rpt = runner_instance.generate_reports(run, formats=[__import__("benchmark.models", fromlist=["ReportFormat"]).ReportFormat.MARKDOWN])[0]
            st.download_button("Download .md", rpt.content, file_name=f"{run.id}.md", mime="text/markdown")
        if r_col2.button("📊 JSON"):
            rpt = runner_instance.generate_reports(run, formats=[__import__("benchmark.models", fromlist=["ReportFormat"]).ReportFormat.JSON])[0]
            st.download_button("Download .json", rpt.content, file_name=f"{run.id}.json", mime="application/json")
        if r_col3.button("🌐 HTML"):
            rpt = runner_instance.generate_reports(run, formats=[__import__("benchmark.models", fromlist=["ReportFormat"]).ReportFormat.HTML])[0]
            st.download_button("Download .html", rpt.content, file_name=f"{run.id}.html", mime="text/html")

    elif not st.session_state.running:
        st.markdown(
            f"""<div style="background:{NEBIUS_CARD};border:1px dashed {NEBIUS_BORDER};
                          border-radius:12px;padding:60px;text-align:center;color:{NEBIUS_MUTED}">
                <div style="font-size:3rem;margin-bottom:16px">🚀</div>
                <h3 style="color:{NEBIUS_TEXT};margin:0 0 8px">Ready to Benchmark</h3>
                <p>Configure your endpoint on the left and click <strong>Run Benchmark</strong></p>
            </div>""",
            unsafe_allow_html=True,
        )
