"""Page 3 — Live Metrics."""

from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import numpy as np
import pandas as pd
import plotly.express as px
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
    PLOTLY_THEME,
)
from benchmark.metrics.analyzer import MetricsAnalyzer
from benchmark.models import BenchmarkRun
from benchmark.storage.database import get_session_factory, init_db
from benchmark.storage.repository import BenchmarkRepository

st.set_page_config(page_title="Live Metrics · NebiusBench", page_icon="📊", layout="wide")
apply_global_styles()
page_header("Live Metrics", "Real-time performance metrics for your benchmark runs", "📊")

init_db()


def _load_runs() -> list[dict]:
    try:
        factory = get_session_factory()
        with factory() as db:
            repo = BenchmarkRepository(db)
            return repo.get_run_summary_list()
    except Exception:
        return []


def _load_run_results(run_id: str):
    try:
        factory = get_session_factory()
        with factory() as db:
            repo = BenchmarkRepository(db)
            return repo.get_results(run_id)
    except Exception:
        return []


# ─── Sidebar: Run Selector ────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"### Select Run")
    runs = _load_runs()

    if not runs:
        st.info("No completed runs yet. Run a benchmark first.")
        st.stop()

    completed_runs = [r for r in runs if r["status"] == "completed"]
    run_names = {r["id"]: f"{r['name']} ({r['created_at']})" for r in completed_runs}

    if not run_names:
        st.info("No completed runs available.")
        st.stop()

    selected_id = st.selectbox("Benchmark Run", list(run_names.keys()),
                                format_func=lambda x: run_names[x])

    auto_refresh = st.toggle("Auto Refresh (5s)", value=False)
    refresh_btn = st.button("Refresh Now")

if auto_refresh:
    time.sleep(5)
    st.rerun()

if refresh_btn:
    st.rerun()

# ─── Load selected run results ────────────────────────────────────────────────
results = _load_run_results(selected_id)
run_meta = next((r for r in completed_runs if r["id"] == selected_id), {})

if not results:
    st.warning("No metric data found for this run.")
    st.stop()

endpoint_result = next((r for r in results if r.result_type == "endpoint"), None)
concurrency_results = [r for r in results if r.result_type == "concurrency"]

# ─── Top KPI Metrics ─────────────────────────────────────────────────────────
st.markdown(f"#### {run_meta.get('name', 'Run')} — Key Performance Indicators")

if endpoint_result:
    m = endpoint_result.metrics
    ttft = m.get("ttft", {})
    latency = m.get("latency", {})

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("TTFT p50", f"{ttft.get('p50', 0):.1f} ms")
    col2.metric("TTFT p90", f"{ttft.get('p90', 0):.1f} ms")
    col3.metric("TTFT p99", f"{ttft.get('p99', 0):.1f} ms")
    col4.metric("Throughput", f"{m.get('throughput_rps', 0):.2f} rps")
    col5.metric("Tokens/sec", f"{m.get('tokens_per_second', 0):.0f}")
    col6.metric(
        "Error Rate",
        f"{m.get('error_rate', 0)*100:.1f}%",
        delta_color="inverse",
    )

    col7, col8, col9, col10 = st.columns(4)
    col7.metric("Success Rate", f"{m.get('success_rate', 0)*100:.1f}%")
    col8.metric("Latency p50", f"{latency.get('p50', 0):.1f} ms")
    col9.metric("Latency p99", f"{latency.get('p99', 0):.1f} ms")
    col10.metric("Total Tokens", f"{m.get('total_tokens', 0):,}")

st.divider()

# ─── Charts ───────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["TTFT Analysis", "Throughput", "Latency Distribution", "Error Analysis"])

with tab1:
    st.markdown("#### Time To First Token")
    if endpoint_result:
        m = endpoint_result.metrics
        ttft_data = m.get("ttft", {})
        raw = endpoint_result.raw_data

        if raw:
            ttft_series = [r.get("ttft_ms") for r in raw if r.get("ttft_ms") is not None]
            if ttft_series:
                col_hist, col_box = st.columns(2)
                with col_hist:
                    fig_hist = px.histogram(
                        x=ttft_series, nbins=40,
                        title=f"TTFT Distribution (n={len(ttft_series)})",
                        labels={"x": "TTFT (ms)", "y": "Count"},
                        color_discrete_sequence=[NEBIUS_BLUE],
                    )
                    fig_hist.update_layout(**PLOTLY_THEME, height=350, margin=dict(l=40,r=20,t=40,b=40))
                    st.plotly_chart(fig_hist, use_container_width=True)
                with col_box:
                    fig_box = go.Figure(go.Box(
                        y=ttft_series,
                        boxmean="sd",
                        fillcolor=f"rgba(0,163,255,0.2)",
                        line=dict(color=NEBIUS_BLUE),
                        name="TTFT",
                    ))
                    fig_box.update_layout(
                        **PLOTLY_THEME, height=350,
                        title="TTFT Box Plot", yaxis_title="ms",
                        margin=dict(l=40,r=20,t=40,b=40),
                    )
                    st.plotly_chart(fig_box, use_container_width=True)

                window = max(5, len(ttft_series) // 30)
                p50s, p90s, p99s, xs = [], [], [], []
                for i in range(window, len(ttft_series) + 1, max(1, len(ttft_series) // 50)):
                    sl = np.array(ttft_series[max(0, i - window): i])
                    p50s.append(float(np.percentile(sl, 50)))
                    p90s.append(float(np.percentile(sl, 90)))
                    p99s.append(float(np.percentile(sl, 99)))
                    xs.append(i)
                if xs:
                    fig_timeline = chart_latency_percentiles(p50s, p90s, p99s, xs)
                    fig_timeline.update_layout(title="TTFT Rolling Percentiles")
                    st.plotly_chart(fig_timeline, use_container_width=True)
        else:
            ttft_data = m.get("ttft", {})
            fig_bar = go.Figure(go.Bar(
                x=["p50", "p90", "p95", "p99", "mean"],
                y=[ttft_data.get(k, 0) for k in ["p50", "p90", "p95", "p99", "mean"]],
                marker_color=[NEBIUS_SUCCESS, NEBIUS_BLUE, NEBIUS_WARNING, NEBIUS_ERROR, NEBIUS_MUTED],
                text=[f"{ttft_data.get(k, 0):.1f}" for k in ["p50", "p90", "p95", "p99", "mean"]],
                textposition="outside",
            ))
            fig_bar.update_layout(**PLOTLY_THEME, title="TTFT Percentiles (ms)",
                                  yaxis_title="ms", height=350, margin=dict(l=40,r=20,t=40,b=40))
            st.plotly_chart(fig_bar, use_container_width=True)

with tab2:
    st.markdown("#### Throughput Metrics")
    if concurrency_results:
        levels = sorted(r.concurrency_level for r in concurrency_results)
        level_map = {r.concurrency_level: r.metrics for r in concurrency_results}
        rps_vals = [level_map[l].get("throughput_rps", 0) for l in levels]
        tps_vals = [level_map[l].get("tokens_per_second", 0) for l in levels]

        fig_tput = chart_throughput_vs_concurrency(levels, rps_vals, tps_vals)
        st.plotly_chart(fig_tput, use_container_width=True)

        p50_vals = [level_map[l].get("ttft", {}).get("p50", 0) for l in levels]
        p95_vals = [level_map[l].get("ttft", {}).get("p95", 0) for l in levels]
        fig_lat = chart_latency_vs_concurrency(levels, p50_vals, p95_vals)
        st.plotly_chart(fig_lat, use_container_width=True)
    elif endpoint_result:
        m = endpoint_result.metrics
        st.markdown(
            f"""<div class="info-card">
            <strong>Throughput:</strong> {m.get('throughput_rps', 0):.2f} requests/sec<br>
            <strong>Tokens/sec:</strong> {m.get('tokens_per_second', 0):.1f}<br>
            <strong>Total Requests:</strong> {m.get('total_requests', 0)}<br>
            <strong>Duration:</strong> {m.get('duration_seconds', 0):.1f}s
            </div>""",
            unsafe_allow_html=True,
        )
        st.info("Enable concurrency sweep to see throughput scaling curves.")

with tab3:
    st.markdown("#### End-to-End Latency Distribution")
    if endpoint_result and endpoint_result.raw_data:
        raw = endpoint_result.raw_data
        lat_series = [r.get("total_latency_ms", 0) for r in raw if r.get("is_success")]
        if lat_series:
            fig_lat_hist = px.histogram(
                x=lat_series, nbins=40,
                title="End-to-End Latency Distribution",
                labels={"x": "Latency (ms)", "y": "Count"},
                color_discrete_sequence=[NEBIUS_SUCCESS],
            )
            fig_lat_hist.update_layout(**PLOTLY_THEME, height=350, margin=dict(l=40,r=20,t=40,b=40))
            st.plotly_chart(fig_lat_hist, use_container_width=True)

            lat_arr = np.array(lat_series)
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown(
                    f"""<div class="info-card">
                    <strong>p50:</strong> {np.percentile(lat_arr, 50):.1f} ms<br>
                    <strong>p90:</strong> {np.percentile(lat_arr, 90):.1f} ms<br>
                    <strong>p95:</strong> {np.percentile(lat_arr, 95):.1f} ms<br>
                    <strong>p99:</strong> {np.percentile(lat_arr, 99):.1f} ms
                    </div>""",
                    unsafe_allow_html=True,
                )
            with col_b:
                st.markdown(
                    f"""<div class="info-card">
                    <strong>Mean:</strong> {np.mean(lat_arr):.1f} ms<br>
                    <strong>Std Dev:</strong> {np.std(lat_arr):.1f} ms<br>
                    <strong>Min:</strong> {np.min(lat_arr):.1f} ms<br>
                    <strong>Max:</strong> {np.max(lat_arr):.1f} ms
                    </div>""",
                    unsafe_allow_html=True,
                )
    elif endpoint_result:
        lat = endpoint_result.metrics.get("latency", {})
        st.markdown(
            f"""<div class="info-card">
            <strong>p50:</strong> {lat.get('p50', 0):.1f} ms &nbsp;|&nbsp;
            <strong>p90:</strong> {lat.get('p90', 0):.1f} ms &nbsp;|&nbsp;
            <strong>p99:</strong> {lat.get('p99', 0):.1f} ms
            </div>""",
            unsafe_allow_html=True,
        )

with tab4:
    st.markdown("#### Error Rate Analysis")
    if concurrency_results:
        levels = sorted(r.concurrency_level for r in concurrency_results)
        level_map = {r.concurrency_level: r.metrics for r in concurrency_results}
        err_pct = [level_map[l].get("error_rate", 0) * 100 for l in levels]
        fig_err = chart_error_rate_vs_concurrency(levels, err_pct)
        st.plotly_chart(fig_err, use_container_width=True)
    elif endpoint_result:
        m = endpoint_result.metrics
        err_rate = m.get("error_rate", 0)
        total = m.get("total_requests", 1)
        success = m.get("successful_requests", 0)
        failed = m.get("failed_requests", 0)
        col_pie_a, col_pie_b = st.columns(2)
        with col_pie_a:
            fig_pie = go.Figure(go.Pie(
                labels=["Successful", "Failed"],
                values=[success, max(failed, 0)],
                marker_colors=[NEBIUS_SUCCESS, NEBIUS_ERROR],
                hole=0.4,
            ))
            fig_pie.update_layout(**PLOTLY_THEME, title="Request Outcomes", height=320,
                                  margin=dict(l=20,r=20,t=40,b=20))
            st.plotly_chart(fig_pie, use_container_width=True)
        with col_pie_b:
            color = NEBIUS_ERROR if err_rate > 0.05 else NEBIUS_WARNING if err_rate > 0.01 else NEBIUS_SUCCESS
            st.markdown(
                f"""<div class="info-card" style="border-left-color:{color}">
                <strong>Error Rate:</strong> {err_rate*100:.2f}%<br>
                <strong>Successful:</strong> {success:,}<br>
                <strong>Failed:</strong> {failed:,}<br>
                <strong>Total:</strong> {total:,}
                </div>""",
                unsafe_allow_html=True,
            )

st.divider()

# ─── Raw metrics table ────────────────────────────────────────────────────────
if endpoint_result and endpoint_result.raw_data:
    with st.expander("Raw Request Data"):
        raw = endpoint_result.raw_data[:500]
        df = pd.DataFrame([
            {
                "Seq": r.get("sequence_num"),
                "TTFT (ms)": round(r.get("ttft_ms", 0) or 0, 1),
                "Latency (ms)": round(r.get("total_latency_ms", 0), 1),
                "Tokens/s": round(r.get("tokens_per_second", 0), 1),
                "Completion Tokens": r.get("completion_tokens", 0),
                "Success": "✓" if r.get("is_success") else "✗",
            }
            for r in raw
        ])
        st.dataframe(df, use_container_width=True, hide_index=True)
